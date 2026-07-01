"""Central configuration for Receipt Vault.

All tunables live here so the agents, tools, and the daily Watchdog sweep read a
single source of truth (course concept: *Harness = Model + Harness* — the harness
supplies constraints and state around the model). Values fall back to sensible
local-first defaults and can be overridden via environment variables (.env).
"""

from __future__ import annotations

import os
from pathlib import Path


def _clean(raw: str) -> str:
    """Strip an inline ``# comment`` and surrounding whitespace from an env value.

    Different .env loaders disagree on inline comments (python-dotenv strips them,
    a naive parser does not). Cleaning here makes config resilient no matter how the
    value reached the environment."""
    return raw.split("#", 1)[0].strip()


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    cleaned = _clean(raw)
    return int(cleaned) if cleaned else default


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    cleaned = _clean(raw)
    return float(cleaned) if cleaned else default


def _path_env(name: str, default: str) -> Path:
    return Path(_clean(os.environ.get(name, default))).expanduser()

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
# `gemini-flash-latest` is a moving alias that always points at the current
# Flash model — fast + cheap, which suits a system that sweeps hundreds of
# receipts daily. Override per-environment with RECEIPT_VAULT_MODEL.
MODEL: str = _clean(os.environ.get("RECEIPT_VAULT_MODEL", "gemini-flash-latest"))

# ---------------------------------------------------------------------------
# Local-first storage layout (privacy pillar: the vault lives on the user's box)
# ---------------------------------------------------------------------------
INBOX_DIR: Path = _path_env("RECEIPT_VAULT_INBOX", "./inbox")
VAULT_DIR: Path = _path_env("RECEIPT_VAULT_HOME", "./vault")
LEDGER_DB: Path = _path_env("RECEIPT_VAULT_DB", str(VAULT_DIR / "ledger.sqlite"))
# Append-only audit trail of what was read, drafted, and sent (Observability pillar).
AUDIT_LOG: Path = _path_env("RECEIPT_VAULT_AUDIT", str(VAULT_DIR / "audit.log"))

# ---------------------------------------------------------------------------
# Watchdog decision thresholds (course concept CR3: the "decision threshold"
# that separates an agent from a one-shot skill).
# ---------------------------------------------------------------------------
# Fire a "return-window-closing" event only when an item is still returnable AND
# has this many days (or fewer) left on its window.
RETURN_WINDOW_THRESHOLD_DAYS: int = _int_env("RECEIPT_VAULT_RETURN_THRESHOLD_DAYS", 7)
# Fire a "warranty-expiring" event when an owned item's warranty lapses within N days.
WARRANTY_THRESHOLD_DAYS: int = _int_env("RECEIPT_VAULT_WARRANTY_THRESHOLD_DAYS", 30)
# A price drop must clear this dollar delta to be worth a price-protection claim.
PRICE_DROP_MIN_DELTA: float = _float_env("RECEIPT_VAULT_PRICE_DROP_MIN_DELTA", 5.00)


def ensure_dirs() -> None:
    """Create the local vault/inbox directories if they do not yet exist.

    Idempotent — safe to call on every startup and from tools.
    """
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
