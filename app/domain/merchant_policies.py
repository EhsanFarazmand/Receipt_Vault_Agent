"""Per-merchant return & price-protection policy knowledge base.

This is the code-side mirror of the ``return-policy`` skill's ``policies/`` resource
(course: *Agent Skills — progressive disclosure*). Keeping it as typed data (not
free text) lets the Watchdog compute exact windows deterministically, while the skill
gives the LLM the same knowledge for natural-language reasoning.

All figures are illustrative defaults for the demo; a production build would keep
this table versioned and cite each merchant's published policy.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MerchantPolicy:
    """Return / price-protection terms for one merchant."""

    name: str
    return_window_days: int
    price_protection_days: int  # 0 if the merchant offers none
    notes: str = ""


# Keyed by lowercased merchant name for case-insensitive lookup.
_POLICIES: dict[str, MerchantPolicy] = {
    "target": MerchantPolicy("Target", 90, 14, "Most items 90d; some electronics 30d."),
    "costco": MerchantPolicy("Costco", 365, 30, "Very generous; most items no deadline, electronics 90d."),
    "apple": MerchantPolicy("Apple", 14, 14, "Standard 14-day return and price match."),
    "amazon": MerchantPolicy("Amazon", 30, 7, "30-day returns; limited price-protection."),
    "best buy": MerchantPolicy("Best Buy", 15, 15, "15-day standard; longer for members."),
    "walmart": MerchantPolicy("Walmart", 90, 0, "90-day returns; no formal price-protection."),
    "home depot": MerchantPolicy("Home Depot", 90, 0, "90-day returns on most items."),
}

# Fallback used when a merchant is unknown — conservative so the Watchdog never
# over-promises a return window that may not exist.
DEFAULT_POLICY = MerchantPolicy("Unknown", 30, 0, "Default: assume a 30-day window, no price-protection.")


def get_policy(merchant: str) -> MerchantPolicy:
    """Return the policy for ``merchant`` (case-insensitive), or a safe default."""
    return _POLICIES.get((merchant or "").strip().lower(), DEFAULT_POLICY)


def known_merchants() -> list[str]:
    """Sorted list of merchants with an explicit policy (used by the skill/tests)."""
    return sorted(p.name for p in _POLICIES.values())
