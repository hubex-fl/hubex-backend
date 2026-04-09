#!/bin/bash
# ═══════════════════════════════════════════════════════════
# HUBEX Demo Instance Setup
# ═══════════════════════════════════════════════════════════
#
# Sets up a complete HUBEX demo with:
#   1. Demo user account
#   2. Sample data (devices, variables, dashboards)
#   3. Running device simulators
#
# Usage:
#   ./scripts/setup-demo.sh
#   ./scripts/setup-demo.sh --server http://your-server:8000
#
# Prerequisites:
#   - HUBEX backend running (default: http://localhost:8000)
#   - curl and python3 installed
#

set -euo pipefail

BOLD="\033[1m"
GREEN="\033[92m"
YELLOW="\033[93m"
CYAN="\033[96m"
RED="\033[91m"
RESET="\033[0m"

SERVER="${1:-http://localhost:8000}"
DEMO_EMAIL="demo@hubex.io"
DEMO_PASSWORD="demo1234"

echo -e "\n${BOLD}${CYAN}╔═══════════════════════════════════════╗"
echo -e "║   HUBEX Demo Setup                    ║"
echo -e "╚═══════════════════════════════════════╝${RESET}"
echo -e "  Server: ${SERVER}\n"

# ── Step 1: Wait for backend ──────────────────────────────
echo -e "${YELLOW}[1/4] Waiting for backend...${RESET}"
for i in $(seq 1 30); do
  if curl -s -o /dev/null -w "%{http_code}" "${SERVER}/api/v1/health" | grep -q "200"; then
    echo -e "  ${GREEN}Backend is ready${RESET}"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo -e "  ${RED}Backend not reachable at ${SERVER}${RESET}"
    echo -e "  Make sure HUBEX is running: docker-compose -f docker-compose.full.yml up -d"
    exit 1
  fi
  sleep 2
done

# ── Step 2: Create demo user ─────────────────────────────
echo -e "\n${YELLOW}[2/4] Creating demo user...${RESET}"
REGISTER_RESP=$(curl -s -w "\n%{http_code}" -X POST "${SERVER}/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${DEMO_EMAIL}\",\"password\":\"${DEMO_PASSWORD}\"}" 2>/dev/null || true)

REGISTER_STATUS=$(echo "$REGISTER_RESP" | tail -1)
REGISTER_BODY=$(echo "$REGISTER_RESP" | head -n -1)

if [ "$REGISTER_STATUS" = "201" ] || [ "$REGISTER_STATUS" = "200" ]; then
  echo -e "  ${GREEN}Demo user created: ${DEMO_EMAIL}${RESET}"
elif echo "$REGISTER_BODY" | grep -q "already registered" 2>/dev/null; then
  echo -e "  ${GREEN}Demo user already exists: ${DEMO_EMAIL}${RESET}"
else
  echo -e "  ${YELLOW}User registration response: ${REGISTER_STATUS}${RESET}"
fi

# ── Step 3: Login and get token ───────────────────────────
echo -e "\n${YELLOW}[3/4] Authenticating...${RESET}"
LOGIN_RESP=$(curl -s -X POST "${SERVER}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${DEMO_EMAIL}\",\"password\":\"${DEMO_PASSWORD}\"}" 2>/dev/null || true)

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || true)

if [ -z "$TOKEN" ]; then
  echo -e "  ${RED}Failed to get auth token. Check credentials.${RESET}"
  echo -e "  Response: ${LOGIN_RESP}"
  exit 1
fi
echo -e "  ${GREEN}Authenticated successfully${RESET}"

# ── Step 4: Seed demo data ────────────────────────────────
echo -e "\n${YELLOW}[4/4] Seeding demo data...${RESET}"
SEED_RESP=$(curl -s -w "\n%{http_code}" -X POST "${SERVER}/api/v1/system/demo-data" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" 2>/dev/null || true)

SEED_STATUS=$(echo "$SEED_RESP" | tail -1)
SEED_BODY=$(echo "$SEED_RESP" | head -n -1)

if [ "$SEED_STATUS" = "200" ]; then
  echo -e "  ${GREEN}Demo data seeded successfully${RESET}"
  echo -e "  ${SEED_BODY}" | python3 -c "
import sys,json
try:
  d = json.load(sys.stdin).get('created',{})
  for k,v in d.items():
    if isinstance(v, (int, str)): print(f'    {k}: {v}')
except: pass
" 2>/dev/null || true
else
  echo -e "  ${YELLOW}Seed response: ${SEED_STATUS}${RESET}"
fi

# ── Start simulators in background ────────────────────────
echo -e "\n${YELLOW}Starting device simulators...${RESET}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "${SCRIPT_DIR}/sim_all.py" ]; then
  python3 "${SCRIPT_DIR}/sim_all.py" \
    --server "${SERVER}" \
    --email "${DEMO_EMAIL}" \
    --password "${DEMO_PASSWORD}" &
  SIM_PID=$!
  echo -e "  ${GREEN}Simulators started (PID: ${SIM_PID})${RESET}"
  echo "$SIM_PID" > /tmp/hubex-demo-sim.pid
else
  echo -e "  ${YELLOW}sim_all.py not found, skipping simulators${RESET}"
fi

# ── Summary ───────────────────────────────────────────────
FRONTEND_URL="${SERVER%:8000}"
if [ "$FRONTEND_URL" = "$SERVER" ]; then
  FRONTEND_URL="http://localhost"
fi

echo -e "\n${BOLD}${GREEN}╔═══════════════════════════════════════╗"
echo -e "║   Demo Ready!                         ║"
echo -e "╚═══════════════════════════════════════╝${RESET}"
echo -e ""
echo -e "  ${BOLD}Frontend:${RESET}  ${FRONTEND_URL}"
echo -e "  ${BOLD}Backend:${RESET}   ${SERVER}"
echo -e "  ${BOLD}n8n:${RESET}       http://localhost:5678"
echo -e ""
echo -e "  ${BOLD}Login:${RESET}     ${DEMO_EMAIL} / ${DEMO_PASSWORD}"
echo -e ""
echo -e "  To stop simulators: kill \$(cat /tmp/hubex-demo-sim.pid)"
echo -e ""
