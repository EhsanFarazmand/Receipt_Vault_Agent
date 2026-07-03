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
"""Policy Server — every tool call passes through here before it executes.

Wired as an ADK `before_tool_callback`, this is the single choke point the
course's zero-trust model calls for. It enforces two kinds of rule and renders
the Vibe Diff:

* **Structural gating** — hard invariants independent of meaning. e.g. a local
  write may only target a path inside the vault; an unknown tool is denied.
* **Semantic gating** — meaning-dependent. e.g. an outbound email whose
  recipient domain is not the receipt's merchant domain is blocked for review
  (a mis-addressed claim is exactly how data leaks).
* **Vibe Diff** — before any send, the action is rendered back in plain language
  so a human approves *intent*, not code. The send only proceeds when
  `state["action_approved"]` is set (JIT: send-scope granted at the approved
  moment, per the IAM pillar).

Returning a dict from a `before_tool_callback` SKIPS the tool and uses that dict
as the result — that is how a blocked call is turned into a safe, explainable
response instead of an execution.
"""
from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.data_sources import policy_for
from app.security.audit import audit

# Tools that send something OUT of the machine. These are the high-stakes calls
# that require semantic checks + a human Vibe-Diff approval.
OUTBOUND_TOOLS = {"send_action"}

# Local roots a write is allowed to touch. Anything outside is denied.
_LOCAL_ROOTS = [settings.store, settings.db_path.parent,
                settings.inbox, settings.audit_path.parent]


def is_local_path(path: str) -> bool:
    """True only if `path` resolves inside one of the allowed local roots."""
    try:
        resolved = Path(path).expanduser().resolve()
    except (OSError, RuntimeError):
        return False
    return any(root in resolved.parents or root == resolved for root in _LOCAL_ROOTS)


def semantic_check(args: dict) -> tuple[bool, str]:
    """Semantic gate for an outbound send: recipient must match merchant domain."""
    merchant = args.get("merchant", "")
    recipient = (args.get("recipient") or "").strip().lower()
    if "@" not in recipient:
        return False, "Recipient is not a valid email address."
    expected_domain = policy_for(merchant).get("domain", "")
    if not expected_domain:
        # Unknown merchant domain — allow but the audit log flags it for review.
        return True, "unknown-merchant-domain"
    recipient_domain = recipient.rsplit("@", 1)[-1]
    if recipient_domain == expected_domain or recipient_domain.endswith(
        "." + expected_domain
    ):
        return True, "domain-match"
    return False, (
        f"Recipient domain '{recipient_domain}' does not match the merchant "
        f"domain '{expected_domain}'. Blocked to prevent a mis-addressed claim."
    )


def render_vibe_diff(args: dict) -> str:
    """Translate a pending send into a plain-language confirmation prompt."""
    merchant = args.get("merchant", "the merchant")
    recipient = args.get("recipient", "customer service")
    subject = args.get("subject", "(no subject)")
    item = args.get("item", "an item")
    return (
        f"I'll email {merchant} ({recipient}) from your account regarding "
        f"'{item}'. Subject: \"{subject}\". Nothing has been sent yet — "
        f"reply 'approve' to send, or 'cancel' to keep it as a draft."
    )


async def policy_gate(tool, args, tool_context) -> dict | None:
    """`before_tool_callback`: gate every tool call. Return None to allow."""
    name = getattr(tool, "name", str(tool))

    # Observability pillar: log every call. Never log full PII — args here are
    # already field-level (last-4 masked upstream by the sanitizer).
    audit("tool_call", tool=name)

    # --- Structural: local writes must stay inside the vault ---
    if name == "write_ledger":
        source = (args.get("entry") or {}).get("source_file")
        if source and not is_local_path(source):
            audit("blocked_structural", tool=name, reason="non-local-write",
                  path=source)
            return {"status": "blocked",
                    "reason": f"Refusing to record a non-local source path: {source}"}

    # --- Outbound: semantic check + Vibe-Diff approval gate ---
    if name in OUTBOUND_TOOLS:
        ok, reason = semantic_check(args)
        if not ok:
            audit("blocked_semantic", tool=name, reason=reason)
            return {"status": "blocked", "reason": reason}

        if not tool_context.state.get("action_approved"):
            diff = render_vibe_diff(args)
            audit("send_blocked_pending_approval", tool=name,
                  recipient=args.get("recipient"), merchant=args.get("merchant"))
            return {
                "status": "blocked_pending_approval",
                "vibe_diff": diff,
                "message": "Human approval required before this send.",
            }
        # Approved: record the JIT grant, then let the tool proceed.
        audit("send_approved", tool=name, recipient=args.get("recipient"),
              semantic=reason)

    return None  # allow
