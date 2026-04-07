#!/usr/bin/env bash
# deploy/update.sh — HUBEX Rolling Update
#
# Pulls/rebuilds images and restarts api, worker, frontend without touching db or redis.
#
# Usage (from project root):
#   sudo bash deploy/update.sh

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; RESET='\033[0m'; BOLD='\033[1m'
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
err()  { echo -e "${RED}✗ ERROR:${RESET} $*" >&2; }
info() { echo -e "${CYAN}→${RESET} $*"; }
header() { echo -e "\n${BOLD}${CYAN}═══ $* ═══${RESET}\n"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$SCRIPT_DIR/.env.prod"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.yml"

if [[ $EUID -ne 0 ]]; then
    err "Run as root or with sudo."
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    err ".env.prod not found at $ENV_FILE"
    exit 1
fi

HUBEX_DOMAIN=$(grep -E "^HUBEX_DOMAIN=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | xargs)

cd "$PROJECT_ROOT"

header "Rebuild Images"
info "Building api, worker, frontend…"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build api worker frontend
ok "Images built"

header "Run Migrations"
info "alembic upgrade head…"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
    run --rm api alembic upgrade head
ok "Migrations applied"

header "Rolling Restart"
info "Restarting api, worker, frontend (db + redis untouched)…"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
    up -d --no-deps api worker frontend
ok "Services restarted"

header "Health Check"
info "Waiting for https://${HUBEX_DOMAIN}/health…"
_attempts=0
until curl -sf --max-time 5 "https://${HUBEX_DOMAIN}/health" &>/dev/null; do
    _attempts=$((_attempts + 1))
    if [[ $_attempts -ge 30 ]]; then
        err "Health check failed after 30s"
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail=30 api
        exit 1
    fi
    sleep 1
done
ok "https://${HUBEX_DOMAIN}/health → OK"

echo ""
echo -e "  ${GREEN}${BOLD}Update complete.${RESET}"
echo ""
