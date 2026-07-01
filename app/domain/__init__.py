"""Domain layer: the deterministic business logic Receipt Vault reasons over.

Kept free of ADK/LLM imports so it is fully unit-testable and so the Watchdog's
window math is reproducible (the same ledger + the same 'today' always yields the
same action events). Modules:

* ``merchant_policies`` — per-merchant return / price-protection knowledge base.
* ``windows``           — return / price-protection / warranty countdown math.
* ``ledger``            — local SQLite ledger (write, query, xlsx export).
"""
