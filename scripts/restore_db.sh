#!/usr/bin/env bash
set -euo pipefail

# Restores a pg_dump custom-format backup into the running Postgres container.
# DESTRUCTIVE: drops and recreates every object in the target database before
# restoring — only ever run this against a database you intend to overwrite.
#
# Usage: scripts/restore_db.sh <backup_file>

BACKUP_FILE="${1:?Usage: scripts/restore_db.sh <backup_file>}"
CONTAINER="${POSTGRES_CONTAINER:-ems-postgres-1}"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE" >&2
  exit 1
fi

POSTGRES_USER=$(docker exec "$CONTAINER" printenv POSTGRES_USER)
POSTGRES_DB=$(docker exec "$CONTAINER" printenv POSTGRES_DB)

echo "Restoring $BACKUP_FILE into '$POSTGRES_DB' on container '$CONTAINER' ..."
docker exec -i "$CONTAINER" pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists < "$BACKUP_FILE"

echo "OK: restore complete."
