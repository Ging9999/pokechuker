"""Local SQLite card database — populated on-demand from the PokéTCG API."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import httpx

DB_PATH = Path(__file__).parent / "data" / "cards.db"
POKETCG_BASE = "https://api.pokemontcg.io/v2/cards"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                set_id      TEXT,
                set_name    TEXT,
                series      TEXT,
                number      TEXT,
                image_small TEXT,
                image_large TEXT,
                supertype   TEXT,
                subtypes    TEXT,
                rarity      TEXT,
                hp          TEXT,
                last_fetched TEXT
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cards_name ON cards(name COLLATE NOCASE)"
        )
        conn.commit()


def _to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    if d.get("subtypes"):
        try:
            d["subtypes"] = json.loads(d["subtypes"])
        except Exception:
            d["subtypes"] = []
    return d


def search_local(q: str, limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM cards WHERE name LIKE ? ORDER BY name LIMIT ?",
            (f"%{q}%", limit),
        ).fetchall()
    return [_to_dict(r) for r in rows]


def upsert_cards(api_cards: list[dict]):
    now = datetime.utcnow().isoformat()
    rows = []
    for c in api_cards:
        rows.append((
            c["id"],
            c.get("name", ""),
            c.get("set", {}).get("id"),
            c.get("set", {}).get("name"),
            c.get("set", {}).get("series"),
            c.get("number"),
            c.get("images", {}).get("small"),
            c.get("images", {}).get("large"),
            c.get("supertype"),
            json.dumps(c.get("subtypes") or []),
            c.get("rarity"),
            c.get("hp"),
            now,
        ))
    with get_conn() as conn:
        conn.executemany(
            """INSERT OR REPLACE INTO cards
               (id, name, set_id, set_name, series, number, image_small, image_large,
                supertype, subtypes, rarity, hp, last_fetched)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )
        conn.commit()


async def fetch_and_cache(q: str) -> list[dict]:
    """Hit PokéTCG API and cache results. Returns raw API list."""
    params = {"q": f'name:"{q}*"', "pageSize": 50}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(POKETCG_BASE, params=params)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                if data:
                    upsert_cards(data)
                return data
    except Exception:
        pass
    return []


async def autocomplete(q: str) -> list[dict]:
    q = q.strip()
    if len(q) < 2:
        return []
    local = search_local(q, limit=20)
    if len(local) >= 8:
        return local
    # Not enough local results — fetch from API then re-query local
    await fetch_and_cache(q)
    return search_local(q, limit=20)
