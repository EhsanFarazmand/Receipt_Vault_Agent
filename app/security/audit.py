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
"""Append-only audit log (7-pillar: Observability / Governance).

Every security-relevant event — a tool call, a sanitization hit, a blocked
send, an approved send — is appended as one JSON line. The log is local,
git-ignored, and never truncated in normal operation, so the "vibe trajectory"
of what the agent read, drafted, and sent is always reconstructable.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app.config import settings


def audit(event: str, **fields) -> dict:
    """Append one structured audit record and return it (for tool responses)."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    settings.audit_path.parent.mkdir(parents=True, exist_ok=True)
    with settings.audit_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record
