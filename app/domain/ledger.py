"""Local SQLite ledger — the structured, self-watching record of every purchase.

Local-first by design (privacy pillar): the ledger is a single SQLite file on the
user's machine. The Ledger agent writes/dedupes through here; the Watchdog reads
open items to sweep; ``export_xlsx`` produces the human-friendly spreadsheet view.

Deterministic and ADK-free so it is unit-testable in isolation.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS receipts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL,          -- item / short description
    merchant         TEXT    NOT NULL,
    purchase_date    TEXT    NOT NULL,          -- ISO 8601 (YYYY-MM-DD)
    total            REAL    NOT NULL,
    category         TEXT    DEFAULT 'general',
    last4            TEXT,                       -- payment card last 4 only (never full PAN)
    returnable       INTEGER NOT NULL DEFAULT 1, -- 0/1
    warranty_expires TEXT,                       -- ISO date or NULL
    current_price    REAL,                       -- latest observed price (price feed)
    recalled         INTEGER NOT NULL DEFAULT 0, -- 0/1 (recall feed)
    source_file      TEXT,                       -- path to filed source document
    created_at       TEXT    DEFAULT (datetime('now')),
    -- Natural key for dedupe: same merchant + item + date + total is the same receipt.
    UNIQUE (merchant, name, purchase_date, total)
);
"""

_BOOL_FIELDS = ("returnable", "recalled")


@contextmanager
def _connect(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection with row access by column name."""
    path = db_path or config.LEDGER_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path | None = None) -> None:
    """Create the ledger table if it does not exist (idempotent)."""
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a DB row to a plain dict, normalizing 0/1 ints to bools."""
    d = dict(row)
    for field in _BOOL_FIELDS:
        if field in d and d[field] is not None:
            d[field] = bool(d[field])
    return d


def upsert_receipt(entry: dict, db_path: Path | None = None) -> dict:
    """Insert a receipt, or update it if the natural key already exists (dedupe).

    ``entry`` must include: name, merchant, purchase_date, total. Optional:
    category, last4, returnable, warranty_expires, current_price, recalled,
    source_file. Returns the stored row as a dict (including its ``id``).
    """
    init_db(db_path)
    fields = {
        "name": entry["name"],
        "merchant": entry["merchant"],
        "purchase_date": entry["purchase_date"],
        "total": float(entry["total"]),
        "category": entry.get("category", "general"),
        "last4": entry.get("last4"),
        "returnable": int(bool(entry.get("returnable", True))),
        "warranty_expires": entry.get("warranty_expires"),
        "current_price": entry.get("current_price"),
        "recalled": int(bool(entry.get("recalled", False))),
        "source_file": entry.get("source_file"),
    }
    cols = ", ".join(fields)
    placeholders = ", ".join(f":{k}" for k in fields)
    # ON CONFLICT keeps the natural key stable and refreshes mutable fields
    # (price/recall/warranty), which is exactly what the daily sweep needs.
    update_cols = ", ".join(
        f"{k}=excluded.{k}"
        for k in ("category", "last4", "returnable", "warranty_expires",
                  "current_price", "recalled", "source_file")
    )
    sql = (
        f"INSERT INTO receipts ({cols}) VALUES ({placeholders}) "
        f"ON CONFLICT(merchant, name, purchase_date, total) DO UPDATE SET {update_cols}"
    )
    with _connect(db_path) as conn:
        conn.execute(sql, fields)
        row = conn.execute(
            "SELECT * FROM receipts WHERE merchant=:merchant AND name=:name "
            "AND purchase_date=:purchase_date AND total=:total",
            fields,
        ).fetchone()
    return _row_to_dict(row)


def all_receipts(db_path: Path | None = None) -> list[dict]:
    """Return every ledger row as a list of dicts."""
    init_db(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM receipts ORDER BY purchase_date DESC").fetchall()
    return [_row_to_dict(r) for r in rows]


def open_items(db_path: Path | None = None) -> list[dict]:
    """Items the Watchdog should still watch: returnable, or with a warranty, or recalled.

    Consumables past every window fall out of the sweep automatically — which is why
    the "don't nag on items past their window" scenario holds.
    """
    init_db(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM receipts "
            "WHERE returnable = 1 OR warranty_expires IS NOT NULL OR recalled = 1 "
            "ORDER BY purchase_date DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def query_category_total(category: str, db_path: Path | None = None) -> float:
    """Sum spend for a category (backs the 'how much on appliances?' NL query)."""
    init_db(db_path)
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(total), 0) AS s FROM receipts WHERE lower(category) = lower(?)",
            (category,),
        ).fetchone()
    return float(row["s"])


def export_xlsx(dest: Path | None = None, db_path: Path | None = None) -> Path:
    """Write a human-friendly .xlsx view of the ledger and return its path."""
    from openpyxl import Workbook  # imported here so the domain layer stays import-light

    dest = dest or (config.VAULT_DIR / "ledger_export.xlsx")
    dest.parent.mkdir(parents=True, exist_ok=True)
    rows = all_receipts(db_path)
    wb = Workbook()
    ws = wb.active
    ws.title = "Ledger"
    headers = [
        "id", "name", "merchant", "purchase_date", "total", "category",
        "last4", "returnable", "warranty_expires", "current_price", "recalled",
    ]
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h) for h in headers])
    wb.save(dest)
    return dest
