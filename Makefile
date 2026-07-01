# Receipt Vault — common commands. (On Windows without `make`, run the commands
# after each target's `:` directly, or use `make` via Git Bash / WSL.)

.PHONY: install seed run web sweep test lint eval-generate eval-grade eval mcp deploy

install:            ## Install deps into a uv-managed venv
	uv sync

seed:               ## Populate the demo ledger from sample_receipts/
	uv run python scripts/seed_demo.py

run:                ## One-off smoke test against the agent (needs GOOGLE_API_KEY)
	agents-cli run "Run today's watchdog sweep and tell me what needs attention."

web:                ## Interactive local playground (ADK web UI)
	agents-cli playground

sweep:              ## Run the daily Watchdog sweep (the standing watch)
	uv run python scripts/daily_watchdog.py

mcp:                ## Start the first-party Receipt Vault MCP server (stdio)
	uv run receipt-vault-mcp

test:               ## Deterministic pytest suite (code correctness, NOT LLM behaviour)
	uv run pytest -q

lint:               ## Ruff lint
	uv run ruff check .

eval-generate:      ## Run the agent over the eval dataset, write traces
	agents-cli eval generate

eval-grade:         ## Grade the traces against tests/eval/eval_config.yaml
	agents-cli eval grade --config tests/eval/eval_config.yaml

eval:               ## generate + grade in one shot
	agents-cli eval run --config tests/eval/eval_config.yaml

deploy:             ## Deploy to Cloud Run (requires GCP auth + explicit approval)
	agents-cli deploy
