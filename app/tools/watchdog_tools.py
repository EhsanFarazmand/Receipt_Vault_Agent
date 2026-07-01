"""Watchdog tools — the agentic core: window math, recall feed, price feed, sweep.

Tier: Read-only. The Watchdog never acts; it raises structured action events for the
Action/Drafting agent. This is the "day 2" behaviour (course CR3): with no new input,
the sweep still counts down every window and escalates what needs attention today.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date

from app.domain import ledger, windows

# A tiny illustrative recall feed standing in for a real source (e.g. CPSC's API).
# Maps a lowercased keyword found in an item name to a recall notice.
_RECALL_FEED: dict[str, str] = {
    "headphone": "CPSC-2026-1187: battery overheating risk; free replacement offered.",
    "space heater": "CPSC-2026-0421: fire hazard; stop use and claim refund.",
}


def _today(reference_date: str) -> date:
    """Parse an ISO reference date, or use the real today if empty (daily run)."""
    return date.fromisoformat(reference_date) if reference_date else date.today()


def _get_item(item_id: str) -> dict | None:
    for row in ledger.all_receipts():
        if str(row["id"]) == str(item_id):
            return row
    return None


def compute_windows(item_id: str, reference_date: str) -> dict:
    """Compute days-left on return, price-protection, and warranty for one item.

    Args:
        item_id: The ledger id of the item to evaluate.
        reference_date: ISO date (YYYY-MM-DD) to compute against, or empty for today.

    Returns:
        dict with 'status' and 'windows' = {return_days_left,
        price_protection_days_left, warranty_days_left}.
    """
    item = _get_item(item_id)
    if item is None:
        return {"status": "error", "error": f"no ledger item with id {item_id}"}
    today = _today(reference_date)
    pdate = date.fromisoformat(item["purchase_date"])
    warranty = item.get("warranty_expires")
    return {
        "status": "success",
        "windows": {
            "return_days_left": windows.return_days_left(pdate, item["merchant"], today),
            "price_protection_days_left": windows.price_protection_days_left(
                pdate, item["merchant"], today
            ),
            "warranty_days_left": windows.warranty_days_left(
                date.fromisoformat(warranty) if warranty else None, today
            ),
        },
    }


def check_recalls(item: str) -> dict:
    """Poll the recall feed for a match against an item name.

    Args:
        item: The item name to check against the recall feed.

    Returns:
        dict with 'status', 'recalled' (bool), and 'notice' (text if matched).
    """
    low = (item or "").lower()
    for keyword, notice in _RECALL_FEED.items():
        if keyword in low:
            return {"status": "success", "recalled": True, "notice": notice}
    return {"status": "success", "recalled": False, "notice": ""}


def record_price_observation(item_id: str, current_price: float) -> dict:
    """Feed a newly observed market price for an item into the ledger (price feed).

    Args:
        item_id: The ledger id of the item.
        current_price: The latest observed price for the same item.

    Returns:
        dict with 'status' and the updated 'entry'.
    """
    item = _get_item(item_id)
    if item is None:
        return {"status": "error", "error": f"no ledger item with id {item_id}"}
    item["current_price"] = current_price
    stored = ledger.upsert_receipt(item)
    return {"status": "success", "entry": stored}


def run_daily_sweep(reference_date: str) -> dict:
    """Run the daily watchdog sweep over every open item and raise action events.

    For each still-watched item, applies the recall feed, then the deadline/price/
    warranty thresholds. This is the standing watch that makes Receipt Vault an agent.

    Args:
        reference_date: ISO date (YYYY-MM-DD) to sweep against, or empty for today.

    Returns:
        dict with 'status', 'count', and 'events' (list of raised action events).
    """
    today = _today(reference_date)
    items = ledger.open_items()

    # Refresh recall flags from the feed before evaluating (read-only enrichment).
    for item in items:
        recall = check_recalls(item["name"])
        item["recalled"] = recall["recalled"]

    events = windows.sweep(items, today)
    return {
        "status": "success",
        "count": len(events),
        "events": [asdict(e) for e in events],
    }
