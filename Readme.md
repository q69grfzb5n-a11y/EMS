# Incentive Management System (IMS)

Web application replacing the Excel-based employee incentive tracking tool at SHIBH AL-JAZIRA Factory for Precast Concrete (SAJCO).

**Stack:** FastAPI + PostgreSQL 16 (backend, uv-managed) · React + Vite + TypeScript (frontend) · Docker Compose · bilingual English/Arabic (RTL).

## Start here

| File | Purpose |
|---|---|
| [PLAN.md](PLAN.md) | The agreed plan of record — architecture, database schema, decisions, risks |
| [INSTRUCTIONS.md](INSTRUCTIONS.md) | Phase-by-phase build runbook (Phases 0–9, steps + demo gates) |
| [PROGRESS.md](PROGRESS.md) | Live status — per-phase checklists, updated with every commit |
| [docs/source/](docs/source/) | Original Excel workbook, evaluation form drafts, attendance sample (immutable reference) |

## Repository layout

- `backend/` — FastAPI app; one folder per module under `backend/app/modules/`
- `frontend/` — React SPA; one folder per module under `frontend/src/modules/`
- `docs/` — project documentation set (filled in as phases complete)
- `scripts/` — quality-gate and ops scripts

**Status:** planning complete, folder structure in place. Code scaffolding begins with Phase 0 (see INSTRUCTIONS.md).
