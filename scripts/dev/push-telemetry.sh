#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_DEVICE_TOKEN:-${DEVICE_TOKEN:-}}"
COUNT="${HUBEX_TELEMETRY_COUNT:-5}"
INTERVAL_MS="${HUBEX_TELEMETRY_INTERVAL_MS:-1000}"

fail() {
  echo "FAIL: $1"
  if [ -n "${2:-}" ]; then
    echo "Status: $2"
  fi
  if [ -n "${3:-}" ]; then
    echo "Body: $3"
  fi
  exit 1
}

call() {
  method="$1"
  url="$2"
  body="$3"
  resp=$(printf "%s" "$body" | curl -sS -X "$method" "$url" -H "Content-Type: application/json" -H "X-Device-Token: $TOKEN" --data-binary @- -w "\n%{http_code}")
  status=$(printf "%s" "$resp" | tail -n 1)
  body_out=$(printf "%s" "$resp" | sed '$d')
  printf "%s\n%s" "$status" "$body_out"
}

[ -n "$TOKEN" ] || fail "HUBEX_DEVICE_TOKEN required"

ok=0
for i in $(seq 1 "$COUNT"); do
  payload=$(printf '{"event_type":"sample","payload":{"temp_c":%s,"voltage":3.7,"rssi":-65,"ok":true}}' "$((20+i))")
  resp=$(call "POST" "$BASE/api/v1/telemetry" "$payload")
  status=$(printf "%s" "$resp" | head -n 1)
  body=$(printf "%s" "$resp" | tail -n +2)
  [ "$status" = "200" ] || fail "telemetry post" "$status" "$body"
  ok=$((ok+1))
  if [ "$i" -lt "$COUNT" ]; then
    sleep $(python - <<PY
ms=int("$INTERVAL_MS")
print(ms/1000)
PY
)
  fi
done

echo "OK: telemetry sent $ok/$COUNT"
