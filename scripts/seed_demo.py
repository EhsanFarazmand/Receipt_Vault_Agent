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
"""Seed the local ledger with synthetic demo entries.

Dates are relative to today so the wow moment ("6 more days to return the
blender") reproduces whenever you run the demo. No real PII. Run:

    uv run python -m scripts.seed_demo
"""
from __future__ import annotations

from datetime import date, timedelta

from app.tools import vault_tools as vt

DEMO = [
    # blender: 84 days ago at Target (90d) -> 6 days left to return.
    {"vendor": "Target", "days_ago": 84, "total": 79.99, "item": "blender",
     "returnable": True, "return_policy_days": 90, "price_protection_days": 14,
     "warranty_months": 0, "category": "appliance"},
    # 4k monitor: 11 days ago at Amazon (price feed 259 < 299) -> price drop.
    {"vendor": "Amazon", "days_ago": 11, "total": 299.00, "item": "4k monitor",
     "returnable": True, "return_policy_days": 30, "price_protection_days": 30,
     "warranty_months": 12, "category": "electronics"},
    # acme headphones: recalled item -> recall-match.
    {"vendor": "Best Buy", "days_ago": 40, "total": 149.00, "item": "acme headphones",
     "returnable": False, "return_policy_days": 15, "price_protection_days": 0,
     "warranty_months": 12, "category": "electronics"},
    # coffee maker: 120 days ago at Target -> window CLOSED, no nag.
    {"vendor": "Target", "days_ago": 120, "total": 40.0, "item": "coffee maker",
     "returnable": True, "return_policy_days": 90, "price_protection_days": 0,
     "warranty_months": 0, "category": "appliance"},
]


def main() -> None:
    today = date.today()
    for d in DEMO:
        entry = {k: v for k, v in d.items() if k != "days_ago"}
        entry["purchase_date"] = (today - timedelta(days=d["days_ago"])).isoformat()
        entry["source_file"] = f"./vault/{d['item'].replace(' ', '_')}.txt"
        vt.write_ledger(entry)
    print(f"Seeded {len(DEMO)} demo entries as of {today.isoformat()}.")


if __name__ == "__main__":
    main()
