#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> backend: ruff"
(cd backend && uv run ruff check .)

echo "==> backend: mypy"
(cd backend && uv run mypy app)

echo "==> backend: pytest"
(cd backend && uv run pytest)

echo "==> frontend: eslint"
(cd frontend && npm run lint)

echo "==> frontend: vitest"
(cd frontend && npm run test -- --run)

echo "==> frontend: build"
(cd frontend && npm run build)

echo "==> line limits"
python3 scripts/check_line_limits.py

echo "All quality gates passed."
