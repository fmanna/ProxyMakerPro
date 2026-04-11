---
name: ProxyMakerPro Layout Engine
description: MTG card proxy PDF generator — layout specs, grid config, DFC compact mode, cut guide design, bleed recommendations
type: project
---

PDF layout engine for printing MTG card proxies on US Letter and A4 paper.

**Why:** User is building a Python-based PDF generator for MTG proxies, needs precise print measurements and layout decisions.

**How to apply:** Use these specs as ground truth for all layout, margin, DPI, and library decisions in this project.

## Card Dimensions
- Standard MTG card: 2.5" × 3.5" = 180 pt × 252 pt = 63mm × 88mm
- With home-print bleed (0.0625"/side): 2.625" × 3.625" = 189 × 261 pt
- With pro-print bleed (0.125"/side): 2.75" × 3.75" = 198 × 270 pt

## Grid Layout (no bleed, default mode)
### US Letter (8.5" × 11" / 612 × 792 pt)
- Cards: 3 columns × 3 rows = **9 cards**
- Margin top/bottom: 0.25" (18 pt)
- Margin left/right: 0.5" (36 pt)
- Gutters: 0" (0 pt)

### A4 (210 × 297 mm / 595 × 842 pt)
- Cards: 3 columns × 3 rows = **9 cards**
- Margin top/bottom: 16.5 mm (47 pt)
- Margin left/right: 10.5 mm (30 pt)
- Gutters: 0 mm (0 pt)

## Cut Guides
- Default (home): dashed lines at card boundary, 0.25 pt weight, 50% gray, dash 2pt on / 2pt off
- Optional (pro): L-shaped corner crop marks, offset 0.0625" from edge, mark length 0.125", 0.25 pt weight, registration black
- Crop marks require 0.125" (9 pt) gutters between cards → reduces to 6 cards/sheet on Letter

## DFC Compact Mode
- Both faces rotated 90° clockwise, stacked vertically in one 2.5" × 3.5" slot
- Each face rendered in a 2.5" × 1.75" sub-zone at ~70% scale
- Scale factor: min(2.5/3.5, 1.75/2.5) = 0.70
- Rendered face: ~2.45" × 1.75" (fills sub-zone completely)
- Body text at 70% scale (~5pt) — marginal readability, best achievable in a compact slot
- Non-compact DFC (two separate card slots) preferred as default

## Bleed Recommendations
- Home printing: no bleed, cut-to-card-boundary
- Pro print services: 0.125" (9 pt / 3.175mm) bleed all sides, safety zone 0.125" inside trim
- Pro mode: export single-card PDFs (2.75" × 3.75" with bleed) rather than sheets

## PDF Library
- Primary: reportlab (reportlab.pdfgen.canvas)
- Pre-processing: Pillow for image compositing / frame overlay
- reportlab units: use inch, mm constants from reportlab.lib.units
- Pillow is NOT the PDF generator — only for pixel-space preprocessing

## DPI
- Target: 300 DPI (Scryfall PNG is 745×1040 px = ~298 DPI at 2.5"×3.5")
- No upsampling or downsampling needed — embed Scryfall PNGs at native size
- Screen version: 150 DPI acceptable (scale to 372×520 px)
- PDF has no inherent DPI — DPI = pixels / placement_inches, resolved by drawImage dimensions
