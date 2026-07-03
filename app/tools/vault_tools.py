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
"""Receipt Vault tools.

Each function is a small, typed, individually-permissioned capability — the
same surface the first-party MCP server exposes. Tool functions follow the ADK
rules: type hints, no default values, JSON-serialisable dict returns, and an
optional `tool_context` for state. The Policy Server (a before_tool_callback)
intercepts every one of these before it runs.
"""
from __future__ import annotations

import os
import re
import shutil
from datetime import date

from app.config import settings
from app.data_sources import check_recall_feed, current_price_for, policy_for
from app.ledger import db
from app.security.audit import audit
from app.security.sanitize import fence_untrusted, sanitize_receipt_text
from app.watchdog_core import compute_windows, evaluate_entry


def _today() -> date:
    """Reference 'today'. Overridable via env so demos/evals are reproducible."""
    override = os.getenv("RECEIPT_VAULT_TODAY")
    return date.fromisoformat(override) if override else date.today()


# --------------------------------------------------------------------------- #
# Intake & Extraction (Read / Draft tier)
# --------------------------------------------------------------------------- #
def scan_inbox(folder: str) -> dict:
    """List new receipt files waiting in a watched inbox folder.

    Args:
        folder: Path to the folder to scan for dropped receipts.

    Returns:
        dict with 'status' and 'files' (a list of absolute file paths).
    """
    root = settings.inbox if not folder or folder == "." else \
        __import__("pathlib").Path(folder).expanduser().resolve()
    if not root.exists():
        return {"status": "empty", "files": [], "folder": str(root)}
    files = [str(p) for p in sorted(root.iterdir())
             if p.is_file() and p.suffix.lower() in {".txt", ".pdf", ".png", ".jpg", ".jpeg"}]
    return {"status": "success", "files": files, "folder": str(root)}


def ocr_receipt(path: str) -> dict:
    """OCR a single receipt image/PDF and return its raw text (UNTRUSTED).

    The text is treated as untrusted data downstream. For the local prototype,
    plain-text fixtures are read directly; images/PDFs would run through an OCR
    engine inside an ephemeral sandbox in production.

    Args:
        path: Path to the receipt file to read.

    Returns:
        dict with 'status' and 'raw_text'.
    """
    from pathlib import Path
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return {"status": "error", "raw_text": "", "reason": f"No such file: {path}"}
    if p.suffix.lower() == ".txt":
        return {"status": "success", "raw_text": p.read_text(encoding="utf-8"),
                "path": str(p)}
    return {"status": "unsupported",
            "raw_text": "",
            "reason": "Image/PDF OCR runs in the sandbox; use .txt fixtures locally."}


def extract_fields(text: str) -> dict:
    """Sanitize untrusted receipt text and extract structured fields.

    Runs PII redaction + prompt-injection neutralisation FIRST, then a
    best-effort structured parse. Any injection attempt is flagged in the audit
    log and the text is returned fenced so it is handled as data, never as
    instructions.

    Args:
        text: Raw OCR text from a receipt.

    Returns:
        dict with 'status', 'fields', 'fenced_text', and 'sanitization'.
    """
    clean = sanitize_receipt_text(text)
    if clean.flagged:
        audit("sanitization_event", flags=clean.injection_flags,
              pii_masked=clean.pii_masked)

    body = clean.text
    vendor = _search(r"(?:vendor|store|merchant)\s*[:\-]?\s*(.+)", body) \
        or _match_known_merchant(body) \
        or _search(r"^([A-Z][A-Za-z' ]{2,})$", body)
    total = _search(r"(?:total|amount)\s*[:\-]?\s*\$?\s*([0-9]+(?:\.[0-9]{2})?)", body) \
        or _max_decimal(body)
    d = _search(r"(\d{4}-\d{2}-\d{2})", body)
    last4 = _search(r"(?:\*{2,}[- ]?){0,3}(\d{4})\b", body)
    item = _search(r"(?:item|product)\s*[:\-]?\s*(.+)", body)

    pol = policy_for(vendor or "")
    fields = {
        "vendor": (vendor or "Unknown").strip(),
        "purchase_date": d or _today().isoformat(),
        "total": float(total) if total else 0.0,
        "item": (item or "").strip(),
        "last4": last4,
        "category": _search(r"(?:category)\s*[:\-]?\s*(.+)", body) or "general",
        "returnable": True,
        "return_policy_days": pol["return_days"],
        "price_protection_days": pol["price_protection_days"],
        "warranty_months": int(_search(r"warranty\s*[:\-]?\s*(\d+)\s*mo", body) or 0),
    }
    return {"status": "success", "fields": fields,
            "fenced_text": fence_untrusted(body),
            "sanitization": {"pii_masked": clean.pii_masked,
                             "injection_flags": clean.injection_flags}}


def _search(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else None


def _match_known_merchant(text: str) -> str | None:
    """Fallback vendor parse for free-form (unlabeled) receipts: match a known
    merchant name anywhere in the text (case-insensitive)."""
    from app.data_sources import MERCHANT_POLICY
    low = (text or "").lower()
    for name in MERCHANT_POLICY:
        if name.lower() in low:
            return name
    return None


def _max_decimal(text: str) -> str | None:
    """Fallback total parse: the largest `NN.NN` amount in the text (the total is
    almost always the largest figure on a receipt)."""
    vals = re.findall(r"\b\d+\.\d{2}\b", text or "")
    return max(vals, key=float) if vals else None


# --------------------------------------------------------------------------- #
# Ledger (Action-local / Read tier)
# --------------------------------------------------------------------------- #
def _normalize_entry(entry: dict) -> dict:
    """Make a ledger entry robust to however the caller (Intake tool or the LLM
    directly) named its fields, and backfill what the Watchdog needs.

    - Accepts common key aliases (date->purchase_date, merchant->vendor, ...).
    - Coerces total to a float.
    - Defaults `returnable` to True.
    - Backfills the merchant's return / price-protection windows from the policy
      table when absent, so windows can be computed even if the row was written
      directly without going through `extract_fields`.
    """
    e = dict(entry or {})
    e["vendor"] = e.get("vendor") or e.get("merchant") or e.get("store")
    e["purchase_date"] = (
        e.get("purchase_date") or e.get("date") or e.get("purchased") or e.get("purchase")
    )
    if e.get("total") is None:
        e["total"] = e.get("amount") or e.get("price")
    try:
        if e.get("total") is not None:
            e["total"] = float(e["total"])
    except (TypeError, ValueError):
        e["total"] = None
    if not e.get("item"):
        items = e.get("items")
        e["item"] = (items[0] if isinstance(items, list) and items else e.get("product"))
    if e.get("returnable") is None:
        e["returnable"] = True

    pol = policy_for(e.get("vendor") or "")
    if not e.get("return_policy_days"):
        e["return_policy_days"] = pol["return_days"]
    if not e.get("price_protection_days"):
        e["price_protection_days"] = pol["price_protection_days"]
    return e


def write_ledger(entry: dict) -> dict:
    """Insert or update one receipt in the local ledger (dedupes automatically).

    Tolerant of field-name variations from the model (e.g. 'date' vs
    'purchase_date') and backfills the merchant's return / price-protection
    windows so the Watchdog can compute deadlines. Requires at least vendor,
    purchase_date, and total; returns a clear error (never a DB crash) if any
    are missing.

    Args:
        entry: Structured receipt fields to persist.

    Returns:
        dict with 'status' and the stored 'entry' (including its assigned id).
    """
    entry = _normalize_entry(entry)
    missing = [k for k in ("vendor", "purchase_date", "total") if not entry.get(k)]
    if missing:
        return {"status": "error",
                "reason": (f"Cannot record receipt — missing: {', '.join(missing)}. "
                           "Provide vendor, purchase_date (YYYY-MM-DD), and total.")}
    stored = db.upsert_entry(entry)
    audit("ledger_write", item_id=stored.get("id"), vendor=stored.get("vendor"))
    return {"status": "success", "entry": stored}


def file_source_document(path: str, entry: dict) -> dict:
    """Rename and file a source receipt into the vault taxonomy.

    Produces a name like `2026-06-14_Target_blender_79.99.pdf` and copies the
    source into the local vault. The Policy Server enforces the destination is
    local before this runs.

    Args:
        path: Current path of the source receipt file.
        entry: The extracted fields used to build the filename.

    Returns:
        dict with 'status' and the new vault 'dest' path.
    """
    from pathlib import Path
    src = Path(path).expanduser().resolve()
    settings.store.mkdir(parents=True, exist_ok=True)
    slug_item = re.sub(r"[^A-Za-z0-9]+", "-", (entry.get("item") or "receipt")).strip("-")
    name = (f"{entry.get('purchase_date', 'undated')}_"
            f"{re.sub(r'[^A-Za-z0-9]+', '', entry.get('vendor', 'unknown'))}_"
            f"{slug_item}_{entry.get('total', 0)}{src.suffix or '.txt'}")
    dest = settings.store / name
    if src.exists():
        shutil.copy2(src, dest)
    audit("source_filed", src=str(src), dest=str(dest))
    return {"status": "success", "dest": str(dest)}


def query_ledger(nl_query: str) -> dict:
    """Answer a question about spending from the local ledger.

    Understands a few common intents (spend totals, counts, category filters)
    over a read-only SELECT. Anything it cannot map returns the open entries so
    the agent can reason over them.

    Args:
        nl_query: A natural-language question, e.g. 'how much did I spend at Target?'.

    Returns:
        dict with 'status' and 'result'.
    """
    q = nl_query.lower()
    try:
        if "how much" in q or "total" in q or "spend" in q or "spent" in q:
            vendor = _match_vendor(q)
            if vendor:
                rows = db.query(
                    "SELECT COALESCE(SUM(total),0) AS total_spent, COUNT(*) AS n "
                    "FROM receipts WHERE lower(vendor)=?",
                    (vendor.lower(),),
                )
            else:
                rows = db.query(
                    "SELECT COALESCE(SUM(total),0) AS total_spent, COUNT(*) AS n "
                    "FROM receipts",
                )
            return {"status": "success", "result": rows}
        if "how many" in q or "count" in q:
            rows = db.query("SELECT COUNT(*) AS n FROM receipts")
            return {"status": "success", "result": rows}
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error", "reason": str(exc)}
    return {"status": "success", "result": db.all_open_entries()}


def _match_vendor(q: str) -> str | None:
    from app.data_sources import MERCHANT_POLICY
    for name in MERCHANT_POLICY:
        if name.lower() in q:
            return name
    return None


# --------------------------------------------------------------------------- #
# Watchdog (Read tier) — the agentic core
# --------------------------------------------------------------------------- #
def compute_windows_tool(item_id: int) -> dict:
    """Compute days-left on the return / price-protection / warranty windows.

    Args:
        item_id: The ledger id of the item to evaluate.

    Returns:
        dict with 'status' and the computed 'windows'.
    """
    entry = db.get_entry(item_id)
    if not entry:
        return {"status": "error", "reason": f"No ledger item {item_id}"}
    w = compute_windows(entry, _today())
    return {"status": "success", "windows": {
        "return_days_left": w.return_days_left, "return_open": w.return_open,
        "price_protection_days_left": w.price_protection_days_left,
        "price_protection_open": w.price_protection_open,
        "warranty_days_left": w.warranty_days_left,
        "warranty_active": w.warranty_active,
    }}


def check_recalls(item: str) -> dict:
    """Check the recall feed for a match on an item description.

    Args:
        item: The item description to look up.

    Returns:
        dict with 'status' and 'recalled' (bool).
    """
    return {"status": "success", "recalled": check_recall_feed(item), "item": item}


def run_daily_sweep(tool_context=None) -> dict:
    """Run the daily watchdog sweep over every open ledger item.

    This is the 'day 2' behaviour (rule CR3): with no new input it re-evaluates
    every open item against today, polling recall + price signals, and raises a
    structured action event for each threshold crossing. Events are stashed in
    session state for the Action agent.

    Returns:
        dict with 'status', 'as_of', and the list of 'events'.
    """
    as_of = _today()
    events: list[dict] = []
    for entry in db.all_open_entries():
        item_desc = entry.get("item") or ""
        raised = evaluate_entry(
            entry=entry,
            as_of=as_of,
            return_alert_days=settings.return_alert_days,
            warranty_alert_days=settings.warranty_alert_days,
            current_price=current_price_for(item_desc),
            recall_hit=check_recall_feed(item_desc),
        )
        for ev in raised:
            events.append({"kind": ev.kind, "item_id": ev.item_id,
                           "vendor": ev.vendor, "item": ev.item,
                           "message": ev.message, "detail": ev.detail})
    audit("daily_sweep", as_of=as_of.isoformat(), events=len(events))
    if tool_context is not None:
        tool_context.state["pending_events"] = events
    return {"status": "success", "as_of": as_of.isoformat(), "events": events}


# --------------------------------------------------------------------------- #
# Action / Drafting (Draft-only / gated Action tier)
# --------------------------------------------------------------------------- #
def draft_action(event: dict) -> dict:
    """Draft a return / price-adjustment / warranty / recall artifact. NEVER sends.

    Args:
        event: An action event produced by the daily sweep.

    Returns:
        dict with 'status' and the 'draft' (recipient, subject, body, merchant).
    """
    kind = event.get("kind", "")
    vendor = event.get("vendor", "the merchant")
    item = event.get("item", "the item")
    domain = policy_for(vendor).get("domain") or "example.com"
    recipient = f"support@{domain}"
    templates = {
        "return-window-closing": (
            f"Return request — {item}",
            f"Hello {vendor}, I would like to return my {item} within the return "
            f"window. Please advise on next steps. Receipt attached."),
        "price-drop": (
            f"Price adjustment request — {item}",
            f"Hello {vendor}, the {item} I purchased recently dropped in price "
            f"within your price-protection window. I'm requesting a refund of the "
            f"difference ({event.get('detail', {}).get('delta', '')})."),
        "warranty-expiring": (
            f"Warranty registration — {item}",
            f"Hello {vendor}, I'd like to register/confirm the warranty on my {item} "
            f"before it lapses."),
        "recall-match": (
            f"Recall claim — {item}",
            f"Hello {vendor}, my {item} appears on a recall notice. I'm requesting "
            f"remedy per the recall."),
    }
    subject, body = templates.get(kind, (f"Regarding {item}", f"Regarding my {item}."))
    draft = {"merchant": vendor, "recipient": recipient, "subject": subject,
             "body": body, "item": item, "item_id": event.get("item_id")}
    audit("draft_created", kind=kind, item=item, merchant=vendor)
    return {"status": "success", "draft": draft}


def set_action_approval(item_id: int, approved: bool, tool_context=None) -> dict:
    """Record the human's Vibe-Diff decision for a pending outbound action.

    Setting approved=True is the JIT grant that lets the very next `send_action`
    proceed through the Policy Server. Call this only in response to an explicit
    human 'approve'.

    Args:
        item_id: The ledger item the pending action relates to.
        approved: True to authorise the send, False to keep it a draft.

    Returns:
        dict with 'status' and the recorded decision.
    """
    if tool_context is not None:
        tool_context.state["action_approved"] = bool(approved)
        tool_context.state["approved_item_id"] = item_id
    audit("human_decision", item_id=item_id, approved=bool(approved))
    return {"status": "success", "approved": bool(approved), "item_id": item_id}


def send_action(recipient: str, merchant: str, subject: str, body: str,
                item: str, tool_context=None) -> dict:
    """Send an approved outbound action (email a claim/request to a merchant).

    HIGH-STAKES. The Policy Server intercepts this call: it is blocked with a
    Vibe-Diff prompt until a human approves, and blocked outright if the
    recipient domain does not match the merchant. Reaching the tool body means
    the gate already passed.

    Args:
        recipient: Merchant support email address.
        merchant: Merchant name (used to validate the recipient domain).
        subject: Email subject line.
        body: Email body text.
        item: The item this action concerns.

    Returns:
        dict with 'status' and a 'sent' record.
    """
    # In production this hands off to the Gmail MCP with a JIT send-scoped token.
    audit("action_sent", recipient=recipient, merchant=merchant, item=item)
    if tool_context is not None:
        # Consume the one-time approval so a second send re-triggers the gate.
        tool_context.state["action_approved"] = False
    return {"status": "success",
            "sent": {"recipient": recipient, "merchant": merchant,
                     "subject": subject, "item": item}}
