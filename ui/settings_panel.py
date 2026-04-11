"""
SettingsPanel — right-side dock panel with print settings and the Generate PDF button.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QCheckBox, QRadioButton, QButtonGroup,
    QPushButton, QGroupBox, QSizePolicy, QSpacerItem,
)

from core.decklist_parser import PrintSettings


class SettingsPanel(QWidget):
    generate_requested = Signal(object)  # carries a PrintSettings instance
    dfc_mode_changed   = Signal(str)     # emitted immediately when DFC selection changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(220)
        self.setMaximumWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        header = QLabel("Print Settings")
        font = header.font()
        font.setPointSize(13)
        font.setBold(True)
        header.setFont(font)
        layout.addWidget(header)

        # ── Page size ──────────────────────────────────────────────────
        page_box = QGroupBox("Page Size")
        pb_layout = QVBoxLayout(page_box)
        self._page_combo = QComboBox()
        self._page_combo.addItem("US Letter (8.5\" × 11\")", "letter")
        self._page_combo.addItem("A4 (210 mm × 297 mm)",     "a4")
        pb_layout.addWidget(self._page_combo)
        layout.addWidget(page_box)

        # ── DFC mode ───────────────────────────────────────────────────
        dfc_box = QGroupBox("Double-Faced Cards")
        dfc_layout = QVBoxLayout(dfc_box)

        self._dfc_group = QButtonGroup(self)
        self._rb_front  = QRadioButton("Front face only")
        self._rb_both   = QRadioButton("Both faces (separate slots)")
        self._rb_compact = QRadioButton("Compact — both stacked")
        self._rb_front.setChecked(True)

        for rb in (self._rb_front, self._rb_both, self._rb_compact):
            self._dfc_group.addButton(rb)
            dfc_layout.addWidget(rb)

        self._compact_warn = QLabel(
            "⚠ Card text shrinks to ~5 pt.\n"
            "'Both faces' is more readable."
        )
        self._compact_warn.setStyleSheet("color: #b85c00; font-size: 11px;")
        self._compact_warn.setWordWrap(True)
        self._compact_warn.hide()
        dfc_layout.addWidget(self._compact_warn)

        self._dfc_group.buttonToggled.connect(self._on_dfc_changed)
        layout.addWidget(dfc_box)

        # ── Options ────────────────────────────────────────────────────
        opt_box = QGroupBox("Options")
        opt_layout = QVBoxLayout(opt_box)

        self._chk_cut_lines = QCheckBox("Include cut lines")
        self._chk_cut_lines.setChecked(True)
        opt_layout.addWidget(self._chk_cut_lines)

        self._chk_sideboard = QCheckBox("Include sideboard")
        self._chk_sideboard.setChecked(True)
        opt_layout.addWidget(self._chk_sideboard)

        layout.addWidget(opt_box)

        # ── Spacer ─────────────────────────────────────────────────────
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum,
                                       QSizePolicy.Policy.Expanding))

        # ── Generate button ────────────────────────────────────────────
        self._gen_btn = QPushButton("Generate PDF…")
        self._gen_btn.setEnabled(False)
        self._gen_btn.clicked.connect(self._on_generate_clicked)
        layout.addWidget(self._gen_btn)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_generate_enabled(self, enabled: bool) -> None:
        self._gen_btn.setEnabled(enabled)

    def set_generating(self, generating: bool) -> None:
        self._gen_btn.setEnabled(not generating)
        self._gen_btn.setText("Generating…" if generating else "Generate PDF…")

    def current_settings(self) -> PrintSettings:
        page = self._page_combo.currentData()

        # Use checkedButton() — more reliable than isChecked() per-button
        # when buttons belong to a QButtonGroup.
        checked = self._dfc_group.checkedButton()
        if checked is self._rb_compact:
            dfc_mode = "compact_stacked"
        elif checked is self._rb_both:
            dfc_mode = "both_separate"
        else:
            dfc_mode = "front_only"

        return PrintSettings(
            page_size=page,
            dfc_mode=dfc_mode,
            cut_lines=self._chk_cut_lines.isChecked(),
            include_sideboard=self._chk_sideboard.isChecked(),
        )

    # ------------------------------------------------------------------

    def _on_dfc_changed(self, button, checked: bool) -> None:
        if not checked:
            return  # Only act on the newly selected button
        self._compact_warn.setVisible(button is self._rb_compact)
        self.dfc_mode_changed.emit(self.current_settings().dfc_mode)

    def _on_generate_clicked(self) -> None:
        self.generate_requested.emit(self.current_settings())
