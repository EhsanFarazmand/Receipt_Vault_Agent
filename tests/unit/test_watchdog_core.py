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
"""Unit tests for the agentic core — mirror the Gherkin watchdog scenarios.

Pure logic, no LLM. (ADK guidance: do not assert on LLM response content in
pytest — that belongs in eval. Deterministic window math belongs here.)
"""
from datetime import date, timedelta

from app.watchdog_core import add_months, compute_windows, evaluate_entry

AS_OF = date(2026, 7, 2)


def _entry(**over):
    base = {
        "id": 1, "vendor": "Target", "item": "blender", "total": 79.99,
        "returnable": True, "return_policy_days": 90, "price_protection_days": 14,
        "warranty_months": 0,
        "purchase_date": (AS_OF - timedelta(days=84)).isoformat(),
    }
    base.update(over)
    return base


def test_return_window_closing_is_raised_in_time():
    # Scenario: Surface a closing return window in time (84d ago, 90d policy -> 6 left).
    events = evaluate_entry(_entry(), AS_OF, 7, 30, current_price=None, recall_hit=False)
    kinds = [e.kind for e in events]
    assert "return-window-closing" in kinds
    ev = next(e for e in events if e.kind == "return-window-closing")
    assert "6 more day" in ev.message


def test_no_nag_after_window_closes():
    # Scenario: Do not nag on items past their window (120d ago, 90d policy).
    entry = _entry(purchase_date=(AS_OF - timedelta(days=120)).isoformat())
    events = evaluate_entry(entry, AS_OF, 7, 30, current_price=None, recall_hit=False)
    assert not any(e.kind == "return-window-closing" for e in events)


def test_qualifying_price_drop_delta():
    # Scenario: Detect a qualifying price drop (299 -> 259 within 30d window).
    entry = _entry(item="4k monitor", vendor="Amazon", total=299.00,
                   return_policy_days=30, price_protection_days=30,
                   purchase_date=(AS_OF - timedelta(days=11)).isoformat())
    events = evaluate_entry(entry, AS_OF, 7, 30, current_price=259.00, recall_hit=False)
    drop = next(e for e in events if e.kind == "price-drop")
    assert drop.detail["delta"] == 40.0


def test_no_price_drop_after_protection_window_closes():
    entry = _entry(item="4k monitor", total=299.00, price_protection_days=7,
                   purchase_date=(AS_OF - timedelta(days=30)).isoformat())
    events = evaluate_entry(entry, AS_OF, 7, 30, current_price=259.00, recall_hit=False)
    assert not any(e.kind == "price-drop" for e in events)


def test_recall_match_is_always_raised():
    events = evaluate_entry(_entry(item="acme headphones"), AS_OF, 7, 30,
                            current_price=None, recall_hit=True)
    assert any(e.kind == "recall-match" for e in events)


def test_add_months_clamps_day():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 12, 15), 1) == date(2027, 1, 15)


def test_windows_open_flags():
    w = compute_windows(_entry(), AS_OF)
    assert w.return_open is True
    assert w.return_days_left == 6
