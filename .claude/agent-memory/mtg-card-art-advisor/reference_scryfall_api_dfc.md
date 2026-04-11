---
name: Scryfall API — DFC image_uris locations and layout field values
description: Where to find image_uris for each DFC layout type in the Scryfall API; critical for proxy image fetching logic
type: reference
---

## Scryfall API: image_uris by layout type

### Layouts where image_uris are on card_faces[n], NOT on top-level card:
- `transform`
- `modal_dfc`
- `reversible`
Access: `card.card_faces[0].image_uris.png` and `card.card_faces[1].image_uris.png`

### Layouts where image_uris are on the TOP-LEVEL card object:
- `flip`
- `split`
- `adventure`
- `saga`
- `class`
- All normal single-faced layouts
Access: `card.image_uris.png`

### Meld (special exception):
- The two meld SOURCE cards each have top-level `image_uris` as normal single-faced cards.
- The MELD RESULT is a completely separate card object with its own Scryfall ID and top-level `image_uris`.
- To get all three images, query source card A, source card B, and the meld result card independently.
- The meld result card's name (e.g., "Brisela, Voice of Nightmares") can be found in the source card's `all_parts` array with `component: "meld_result"`.

## Key Scryfall layout field values (as of 2025)
- `normal` — standard single-faced card
- `transform` — classic DFC, transforms mid-game
- `modal_dfc` — MDFC, choose face at cast time (Zendikar Rising+)
- `meld` — two cards meld into a combined back (Eldritch Moon, Brothers' War, etc.)
- `reversible_card` — two distinct artworks/versions, same card rules (Brother's War retro artifacts, some Secret Lairs)
- `flip` — Kamigawa-era rotational flip (single face)
- `split` — two spells on one face
- `adventure` — creature + adventure spell on one face
- `saga` — chapter enchantment (single face; note: some sagas in NEO are layout `transform`)
- `class` — level-up enchantment (single face)
- `prototype` — MOM artifact with alternate casting mode (single face)
- `mutate` — (handled as normal; mutate text is on single face)
- `battle` — Battle card type (single face, defense stat)

## Scryfall API base URL
https://api.scryfall.com/cards/named?fuzzy=CARDNAME
https://api.scryfall.com/cards/SCRYFALLID
