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
"""Unit tests for the Policy Server — mirror the approval-gate Gherkin scenarios."""
import asyncio
from types import SimpleNamespace

from app.policy.policy_server import (
    is_local_path,
    policy_gate,
    render_vibe_diff,
    semantic_check,
)


class _Tool:
    def __init__(self, name):
        self.name = name


class _Ctx:
    def __init__(self, approved=False):
        self.state = {"action_approved": approved}


def test_semantic_gate_allows_matching_domain():
    ok, reason = semantic_check({"merchant": "Target", "recipient": "support@target.com"})
    assert ok and reason == "domain-match"


def test_semantic_gate_blocks_mismatched_domain():
    ok, reason = semantic_check({"merchant": "Target", "recipient": "x@evil.com"})
    assert not ok
    assert "does not match" in reason


def test_send_blocked_pending_approval():
    # Scenario: Never send without explicit confirmation.
    args = {"merchant": "Target", "recipient": "support@target.com",
            "subject": "Return", "item": "blender"}
    result = asyncio.run(policy_gate(_Tool("send_action"), args, _Ctx(approved=False)))
    assert result["status"] == "blocked_pending_approval"
    assert "blender" in result["vibe_diff"]


def test_send_allowed_after_approval():
    args = {"merchant": "Target", "recipient": "support@target.com",
            "subject": "Return", "item": "blender"}
    result = asyncio.run(policy_gate(_Tool("send_action"), args, _Ctx(approved=True)))
    assert result is None  # None == allow the tool to proceed


def test_structural_gate_blocks_non_local_write():
    args = {"entry": {"source_file": "//server/share/secret.txt"}}
    result = asyncio.run(policy_gate(_Tool("write_ledger"), args, _Ctx()))
    assert result is not None and result["status"] == "blocked"


def test_render_vibe_diff_is_plain_language():
    diff = render_vibe_diff({"merchant": "Target", "recipient": "support@target.com",
                             "subject": "Return request", "item": "blender"})
    assert "Target" in diff and "reply 'approve'" in diff


def test_local_path_detection():
    assert is_local_path("./vault/x.txt") is True
    assert is_local_path("C:/Windows/System32/evil.exe") is False
