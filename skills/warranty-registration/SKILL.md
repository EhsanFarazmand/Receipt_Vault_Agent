---
name: warranty-registration
description: >
  Track warranty expiry on owned items and draft a registration or claim before
  it lapses. Trigger when a warranty is within the alert threshold or an owned
  item is failing. TIER: Draft-Only (produces a draft; never sends).
tier: draft-only
---

# Warranty Registration

## Procedure
1. Compute `warranty_expiry = purchase_date + warranty_months`.
2. If `0 <= (warranty_expiry - today) <= warranty_alert_days`, raise a
   `warranty-expiring` event.
3. For a failing item still under warranty, prefer a **claim**; for a healthy
   item nearing the *registration* deadline, prefer a **registration**.

## What voids a warranty (check before drafting)
- Missing proof of purchase → the vault already holds the filed receipt; attach it.
- Unauthorized repair or physical/water damage (unless accidental-damage cover).
- Lapsed **registration** window on brands that require it.

## Drafting (Draft-Only)
Draft the registration/claim to the manufacturer or merchant, attaching the
filed receipt. **Never send** — route via the Vibe Diff for human approval.
