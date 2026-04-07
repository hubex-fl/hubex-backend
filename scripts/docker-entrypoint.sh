#!/bin/sh
set -e

echo "=== HubEx Backend Starting ==="

# Export DATABASE_URL from HUBEX_DATABASE_URL if set (for Alembic compatibility)
if [ -n "$HUBEX_DATABASE_URL" ] && [ -z "$DATABASE_URL" ]; then
  export DATABASE_URL="$HUBEX_DATABASE_URL"
fi

# Wait for PostgreSQL to be ready
echo "Waiting for database..."
until pg_isready -h "${DB_HOST:-postgres}" -p "${DB_PORT:-5432}" -U "${DB_USER:-hubex}" -q 2>/dev/null; do
  sleep 1
done
echo "Database ready."

# Run Alembic migrations (idempotent — safe to run on every start)
if [ "${HUBEX_RUN_MIGRATIONS:-true}" = "true" ] && [ -f alembic.ini ]; then
  echo "Running database migrations..."
  alembic upgrade head 2>&1 || {
    echo "WARN: Alembic migration failed — app will use create_all as fallback"
  }
  echo "Migrations complete."
fi

# Start the application
echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${HUBEX_PORT:-8000}"
