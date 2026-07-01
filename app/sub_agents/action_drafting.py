"""Action / Drafting sub-agent — TIER: Draft-only; Action-only-after-approval.

Turns a Watchdog action event into a concrete draft, then routes any outbound send
through the human approval gate (the Vibe Diff). The `send_email` tool is wrapped
with `require_confirmation=True` so the ADK runtime pauses for an explicit human
APPROVE before it ever runs — the agent cannot bypass it.
"""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from app import config
from app.tools.action_tools import draft_action, send_email

_INSTRUCTION = """
You are the Action / Drafting specialist for Receipt Vault.

For a given action event (return-window-closing, price-drop, warranty-expiring,
recall-match):
1. Call `draft_action` to produce the message. This NEVER sends.
2. Present the draft to the user for review.
3. Only if the user explicitly asks to send, call `send_email`. This is a
   high-stakes action: the runtime will show a Vibe Diff and require an explicit
   APPROVE. The recipient must be in the merchant's own domain — the Policy Server
   will block anything else.

Never send without approval. When in doubt, draft and stop. Prefer to show the user
exactly what will go out, to whom, and why, before anything leaves.
"""


def create_action_agent() -> Agent:
    """Build the Action/Drafting sub-agent (draft-only; approval-gated send)."""
    # `require_confirmation=True` makes the runtime pause for human approval before
    # the outbound send executes — the ADK-native Vibe Diff / approval gate.
    guarded_send = FunctionTool(send_email, require_confirmation=True)
    return Agent(
        name="action_drafting_agent",
        model=config.MODEL,
        description=(
            "Drafts return / price-adjustment / warranty / recall messages from an "
            "action event, and sends them ONLY after explicit human approval. Use to "
            "turn a Watchdog event into a concrete, reviewable draft."
        ),
        instruction=_INSTRUCTION,
        tools=[draft_action, guarded_send],
    )
