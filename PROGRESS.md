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

## Phase 1 — Auth, Users, RBAC   [status: done]   (2026-07-18)
- [x] users/roles/user_roles/refresh_tokens models + migration
- [x] bcrypt + JWT + refresh rotation (httpOnly cookie)
- [x] login / refresh / logout / me / change-password endpoints
- [x] require_roles dependency + HR-only role grants (admin excluded)
- [x] audit_log table + write_audit core, wired to auth events
- [x] seed: 9 roles + admin user (forced password change)
- [x] Frontend: login, authStore, guards, permissions.ts, Can, users admin screen
- [x] Tests: security unit + auth API + interceptor refresh queue
- [x] DEMO GATE: role-gated 403/200 + audit rows
### Notes / deviations
- 2026-07-18: **Real bug caught by manual testing**: the refresh cookie was originally scoped to `path=/api/v1/auth/refresh` per INSTRUCTIONS.md's literal wording — but a cookie scoped to one exact path is never sent by a browser (or curl, correctly) to a sibling path, so `/auth/logout` could never actually read it and silently did nothing while still returning 204. Fixed by widening the cookie's `path` to `/api/v1/auth` (still narrower than site-wide `/`, covers `refresh` + `logout`). Caught only because the full login→refresh→logout→replay flow was walked end-to-end with real cookies, not just unit-tested in isolation.
- 2026-07-18: `users.employee_id` is a nullable `BigInteger` with **no FK constraint yet** — the `employees` table doesn't exist until Phase 2, which will add the constraint via a new migration. Documented inline in `models.py`.
- 2026-07-18: Seed bootstrap: admin user `0001` is granted **both** `admin` and `hr` roles directly at the DB layer in `seed.py` (bypassing the runtime rule that only HR can grant roles, which not even admin can bypass through the API). This is the intentional, documented way the very first HR account gets created — someone has to be able to grant roles before any HR account exists. Default password `ChangeMe123!`, `must_change_password=true`.
- 2026-07-18: Permission split for `/users/*` wasn't fully spelled out in INSTRUCTIONS.md ("Users admin: GET/POST/PATCH /users, PUT /users/{id}/roles (HR only), POST reset-password (HR)") — interpreted as: list/create/patch-active open to **ADMIN or HR**, role assignment and password reset **HR only**. Worth confirming with PMO/HR if this split matches intent.
- 2026-07-18: **Dev-machine-only quirk, not a project issue**: this machine has a pre-existing native Windows PostgreSQL 18 service bound to `localhost:5432`, which silently intercepts any bare-metal (`uv run alembic`/`uv run pytest`) connection attempt meant for the Docker Postgres. Migrations, seeding, and pytest were all run via `docker exec ems-backend-1 uv run ...` instead, which correctly resolves the `postgres` hostname on the compose network. CI is unaffected (no such conflict on GitHub Actions runners).
- 2026-07-18: Test DB isolation: `tests/conftest.py` creates/reuses a separate `ems_test` database and truncates all tables after each test (not the transaction-rollback/savepoint pattern) — simpler to reason about, fine at this data volume.
- 2026-07-18: `openapi-typescript` codegen isn't wired up yet — `frontend/src/modules/auth/types.ts` is hand-written to mirror the Pydantic schemas (snake_case, per PLAN §7). Fine per plan ("hand-written thin API fns"), but the committed-schema-snapshot pipeline itself is still a Phase 0 TODO if we want it later.
- 2026-07-18: Verified the full backend flow live via curl against the real Docker Postgres (not just pytest): login → forced password change → create user → assign role as HR → 403 for admin/reviewer attempting HR-only actions → audit rows in DB → refresh rotation revokes the old token → logout revokes the current token. Frontend build/typecheck/lint/tests are all green and the dev server serves every new module without transform errors, but the **React UI itself was not click-tested in a live browser** (no browser-automation tool available in this environment) — only the API layer it calls was exercised end-to-end.

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
