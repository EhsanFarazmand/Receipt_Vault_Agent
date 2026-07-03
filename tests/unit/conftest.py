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
"""Test isolation: point the ledger at a throwaway DB and pin 'today'.

These env vars are set at import time — before `app.config.settings` is
constructed — so the unit suite never touches a real user ledger and the window
math is deterministic regardless of the wall-clock date.
"""
import os
import tempfile

os.environ.setdefault("RECEIPT_VAULT_TODAY", "2026-07-02")
os.environ.setdefault(
    "RECEIPT_VAULT_DB", os.path.join(tempfile.gettempdir(), "rv_test_ledger.db")
)
# Avoid any real cloud auth during import of the (non-agent) modules under test.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")
os.environ.setdefault("GOOGLE_API_KEY", "test-key-not-used")
