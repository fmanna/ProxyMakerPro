---
name: Reference: Scryfall Image Specs
description: Scryfall image format sizes and DPI implications for MTG card printing at 2.5"x3.5"
type: reference
---

## Scryfall Image Formats (public API)
- `png`: 745 × 1040 px — **use for print** — ~298 DPI at 2.5"×3.5"
- `large`: 672 × 936 px, JPEG — not suitable for 300 DPI print
- `normal`: 488 × 680 px, JPEG — not suitable for print
- `small`: low resolution — not suitable for print
- `border_crop`: 480 × 680 px — border removed, use only with custom frame layers

## DPI Math
- 745 px / 2.5" = 298 DPI horizontal
- 1040 px / 3.5" = 297 DPI vertical
- Scryfall PNG is purpose-sized for 300 DPI print output

## Usage Note
Embed `png` images in reportlab at exactly 2.5"×3.5" (180×252 pt) to achieve native 300 DPI.
No resampling required for print output.
