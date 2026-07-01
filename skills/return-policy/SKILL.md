---
name: return-policy
description: >
  Determine the return window for a purchase from its merchant and date, and decide
  whether a return is still possible. Trigger when computing days-left on a return
  window or drafting a return request.
tier: draft-only
---

# Return Policy

**Tier: Draft-Only.** Produce a return window or a return-request draft; never send.

## When this fires
The Watchdog needs a return deadline for an item, or the Action agent is drafting a
return request and needs to confirm the item is still in-window.

## Procedure
1. Identify the **merchant** and the **purchase date** (ISO).
2. Look up the merchant's return window in `policies/merchant_policies.md`
   (bulky resource — load it only when you reach this step: *progressive disclosure*).
3. `days_left = return_window_days - (today - purchase_date)`.
4. If `days_left >= 0` the item is still returnable; if it is `<= threshold` (default 7)
   the Watchdog should raise `return-window-closing`.
5. Unknown merchant → assume the conservative default (30 days, no price-protection).

## Do NOT
- Do not invent a policy for an unlisted merchant — use the default and say so.
- Do not draft a return for an item already past its window (no nagging).

## Resources (progressive disclosure)
- `policies/merchant_policies.md` — the per-merchant table (loaded on demand).
- Code mirror: `../../app/domain/merchant_policies.py` and `../../app/domain/windows.py`.
