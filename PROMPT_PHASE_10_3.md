# Phase 10.3 — One-Click Deploy Script

## Goal
Create a `deploy/deploy.sh` script that sets up a fresh Ubuntu server with HUBEX in one command. The script handles Docker install, .env.prod setup, database migration, and service startup.

## Files to Create

### `deploy/deploy.sh`
Bash script that:

1. **Preflight checks**
   - Must run as root (or via sudo)
   - Check `docker` and `docker compose` available; install Docker if missing
   - Check `.env.prod` exists (abort with instructions if not)
   - Check `HUBEX_DOMAIN`, `SECRET_KEY`, `POSTGRES_PASSWORD` set in `.env.prod`

2. **Pull / build images**
   - `docker compose -f docker-compose.prod.yml --env-file deploy/.env.prod pull` (pulls pre-built images if available)
   - `docker compose -f docker-compose.prod.yml --env-file deploy/.env.prod build` (builds local images)

3. **Start infrastructure only** (db + redis) first, wait for healthy

4. **Run Alembic migrations**
   - `docker compose -f docker-compose.prod.yml --env-file deploy/.env.prod run --rm api alembic upgrade head`

5. **Start all services**
   - `docker compose -f docker-compose.prod.yml --env-file deploy/.env.prod up -d`

6. **Health check**
   - Poll `https://${HUBEX_DOMAIN}/health` up to 30s
   - Print success URL or show `docker compose logs api` on failure

7. **Print summary**
   - URLs, how to view logs, how to run migrations again, how to stop

### `deploy/update.sh`
Lightweight update script (for subsequent deploys):
1. Pull latest images / rebuild
2. `docker compose ... up -d --no-deps api worker frontend` (rolling restart, db/redis untouched)
3. Run migrations
4. Health check

## Script Requirements
- Color output (green/red/yellow with tput or ANSI escapes)
- `set -euo pipefail` — abort on any error
- Idempotent — safe to run multiple times
- Works on Ubuntu 22.04+ / Debian 12+

## After Completion
1. Update ROADMAP.md: Step 3 done → Milestone 10 COMPLETE
2. Write report to REPORTS.md
3. Generate PROMPT_PHASE_11_1.md (n8n Webhook Templates)
