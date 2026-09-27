"""SQLite database layer for BGS scraper."""
import csv
import sqlite3
from datetime import datetime
from pathlib import Path

import config

_CREATE_CARDS = """
CREATE TABLE IF NOT EXISTS cards (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id       INTEGER UNIQUE,           -- Beckett card-lookup ?item_id=N
    card_id       TEXT    UNIQUE NOT NULL,  -- derived from item_id or URL slug
    name          TEXT    NOT NULL,
    set_name      TEXT,
    year          TEXT,
    card_number   TEXT,
    category      TEXT,
    front_image_url  TEXT,
    back_image_url   TEXT,
    front_image_path TEXT,
    back_image_path  TEXT,
    centering     REAL,
    corners       REAL,
    edges         REAL,
    surface       REAL,
    overall_grade REAL,
    grade_label   TEXT,
    source_url    TEXT    NOT NULL,
    scraped_at    TEXT    NOT NULL
)
"""

_CREATE_ERRORS = """
CREATE TABLE IF NOT EXISTS errors (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    url          TEXT    NOT NULL,
    card_id      TEXT,
    error_msg    TEXT    NOT NULL,
    attempted_at TEXT    NOT NULL,
    retry_count  INTEGER NOT NULL DEFAULT 0
)
"""

_CREATE_IDX     = "CREATE INDEX IF NOT EXISTS idx_cards_card_id  ON cards(card_id)"
_CREATE_IDX_IID = "CREATE INDEX IF NOT EXISTS idx_cards_item_id  ON cards(item_id)"


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")   # allows concurrent readers + one writer
    con.execute("PRAGMA synchronous=NORMAL") # safe + faster than FULL under WAL
    return con


def init_db() -> None:
    """Create tables and indexes. Migrates existing DBs to add new columns."""
    with _conn() as con:
        con.execute(_CREATE_CARDS)
        con.execute(_CREATE_ERRORS)
        # Migration: add new columns before creating indexes that reference them
        for col, typedef in [("item_id", "INTEGER"), ("category", "TEXT")]:
            try:
                con.execute(f"ALTER TABLE cards ADD COLUMN {col} {typedef}")
            except Exception:
                pass  # column already exists
        con.execute(_CREATE_IDX)
        con.execute(_CREATE_IDX_IID)


def card_exists(card_id: str) -> bool:
    with _conn() as con:
        row = con.execute("SELECT 1 FROM cards WHERE card_id = ?", (card_id,)).fetchone()
        return row is not None


def item_id_exists(item_id: int) -> bool:
    """True if this item_id was already successfully scraped."""
    with _conn() as con:
        row = con.execute("SELECT 1 FROM cards WHERE item_id = ?", (item_id,)).fetchone()
        return row is not None


def get_last_scraped_id() -> int:
    """Return the highest item_id stored, or 0 if none. Used for --resume."""
    with _conn() as con:
        row = con.execute(
            "SELECT MAX(item_id) FROM cards WHERE item_id IS NOT NULL"
        ).fetchone()
        return row[0] or 0


def insert_card(data: dict) -> None:
    """Insert a card record. Silently ignores duplicates (resume support)."""
    data.setdefault("scraped_at", datetime.utcnow().isoformat())
    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" * len(data))
    with _conn() as con:
        con.execute(
            f"INSERT OR IGNORE INTO cards ({cols}) VALUES ({placeholders})",
            list(data.values()),
        )


def log_error(url: str, error_msg: str, card_id: str | None = None) -> None:
    """Log a failed scrape. Increments retry_count if URL already in errors."""
    with _conn() as con:
        existing = con.execute(
            "SELECT id, retry_count FROM errors WHERE url = ?", (url,)
        ).fetchone()
        if existing:
            con.execute(
                "UPDATE errors SET retry_count = ?, attempted_at = ?, error_msg = ? WHERE id = ?",
                (existing["retry_count"] + 1, datetime.utcnow().isoformat(), error_msg, existing["id"]),
            )
        else:
            con.execute(
                "INSERT INTO errors (url, card_id, error_msg, attempted_at) VALUES (?, ?, ?, ?)",
                (url, card_id, error_msg, datetime.utcnow().isoformat()),
            )


def get_failed_urls() -> list[str]:
    """Return URLs from the errors table for retry."""
    with _conn() as con:
        rows = con.execute("SELECT url FROM errors").fetchall()
        return [r["url"] for r in rows]


def total_scraped() -> int:
    with _conn() as con:
        return con.execute("SELECT COUNT(*) FROM cards").fetchone()[0]


def total_errors() -> int:
    with _conn() as con:
        return con.execute("SELECT COUNT(*) FROM errors").fetchone()[0]


def export_csv(path: str = config.CSV_OUTPUT) -> int:
    """Write all cards to a CSV file. Returns row count."""
    with _conn() as con:
        rows = con.execute("SELECT * FROM cards ORDER BY id").fetchall()
    if not rows:
        return 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows([dict(r) for r in rows])
    return len(rows)
