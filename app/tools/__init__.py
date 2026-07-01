"""ADK FunctionTools — the thin, typed surface each sub-agent is given.

Each tool wraps the deterministic domain/security logic and returns a JSON-serializable
dict with a ``status`` key (ADK tool convention). Tools carry no default argument
values (an ADK requirement) and never mention the injected ``tool_context`` in their
docstrings (which are sent verbatim to the model).

The same functions are re-exported by ``mcp_server/server.py`` as the first-party
Receipt Vault MCP tool surface — one implementation, two front doors (ADK + MCP).
"""
