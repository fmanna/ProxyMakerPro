"""
PDF generation for MTG card proxies.

Card dimensions: 2.5" × 3.5"  =  180 pt × 252 pt  (at 72 pt/inch)

US Letter layout (8.5" × 11" = 612 × 792 pt) — perfect fit, zero vertical gap:
  Left/right margin : 18 pt (0.25")
  Columns           : 3 × 180 pt = 540 pt, with 18 pt gaps  → 18 | 180 | 18 | 180 | 18 | 180 | 18
  Top/bottom margin : 18 pt (0.25")
  Rows              : 3 × 252 pt = 756 pt, no vertical gap   → 18 | 252 | 252 | 252 | 18
  Cards per page    : 9

A4 layout (210 mm × 297 mm = 595.28 × 841.89 pt) — cards centred, no inter-card gaps:
  Horizontal margin : (595.28 − 540) / 2 ≈ 27.64 pt
  Vertical margin   : (841.89 − 756) / 2 ≈ 42.95 pt
  Cards per page    : 9

DFC modes:
  front_only      – only the front face is printed (one slot per card)
  both_separate   – front and back printed as consecutive separate slots
  compact_stacked – both faces stacked in one slot (top half = front, bottom = back)
"""

from pathlib import Path
from typing import Optional

from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from core.decklist_parser import CardEntry, PrintSettings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CARD_W: float = 2.5 * 72   # 180.0 pt
CARD_H: float = 3.5 * 72   # 252.0 pt

COLS = 3
ROWS = 3
CARDS_PER_PAGE = COLS * ROWS


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def _layout(settings: PrintSettings) -> dict:
    """Return page geometry as a dict of floats (all in points)."""
    if settings.page_size == "a4":
        page_w, page_h = 595.28, 841.89
        left   = (page_w - COLS * CARD_W) / 2   # ≈ 27.64 pt
        bottom = (page_h - ROWS * CARD_H) / 2   # ≈ 42.95 pt
        h_gap  = 0.0
        v_gap  = 0.0
    else:  # letter
        page_w, page_h = 612.0, 792.0
        left   = 18.0
        bottom = 18.0
        h_gap  = 18.0   # gap between columns
        v_gap  = 0.0    # no gap needed vertically

    return dict(page_w=page_w, page_h=page_h,
                left=left, bottom=bottom,
                h_gap=h_gap, v_gap=v_gap)


def _card_xy(slot_index: int, geo: dict) -> tuple[float, float]:
    """
    Return the bottom-left (x, y) corner for a card at slot_index on the page.
    Slots fill left→right, top→bottom.
    Reportlab y=0 is at the page bottom.
    """
    col           = slot_index % COLS
    row_from_top  = slot_index // COLS
    row_from_bot  = ROWS - 1 - row_from_top
    x = geo["left"]   + col          * (CARD_W + geo["h_gap"])
    y = geo["bottom"] + row_from_bot * (CARD_H + geo["v_gap"])
    return x, y


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def _draw_image(
    c: canvas.Canvas,
    path: Optional[Path],
    x: float, y: float,
    w: float, h: float,
) -> None:
    """Draw a card image. Draws a gray placeholder if path is missing."""
    if path and path.exists():
        try:
            reader = ImageReader(str(path))
            c.drawImage(reader, x, y, w, h,
                        preserveAspectRatio=True, mask="auto")
            return
        except Exception:
            pass
    # Placeholder
    c.saveState()
    c.setFillColorRGB(0.88, 0.88, 0.88)
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.setFont("Helvetica", 8)
    label = "Image not found"
    c.drawCentredString(x + w / 2, y + h / 2 - 4, label)
    c.restoreState()


def _draw_cut_lines(
    c: canvas.Canvas,
    x: float, y: float,
    w: float = CARD_W, h: float = CARD_H,
) -> None:
    c.saveState()
    c.setStrokeColorRGB(0.55, 0.55, 0.55)
    c.setLineWidth(0.5)
    c.setDash(3, 3)
    c.rect(x, y, w, h, fill=0, stroke=1)
    c.restoreState()


def _draw_rotated_image(
    c: canvas.Canvas,
    path: Optional[Path],
    x: float, y: float,
    w: float, h: float,
    clockwise: bool,
) -> None:
    """
    Draw a card image rotated 90° into a w×h rectangle whose bottom-left is (x, y).

    The image's natural orientation is portrait (CARD_W × CARD_H).
    After a 90° rotation it occupies a landscape slot of width h and height w
    (i.e. the w/h args here are the slot dimensions, not the image dimensions).

    clockwise=True  : front face in top slot  — rotate -90° (CW)
    clockwise=False : back face in bottom slot — rotate +90° (CCW)

    Dead // Gone layout reference:
      Top half:    front face rotated 90° CW  → top of card points right
      Bottom half: back face rotated 90° CCW  → top of card points left
      When the physical card is flipped 180° the back face reads upright.
    """
    if path and path.exists():
        try:
            reader = ImageReader(str(path))
        except Exception:
            reader = None
    else:
        reader = None

    c.saveState()
    if clockwise:
        # Rotate -90° around the top-left corner of the slot.
        # After rotation, draw the image in the transformed space.
        # translate to top-left of slot (x, y+h), then rotate -90°
        c.translate(x, y + h)
        c.rotate(-90)
        # Now the slot maps to (0,0,h,w) in the rotated space
        draw_x, draw_y, draw_w, draw_h = 0, 0, h, w
    else:
        # Rotate +90° around the bottom-right corner of the slot.
        c.translate(x + w, y)
        c.rotate(90)
        draw_x, draw_y, draw_w, draw_h = 0, 0, h, w

    if reader is not None:
        try:
            c.drawImage(reader, draw_x, draw_y, draw_w, draw_h,
                        preserveAspectRatio=True, mask="auto")
            c.restoreState()
            return
        except Exception:
            pass

    # Placeholder
    c.setFillColorRGB(0.88, 0.88, 0.88)
    c.rect(draw_x, draw_y, draw_w, draw_h, fill=1, stroke=0)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.setFont("Helvetica", 8)
    c.drawCentredString(draw_x + draw_w / 2, draw_y + draw_h / 2 - 4, "Image not found")
    c.restoreState()


def _draw_compact_divider(
    c: canvas.Canvas,
    x: float, y: float,
    w: float = CARD_W,
) -> None:
    """Draw the horizontal divider between the two faces in compact mode."""
    mid_y = y + CARD_H / 2
    c.saveState()
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.setLineWidth(0.75)
    c.setDash(4, 2)
    c.line(x, mid_y, x + w, mid_y)
    c.restoreState()


# ---------------------------------------------------------------------------
# Render list construction
# ---------------------------------------------------------------------------

def _build_render_list(
    entries: list[CardEntry],
    settings: PrintSettings,
) -> list[tuple[str, CardEntry]]:
    """
    Expand the deck entries into a flat render list of (face, entry) tuples.
      face = "front" | "back"

    - front_only      : one "front" per copy
    - compact_stacked : one "front" per copy (back drawn in same slot)
    - both_separate   : one "front" per copy, then one "back" per copy (if DFC)
    """
    render: list[tuple[str, CardEntry]] = []
    for entry in entries:
        if not settings.include_sideboard and entry.is_sideboard:
            continue
        for _ in range(entry.count):
            render.append(("front", entry))
        if settings.dfc_mode == "both_separate" and entry.back_image_path:
            for _ in range(entry.count):
                render.append(("back", entry))
    return render


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate(
    entries: list[CardEntry],
    settings: PrintSettings,
    output_path: str,
) -> None:
    """
    Generate a print-ready PDF at output_path.
    Raises on file I/O errors; individual missing images become gray placeholders.
    """
    geo = _layout(settings)
    render_list = _build_render_list(entries, settings)

    c = canvas.Canvas(output_path, pagesize=(geo["page_w"], geo["page_h"]))

    for abs_idx, (face, entry) in enumerate(render_list):
        slot = abs_idx % CARDS_PER_PAGE

        # Start a new page (not for the very first card)
        if abs_idx > 0 and slot == 0:
            c.showPage()

        x, y = _card_xy(slot, geo)

        if settings.dfc_mode == "compact_stacked" and entry.back_image_path:
            # Front face: top half, rotated 90° CW (Dead // Gone layout)
            _draw_rotated_image(c, entry.front_image_path,
                                x, y + CARD_H / 2, CARD_W, CARD_H / 2,
                                clockwise=True)
            # Back face: bottom half, rotated 90° CCW
            _draw_rotated_image(c, entry.back_image_path,
                                x, y, CARD_W, CARD_H / 2,
                                clockwise=False)
            _draw_compact_divider(c, x, y)
        elif face == "back":
            _draw_image(c, entry.back_image_path, x, y, CARD_W, CARD_H)
        else:
            _draw_image(c, entry.front_image_path, x, y, CARD_W, CARD_H)

        if settings.cut_lines:
            _draw_cut_lines(c, x, y)

    # Save even if render_list is empty (produces a blank page)
    c.save()
