# ProxyMakerPro

A macOS desktop app for generating print-ready Magic: The Gathering card proxy PDFs.
Card images are fetched from [Scryfall](https://scryfall.com) (with a Gatherer fallback)
and laid out in a 3×3 grid at exactly 2.5" × 3.5" — standard Magic card size.

---

## Requirements

- macOS 11 or later
- Python 3.11 or later (`python3 --version` to check)

---

## Installation & Launch

```bash
# 1. Install dependencies (one-time)
pip install -r requirements.txt

# 2. Run the app
python main.py
```

---

## How to Use

1. **Paste your decklist** into the left panel.
2. Click **Fetch Cards** — images are downloaded from Scryfall and appear in the preview grid.
   Previously downloaded images are served from the local cache instantly.
3. Adjust **Print Settings** in the right panel.
4. Click **Generate PDF…** and choose a save location.
   The PDF opens automatically in Preview when done.

---

## Supported Decklist Formats

### MTG Arena (recommended)

The Arena export format is fully supported and provides the richest information,
including the exact set and collector number for each card.

Copy a deck from the Arena client (**Decks → Export → Copy to Clipboard**) and paste directly.

```
Companion
1 Lurrus of the Dream-Den (IKO) 226

Deck
4 Lightning Bolt (M21) 150
2 Delver of Secrets // Insectile Aberration (ISD) 51
3 Snapcaster Mage (UMA) 71

Sideboard
3 Grafdigger's Cage (M20) 227
1 Lurrus of the Dream-Den (IKO) 226
```

**Section headers** (`Deck`, `Sideboard`, `Companion`, `Commander`) are optional but recommended.
Double-faced card names like `Delver of Secrets // Insectile Aberration` are handled automatically —
only the front-face name is used for the lookup.

---

### MTGGoldfish

Export from any deck page on MTGGoldfish using the **Text** export option.
Cards appear without set annotations; the app uses Scryfall's fuzzy name search
and returns the default printing (usually the most recent major-set release).

```
4 Lightning Bolt
2 Delver of Secrets
3 Snapcaster Mage

Sideboard
3 Grafdigger's Cage
```

A blank line between the main deck and sideboard is recognised as a section separator.

---

### MTGO / Generic

MTGO text exports and plain lists work too.
The `SB:` prefix marks sideboard cards.

```
4 Lightning Bolt
2 Delver of Secrets
SB: 3 Grafdigger's Cage
```

---

## Specifying a Particular Set's Art

By default, when no set information is present, the app picks the **most recent
non-promo English printing** of each card (Scryfall's default).

**To get a specific set's art**, include the set code (and optionally the collector number):

```
4 Lightning Bolt (LEA) 161        ← Alpha art, exact printing
4 Lightning Bolt (M21) 150        ← Magic 2021 art, exact printing
4 Lightning Bolt (ORI)            ← Origins art, no collector number needed
```

- With both set code and collector number, the app uses the precise
  `https://api.scryfall.com/cards/{set}/{number}` endpoint.
- With set code only, the app passes `set=` to the `/cards/named` fuzzy endpoint,
  returning that set's printing.

Collector numbers may be alphanumeric — `85a`, `85b`, etc. are valid:

```
1 Urza's Tower (ATQ) 85a
```

### Printing multiple art styles of the same card

Each line in the decklist is treated as an independent printing. To get four different
art styles of the same card, list each one separately:

```
1 Ancient Tomb (ZNE)
1 Ancient Tomb (EXP)
1 Ancient Tomb (EOS)
1 Ancient Tomb (TMP)
```

Each will be fetched and displayed as a separate thumbnail, and printed as a separate card.

### Finding set codes and collector numbers

- **From Arena:** the Export feature includes them automatically.
- **From Scryfall:** search for a card, click the printing you want, and read the URL:
  `https://scryfall.com/card/m21/150/lightning-bolt` → set `m21`, number `150`.
- **From MTGGoldfish:** use the Arena export option instead of the plain text export.

> **Note:** Gatherer fallback (used only if the Scryfall image CDN fails) does not
> support tokens or Arena-only digital sets.

---

## Print Settings

| Setting | Options | Notes |
|---|---|---|
| **Page size** | US Letter, A4 | 9 cards per page on both |
| **DFC mode** | Front face only | One slot per card; ignores back face |
| | Both faces (separate) | Front and back printed in consecutive slots |
| | Compact — both stacked | Front and back in one slot, rotated 90° |
| **Print borders** | On / Off | Print cards with/without borders |
| **Cut lines** | On / Off | Dashed guide lines at card boundaries |
| **Include sideboard** | On / Off | Exclude sideboard cards from the PDF |

### Borderless mode (Print borders: Off)

When **Print borders** is unchecked, the black border is removed from each card:

- The card slot shrinks to art-only dimensions (~2.33" × 3.25"), cropping out the ~2 mm
  black border on each edge.
- The page grid re-centres around the smaller slots.
- Cut lines (if enabled) draw around the art boundary, so the card you cut out has no border.

This is useful for borderless-style proxies or when sleeving cards where the border would
show through a clear sleeve. The printed card will be slightly smaller than a standard
Magic card.

### About Compact DFC Mode

Compact mode fits both faces of a double-faced card into one slot by rotating each face
90° clockwise and stacking them top/bottom (matching the layout of split cards like
Dead // Gone). The card preview in the grid updates to reflect the selected mode.

---

## Image Cache

Downloaded images and card metadata are stored in `~/Library/Caches/com.proxymakerpro.images/`.
Re-fetching the same card (same set and collector number) is instant on subsequent runs —
no network request is made.

To clear the cache: **File → Clear Image Cache…**

> After clearing the cache, the next Fetch Cards will re-download all images and
> re-query the Scryfall API for metadata.

---

## Tips

- **Commander decks (99 cards)** produce ~11 pages. Pre-fetch before printing so
  you can review any errors in the preview grid.
- **Cut lines** make a reliable cutting guide. A paper trimmer gives cleaner edges
  than scissors.
- **Card sleeves:** standard-size sleeves (63 × 88 mm) fit the cut proxies perfectly.
  Borderless-mode cards (~59 × 84 mm) fit too, with a small gap at the edges.
- If a card shows an error thumbnail, the card name may be misspelled or the card
  may be Arena/digital-only (not on Scryfall's image CDN). Double-check the spelling
  and try the Arena format with an explicit set code.
- **Different art for the same card:** list each printing on its own line with its
  set code. The app fetches and prints each independently.
