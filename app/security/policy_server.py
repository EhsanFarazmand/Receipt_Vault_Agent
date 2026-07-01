"""Zero-trust Policy Server: structural + semantic gating and the Vibe Diff.

Every tool call is intercepted *before* execution (course: *Policy Server —
Structural and Semantic Gating*, Day 5; *Governance* pillar, Day 4). Two decision
layers:

* **Structural** — hard, deterministic rules on the shape of a call. Example: the
  Ledger agent may only write to the *local* ledger path; never an arbitrary file.
* **Semantic** — meaning-aware rules. Example: an outbound email whose recipient is
  not the receipt's own merchant domain is blocked pending human review.

High-stakes (outbound) actions additionally require a **Vibe Diff**: a plain-language
render of the intended action that a human must approve before anything is sent.

The core is a plain ``PolicyServer`` class (unit-testable, no ADK needed). The
``PolicyPlugin`` at the bottom wires it into the ADK runner via ``before_tool_callback``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from app import config


class Decision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    NEEDS_APPROVAL = "needs_approval"  # allowed only after a human Vibe-Diff approval


# Tools that perform an outbound, real-world side effect. These are the only calls
# that can reach NEEDS_APPROVAL — everything else is allow/block on structural rules.
OUTBOUND_TOOLS = frozenset({"send_email", "submit_return_form", "send_gmail", "file_claim"})

# Tools that write to local storage — structurally confined to the vault directory.
LOCAL_WRITE_TOOLS = frozenset({"write_ledger", "rename_and_file", "export_ledger_xlsx"})


@dataclass
class PolicyVerdict:
    """Result of a policy evaluation for a single tool call."""

    decision: Decision
    reason: str
    vibe_diff: str | None = None  # human-facing confirmation text for outbound actions

    @property
    def allowed(self) -> bool:
        return self.decision is Decision.ALLOW


def _merchant_domain(merchant: str) -> str:
    """Best-effort map a merchant display name to its email domain.

    Deliberately conservative: unknown merchants yield an empty domain, which the
    semantic rule treats as "cannot verify recipient" → block pending review.
    """
    known = {
        "target": "target.com",
        "costco": "costco.com",
        "apple": "apple.com",
        "amazon": "amazon.com",
        "best buy": "bestbuy.com",
        "walmart": "walmart.com",
        "home depot": "homedepot.com",
    }
    return known.get((merchant or "").strip().lower(), "")


class PolicyServer:
    """Structural + semantic gate for every tool call."""

    def __init__(self, vault_dir: Path | None = None) -> None:
        # All local writes must resolve to somewhere under this root.
        self.vault_dir = (vault_dir or config.VAULT_DIR).resolve()

    # -- structural ---------------------------------------------------------
    def _check_local_path(self, path_str: str) -> PolicyVerdict | None:
        """Confine local-write tools to the vault directory. Returns a BLOCK
        verdict on violation, or ``None`` if the path is fine."""
        try:
            target = Path(path_str).resolve()
        except (OSError, ValueError):
            return PolicyVerdict(Decision.BLOCK, f"unparseable path: {path_str!r}")
        # ``is_relative_to`` (3.9+) — structural containment check.
        if not target.is_relative_to(self.vault_dir):
            return PolicyVerdict(
                Decision.BLOCK,
                f"structural violation: write outside vault ({target} not under {self.vault_dir})",
            )
        return None

    # -- semantic -----------------------------------------------------------
    def _check_recipient(self, recipient: str, merchant: str) -> PolicyVerdict | None:
        """Outbound email recipient must belong to the receipt's merchant domain."""
        domain = _merchant_domain(merchant)
        recipient = (recipient or "").strip().lower()
        if not recipient or "@" not in recipient:
            return PolicyVerdict(Decision.BLOCK, "semantic violation: missing/invalid recipient")
        if not domain:
            return PolicyVerdict(
                Decision.BLOCK,
                f"semantic violation: unverifiable merchant domain for {merchant!r}",
            )
        if not recipient.endswith("@" + domain) and not recipient.endswith("." + domain):
            return PolicyVerdict(
                Decision.BLOCK,
                f"semantic violation: recipient {recipient!r} is not in merchant domain {domain!r}",
            )
        return None

    # -- public API ---------------------------------------------------------
    def evaluate(self, tool_name: str, args: dict) -> PolicyVerdict:
        """Evaluate a single tool call and return a verdict.

        Order: structural rules first (cheap, absolute), then semantic rules, then —
        for outbound tools that survive both — a NEEDS_APPROVAL verdict carrying the
        Vibe Diff.
        """
        # Structural: local writes stay in the vault.
        if tool_name in LOCAL_WRITE_TOOLS:
            path_str = args.get("path") or args.get("dest") or args.get("file_path")
            if path_str is not None:
                verdict = self._check_local_path(str(path_str))
                if verdict is not None:
                    return verdict
            return PolicyVerdict(Decision.ALLOW, "local write confined to vault")

        # Outbound: structural + semantic + Vibe Diff.
        if tool_name in OUTBOUND_TOOLS:
            recipient = args.get("recipient", "")
            merchant = args.get("merchant", "")
            verdict = self._check_recipient(recipient, merchant)
            if verdict is not None:
                return verdict
            # Passed the gates — but a human still approves intent, not code.
            return PolicyVerdict(
                Decision.NEEDS_APPROVAL,
                "outbound action requires human approval",
                vibe_diff=self.render_vibe_diff(tool_name, args),
            )

        # Everything else (read/draft tier) is allowed.
        return PolicyVerdict(Decision.ALLOW, "read/draft tier: no gate")

    def render_vibe_diff(self, tool_name: str, args: dict) -> str:
        """Translate an outbound action into a plain-language confirmation.

        The course's *Vibe Diff*: a human approves *intent*, expressed in natural
        language, not generated code. Kept deterministic and template-based so the
        confirmation text itself is never model-authored (and so it is testable).
        """
        merchant = args.get("merchant", "the merchant")
        recipient = args.get("recipient", "(unknown recipient)")
        subject = args.get("subject", "(no subject)")
        item = args.get("item", "the item")
        action = {
            "send_email": "email",
            "send_gmail": "email",
            "submit_return_form": "submit a return form to",
            "file_claim": "file a claim with",
        }.get(tool_name, "contact")
        return (
            f"Vibe Diff — approve before sending:\n"
            f"  I will {action} {merchant} ({recipient})\n"
            f'  Subject: "{subject}"\n'
            f"  Regarding: {item}\n"
            f"  Nothing is sent until you reply APPROVE."
        )


# ---------------------------------------------------------------------------
# ADK integration: a plugin that runs the Policy Server on every tool call.
# ---------------------------------------------------------------------------
# Imported lazily-guarded so the pure PolicyServer above can be unit-tested in
# environments without google-adk installed.
try:  # pragma: no cover - exercised only when ADK is present
    from google.adk.plugins.base_plugin import BasePlugin

    class PolicyPlugin(BasePlugin):
        """Registers the Policy Server as a global before-tool guardrail.

        Returning a dict from ``before_tool_callback`` short-circuits the tool and
        uses the dict as its result — so a blocked call never executes, and an
        outbound call is held with its Vibe Diff until a human approves.
        """

        def __init__(self) -> None:
            super().__init__(name="policy_server")
            self._server = PolicyServer()

        async def before_tool_callback(self, *, tool, tool_context, args):  # noqa: ANN001
            verdict = self._server.evaluate(tool.name, args or {})
            _audit(tool.name, verdict)
            if verdict.decision is Decision.BLOCK:
                return {"status": "blocked", "reason": verdict.reason}
            if verdict.decision is Decision.NEEDS_APPROVAL:
                # Surface the Vibe Diff; the Action tool itself also uses ADK
                # tool confirmation, so this is the governance-side record.
                return {
                    "status": "needs_approval",
                    "vibe_diff": verdict.vibe_diff,
                    "reason": verdict.reason,
                }
            return None  # ALLOW → let the tool run

except ImportError:  # pragma: no cover
    PolicyPlugin = None  # type: ignore[assignment]


def _audit(tool_name: str, verdict: PolicyVerdict) -> None:
    """Append a governance decision to the audit log (Observability pillar)."""
    try:
        config.AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with config.AUDIT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"POLICY\t{tool_name}\t{verdict.decision.value}\t{verdict.reason}\n")
    except OSError:
        # Never let audit-logging failures block a decision; log to stderr instead.
        if os.environ.get("RECEIPT_VAULT_DEBUG"):
            import sys

            print(f"[audit-failed] {tool_name} {verdict.decision}", file=sys.stderr)
