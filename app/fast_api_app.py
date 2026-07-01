"""Cloud Run entrypoint: serves the ADK app over HTTP + a daily Pub/Sub trigger.

`get_fast_api_app` discovers the agent package in ``agents_dir`` (the repo root, which
contains the ``app/`` package) and exposes the standard ADK routes plus a Pub/Sub
trigger endpoint. Cloud Scheduler publishes to a topic on a cron schedule; the topic
is wired to ``/apps/app/trigger/pubsub`` so the Watchdog sweep runs daily with no
interactive user (course: ambient/scheduled agents). See deployment/README.md.

Run locally:   uv run uvicorn app.fast_api_app:app --port 8080
On Cloud Run:  the Dockerfile launches this module with uvicorn.
"""

from __future__ import annotations

import os
from pathlib import Path

from google.adk.cli.fast_api import get_fast_api_app

# The directory that CONTAINS the agent package (`app/`). At repo root that's ".".
AGENTS_DIR = str(Path(__file__).resolve().parent.parent)

# `trigger_sources=["pubsub"]` enables /apps/{app}/trigger/pubsub — how the daily
# Cloud Scheduler → Pub/Sub tick reaches the Watchdog on Cloud Run.
app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    web=os.environ.get("RECEIPT_VAULT_WEB", "false").lower() == "true",
    trigger_sources=["pubsub"],
)
