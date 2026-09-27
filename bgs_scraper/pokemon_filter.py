"""Pokémon card filter.

Checks a scraped record against three gates (in order, fast → slow):

  1. Category gate  — BGS sport/category field vs POKEMON_CATEGORIES list.
                      Hard-rejects obvious non-Pokémon sports.
  2. Keyword gate   — card name contains one of the POKEMON_KEYWORDS strings.
  3. PokéTCG gate   — first token of card name found in the full PokéTCG API
                      name list (fetched once and cached to POKETCG_NAMES_CACHE).

Toggle with ``POKEMON_ONLY = False`` in config.py to pass everything through.
"""

import json
import re
import time
from pathlib import Path
from typing import Optional

import httpx

import config


# ── Name normalisation ────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    """Lowercase, replace accented chars, strip punctuation."""
    s = s.lower()
    s = s.replace("é", "e").replace("è", "e").replace("ê", "e")
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return s.strip()


# ── PokéTCG name cache ────────────────────────────────────────────────────────

_NAMES_CACHE: Optional[set[str]] = None   # normalised names, loaded once


def _load_disk_cache() -> set[str]:
    p = Path(config.POKETCG_NAMES_CACHE)
    if p.exists():
        try:
            return set(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return set()


def _save_disk_cache(names: set[str]) -> None:
    Path(config.POKETCG_NAMES_CACHE).write_text(
        json.dumps(sorted(names), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _fetch_poketcg_names() -> set[str]:
    """Page through PokéTCG API and collect all unique card names (normalised)."""
    print("[filter] Building Pokémon name list from PokéTCG API (one-time) …")
    names: set[str] = set()
    client = httpx.Client(timeout=15, follow_redirects=True)
    page = 1

    while True:
        try:
            resp = client.get(
                "https://api.pokemontcg.io/v2/cards",
                params={"page": page, "pageSize": 250, "select": "name"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"[filter] PokéTCG API error (page {page}): {exc}")
            break

        cards = data.get("data", [])
        if not cards:
            break

        for card in cards:
            raw = card.get("name", "").strip()
            if raw:
                # Store both the full card name and the first "word" (species name)
                names.add(_norm(raw))
                names.add(_norm(raw.split(" ")[0]))  # e.g. "charizard" from "Charizard VMAX"

        total = data.get("totalCount", "?")
        print(f"[filter]   page {page}: {len(names)} unique names (total cards: {total})")

        if len(cards) < 250:
            break
        page += 1
        time.sleep(0.3)

    return names


def get_pokemon_names() -> set[str]:
    """Return the cached normalised name set, fetching from API if needed."""
    global _NAMES_CACHE
    if _NAMES_CACHE is not None:
        return _NAMES_CACHE

    _NAMES_CACHE = _load_disk_cache()
    if _NAMES_CACHE:
        return _NAMES_CACHE

    # Add hardcoded keywords as a baseline before API fetch
    _NAMES_CACHE = {_norm(kw) for kw in config.POKEMON_KEYWORDS}

    api_names = _fetch_poketcg_names()
    _NAMES_CACHE.update(api_names)

    _save_disk_cache(_NAMES_CACHE)
    print(f"[filter] Cached {len(_NAMES_CACHE)} Pokémon names to {config.POKETCG_NAMES_CACHE}")
    return _NAMES_CACHE


def warm_cache() -> int:
    """Pre-load the name list. Returns name count. Call once at startup."""
    if not config.POKEMON_ONLY:
        return 0
    return len(get_pokemon_names())


# ── Non-Pokémon sport deny-list ───────────────────────────────────────────────

_DENY_SPORTS = {
    "baseball", "basketball", "football", "hockey", "soccer", "tennis", "golf",
    "wrestling", "boxing", "ufc", "mma", "nfl", "nba", "mlb", "nhl", "nascar",
    "cricket", "rugby", "volleyball",
    "magic the gathering", "magic: the gathering", "yugioh", "yu-gi-oh",
    "one piece", "digimon", "dragon ball",
}


# ── Public filter function ────────────────────────────────────────────────────

def is_pokemon_card(
    name: str,
    category: str = "",
    set_name: str = "",
) -> bool:
    """
    Return True if this card should be saved (passes the Pokémon filter).

    Always returns True when ``config.POKEMON_ONLY`` is False.
    """
    if not config.POKEMON_ONLY:
        return True

    # ── Gate 1: category field ────────────────────────────────────────────────
    if category:
        cat = _norm(category)
        # Explicit match → accept immediately
        if any(c in cat for c in config.POKEMON_CATEGORIES):
            return True
        # Explicit deny → reject without further checks
        if any(d in cat for d in _DENY_SPORTS):
            return False

    # ── Gate 2: keyword whitelist ─────────────────────────────────────────────
    name_lower = name.lower()
    if any(kw.lower() in name_lower for kw in config.POKEMON_KEYWORDS):
        return True

    # ── Gate 3: PokéTCG name list ─────────────────────────────────────────────
    pokemon_names = get_pokemon_names()
    # Check the first token (the Pokémon species name)
    first_token = _norm(name.split()[0]) if name.split() else ""
    if first_token and first_token in pokemon_names:
        return True
    # Check the full normalised name
    if _norm(name) in pokemon_names:
        return True

    return False


def filter_reason(name: str, category: str = "") -> str:
    """Human-readable reason string for why a card was skipped (for debug logging)."""
    if not category and not name:
        return "empty name and category"
    cat = _norm(category)
    for d in _DENY_SPORTS:
        if d in cat:
            return f"category '{category}' is not Pokémon"
    return f"name '{name}' not in Pokémon name list"
