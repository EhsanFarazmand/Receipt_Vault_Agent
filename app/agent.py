"""Receipt Vault — Orchestrator (ADK root agent) + App wiring.

The Orchestrator routes each event to the right specialist by intent and state
(course: *Orchestrator* role; *Harness = Model + Harness*). It holds minimal working
memory and delegates detail to the four sub-agents via ADK LLM delegation.

Two shared layers wrap the agents:
  * the Policy Server plugin (zero-trust gating on every tool call), and
  * a state-initialization callback (prevents KeyError on first-turn state reads).

`root_agent` and `app` are what the ADK runner / agents-cli discover. `App(name="app")`
MUST match this package directory name ("app") or eval hits "Session not found".
"""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App, ResumabilityConfig

from app import config
from app.sub_agents import (
    create_action_agent,
    create_intake_agent,
    create_ledger_agent,
    create_watchdog_agent,
)

# The Policy Server plugin is optional at import time so unit tests of the pure
# policy logic don't require the full ADK plugin stack.
try:
    from app.security.policy_server import PolicyPlugin
except Exception:  # pragma: no cover
    PolicyPlugin = None  # type: ignore[assignment]


_ORCHESTRATOR_INSTRUCTION = """
You are the Orchestrator for Receipt Vault, a local-first, privacy-first receipt
concierge. Your job is to ROUTE, not to do the specialists' work yourself.

Route by intent:
- A NEW receipt file/photo/PDF, or a folder of them  → intake_extraction_agent,
  then hand its structured fields to ledger_agent to record.
- A question about spending or what's on file        → ledger_agent.
- A daily tick, "what needs attention today", or a
  window/recall/price check                          → watchdog_agent.
- Turning a raised action event into a draft, or an
  approved send                                       → action_drafting_agent.

Principles:
- Local-first & private: never suggest uploading the vault; PII is redacted before
  any model call by the sanitization layer.
- Nothing outbound without explicit human approval (the Vibe Diff). You never send.
- Lead with the single most time-sensitive item when reporting Watchdog results.
- Keep your own messages short; let specialists carry the detail.
"""


async def _init_state(callback_context: CallbackContext) -> None:
    """Seed session state so instruction templates never KeyError on turn 1."""
    state = callback_context.state
    state.setdefault("inbox_dir", str(config.INBOX_DIR))
    state.setdefault("vault_dir", str(config.VAULT_DIR))


def create_root_agent() -> Agent:
    """Build the Orchestrator root agent with its four specialist sub-agents."""
    config.ensure_dirs()
    return Agent(
        name="receipt_vault_orchestrator",
        model=config.MODEL,
        description="Routes receipt events to the Intake, Ledger, Watchdog, and Action specialists.",
        instruction=_ORCHESTRATOR_INSTRUCTION,
        sub_agents=[
            create_intake_agent(),
            create_ledger_agent(),
            create_watchdog_agent(),
            create_action_agent(),
        ],
        before_agent_callback=_init_state,
    )


root_agent = create_root_agent()

# Register the Policy Server as a global guardrail plugin when ADK supports it.
_plugins = [PolicyPlugin()] if PolicyPlugin is not None else []

# `resumability` lets the runtime pause for the human approval gate and resume after
# the user replies APPROVE (the outbound Vibe Diff). Name MUST equal the dir ("app").
app = App(
    name="app",
    root_agent=root_agent,
    plugins=_plugins,
    resumability_config=ResumabilityConfig(is_resumable=True),
)
