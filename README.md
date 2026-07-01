# Receipt Vault 🧾🔒

**The receipt agent that watches your return windows, warranties, recalls, and price drops — and acts before they expire.**

> Drop a shoebox of receipt photos in a folder. Seconds later: a searchable ledger **and** a notification —
> *"You can still return the blender for 6 more days — and it's $18 cheaper now. Want me to file the price-adjustment too?"*

**Track:** Concierge Agents · **Built on:** Google [Agent Development Kit (ADK)](https://adk.dev) + the `agents-cli` workflow · **Capstone:** Kaggle *AI Agents: Intensive Vibe Coding* with Google.

---

## The problem

The receipt is the most-lost financial document in the home, and losing it is quietly expensive: missed return windows, warranties that lapse on a technicality, safety recalls nobody hears about, and price-protection refunds left on the table. We keep a shoebox — physical or digital — and only dig through it a day after the window closed.

## Why an agent (not a single LLM call)

A model can read *one* receipt — that's a **skill**. Receipt Vault's job is to **stand watch over every deadline attached to every purchase, every day, and act on the one that matters today.** Drop nothing new in and it *still* wakes, counts down every open window, polls the recall feed, watches for price drops, and escalates the single thing you need to act on. That standing watch — stateful, scheduled, autonomous, threshold-gated — is the irreducible "why an agent."

## What it does

1. **Intake** — you drop receipts into a watched folder. Each is OCR'd in a sandbox, sanitized, and extracted to `{vendor, date, total, last4, category, returnable}`.
2. **Ledger** — entries are normalized, deduped, and written to a **local SQLite ledger** (with an `.xlsx` export). It answers *"how much did I spend on appliances?"*
3. **Watchdog (the agentic core)** — a daily sweep computes days-left on return / price-protection / warranty windows, polls a recall feed, and raises a structured **action event** when a threshold is crossed.
4. **Action / Drafting** — turns an event into a drafted return / price-adjustment / warranty / recall message and routes it to **you for approval before anything is sent** (the *Vibe Diff*).

---

## Architecture (multi-agent, ADK)

An **Orchestrator** (ADK root agent) routes each event to one of four specialist sub-agents, over a shared MCP tool surface, behind a zero-trust Policy Server. Full detail in [ARCHITECTURE.md](ARCHITECTURE.md).

```
   Watched folder ─┐                  ┌──────────────────────┐   ┌── Daily scheduler
   Forwarded email ─┼───────────────▶ │     ORCHESTRATOR     │ ◀─┘   (cron / Pub/Sub)
   Drag-and-drop  ──┘                  │  (ADK root agent)    │
                                       └──────────┬───────────┘
             ┌──────────────┬─────────────────────┼───────────────────┬──────────────┐
             ▼              ▼                     ▼                    ▼
      ┌────────────┐ ┌────────────┐       ┌────────────┐       ┌────────────┐
      │  INTAKE &  │ │  LEDGER    │       │  WATCHDOG  │       │  ACTION /  │
      │ EXTRACTION │ │  AGENT     │       │  AGENT     │       │  DRAFTING  │
      │ read-only  │ │ local write│       │ read-only  │       │ draft-only │
      └────────────┘ └────────────┘       └────────────┘       └────────────┘
             └──────────────┴──────────┬──────────┴────────────────┘
                                       ▼
                        ┌────────────────────────────────┐
                        │  RECEIPT VAULT MCP SERVER       │  first-party tool surface
                        │  + consumes Gmail/Calendar/Files│  (mcp_server/server.py)
                        └────────────────┬───────────────┘
                                         ▼
                        ┌────────────────────────────────┐
                        │  POLICY SERVER / ZERO-TRUST     │  intercepts every tool call
                        │  (structural + semantic + Vibe  │  (app/security/policy_server.py)
                        │   Diff)                         │
                        └────────────────────────────────┘
```

---

## Course concepts → where in the code

The capstone asks for **≥3** of six concepts; Receipt Vault implements **all six**.

| Course concept | Where in this repo |
| :--- | :--- |
| **Multi-agent system (ADK)** | [app/agent.py](app/agent.py) (Orchestrator) + [app/sub_agents/](app/sub_agents/) (4 specialists, per-agent tier) |
| **MCP Server** | First-party [mcp_server/server.py](mcp_server/server.py); consumes Gmail/Calendar/Filesystem MCPs (see ARCHITECTURE) |
| **Agent skills** | [skills/](skills/) — 4 `SKILL.md` with progressive disclosure + tier metadata; per-merchant policy resource loaded on demand |
| **Security features** | [app/security/sanitize.py](app/security/sanitize.py) (PII redaction + injection defense), [app/security/policy_server.py](app/security/policy_server.py) (zero-trust gating + Vibe Diff) |
| **Deployability** | Local-first (`adk web`), optional [Dockerfile](Dockerfile) + [deployment/](deployment/) (Cloud Run + Cloud Scheduler) |
| **Antigravity** | Built spec-first ([specs/](specs/) Gherkin) in Google Antigravity — shown in the video |

---

## Quickstart (local-first)

Prereqs: Python 3.10+, [`uv`](https://docs.astral.sh/uv/), and the `agents-cli`
(`uv tool install google-agents-cli`). A Google AI Studio key for the model.

```bash
# 1. Configure (NO secrets in code). ADK loads the AGENT dir's env file — app/.env.
cp app/.env.example app/.env   # then set GOOGLE_API_KEY  (Windows: copy app\.env.example app\.env)

# 2. Install (generates uv.lock — commit it: real supply-chain pinning)
uv sync

# 3. Seed the demo ledger from the synthetic sample receipts
uv run python scripts/seed_demo.py

# 4a. Talk to the agent interactively
agents-cli playground          # or: uv run adk web

# 4b. Or run the standing-watch sweep directly
uv run python scripts/daily_watchdog.py 2026-07-01
#   → raises price-drop (monitor -$40), warranty-expiring + recall (headphones)

# 5. Deterministic tests (code correctness) and behavioural eval (agent quality)
uv run pytest -q                                          # 21 tests, no LLM
uv run python scripts/local_eval.py --model gemini-flash-lite-latest --delay 20
#   local AI-Studio eval (no GCP). agents-cli eval also works if you have a GCP project:
#   agents-cli eval run --config tests/eval/eval_config.yaml
```

See [docs/EVALUATION.md](docs/EVALUATION.md) for the eval methodology and results (21 pytest + 5/5 agent-behaviour cases).

Register the daily sweep with your OS scheduler (Task Scheduler / cron) so the agent
keeps watch — snippets are in [scripts/daily_watchdog.py](scripts/daily_watchdog.py).

---

## Security & privacy (structural, not promised)

- **Local-first:** OCR, extraction, ledger, and vault all live on your machine. Nothing leaves except model-reasoning calls you opt into and outbound drafts **you approve**.
- **PII redaction before any model call:** card numbers → `****last4`, addresses/emails masked ([sanitize.py](app/security/sanitize.py)).
- **Prompt-injection defense:** OCR text is treated as **data, never instructions** — a malicious "receipt" cannot make the agent exfiltrate the ledger (tested in [tests/unit/test_sanitize.py](tests/unit/test_sanitize.py) and [specs/prompt_injection.feature](specs/prompt_injection.feature)).
- **Zero-trust Policy Server:** every tool call is gated — local writes confined to the vault, outbound recipients confined to the merchant domain, and every outbound send held behind a plain-language **Vibe Diff** approval ([policy_server.py](app/security/policy_server.py)).
- **No secrets in the repo:** `.env` is git-ignored; only `.env.example` is committed. Dependencies are version-bounded + lock-filed (slopsquatting defense).

## Testing philosophy

- `uv run pytest` — deterministic **code correctness** (sanitizer, policy gates, window math, ledger dedupe). 21 tests, no LLM.
- `scripts/local_eval.py` — non-deterministic **agent behaviour** on the real multi-agent system, local-first via the ADK `InMemoryRunner` (no GCP needed). 5/5 cases pass. `agents-cli eval` is the Vertex-based equivalent if you have a GCP project. See [docs/EVALUATION.md](docs/EVALUATION.md).

Behavioural rules are pinned as Gherkin in [specs/](specs/) — the acceptance tests and the eval set at once.

## Repo layout

```
app/            ADK app: agent.py (orchestrator), sub_agents/, tools/, domain/, security/
mcp_server/     first-party Receipt Vault MCP server (stdio)
skills/         4 SKILL.md modules (progressive disclosure, tiered)
specs/          Gherkin acceptance/eval scenarios
tests/          pytest (unit) + eval (dataset + config)
scripts/        seed_demo.py, daily_watchdog.py (the standing watch)
deployment/     Cloud Run + Cloud Scheduler notes; Dockerfile at root
sample_receipts/ synthetic receipts (no real PII), incl. one injection attempt
```

Apache-2.0. Built for the Kaggle *AI Agents: Intensive Vibe Coding* capstone.
