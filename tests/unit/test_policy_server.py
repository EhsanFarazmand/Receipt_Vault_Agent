"""Zero-trust Policy Server tests: structural + semantic gating + Vibe Diff.

Enforces the `approval_gate.feature` spec at the unit level.
"""

import os
from pathlib import Path

from app.security.policy_server import Decision, PolicyServer


def _server() -> PolicyServer:
    return PolicyServer(vault_dir=Path(os.environ["RECEIPT_VAULT_HOME"]))


def test_local_write_inside_vault_allowed():
    v = _server().evaluate("write_ledger", {"path": os.environ["RECEIPT_VAULT_DB"]})
    assert v.decision is Decision.ALLOW


def test_local_write_outside_vault_blocked():
    v = _server().evaluate("write_ledger", {"path": r"C:\Windows\evil.db"})
    assert v.decision is Decision.BLOCK
    assert "structural violation" in v.reason


def test_outbound_to_merchant_domain_needs_approval_with_vibe_diff():
    v = _server().evaluate(
        "send_email",
        {"recipient": "help@target.com", "merchant": "Target", "subject": "Return", "item": "blender"},
    )
    assert v.decision is Decision.NEEDS_APPROVAL
    assert v.vibe_diff is not None
    assert "Vibe Diff" in v.vibe_diff


def test_outbound_to_wrong_domain_blocked():
    v = _server().evaluate(
        "send_email",
        {"recipient": "attacker@x.com", "merchant": "Target", "subject": "x", "item": "blender"},
    )
    assert v.decision is Decision.BLOCK
    assert "semantic violation" in v.reason


def test_unknown_merchant_domain_blocked():
    v = _server().evaluate(
        "send_email",
        {"recipient": "someone@wherever.com", "merchant": "NoSuchStore", "subject": "x", "item": "y"},
    )
    assert v.decision is Decision.BLOCK
