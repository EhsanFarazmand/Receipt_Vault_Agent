"""Deadline math for the Watchdog — the agentic core, made deterministic.

Given a ledger item and a reference date ("today"), compute days-left on the return
and price-protection windows and on any warranty, then decide whether a configurable
threshold has been crossed (course concept CR3: *decision threshold*). Crossing a
threshold raises a structured :class:`ActionEvent`.

Pure functions, no LLM: the same ledger + the same 'today' always produce the same
events. This is what makes the "day 2" test reproducible and unit-testable — the
Watchdog does real work with no new input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app import config
from app.domain.merchant_policies import get_policy


@dataclass
class ActionEvent:
    """A structured event the Watchdog hands to the Action/Drafting agent."""

    kind: str  # "return-window-closing" | "price-drop" | "warranty-expiring" | "recall-match"
    item_id: str
    item: str
    merchant: str
    message: str  # human-facing summary, e.g. "You can still return the blender for 6 more days"
    days_left: int | None = None
    detail: dict = field(default_factory=dict)


def _days_between(start: date, end: date) -> int:
    """Whole days from ``start`` to ``end`` (negative if end is before start)."""
    return (end - start).days


def return_days_left(purchase_date: date, merchant: str, today: date) -> int:
    """Days remaining on the merchant's return window (negative once closed)."""
    policy = get_policy(merchant)
    deadline_day = _days_between(purchase_date, today)
    return policy.return_window_days - deadline_day


def price_protection_days_left(purchase_date: date, merchant: str, today: date) -> int:
    """Days remaining on the merchant's price-protection window (negative once closed)."""
    policy = get_policy(merchant)
    return policy.price_protection_days - _days_between(purchase_date, today)


def warranty_days_left(warranty_expires: date | None, today: date) -> int | None:
    """Days until warranty expiry, or ``None`` if the item has no tracked warranty."""
    if warranty_expires is None:
        return None
    return _days_between(today, warranty_expires)


def evaluate_item(item: dict, today: date) -> list[ActionEvent]:
    """Run every deadline check for a single ledger item and return raised events.

    ``item`` is a ledger row (see ``domain.ledger``). Expected keys:
      id, name, merchant, purchase_date (ISO str), total (float),
      returnable (bool), warranty_expires (ISO str | None),
      current_price (float | None), recalled (bool).

    Threshold logic (from ``config``):
      * return-window-closing — returnable AND 0 <= days_left <= RETURN_WINDOW_THRESHOLD_DAYS
      * price-drop            — returnable AND still in price-protection window AND
                                current_price is at least PRICE_DROP_MIN_DELTA below paid
      * warranty-expiring     — 0 <= warranty_days_left <= WARRANTY_THRESHOLD_DAYS
      * recall-match          — item flagged recalled by the recall feed
    """
    events: list[ActionEvent] = []
    name = item["name"]
    merchant = item["merchant"]
    item_id = str(item["id"])
    purchase_date = date.fromisoformat(item["purchase_date"])
    returnable = bool(item.get("returnable", False))

    # 1. Return window ------------------------------------------------------
    if returnable:
        rdl = return_days_left(purchase_date, merchant, today)
        if 0 <= rdl <= config.RETURN_WINDOW_THRESHOLD_DAYS:
            events.append(
                ActionEvent(
                    kind="return-window-closing",
                    item_id=item_id,
                    item=name,
                    merchant=merchant,
                    message=f"You can still return the {name} for {rdl} more day"
                    f"{'s' if rdl != 1 else ''}.",
                    days_left=rdl,
                    detail={"total": item.get("total")},
                )
            )

    # 2. Price-protection drop ---------------------------------------------
    current_price = item.get("current_price")
    total = item.get("total")
    if returnable and current_price is not None and total is not None:
        ppdl = price_protection_days_left(purchase_date, merchant, today)
        delta = round(float(total) - float(current_price), 2)
        if ppdl >= 0 and delta >= config.PRICE_DROP_MIN_DELTA:
            events.append(
                ActionEvent(
                    kind="price-drop",
                    item_id=item_id,
                    item=name,
                    merchant=merchant,
                    message=f"The {name} dropped ${delta:.2f} — within {merchant}'s "
                    f"price-protection window. Draft ready.",
                    days_left=ppdl,
                    detail={"paid": total, "now": current_price, "delta": delta},
                )
            )

    # 3. Warranty expiry ----------------------------------------------------
    warranty_expires = item.get("warranty_expires")
    if warranty_expires:
        wdl = warranty_days_left(date.fromisoformat(warranty_expires), today)
        if wdl is not None and 0 <= wdl <= config.WARRANTY_THRESHOLD_DAYS:
            events.append(
                ActionEvent(
                    kind="warranty-expiring",
                    item_id=item_id,
                    item=name,
                    merchant=merchant,
                    message=f"The {name}'s warranty expires in {wdl} day"
                    f"{'s' if wdl != 1 else ''}.",
                    days_left=wdl,
                )
            )

    # 4. Recall match -------------------------------------------------------
    if bool(item.get("recalled", False)):
        events.append(
            ActionEvent(
                kind="recall-match",
                item_id=item_id,
                item=name,
                merchant=merchant,
                message=f"The {name} was recalled — here's the claim, already drafted.",
            )
        )

    return events


def sweep(items: list[dict], today: date) -> list[ActionEvent]:
    """Evaluate every item and return all raised action events (the daily sweep)."""
    events: list[ActionEvent] = []
    for item in items:
        events.extend(evaluate_item(item, today))
    return events
