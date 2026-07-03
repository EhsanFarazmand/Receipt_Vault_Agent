# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""The local SQLite ledger.

Uses only the Python standard library (`sqlite3`) — no ORM, no extra
dependency, which keeps the supply-chain surface (slopsquatting risk) minimal.
The ledger lives on the user's machine and is git-ignored: financial history is
never uploaded or tracked in the repo.

`upsert_entry` deduplicates on (vendor, purchase_date, total) so re-dropping the
same receipt photo does not create a second row — the Ledger agent's job.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS receipts (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor                TEXT NOT NULL,
    purchase_date         TEXT NOT NULL,          -- ISO date
    total                 REAL NOT NULL,
    currency              TEXT DEFAULT 'USD',
    item                  TEXT,                    -- primary item description
    items_json            TEXT DEFAULT '[]',       -- all line items
    last4                 TEXT,                    -- masked payment last-4 only
    category              TEXT,
    returnable            INTEGER DEFAULT 0,       -- 0/1
    return_policy_days    INTEGER DEFAULT 0,
    price_protection_days INTEGER DEFAULT 0,
    warranty_months       INTEGER DEFAULT 0,
    source_file           TEXT,
    status                TEXT DEFAULT 'open',
    created_at            TEXT DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_dedupe
    ON receipts (vendor, purchase_date, total);
"""

_COLUMNS = [
    "vendor", "purchase_date", "total", "currency", "item", "items_json",
    "last4", "category", "returnable", "return_policy_days",
    "price_protection_days", "warranty_months", "source_file", "status",
]


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    try:
        d["items"] = json.loads(d.pop("items_json", "[]") or "[]")
    except json.JSONDecodeError:
        d["items"] = []
    d["returnable"] = bool(d.get("returnable"))
    return d


def upsert_entry(entry: dict) -> dict:
    """Insert or update a ledger row, deduping on (vendor, date, total)."""
    values = {c: entry.get(c) for c in _COLUMNS}
    values["items_json"] = json.dumps(entry.get("items", []))
    values["returnable"] = 1 if entry.get("returnable") else 0
    # Default status explicitly: passing None here would store SQL NULL and
    # bypass the column's DEFAULT 'open', hiding the row from the daily sweep.
    values["status"] = entry.get("status") or "open"
    values["currency"] = entry.get("currency") or "USD"
    with _conn() as conn:
        cols = ", ".join(_COLUMNS)
        placeholders = ", ".join(f":{c}" for c in _COLUMNS)
        updates = ", ".join(f"{c}=excluded.{c}" for c in _COLUMNS if c != "vendor")
        conn.execute(
            f"INSERT INTO receipts ({cols}) VALUES ({placeholders}) "
            f"ON CONFLICT(vendor, purchase_date, total) DO UPDATE SET {updates}",
            values,
        )
        row = conn.execute(
            "SELECT * FROM receipts WHERE vendor=:vendor AND purchase_date=:purchase_date "
            "AND total=:total",
            values,
        ).fetchone()
    return _row_to_dict(row)


def get_entry(item_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE id=?", (item_id,)).fetchone()
    return _row_to_dict(row) if row else None


def all_open_entries() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM receipts WHERE status='open' ORDER BY purchase_date"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def query(sql_where: str, params: tuple = ()) -> list[dict]:
    """Run a read-only SELECT with a caller-supplied WHERE/aggregate clause.

    Only SELECT statements are permitted; anything else is rejected. This is the
    structural guardrail behind the natural-language `query_ledger` tool.
    """
    stmt = f"SELECT {sql_where}" if not sql_where.lstrip().upper().startswith("SELECT") \
        else sql_where
    if not stmt.lstrip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are permitted against the ledger.")
    with _conn() as conn:
        rows = conn.execute(stmt, params).fetchall()
    return [dict(r) for r in rows]
