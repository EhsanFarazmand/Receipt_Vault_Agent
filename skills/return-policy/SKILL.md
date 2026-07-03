---
name: return-policy
description: >
  Determine the return window (in days) for a purchase from its merchant and
  date, and whether an item is still returnable today. Trigger when computing a
  return deadline or drafting a return request. Loads the per-merchant policy
  table only when needed. TIER: Draft-Only (produces a claim; never sends).
tier: draft-only
---

# Return Policy

Given a `vendor` and `purchase_date`, determine days-left on the return window.

## Procedure
1. Look up the merchant in the policy table (`policies/policies.md`). If the
   merchant is not listed, use the conservative default of **30 days**.
2. `return_deadline = purchase_date + policy_days`.
3. `days_left = return_deadline - today`. If `days_left < 0`, the window is
   **closed** — do not raise a return action (no nagging).
4. An item must be marked `returnable` and unused to qualify.

## Drafting a return request (Draft-Only)
Produce a short, polite request addressed to the merchant's support address,
referencing the item and receipt. **Never send** — hand the draft to the human
via the Vibe Diff. The bulky per-merchant details live in `policies/policies.md`
(progressive disclosure: this body stays small; the table loads on demand).
