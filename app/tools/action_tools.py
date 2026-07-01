"""Action / Drafting tools: turn an action event into a draft, then (only on human
approval) send it.

Tier: Draft-only for ``draft_action``; Action-Allowed-after-approval for ``send_email``.
The send path is gated three ways (defense in depth):
  1. The Policy Server (semantic rule) blocks any recipient outside the merchant domain.
  2. The Policy Server marks the call NEEDS_APPROVAL and renders a Vibe Diff.
  3. In the ADK agent, ``send_email`` is wrapped with ``require_confirmation=True`` so
     the runtime pauses for an explicit human APPROVE before the tool ever executes.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app import config
from app.security.policy_server import Decision, PolicyServer

_DRAFT_TEMPLATES = {
    "return-window-closing": (
        "Subject: Return request — {item} (order at {merchant})\n\n"
        "Hello {merchant} team,\n\nI'd like to return the {item} I purchased. "
        "It is within your return window. Please advise on next steps.\n\nThank you."
    ),
    "price-drop": (
        "Subject: Price adjustment request — {item}\n\n"
        "Hello {merchant} team,\n\nI purchased the {item} recently and it has since "
        "dropped in price within your price-protection window. I'd like to request a "
        "price adjustment for the difference. Receipt attached.\n\nThank you."
    ),
    "warranty-expiring": (
        "Subject: Warranty registration / claim — {item}\n\n"
        "Hello,\n\nI'd like to register (or open a claim on) the warranty for my {item} "
        "before it expires.\n\nThank you."
    ),
    "recall-match": (
        "Subject: Recall claim — {item}\n\n"
        "Hello {merchant} team,\n\nMy {item} is affected by a safety recall. I'd like to "
        "file a claim for the offered remedy. Proof of purchase attached.\n\nThank you."
    ),
}


def draft_action(kind: str, item: str, merchant: str) -> dict:
    """Draft a return / price-adjustment / warranty / recall message. Never sends.

    Args:
        kind: The action event kind (return-window-closing, price-drop,
            warranty-expiring, or recall-match).
        item: The item the action concerns.
        merchant: The merchant to contact.

    Returns:
        dict with 'status' and 'draft' (the drafted message text).
    """
    template = _DRAFT_TEMPLATES.get(kind)
    if template is None:
        return {"status": "error", "error": f"unknown action kind: {kind}"}
    draft = template.format(item=item, merchant=merchant)
    _audit("DRAFT", f"{kind}:{item}", "drafted")
    return {"status": "success", "draft": draft}


def send_email(recipient: str, merchant: str, subject: str, body: str, item: str) -> dict:
    """Send an approved outbound email via the Gmail MCP (approval-gated).

    This is a high-stakes action: it only runs after the human has approved the Vibe
    Diff. It re-checks the Policy Server as a final structural/semantic gate, then (in
    this local-first build) records the send to the audit log instead of contacting a
    live mail server. Wiring a real Gmail MCP swaps only the final step.

    Args:
        recipient: The email recipient (must be in the merchant's domain).
        merchant: The merchant name (used to verify the recipient domain).
        subject: The email subject line.
        body: The email body.
        item: The item this action concerns.

    Returns:
        dict with 'status' and details of the send or the block reason.
    """
    server = PolicyServer()
    args = {"recipient": recipient, "merchant": merchant, "subject": subject, "item": item}
    verdict = server.evaluate("send_email", args)

    if verdict.decision is Decision.BLOCK:
        _audit("SEND-BLOCKED", f"{merchant}:{recipient}", verdict.reason)
        return {"status": "blocked", "reason": verdict.reason}

    # A real deployment hands this to the Gmail MCP here (with JIT send-scope).
    _audit("SEND", f"{merchant}:{recipient}", subject)
    return {
        "status": "sent",
        "recipient": recipient,
        "subject": subject,
        "note": "recorded to audit log (local-first demo; wire Gmail MCP to actually send)",
    }


def _audit(kind: str, name: str, detail: str) -> None:
    try:
        config.AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with config.AUDIT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"{date.today().isoformat()}\t{kind}\t{name}\t{detail}\n")
    except OSError:
        pass
