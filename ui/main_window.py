"""
MainWindow — top-level application window.

Layout:
  QSplitter (horizontal)
    ├── DecklistPanel  (left, ~280 px)
    ├── CardGrid       (centre, expands)
    └── SettingsPanel  (right, fixed ~240 px)

Status bar: QProgressBar + status text.
Menu bar:   File (Open, Save PDF, Clear Cache, Quit), Edit (system cut/copy/paste).
"""

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QProgressBar, QFileDialog,
    QMessageBox, QStatusBar, QLabel,
)
from PySide6.QtGui import QAction, QKeySequence

from core import decklist_parser, scryfall
from core.decklist_parser import CardEntry, PrintSettings
from ui.decklist_panel import DecklistPanel
from ui.card_grid import CardGrid
from ui.settings_panel import SettingsPanel
from workers.fetch_worker import FetchWorker
from workers.pdf_worker import PDFWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ProxyMakerPro")
        self.resize(1100, 720)

        self._entries: list[CardEntry] = []
        self._fetch_worker: Optional[FetchWorker] = None
        self._pdf_worker:   Optional[PDFWorker]   = None

        self._build_ui()
        self._build_menu()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        self._deck_panel = DecklistPanel()
        self._deck_panel.setMinimumWidth(260)
        self._deck_panel.setMaximumWidth(380)
        self._deck_panel.fetch_requested.connect(self._on_fetch_requested)

        self._card_grid = CardGrid()

        self._settings_panel = SettingsPanel()
        self._settings_panel.generate_requested.connect(self._on_generate_requested)
        self._settings_panel.dfc_mode_changed.connect(self._card_grid.set_dfc_mode)

        splitter.addWidget(self._deck_panel)
        splitter.addWidget(self._card_grid)
        splitter.addWidget(self._settings_panel)
        splitter.setStretchFactor(1, 1)   # card grid takes all extra space

        self.setCentralWidget(splitter)

        # Status bar
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        self._status_label = QLabel("Ready")
        status_bar.addWidget(self._status_label, 1)

        self._progress = QProgressBar()
        self._progress.setFixedWidth(200)
        self._progress.setRange(0, 100)
        self._progress.hide()
        status_bar.addPermanentWidget(self._progress)

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()

        # ── File ──
        file_menu = menu_bar.addMenu("File")

        open_act = QAction("Open Decklist…", self)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        open_act.triggered.connect(self._on_open_decklist)
        file_menu.addAction(open_act)

        file_menu.addSeparator()

        save_act = QAction("Save PDF…", self)
        save_act.setShortcut(QKeySequence.StandardKey.Save)
        save_act.triggered.connect(self._on_save_pdf)
        file_menu.addAction(save_act)

        file_menu.addSeparator()

        cache_act = QAction("Clear Image Cache…", self)
        cache_act.triggered.connect(self._on_clear_cache)
        file_menu.addAction(cache_act)

        file_menu.addSeparator()

        quit_act = QAction("Quit", self)
        quit_act.setShortcut(QKeySequence.StandardKey.Quit)
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

        # ── Edit — Qt wires Cut/Copy/Paste/Select All automatically on macOS ──
        edit_menu = menu_bar.addMenu("Edit")
        for item in [
            (QKeySequence.StandardKey.Undo,      "Undo"),
            (QKeySequence.StandardKey.Redo,      "Redo"),
            None,
            (QKeySequence.StandardKey.Cut,       "Cut"),
            (QKeySequence.StandardKey.Copy,      "Copy"),
            (QKeySequence.StandardKey.Paste,     "Paste"),
            (QKeySequence.StandardKey.SelectAll, "Select All"),
        ]:
            if item is None:
                edit_menu.addSeparator()
                continue
            key, text = item
            act = QAction(text, self)
            act.setShortcut(key)
            edit_menu.addAction(act)

    # ------------------------------------------------------------------
    # Slots — fetch flow
    # ------------------------------------------------------------------

    @Slot(str)
    def _on_fetch_requested(self, text: str) -> None:
        # Cancel any running fetch
        if self._fetch_worker and self._fetch_worker.isRunning():
            self._fetch_worker.stop()
            self._fetch_worker.wait()

        self._entries = decklist_parser.parse(text)
        if not self._entries:
            QMessageBox.warning(self, "No cards found",
                                "Could not parse any cards from the decklist.")
            return

        self._card_grid.populate(self._entries)
        self._settings_panel.set_generate_enabled(False)
        self._deck_panel.set_fetching(True)
        self._progress.show()
        self._progress.setValue(0)
        self._set_status(f"Fetching {len(set(e.name for e in self._entries))} unique cards…")

        self._fetch_worker = FetchWorker(self._entries, parent=self)
        self._fetch_worker.progress.connect(self._on_fetch_progress)
        self._fetch_worker.card_ready.connect(self._card_grid.update_card)
        self._fetch_worker.card_error.connect(self._card_grid.set_card_error)
        self._fetch_worker.finished.connect(self._on_fetch_finished)
        self._fetch_worker.start()

    @Slot(int, int)
    def _on_fetch_progress(self, current: int, total: int) -> None:
        if total > 0:
            self._progress.setValue(int(current * 100 / total))

    @Slot()
    def _on_fetch_finished(self) -> None:
        self._deck_panel.set_fetching(False)
        self._progress.hide()
        self._settings_panel.set_generate_enabled(True)

        errors = [e for e in self._entries if e.error]
        ok     = [e for e in self._entries if not e.error]
        msg = f"Done — {len(ok)} card(s) fetched"
        if errors:
            msg += f", {len(errors)} error(s)"
        self._set_status(msg)

    # ------------------------------------------------------------------
    # Slots — PDF flow
    # ------------------------------------------------------------------

    @Slot(object)
    def _on_generate_requested(self, settings: object) -> None:
        self._start_pdf(settings)

    def _on_save_pdf(self) -> None:
        if not self._entries:
            QMessageBox.information(self, "No cards", "Fetch cards before saving a PDF.")
            return
        self._start_pdf(self._settings_panel.current_settings())

    def _start_pdf(self, settings: PrintSettings) -> None:
        if self._pdf_worker and self._pdf_worker.isRunning():
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF", str(Path.home() / "proxies.pdf"),
            "PDF Files (*.pdf)"
        )
        if not output_path:
            return
        if not output_path.lower().endswith(".pdf"):
            output_path += ".pdf"

        self._settings_panel.set_generating(True)
        self._set_status("Generating PDF…")
        self._progress.show()
        self._progress.setValue(50)

        self._pdf_worker = PDFWorker(
            self._entries, settings, output_path,
            open_after=True, parent=self
        )
        self._pdf_worker.finished.connect(self._on_pdf_finished)
        self._pdf_worker.error.connect(self._on_pdf_error)
        self._pdf_worker.start()

    @Slot(str)
    def _on_pdf_finished(self, path: str) -> None:
        self._settings_panel.set_generating(False)
        self._progress.hide()
        self._set_status(f"PDF saved: {os.path.basename(path)}")

    @Slot(str)
    def _on_pdf_error(self, message: str) -> None:
        self._settings_panel.set_generating(False)
        self._progress.hide()
        self._set_status("PDF generation failed")
        QMessageBox.critical(self, "PDF Error", message)

    # ------------------------------------------------------------------
    # Slots — File menu helpers
    # ------------------------------------------------------------------

    def _on_open_decklist(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Decklist", str(Path.home()),
            "Text Files (*.txt);;All Files (*)"
        )
        if path:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
            self._deck_panel.set_text(text)

    def _on_clear_cache(self) -> None:
        reply = QMessageBox.question(
            self, "Clear Cache",
            "Delete all cached card images?\nThey will be re-downloaded next time.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            count = scryfall.clear_cache()
            self._set_status(f"Cache cleared — {count} image(s) removed")

    # ------------------------------------------------------------------

    def _set_status(self, text: str) -> None:
        self._status_label.setText(text)

    def closeEvent(self, event):
        # Cleanly stop any running workers before quitting
        for w in (self._fetch_worker, self._pdf_worker):
            if w and w.isRunning():
                if hasattr(w, "stop"):
                    w.stop()
                w.wait(2000)
        event.accept()
