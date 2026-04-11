"""
FetchWorker — QThread that fetches Scryfall metadata then downloads card images.

Phase 1 (sequential): resolve metadata for each unique card.
  - Metadata (card ID, layout, image URLs) is cached to disk; cached cards
    skip the API call entirely and cost no delay.
  - Only cards not in the metadata cache hit the /cards/named endpoint,
    with a 600 ms inter-request delay to respect Scryfall's rate limit.

Phase 2 (concurrent): download any missing images (up to 5 threads).
  - Already-cached images are skipped immediately.
  - card_ready is emitted as soon as each card's images are confirmed on disk,
    so thumbnails populate progressively rather than all at once.

Signals:
  progress(current: int, total: int)  — use for progress bar
  card_ready(name: str, front_path: object, back_path: object)
  card_error(name: str, message: str)
  finished()
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

from core import scryfall
from core.decklist_parser import CardEntry


class FetchWorker(QThread):
    progress   = Signal(int, int)            # current, total
    card_ready = Signal(str, object, object) # name, front_path, back_path|None
    card_error = Signal(str, str)            # name, message
    finished   = Signal()

    def __init__(self, entries: list[CardEntry], parent=None):
        super().__init__(parent)
        self.entries = entries
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    # ------------------------------------------------------------------

    def run(self) -> None:
        scryfall.ensure_cache()

        # Deduplicate by name, preserving first occurrence (carries set annotation).
        name_to_rep: dict[str, CardEntry] = {}
        for e in self.entries:
            if e.name not in name_to_rep:
                name_to_rep[e.name] = e
        unique_names = list(name_to_rep.keys())

        meta_total = len(unique_names)
        metadata_cache = scryfall.load_metadata_cache()

        # ---------------------------------------------------------------
        # Phase 1: Resolve metadata (cache-first, then API)
        # ---------------------------------------------------------------
        card_info: dict[str, dict] = {}
        api_call_count = 0  # track how many calls actually need the rate-limit delay

        for i, name in enumerate(unique_names):
            if self._stop:
                self.finished.emit()
                return

            self.progress.emit(i, meta_total * 2)

            rep = name_to_rep[name]
            cache_key = scryfall.metadata_cache_key(
                name, rep.set_code, rep.collector_number
            )

            if cache_key in metadata_cache:
                # Fast path — no network call needed
                info = metadata_cache[cache_key]
                card_info[name] = info
                for entry in self.entries:
                    if entry.name == name:
                        entry.scryfall_id      = info["card_id"]
                        entry.layout           = info["layout"]
                        entry.front_image_path = Path(info["front_path"])
                        entry.back_image_path  = Path(info["back_path"]) if info.get("back_path") else None
                continue

            # Slow path — hit the Scryfall API
            if api_call_count > 0:
                time.sleep(scryfall.REQUEST_DELAY)
            api_call_count += 1

            try:
                card = scryfall.fetch_card_metadata(
                    name,
                    set_code=rep.set_code,
                    collector_number=rep.collector_number,
                )
                layout   = card.get("layout", "normal")
                card_id  = card["id"]

                front_url, back_url = scryfall.get_image_urls(card)

                if layout == "meld" and back_url is None:
                    time.sleep(scryfall.REQUEST_DELAY)
                    api_call_count += 1
                    back_url = scryfall.fetch_meld_result_url(card)

                multiverse_ids = card.get("multiverse_ids") or []
                mid: Optional[int] = multiverse_ids[0] if multiverse_ids else None

                front_path = scryfall.front_cache_path(card_id)
                back_path  = scryfall.back_cache_path(card_id) if back_url else None

                info = {
                    "card_id":       card_id,
                    "layout":        layout,
                    "front_url":     front_url,
                    "back_url":      back_url,
                    "front_path":    str(front_path),
                    "back_path":     str(back_path) if back_path else None,
                    "multiverse_id": mid,
                }
                card_info[name] = info
                scryfall.save_metadata_entry(cache_key, info, metadata_cache)

                for entry in self.entries:
                    if entry.name == name:
                        entry.scryfall_id      = card_id
                        entry.layout           = layout
                        entry.front_image_path = front_path
                        entry.back_image_path  = back_path

            except Exception as exc:
                msg = str(exc)
                card_info[name] = {"error": msg}
                for entry in self.entries:
                    if entry.name == name:
                        entry.error = msg
                self.card_error.emit(name, msg)

        # ---------------------------------------------------------------
        # Phase 2: Download missing images, emit card_ready progressively
        # ---------------------------------------------------------------
        # Cards whose images are already on disk get card_ready right away.
        # Others get it when their download(s) complete.

        download_tasks: list[tuple[str, Path, Optional[int], str, bool]] = []
        # Track which cards are waiting on downloads to know when they're done
        pending_downloads: dict[str, int] = {}  # name → count of outstanding downloads

        for name, info in card_info.items():
            if "error" in info:
                continue

            fp   = Path(info["front_path"])
            bp   = Path(info["back_path"]) if info.get("back_path") else None
            mid  = info.get("multiverse_id")
            bu   = info.get("back_url")

            need_front = not fp.exists()
            need_back  = bp is not None and not bp.exists() and bu

            if not need_front and not need_back:
                # Everything cached — emit immediately
                self.card_ready.emit(name, fp, bp)
                continue

            pending_downloads[name] = (1 if need_front else 0) + (1 if need_back else 0)
            if need_front:
                download_tasks.append((info["front_url"], fp, mid, name, False))
            if need_back:
                download_tasks.append((bu, bp, None, name, True))

        img_total = len(download_tasks)
        img_done  = 0

        # Per-card state for progressive card_ready emission
        download_results: dict[str, dict] = {
            name: {
                "fp": Path(card_info[name]["front_path"]),
                "bp": Path(card_info[name]["back_path"]) if card_info[name].get("back_path") else None,
                "failed": False,
            }
            for name in pending_downloads
        }

        with ThreadPoolExecutor(max_workers=5) as pool:
            future_map = {
                pool.submit(scryfall.download_image, url, dest, mid): (name, is_back)
                for url, dest, mid, name, is_back in download_tasks
            }
            for future in as_completed(future_map):
                if self._stop:
                    pool.shutdown(wait=False, cancel_futures=True)
                    self.finished.emit()
                    return

                img_done += 1
                self.progress.emit(meta_total + img_done, meta_total * 2 + img_total)

                name, is_back = future_map[future]
                try:
                    future.result()
                except Exception as exc:
                    download_results[name]["failed"] = True
                    self.card_error.emit(name, f"Image download failed: {exc}")

                pending_downloads[name] -= 1
                if pending_downloads[name] == 0:
                    # All downloads for this card are done
                    res = download_results[name]
                    fp  = res["fp"]
                    bp  = res["bp"]
                    if not res["failed"] and fp.exists():
                        self.card_ready.emit(name, fp, bp)

        total = meta_total * 2 + img_total
        self.progress.emit(total, total)
        self.finished.emit()
