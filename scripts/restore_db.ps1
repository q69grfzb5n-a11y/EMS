param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile
)
$ErrorActionPreference = "Stop"

# Restores a pg_dump custom-format backup into the running Postgres container.
# DESTRUCTIVE: drops and recreates every object in the target database before
# restoring — only ever run this against a database you intend to overwrite.

$Container = if ($env:POSTGRES_CONTAINER) { $env:POSTGRES_CONTAINER } else { "ems-postgres-1" }

if (-not (Test-Path $BackupFile)) {
    Write-Error "Backup file not found: $BackupFile"
    exit 1
}
$BackupFile = (Resolve-Path $BackupFile).Path

$PostgresUser = docker exec $Container printenv POSTGRES_USER
$PostgresDb = docker exec $Container printenv POSTGRES_DB

Write-Host "Restoring $BackupFile into '$PostgresDb' on container '$Container' ..."
# Same cmd.exe delegation as backup_db.ps1: PowerShell's own `<` redirection
# would re-encode the binary dump file before it reaches docker exec's stdin.
cmd /c "docker exec -i $Container pg_restore -U $PostgresUser -d $PostgresDb --clean --if-exists < `"$BackupFile`""
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: restore complete."
