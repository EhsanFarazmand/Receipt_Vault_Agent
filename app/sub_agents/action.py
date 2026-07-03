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
"""Action / Drafting Agent — TIER: Draft-only (human sends).

Turns an action event into a concrete draft, shows the Vibe Diff, and only
sends after an explicit human approval. The Policy Server enforces the gate; the
agent must never claim something was sent that was only drafted.
"""
from __future__ import annotations

from google.adk.agents import Agent

from app.config import MODEL
from app.policy.policy_server import policy_gate
from app.tools import draft_action, send_action, set_action_approval

_INSTRUCTION = """
You are the Action & Drafting specialist for Receipt Vault.

Workflow for an action event:
1. Call `draft_action` to produce the return/price-adjustment/warranty/recall
   draft. Drafting NEVER sends.
2. Present the draft to the user as a plain-language Vibe Diff and ask for
   approval. Do not send yet.
3. Only when the user explicitly approves, call `set_action_approval` with
   approved=true, then call `send_action`. If the Policy Server returns
   `blocked_pending_approval` or `blocked`, relay that to the user honestly —
   never pretend a blocked action was sent.

Rules:
- Money- and outbound-actions are behind the approval gate. Default to drafting.
- If the user has not approved, keep it a draft and say so.
"""


def create_action_agent() -> Agent:
    return Agent(
        name="action_drafting_agent",
        model=MODEL,
        description=(
            "Drafts return/price-adjustment/warranty/recall claims from action "
            "events, shows the Vibe Diff, and sends ONLY after explicit human "
            "approval. Use to act on a watchdog event or an approved draft."
        ),
        instruction=_INSTRUCTION,
        tools=[draft_action, set_action_approval, send_action],
        before_tool_callback=policy_gate,
    )
