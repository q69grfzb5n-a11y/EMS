# INSTRUCTIONS — How to Execute Each Phase

Step-by-step runbook for building the Incentive Management System. Architecture and rationale live in [PLAN.md](PLAN.md); track completion in [PROGRESS.md](PROGRESS.md).

**Universal rules (every phase):**
- Work phase by phase. A phase is done only when its **demo gate** passes.
- Update `PROGRESS.md` in the same commit as the work (check items, add notes/deviations).
- Max 1500 lines per code file (CI enforces; warn at 1200 — split before you hit the wall).
- Every backend module = its own folder with `router.py`, `service.py`, `models.py`, `schemas.py`. Every frontend module = `api/ components/ pages/ types.ts locales/{en,ar}.json index.ts`.
- All money math in `Decimal`. All statuses via `common/enums.py` StrEnums. Every mutating endpoint writes an audit row.
- Commit style: `feat(module): ...`, `fix(module): ...`, `chore: ...`.

---

## Phase 0 — Scaffolding & Dev Environment

**Goal:** `docker compose up` boots a hello-world bilingual stack; all quality gates runnable.

### 0.1 Root files
1. `.gitignore` (exists), `.gitattributes` (`* text=auto eol=lf`), `.editorconfig`.
2. `.env.example` — document every variable: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES=30`, `REFRESH_TOKEN_EXPIRE_DAYS=14`, `APP_ENV=dev`, `DEFAULT_LOCALE=ar`.
3. `scripts/check_line_limits.py` — walk `backend/app` + `frontend/src`, count lines of `*.py|*.ts|*.tsx` (exclude `alembic/versions`, `types.gen.ts`), exit 1 if >1500, warn >1200.
4. `scripts/check_all.ps1` + `.sh` — run every quality gate locally.

### 0.2 Backend skeleton (uv)
```powershell
cd backend
uv init --package .        # or hand-write pyproject.toml with [project] + [tool.*] sections
uv add fastapi "uvicorn[standard]" sqlalchemy alembic psycopg[binary] pydantic-settings python-multipart bcrypt pyjwt openpyxl
uv add --dev ruff mypy pytest pytest-cov httpx
```
1. `app/main.py` — `create_app()`, mount `/api/v1` router, `/health` endpoint returning `{status, db}` (db = `SELECT 1` check).
2. `app/core/config.py` — pydantic-settings reading the `.env` names above.
3. `app/db/base.py` — `DeclarativeBase` with MetaData naming conventions (`pk_%`, `fk_%_%`, `uq_%`, `ix_%`, `ck_%`) + `TimestampMixin`. `app/db/session.py` — engine + sessionmaker.
4. `alembic init alembic` → wire `env.py` to `app.db.base` metadata + `DATABASE_URL` from settings; create empty initial migration.
5. `Dockerfile` — multi-stage: `python:3.12-slim`; uv copy pattern (`COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/`); dev target (`uv sync --frozen`) + prod target (`uv sync --frozen --no-dev`, add `libpango-1.0-0 libpangoft2-1.0-0 fonts-noto-core` for later WeasyPrint). `entrypoint.sh` (**LF line endings**): `alembic upgrade head && exec "$@"`.
6. Configure `pyproject.toml`: ruff (line-length 100), mypy (strict paths listed later), pytest.
7. Verify locally: `uv run uvicorn app.main:app --reload` → GET `/health` 200.

### 0.3 Frontend skeleton
```powershell
cd frontend
npm create vite@latest . -- --template react-ts
npm i antd @tanstack/react-query zustand react-hook-form zod @hookform/resolvers i18next react-i18next i18next-resources-to-backend react-router-dom dayjs axios @fontsource/ibm-plex-sans-arabic
npm i -D vitest @testing-library/react @testing-library/jest-dom msw eslint prettier openapi-typescript jsdom
```
1. `index.html` — inline 3-line script: read `localStorage.lang` (default `ar`), set `<html lang dir>` before bundle loads.
2. `src/app/providers/LocaleProvider.tsx` — i18next init; on `languageChanged`: set `document.documentElement.dir/lang`, antd `ConfigProvider direction+locale`, `dayjs.locale()`. **Default locale Arabic.**
3. `src/app/router.tsx` — `createBrowserRouter`, lazy routes; placeholder Login + Dashboard pages.
4. `src/app/layout/AppShell.tsx` + `SideNav.tsx` + `navigation.ts` + `LanguageSwitcher.tsx`.
5. `src/shared/i18n/locales/{en,ar}/common.json` — first keys (app name, nav labels).
6. ESLint flat config with `max-lines: ["error", 1500]`; prettier; vitest config.
7. `Dockerfile` (node build → nginx:alpine) + `nginx.conf` (SPA `try_files`, `/api` → `backend:8000` proxy, gzip).
8. Verify: `npm run dev` → shell renders, language toggle flips RTL/LTR without reload artifacts.

### 0.4 Compose + CI
1. `docker-compose.yml` (base): postgres:16-alpine (healthcheck `pg_isready`, named volume, NO published port), backend (depends_on healthy, prod target), frontend (nginx, port 80).
2. `docker-compose.dev.yml`: backend dev target + bind mount + `--reload` + port 8000; frontend replaced by node container running `vite --host` (node_modules named volume, `usePolling: true`), port 5173; postgres port 5432 exposed.
3. `.github/workflows/ci.yml`: jobs — backend (uv sync → ruff → mypy → pytest w/ PG service), frontend (npm ci → eslint → vitest → build), line-check, docker builds.
4. `.pre-commit-config.yaml`: ruff, ruff-format, line-limit script, prettier mirror, end-of-file-fixer, check-merge-conflict.

**Demo gate:** `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` → `/health` shows db-connected, frontend shows bilingual shell with working RTL toggle, `pre-commit run --all-files` passes, CI green.

---

## Phase 1 — Auth, Users, RBAC

**Goal:** staff-number + password login with role-gated API.

1. **Models** (`modules/auth/models.py` + migration): `users`, `roles`, `user_roles`, `refresh_tokens` (see PLAN §5).
2. **Security** (`core/security.py`): bcrypt hash/verify; JWT encode/decode (HS256, `sub` = user id, `roles` claim); opaque refresh token → sha256 stored.
3. **Endpoints** (`modules/auth/router.py`): `POST /auth/login` (staff_no + password → access token in body + refresh token as httpOnly SameSite=Strict cookie scoped to `/api/v1/auth/refresh`), `/auth/refresh` (rotation: revoke old, issue new), `/auth/logout` (revoke), `GET /auth/me`, `POST /auth/change-password`. Users admin: `GET/POST/PATCH /users`, `PUT /users/{id}/roles` (**HR role only — not even admin**), `POST /users/{id}/reset-password` (HR).
4. **Deps** (`core/deps.py`): `get_current_user`, `require_roles(*roles)` dependency factory.
5. **Audit core** (`common/audit.py`): `write_audit(session, actor, action, entity_type, entity_id, before, after)` + `audit_log` table migration. Wire into login, role grant, user create.
6. **Seed**: roles (9) + admin user staff_no `0001` with `must_change_password=true` (in `backend/scripts/seed.py --core`, idempotent upserts).
7. **Frontend**: `authStore.ts` (token in memory), login page, `AuthProvider` silent refresh on boot, `RequireAuth`/`RequirePermission` guards, `permissions.ts` map, `<Can>`, change-password page (forced when flag set), HR users/roles admin screen.
8. **Tests**: unit (bcrypt/JWT round-trip, expiry) + API (login/refresh rotation/revocation; role grant forbidden for non-HR **including admin**; must_change_password flow). Frontend: interceptor single-flight refresh test (MSW).

**Demo gate:** login as `0001` → forced password change → create user → assign role (as HR) → verify 403 vs 200 per role → audit rows visible in DB.

---

## Phase 2 — Org Structure (Departments, Positions, Employees, Salaries)

**Goal:** org master data in DB, imported from the real workbook.

1. **Models + migrations**: `departments`, `positions`, `position_rates` (temporal, GiST EXCLUDE via `btree_gist` extension), `employees`, `employee_salaries` (temporal), `evaluation_assignments`. Enable `pg_trgm` + GIN indexes on names.
2. **Seed data JSON** (`app/db/seed_data/`): `departments.json` (8), `positions.json` (47 from workbook `Database!F2:G47` with `flat_ref_amount`; `incentive_pct` null until HR supplies).
3. **As-of helpers** (`modules/org/service.py` or `employees/service.py`): `rate_as_of(position_id, date)`, `salary_as_of(employee_id, date)` — first-day-of-month rule; unit tested (gaps, boundaries).
4. **Endpoints**: org CRUD (HR write), employees CRUD (HR), scoped GET lists (reviewer→assigned, dept_manager→own dept, employee→self), salaries GET/POST (HR write; HR/Finance/PMO read), reviewer assignment PUT.
5. **Salary confidentiality**: separate Pydantic response models — salary field **absent** for unauthorized roles; every salary read/write audited.
6. **Roster import** (`backend/scripts/import_legacy.py`): parse 8 dept sheets from `docs/source/*.xlsm` starting row 8 (Oracle no → staff_no normalized string, name_ar, contract position, col F → position FK, status شغال → active); cross-match attendance xlsx `Person No.` → backfill `name_en`; unmatched rows → console report (never silent skip).
7. **Frontend**: departments/positions/rates screens (org module), employees list+detail+CRUD with Arabic search, salary tab (role-gated), `DataTable` + `useLocalizedField` built here.
8. **Tests**: overlap rejection (EXCLUDE constraint), as-of boundary cases, HR-only writes, scope filters per role, import script against the real file.

**Ask HR first:** is `Engs` a 9th department or a cross-department group? (Blocks final seed.)

**Demo gate:** ~370 real employees browsable EN/AR with search; salary invisible when logged in as a Reviewer; re-running import is idempotent.

---

## Phase 3 — KPI Templates

**Goal:** flexible, versioned, per-position evaluation templates.

1. **Models + migrations**: `kpi_templates`, `kpi_template_versions` (partial unique: one active per template), `kpi_criteria` (max_marks, input_mode marks|scale_1_5, allow_negative, auto_source + auto_params jsonb), `kpi_template_assignments` (position → logical template, effective-dated).
2. **Lifecycle rules** (service): criteria editable only while version `draft`; `activate` archives previous active; used versions immutable forever.
3. **Validator**: criteria max_marks must sum to exactly 100 for new-style templates (zod mirror on frontend).
4. **Seed 4 templates** (`seed_data/kpi_templates.json`): SKILLED, NON_SKILLED, KEY_FOREMAN (from Word drafts — criteria EN/AR names, marks, guidance text, auto_source: overtime_hours on "Worked Beyond Duty Hours" {unit_hours:3, points_per_unit:1}, absence_penalty on "Attendance" {penalty_per_absence:5}), LEGACY_TEAM (8 criteria 30/20/10/10/10/10/5/5, input_mode scale_1_5).
5. **Endpoints**: templates/versions/criteria CRUD (PMO/admin write per PLAN §6), activation, position assignment (PMO/HR).
6. **Frontend** (kpi-templates module): template list, version history, criteria editor with live sum-to-100 validation, position assignment screen.
7. **Tests**: activation swap, draft-only editing, assignment resolution, sum validator.

**Demo gate:** open "Skilled Personnel" template → clone to v2 → change a weight → publish → v1 remains frozen and evaluations made against v1 still render identically.

---

## Phase 4 — Attendance Upload

**Goal:** monthly Oracle Excel becomes validated attendance records.

1. **Models + migrations**: `incentive_periods` (create here — attendance needs it), `attendance_imports`, `attendance_records`, `attendance_zero_flags`.
2. **Parser** (`modules/attendance/importer.py`, pure — bytes in, `ParsedRow[] + issues[]` out): `openpyxl load_workbook(read_only=True, data_only=True)`; validate sheet name `Employees Time Card Summary Rep` + all 17 headers verbatim (fail fast on drift); row `Month` must equal declared period; normalize Person No. (int→str, strip, no leading zeros); bucket-sum sanity check (Present+Off+Absent+Leave+Holiday == days-in-month → warning).
3. **Import flow** (service): dry-run (parse + match by staff_no, return preview + row errors, commit nothing) → commit (upsert `ON CONFLICT (period_id, employee_id) DO UPDATE`, mark prior import `superseded`); sha256-identical file → 409; locked period → 409. Never read department/name from file into masters.
4. **Zero rule** (`zero_rule.py`, pure): rolling leave+absence vs contract allowance (45d/1yr, 90d/2yr from `contract_years`); on breach create `attendance_zero_flags` row (period → period+5); degrade gracefully when contract data missing (report, no flag). HR override endpoint with reason.
5. **Endpoints**: `POST /attendance/imports?dry_run=true|false` (HR), imports list/detail, records browse (scoped), zero-flags list + override.
6. **Frontend** (attendance module): 3-step upload wizard (`FileUploadWithPreview`: drag → dry-run preview with error-highlighted rows + summary banner → commit), monthly browse per department, zero-flags screen.
7. **Tests**: fixture xlsx files (happy, wrong header, bad month, dup staff_no, bucket mismatch); idempotency 409; supersede path; zero-rule window math boundaries; locked-period rejection.

**Ask PMO first:** exact attendance-factor formula (workbook is a manual 0–1.2 knob) — implement as configurable rule, default = manual entry on the run line.

**Demo gate:** upload the real 420-row file → preview shows N matched / M unmatched → commit → browse June-2026 attendance; re-upload same file → 409.

---

## Phase 5 — Approvals Engine + Evaluations

**Goal:** generic state machine powering the first real workflow. **The biggest phase.**

1. **Workflow engine** (`common/workflow.py`): `TransitionTable` dataclass mapping `(state, action) → Step{to, roles, guard}`; `apply_transition(session, entity, action, actor)` validates role+guard, mutates status, inserts `approval_actions` row, creates notification. `approval_actions` + `notifications` migrations here.
2. **Evaluation models + migrations**: `evaluations` (kind regular|self_appraisal, pinned template_version_id, activities jsonb, row_version optimistic lock), `evaluation_scores`.
3. **Transition tables** (`modules/evaluations/workflow.py`): REGULAR (draft→submitted→manager_approved, with return loop) and SELF (draft→submitted→pmo_reviewed→fm_approved, return loops) — guards: `is_owner`, `same_department`.
4. **Scoring** (service): server-side recompute on every save/submit — `score_pct = max(Σ awarded, 0) / Σ max`, scale_1_5 → `rank/5 × max_marks`; grade from settings bands (0.90/0.60/0.40).
5. **Suggestions** (`suggestions.py`, pure): from `attendance_records` via criteria `auto_source/auto_params`; store `auto_suggested_marks` alongside reviewer's `awarded_marks`; forced 0 marks suggestion under active zero-flag.
6. **Endpoints**: create (resolves template version + suggestions into draft), bulk-create per department, scoped lists, update (draft/returned only, row_version check → 409), submit/approve/return, `GET /approvals/pending` (unified inbox), `GET /approvals/{type}/{id}/history`.
7. **Frontend**: approvals inbox (module approvals), `EvaluationFormRenderer` (info header via Descriptions, 3 activities, criteria table with max/entered/remarks + guidance tooltips, live TOTAL/100, suggestion hint rows with Apply button), bulk entry grid for a reviewer's team (keyboard-friendly; row-level edit, not 400 controlled inputs), review page with `ApprovalTimeline` + `ApprovalActionModal`.
8. **Tests**: exhaustive transition matrix (every state×action×role → allowed/denied); template pinning reproducibility (edit template after eval created → eval unchanged); optimistic-lock 409; suggestion math; full workflow walks; scope enforcement.

**Demo gate:** Reviewer scores a Production crew via bulk grid → Dept Manager returns one with comment → Reviewer fixes → approved; timeline shows every step.

---

## Phase 6 — Self-Appraisals + Transfers

**Goal:** prove the approvals engine is generic.

1. **Self-appraisals**: `kind='self_appraisal'` evaluations (Key Person creates own; reviewer_user_id = own user), SELF transition table (→ PMO → FM), frontend page reusing `EvaluationFormRenderer` + inbox integration.
2. **Transfers**: `transfer_requests` model + migration; transition table draft→submitted→pmo_reviewed→fm_approved→applied; on FM approval, apply at `effective_date`: update `employees.department_id` (effective-dated — calc engine for months before effective_date uses old dept).
3. **Endpoints + frontend**: request form, PMO/FM review pages, history list; both flows appear in the same unified inbox.
4. **Tests**: full route walks; `applied` actually moves the employee; transfer respects effective date in later phases' runs; RBAC (only PMO can pmo-review etc.).

**Demo gate:** Key Person self-rates → PMO endorses → FM approves. Transfer approved with next-month effective date → employee still in old dept for current month's run.

---

## Phase 7 — Calculation Engine + Incentive Runs

**Goal:** reproduce the Excel numbers exactly. **Highest-risk logic — TDD.**

1. **Engine FIRST, tests-first** (`modules/incentives/engine.py`, pure, Decimal-only): `compute_line(LineInputs, RunParams) → LineResult`; formula modes `pct_of_salary` (evalPct × salary × positionPct × attFactor × ratio) and `legacy_flat` (evalPct × flatRef × attFactor × ratio); `round_step(x, step=10, mode=CEILING)`. **Golden tests**: hand-verified rows from the recomputed March-2026 workbook (e.g. 0.85 × 2000 × 1 × 0.7218 → ceil10 = 1230) — validate the recomputed sheet with PMO first (history cells are stale pasted values!).
2. **Models + migrations**: `incentive_runs` (partial unique: one approved per period, frozen params jsonb), `incentive_line_items` (full input snapshot).
3. **Run service**: create draft run → resolve every active employee's evaluation_pct (approved evals only), salary/rate as-of first-of-month, attendance factor, period ratio → snapshot into lines; exceptions list (missing eval, missing attendance, missing salary for pct mode, inactive); recalculate/edit lines (att factor, override with reason, exclude) only in draft; transitions draft→pmo_audit→fm_approval→approved (locks period: blocks eval edits, attendance re-import, pool edits).
4. **Endpoints**: periods CRUD (pools — PMO), run create/detail/lines (paginated, dept filter), line PATCH, recalculate, submit-audit/fm-approve/reject, `GET /my/incentives`.
5. **Frontend** (incentives module): run dashboard (per-dept totals like Inc. Tracking), line drill-down with formula breakdown (`IncentiveLineBreakdown`: evalPct × base × factor × ratio → rounded), PMO audit view (variance vs previous month), FM approve screen, lock indicator.
6. **Tests**: engine goldens (100% coverage on engine.py); rounding edges (exact multiples of 10, zero); both formula modes; snapshot correctness (change salary after approval → line unchanged); one-approved-run constraint; lock side-effects; totals = Σ lines.

**Ask HR/PMO first:** per-position incentive percentages (for pct mode) and confirmation of pool number source.

**Demo gate:** create run from Phases 4–5 data → drill into one employee showing full formula breakdown → PMO audit → FM approve → period locked, nothing editable, `my incentives` visible to employee.

---

## Phase 8 — Reports & Exports

**Goal:** Finance gets its pack; managers get printable forms.

1. **Finance Excel** (`modules/incentives/export.py` + `reports`): approved-run payout sheet per department + grand totals (openpyxl, RTL sheet view for Arabic names); period summary endpoint (replaces Inc. Tracking).
2. **PDF** (WeasyPrint): add lib + system deps (already in Docker image from Phase 0); Jinja2 HTML templates + `@page` CSS; vendored Noto Naskh Arabic + Noto Sans in `app/assets/fonts/` via `@font-face`; **render only in-container** (document GTK escape hatch for bare Windows in development.md). Golden-file test: fixture with real Arabic names → assert text layer contains reshaped strings.
3. **Blank evaluation templates**: generator producing Excel (criteria rows + validation dropdowns per template version, one sheet per team) + PDF print version — downloadable by Foremen/Group Heads per position/template.
4. **Frontend** (finance module): reports page with period/dept filters + download buttons (blob via `download.ts`); export pack per locked run.
5. **Tests**: export totals equal Σ line items; header/format snapshot; Arabic PDF golden file.

**Demo gate:** locked run → download finance Excel (opens correctly in Arabic Excel) + PDF summary with correct RTL names; download blank "Skilled" template.

---

## Phase 9 — Hardening & Deployment

**Goal:** production-ready.

1. Audit-log viewer UI (audit module, filters by entity/actor/date).
2. Dashboard widgets (permission-gated): my incentive card, pending approvals count, month status, dept totals chart (Recharts).
3. **Permissions penetration pass**: scripted matrix test — every endpoint × every role → expected 200/403; fix all gaps.
4. i18n completeness: en/ar key-parity CI test green; human review of Arabic wording by SAJCO staff.
5. Ops: `scripts/backup_db.sh` + restore drill documented and rehearsed; prod compose profile validated on the target machine; `docs/deployment.md` walkthrough.
6. **UAT parallel month**: PMO runs Excel and the system side-by-side for one full cycle; totals must reconcile; fix list; then Excel retirement decision.

**Demo gate:** full month-cycle rehearsal end-to-end on the prod-profile stack, plus successful restore-from-backup.

---

## Open Questions Checklist (answer before the phase that needs them)

- [ ] **Phase 2 / HR:** Is `Engs` a 9th department or a cross-department engineers group?
- [ ] **Phase 4 / PMO:** Exact attendance-factor rule (formula from Present/Absent/Leave/Deduct Min, or stays a manual knob?)
- [ ] **Phase 7 / HR:** Per-position incentive percentages for the %-of-salary formula + employee base salaries loaded.
- [ ] **Phase 7 / PMO:** Source of monthly target/actual pool figures.
- [ ] **Phase 4 / HR:** Contract years + start dates for the 6-month zero rule.
