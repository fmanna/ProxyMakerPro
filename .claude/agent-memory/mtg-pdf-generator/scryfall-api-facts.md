---
name: Scryfall API Facts
description: Verified Scryfall API endpoint URLs, rate limits, image format dimensions, DFC/transform card_faces structure, and Gatherer fallback details
type: project
---

## Endpoints

- Named card fetch: `GET https://api.scryfall.com/cards/named?fuzzy=<name>` (fuzzy) or `?exact=<name>` (exact)
- Optional set scoping: add `&set=<set_code>` parameter
- Image direct fetch: `GET https://api.scryfall.com/cards/named?fuzzy=<name>&format=image&version=<size>`

## Rate Limits (tiered — confirmed from docs)

- Lightweight endpoints (cards by ID, sets, autocomplete): 10 req/sec
- Heavy endpoints (search, named, random, collection): **2 req/sec**
- Recommended delay: 50–100ms between requests
- HTTP 429 = rate limited for 30 seconds; continued abuse risks permanent ban
- Required headers: `User-Agent` (accurate description of your app), `Accept`

## Image Format Options

| Version     | Format | Approx Dimensions | Notes                                      |
|-------------|--------|-------------------|--------------------------------------------|
| small       | JPG    | 146×204px         | Thumbnail only                             |
| normal      | JPG    | 488×680px         | Good for preview                           |
| large       | JPG    | 672×936px         | Default per docs; good quality             |
| **png**     | PNG    | **745×1040px**    | **Highest quality; transparent corners; lossless** |
| art_crop    | JPG    | variable          | Art only, no frame                         |
| border_crop | JPG    | 480×680px         | Full card, no white corners                |

**Recommendation for print proxy**: Use `png` — highest resolution, transparent corners, lossless. ~1MB per card.

## DFC / Transform Card Structure

For cards with layout `transform`, `modal_dfc`, `double_faced_token`, `flip`:
- **Top-level `image_uris` is ABSENT** (not null — the field simply does not exist)
- Images live exclusively in `card_faces[0].image_uris` (front) and `card_faces[1].image_uris` (back)
- Each face object has its own `image_uris` with all the same size keys (small, normal, large, png, art_crop, border_crop)
- The `name` field on the root object is the combined name: `"Delver of Secrets // Insectile Aberration"`
- Each face has its own `name`, `mana_cost`, `type_line`, `oracle_text` fields

Detection pattern: check `if card.get('card_faces')` — if truthy, use card_faces image_uris instead of top-level.

## Multiverse IDs

- Present in top-level `multiverse_ids` array (can be multiple for DFC cards — one per face)
- Absent or empty for: tokens, Alchemy/digital-only cards, some Unfinity Acorn-stamped cards, art cards, promotional one-offs
- Scryfall's own `id` (UUID) is always present and stable — prefer this as cache key

## Gatherer Fallback URL

`https://gatherer.wizards.com/Handlers/Image.ashx?multiverseid=<id>&type=card`

Coverage gaps where Gatherer CANNOT serve as fallback:
- All tokens (no Gatherer presence)
- Alchemy/Arena-only cards (digital-only sets: A30, Y22, etc.)
- Unfinity Acorn-stamped cards
- Mystery Booster test cards
- Some very recent sets before Gatherer indexes them
- Cards with empty `multiverse_ids` array in Scryfall response

**Why**: Scryfall has the broadest coverage. Gatherer fallback is only useful for a narrow set of older cards when Scryfall's CDN specifically fails, not as a general fallback.
