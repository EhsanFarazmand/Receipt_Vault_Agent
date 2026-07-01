"""Daily Watchdog entrypoint — the standing watch that makes Receipt Vault an agent.

Register this with a local scheduler so the sweep runs every day with NO new input
(course CR3: continuous monitoring / the "day 2" test). Deployed on Cloud Run, the
same job is triggered by Cloud Scheduler → Pub/Sub instead (see deployment/).

Local scheduling:
  * Windows (Task Scheduler):
      schtasks /Create /SC DAILY /TN "ReceiptVaultWatchdog" /ST 20:00 ^
        /TR "\"%CD%\\.venv\\Scripts\\python.exe\" \"%CD%\\scripts\\daily_watchdog.py\""
  * macOS/Linux (cron, 8 PM daily):
      0 20 * * *  cd /path/to/receipt-vault && .venv/bin/python scripts/daily_watchdog.py

It emits results as structured JSON to stdout so a scheduler/Cloud Logging can pick
them up, and appends a line to the audit log. It NEVER sends anything — it only raises
events; acting on them stays behind the human approval gate in the Action agent.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

# Make `app` importable when a scheduler invokes this script directly (not via `uv run`).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.tools.watchdog_tools import run_daily_sweep  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    # Optional ISO date arg lets you simulate a specific "today" for demos/tests.
    reference_date = argv[0] if argv else ""
    result = run_daily_sweep(reference_date)
    events = result.get("events", [])

    # Structured line for logs / Cloud Logging.
    print(json.dumps({"sweep": reference_date or date.today().isoformat(), **result}))

    # Human-friendly summary, most time-sensitive first.
    ranked = sorted(events, key=lambda e: (e.get("days_left") is None, e.get("days_left", 1e9)))
    if not ranked:
        print("Watchdog: nothing crosses a threshold today. Standing watch continues.")
    else:
        print(f"Watchdog raised {len(ranked)} event(s):")
        for e in ranked:
            print(f"  • [{e['kind']}] {e['message']}")

    try:
        config.AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with config.AUDIT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"{date.today().isoformat()}\tSWEEP\t{len(ranked)} events\n")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
