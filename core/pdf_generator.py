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

# Fraction of the Scryfall PNG occupied by the black border on each side.
# Modern cards: ~2 mm border on a 63 mm card ≈ 3.2%; 3.5% gives a safe margin.
BORDER_FRACTION: float = 0.035


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def _layout(settings: PrintSettings, card_w: float, card_h: float) -> dict:
    """
    Return page geometry as a dict of floats (all in points).
    card_w/card_h are the effective slot dimensions — full card size when
    printing borders, art-only size when borders are omitted.
    """
    if settings.page_size == "a4":
        page_w, page_h = 595.28, 841.89
        left   = (page_w - COLS * card_w) / 2
        bottom = (page_h - ROWS * card_h) / 2
        h_gap  = 0.0
        v_gap  = 0.0
    elif settings.print_borders:
        # US Letter bordered: fixed 18 pt margins with 18 pt column gaps
        page_w, page_h = 612.0, 792.0
        left   = 18.0
        bottom = 18.0
        h_gap  = 18.0
        v_gap  = 0.0
    else:
        # US Letter borderless: centre the smaller art grid, no gaps
        page_w, page_h = 612.0, 792.0
        left   = (page_w - COLS * card_w) / 2
        bottom = (page_h - ROWS * card_h) / 2
        h_gap  = 0.0
        v_gap  = 0.0

    return dict(page_w=page_w, page_h=page_h,
                left=left, bottom=bottom,
                h_gap=h_gap, v_gap=v_gap,
                card_w=card_w, card_h=card_h)


def _card_xy(slot_index: int, geo: dict) -> tuple[float, float]:
    """
    Return the bottom-left (x, y) corner for a card at slot_index on the page.
    Slots fill left→right, top→bottom.
    Reportlab y=0 is at the page bottom.
    """
    col           = slot_index % COLS
    row_from_top  = slot_index // COLS
    row_from_bot  = ROWS - 1 - row_from_top
    x = geo["left"]   + col          * (geo["card_w"] + geo["h_gap"])
    y = geo["bottom"] + row_from_bot * (geo["card_h"] + geo["v_gap"])
    return x, y


# ---------------------------------------------------------------------------
# Image reader cache
# ---------------------------------------------------------------------------

def _get_reader(
    path: Optional[Path],
    cache: dict,
) -> Optional[ImageReader]:
    """
    Return a cached ImageReader for path, loading it on first access.
    Using a shared cache across draw calls avoids re-reading the same PNG
    for every copy of a card (e.g. 4× Lightning Bolt → 1 disk read, not 4).
    """
    if not path:
        return None
    key = str(path)
    if key not in cache:
        if path.exists():
            try:
                cache[key] = ImageReader(key)
            except Exception:
                cache[key] = None
        else:
            cache[key] = None
    return cache[key]


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def _draw_image(
    c: canvas.Canvas,
    path: Optional[Path],
    x: float, y: float,
    w: float, h: float,
    _cache: Optional[dict] = None,
) -> None:
    """Draw a card image. Draws a gray placeholder if path is missing."""
    reader = _get_reader(path, _cache if _cache is not None else {})
    if reader is not None:
        try:
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
    c.drawCentredString(x + w / 2, y + h / 2 - 4, "Image not found")
    c.restoreState()


def _draw_image_borderless(
    c: canvas.Canvas,
    path: Optional[Path],
    x: float, y: float,
    w: float, h: float,
    _cache: Optional[dict] = None,
) -> None:
    """
    Draw a card image scaled up so the black border extends outside the slot,
    then clip to the exact slot rectangle so only the art/text area is visible.
    Falls back to the normal draw (with placeholder) if the image is missing.
    """
    reader = _get_reader(path, _cache if _cache is not None else {})
    if reader is None:
        _draw_image(c, path, x, y, w, h, _cache)
        return

    scale  = 1.0 / (1.0 - 2.0 * BORDER_FRACTION)  # ≈ 1.0753
    draw_w = w * scale
    draw_h = h * scale
    draw_x = x - (draw_w - w) / 2
    draw_y = y - (draw_h - h) / 2

    c.saveState()
    clip = c.beginPath()
    clip.rect(x, y, w, h)
    c.clipPath(clip, stroke=0, fill=0)
    c.drawImage(reader, draw_x, draw_y, draw_w, draw_h,
                preserveAspectRatio=False, mask="auto")
    c.restoreState()


def _draw_rotated_image_borderless(
    c: canvas.Canvas,
    path: Optional[Path],
    x: float, y: float,
    w: float, h: float,
    clockwise: bool,
    _cache: Optional[dict] = None,
) -> None:
    """
    Borderless variant of _draw_rotated_image for compact DFC mode.
    The clip is established after the rotate transform so it aligns with
    the rotated slot, not the pre-rotation page coordinates.
    """
    reader = _get_reader(path, _cache if _cache is not None else {})
    if reader is None:
        _draw_rotated_image(c, path, x, y, w, h, clockwise, _cache)
        return

    scale = 1.0 / (1.0 - 2.0 * BORDER_FRACTION)

    c.saveState()
    if clockwise:
        c.translate(x, y + h)
        c.rotate(-90)
    else:
        c.translate(x + w, y)
        c.rotate(90)

    # After rotation the slot occupies (0, 0, h, w) in local space
    local_w, local_h = h, w
    draw_w = local_w * scale
    draw_h = local_h * scale
    draw_x = -(draw_w - local_w) / 2
    draw_y = -(draw_h - local_h) / 2

    clip = c.beginPath()
    clip.rect(0, 0, local_w, local_h)
    c.clipPath(clip, stroke=0, fill=0)
    c.drawImage(reader, draw_x, draw_y, draw_w, draw_h,
                preserveAspectRatio=False, mask="auto")
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
    _cache: Optional[dict] = None,
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
    reader = _get_reader(path, _cache if _cache is not None else {})

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
    card_w: float = CARD_W,
    card_h: float = CARD_H,
) -> None:
    """Draw the horizontal divider between the two faces in compact mode."""
    mid_y = y + card_h / 2
    c.saveState()
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.setLineWidth(0.75)
    c.setDash(4, 2)
    c.line(x, mid_y, x + card_w, mid_y)
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
    if settings.print_borders:
        card_w, card_h = CARD_W, CARD_H
        draw_fn         = _draw_image
        draw_rotated_fn = _draw_rotated_image
    else:
        card_w = CARD_W * (1.0 - 2.0 * BORDER_FRACTION)
        card_h = CARD_H * (1.0 - 2.0 * BORDER_FRACTION)
        draw_fn         = _draw_image_borderless
        draw_rotated_fn = _draw_rotated_image_borderless

    geo = _layout(settings, card_w, card_h)
    render_list = _build_render_list(entries, settings)

    # Pre-load every unique image once so multi-copy cards don't re-read the file.
    reader_cache: dict = {}
    for entry in entries:
        for p in (entry.front_image_path, entry.back_image_path):
            _get_reader(p, reader_cache)

    c = canvas.Canvas(output_path, pagesize=(geo["page_w"], geo["page_h"]))

    for abs_idx, (face, entry) in enumerate(render_list):
        slot = abs_idx % CARDS_PER_PAGE

        # Start a new page (not for the very first card)
        if abs_idx > 0 and slot == 0:
            c.showPage()

        x, y = _card_xy(slot, geo)

        if settings.dfc_mode == "compact_stacked" and entry.back_image_path:
            # Front face: top half, rotated 90° CW (Dead // Gone layout)
            draw_rotated_fn(c, entry.front_image_path,
                            x, y + card_h / 2, card_w, card_h / 2,
                            clockwise=True, _cache=reader_cache)
            # Back face: bottom half, rotated 90° CW (same orientation as front)
            draw_rotated_fn(c, entry.back_image_path,
                            x, y, card_w, card_h / 2,
                            clockwise=True, _cache=reader_cache)
            _draw_compact_divider(c, x, y, card_w, card_h)
        elif face == "back":
            draw_fn(c, entry.back_image_path, x, y, card_w, card_h,
                    _cache=reader_cache)
        else:
            draw_fn(c, entry.front_image_path, x, y, card_w, card_h,
                    _cache=reader_cache)

        if settings.cut_lines:
            _draw_cut_lines(c, x, y, card_w, card_h)

    # Save even if render_list is empty (produces a blank page)
    c.save()
