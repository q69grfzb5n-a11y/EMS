$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

Write-Host "==> backend: ruff"
Set-Location backend
uv run ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> backend: mypy"
uv run mypy app
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> backend: pytest"
uv run pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Set-Location $RootDir

Write-Host "==> frontend: eslint"
Set-Location frontend
npm run lint
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> frontend: vitest"
npm run test -- --run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> frontend: build"
npm run build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Set-Location $RootDir

Write-Host "==> line limits"
python scripts/check_line_limits.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> i18n key parity"
python scripts/check_i18n_parity.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "All quality gates passed."
