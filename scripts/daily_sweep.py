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
"""Daily watchdog sweep entrypoint (the scheduler's target).

This is what a local cron / Windows Task Scheduler / Cloud Scheduler triggers
each day. It runs the pure sweep (no LLM required) so the "standing watch" keeps
working with zero new input — the irreducible "why an agent" (rule CR3).

    uv run python -m scripts.daily_sweep

Wire it up:
  * Windows:  schtasks /Create /SC DAILY /TN ReceiptVault /TR "uv run python -m scripts.daily_sweep" /ST 08:00
  * Linux:    0 8 * * *  cd /path && uv run python -m scripts.daily_sweep
  * Cloud:    Cloud Scheduler -> Pub/Sub -> the ADK /trigger/pubsub endpoint.
"""
from __future__ import annotations

import json

from app.tools import vault_tools as vt


def main() -> None:
    result = vt.run_daily_sweep()
    # Structured JSON to stdout -> Cloud Logging in a deployed environment.
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["events"]:
        print("Nothing needs your attention today.")
    else:
        top = result["events"][0]
        print(f"\nMost urgent: {top['message']}")


if __name__ == "__main__":
    main()
