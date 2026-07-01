"""Receipt Vault MCP server — the "USB-C" tool surface (course concept: MCP Server).

Exposes the vault as a clean, typed, individually-permissioned tool surface so *any*
MCP-capable harness (not just this ADK app) can drive it. It wraps the SAME functions
the ADK sub-agents use (``app.tools.*``) — one implementation, two front doors — which
is exactly the NxM-avoidance point: speak MCP once, plug into everything.

Run it over stdio:
    uv run python -m mcp_server.server
    # or, via the console script declared in pyproject.toml:
    uv run receipt-vault-mcp

Point an MCP client (Claude Desktop, Gemini CLI, or the ADK `McpToolset`) at that
command. The Policy Server still governs high-stakes calls on the ADK side; an MCP
client wiring the send tool should apply its own approval gate too.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.tools.action_tools import draft_action
from app.tools.intake_tools import extract_fields, ocr_receipt, rename_and_file, scan_inbox
from app.tools.ledger_tools import export_ledger_xlsx, query_ledger, write_ledger
from app.tools.watchdog_tools import (
    check_recalls,
    compute_windows,
    record_price_observation,
    run_daily_sweep,
)

mcp = FastMCP("receipt-vault")

# ---- Read tier -------------------------------------------------------------
mcp.tool()(scan_inbox)          # list new receipt files in a watched folder
mcp.tool()(ocr_receipt)         # OCR one file → sanitized (untrusted) text
mcp.tool()(query_ledger)        # natural-language question over the ledger
mcp.tool()(compute_windows)     # days-left on return / price-protection / warranty
mcp.tool()(check_recalls)       # poll the recall feed for a match
mcp.tool()(run_daily_sweep)     # the daily watchdog sweep → action events

# ---- Draft tier ------------------------------------------------------------
mcp.tool()(extract_fields)      # structured extraction from sanitized text
mcp.tool()(draft_action)        # produce a return/price/warranty/recall draft (never sends)

# ---- Local-action tier (Policy Server confines writes to the vault) --------
mcp.tool()(write_ledger)             # insert/upsert into the local ledger
mcp.tool()(export_ledger_xlsx)       # export the spreadsheet view
mcp.tool()(rename_and_file)          # file a source document into the vault
mcp.tool()(record_price_observation) # feed a new observed price into the ledger


def main() -> None:
    """Console-script entrypoint (see pyproject.toml [project.scripts])."""
    mcp.run()  # defaults to stdio transport


if __name__ == "__main__":
    main()
