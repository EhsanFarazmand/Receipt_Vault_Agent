---
name: price-protection
description: >
  Detect a qualifying price drop within a merchant's price-protection window and
  draft a price-adjustment claim. Trigger when a still-in-window item's current
  price is below the paid price. TIER: Draft-Only (produces a claim; never sends).
tier: draft-only
---

# Price Protection

Some merchants/cards refund the difference if an item's price drops within a
protection window after purchase.

## Procedure
1. Confirm the item is inside its price-protection window
   (`purchase_date + price_protection_days >= today`). See
   `../return-policy/policies/policies.md` for per-merchant windows.
2. Compare the current observed price to the paid `total`. A drop qualifies only
   if `current_price < total`; the delta is `total - current_price`.
3. If it qualifies, raise a `price-drop` event with the delta.

## Drafting a claim (Draft-Only)
Draft a concise price-adjustment request to the merchant referencing the item,
the paid price, the current price, and the delta. **Never send** — surface the
Vibe Diff for human approval. Lead the user message with the quantified save
(e.g. "The monitor dropped $40, inside the window — draft ready").
