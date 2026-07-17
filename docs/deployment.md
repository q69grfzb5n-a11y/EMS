# Deployment

> Status: skeleton — full production walkthrough + backup/restore drill added in Phase 9.

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

`scripts/backup_db.sh` (pg_dump -Fc, daily) + restore drill — added Phase 9.

## Production walkthrough

_Added in Phase 9 alongside the hardening pass._
