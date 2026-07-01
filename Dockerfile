# Receipt Vault — Cloud Run container (single-stage, uv-managed deps).
# Local-first by default; this image is the OPTIONAL headless deployment path
# (course: Deployability). No inbound ports beyond the one Cloud Run injects.

FROM python:3.12-slim

# uv for fast, reproducible installs from the committed lockfile (supply-chain safety).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /srv

# Install dependencies first (better layer caching). Copy lock + manifest, then sync.
COPY pyproject.toml ./
COPY uv.lock* ./
RUN uv sync --no-dev --frozen || uv sync --no-dev

# App code
COPY app ./app
COPY mcp_server ./mcp_server
COPY scripts ./scripts

# Cloud Run provides $PORT (default 8080). Serve the ADK FastAPI app.
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port ${PORT}"]
