"""
CardThumbnailWidget — displays a single deck entry as a card image thumbnail.

States:
  placeholder  – shown immediately after parse, before images arrive
  loaded       – card image(s) downloaded and displayed
  error        – Scryfall lookup or download failed

The widget is 160 × 245 px:
  • 150 × 210 px image area  (matches the 2.5:3.5 card ratio)
  •  10 px padding around image
  •  25 px name/count strip below image
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QTransform
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

from core.decklist_parser import CardEntry

_THUMB_W = 150
_THUMB_H = 210  # 150 × 1.4  (card aspect ratio)
_WIDGET_W = _THUMB_W + 10
_WIDGET_H = _THUMB_H + 35


class CardThumbnailWidget(QFrame):
    def __init__(self, entry: CardEntry, parent=None):
        super().__init__(parent)
        self.entry      = entry
        self.front_path: Optional[Path] = None
        self.back_path:  Optional[Path] = None
        self._dfc_mode: str = "front_only"

        self.setFixedSize(_WIDGET_W, _WIDGET_H)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # Image area
        self._img_label = QLabel()
        self._img_label.setFixedSize(_THUMB_W, _THUMB_H)
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setStyleSheet(
            "background: #e8e8e8; border-radius: 4px; color: #555;"
        )
        self._img_label.setText(self._short_name())
        self._img_label.setWordWrap(True)
        layout.addWidget(self._img_label)

        # Name / count strip
        self._info_label = QLabel()
        self._info_label.setFixedWidth(_THUMB_W)
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(9)
        self._info_label.setFont(font)
        self._refresh_info_label()
        layout.addWidget(self._info_label)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_loaded(
        self,
        front_path: Path,
        back_path: Optional[Path],
        dfc_mode: str = "front_only",
    ) -> None:
        self.front_path = front_path
        self.back_path  = back_path
        self._dfc_mode  = dfc_mode
        self.entry.front_image_path = front_path
        self.entry.back_image_path  = back_path
        self._render()
        self._refresh_info_label()

    def refresh_display(self, dfc_mode: str) -> None:
        """Re-render with a new DFC mode; no-op if images haven't loaded yet."""
        if self.front_path is None:
            return
        self._dfc_mode = dfc_mode
        self._render()

    # ------------------------------------------------------------------
    # Internal rendering
    # ------------------------------------------------------------------

    def _render(self) -> None:
        is_dfc = self.back_path and self.back_path.exists()

        if is_dfc and self._dfc_mode == "compact_stacked":
            pixmap = self._composite(self.front_path, self.back_path, rotated=True)
        elif is_dfc and self._dfc_mode == "both_separate":
            pixmap = self._composite(self.front_path, self.back_path, rotated=False)
        else:
            pixmap = QPixmap(str(self.front_path))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    _THUMB_W, _THUMB_H,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

        if not pixmap.isNull():
            self._img_label.setPixmap(pixmap)
            self._img_label.setStyleSheet("background: white; border-radius: 4px;")
        else:
            self._img_label.setText("(could not load image)")

    def _composite(
        self, front_path: Path, back_path: Path, rotated: bool
    ) -> QPixmap:
        """
        Stack front (top) and back (bottom) into a single _THUMB_W × _THUMB_H pixmap.
        rotated=True  → each face is rotated 90° CW first (compact mode).
        rotated=False → faces are shown in portrait (both_separate mode).
        """
        half_h = _THUMB_H // 2
        result = QPixmap(_THUMB_W, _THUMB_H)
        result.fill(QColor(255, 255, 255))

        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rotate_cw = QTransform().rotate(90) if rotated else None

        for i, path in enumerate((front_path, back_path)):
            src = QPixmap(str(path))
            if src.isNull():
                continue
            if rotate_cw is not None:
                src = src.transformed(rotate_cw, Qt.TransformationMode.SmoothTransformation)
            scaled = src.scaled(
                _THUMB_W, half_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            dest_x = (_THUMB_W - scaled.width()) // 2
            dest_y = i * half_h + (half_h - scaled.height()) // 2
            painter.drawPixmap(dest_x, dest_y, scaled)

        painter.setPen(QColor(160, 160, 160))
        painter.drawLine(0, half_h, _THUMB_W, half_h)
        painter.end()
        return result

    def set_error(self, message: str) -> None:
        self.entry.error = message
        # Truncate long errors so the widget stays a fixed size
        short_msg = message if len(message) <= 60 else message[:57] + "…"
        self._img_label.setPixmap(QPixmap())  # clear any previous image
        self._img_label.setText(f"⚠ {short_msg}")
        self._img_label.setStyleSheet(
            "background: #ffe5e5; border: 2px solid #cc3333;"
            "border-radius: 4px; color: #cc3333; padding: 4px;"
        )
        self._img_label.setWordWrap(True)
        self._refresh_info_label()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _short_name(self) -> str:
        n = self.entry.name
        return (n[:22] + "…") if len(n) > 22 else n

    def _refresh_info_label(self) -> None:
        dfc  = " [DFC]" if self.back_path else ""
        sb   = " [SB]"  if self.entry.is_sideboard else ""
        err  = " ✗"     if self.entry.error else ""
        text = f"{self.entry.count}× {self._short_name()}{dfc}{sb}{err}"
        self._info_label.setText(text)
        self._info_label.setToolTip(self.entry.name)
