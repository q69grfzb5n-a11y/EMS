#!/bin/sh
set -eu

# Runs inside the `backup` sidecar service (postgres:16-alpine image, has
# pg_dump built in) — connects to postgres over the compose network directly,
# no docker socket / docker exec needed. Loops forever: dump, prune old
# backups past retention, sleep, repeat. POSIX sh only (no bashisms) since
# the postgres:alpine image doesn't ship bash.

BACKUP_DIR="/backups"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

mkdir -p "$BACKUP_DIR"

echo "Backup sidecar started: every ${INTERVAL}s, keeping ${RETENTION_DAYS} days, writing to $BACKUP_DIR"

while true; do
  timestamp=$(date +%Y%m%d_%H%M%S)
  outfile="$BACKUP_DIR/ems_backup_${timestamp}.dump"

  if pg_dump -Fc -f "$outfile"; then
    echo "$(date -Iseconds) OK: backed up to $outfile ($(du -h "$outfile" | cut -f1))"
  else
    echo "$(date -Iseconds) ERROR: pg_dump failed, leaving prior backups untouched" >&2
  fi

  find "$BACKUP_DIR" -name 'ems_backup_*.dump' -type f -mtime "+${RETENTION_DAYS}" -delete

  sleep "$INTERVAL"
done
