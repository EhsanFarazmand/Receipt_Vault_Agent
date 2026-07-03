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
"""Watchdog Agent — TIER: Read-only. The agentic core.

Runs the daily sweep: for every open item it computes days-left on each window,
polls recall + price signals, and raises structured action events when a
threshold is crossed. It reads only; it never drafts or sends.
"""
from __future__ import annotations

from google.adk.agents import Agent

from app.config import MODEL
from app.policy.policy_server import policy_gate
from app.tools import check_recalls, compute_windows_tool, run_daily_sweep

_INSTRUCTION = """
You are the Watchdog specialist for Receipt Vault — the standing watch.

When asked to run the daily sweep (or on a daily tick):
1. Call `run_daily_sweep`. It re-evaluates every open item against today and
   returns a list of `events` (return-window-closing, price-drop,
   warranty-expiring, recall-match). This works with NO new receipts — that is
   the whole point.
2. Summarise the events for the user, leading with the single most urgent one
   (e.g. "You can still return the blender for 6 more days").
3. For a specific item you can call `compute_windows` or `check_recalls`.

You raise events only. You do NOT draft or send — hand events to the Action
specialist.
"""


def create_watchdog_agent() -> Agent:
    return Agent(
        name="watchdog_agent",
        model=MODEL,
        description=(
            "The agentic core. Runs the daily sweep over all open items, "
            "computing return/price-protection/warranty countdowns and polling "
            "recall + price feeds, raising action events on threshold crossings. "
            "Use for a daily tick or 'what needs my attention today'."
        ),
        instruction=_INSTRUCTION,
        tools=[run_daily_sweep, compute_windows_tool, check_recalls],
        before_tool_callback=policy_gate,
    )
