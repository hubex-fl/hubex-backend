#!/bin/bash
# HUBEX Restore Script
# Usage: bash scripts/restore.sh <backup_file.sql.gz>
#
# Restores a database backup created by backup.sh.
# WARNING: This replaces ALL data in the current database!

set -e

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: bash scripts/restore.sh <backup_file.sql.gz>"
  echo ""
  echo "Available backups:"
  ls -lh backups/hubex_db_*.sql.gz 2>/dev/null || echo "  No backups found in ./backups/"
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "ERROR: File not found: $BACKUP_FILE"
  exit 1
fi

echo "=== HUBEX Restore ==="
echo "  Backup: $BACKUP_FILE"
echo ""
echo "  WARNING: This will REPLACE all current data!"
read -p "  Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "Aborted."
  exit 0
fi

# Stop backend to prevent writes during restore
echo "  Stopping backend..."
docker compose -f docker-compose.prod.yml stop backend 2>/dev/null || true

# Restore database
echo "  Restoring database..."
gunzip -c "$BACKUP_FILE" | docker exec -i hubex-postgres psql -U hubex -d hubex --quiet 2>/dev/null

# Restart backend
echo "  Starting backend..."
docker compose -f docker-compose.prod.yml start backend

echo ""
echo "Restore complete! Verify at: http://localhost:8000/health"
