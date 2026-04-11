---
name: Caching Strategy
description: macOS cache directory location, Scryfall ID as cache key, directory structure for image cache
type: project
---

## macOS Cache Location

Use `~/Library/Caches/<bundle-id>/` — this is the correct macOS convention for re-downloadable data:
- macOS may purge this under low-disk-space conditions (acceptable: images can be re-fetched)
- Do NOT use `~/Library/Application Support/` — that is for data the app cannot recreate
- Resolved programmatically via `NSCachesDirectory` (Swift/ObjC) or `os.path.expanduser("~/Library/Caches/")` (Python)

Recommended path: `~/Library/Caches/com.proxymakerPro.images/`

## Cache Key

Use Scryfall's UUID `id` field as the filename — it is:
- Globally unique per printing
- Stable (does not change when card data is updated)
- Already in the API response, so no extra lookup needed

For DFC cards, each face has its own image, but they share the parent card's `id`. Use a suffix to distinguish:
- `{scryfall_id}_face0.png` — front face
- `{scryfall_id}_face1.png` — back face
- `{scryfall_id}.png` — normal single-faced card

## Directory Structure

```
~/Library/Caches/com.proxymakerPro.images/
  {uuid}.png                    # single-faced card
  {uuid}_face0.png              # DFC front face
  {uuid}_face1.png              # DFC back face
```

Flat directory is fine for ~100 card images. If scaling to thousands, add a 2-char hex prefix subdirectory: `{uuid[0:2]}/{uuid}.png`

## Cache Lookup Flow

1. Compute expected cache path from Scryfall ID
2. If file exists on disk, skip download
3. If missing, fetch from Scryfall CDN and stream directly to disk
4. Never hold all images in memory simultaneously — stream to disk

## Cache Invalidation

- No TTL needed for print proxy use: a card's art rarely changes between sessions
- Provide a manual "clear cache" option in the UI for edge cases
- Cache size for 100 cards at ~1MB PNG each: ~100MB — acceptable
