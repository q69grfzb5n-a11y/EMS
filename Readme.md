# Incentive Management System (IMS)

Web application replacing the Excel-based employee incentive tracking tool at SHIBH AL-JAZIRA Factory for Precast Concrete (SAJCO).

**Stack:** FastAPI + PostgreSQL 16 (backend, uv-managed) · React + Vite + TypeScript (frontend) · Docker Compose · bilingual English/Arabic (RTL).

## Start here

| File | Purpose |
|---|---|
| **[RUNNING.md](RUNNING.md)** | **How to run the system** — setup, seeding, tests, troubleshooting |
| [PLAN.md](PLAN.md) | The agreed plan of record — architecture, database schema, decisions, risks |
| [INSTRUCTIONS.md](INSTRUCTIONS.md) | Phase-by-phase build runbook (Phases 0–9, steps + demo gates) |
| [PROGRESS.md](PROGRESS.md) | Live status — per-phase checklists, updated with every commit |
| [docs/source/](docs/source/) | Original Excel workbook, evaluation form drafts, attendance sample (immutable reference) |

## Run it

```bash
cp .env.example .env          # then set SECRET_KEY and POSTGRES_PASSWORD
docker compose up -d --build  # https://localhost
```

Then load the data and sign in — see [RUNNING.md](RUNNING.md) for the full
walkthrough, including the first-login password change and the order the
incentive chain has to be set up in.

## Repository layout

- `backend/` — FastAPI app; one folder per module under `backend/app/modules/`
- `frontend/` — React SPA; one folder per module under `frontend/src/modules/`
- `docs/` — project documentation set (filled in as phases complete)
- `scripts/` — quality-gate and ops scripts

**Status:** all phases (0–9) complete and hardened. Backend 262 tests passing;
`ruff`, `mypy`, `eslint`, `tsc`, `vitest`, production build, and English/Arabic
key-parity checks all green. Runs end to end against the real 440-employee
roster from the source workbook.

Two items remain open by nature rather than by omission, both needing real
stakeholders rather than code: **Arabic wording review by SAJCO staff**, and a
**parallel-month UAT** reconciling the system's output against the legacy Excel
workbook. Both are documented in [PROGRESS.md](PROGRESS.md).
