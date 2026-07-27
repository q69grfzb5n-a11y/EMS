# Running the Incentive Management System

Everything needed to get the system running from a clean checkout, plus the
gotchas that are easy to lose an hour to.

> These steps were verified end to end by cloning this repository into an empty
> directory and following them exactly: the stack built, migrations ran on an
> empty database, the seed and import loaded all **440 real employees**, and
> the first-login password change worked. Nothing beyond Docker and the clone
> is required.

**Contents:** [Prerequisites](#prerequisites) · [Quick start](#quick-start-production-profile) ·
[Loading real data](#loading-the-real-data) · [Signing in](#signing-in) ·
[Development mode](#development-mode) · [Tests](#running-the-tests-and-quality-gates) ·
[Backups](#backups) · [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Tool | Notes |
|---|---|
| **Docker Desktop** | The only hard requirement. Everything runs in containers. |
| **Git Bash / WSL** (Windows) | For the `.sh` scripts. PowerShell equivalents (`.ps1`) are provided for backup/restore. |
| **OpenSSL** | Only for generating a local TLS certificate. Ships with Git for Windows. |

Node.js and Python are **not** required on the host — they only matter if you
want to run the linters and tests outside Docker.

---

## Quick start (production profile)

This is the profile to demo: HTTPS, a built frontend served by nginx, and no
development tooling in the image.

```bash
# 1. Create your environment file
cp .env.example .env
```

Open `.env` and set real values. **`SECRET_KEY` and `POSTGRES_PASSWORD` must be
changed** — the app refuses to start with the placeholder values when
`APP_ENV=prod`, deliberately, so a forgotten default can never reach production.

```bash
# Generate a strong secret (any of these)
openssl rand -hex 32
```

```bash
# 2. Build and start everything
docker compose up -d --build

# 3. Watch it come up
docker compose ps
docker compose logs -f backend
```

**No certificate step is needed.** On first start the frontend container
generates a self-signed certificate into `certs/` if none is there, and reuses
it afterwards. For a real deployment, put real certificates at
`certs/localhost.crt` and `certs/localhost.key` before starting and the
container will leave them alone. (`scripts/generate_dev_tls_cert.sh` still
exists if you prefer to create one on the host explicitly.)

Database migrations run automatically on backend startup — there is no separate
migrate step.

The app is then at **`https://localhost`**. Your browser will warn that the
certificate is not trusted; that is expected for a self-signed certificate —
choose **Advanced → Proceed**.

### Stopping

```bash
docker compose down          # stop, keep the database
docker compose down -v       # stop and DELETE the database volume
```

---

## Loading the real data

A fresh database has no rows. Two steps, in order:

```bash
# 1. Roles, the bootstrap admin, departments, positions, rate card, KPI templates
docker compose exec backend uv run python scripts/seed.py --core

# 2. The real employee roster from the source workbook
docker compose exec backend uv run python scripts/import_legacy.py \
  --file "/docs/source/Precast Incentives 03-2026.xlsm" \
  --attendance "/docs/source/attendance_export_06-2026.xlsx"
```

> **Windows / Git Bash:** prefix the import command with `MSYS_NO_PATHCONV=1`.
> Git Bash rewrites arguments that look like Unix paths, turning the container
> path `/docs/source/...` into `C:/Program Files/Git/docs/source/...`, which
> fails with `workbook not found`. PowerShell and CMD are unaffected.
>
> ```bash
> MSYS_NO_PATHCONV=1 docker compose exec backend uv run python scripts/import_legacy.py \
>   --file "/docs/source/Precast Incentives 03-2026.xlsm" \
>   --attendance "/docs/source/attendance_export_06-2026.xlsx"
> ```

Expect roughly `Roster: 440 created`, three rows flagged for HR attention, and
`407 employees updated` during name enrichment. The source workbook genuinely
contains a few incomplete rows; they are reported rather than hidden.

The import is **idempotent** — safe to re-run as the source file is corrected.
It never skips a row silently: anything it cannot resolve is printed with a
reason for a human to fix.

### Two optional setup helpers

```bash
# Give every position a KPI template (by seniority). Without a template a
# position's employees can never be evaluated, so they appear as
# `missing_evaluation` exceptions on every incentive run.
docker compose exec backend uv run python scripts/assign_kpi_templates.py

# Link existing logins to employee records by matching staff number.
# New accounts link automatically; this covers ones created earlier.
docker compose exec backend uv run python scripts/link_users_to_employees.py
```

Both are idempotent and both support inspection before writing
(`assign_kpi_templates.py --dry-run`).

---

## Signing in

After `seed.py --core` there is exactly one account:

| Staff number | Password | Roles |
|---|---|---|
| `0001` | `ChangeMe123!` | Admin + HR |

**You are forced to change this password on first login**, and that is enforced
by the server — not just the screen — so it cannot be bypassed by calling the
API directly.

From there, create the rest through **Users & Roles**. Use each person's **real
staff number** as their login: the system then links them to their employee
record automatically, which is what makes department scoping, reviewer
assignment, and "my incentives" resolve correctly.

### The order things must happen in

The incentive calculation depends on a chain. If a run produces zero lines,
one of these is missing:

1. A **KPI template** assigned to the employee's position
2. An **evaluation** for the period, scored and approved
3. An **attendance record** for the period
4. The period's **target and actual pool** figures set

Every employee who does not produce a line is listed on the run as an
exception **with the reason**, so the gap is always visible rather than silent.

---

## Development mode

Hot reload for both backend and frontend, over plain HTTP:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

| Service | URL |
|---|---|
| Frontend (Vite) | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

> **Note:** the running `uvicorn --reload` process does not always pick up
> **newly added routes**. If a brand-new endpoint 404s, restart the container:
> `docker compose restart backend`. Edits to existing files reload fine.

---

## Running the tests and quality gates

Everything at once:

```bash
bash scripts/check_all.sh      # or: pwsh scripts/check_all.ps1
```

Individually, inside the containers:

```bash
docker compose exec backend uv run pytest        # backend tests
docker compose exec backend uv run ruff check .  # lint
docker compose exec backend uv run mypy app      # types

docker compose exec frontend npm run lint
docker compose exec frontend npm run test -- --run
docker compose exec frontend npm run build

python scripts/check_i18n_parity.py              # English/Arabic key parity
python scripts/check_line_limits.py              # file-size guard
```

> Do **not** run two `pytest` processes against the same test database at
> once — they will deadlock on the shared truncate between tests.

---

## Backups

An automated backup sidecar runs on a schedule (daily by default, 14-day
retention) and writes to `./backups/`. Configure via `BACKUP_INTERVAL_SECONDS`
and `BACKUP_RETENTION_DAYS` in `.env`.

On demand:

```bash
bash scripts/backup_db.sh                          # -> ./backups/ems_backup_<timestamp>.dump
bash scripts/restore_db.sh backups/<file>.dump     # DESTRUCTIVE: overwrites the database
```

PowerShell equivalents: `scripts/backup_db.ps1`, `scripts/restore_db.ps1`.
They delegate the byte stream to `cmd.exe` because PowerShell 5.1's own
redirection corrupts binary data.

---

## Troubleshooting

### The site shows an old version after redeploying

Hard refresh once: **`Ctrl` + `Shift` + `R`**, or open a private window.

`index.html` is served with `Cache-Control: no-cache` so this should not recur —
but a copy cached *before* that header existed can persist until forced out.

### `http://` does not redirect to `https://`

Almost always **HSTS** cached in the browser. HSTS is keyed on the *hostname*
and ignores the port, so once a browser has seen it for `localhost` it will
force HTTPS on **every** localhost port — including ones that only speak HTTP.

Clear it: `edge://net-internals/#hsts` (or `chrome://net-internals/#hsts`) →
**Delete domain security policies** → enter `localhost` → Delete.

For this reason HSTS is **off by default** and must be opted into with
`ENABLE_HSTS=1` in `.env`. Only enable it behind a real domain with a real
certificate.

### `ERR_CONNECTION_REFUSED`, or the site never loads

Check the containers first — the frontend restarting in a loop looks identical
to the server being down:

```bash
docker compose ps
docker compose logs frontend
```

Common causes:

- **Docker is not running.** Start Docker Desktop.
- **Port 80 or 443 is already taken** by another web server (IIS, Skype, an
  existing nginx). The error is `port is already allocated`. Fix by remapping
  in `docker-compose.yml`:
  ```yaml
  frontend:
    ports:
      - "8080:80"
      - "8443:443"
  ```
  then also set `HTTPS_PORT_SUFFIX=:8443` in `.env` so the HTTP→HTTPS redirect
  targets the right port, and browse to `https://localhost:8443`.
- **`cannot load certificate`** in the frontend logs. This should no longer
  happen — the container self-provisions one — but if `certs/` exists on the
  host containing an unreadable or partial file, delete the directory and
  restart: `rm -rf certs && docker compose up -d`.

### A department manager sees no team, or the wrong one

Their login is not linked to an employee record. A manager's department is
derived from the employee they are linked to — there is no separate
"department manager" field.

Fix in **Users & Roles → Link to Employee**, or run
`scripts/link_users_to_employees.py` to link everyone by staff number at once.

### An incentive run produces 0 lines and many exceptions

Working as designed — read the exception reasons on the run. See
[the order things must happen in](#the-order-things-must-happen-in) above.

### "This period is locked"

A period locks automatically when one of its incentive runs is approved. Only
one run per period can ever be approved, enforced in the database. Attendance,
pools, and evaluations for that period become read-only.

---

## Further reading

| Document | Contents |
|---|---|
| [docs/deployment.md](docs/deployment.md) | Production deployment and backup drills |
| [docs/development.md](docs/development.md) | Local development conventions |
| [docs/architecture.md](docs/architecture.md) | System design |
| [docs/user-roles.md](docs/user-roles.md) | Roles and what each can do |
| [docs/workflows.md](docs/workflows.md) | Approval chains |
| [docs/calculation-engine.md](docs/calculation-engine.md) | How incentives are calculated |
| [PROGRESS.md](PROGRESS.md) | Full build history, including every bug found and fixed |
