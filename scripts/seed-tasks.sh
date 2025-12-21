#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"
DEVICE_ID="${HUBEX_DEVICE_ID:-}"
DEVICE_TOKEN="${HUBEX_DEVICE_TOKEN:-}"
CONTEXT_KEY="${HUBEX_CONTEXT_KEY:-default}"

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
  auth="$4"
  extra="$5"
  if [ -n "$body" ]; then
    resp=$(printf "%s" "$body" | curl -sS -X "$method" "$url" $extra -H "Content-Type: application/json" -H "Authorization: Bearer $auth" --data-binary @- -w "\n%{http_code}")
  else
    resp=$(curl -sS -X "$method" "$url" $extra -H "Authorization: Bearer $auth" -w "\n%{http_code}")
  fi
  status=$(printf "%s" "$resp" | tail -n 1)
  body_out=$(printf "%s" "$resp" | sed '$d')
  printf "%s\n%s" "$status" "$body_out"
}

json_get() {
  python - <<'PY'
import json
import sys

body = sys.stdin.read()
try:
    obj = json.loads(body)
except Exception:
    print("")
    sys.exit(0)

key = sys.argv[1]
cur = obj
for part in key.split('.'):
    if isinstance(cur, dict) and part in cur:
        cur = cur[part]
    else:
        print("")
        sys.exit(0)

if isinstance(cur, (dict, list)):
    print(json.dumps(cur))
else:
    print(cur)
PY
}

[ -n "$TOKEN" ] || fail "HUBEX_TOKEN required"
[ -n "$DEVICE_ID" ] || fail "HUBEX_DEVICE_ID required"
[ -n "$DEVICE_TOKEN" ] || fail "HUBEX_DEVICE_TOKEN required"

context_body=$(printf '{"context_key":"%s","capabilities":{"tasks":["config.apply"]},"meta":{"version":"1.0"}}' "$CONTEXT_KEY")
resp=$(printf "%s" "$context_body" | curl -sS -X POST "$BASE/api/v1/tasks/context/heartbeat" -H "Content-Type: application/json" -H "X-Device-Token: $DEVICE_TOKEN" --data-binary @- -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
body=$(printf "%s" "$resp" | sed '$d')
[ "$status" = "200" ] || fail "context heartbeat" "$status" "$body"

task_body=$(printf '{"type":"config.apply","payload":{"mode":"seed"},"execution_context_key":"%s"}' "$CONTEXT_KEY")
resp=$(printf "%s" "$task_body" | curl -sS -X POST "$BASE/api/v1/devices/$DEVICE_ID/tasks" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" --data-binary @- -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
body=$(printf "%s" "$resp" | sed '$d')
[ "$status" = "200" ] || fail "owner enqueue task" "$status" "$body"

task_id=$(printf "%s" "$body" | json_get id)
[ -n "$task_id" ] || fail "task id missing" "$status" "$body"

resp=$(curl -sS -X POST "$BASE/api/v1/tasks/poll?limit=1&context_key=$CONTEXT_KEY&lease_seconds=300" -H "X-Device-Token: $DEVICE_TOKEN" -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
body=$(printf "%s" "$resp" | sed '$d')
[ "$status" = "200" ] || fail "task poll" "$status" "$body"
lease_token=$(printf "%s" "$body" | python - <<'PY'
import json
import sys
try:
    arr = json.loads(sys.stdin.read())
except Exception:
    print("")
    sys.exit(0)
if isinstance(arr, list) and arr:
    print(arr[0].get("lease_token") or "")
else:
    print("")
PY
)
[ -n "$lease_token" ] || fail "lease_token missing" "$status" "$body"

echo "OK: task claimed"
echo "TASK_ID=$task_id"
echo "LEASE_TOKEN=$lease_token"
echo "NOTE: task left in_flight to keep device busy"
