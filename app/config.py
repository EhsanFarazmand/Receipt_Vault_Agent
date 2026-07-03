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
"""Central configuration for Receipt Vault.

Every runtime knob — model, local paths, and the *decision thresholds* that turn
passive ledger data into an autonomous action (rule CR3) — is read from an
environment variable with a safe, local-first default. Nothing sensitive is
hard-coded, and the whole system runs offline on the user's machine by default.

Thresholds live here (not scattered inside agent prompts) so they are typed,
discoverable, and unit-testable in isolation from any LLM call.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# The scaffold validated `gemini-flash-latest`; we keep a single model constant
# so we never drift into a hallucinated / 404 model name. (Per CLAUDE.md: do not
# change the model unless explicitly asked.) The orchestrator and the four
# specialists all use it — cheap, fast, and enough for this task decomposition.
MODEL = os.getenv("RECEIPT_VAULT_MODEL", "gemini-flash-latest")


# Cloud Run (and most serverless container runtimes) mount a READ-ONLY root
# filesystem with only /tmp writable, and always set K_SERVICE. When we detect
# that, the writable working dirs default under /tmp so the ledger/vault/audit
# writes don't crash the service. Locally, K_SERVICE is unset -> "." as before.
# Explicit RECEIPT_VAULT_* env vars still override either default.
_WRITABLE_BASE = "/tmp" if os.getenv("K_SERVICE") else "."


def _path(env: str, default: str) -> Path:
    return Path(os.getenv(env, default)).expanduser().resolve()


@dataclass(frozen=True)
class Settings:
    # --- Working directories (local-first; on Cloud Run these live under /tmp) ---
    inbox: Path = _path("RECEIPT_VAULT_INBOX", f"{_WRITABLE_BASE}/inbox")
    store: Path = _path("RECEIPT_VAULT_STORE", f"{_WRITABLE_BASE}/vault")
    db_path: Path = _path("RECEIPT_VAULT_DB", f"{_WRITABLE_BASE}/data/receipt_vault.db")
    audit_path: Path = _path("RECEIPT_VAULT_AUDIT", f"{_WRITABLE_BASE}/audit/audit.log")

    # --- Decision thresholds (rule CR3): fire only when a window crosses these.
    return_alert_days: int = int(os.getenv("RECEIPT_VAULT_RETURN_ALERT_DAYS", "7"))
    warranty_alert_days: int = int(os.getenv("RECEIPT_VAULT_WARRANTY_ALERT_DAYS", "30"))

    def ensure_dirs(self) -> None:
        """Create the local working directories on first use (idempotent)."""
        for p in (self.inbox, self.store, self.db_path.parent, self.audit_path.parent):
            p.mkdir(parents=True, exist_ok=True)


settings = Settings()
