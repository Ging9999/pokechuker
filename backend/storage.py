"""Flat-file JSON storage helpers."""
import json
import os
import re
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"
CARDS_DIR = DATA_DIR / "cards"
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"

CARDS_DIR.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:80]


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------- Card listing storage ----------

def card_path(slug: str) -> Path:
    return CARDS_DIR / f"{slug}.json"


def load_card(slug: str) -> dict:
    default = {"slug": slug, "listings": [], "last_updated": None}
    return _read_json(card_path(slug), default)


def save_card(slug: str, data: dict) -> None:
    _write_json(card_path(slug), data)


def upsert_listings(slug: str, new_listings: list[dict]) -> dict:
    """Merge new listings into stored data, deduplicating by listing id."""
    card = load_card(slug)
    existing = {l["id"]: l for l in card.get("listings", [])}
    for listing in new_listings:
        existing[listing["id"]] = listing
    card["listings"] = sorted(existing.values(), key=lambda x: x.get("date", ""), reverse=True)
    from datetime import datetime
    card["last_updated"] = datetime.utcnow().isoformat()
    save_card(slug, card)
    return card


def list_cards() -> list[str]:
    return [p.stem for p in CARDS_DIR.glob("*.json")]


# ---------- Portfolio storage ----------

def load_portfolio() -> dict:
    return _read_json(PORTFOLIO_FILE, {"cards": []})


def save_portfolio(data: dict) -> None:
    _write_json(PORTFOLIO_FILE, data)


def get_portfolio_card(portfolio: dict, card_id: str) -> dict | None:
    for c in portfolio["cards"]:
        if c["id"] == card_id:
            return c
    return None
