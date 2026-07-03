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
"""The agentic core, as *pure* functions.

This module holds the deadline math that makes Receipt Vault an agent rather
than a skill: for any ledger entry and any reference date it computes days-left
on the return / price-protection / warranty windows and decides which threshold
crossings deserve an action event today.

It deliberately contains **no ADK, no LLM, no I/O** so the "day 2" behaviour
(rule CR3) is deterministic and unit-testable with a fixed `as_of` date. The
Watchdog agent's tools are thin wrappers over these functions.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date


def add_months(d: date, months: int) -> date:
    """Add whole calendar months, clamping the day to the target month length.

    e.g. Jan 31 + 1 month -> Feb 28/29. Avoids a python-dateutil dependency
    (fewer deps = smaller supply-chain / slopsquatting surface).
    """
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@dataclass
class Windows:
    """All deadline countdowns for a single item, as of a reference date."""

    return_deadline: date | None = None
    return_days_left: int | None = None
    return_open: bool = False

    price_protection_deadline: date | None = None
    price_protection_days_left: int | None = None
    price_protection_open: bool = False

    warranty_expiry: date | None = None
    warranty_days_left: int | None = None
    warranty_active: bool = False


def compute_windows(entry: dict, as_of: date) -> Windows:
    """Compute every deadline countdown for one ledger entry.

    `entry` uses days/months policy fields captured at intake:
      purchase_date (ISO str), returnable (bool), return_policy_days (int),
      price_protection_days (int), warranty_months (int).
    """
    purchase = date.fromisoformat(entry["purchase_date"])
    w = Windows()

    return_days = int(entry.get("return_policy_days") or 0)
    if return_days > 0:
        w.return_deadline = date.fromordinal(purchase.toordinal() + return_days)
        w.return_days_left = (w.return_deadline - as_of).days
        # A window is "open" only if the item is returnable AND today is on or
        # before the deadline. Past-deadline items are closed -> no nagging.
        w.return_open = bool(entry.get("returnable")) and w.return_days_left >= 0

    pp_days = int(entry.get("price_protection_days") or 0)
    if pp_days > 0:
        w.price_protection_deadline = date.fromordinal(purchase.toordinal() + pp_days)
        w.price_protection_days_left = (w.price_protection_deadline - as_of).days
        w.price_protection_open = w.price_protection_days_left >= 0

    warranty_months = int(entry.get("warranty_months") or 0)
    if warranty_months > 0:
        w.warranty_expiry = add_months(purchase, warranty_months)
        w.warranty_days_left = (w.warranty_expiry - as_of).days
        w.warranty_active = w.warranty_days_left >= 0

    return w


@dataclass
class ActionEvent:
    """A threshold crossing worth surfacing to the user today."""

    kind: str  # return-window-closing | price-drop | warranty-expiring | recall-match
    item_id: str
    vendor: str
    item: str
    message: str
    detail: dict = field(default_factory=dict)


def evaluate_entry(
    entry: dict,
    as_of: date,
    return_alert_days: int,
    warranty_alert_days: int,
    current_price: float | None,
    recall_hit: bool,
) -> list[ActionEvent]:
    """Decide which action events a single item warrants as of `as_of`.

    This is the heart of the daily sweep. It fires ONLY on a threshold crossing,
    never on raw data — the difference between an agent that acts and a report
    that lists. Recall and price signals are passed in (they come from feeds) so
    this function stays pure and deterministic.
    """
    events: list[ActionEvent] = []
    w = compute_windows(entry, as_of)
    item_id = str(entry.get("id"))
    vendor = entry.get("vendor", "the merchant")
    item = entry.get("item") or (entry.get("items") or ["item"])[0]

    # 1) Return window closing — open, and within the alert threshold.
    if w.return_open and 0 <= (w.return_days_left or 0) <= return_alert_days:
        events.append(
            ActionEvent(
                kind="return-window-closing",
                item_id=item_id,
                vendor=vendor,
                item=item,
                message=(
                    f"You can still return the {item} for "
                    f"{w.return_days_left} more day(s)."
                ),
                detail={"days_left": w.return_days_left,
                        "deadline": w.return_deadline.isoformat()},
            )
        )

    # 2) Price drop — a qualifying drop while the price-protection window is open.
    if w.price_protection_open and current_price is not None:
        original = float(entry.get("total") or 0.0)
        if current_price < original:
            delta = round(original - current_price, 2)
            events.append(
                ActionEvent(
                    kind="price-drop",
                    item_id=item_id,
                    vendor=vendor,
                    item=item,
                    message=(
                        f"The {item} dropped ${delta:.2f} "
                        f"(now ${current_price:.2f}), inside the "
                        f"price-protection window."
                    ),
                    detail={"delta": delta, "current_price": current_price,
                            "original_price": original},
                )
            )

    # 3) Warranty expiring — active and within the alert threshold.
    if w.warranty_active and 0 <= (w.warranty_days_left or 0) <= warranty_alert_days:
        events.append(
            ActionEvent(
                kind="warranty-expiring",
                item_id=item_id,
                vendor=vendor,
                item=item,
                message=(
                    f"The {item} warranty expires in "
                    f"{w.warranty_days_left} day(s)."
                ),
                detail={"days_left": w.warranty_days_left,
                        "expiry": w.warranty_expiry.isoformat()},
            )
        )

    # 4) Recall match — a safety signal, always worth surfacing.
    if recall_hit:
        events.append(
            ActionEvent(
                kind="recall-match",
                item_id=item_id,
                vendor=vendor,
                item=item,
                message=f"The {item} was recalled — a claim can be drafted.",
                detail={"source": "recall-feed"},
            )
        )

    return events
