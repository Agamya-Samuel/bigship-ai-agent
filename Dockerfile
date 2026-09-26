# ---- base: locked Python with uv ----
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_FROZEN=1
WORKDIR /app

# ---- deps: resolve + install without source (better layer cache) ----
FROM base AS deps
COPY pyproject.toml uv.lock ./
# bigship-sdk is a git dependency — needs git at build time
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && uv sync --no-dev --no-install-project

# ---- runtime ----
FROM base AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser
COPY --from=deps /app/.venv /app/.venv
COPY agent ./agent
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --no-dev --no-install-project --offline || uv sync --no-dev
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app"
USER appuser
EXPOSE 8000
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1
CMD ["uvicorn", "agent.service:app", "--host", "0.0.0.0", "--port", "8000"]
