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
"""Receipt Vault MCP server — the "USB-C" tool surface (course concept).

Exposes the vault as a clean, typed, individually-permissioned MCP tool surface
so *any* MCP-capable harness (ADK, Claude, Gemini CLI, ...) can drive it — not
just this project's agents. Each tool is small and single-purpose; the tiers
(Read / Draft / Action-local) mirror the blueprint's §5 table.

Run it over stdio:
    uv run python -m mcp_server.server

Then point an MCP client at it, e.g. in ADK:
    McpToolset(connection_params=StdioConnectionParams(server_params=
        StdioServerParameters(command="uv",
            args=["run", "python", "-m", "mcp_server.server"])))

The outbound `send_action` is deliberately NOT exposed here — sending stays
behind the in-process Action agent and its Policy-Server approval gate.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.tools import vault_tools as vt

mcp = FastMCP("receipt-vault")


# --- Read tier -------------------------------------------------------------
@mcp.tool()
def scan_inbox(folder: str) -> dict:
    """List new receipt files waiting in a watched inbox folder."""
    return vt.scan_inbox(folder)


@mcp.tool()
def ocr_receipt(path: str) -> dict:
    """OCR one receipt file and return its raw (untrusted) text."""
    return vt.ocr_receipt(path)


@mcp.tool()
def query_ledger(nl_query: str) -> dict:
    """Answer a natural-language spending question from the local ledger."""
    return vt.query_ledger(nl_query)


@mcp.tool()
def compute_windows(item_id: int) -> dict:
    """Days-left on the return / price-protection / warranty windows of an item."""
    return vt.compute_windows_tool(item_id)


@mcp.tool()
def check_recalls(item: str) -> dict:
    """Check the recall feed for a match on an item description."""
    return vt.check_recalls(item)


@mcp.tool()
def run_daily_sweep() -> dict:
    """Run the daily watchdog sweep over all open items and return action events."""
    return vt.run_daily_sweep()


# --- Draft tier ------------------------------------------------------------
@mcp.tool()
def extract_fields(text: str) -> dict:
    """Sanitise untrusted receipt text (PII + injection) and extract fields."""
    return vt.extract_fields(text)


@mcp.tool()
def draft_action(event: dict) -> dict:
    """Draft a return/price/warranty/recall artifact from an action event. Never sends."""
    return vt.draft_action(event)


# --- Action (local) tier ---------------------------------------------------
@mcp.tool()
def write_ledger(entry: dict) -> dict:
    """Insert/upsert a receipt into the LOCAL ledger (dedupes automatically)."""
    return vt.write_ledger(entry)


if __name__ == "__main__":
    # Default transport is stdio — ideal for a local, no-inbound-ports server.
    mcp.run()
