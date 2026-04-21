"""
FetchWorker — QThread that fetches Scryfall metadata then downloads card images.

Deduplication is by slot_key = (name, set_code, collector_number), so multiple
different printings of the same card name are each fetched independently.

Phase 1 (sequential): resolve metadata for each unique slot_key.
  - Metadata (card ID, layout, image URLs) is cached to disk; cached slots
    skip the API call entirely and cost no delay.
  - Only slots not in the metadata cache hit the Scryfall endpoint,
    with a 600 ms inter-request delay to respect the rate limit.

Phase 2 (concurrent): download any missing images (up to 5 threads).
  - Already-cached images are skipped immediately.
  - card_ready is emitted per slot_key as soon as its images land on disk,
    so thumbnails populate progressively rather than all at once.

Signals:
  progress(current: int, total: int)
  card_ready(slot_key: str, front_path: object, back_path: object)
  card_error(slot_key: str, message: str)
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
    card_ready = Signal(str, object, object) # slot_key, front_path, back_path|None
    card_error = Signal(str, str)            # slot_key, message
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

        # Deduplicate by slot_key so each unique (name, set, collector_number)
        # combo is fetched independently, enabling different art per printing.
        slot_to_rep: dict[str, CardEntry] = {}
        for e in self.entries:
            if e.slot_key not in slot_to_rep:
                slot_to_rep[e.slot_key] = e
        slot_keys = list(slot_to_rep.keys())

        meta_total = len(slot_keys)
        metadata_cache = scryfall.load_metadata_cache()

        # ---------------------------------------------------------------
        # Phase 1: Resolve metadata (cache-first, then API)
        # ---------------------------------------------------------------
        card_info: dict[str, dict] = {}  # slot_key → info dict
        api_call_count = 0

        for i, slot_key in enumerate(slot_keys):
            if self._stop:
                self.finished.emit()
                return

            self.progress.emit(i, meta_total * 2)

            rep = slot_to_rep[slot_key]

            if slot_key in metadata_cache:
                # Fast path — no network call needed
                info = metadata_cache[slot_key]
                card_info[slot_key] = info
                for entry in self.entries:
                    if entry.slot_key == slot_key:
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
                    rep.name,
                    set_code=rep.set_code,
                    collector_number=rep.collector_number,
                )
                layout  = card.get("layout", "normal")
                card_id = card["id"]

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
                card_info[slot_key] = info
                scryfall.save_metadata_entry(slot_key, info, metadata_cache)

                for entry in self.entries:
                    if entry.slot_key == slot_key:
                        entry.scryfall_id      = card_id
                        entry.layout           = layout
                        entry.front_image_path = front_path
                        entry.back_image_path  = back_path

            except Exception as exc:
                msg = str(exc)
                card_info[slot_key] = {"error": msg}
                for entry in self.entries:
                    if entry.slot_key == slot_key:
                        entry.error = msg
                self.card_error.emit(slot_key, msg)

        # ---------------------------------------------------------------
        # Phase 2: Download missing images, emit card_ready progressively
        # ---------------------------------------------------------------
        download_tasks: list[tuple[str, Path, Optional[int], str, bool]] = []
        pending_downloads: dict[str, int] = {}  # slot_key → outstanding count

        for slot_key, info in card_info.items():
            if "error" in info:
                continue

            fp  = Path(info["front_path"])
            bp  = Path(info["back_path"]) if info.get("back_path") else None
            mid = info.get("multiverse_id")
            bu  = info.get("back_url")

            need_front = not fp.exists()
            need_back  = bp is not None and not bp.exists() and bu

            if not need_front and not need_back:
                self.card_ready.emit(slot_key, fp, bp)
                continue

            pending_downloads[slot_key] = (1 if need_front else 0) + (1 if need_back else 0)
            if need_front:
                download_tasks.append((info["front_url"], fp, mid, slot_key, False))
            if need_back:
                download_tasks.append((bu, bp, None, slot_key, True))

        img_total = len(download_tasks)
        img_done  = 0

        download_results: dict[str, dict] = {
            sk: {
                "fp":     Path(card_info[sk]["front_path"]),
                "bp":     Path(card_info[sk]["back_path"]) if card_info[sk].get("back_path") else None,
                "failed": False,
            }
            for sk in pending_downloads
        }

        with ThreadPoolExecutor(max_workers=5) as pool:
            future_map = {
                pool.submit(scryfall.download_image, url, dest, mid): (slot_key, is_back)
                for url, dest, mid, slot_key, is_back in download_tasks
            }
            for future in as_completed(future_map):
                if self._stop:
                    pool.shutdown(wait=False, cancel_futures=True)
                    self.finished.emit()
                    return

                img_done += 1
                self.progress.emit(meta_total + img_done, meta_total * 2 + img_total)

                slot_key, is_back = future_map[future]
                try:
                    future.result()
                except Exception as exc:
                    download_results[slot_key]["failed"] = True
                    self.card_error.emit(slot_key, f"Image download failed: {exc}")

                pending_downloads[slot_key] -= 1
                if pending_downloads[slot_key] == 0:
                    res = download_results[slot_key]
                    fp  = res["fp"]
                    bp  = res["bp"]
                    if not res["failed"] and fp.exists():
                        self.card_ready.emit(slot_key, fp, bp)

        total = meta_total * 2 + img_total
        self.progress.emit(total, total)
        self.finished.emit()
