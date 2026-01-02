#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"

if [ -z "$TOKEN" ]; then
  echo "HUBEX_TOKEN missing" >&2
  exit 1
fi

ENDPOINT="$BASE/api/v1/variables/defs"

call_once() {
  status=$(curl -sS -o /tmp/rl_body.$$ -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$ENDPOINT" || true)
  body=$(cat /tmp/rl_body.$$ 2>/dev/null || true)
  echo "$status:$body"
}

echo "SMOKE_RL_BASE=$BASE"

has429=0
for i in $(seq 1 10); do
  out="$(call_once)"
  status="${out%%:*}"
  if [ "$status" = "429" ]; then
    has429=1
  fi
done

if [ "${HUBEX_RL_ENABLED:-0}" = "1" ]; then
  if [ "$has429" -eq 0 ]; then
    echo "FAIL: expected 429 with HUBEX_RL_ENABLED=1" >&2
    exit 1
  fi
  echo "OK: 429 observed (rate limit enabled)"
else
  if [ "$has429" -eq 1 ]; then
    echo "FAIL: unexpected 429 with HUBEX_RL_ENABLED!=1" >&2
    exit 1
  fi
  echo "OK: no 429 (rate limit disabled)"
fi
