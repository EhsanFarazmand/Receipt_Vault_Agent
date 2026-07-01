---
name: price-protection
description: >
  Detect a qualifying price drop within a merchant's price-protection window and draft
  a price-adjustment claim. Trigger when a price feed reports a lower price on a
  still-owned, still-returnable item.
tier: draft-only
---

# Price Protection

**Tier: Draft-Only.** Detect the qualifying drop and draft the claim; never send.

## When this fires
A price observation for an item you already own comes in lower than what was paid, and
the item is still inside the merchant's price-protection window.

## Procedure
1. Confirm the merchant offers price-protection and get its window from the
   `return-policy` skill's `policies/merchant_policies.md`.
2. `days_left = price_protection_days - (today - purchase_date)`. Must be `>= 0`.
3. `delta = paid - current_price`. Must clear the minimum delta (default $5.00) to be
   worth a claim.
4. If both hold, raise `price-drop` with the delta and draft a price-adjustment message
   to the merchant, attaching the receipt.

## Do NOT
- Do not claim on an item outside the price-protection window.
- Do not claim on tiny deltas below the configured minimum (avoid spammy claims).

## Resources
Code mirror: `../../app/domain/windows.py` (`price_protection_days_left`) and
`../../app/tools/action_tools.py` (`draft_action` → `price-drop` template).
