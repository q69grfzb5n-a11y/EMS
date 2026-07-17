# Incentive Management System (IMS) — Project Plan

SHIBH AL-JAZIRA Factory for Precast Concrete (SAJCO) · converting the Excel-based incentive tool into a full web application.

> This is the agreed plan of record. Edit only on genuine scope change, with an entry in the Changelog at the bottom.
> How to execute each phase step-by-step: see [INSTRUCTIONS.md](INSTRUCTIONS.md). Current status: see [PROGRESS.md](PROGRESS.md).

## 1. Context

The factory tracks ~340–420 employees' monthly incentives in an Excel macro workbook (`docs/source/Precast Incentives 03-2026 (1).xlsm`) plus paper evaluation forms (3 Word drafts) and a monthly Oracle attendance export. All source files were analyzed — **the workbook has no VBA; the entire business logic is worksheet formulas, fully extracted and verified below.** The goal: an industry-grade web app with staff-number login, RBAC (HR-only role management), position-specific KPIs, attendance import, evaluation workflows with PMO → Factory Manager approvals, a bonus calculation engine, Finance summary, and Excel/PDF export.

## 2. Confirmed Decisions

**Stack:** Python FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL 16 (`backend/`, **uv-managed environment**) · React 18 + Vite + TypeScript SPA (`frontend/`) · Docker Compose · English + Arabic with full RTL · standalone JWT (staff number = login).

**Business rules:**
1. **Flexible KPI templates** — DB-driven, versioned, assigned per POSITION; criteria with max marks; always normalize to a percentage. Expresses both the new 100-point forms and the legacy 1–5 scheme (weights ×100 = max marks — verified they map perfectly).
2. **Bonus formula** — `bonus = evaluationPct × (baseSalary × positionIncentivePct) × attendanceFactor × budgetTargetRatio`, CEILING-to-10-SAR (configurable). Engine is dual-mode: also supports legacy `flat_ref_amount` — **required for phased cutover because base salaries exist in NO source file**; the system can run the legacy formula on day one and switch per-run to %-of-salary once HR loads salaries.
3. **Approval flows** — regular evaluations: Reviewer → Dept Manager. Self-appraisals (Key Persons) & transfers: → PMO → Factory Manager. Monthly incentive run: draft → PMO audit → FM approve → period locked → Finance export.
4. **Hard requirements** — max 1500 lines/file (CI-enforced), one folder per module (backend & frontend), PLAN.md + PROGRESS.md in repo root, docs/ documentation set, step-by-step phases.

## 3. Verified Domain Spec (extracted from real files)

### 3.1 Legacy calculation (workbook, cell-verified)
`incentive = CEILING(evaluationPct × positionRef × attendanceFactor × targetRatio, 10)` where evaluationPct = Σ(kpiScore 1–5 × weight)÷5 (weights 30/20/10/10/10/10/5/5), positionRef = VLOOKUP into 47-position SAR rate card (Labor 600 … Engineer 1 2700), attendanceFactor = manual 0–1.2, targetRatio = actualPool ÷ targetPool per month. Grades (informational): A ≥4.5, B 3–<4.5, C 2–<3, D <2 on the /5 score (≡ 0.90/0.60/0.40 bands on pct). 8 dept sheets + Engs variant (different KPI names). March-2026: 338 employees, 239,990 SAR total. ⚠ Historical month columns are pasted values, not live formulas — golden tests must use recomputed values.

### 3.2 New evaluation forms (Word drafts) — 100-point templates
Common: info block (Name, Oracle No., Position, Month, Reviewer, Reviewer Title), 3 assigned activities, criteria table (Total Marks | Employee Marks | Remarks), Reviewer + Manager signatures.

| Criterion | Skilled | Non-Skilled | Key Foreman |
|---|---|---|---|
| Worked Beyond Duty Hours (1 pt / 3 OT hrs) | 30 | 30 | 20 |
| Production Efficiency | 20 | 20 | 20 |
| Work Quality | 10 | 10 | 10 |
| Safety – PPE (−2/violation) | 10 | 10 | 10 |
| Teamwork & Skill Development | 10 | Skill Dev 10 + Teamwork 10 | — |
| Hand Tools & Equipment Handling | 10 | — | 10 |
| Reports & Planning | — | — | 10 |
| Team Coordination & Consultant Handover | — | — | 10 |
| Attendance (−5/absence; 6-month zero if leave+absence > allowance 45d/1yr, 90d/2yr contract) | 10 | 10 | 10 |
| **TOTAL** | **100** | **100** | **100** |

### 3.3 Attendance import (monthly Oracle export)
Sheet `Employees Time Card Summary Rep`, ~420 rows, 17 fixed columns: Month ("MM-YYYY"), Person No. (join key = staff number; int-or-text → normalize to string), Name, Department (Oracle org names — NEVER use for dept mapping), Worksite, Sponsor, Present, Off Days, Absent, Leave, Public Holiday (buckets sum to days-in-month), Deduct Min, Over Time (hrs), Approved, Pending Approval, Submitted, Approved Over Time. Maps: OT hours → "Worked Beyond Duty" suggestion; Absent → −5/absence penalty; Leave+Absent → allowance tracking.

## 4. Repository Structure

The complete folder tree is already created in this repo. Summary:

```
EMS/
├── PLAN.md  INSTRUCTIONS.md  PROGRESS.md  Readme.md
├── docker-compose.yml  docker-compose.dev.yml  .env.example        (Phase 0)
├── .github/workflows/ci.yml   .pre-commit-config.yaml              (Phase 0)
├── scripts/            # check_line_limits.py, check_all.ps1/.sh, backup_db.sh
├── docs/               # documentation set (§10) · decisions/ (ADRs) · source/ (original files)
├── backend/
│   ├── Dockerfile  entrypoint.sh  pyproject.toml  uv.lock  alembic/
│   ├── scripts/        # seed.py, import_legacy.py
│   ├── app/
│   │   ├── main.py  core/  db/(base, session, seed_data/)  common/  assets/fonts/
│   │   └── modules/    # auth, org, employees, kpi, evaluations, attendance, transfers,
│   │                   # approvals, incentives, reports, notifications, audit, settings
│   │                   # each: router.py service.py models.py schemas.py (+ module-specific pure files)
│   └── tests/          # conftest.py, fixtures/, unit/, api/
└── frontend/
    ├── Dockerfile  nginx.conf  package.json  vite.config.ts  openapi/schema.json
    └── src/
        ├── app/        # router, providers (LocaleProvider = RTL choke point), guards, layout
        ├── shared/     # api, auth (permissions.ts, Can), i18n, ui, hooks, utils
        └── modules/    # auth, dashboard, employees, org, kpi-templates, evaluations,
                        # self-appraisals, transfers, attendance, approvals, incentives, finance, audit
                        # each: api/ components/ pages/ types.ts locales/{en,ar}.json index.ts
```

Rules: every module in its own folder · max **1500 lines per code file** (CI fails >1500, warns >1200) · pure business logic (calc engine, workflow, importer) in dedicated importable files with zero DB dependencies.

## 5. Database Schema (PostgreSQL 16)

Conventions: BIGINT identity PKs · timestamptz UTC · statuses as varchar+CHECK (Python StrEnum) · percentages numeric(6,4) as 0–1 fractions · money numeric(12,2), never floats · created/updated audit columns · SQLAlchemy MetaData naming conventions for deterministic Alembic.

| Table | Key design points |
|---|---|
| `departments` | 8 seeded (MGMT/PROD/TECH/HC/QC/MAINT/INST/SCM), name_en/name_ar, is_active |
| `positions` | 47-row rate-card identities: code slug, title_en/title_ar |
| `position_rates` | **Temporal**: effective_from/to, `incentive_pct` AND/OR `flat_ref_amount` (dual-mode), GiST EXCLUDE prevents overlapping windows |
| `employees` | staff_no unique (normalized string), full_name_ar/en, department FK, position FK (ACTUAL position), contract_position_title, contract_years (1\|2) + contract_start_date (zero rule), employment_status, pg_trgm GIN on names |
| `employee_salaries` | **Temporal**, separate restricted table; as-of rule = first day of incentive month |
| `users` | employee FK, staff_no login, bcrypt hash, must_change_password |
| `roles` / `user_roles` | 9 seeded roles; grants HR-only (service-enforced, audited) — **admin cannot assign roles** |
| `refresh_tokens` | sha256 hash, rotation + revocation |
| `evaluation_assignments` | one active reviewer per employee |
| `kpi_templates` → `kpi_template_versions` → `kpi_criteria` | Logical template → immutable versions (draft→active→archived; partial unique: one active) → criteria (name_en/ar, max_marks, `input_mode` marks\|scale_1_5, `allow_negative`, `auto_source` none\|overtime_hours\|absence_penalty + `auto_params` jsonb) |
| `kpi_template_assignments` | position → logical template, effective-dated; version pinned at evaluation creation |
| `evaluations` | period+employee+kind unique; `kind` regular\|self_appraisal (one table, two transition maps); pinned template_version FK; activities jsonb; score_pct recomputed server-side; `row_version` optimistic locking |
| `evaluation_scores` | per criterion: raw_input, awarded_marks (may be negative), `auto_suggested_marks` retained for audit diff, remarks |
| `attendance_imports` | file sha256 unique per period (idempotency 409), error_report jsonb, superseded chain |
| `attendance_records` | one current row per employee+period, upsert ON CONFLICT, provenance import FK, all 17 columns |
| `attendance_zero_flags` | materialized 6-month zero rule (from/to period), HR-overridable with reason |
| `incentive_periods` | year+month unique, target_pool/actual_pool, open→locked |
| `incentive_runs` | run_no per period, draft→pmo_audit→fm_approval→approved (partial unique: ONE approved run/period), frozen `params` jsonb (formula mode, rounding, engine_version) |
| `incentive_line_items` | **full input snapshot** (evaluation_pct, base_salary, position_incentive_pct OR flat_ref_amount, attendance_factor, target_ratio, computed/rounded/override/final amounts, excluded+reason) — approved payouts immune to later master-data edits |
| `transfer_requests` | from/to dept, effective_date, draft→submitted→pmo_reviewed→fm_approved→applied |
| `approval_actions` | shared transition history for all workflows (entity_type+id, action, from/to status, actor, role, comment) — powers timeline UI |
| `audit_log` | append-only (no UPDATE/DELETE grant), before/after jsonb diffs, BRIN on created_at |
| `notifications` | in-app only v1 |
| `app_settings` | rounding_step/mode, grade_bands, allowance days, ot_hours_per_point, absence_penalty_points |

**No hard deletes on domain data** — statuses carry semantics (terminated/cancelled/superseded/is_active).

## 6. Key Backend Design Decisions

1. **Approval state machine — hybrid**: status column ON each entity (indexable, DB-constrainable) + one shared `approval_actions` history table + transition rules as data (`common/workflow.py` `TransitionTable`: (state, action) → {to, roles, guard}); `apply_transition()` validates, mutates, logs, notifies — one unit-testable code path.
2. **Calculation engine** (`incentives/engine.py`): pure — dataclasses in/out, zero SQLAlchemy imports, Decimal-only; `round_step(x, 10, CEILING)` reproduces Excel exactly. TDD against workbook goldens.
3. **Attendance→KPI suggestions** (`evaluations/suggestions.py`, pure): overtime `min(floor(approved_OT/3)×1, max_marks)`; absence `max_marks − 5×absent_days` (may go negative); forced 0 under active zero-flag; suggestions pre-fill but reviewer's marks are authoritative.
4. **Import idempotency**: sha256-identical re-upload → 409; changed file → transactional upsert + prior import `superseded`; blocked when period locked; synchronous (420 rows <1s, **no Celery/Redis**).
5. **API conventions**: `/api/v1`, error envelope `{"error":{code,message,details}}` with stable codes, `?page&size&sort` whitelist, scoped list endpoints (reviewer→assigned, dept_manager→own dept, employee→self), salary fields absent (not masked) for unauthorized roles. JWT access 30min / refresh 14d rotation.

## 7. Frontend Architecture

**Libraries:** Ant Design v5 (first-class RTL via `ConfigProvider direction="rtl"`) · TanStack Query v5 · Zustand (auth/ui only) · react-hook-form + zod (runtime schema from KPI template) · i18next (namespace per module, lazy per route chunk) · react-router 6.4 lazy · dayjs · Recharts (dashboard only) · axios + openapi-typescript (committed schema snapshot; hand-written thin API fns; keep snake_case) · vitest + testing-library + MSW · IBM Plex Sans Arabic self-hosted.

**RTL/i18n rules:** default locale **Arabic** (develop RTL-first); pre-hydration `dir` script in index.html; logical CSS properties only (stylelint enforced); `<bdi>`-wrapped mixed Arabic/Latin cells; numbers/IDs/money in LTR-isolated spans with tabular-nums; **Western digits** (`ar-SA-u-nu-latn`); UI chrome from i18next vs business data from API `*_en`/`*_ar` pairs via `useLocalizedField`; CI en/ar key-parity test.

**Auth/RBAC client:** access token in memory (Zustand), refresh token httpOnly SameSite=Strict cookie; 401 interceptor with single-flight refresh queue; roles → flat permission set in single `permissions.ts`; 3 enforcement layers (route guards, permission-filtered nav, `<Can>`); multi-role users = permission union; dashboard = permission-gated widgets. Client checks are UX only.

**Key components:** `EvaluationFormRenderer` (mirrors paper sheet, live TOTAL/100, suggestions as apply-hints never auto-filled) · `ApprovalTimeline` · `FileUploadWithPreview` (backend dry-run = single parse truth) · `DataTable` (server pagination, numeric/bidi column types, virtual for 400-row screens) · `PeriodPicker` (canonical "YYYY-MM", display "MM-YYYY") · `StatusBadge` (exhaustive TS Record) · `ApprovalActionModal`.

## 8. Phased Roadmap

| # | Phase | Size | Demo gate |
|---|---|---|---|
| 0 | **Scaffolding & dev env** | M | `docker compose up` boots bilingual stack; CI green |
| 1 | **Auth + RBAC** | M | role-gated 403/200; audit rows |
| 2 | **Org structure** (departments, positions+rates, employees, salaries, roster import) | M/L | real roster browsable EN/AR; salary invisible to Reviewer |
| 3 | **KPI templates** (versioned, position assignment, 4 seeds) | M | clone v1→v2, v1 frozen |
| 4 | **Attendance upload** (17-col parser, dry-run→commit, zero-flags) | M | upload real 420-row file, preview, commit |
| 5 | **Approvals engine + evaluations** (TransitionTable, bulk entry grid, Reviewer→Dept Mgr) | L | score→return→fix→approve with timeline |
| 6 | **Self-appraisals + transfers** (→PMO→FM) | M | transfer affects next month only |
| 7 | **Calculation engine + incentive runs** (dual formula, snapshot lines, lock) | L | golden test: recomputed March-2026 row-for-row |
| 8 | **Reports & exports** (openpyxl Excel, WeasyPrint Arabic PDF, blank templates) | M/L | locked run → finance pack; Arabic PDF correct |
| 9 | **Hardening & deployment** (audit UI, penetration pass, backups, UAT parallel month) | M | full month-cycle rehearsal on prod profile |

Size: S ≈ 1–2 days, M ≈ 3–5 days, L ≈ 1–2 weeks. Strict dependencies through Phase 5; 6/8 parallelizable. Detailed steps per phase: [INSTRUCTIONS.md](INSTRUCTIONS.md).

## 9. DevOps, Tooling, Seeding

- **Compose**: base (prod-shaped: postgres:16-alpine healthcheck+volume, backend python:3.12-slim + pango/fonts for WeasyPrint, nginx SPA + `/api` proxy = single origin no CORS) + dev override (uvicorn --reload, vite dev server, node_modules named volume, polling watchers, pg port exposed). Entrypoint runs `alembic upgrade head`; seeds always explicit.
- **Windows dev**: `.gitattributes * text=auto eol=lf` from commit 1; WSL2; LF entrypoint.sh.
- **Python env — uv**: committed `uv.lock`; local dev = `uv sync` + `uv run …`; Dockerfile uses `uv sync --frozen --no-dev` (prod); CI runs everything through `uv run`.
- **Quality gates**: ruff, mypy (strict on incentives/workflow/importer), pytest vs dockerized PG, coverage 85% overall / 100% engine+workflow+importer+zero_rule; eslint (max-lines 1500), prettier, vitest+MSW; pre-commit; CI = lint→types→tests→line-check→docker builds. Conventional commits by convention.
- **Seeding** (idempotent, natural-key upserts): `--core` = departments, 47 positions + flat rates, 4 KPI templates (reviewed JSON in `db/seed_data/`), roles, settings, admin user (forced password change). `import_legacy.py` = roster from xlsm + users; optional March-2026 history as locked run = golden dataset.
- **Backups**: pg_dump -Fc daily script + documented restore drill.

## 10. Documentation Set (docs/)

architecture.md · database-schema.md (mermaid ERD) · api-reference.md · calculation-engine.md (worked examples) · user-roles.md (role×permission matrix) · workflows.md (state diagrams) · attendance-import.md (17-column contract) · kpi-templates.md · deployment.md · development.md (Windows) · i18n-guide.md · decisions/ADR-*.md · source/ (original files, immutable).

## 11. Risks & Open Questions

| Risk / question | Handling | Owner / deadline |
|---|---|---|
| Base salaries in no source file | Dual-mode engine; launch on legacy flat amounts, switch per-run to %-of-salary once HR loads salaries | HR — before Phase 7 |
| `Engs` 9th sheet — department or cross-dept group? | Decide before org seed is final | HR — Phase 2 |
| Attendance-factor exact rule (workbook is manual 0–1.2) | Configurable rule engine; confirm formula | PMO — Phase 4 |
| Target/actual pool provenance (Inc. Tracking full of #REF!) | Manual PMO entry per period; confirm source | PMO — before UAT |
| Contract years/start dates exist nowhere | Zero rule degrades gracefully + data-quality report | HR — Phase 4 |
| Workbook history = pasted stale values | Goldens validated against recomputed copy with stakeholders | PMO — Phase 7 |
| Arabic PDF shaping | WeasyPrint+Pango, vendored fonts, golden-file tests; fallback: Excel-only first | dev — Phase 8 |
| Excel format drift | Header-name matching + versioned contract + dry-run + reject-with-report | dev — Phase 4 |
| Salary confidentiality | Separate table, role-scoped response models, audited access | dev — Phase 2 |

Defer to v2: Oracle HR integration, email/WhatsApp notifications, SSO/AD, mobile app, multi-factory, column-level encryption.

## 12. Verification

- **Per phase**: demo gate (§8) must pass before the next phase starts; PROGRESS.md updated in the same commit as the work.
- **Engine acceptance (Phase 7)**: golden tests reproduce the recomputed March-2026 workbook incentive column row-for-row (Decimal math, CEILING-10).
- **Continuous**: `docker compose up` from clean clone must always boot; CI green on every commit; permissions matrix test (every endpoint × every role).
- **Final (Phase 9)**: one parallel month — PMO runs Excel and the system side-by-side; totals must reconcile before Excel retirement.

## Changelog

- **2026-07-16** — Initial plan agreed and committed. Folder structure created. Code scaffolding (Phase 0) not started yet — deferred by user instruction (planning files + folder structure only).
