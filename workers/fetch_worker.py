"""
FetchWorker — QThread that fetches Scryfall metadata then downloads card images.

Phase 1 (sequential): /cards/named API calls, 600 ms apart.
Phase 2 (concurrent): image CDN downloads via ThreadPoolExecutor(max_workers=5).

Signals:
  progress(current: int, total: int)  — use for progress bar
  card_ready(name: str, front_path: object, back_path: object)  — image on disk
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
    progress   = Signal(int, int)       # current, total
    card_ready = Signal(str, object, object)  # name, front_path, back_path|None
    card_error = Signal(str, str)       # name, message
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

        # Deduplicate by name, preserving insertion order.
        # Keep the first entry for each name so we can forward its
        # set_code / collector_number to the Scryfall lookup.
        name_to_rep: dict[str, CardEntry] = {}
        for e in self.entries:
            if e.name not in name_to_rep:
                name_to_rep[e.name] = e
        unique_names = list(name_to_rep.keys())

        # ---------------------------------------------------------------
        # Phase 1: Fetch metadata sequentially
        # ---------------------------------------------------------------
        # card_info maps name → dict with all we need for phase 2
        card_info: dict[str, dict] = {}

        meta_total = len(unique_names)

        for i, name in enumerate(unique_names):
            if self._stop:
                self.finished.emit()
                return

            self.progress.emit(i, meta_total * 2)

            rep = name_to_rep[name]
            try:
                card = scryfall.fetch_card_metadata(
                    name,
                    set_code=rep.set_code,
                    collector_number=rep.collector_number,
                )
                layout = card.get("layout", "normal")
                card_id = card["id"]

                front_url, back_url = scryfall.get_image_urls(card)

                # Meld: back face is a separate card object
                if layout == "meld" and back_url is None:
                    time.sleep(scryfall.REQUEST_DELAY)
                    back_url = scryfall.fetch_meld_result_url(card)

                multiverse_ids = card.get("multiverse_ids") or []
                mid: Optional[int] = multiverse_ids[0] if multiverse_ids else None

                front_path = scryfall.front_cache_path(card_id)
                back_path  = scryfall.back_cache_path(card_id) if back_url else None

                card_info[name] = {
                    "card_id":       card_id,
                    "layout":        layout,
                    "front_url":     front_url,
                    "back_url":      back_url,
                    "front_path":    front_path,
                    "back_path":     back_path,
                    "multiverse_id": mid,
                }

                # Update every CardEntry for this name
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

            # Respect Scryfall's heavy-endpoint rate limit
            if i < meta_total - 1:
                time.sleep(scryfall.REQUEST_DELAY)

        # ---------------------------------------------------------------
        # Phase 2: Download images concurrently
        # ---------------------------------------------------------------
        # Build list of (url, dest_path, multiverse_id, card_name, is_back)
        download_tasks: list[tuple[str, Path, Optional[int], str, bool]] = []

        for name, info in card_info.items():
            if "error" in info:
                continue
            fp: Path = info["front_path"]
            bp: Optional[Path] = info["back_path"]
            mid = info["multiverse_id"]

            if not fp.exists():
                download_tasks.append((info["front_url"], fp, mid, name, False))
            if bp and not bp.exists() and info["back_url"]:
                download_tasks.append((info["back_url"], bp, None, name, True))

        img_total = len(download_tasks)
        img_done  = 0

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
                    self.card_error.emit(name, f"Image download failed: {exc}")

        # ---------------------------------------------------------------
        # Emit card_ready for every successfully fetched card
        # ---------------------------------------------------------------
        for name, info in card_info.items():
            if "error" in info:
                continue
            fp: Path = info["front_path"]
            bp: Optional[Path] = info["back_path"]
            if fp.exists():
                self.card_ready.emit(name, fp, bp)
            else:
                self.card_error.emit(name, "Front image missing after download")

        total = meta_total * 2 + img_total
        self.progress.emit(total, total)
        self.finished.emit()
