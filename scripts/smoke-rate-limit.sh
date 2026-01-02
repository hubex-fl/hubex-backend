#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"

if [ -z "$TOKEN" ]; then
  echo "HUBEX_TOKEN missing" >&2
  exit 1
fi

ENDPOINT="$BASE/api/v1/devices"

call_once() {
  curl -sS -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$ENDPOINT" || true
}

echo "SMOKE_RL_BASE=$BASE"

count_200=0
count_401=0
count_403=0
count_429=0

inc() {
  case "$1" in
    200) count_200=$((count_200+1)) ;;
    401) count_401=$((count_401+1)) ;;
    403) count_403=$((count_403+1)) ;;
    429) count_429=$((count_429+1)) ;;
  esac
}

if [ "${HUBEX_RL_ENABLED:-0}" = "1" ]; then
  max=60
  found=0
  i=1
  while [ "$i" -le "$max" ]; do
    status="$(call_once)"
    inc "$status"
    if [ "$status" = "429" ]; then
      found=1
      break
    fi
    i=$((i+1))
  done
  if [ "$found" -eq 0 ]; then
    echo "FAIL: expected 429 with HUBEX_RL_ENABLED=1" >&2
    exit 1
  fi
  echo "OK: 429 observed (rate limit enabled)"
else
  for i in $(seq 1 15); do
    status="$(call_once)"
    inc "$status"
    if [ "$status" = "429" ]; then
      echo "FAIL: unexpected 429 with HUBEX_RL_ENABLED!=1" >&2
      exit 1
    fi
  done
  echo "OK: no 429 (rate limit disabled)"
fi

echo "STATUS_HISTOGRAM 200=$count_200,401=$count_401,403=$count_403,429=$count_429"
