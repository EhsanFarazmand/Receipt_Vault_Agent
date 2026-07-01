"""Receipt Vault ADK application package.

Exposes ``root_agent`` and ``app`` for the ADK runner / agents-cli to discover
(they also import ``app.agent`` directly). The package directory name ("app") must
match ``App(name="app")`` in agent.py.

The agent import is guarded so the deterministic layers (``app.domain``,
``app.security``, ``app.tools``) remain importable and unit-testable in environments
where ``google-adk`` is not installed. When ADK is present, ``root_agent`` and ``app``
are re-exported here for convenience.
"""

try:  # google-adk present (the normal `uv sync` runtime)
    from app.agent import app, root_agent

    __all__ = ["app", "root_agent"]
except ImportError:  # google-adk not installed — domain/security/tools still import
    __all__ = []
