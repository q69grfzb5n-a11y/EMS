FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

# --- dev target: editable install with dev dependencies, source bind-mounted at runtime ---
FROM base AS dev
RUN uv sync --frozen --no-install-project
COPY . .
RUN uv sync --frozen
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# --- prod target: no dev deps, no bind mount ---
FROM base AS prod
# Also covers `uv run` at container runtime (entrypoint.sh, CMD): without these,
# uv's implicit sync-before-run re-installs the dev dependency group (mypy, ruff, ...)
# on every container start, which both defeats this stage's --no-dev build and would
# hard-fail in a real network-isolated production host with no PyPI egress.
ENV UV_FROZEN=1 \
    UV_NO_DEV=1
RUN uv sync --frozen --no-install-project --no-dev
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini README.md ./
COPY scripts ./scripts
RUN uv sync --frozen --no-dev
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
