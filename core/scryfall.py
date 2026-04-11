"""
Scryfall API client with local image cache.

Card metadata is fetched sequentially (600 ms inter-request delay to respect
Scryfall's heavy-endpoint rate limit of ~2 req/s).

Card images are downloaded concurrently (up to 5 threads) from Scryfall's CDN.
If a CDN download fails and the card has a Gatherer multiverse ID, a Gatherer
fallback URL is attempted.

Cache location: ~/Library/Caches/com.proxymakerpro.images/
"""

import json
import time
from pathlib import Path
from typing import Optional
import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CACHE_DIR           = Path.home() / "Library" / "Caches" / "com.proxymakerpro.images"
_METADATA_CACHE_FILE = CACHE_DIR / "metadata_cache.json"

_API_BASE = "https://api.scryfall.com"
_GATHERER_IMG = "https://gatherer.wizards.com/Handlers/Image.ashx"

_HEADERS = {
    "User-Agent": "ProxyMakerPro/1.0",
    "Accept": "application/json",
}

REQUEST_DELAY = 0.6  # seconds between /cards/named API calls


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def ensure_cache() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def clear_cache() -> int:
    """Delete all cached PNG files and the metadata cache. Returns image count removed."""
    count = 0
    if CACHE_DIR.exists():
        for f in CACHE_DIR.glob("*.png"):
            f.unlink(missing_ok=True)
            count += 1
    _METADATA_CACHE_FILE.unlink(missing_ok=True)
    return count


# ---------------------------------------------------------------------------
# Metadata cache
# ---------------------------------------------------------------------------

def metadata_cache_key(
    name: str,
    set_code: Optional[str],
    collector_number: Optional[str],
) -> str:
    return f"{name.lower()}|{(set_code or '').lower()}|{collector_number or ''}"


def load_metadata_cache() -> dict:
    if _METADATA_CACHE_FILE.exists():
        try:
            return json.loads(_METADATA_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_metadata_entry(key: str, data: dict, cache: dict) -> None:
    """Write a single entry into the in-memory cache dict and persist to disk."""
    cache[key] = data
    try:
        _METADATA_CACHE_FILE.write_text(
            json.dumps(cache, indent=2), encoding="utf-8"
        )
    except Exception:
        pass  # Non-fatal — next run will re-fetch


def front_cache_path(scryfall_id: str) -> Path:
    return CACHE_DIR / f"{scryfall_id}.png"


def back_cache_path(scryfall_id: str) -> Path:
    return CACHE_DIR / f"{scryfall_id}_back.png"


# ---------------------------------------------------------------------------
# Metadata fetch
# ---------------------------------------------------------------------------

def fetch_card_metadata(
    name: str,
    set_code: Optional[str] = None,
    collector_number: Optional[str] = None,
) -> dict:
    """
    Fetch card JSON from Scryfall.

    When set_code and collector_number are both provided (from an MTG Arena
    decklist annotation like "(M21) 150"), the precise /cards/{set}/{number}
    endpoint is used to retrieve that exact printing and art.  Falls back to
    fuzzy name search if the set/number lookup returns an error.
    """
    if set_code and collector_number:
        url = f"{_API_BASE}/cards/{set_code.lower()}/{collector_number}"
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError:
            pass  # Fall through to fuzzy search

    params: dict = {"fuzzy": name}
    if set_code:
        params["set"] = set_code.lower()

    resp = requests.get(
        f"{_API_BASE}/cards/named",
        params=params,
        headers=_HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_image_urls(card: dict) -> tuple[str, Optional[str]]:
    """
    Return (front_png_url, back_png_url | None) from a Scryfall card dict.

    - Normal cards: top-level image_uris["png"]
    - Transform / modal_dfc: card_faces[0/1].image_uris["png"]
    - Meld (source card): top-level image_uris["png"], back handled separately
    """
    faces = card.get("card_faces")
    if faces and faces[0].get("image_uris"):
        # transform / modal_dfc — top-level image_uris is absent
        back_uris = faces[1].get("image_uris") if len(faces) > 1 else None
        back_url = back_uris["png"] if back_uris else None
        return faces[0]["image_uris"]["png"], back_url
    # normal, adventure, split, saga, flip, meld (front)
    return card["image_uris"]["png"], None


def fetch_meld_result_url(card: dict) -> Optional[str]:
    """
    For meld layout cards, find the meld_result entry in all_parts,
    fetch that card separately, and return its image URL.
    """
    for part in card.get("all_parts", []):
        if part.get("component") == "meld_result":
            card_id = part["id"]
            resp = requests.get(
                f"{_API_BASE}/cards/{card_id}",
                headers=_HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            result_card = resp.json()
            uris = result_card.get("image_uris", {})
            return uris.get("png")
    return None


# ---------------------------------------------------------------------------
# Image download
# ---------------------------------------------------------------------------

def download_image(
    url: str,
    dest: Path,
    multiverse_id: Optional[int] = None,
) -> None:
    """
    Stream-download a card image to dest.
    Falls back to Gatherer if the primary URL fails and multiverse_id is set.
    Note: Gatherer does not cover tokens or Arena-only sets.
    """
    if dest.exists():
        return  # Already cached

    def _stream(target_url: str) -> None:
        resp = requests.get(target_url, timeout=20, stream=True)
        resp.raise_for_status()
        tmp = dest.with_suffix(".tmp")
        try:
            with open(tmp, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    fh.write(chunk)
            tmp.rename(dest)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    try:
        _stream(url)
    except requests.RequestException as primary_err:
        if multiverse_id is None:
            raise
        gatherer_url = f"{_GATHERER_IMG}?multiverseid={multiverse_id}&type=card"
        try:
            _stream(gatherer_url)
        except requests.RequestException:
            # Re-raise the original Scryfall error so the caller has context
            raise primary_err
