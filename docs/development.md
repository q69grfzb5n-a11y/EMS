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

- WeasyPrint (Phase 8, PDF export) needs Pango/GTK system libs not available bare on Windows — render only inside the Docker container (`libpango-1.0-0`/`libpangoft2-1.0-0`/`fonts-noto-core` are already in the backend image from Phase 0). Verified working end-to-end in Phase 8's live demo; no bare-Windows escape hatch has been needed in practice.
- File-watching in the dockerized frontend uses polling (`CHOKIDAR_USEPOLLING=true`) since native FS events don't cross the Windows↔container boundary reliably.
- The **backend's** `uvicorn --reload` does *not* reliably pick up new routes/files across the Windows↔container bind mount either, despite `WatchFiles` reporting it's watching `/app` — seen repeatedly in Phases 7–9 (a brand-new endpoint 404'd until the container was restarted). `docker exec`-based commands (pytest, alembic, one-off scripts) are unaffected since each spawns a fresh process that reads current files regardless of the long-running server's reload state. If a newly-added endpoint 404s during manual/live testing, restart the backend container (`docker restart ems-backend-1`) before assuming it's a real bug.
- Run `scripts/check_all.ps1` (PowerShell) instead of the `.sh` variant.
- `scripts/backup_db.ps1`/`restore_db.ps1` shell out to `cmd.exe` for the actual stdout/stdin redirection rather than using PowerShell's own `>`/`<` — PowerShell 5.1 re-encodes a native command's byte stream as text on redirection, which silently corrupts a binary `pg_dump`/`pg_restore` stream.
