"""Pytest configuration: sandbox the vault into a temp dir BEFORE app.config imports.

`app.config` reads its paths from the environment at import time, so we set them here
(conftest is imported before any test module) to keep tests hermetic — they never
touch the developer's real ./vault or ./inbox.
"""

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="receipt_vault_tests_"))
os.environ["RECEIPT_VAULT_HOME"] = str(_TMP / "vault")
os.environ["RECEIPT_VAULT_DB"] = str(_TMP / "vault" / "ledger.sqlite")
os.environ["RECEIPT_VAULT_INBOX"] = str(_TMP / "inbox")
os.environ["RECEIPT_VAULT_AUDIT"] = str(_TMP / "vault" / "audit.log")


import pytest  # noqa: E402

from app.domain import ledger  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_ledger():
    """Give each test a fresh ledger table."""
    db = Path(os.environ["RECEIPT_VAULT_DB"])
    if db.exists():
        db.unlink()
    ledger.init_db()
    yield
