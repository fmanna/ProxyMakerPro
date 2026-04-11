"""
CardGrid — a scrollable 3-column grid of CardThumbnailWidgets.

Maintains a name → [widgets] mapping so that when FetchWorker emits
card_ready(name, front_path, back_path), every thumbnail for that card
name (maindeck and sideboard) is updated simultaneously.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QScrollArea, QGridLayout, QLabel, QSizePolicy
)

from core.decklist_parser import CardEntry
from ui.card_thumbnail import CardThumbnailWidget

_COLS = 3


class CardGrid(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Outer scroll area
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Inner container
        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setSpacing(8)
        self._grid.setContentsMargins(8, 8, 8, 8)
        self._scroll.setWidget(self._container)

        # Empty-state label
        self._empty_label = QLabel(
            "Paste a decklist on the left and click  Fetch Cards."
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color: #888; font-size: 14px;")

        # Root layout (shows either the scroll area or the empty label)
        from PySide6.QtWidgets import QVBoxLayout
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._empty_label)
        root.addWidget(self._scroll)
        self._scroll.hide()

        # name → list of thumbnail widgets
        self._name_map: dict[str, list[CardThumbnailWidget]] = {}
        self._dfc_mode: str = "front_only"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def populate(self, entries: list[CardEntry]) -> None:
        """Replace the current grid contents with placeholder thumbnails."""
        self._clear_grid()
        self._name_map.clear()

        if not entries:
            self._scroll.hide()
            self._empty_label.show()
            return

        self._empty_label.hide()
        self._scroll.show()

        for idx, entry in enumerate(entries):
            widget = CardThumbnailWidget(entry)
            row = idx // _COLS
            col = idx % _COLS
            self._grid.addWidget(widget, row, col, Qt.AlignmentFlag.AlignTop)

            self._name_map.setdefault(entry.name, []).append(widget)

        # Fill remaining cells in the last row with spacers for alignment
        total = len(entries)
        remainder = total % _COLS
        if remainder:
            for col in range(remainder, _COLS):
                spacer = QWidget()
                spacer.setSizePolicy(
                    QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
                )
                self._grid.addWidget(spacer, total // _COLS, col)

    def set_dfc_mode(self, mode: str) -> None:
        """Update the display mode and re-render all loaded thumbnails."""
        self._dfc_mode = mode
        for widgets in self._name_map.values():
            for widget in widgets:
                widget.refresh_display(mode)

    def update_card(
        self, name: str, front_path: object, back_path: object
    ) -> None:
        """Called by FetchWorker.card_ready — update all thumbnails for name."""
        fp = front_path if isinstance(front_path, Path) else Path(str(front_path))
        bp = Path(str(back_path)) if back_path else None

        for widget in self._name_map.get(name, []):
            widget.set_loaded(fp, bp, self._dfc_mode)

    def set_card_error(self, name: str, message: str) -> None:
        """Called by FetchWorker.card_error — mark all thumbnails for name."""
        for widget in self._name_map.get(name, []):
            widget.set_error(message)

    def clear(self) -> None:
        self._clear_grid()
        self._name_map.clear()
        self._scroll.hide()
        self._empty_label.show()

    # ------------------------------------------------------------------

    def _clear_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
