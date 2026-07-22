#!/usr/bin/env bash
set -euo pipefail

# Backs up the running Postgres container's database with pg_dump (custom
# format, compressed) — works against either compose profile (dev or prod
# override) since both use the same container name from docker-compose.yml.
# Reads POSTGRES_USER/POSTGRES_DB from the container's own environment so this
# script never needs its own copy of secrets.
#
# Usage: scripts/backup_db.sh [output_dir]

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${1:-$ROOT_DIR/backups}"
CONTAINER="${POSTGRES_CONTAINER:-ems-postgres-1}"

mkdir -p "$OUTPUT_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="$OUTPUT_DIR/ems_backup_${TIMESTAMP}.dump"

POSTGRES_USER=$(docker exec "$CONTAINER" printenv POSTGRES_USER)
POSTGRES_DB=$(docker exec "$CONTAINER" printenv POSTGRES_DB)

echo "Backing up '$POSTGRES_DB' from container '$CONTAINER' -> $OUTPUT_FILE"
docker exec "$CONTAINER" pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > "$OUTPUT_FILE"

echo "OK: $(du -h "$OUTPUT_FILE" | cut -f1) written to $OUTPUT_FILE"
