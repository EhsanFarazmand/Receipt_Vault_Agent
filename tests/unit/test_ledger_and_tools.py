"""Ledger + tool-contract tests.

These check code correctness (dedupe, tool return shapes) — NOT LLM behaviour, which
belongs in `agents-cli eval`.
"""

from datetime import date, timedelta

from app.domain import ledger
from app.tools import intake_tools, ledger_tools, watchdog_tools


def test_ledger_dedupes_on_natural_key():
    e1 = ledger.upsert_receipt(
        {"name": "blender", "merchant": "Target", "purchase_date": "2026-04-01", "total": 79.99}
    )
    e2 = ledger.upsert_receipt(
        {"name": "blender", "merchant": "Target", "purchase_date": "2026-04-01", "total": 79.99}
    )
    assert e1["id"] == e2["id"]
    assert len(ledger.all_receipts()) == 1


def test_open_items_excludes_non_returnable_consumable():
    ledger.upsert_receipt(
        {"name": "coffee", "merchant": "Target", "purchase_date": "2026-04-01",
         "total": 4.99, "returnable": False}
    )
    assert ledger.open_items() == []


def test_query_ledger_category_total():
    ledger_tools.write_ledger("blender", "Target", "2026-04-01", 79.99, "appliance", "", True, "")
    ledger_tools.write_ledger("microwave", "Target", "2026-04-02", 120.00, "appliance", "", True, "")
    res = ledger_tools.query_ledger("how much on appliances?")
    assert res["status"] == "success"
    assert "199.99" in res["answer"]


def test_extract_fields_parses_sanitized_text():
    text = "Target\nDate: 2026-06-14\nBlender 79.99\nTotal: 79.99\n[CARD ****1234]"
    res = intake_tools.extract_fields(text)
    f = res["fields"]
    assert f["vendor"] == "Target"
    assert f["purchase_date"] == "2026-06-14"
    assert f["total"] == 79.99
    assert f["last4"] == "1234"
    assert f["category"] == "appliance"
    assert f["returnable"] is True


def test_run_daily_sweep_returns_events():
    # Blender 84 days ago → within 7-day return threshold at Target.
    pdate = (date.today() - timedelta(days=84)).isoformat()
    ledger_tools.write_ledger("blender", "Target", pdate, 79.99, "appliance", "", True, "")
    res = watchdog_tools.run_daily_sweep("")  # empty → today
    assert res["status"] == "success"
    kinds = [e["kind"] for e in res["events"]]
    assert "return-window-closing" in kinds


def test_check_recalls_matches_feed():
    assert watchdog_tools.check_recalls("Sony headphones")["recalled"] is True
    assert watchdog_tools.check_recalls("blender")["recalled"] is False
