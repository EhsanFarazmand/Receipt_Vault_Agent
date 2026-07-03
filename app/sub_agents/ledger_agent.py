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
"""Ledger Agent — TIER: Action (writes the LOCAL ledger only).

Normalises and deduplicates entries into the local SQLite ledger and answers
natural-language questions about spending.
"""
from __future__ import annotations

from google.adk.agents import Agent

from app.config import MODEL
from app.policy.policy_server import policy_gate
from app.tools import query_ledger, write_ledger

_INSTRUCTION = """
You are the Ledger specialist for Receipt Vault.

- To record a receipt: call `write_ledger` with the structured fields. It
  deduplicates automatically, so re-recording the same receipt is safe.
- To answer a spending question ("how much did I spend at Target this year?"):
  call `query_ledger` with the user's question and summarise the result.

You may only write to the LOCAL ledger. Never send anything outbound.
"""


def create_ledger_agent() -> Agent:
    return Agent(
        name="ledger_agent",
        model=MODEL,
        description=(
            "Writes normalised, deduplicated receipt entries to the local ledger "
            "and answers natural-language spending queries. Use after intake has "
            "extracted fields, or for any 'how much did I spend' question."
        ),
        instruction=_INSTRUCTION,
        tools=[write_ledger, query_ledger],
        before_tool_callback=policy_gate,
    )
