# PROGRESS

Living status tracker. Rule: update this file **in the same commit** as the work it describes. Checklists mirror [INSTRUCTIONS.md](INSTRUCTIONS.md); details/rationale in [PLAN.md](PLAN.md).

**Legend:** `[ ]` pending · `[x]` done · status per phase: `not started | in progress | done`

---

## Pre-Phase — Planning & Repo Setup   [status: done]  (2026-07-16)
- [x] Source files analyzed (xlsm formulas, 3 Word drafts, attendance format extracted & verified)
- [x] Stack + business decisions confirmed with owner (see PLAN §2)
- [x] PLAN.md, INSTRUCTIONS.md, PROGRESS.md written
- [x] git init; source files moved to `docs/source/`
- [x] Complete folder structure created (backend/frontend/docs/scripts, all module folders)
### Notes / deviations
- 2026-07-16: Code scaffolding intentionally deferred — user instructed planning files + folder structure only.
- 2026-07-17: Correction — `git init` had **not** actually been run as of 2026-07-16 despite the checklist above; the repo was initialized today and the Phase 0 scaffold is its root commit.

## Phase 0 — Scaffolding & Dev Environment   [status: done]   (2026-07-17)
- [x] Root meta files (.gitattributes, .editorconfig, .env.example)
- [x] scripts/check_line_limits.py + check_all.ps1/.sh
- [x] Backend: uv project + FastAPI /health + SQLAlchemy base + Alembic wired
- [x] Backend Dockerfile (dev+prod targets) + entrypoint.sh (LF)
- [x] Frontend: Vite React TS + antd + i18next EN/AR + RTL flip + AppShell
- [x] Frontend Dockerfile + nginx.conf (/api proxy)
- [x] docker-compose.yml + docker-compose.dev.yml
- [x] CI workflow + pre-commit hooks
- [x] docs/ skeleton files
- [x] DEMO GATE: compose up boots bilingual stack; all gates green
### Notes / deviations
- 2026-07-17: Docker Desktop + WSL2 installed on the dev machine (were missing). Full demo gate verified end-to-end:
  - `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build` → `GET /health` on :8000 returns `{"status":"ok","db":"connected"}` against the real postgres container; frontend on :5173 serves the Arabic RTL shell.
  - `docker compose up --build` (prod-shaped, single-origin) → frontend on :80 serves the RTL shell via nginx; `/api/v1/*` proxies through to the backend (confirmed via a live FastAPI 404, not an nginx gateway error); backend `/health` (not published, checked via `docker exec`) returns `db:"connected"`.
  - Fixed two real bugs surfaced only by the actual Docker build (not caught by bare-metal `uv run`): (1) `backend/Dockerfile` ran `uv sync` before `app/__init__.py` was copied into the image — split into a cached deps-only `uv sync --no-install-project` layer followed by the real sync after `COPY`; (2) the prod stage didn't copy `README.md`, which `pyproject.toml`'s `readme =` field requires at build time.
- 2026-07-17: `uv init` initially created a nested git repo + `src/` package layout inside `backend/`; removed and rebuilt to the flat `app/` layout INSTRUCTIONS.md specifies.
- 2026-07-17: docs/ skeleton written per PLAN §10 (architecture, database-schema, api-reference, calculation-engine, user-roles, workflows, attendance-import, kpi-templates, deployment, development, i18n-guide, ADR template). **`docs/source/` is empty** — the real workbook/Word/attendance files PLAN.md references (`Precast Incentives 03-2026 (1).xlsm`, 3 Word drafts, Oracle attendance export) are not actually in the repo yet; needed before Phase 2/7 can proceed for real.
- 2026-07-17: docs/ skeleton files (architecture.md, database-schema.md, etc. per PLAN §10) deferred — not blocking the demo gate, will add alongside the content they document.

## Phase 1 — Auth, Users, RBAC   [status: not started]
- [ ] users/roles/user_roles/refresh_tokens models + migration
- [ ] bcrypt + JWT + refresh rotation (httpOnly cookie)
- [ ] login / refresh / logout / me / change-password endpoints
- [ ] require_roles dependency + HR-only role grants (admin excluded)
- [ ] audit_log table + write_audit core, wired to auth events
- [ ] seed: 9 roles + admin user (forced password change)
- [ ] Frontend: login, authStore, guards, permissions.ts, Can, users admin screen
- [ ] Tests: security unit + auth API + interceptor refresh queue
- [ ] DEMO GATE: role-gated 403/200 + audit rows

## Phase 2 — Org Structure   [status: not started]
- [ ] departments/positions/position_rates/employees/employee_salaries models (+ btree_gist, pg_trgm)
- [ ] seed JSON: 8 departments + 47 positions with flat rates
- [ ] as-of helpers (salary/rate, first-of-month rule) + tests
- [ ] org + employees + salaries endpoints (scoped, salary role-gated)
- [ ] import_legacy.py roster import (~370) + name_en enrichment + unmatched report
- [ ] Frontend: org screens, employees CRUD, DataTable + useLocalizedField
- [ ] OPEN QUESTION answered: Engs department? (HR)
- [ ] DEMO GATE: real roster EN/AR browsable; salary hidden from Reviewer

## Phase 3 — KPI Templates   [status: not started]
- [ ] templates/versions/criteria/assignments models + lifecycle rules
- [ ] sum-to-100 validator (backend + frontend)
- [ ] seed 4 templates (SKILLED, NON_SKILLED, KEY_FOREMAN, LEGACY_TEAM)
- [ ] endpoints + template builder UI
- [ ] DEMO GATE: clone v1→v2, v1 frozen

## Phase 4 — Attendance Upload   [status: not started]
- [ ] incentive_periods + attendance models
- [ ] importer.py pure parser (17-column contract, fail-fast header check)
- [ ] dry-run → commit flow, sha256 idempotency, supersede, lock check
- [ ] zero_rule.py + flags + HR override
- [ ] upload wizard UI + monthly browse
- [ ] OPEN QUESTION answered: attendance-factor rule (PMO)
- [ ] DEMO GATE: real 420-row file end-to-end; re-upload → 409

## Phase 5 — Approvals Engine + Evaluations   [status: not started]
- [ ] common/workflow.py TransitionTable + apply_transition + approval_actions + notifications
- [ ] evaluations + evaluation_scores models, two transition tables, guards
- [ ] server-side scoring + suggestions.py
- [ ] endpoints incl. bulk-create + unified pending inbox + history
- [ ] EvaluationFormRenderer + bulk entry grid + inbox + timeline UI
- [ ] exhaustive transition matrix tests + reproducibility test
- [ ] DEMO GATE: score→return→fix→approve with timeline

## Phase 6 — Self-Appraisals + Transfers   [status: not started]
- [ ] self_appraisal flow (→PMO→FM) reusing renderer
- [ ] transfer_requests + apply-at-effective-date
- [ ] both in unified inbox
- [ ] DEMO GATE: transfer affects next month only

## Phase 7 — Calculation Engine + Incentive Runs   [status: not started]
- [ ] engine.py pure, Decimal, dual formula modes, round_step — TDD
- [ ] GOLDEN TESTS: recomputed March-2026 workbook row-for-row (validated with PMO)
- [ ] runs + line items (full snapshot) + lifecycle + period lock
- [ ] run dashboard + line breakdown + audit/approve screens
- [ ] OPEN QUESTIONS answered: position %s + salaries loaded (HR), pool source (PMO)
- [ ] DEMO GATE: draft→audit→approve→locked with drill-down

## Phase 8 — Reports & Exports   [status: not started]
- [ ] finance Excel export (openpyxl) + period summary
- [ ] WeasyPrint PDFs (vendored Arabic fonts, golden-file test)
- [ ] blank evaluation template generator (Excel + PDF)
- [ ] reports UI + downloads
- [ ] DEMO GATE: finance pack from locked run; Arabic PDF correct

## Phase 9 — Hardening & Deployment   [status: not started]
- [ ] audit viewer + dashboard widgets
- [ ] permissions penetration matrix (every endpoint × every role)
- [ ] i18n completeness + Arabic review by SAJCO staff
- [ ] backup/restore drill + deployment walkthrough
- [ ] UAT parallel month vs Excel — totals reconcile
- [ ] DEMO GATE: full month-cycle rehearsal on prod profile
