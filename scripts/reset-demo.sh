#!/bin/bash
# ═══════════════════════════════════════════════════════════
# HUBEX Demo Reset
# ═══════════════════════════════════════════════════════════
#
# Removes all demo data and re-seeds fresh.
# Useful for daily cron reset of demo instances.
#
# Usage:
#   ./scripts/reset-demo.sh
#   ./scripts/reset-demo.sh --server http://your-server:8000
#
# Cron example (reset every day at 6 AM):
#   0 6 * * * /path/to/hubex/scripts/reset-demo.sh >> /var/log/hubex-demo-reset.log 2>&1
#

set -euo pipefail

BOLD="\033[1m"
GREEN="\033[92m"
YELLOW="\033[93m"
CYAN="\033[96m"
RED="\033[91m"
RESET="\033[0m"

SERVER="${1:-http://localhost:8000}"
DEMO_EMAIL="demo@hubextest.tech"
DEMO_PASSWORD="demo1234"

echo -e "\n${BOLD}${CYAN}╔═══════════════════════════════════════╗"
echo -e "║   HUBEX Demo Reset                    ║"
echo -e "╚═══════════════════════════════════════╝${RESET}"
echo -e "  Server: ${SERVER}\n"

# ── Stop running simulators ───────────────────────────────
echo -e "${YELLOW}[1/4] Stopping existing simulators...${RESET}"
if [ -f /tmp/hubex-demo-sim.pid ]; then
  SIM_PID=$(cat /tmp/hubex-demo-sim.pid 2>/dev/null || true)
  if [ -n "$SIM_PID" ] && kill -0 "$SIM_PID" 2>/dev/null; then
    kill "$SIM_PID" 2>/dev/null || true
    # Also kill child processes
    pkill -P "$SIM_PID" 2>/dev/null || true
    echo -e "  ${GREEN}Simulators stopped (PID: ${SIM_PID})${RESET}"
  else
    echo -e "  ${GREEN}No running simulators found${RESET}"
  fi
  rm -f /tmp/hubex-demo-sim.pid
else
  echo -e "  ${GREEN}No simulator PID file found${RESET}"
fi

# ── Authenticate ──────────────────────────────────────────
echo -e "\n${YELLOW}[2/4] Authenticating...${RESET}"
LOGIN_RESP=$(curl -s -X POST "${SERVER}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${DEMO_EMAIL}\",\"password\":\"${DEMO_PASSWORD}\"}" 2>/dev/null || true)

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || true)

if [ -z "$TOKEN" ]; then
  echo -e "  ${RED}Failed to authenticate. Is the backend running?${RESET}"
  exit 1
fi
echo -e "  ${GREEN}Authenticated${RESET}"

# ── Full reset: delete ALL user data for clean slate ──────
echo -e "\n${YELLOW}[3/4] Removing ALL data (full reset)...${RESET}"
DELETE_RESP=$(curl -s -w "\n%{http_code}" -X DELETE "${SERVER}/api/v1/system/reset" \
  -H "Authorization: Bearer ${TOKEN}" 2>/dev/null || true)

DELETE_STATUS=$(echo "$DELETE_RESP" | tail -1)

if [ "$DELETE_STATUS" = "200" ]; then
  echo -e "  ${GREEN}All data removed (clean slate)${RESET}"
elif [ "$DELETE_STATUS" = "403" ]; then
  # Fallback: user may not have cap.admin, try demo-data only
  echo -e "  ${YELLOW}No admin access — falling back to demo data cleanup only${RESET}"
  DELETE_RESP=$(curl -s -w "\n%{http_code}" -X DELETE "${SERVER}/api/v1/system/demo-data" \
    -H "Authorization: Bearer ${TOKEN}" 2>/dev/null || true)
  DELETE_STATUS=$(echo "$DELETE_RESP" | tail -1)
  if [ "$DELETE_STATUS" = "200" ]; then
    echo -e "  ${GREEN}Demo data removed${RESET}"
  else
    echo -e "  ${YELLOW}Delete response: ${DELETE_STATUS}${RESET}"
  fi
else
  echo -e "  ${YELLOW}Reset response: ${DELETE_STATUS} (may be empty already)${RESET}"
fi

# ── Re-seed ───────────────────────────────────────────────
echo -e "\n${YELLOW}[4/4] Re-seeding demo data...${RESET}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "${SCRIPT_DIR}/setup-demo.sh" "${SERVER}"
