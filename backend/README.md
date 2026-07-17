# EMS Backend

FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL 16, managed with [uv](https://docs.astral.sh/uv/).

## Dev setup

```powershell
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

`GET /health` should return `{"status": "ok", "db": "connected"}`.

## Quality gates

```powershell
uv run ruff check .
uv run mypy app
uv run pytest
```
