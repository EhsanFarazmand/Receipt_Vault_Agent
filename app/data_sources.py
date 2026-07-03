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
"""Local, synthetic stand-ins for external feeds and merchant knowledge.

For the capstone these are deterministic local fixtures so the demo and the eval
suite are reproducible offline and contain no real PII. In production each would
be swapped for a real source (a CPSC recall API, a retailer price API) behind the
same function signature — the Watchdog tools would not change.

The per-merchant return-policy table also backs the `return-policy` SKILL: this
is the "resource" tier of that skill's progressive disclosure.
"""
from __future__ import annotations

# --- Per-merchant policy knowledge base (return / price-protection windows) ---
# Days. Sourced from public store policies; kept small and honest for the demo.
MERCHANT_POLICY: dict[str, dict] = {
    "Target": {"return_days": 90, "price_protection_days": 14, "domain": "target.com"},
    "Costco": {"return_days": 365, "price_protection_days": 30, "domain": "costco.com"},
    "Apple": {"return_days": 14, "price_protection_days": 14, "domain": "apple.com"},
    "Amazon": {"return_days": 30, "price_protection_days": 7, "domain": "amazon.com"},
    "Best Buy": {"return_days": 15, "price_protection_days": 15, "domain": "bestbuy.com"},
    "Walmart": {"return_days": 90, "price_protection_days": 0, "domain": "walmart.com"},
}
_DEFAULT_POLICY = {"return_days": 30, "price_protection_days": 0, "domain": ""}


def policy_for(vendor: str) -> dict:
    """Return the return/price-protection policy for a merchant (case-tolerant)."""
    for name, pol in MERCHANT_POLICY.items():
        if name.lower() == (vendor or "").strip().lower():
            return {**pol, "merchant": name}
    return {**_DEFAULT_POLICY, "merchant": vendor}


# --- Synthetic recall feed (stands in for a CPSC-style API) -----------------
# Substrings that, if present in an item description, count as a recall match.
_RECALLED_ITEMS = {"acme headphones", "solaris space heater", "nimbus baby monitor"}


def check_recall_feed(item: str) -> bool:
    """Return True if the item matches an entry in the (synthetic) recall feed."""
    needle = (item or "").strip().lower()
    return any(r in needle or needle in r for r in _RECALLED_ITEMS if needle)


# --- Synthetic price feed (stands in for a retailer price API) --------------
# Current observed price by item description; missing = no price signal.
_PRICE_FEED: dict[str, float] = {
    "blender": 61.99,          # was 79.99 -> qualifying drop
    "4k monitor": 259.00,      # was 299.00 -> qualifying drop
    "coffee maker": 49.99,     # unchanged
}


def current_price_for(item: str) -> float | None:
    """Return the latest observed price for an item, or None if not tracked."""
    return _PRICE_FEED.get((item or "").strip().lower())
