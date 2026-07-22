# Deployment

## Compose profiles

- `docker-compose.yml` (base, prod-shaped): postgres:16-alpine (healthcheck, named volume, no published port), backend (prod target, depends on healthy postgres), frontend (nginx, port 80, `/api` proxy → backend:8000 — single origin, no CORS).
- `docker-compose.dev.yml` (override): backend dev target with bind mount + `--reload` on port 8000; frontend as a node container running `vite --host` with a named `node_modules` volume; postgres port 5432 exposed.

```powershell
# dev
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# prod-shaped
docker compose up
```

Entrypoint runs `alembic upgrade head` before starting the app; seeds are always run explicitly (`backend/scripts/seed.py`), never automatically.

## Backups

`scripts/backup_db.sh` (bash) / `scripts/backup_db.ps1` (PowerShell) — `pg_dump -Fc`
(custom format, compressed) against the running Postgres container, reading
`POSTGRES_USER`/`POSTGRES_DB` from the container's own environment so the
script never needs its own copy of secrets. Writes to `backups/` (gitignored)
by default; pass a directory as the first argument to write elsewhere (e.g. a
mounted network share for off-box retention).

```powershell
# from repo root
./scripts/backup_db.ps1
# ./scripts/backup_db.ps1 D:\ems-backups
```

```bash
./scripts/backup_db.sh
# ./scripts/backup_db.sh /mnt/ems-backups
```

Run this on a schedule (Task Scheduler / cron) against the prod-profile stack;
a daily cadence is reasonable given the incentive cycle is monthly.

### Restore drill

`scripts/restore_db.sh` / `scripts/restore_db.ps1` — `pg_restore --clean --if-exists`
against a backup file. **Destructive**: drops and recreates every object in the
target database before restoring, so only ever point it at a database you mean
to overwrite (a scratch/staging Postgres, or the real one during an actual
incident).

```powershell
./scripts/restore_db.ps1 .\backups\ems_backup_20260721_120000.dump
```

```bash
./scripts/restore_db.sh backups/ems_backup_20260721_120000.dump
```

The Windows `.ps1` variants delegate the actual stdout/stdin redirection to
`cmd.exe` rather than PowerShell's own `>`/`<` operators — PowerShell 5.1
re-encodes a native command's byte stream as text on redirection, which
silently corrupts a binary `pg_dump`/`pg_restore` stream.

**Rehearsed 2026-07-21** (see PROGRESS.md Phase 9 notes for the full live
transcript): against the isolated `ems-prod-validation` stack (seeded with the
real 440-employee roster), took a `pg_dump -Fc` backup, deliberately deleted
every row from `employees` to simulate data loss (confirmed count dropped to
0), then restored from the backup and confirmed all 440 rows came back — run
once with the bash scripts and once with the PowerShell scripts (`cmd.exe`
redirection workaround), both giving an identical result.

## Production walkthrough

Rehearsed 2026-07-21 on this machine — see PROGRESS.md Phase 9 notes for the
full transcript (fresh migrations, core seed, the real legacy roster import,
and an RBAC + bilingual spot-check, all run against the prod-shaped
single-origin stack rather than the dev stack used throughout Phases 0–8).
The business-workflow demo gates themselves (attendance → evaluations →
incentive runs → reports) were already proven live in Phases 3–8 against real
data; this pass exists to validate the *deployment topology* — the prod
Docker target, the single-origin nginx proxy, and the seed/import scripts —
not to repeat that walkthrough a second time on a throwaway database.

```powershell
docker compose up --build
```

- Postgres has no published port (only reachable from other containers on the
  compose network) and a named volume for data durability across restarts.
- Backend runs the `prod` Dockerfile target (no dev deps, no bind mount,
  `uvicorn` without `--reload`).
- Frontend is nginx serving the built SPA on port 80, proxying `/api/*` to
  `backend:8000` — single origin, no CORS configuration needed anywhere.
- The entrypoint always runs `alembic upgrade head` before the app starts;
  seeding (`backend/scripts/seed.py --core`, `backend/scripts/import_legacy.py`)
  is always a separate, explicit step — never automatic — so a production
  restart never silently re-seeds or re-imports real data.
