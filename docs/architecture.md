# Architecture

> Status: skeleton — filled in as each phase lands. See [PLAN.md](../PLAN.md) for the agreed design.

## System overview

FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL 16 backend, React 18 + Vite + TypeScript SPA frontend, Docker Compose deployment, single-origin via nginx `/api` proxy (no CORS). See [PLAN.md §2–4](../PLAN.md).

## Backend module layout

Each module under `backend/app/modules/<name>/` owns `router.py`, `service.py`, `models.py`, `schemas.py`. Pure business logic (calculation engine, workflow engine, importers) lives in dedicated zero-DB-dependency files — see [calculation-engine.md](calculation-engine.md) and [workflows.md](workflows.md).

## Frontend module layout

Each module under `frontend/src/modules/<name>/` owns `api/ components/ pages/ types.ts locales/{en,ar}.json index.ts`. RTL/i18n choke point: `src/app/providers/LocaleProvider.tsx`.

## Diagrams

_To add: component diagram, request-flow diagram (Phase 0–1), deployment diagram (Phase 9)._
