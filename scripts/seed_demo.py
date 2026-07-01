"""Seed the ledger with the synthetic sample receipts for the demo / video.

Reads every file in ``sample_receipts/`` through the same intake path the agent uses
(OCR → sanitize → extract → ledger), so the demo ledger is populated deterministically
and the Watchdog has something to watch. Also stages a couple of items so the wow
moments fire on a fixed "today" you pass to scripts/daily_watchdog.py.

Usage:  uv run python scripts/seed_demo.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

# Make `app` importable when run directly (not via `uv run`).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.domain import ledger  # noqa: E402
from app.tools.intake_tools import extract_fields, ocr_receipt  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / "sample_receipts"


def main() -> int:
    ledger.init_db()
    count = 0
    for path in sorted(SAMPLES.glob("*.txt")):
        ocr = ocr_receipt(str(path))
        if ocr["status"] != "success":
            print(f"skip {path.name}: {ocr.get('error')}")
            continue
        fields = extract_fields(ocr["text"])["fields"]
        if not (fields["vendor"] and fields["purchase_date"] and fields["total"]):
            print(f"skip {path.name}: incomplete fields {fields}")
            continue
        ledger.upsert_receipt(
            {
                "name": _guess_item(path.stem),
                "merchant": fields["vendor"].title(),
                "purchase_date": fields["purchase_date"],
                "total": fields["total"],
                "category": fields["category"],
                "last4": fields["last4"],
                "returnable": fields["returnable"],
                "source_file": str(path),
            }
        )
        count += 1
        print(f"seeded {path.name}: {fields['vendor']} ${fields['total']}")

    # Stage the wow moments: a price drop on the monitor and a recall on the headphones.
    for row in ledger.all_receipts():
        if "monitor" in row["name"].lower():
            row["current_price"] = 259.00  # $40 drop inside price-protection window
            ledger.upsert_receipt(row)
        if "headphone" in row["name"].lower():
            row["warranty_expires"] = (date.today() + timedelta(days=20)).isoformat()
            ledger.upsert_receipt(row)

    print(f"\nSeeded {count} receipts. Run: uv run python scripts/daily_watchdog.py")
    return 0


def _guess_item(stem: str) -> str:
    """Derive a short item name from the sample filename (…_target_blender → blender)."""
    parts = stem.split("_")
    return parts[-1] if parts else stem


if __name__ == "__main__":
    raise SystemExit(main())
