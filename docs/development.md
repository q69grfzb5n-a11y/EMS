# Development (Windows)

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python env manager)
- Node.js 22+ / npm
- Docker Desktop (WSL2 backend)
- Git, with `.gitattributes` already forcing `* text=auto eol=lf` — do not fight this on Windows checkouts.

## Backend

```powershell
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

`GET /health` → `{"status": "ok", "db": "connected"}`.

Quality gates: `uv run ruff check .`, `uv run mypy app`, `uv run pytest`.

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Quality gates: `npm run lint`, `npm run test -- --run`, `npm run build`.

## Full stack

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Windows-specific notes

- WeasyPrint (Phase 8, PDF export) needs Pango/GTK system libs not available bare on Windows — render only inside the Docker container; a GTK escape hatch for bare-Windows dev will be documented here if needed.
- File-watching in the dockerized frontend uses polling (`CHOKIDAR_USEPOLLING=true`) since native FS events don't cross the Windows↔container boundary reliably.
- Run `scripts/check_all.ps1` (PowerShell) instead of the `.sh` variant.
