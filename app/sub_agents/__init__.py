"""The four specialist sub-agents Receipt Vault's Orchestrator delegates to.

Each is exposed as a *factory function* (not a module-level instance) so the same
agent can be attached under a parent without ADK's "agent already has a parent"
error (see /google-agents-cli-adk-code). Narrow tool sets per agent keep context
small (fights context rot) and let the security tier differ per agent.
"""

from app.sub_agents.intake_extraction import create_intake_agent
from app.sub_agents.ledger_agent import create_ledger_agent
from app.sub_agents.watchdog import create_watchdog_agent
from app.sub_agents.action_drafting import create_action_agent

__all__ = [
    "create_intake_agent",
    "create_ledger_agent",
    "create_watchdog_agent",
    "create_action_agent",
]
