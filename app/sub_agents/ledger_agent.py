"""Ledger sub-agent — TIER: Action-Allowed (local file only).

Normalizes and deduplicates entries into the local SQLite ledger, answers
natural-language queries over it, and exports the spreadsheet view. Its only writes
are local; the Policy Server structurally confines them to the vault directory.
"""

from __future__ import annotations

from google.adk.agents import Agent

from app import config
from app.tools.ledger_tools import export_ledger_xlsx, query_ledger, write_ledger

_INSTRUCTION = """
You are the Ledger specialist for Receipt Vault.

Responsibilities:
- Given structured receipt fields, call `write_ledger` to insert/update the entry.
  The ledger dedupes on (merchant, name, purchase_date, total), so re-recording the
  same receipt is safe.
- Answer natural-language questions about spending with `query_ledger`
  (e.g. "how much did I spend on appliances this year?").
- Export the spreadsheet view with `export_ledger_xlsx` when asked.

Always pass ISO dates (YYYY-MM-DD). Use an empty string for unknown last4 or
warranty_expires. You only ever write to the LOCAL ledger — never anything outbound.
"""


def create_ledger_agent() -> Agent:
    """Build the Ledger sub-agent (local action tier)."""
    return Agent(
        name="ledger_agent",
        model=config.MODEL,
        description=(
            "Writes/dedupes receipts into the local ledger and answers spending "
            "queries. Use after fields are extracted, or for any question about what "
            "was purchased or how much was spent."
        ),
        instruction=_INSTRUCTION,
        tools=[write_ledger, query_ledger, export_ledger_xlsx],
    )
