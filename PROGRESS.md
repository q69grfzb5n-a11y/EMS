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
- 2026-07-18: Verified the full backend flow live via curl against the real Docker Postgres (not just pytest): login → forced password change → create user → assign role as HR → 403 for admin/reviewer attempting HR-only actions → audit rows in DB → refresh rotation revokes the old token → logout revokes the current token.
- 2026-07-18: Owner then click-tested the real login page in a browser and hit **four further real bugs** invisible from curl-only testing, all now fixed:
  1. Password/staff-number `<Input>`s had no `dir="ltr"`, so the RTL page bidi-reordered typed Latin+punctuation text (a trailing `!` visually jumped to the front) — confusing to type in and to verify. First fix (`dir="ltr"` on the component) was incomplete: antd's `Input.Password` renders through an affix wrapper because of its visibility-toggle icon, so `dir`/`style` landed on the wrapper, not the real `<input>`. Fixed properly with antd's `styles={{ input: {...} }}` semantic slot (`shared/ui/ltrInput.ts`).
  2. `navigate()` calls after login/logout into a lazy-loaded route (`React.lazy` + Suspense) threw "component suspended while responding to synchronous input" under React 18's stricter Suspense rules. Fixed by wrapping those specific `navigate()` calls in `React.startTransition(...)` directly (LoginPage, ChangePasswordPage, AppShell logout).
  3. **The big one**: Vite's dev-server `/api` proxy target was hardcoded to `http://localhost:8000`. That only resolves inside the *frontend* container's own network namespace when running the dockerized dev stack — nothing listens there, since the backend is a separate container. Every real browser login attempt was silently failing at the proxy layer. Made the target configurable via `VITE_API_PROXY_TARGET`, set to `http://backend:8000` in `docker-compose.dev.yml`. This one had been broken since Phase 0 and wasn't caught earlier because prior verification always curled the backend's published port directly rather than going through the frontend's own proxy path.
  4. LoginPage/ChangePasswordPage always displayed "invalid password" on *any* failure, including the proxy bug above — actively misleading during diagnosis. Added `shared/utils/apiError.ts` to distinguish network errors, known backend error codes, and unknown failures with distinct messages.
  - **Lesson for future phases**: curling the backend's published port (`localhost:8000`) proves the API works; it does **not** prove the frontend can reach it through its own dev-server proxy when containerized. Test end-to-end through the frontend's own port (`localhost:5173/api/...`) going forward, per the `verify` skill's intent.

## Phase 2 — Org Structure   [status: done]   (2026-07-19)
- [x] departments/positions/position_rates/employees/employee_salaries models (+ btree_gist, pg_trgm) + migration `1861e1738425`
- [x] seed JSON: 9 departments (see Engs note below) + 46 positions with flat rates (`Database!F2:G47` is 46 rows, not 47 — PLAN's "47" was an off-by-one against the actual range)
- [x] as-of helpers (`rate_as_of`, `salary_as_of`, first-of-month rule) + boundary tests
- [x] org + employees + salaries endpoints (scoped, salary role-gated) — pre-existing from the prior commit, reviewed
- [x] `backend/scripts/import_legacy.py` — parses all 9 real department sheets header-name-first (never fixed column indices: the real sheets disagree with each other on column order and some duplicate the "Actual Position Final" header), resolves positions, applies the "خروج نهائي" (final exit) marker as the only free-text phrase that means terminated, backfills `full_name_en` from the attendance export by staff number, reports every unresolved row instead of skipping silently. Run for real against the actual `docs/source/*.xlsm`: **440 employees created**, 3 rows correctly reported unresolved (genuinely blank "Actual Position Final" cells in the source), 407 got `full_name_en` backfilled from the June-2026 attendance export (33 have no match there — plausible for a March-2026 roster vs a later attendance month). Re-ran the import a second time: 0 created / 440 updated — confirmed idempotent.
- [x] Frontend: org module (departments/positions tabs, rate-history modal), employees module (searchable roster via `DataTable`, detail page with overview/edit, reviewer assignment, salary tabs), `useLocalizedField` hook — all under `MANAGE_ORG`/`MANAGE_EMPLOYEES`/`VIEW_SALARY` permissions
- [x] OPEN QUESTION answered: `Engs` is seeded and imported as its own (9th) department (code `ENGS`), not a cross-department tag — matches how the seed data was already structured
- [x] DEMO GATE: real roster EN/AR browsable; salary hidden from Reviewer — **verified live**, see below
### Notes / deviations
- 2026-07-19: All static gates are green (`ruff check`, `mypy app`, `pytest`, frontend `tsc -b`, `eslint`, `vitest run`, `vite build`, and the repo's line-limit script) — run both bare and inside the actual `ems-backend-1`/`ems-frontend-1` containers. Fixed two real `mypy --strict` failures in the already-committed `org/service.py` and `employees/service.py` (untyped `Decimal`/`date` params) while touching those files.
- 2026-07-19: **Real bug caught by the new tests, not by manual testing this time**: `app/main.py`'s custom `RequestValidationError` handler passed `exc.errors()` straight into `JSONResponse`, but pydantic's `@model_validator(mode="after")`-raised `ValueError`s land inside `ctx.error` as the *raw exception object*, which `json.dumps` can't serialize — so any 422 from a custom validator (e.g. `PositionRateCreateRequest`'s "at least one of incentive_pct/flat_ref_amount" check) crashed as an unhandled 500 instead of returning 422. Fixed with a `_sanitize_errors` pass that stringifies `ctx.error` before `jsonable_encoder`. Only surfaced because `test_position_rate_requires_at_least_one_rate_value` was the first test in the repo to actually exercise a model-level (not field-level) validator through the API.
- 2026-07-19: Docker Desktop's WSL2 backend went unresponsive mid-session (`docker ps` hung indefinitely, survived a Docker Desktop process restart + `wsl --shutdown`); recovered after the machine was rebooted. Once back up, ran the full sequence for real: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build` → `alembic upgrade head` (entrypoint, confirmed at `1861e1738425`) → `seed.py --core` → `import_legacy.py` (twice, to prove idempotency) → full `pytest` (45 passed) → live demo gate over HTTP through the frontend's own dev proxy (`localhost:5173/api/...`, not the backend's published port directly, per the Phase 1 lesson): logged in as HR/admin, listed all 440 employees with real bilingual names, created a `reviewer` test user, confirmed 403 on an employee they weren't assigned to, 200 after HR assigned them, then **403 on that same employee's salaries** even though they could see the employee record — proving the salary gate is a real, separate authorization check and not just record-level scoping. Test reviewer user deactivated afterward, not deleted (no hard deletes on domain data, per PLAN §5).
- 2026-07-19: Mounted `./docs:/docs:ro` into the dev backend container (`docker-compose.dev.yml`) so `import_legacy.py` can reach the real source files from inside the container; invoked with `MSYS_NO_PATHCONV=1` on Windows to stop Git Bash from mangling the `/docs/...` container path into a host path.

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
