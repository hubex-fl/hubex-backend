#!/bin/bash
# HUBEX Backup Script
# Usage: bash scripts/backup.sh [backup_dir]

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

echo "📦 HUBEX Backup — $TIMESTAMP"

# Database backup
echo "  💾 Backing up database..."
docker exec hubex-postgres pg_dump -U hubex hubex | gzip > "$BACKUP_DIR/hubex_db_$TIMESTAMP.sql.gz"
echo "  ✅ Database: hubex_db_$TIMESTAMP.sql.gz"

# Config backup (via API if running)
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "  📋 Backing up config via API..."
    curl -sf http://localhost:8000/api/v1/export > "$BACKUP_DIR/hubex_config_$TIMESTAMP.json" 2>/dev/null || true
    echo "  ✅ Config: hubex_config_$TIMESTAMP.json"
fi

# Clean old backups
echo "  🧹 Cleaning backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "hubex_*" -mtime +$RETENTION_DAYS -delete 2>/dev/null

echo "✅ Backup complete: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"/hubex_*_$TIMESTAMP.* 2>/dev/null
