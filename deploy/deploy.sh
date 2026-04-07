#!/usr/bin/env bash
# deploy/deploy.sh — HUBEX One-Click Deploy
#
# Usage (from project root):
#   sudo bash deploy/deploy.sh
#
# Prerequisites:
#   - Ubuntu 22.04+ or Debian 12+
#   - copy deploy/.env.prod.example → deploy/.env.prod and fill in values

set -euo pipefail

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; RESET='\033[0m'; BOLD='\033[1m'
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
err()  { echo -e "${RED}✗ ERROR:${RESET} $*" >&2; }
info() { echo -e "${CYAN}→${RESET} $*"; }
warn() { echo -e "${YELLOW}⚠${RESET} $*"; }
header() { echo -e "\n${BOLD}${CYAN}═══ $* ═══${RESET}\n"; }

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------
header "HUBEX Deploy — Preflight"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$SCRIPT_DIR/.env.prod"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.yml"

# Root check
if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root or with sudo."
    exit 1
fi
ok "Running as root"

# .env.prod check
if [[ ! -f "$ENV_FILE" ]]; then
    err ".env.prod not found at $ENV_FILE"
    echo ""
    echo "  Create it from the template:"
    echo "    cp deploy/.env.prod.example deploy/.env.prod"
    echo "    nano deploy/.env.prod"
    exit 1
fi
ok ".env.prod found"

# Required variable checks
_required_vars=(SECRET_KEY POSTGRES_PASSWORD HUBEX_DOMAIN LETSENCRYPT_EMAIL)
_missing=()
for var in "${_required_vars[@]}"; do
    val=$(grep -E "^${var}=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | xargs)
    if [[ -z "$val" || "$val" == "change-me"* ]]; then
        _missing+=("$var")
    fi
done
if [[ ${#_missing[@]} -gt 0 ]]; then
    err "The following variables must be set in .env.prod:"
    for v in "${_missing[@]}"; do echo "    - $v"; done
    exit 1
fi
ok "Required env vars set"

# Read HUBEX_DOMAIN for later
HUBEX_DOMAIN=$(grep -E "^HUBEX_DOMAIN=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | xargs)

# ---------------------------------------------------------------------------
# Install Docker (if missing)
# ---------------------------------------------------------------------------
header "Docker"

if ! command -v docker &>/dev/null; then
    info "Docker not found — installing via get.docker.com…"
    curl -fsSL https://get.docker.com | sh
    ok "Docker installed: $(docker --version)"
else
    ok "Docker found: $(docker --version)"
fi

if ! docker compose version &>/dev/null; then
    err "docker compose plugin not available. Install Docker Engine >= 20.10 with Compose v2."
    exit 1
fi
ok "Docker Compose: $(docker compose version --short)"

# ---------------------------------------------------------------------------
# Build images
# ---------------------------------------------------------------------------
header "Building Images"

cd "$PROJECT_ROOT"
info "Building api, worker, frontend…"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build api worker frontend
ok "Images built"

# ---------------------------------------------------------------------------
# Start database + redis, wait for healthy
# ---------------------------------------------------------------------------
header "Starting Infrastructure"

info "Starting db and redis…"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d db redis

info "Waiting for Postgres to be healthy…"
_attempts=0
until docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T db \
        pg_isready -q 2>/dev/null; do
    _attempts=$((_attempts + 1))
    if [[ $_attempts -ge 30 ]]; then
        err "Postgres did not become healthy after 30s"
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs db
        exit 1
    fi
    sleep 1
done
ok "Postgres healthy"

# ---------------------------------------------------------------------------
# Database migrations
# ---------------------------------------------------------------------------
header "Running Migrations"

info "alembic upgrade head…"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
    run --rm api alembic upgrade head
ok "Migrations applied"

# ---------------------------------------------------------------------------
# Start all services
# ---------------------------------------------------------------------------
header "Starting Services"

info "Starting all services…"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
ok "All containers started"

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
header "Health Check"

info "Waiting for https://${HUBEX_DOMAIN}/health (up to 60s)…"
_attempts=0
until curl -sf --max-time 5 "https://${HUBEX_DOMAIN}/health" &>/dev/null; do
    _attempts=$((_attempts + 1))
    if [[ $_attempts -ge 60 ]]; then
        warn "Health endpoint not responding after 60s — showing API logs:"
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail=50 api
        exit 1
    fi
    sleep 1
done
ok "https://${HUBEX_DOMAIN}/health → OK"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
header "Deploy Complete"

echo -e "  ${GREEN}${BOLD}HUBEX is live!${RESET}"
echo ""
echo -e "  ${BOLD}Dashboard:${RESET}     https://${HUBEX_DOMAIN}"
echo -e "  ${BOLD}API docs:${RESET}      https://${HUBEX_DOMAIN}/docs"
echo -e "  ${BOLD}Health:${RESET}        https://${HUBEX_DOMAIN}/health"
echo ""
echo -e "  ${BOLD}Useful commands:${RESET}"
echo "    docker compose -f docker-compose.prod.yml --env-file deploy/.env.prod logs -f api"
echo "    docker compose -f docker-compose.prod.yml --env-file deploy/.env.prod ps"
echo "    bash deploy/update.sh   # pull + rolling restart"
echo ""
