"""
PDFWorker — QThread that calls pdf_generator.generate() in the background
so the UI remains responsive during PDF assembly.

Signals:
  finished(output_path: str)   — PDF written successfully
  error(message: str)          — generation failed
"""

import subprocess

from PySide6.QtCore import QThread, Signal

from core.decklist_parser import CardEntry, PrintSettings
from core import pdf_generator


class PDFWorker(QThread):
    finished = Signal(str)   # output_path
    error    = Signal(str)   # error message

    def __init__(
        self,
        entries: list[CardEntry],
        settings: PrintSettings,
        output_path: str,
        open_after: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.entries     = entries
        self.settings    = settings
        self.output_path = output_path
        self.open_after  = open_after

    def run(self) -> None:
        try:
            pdf_generator.generate(self.entries, self.settings, self.output_path)
        except Exception as exc:
            self.error.emit(str(exc))
            return

        if self.open_after:
            subprocess.run(["open", self.output_path], check=False)

        self.finished.emit(self.output_path)
