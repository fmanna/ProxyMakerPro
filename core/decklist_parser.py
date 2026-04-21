"""
Parse MTG Arena, MTGGoldfish, and MTGO decklist formats into CardEntry objects.

Supported formats:
  MTG Arena:   "4 Lightning Bolt (M21) 150"  with Deck/Sideboard/Companion headers
  MTGGoldfish: "4 Lightning Bolt"            with optional Sideboard header or blank line
  MTGO:        "4 Lightning Bolt"  or  "SB: 3 Grafdigger's Cage"
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Standalone lines that indicate a section change (case-insensitive match)
_SECTION_HEADERS = {"deck", "sideboard", "companion", "commander", "maindeck"}

# Matches: "4 Card Name" or "4x Card Name" optionally followed by " (SET)" or " (SET) 123"
# Groups: 1=count  2=name  3=set_code (optional)  4=collector_number (optional)
_LINE_RE = re.compile(
    r"^(\d+)[xX]?\s+(.+?)(?:\s+\(([A-Z0-9]{3,6})\)(?:\s+(\d+))?)?$"
)


@dataclass
class CardEntry:
    count: int
    name: str           # Front-face name only — DFC " // " suffix stripped; used for Scryfall
    raw_name: str       # Original text from decklist line
    is_sideboard: bool

    # From the decklist annotation — used to fetch a specific printing:
    set_code: Optional[str] = field(default=None)
    collector_number: Optional[str] = field(default=None)

    # Populated by FetchWorker after images are downloaded:
    scryfall_id: Optional[str] = field(default=None, repr=False)
    layout: Optional[str] = field(default=None, repr=False)
    front_image_path: Optional[Path] = field(default=None, repr=False)
    back_image_path: Optional[Path] = field(default=None, repr=False)
    error: Optional[str] = field(default=None, repr=False)


@dataclass
class PrintSettings:
    page_size: str = "letter"       # "letter" | "a4"
    dfc_mode: str = "front_only"    # "front_only" | "both_separate" | "compact_stacked"
    print_borders: bool = True
    cut_lines: bool = True
    include_sideboard: bool = True


def parse(text: str) -> list[CardEntry]:
    """Parse a decklist string and return a list of CardEntry objects."""
    # Strip UTF-8 BOM and normalise line endings
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")

    entries: list[CardEntry] = []
    is_sideboard = False
    main_deck_seen = False
    blank_seen_after_main = False

    for raw_line in text.split("\n"):
        line = raw_line.strip()

        # --- Blank line ---
        if not line:
            if main_deck_seen and not is_sideboard:
                blank_seen_after_main = True
            continue

        # --- MTGO "SB: " prefix ---
        sb_prefix = False
        if line.lower().startswith("sb: "):
            line = line[4:].strip()
            sb_prefix = True

        # --- Section header ---
        if line.lower() in _SECTION_HEADERS:
            if line.lower() == "sideboard":
                is_sideboard = True
            else:
                # "Deck", "Commander", "Companion", "Maindeck" → main section
                is_sideboard = False
                main_deck_seen = True
            blank_seen_after_main = False
            continue

        # --- Blank-line section transition (Goldfish / MTGO style) ---
        if blank_seen_after_main and not is_sideboard:
            is_sideboard = True
            blank_seen_after_main = False

        if sb_prefix:
            is_sideboard = True

        # --- Try to parse as a card line ---
        m = _LINE_RE.match(line)
        if not m:
            continue

        count = int(m.group(1))
        raw_name = m.group(2).strip()
        set_code = m.group(3)           # None when annotation absent
        collector_number = m.group(4)   # None when annotation absent

        # Strip DFC " // back-face" from the name — Scryfall accepts the front name
        name = raw_name.split(" // ")[0].strip()

        entries.append(CardEntry(
            count=count,
            name=name,
            raw_name=raw_name,
            is_sideboard=is_sideboard,
            set_code=set_code,
            collector_number=collector_number,
        ))

        if not is_sideboard:
            main_deck_seen = True

    return entries
