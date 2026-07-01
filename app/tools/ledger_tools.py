"""Ledger tools: write/dedupe entries, answer NL queries, export the spreadsheet.

Tier: Action-Allowed but only against the LOCAL ledger file. The Policy Server's
structural rule confines every write to the vault directory.
"""

from __future__ import annotations

from app.domain import ledger


def write_ledger(
    name: str,
    merchant: str,
    purchase_date: str,
    total: float,
    category: str,
    last4: str,
    returnable: bool,
    warranty_expires: str,
) -> dict:
    """Insert or update a receipt in the local ledger (dedupes on natural key).

    Args:
        name: Item / short description.
        merchant: Merchant name.
        purchase_date: ISO date (YYYY-MM-DD).
        total: Purchase total.
        category: Category label (e.g. appliance, electronics, consumable).
        last4: Payment card last 4 digits, or empty string if unknown.
        returnable: Whether the item is returnable.
        warranty_expires: ISO date the warranty expires, or empty string if none.

    Returns:
        dict with 'status' and 'entry' (the stored row including its id).
    """
    entry = {
        "name": name,
        "merchant": merchant,
        "purchase_date": purchase_date,
        "total": total,
        "category": category,
        "last4": last4 or None,
        "returnable": returnable,
        "warranty_expires": warranty_expires or None,
    }
    stored = ledger.upsert_receipt(entry)
    return {"status": "success", "entry": stored}


def query_ledger(nl_query: str) -> dict:
    """Answer a simple natural-language question over the ledger.

    Supports category-spend questions ("how much did I spend on appliances?") and a
    plain listing. For anything richer, returns all rows for the agent to reason over.

    Args:
        nl_query: The user's natural-language question about their receipts.

    Returns:
        dict with 'status', 'answer' (text), and 'rows' (matching ledger rows).
    """
    low = nl_query.lower()
    known_categories = ("appliance", "electronics", "furniture", "consumable", "general")
    for cat in known_categories:
        if cat in low:
            total = ledger.query_category_total(cat)
            return {
                "status": "success",
                "answer": f"You spent ${total:.2f} on {cat} items.",
                "rows": [r for r in ledger.all_receipts() if r["category"].lower() == cat],
            }
    rows = ledger.all_receipts()
    return {
        "status": "success",
        "answer": f"You have {len(rows)} receipts on file.",
        "rows": rows,
    }


def export_ledger_xlsx(path: str) -> dict:
    """Export the ledger to a human-friendly .xlsx spreadsheet inside the vault.

    Args:
        path: Destination .xlsx path (must be inside the vault directory).

    Returns:
        dict with 'status' and 'dest' (the written spreadsheet path).
    """
    from pathlib import Path

    dest = ledger.export_xlsx(Path(path).expanduser())
    return {"status": "success", "dest": str(dest)}
