"""
DecklistPanel — left panel containing the deck input text area and Fetch button.
"""

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPlainTextEdit, QPushButton
)

_PLACEHOLDER = """\
Paste an MTG Arena, MTGGoldfish, or MTGO decklist here.

Example (Arena format):
Deck
4 Lightning Bolt (M21) 150
2 Delver of Secrets // Insectile Aberration (ISD) 51

Sideboard
3 Grafdigger's Cage (M20) 227
"""


class DecklistPanel(QWidget):
    fetch_requested = Signal(str)   # emits the raw decklist text

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QLabel("Decklist")
        font = header.font()
        font.setPointSize(13)
        font.setBold(True)
        header.setFont(font)
        layout.addWidget(header)

        self._text_edit = QPlainTextEdit()
        self._text_edit.setPlaceholderText(_PLACEHOLDER)
        mono = QFont("Menlo")
        if not mono.exactMatch():
            mono = QFont("Courier New")
        mono.setPointSize(12)
        self._text_edit.setFont(mono)
        layout.addWidget(self._text_edit, stretch=1)

        self._fetch_btn = QPushButton("Fetch Cards")
        self._fetch_btn.setDefault(True)
        self._fetch_btn.clicked.connect(self._on_fetch_clicked)
        layout.addWidget(self._fetch_btn)

    # ------------------------------------------------------------------

    def set_fetching(self, fetching: bool) -> None:
        self._fetch_btn.setEnabled(not fetching)
        self._fetch_btn.setText("Fetching…" if fetching else "Fetch Cards")

    def get_text(self) -> str:
        return self._text_edit.toPlainText()

    def set_text(self, text: str) -> None:
        self._text_edit.setPlainText(text)

    # ------------------------------------------------------------------

    def _on_fetch_clicked(self) -> None:
        text = self._text_edit.toPlainText().strip()
        if text:
            self.fetch_requested.emit(text)
