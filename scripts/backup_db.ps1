param(
    [string]$OutputDir
)
$ErrorActionPreference = "Stop"

# Backs up the running Postgres container's database with pg_dump (custom
# format, compressed) — works against either compose profile (dev or prod
# override) since both use the same container name from docker-compose.yml.
# Reads POSTGRES_USER/POSTGRES_DB from the container's own environment so this
# script never needs its own copy of secrets.

$RootDir = Split-Path -Parent $PSScriptRoot
if (-not $OutputDir) { $OutputDir = Join-Path $RootDir "backups" }
$Container = if ($env:POSTGRES_CONTAINER) { $env:POSTGRES_CONTAINER } else { "ems-postgres-1" }

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutputFile = Join-Path $OutputDir "ems_backup_$Timestamp.dump"

$PostgresUser = docker exec $Container printenv POSTGRES_USER
$PostgresDb = docker exec $Container printenv POSTGRES_DB

Write-Host "Backing up '$PostgresDb' from container '$Container' -> $OutputFile"
# PowerShell 5.1's own `>` redirection re-encodes a native command's stdout as
# text, which corrupts pg_dump's binary output — delegate the redirection to
# cmd.exe instead, which writes the raw bytes untouched.
cmd /c "docker exec $Container pg_dump -U $PostgresUser -Fc $PostgresDb > `"$OutputFile`""
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Size = (Get-Item $OutputFile).Length
Write-Host "OK: $Size bytes written to $OutputFile"
