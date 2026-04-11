---
name: ProxyMakerPro — Project Overview
description: macOS app that generates print-ready MTG card proxy PDFs; core printing decisions around card dimensions, DFC layouts, and decklist import formats
type: project
---

The user is building a macOS app called ProxyMakerPro that generates print-ready MTG card proxy PDFs.

**Why:** Proxy printing for personal/playtest use. Authoritative MTG card specs are needed so the app outputs correctly sized, printable cards.

**Core decisions confirmed (2026-04-11):**

### Card Dimensions
- Trim size: 2.5" x 3.5" (63.5mm x 88.9mm)
- Bleed: 1/8" (3.175mm) on all sides → full bleed canvas 2.75" x 3.75" (69.85mm x 95.25mm)
- Safe zone: ~1/16" inside trim on all sides
- At 300 DPI: trim = 750x1050px, full bleed = 825x1125px
- Corner radius: ~1/8" (3.175mm)

### DFC Layouts — Print Both Faces
| Layout | Print both? | Notes |
|---|---|---|
| transform | YES | Back face is separate permanent; must print both |
| modal_dfc | YES | Either face can be cast; both needed |
| meld | YES (3 items) | Two source cards + separate meld result card |
| reversible | Optional | Same card, different art |
| flip / split / adventure / saga | NO | Single face covers everything |

### Scryfall API — image_uris location
- transform / MDFC: image_uris are on each `card_faces[n]` object, NOT on top-level card
- meld sources: image_uris on top-level card; meld result is a SEPARATE card object
- flip / split / adventure: image_uris on top-level card only (no per-face images)

### Decklist Import Formats
- MTG Arena: `1 Front Face Name (SET) 123` — front face only, includes set+collector number
- MTGGoldfish native: `1 Front Face Name` — front face only, no set info
- MTGGoldfish MTGO export: `1 Front // Back` — full double-name
- MTGO format: `1 Front // Back` — must support for full compatibility

**How to apply:** When importing decklists, parse front-face name and optionally set+number. Use Scryfall to look up full card object and determine layout type to decide whether to fetch and print a second face.
