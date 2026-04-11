---
name: Decklist Format Notes
description: Arena/MTGO/MTGGoldfish format differences, section headers, regex edge cases for card name parsing
type: project
---

## MTG Arena Export Format

Full example with all section types:
```
Companion
1 Lurrus of the Dream-Den (IKO) 226

Deck
4 Thoughtseize (THS) 107
4 Inquisition of Kozilek (RNA) 71
2 Delver of Secrets // Insectile Aberration (ISD) 51
2 Uro, Titan of Nature's Wrath (THB) 229

Sideboard
2 Grafdigger's Cage (M20) 227
1 Lurrus of the Dream-Den (IKO) 226
```

Key structural rules:
- Section headers are standalone lines: `Deck`, `Sideboard`, `Companion`, `Commander`
- Cards: `<qty> <Name> (<SET>) <Collector#>`
- Set code and collector number are optional on import but always present on export
- DFC card name uses `//` separator with a space on both sides
- Blank line can also separate mainboard from sideboard (older copy-paste style)
- Commander format uses `Commander` header instead of `Deck`

## MTGGoldfish Format

```
4 Thoughtseize
4 Inquisition of Kozilek
2 Delver of Secrets

Sideboard
2 Grafdigger's Cage
```

Key differences from Arena:
- No set code or collector number
- Quantities are bare integers (no `x` suffix)
- May or may not have section headers
- No `Companion` section (shown as part of sideboard)

## MTGO Format

```
4 Thoughtseize
4 Inquisition of Kozilek

SIDEBOARD:
2 Grafdigger's Cage
```

Key differences:
- `SIDEBOARD:` header with colon (all-caps variant exists)
- Blank line between main and side is the primary separator
- No set codes

## Common Formats for Quantity Prefix

All of these appear in the wild and must be handled:
- `4 Lightning Bolt` — Arena, MTGGoldfish, MTGO
- `4x Lightning Bolt` — many deck builders and community sites
- `4X Lightning Bolt` — rare but seen
- `x4 Lightning Bolt` — very rare

## Regex Edge Cases in Card Names

### Special characters that appear in real card names:
- Apostrophes: `Gaea's Cradle`, `Urza's Mine`, `Serra's Sanctum`, `Ob Nixilis, the Fallen`
- Commas: `Korvold, Fae-Cursed King`, `Thalia, Guardian of Thraben`
- Hyphens: `Niv-Mizzet, Parun`, `Will-o'-the-Wisp` (apostrophe + hyphens)
- Colons: `Claim // Fame` (split card separator)
- Slashes: `Wear // Tear`, `Delver of Secrets // Insectile Aberration`
- Numbers: `Ink-Treader Nephilim`, `B.F.M. (Big Furry Monster)`, `Emrakul, the Promised End`
- Periods: `B.F.M.` (silver border joke card)
- Exclamation: none in current tournament-legal cards

### DFC name parsing:
- Arena exports only the front face name for the query; the `//` form is shown in exported lists but Scryfall's `fuzzy` endpoint resolves either the full `//` name or just the front face name correctly
- Safe approach: strip everything from ` // ` onward before querying Scryfall if the full name fails

### Set code in Arena format:
- Regex to strip set annotation: ` \([A-Z0-9]{3,6}\) \d+$`
- Must be stripped before using the name as a Scryfall query

### Cards with numbers in names:
- `Emrakul, the Aeons Torn`, `Marit Lage` — no numbers in name
- `Borrowing 100,000 Arrows` — number + comma (silver border)
- Safest approach: accept any character except digits-at-start for the name field in the regex

### Recommended name extraction regex:
```
^(\d+)[xX]?\s+(.+?)(?:\s+\([A-Z0-9]{3,6}\)\s+\d+)?$
```
Group 1 = quantity, Group 2 = card name (with set annotation stripped)
