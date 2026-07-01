"""Watchdog sub-agent — the agentic core. TIER: Read-only.

Runs the daily sweep: for every open item it checks recalls, computes return/
price-protection/warranty windows, and raises structured action events when a
threshold is crossed. It never acts — it hands events to the Action agent.
"""

from __future__ import annotations

from google.adk.agents import Agent

from app import config
from app.tools.watchdog_tools import (
    check_recalls,
    compute_windows,
    record_price_observation,
    run_daily_sweep,
)

_INSTRUCTION = """
You are the Watchdog specialist for Receipt Vault — the agent's standing watch.

When a daily tick arrives (or you are asked to sweep):
1. Call `run_daily_sweep` (pass an empty reference_date to use today, or an ISO date
   for a simulated run). This returns structured action events already filtered by
   the configured thresholds.
2. Summarize the events for the user in plain language, leading with the most
   time-sensitive one (smallest days_left), e.g.
   "You can still return the blender for 6 more days."
3. For any event, the Action agent will draft the response — do NOT draft or send
   anything yourself. You are read-only.

Use `compute_windows`, `check_recalls`, and `record_price_observation` for targeted
checks on a single item when asked. Never invent deadlines — rely on the tools.
"""


def create_watchdog_agent() -> Agent:
    """Build the Watchdog sub-agent (read-only, the agentic core)."""
    return Agent(
        name="watchdog_agent",
        model=config.MODEL,
        description=(
            "Runs the daily deadline sweep: recall feed + return/price-protection/"
            "warranty window math, raising action events past threshold. Use for a "
            "daily tick, 'what needs attention today', or single-item window checks."
        ),
        instruction=_INSTRUCTION,
        tools=[run_daily_sweep, compute_windows, check_recalls, record_price_observation],
    )
