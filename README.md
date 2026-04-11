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

**To get a specific set's art**, use the MTG Arena format and include the set code
and collector number in parentheses:

```
4 Lightning Bolt (LEA) 161        ← Alpha art
4 Lightning Bolt (M21) 150        ← Magic 2021 art
4 Lightning Bolt (ORI) 152        ← Origins art
```

The app uses the precise `https://api.scryfall.com/cards/{set}/{number}` endpoint
when this annotation is present, guaranteeing the exact printing and artwork you requested.

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
| | Both faces (separate) | Front cards first, then back cards |
| | Compact — both stacked | Front and back in one card slot (top/bottom halves) |
| **Cut lines** | On / Off | Dashed guide lines at card boundaries |
| **Include sideboard** | On / Off | Exclude sideboard cards from the PDF |

### About Compact DFC Mode

Compact mode fits both faces of a double-faced card into the standard 2.5" × 3.5" slot
by printing each face at half height (~1.75"). This is useful as a quick reference but
reduces card text to roughly 5 pt — legible but small.
**"Both faces (separate)"** is recommended when you need to read the card text comfortably.

---

## Image Cache

Downloaded images are stored in `~/Library/Caches/com.proxymakerpro.images/`.
Re-fetching the same card is instant on subsequent runs.

To clear the cache: **File → Clear Image Cache…**

---

## Tips

- **Commander decks (99 cards)** produce ~11 pages. Pre-fetch before printing so
  you can review any errors in the preview grid.
- **Cut lines** make a reliable cutting guide. A paper trimmer gives cleaner edges
  than scissors.
- **Card sleeves:** standard-size sleeves (63 × 88 mm) fit the cut proxies perfectly.
- If a card shows an error thumbnail, the card name may be misspelled or the card
  may be Arena/digital-only (not on Scryfall's image CDN). Double-check the spelling
  and try the Arena format with an explicit set code.
