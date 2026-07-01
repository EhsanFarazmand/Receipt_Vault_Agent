---
name: warranty-registration
description: >
  Register a warranty or draft a warranty claim before it lapses. Trigger when an
  owned item's warranty is within the expiry threshold, or the user reports a fault on
  a covered item.
tier: draft-only
---

# Warranty Registration

**Tier: Draft-Only.** Draft the registration or claim; never send.

## When this fires
The Watchdog reports a warranty expiring within the threshold (default 30 days), or the
user says a covered item is malfunctioning.

## Procedure
1. Confirm the item's `warranty_expires` date from the ledger.
2. `days_left = warranty_expires - today`. If `0 <= days_left <= threshold`, raise
   `warranty-expiring`.
3. Draft either:
   - a **registration** message (if never registered), or
   - a **claim** message (if the item is faulty), attaching proof of purchase.
4. Note anything that could **void** the warranty (missing registration, unauthorized
   repair, water damage) so the user can act before filing.

## Do NOT
- Do not draft a claim for an item already out of warranty.
- Do not omit the proof-of-purchase reference — most claims require it.

## Resources
Code mirror: `../../app/domain/windows.py` (`warranty_days_left`) and
`../../app/tools/action_tools.py` (`draft_action` → `warranty-expiring` template).
