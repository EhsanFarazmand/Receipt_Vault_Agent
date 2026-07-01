"""Watchdog window-math tests — the agentic core.

Enforces `return_window.feature` and `price_protection.feature` deterministically.
"""

from datetime import date, timedelta

from app.domain import windows
from app.domain.ledger import upsert_receipt


def _add(**over) -> dict:
    base = {
        "name": "blender",
        "merchant": "Target",
        "purchase_date": "2026-04-01",
        "total": 79.99,
        "category": "appliance",
        "returnable": True,
    }
    base.update(over)
    return upsert_receipt(base)


def test_return_window_closing_fires_at_six_days():
    item = _add()
    today = date(2026, 4, 1) + timedelta(days=84)  # Target 90d → 6 left
    events = windows.evaluate_item(item, today)
    closing = [e for e in events if e.kind == "return-window-closing"]
    assert len(closing) == 1
    assert closing[0].days_left == 6
    assert "6 more days" in closing[0].message


def test_no_nag_past_window():
    item = _add()
    today = date(2026, 4, 1) + timedelta(days=120)  # past 90d window
    events = windows.evaluate_item(item, today)
    assert not [e for e in events if e.kind == "return-window-closing"]


def test_price_drop_within_protection_window():
    item = _add(name="monitor", total=299.00, category="electronics", current_price=259.00)
    today = date(2026, 4, 1) + timedelta(days=11)  # Target price-protection 14d
    events = windows.evaluate_item(item, today)
    drop = [e for e in events if e.kind == "price-drop"]
    assert len(drop) == 1
    assert abs(drop[0].detail["delta"] - 40.00) < 1e-6


def test_warranty_expiring_fires_within_threshold():
    expires = (date(2026, 4, 1) + timedelta(days=100)).isoformat()
    item = _add(name="laptop", category="electronics", warranty_expires=expires)
    today = date(2026, 4, 1) + timedelta(days=80)  # 20 days to expiry, threshold 30
    events = windows.evaluate_item(item, today)
    assert [e for e in events if e.kind == "warranty-expiring"]


def test_recalled_item_raises_recall_event():
    item = _add(name="headphones", category="electronics")
    item["recalled"] = True
    events = windows.evaluate_item(item, date(2026, 4, 10))
    assert [e for e in events if e.kind == "recall-match"]
