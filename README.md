# Receipt Vault 🧾🔒

**The receipt agent that watches your return windows, warranties, recalls, and price drops — and acts before they expire.**

**Track:** Concierge Agents · Kaggle *AI Agents: Intensive Vibe Coding* Capstone with Google

**📹 Demo video:** [Watch the 5-minute walkthrough](https://youtu.be/BAWezTeheWs)

> **Wow moment:** Drop a shoebox of receipt photos in a folder. Seconds later you have a searchable ledger **and** a nudge:
> *"You can still return the blender for 6 more days — and it's $18 cheaper now. Want me to file the price-adjustment too?"*

---

## The problem

The receipt is the most-lost financial document in the home, and losing it is quietly expensive. Behind every receipt sits a cluster of deadlines nobody tracks: a **return window** that closes in 30/60/90 days, a **warranty** that must be registered, a **safety recall** announced months later, a **price-protection** window during which a refund of the difference is yours for the asking. We keep receipts in a shoebox and only look when something breaks — by then the window has closed.

## Why an agent, not a single LLM call

A model can read *one* receipt — that's a **skill**, one input → one output → done. The real problem is **standing watch over every deadline attached to every purchase, every day, and acting on the one that matters today.** That needs a stateful ledger across hundreds of receipts, a daily self-scheduled sweep, a decision threshold, per-merchant policy lookup, and an outbound action held for human approval — a multi-step, stateful, autonomous loop. **The "day 2" test:** drop nothing new in, and Receipt Vault still wakes, counts down every open window, polls recall + price feeds, and escalates the one thing you need today. That standing watch is the irreducible *why an agent*.

## Architecture (multi-agent, ADK)

An **Orchestrator** (ADK root agent) routes each event to one of four specialists, each with a narrow tool set and its own security tier. Beneath them sit the **Receipt Vault MCP** tool surface and a **Policy Server** that intercepts every tool call.

```
  Watched folder ─┐                    ┌─ Daily scheduler (cron / Cloud Scheduler)
  Forwarded email ─┼──▶  ORCHESTRATOR  ◀┘
  Drag-and-drop  ─┘     (routes by intent + state)
        ┌───────────────┬───────────────┬────────────────┐
        ▼               ▼               ▼                ▼
   INTAKE &         LEDGER          WATCHDOG          ACTION /
   EXTRACTION       AGENT           AGENT             DRAFTING
   (Read/Draft)     (Action-local)  (Read-only) ◀ the (Draft-only,
   OCR→sanitize→    normalize,      agentic core:     human sends)
   extract→file     dedupe, query   daily window math,
                                    recall+price feeds
        └───────────────┴──────┬────────┴────────────────┘
                               ▼
              RECEIPT VAULT MCP  (scan_inbox, ocr_receipt, extract_fields,
              (first-party tools) write_ledger, query_ledger, compute_windows,
                               ▼  check_recalls, run_daily_sweep, draft_action)
              POLICY SERVER / ZERO-TRUST GATEWAY
              (structural + semantic gating, Vibe Diff)  ← every tool call
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full data flow and security model.

## Course concepts → where they live (all 6 implemented)

| Concept | Where in this repo |
| :-- | :-- |
| **Multi-agent (ADK)** | [`app/agent.py`](app/agent.py) (Orchestrator + `sub_agents`) and [`app/sub_agents/`](app/sub_agents/) (4 specialists, factory functions, per-agent tier). |
| **MCP server** | First-party [`mcp_server/server.py`](mcp_server/server.py) (FastMCP, the "USB-C" tool surface). Designed to consume external Gmail/Calendar/Filesystem MCPs for outbound (wire-in point in [`send_action`](app/tools/vault_tools.py); see ARCHITECTURE). |
| **Agent skills** | [`skills/`](skills/) — 4 `SKILL.md` modules with progressive disclosure + Read/Draft/Action tiers. |
| **Security** | [`app/security/sanitize.py`](app/security/sanitize.py) (PII redaction + prompt-injection), [`app/security/audit.py`](app/security/audit.py) (audit trail), [`app/policy/policy_server.py`](app/policy/policy_server.py) (structural + semantic gating, Vibe Diff). |
| **Deployability** | Local-first single command **plus a verified Cloud Run deploy** (private, Vertex-backed) — [`Dockerfile`](Dockerfile) + Terraform under [`deployment/`](deployment/); daily sweep via [`scripts/daily_sweep.py`](scripts/daily_sweep.py). |
| **Antigravity / Spec-driven** | Gherkin specs in [`specs/receipt_vault.feature`](specs/receipt_vault.feature) drive the build; shown in the [demo video](https://youtu.be/BAWezTeheWs). |

## Quickstart (local-first)

```bash
# 0. From the project dir, with uv installed (https://docs.astral.sh/uv/)
cp .env.example .env          # add your GOOGLE_API_KEY (AI Studio) — never commit .env
uv sync                       # install deps into .venv

# 1. Prove the logic (no model / no credentials needed) — 23 unit tests
uv run pytest tests/unit -q

# 2. Seed synthetic demo receipts (dates relative to today, no real PII)
uv run python -m scripts.seed_demo

# 3. Run the daily watchdog sweep — the "day 2" standing watch (no LLM needed)
uv run python -m scripts.daily_sweep
#   → "Most urgent: You can still return the blender for 6 more day(s)."

# 4. Talk to the full multi-agent system (needs model credentials)
agents-cli playground         # or: uv run adk run app
```

The first-party MCP server runs standalone over stdio:
```bash
uv run python -m mcp_server.server
```

> **Full demo runbook:** [`DEMO.md`](DEMO.md) has copy-paste seed prompts, the
> six-capability demo sequence (watchdog, ledger query, injection defense, approval
> gate), and a timed 5-minute video beat sheet.

## Evaluation (tests-as-eval)

The Gherkin scenarios are both acceptance tests and the eval set.
- **Deterministic logic** → `uv run pytest tests/unit` (23 tests: window math, sanitizer, policy gate, ledger dedupe/sweep).
- **Agent behaviour** → seed the ledger, then:
  ```bash
  uv run python -m scripts.seed_demo
  agents-cli eval run           # generate traces + grade (needs model creds)
  ```
  Metrics live in [`tests/eval/eval_config.yaml`](tests/eval/eval_config.yaml): `final_response_quality`, `multi_turn_tool_use_quality`, plus custom judges `security_injection_defense` and `approval_gate_respected`. Dataset: [`tests/eval/datasets/basic-dataset.json`](tests/eval/datasets/basic-dataset.json).

## Deploy (Cloud Run — verified)

Prototype-first: the agent runs fully locally. Cloud Run infra was added with
`agents-cli scaffold enhance . --deployment-target cloud_run` (Terraform under
[`deployment/`](deployment/)), and the service has been **deployed and driven
end-to-end** — private, IAM-gated, running on Vertex AI.

```bash
agents-cli deploy --project <your-gcp-project>                       # explicit approval + GCP project
gcloud run services proxy <service> --region <region> --project <p>  # private access to the Dev UI
```

Everything Cloud Run needs is handled in code / Terraform:
- **Writable paths auto-route to `/tmp`** on Cloud Run (`K_SERVICE` detection in [`app/config.py`](app/config.py)) — the container FS is otherwise read-only.
- **Model auth via the service account** (Vertex, `GOOGLE_CLOUD_LOCATION=global`) — no keys in the image; the runtime SA is granted `roles/aiplatform.user` by Terraform.
- **Scheduled sweep:** run [`scripts/daily_sweep.py`](scripts/daily_sweep.py) locally, or on Cloud via Cloud Scheduler → the ADK trigger endpoint.

See [`DEMO.md`](DEMO.md) for the demo runbook. Full data-flow + security model in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Privacy & security (structural, not promised)

- **Local-first** — OCR, extraction, ledger, and vault all live on your machine. `vault/`, `data/`, and `audit/` are git-ignored; your purchase history is never uploaded or tracked.
- **PII redaction before any model call** — card numbers → last-4 only, addresses masked ([`sanitize.py`](app/security/sanitize.py)).
- **Prompt-injection defense** — untrusted OCR text is neutralised + fenced and treated as *data, never instructions* (defends the Confused Deputy problem).
- **Approval gate on every send** — the Policy Server blocks outbound actions and shows a plain-language **Vibe Diff**; the human sends.
- **No secrets in code** — everything via `.env` (git-ignored); `.env.example` documents the vars.

## Repo layout

```
app/                    ADK agent code
├── agent.py            Orchestrator (root agent) + App(name="app")
├── fast_api_app.py     Cloud Run serving entrypoint (ADK FastAPI app + /feedback)
├── config.py           models, paths, decision thresholds
├── watchdog_core.py    pure window math (the agentic core) — unit-tested
├── data_sources.py     synthetic merchant policies + recall/price feeds
├── sub_agents/         intake · ledger · watchdog · action (per-agent tiers)
├── tools/              the vault tool functions
├── ledger/             local SQLite ledger (stdlib sqlite3)
├── security/           sanitize (PII + injection) · audit log
├── policy/             Policy Server (before_tool_callback gate + Vibe Diff)
└── app_utils/          telemetry + Feedback typing (Cloud Run serving helpers)
mcp_server/server.py    first-party Receipt Vault MCP (FastMCP)
skills/                 4 SKILL.md modules (progressive disclosure, tiers)
specs/                  Gherkin (acceptance = eval)
scripts/                seed_demo · daily_sweep (scheduler entrypoint)
sample_receipts/        synthetic receipts (incl. an injection test), no real PII
tests/unit/             23 pure-logic tests mirroring the Gherkin scenarios
deployment/             Cloud Run Terraform (single-project) from `scaffold enhance`
DEMO.md                 test + demo runbook: seed prompts, capability sequence, video beats
ARCHITECTURE.md         data flow + 7-pillar security model + deployment notes
LICENSE                 Apache License 2.0
```

## License

Licensed under the [Apache License 2.0](LICENSE). Each source file carries the
standard Apache 2.0 header.

---
*Generated with `agents-cli` v0.5.0 (adk template) and built out per the Receipt Vault blueprint. See `CLAUDE.md` for the coding-agent workflow.*
