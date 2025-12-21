#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
EMAIL="${HUBEX_EMAIL:-dev@example.com}"
PASSWORD="${HUBEX_PASSWORD:-devdevdev}"
SIM_SECONDS="${HUBEX_SIM_SECONDS:-30}"

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
  if [ -n "$body" ]; then
    if [ -n "$auth" ]; then
      resp=$(printf "%s" "$body" | curl -sS -X "$method" "$url" -H "Authorization: Bearer $auth" -H "Content-Type: application/json" --data-binary @- -w "\n%{http_code}")
    else
      resp=$(printf "%s" "$body" | curl -sS -X "$method" "$url" -H "Content-Type: application/json" --data-binary @- -w "\n%{http_code}")
    fi
  else
    if [ -n "$auth" ]; then
      resp=$(curl -sS -X "$method" "$url" -H "Authorization: Bearer $auth" -w "\n%{http_code}")
    else
      resp=$(curl -sS -X "$method" "$url" -w "\n%{http_code}")
    fi
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

payload=$(printf '{"email":"%s","password":"%s"}' "$EMAIL" "$PASSWORD")

echo "Login..."
resp=$(call "POST" "$BASE/api/v1/auth/login" "$payload" "")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
if [ "$status" != "200" ]; then
  echo "Register..."
  reg=$(call "POST" "$BASE/api/v1/auth/register" "$payload" "")
  rstatus=$(printf "%s" "$reg" | head -n 1)
  rbody=$(printf "%s" "$reg" | tail -n +2)
  [ "$rstatus" = "200" ] || fail "register" "$rstatus" "$rbody"
  resp=$(call "POST" "$BASE/api/v1/auth/login" "$payload" "")
  status=$(printf "%s" "$resp" | head -n 1)
  body=$(printf "%s" "$resp" | tail -n +2)
  [ "$status" = "200" ] || fail "login" "$status" "$body"
fi

token=$(printf "%s" "$body" | json_get access_token)
[ -n "$token" ] || fail "login token missing" "$status" "$body"

device_uid="e2e-$(date +%Y%m%d%H%M%S)"
hello_body=$(printf '{"device_uid":"%s","firmware_version":"sim-1.0","capabilities":{"sim":true}}' "$device_uid")
resp=$(call "POST" "$BASE/api/v1/devices/hello" "$hello_body" "")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
[ "$status" = "200" ] || fail "devices/hello" "$status" "$body"

device_id=$(printf "%s" "$body" | json_get device_id)

pair_body=$(printf '{"device_uid":"%s"}' "$device_uid")
resp=$(call "POST" "$BASE/api/v1/pairing/start" "$pair_body" "$token")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
[ "$status" = "200" ] || fail "pairing start" "$status" "$body"
code=$(printf "%s" "$body" | json_get pairing_code)
[ -n "$code" ] || fail "pairing start missing pairing_code" "$status" "$body"

confirm_body=$(printf '{"device_uid":"%s","pairing_code":"%s"}' "$device_uid" "$code")
resp=$(call "POST" "$BASE/api/v1/pairing/confirm" "$confirm_body" "")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
[ "$status" = "200" ] || fail "pairing confirm" "$status" "$body"

device_token=$(printf "%s" "$body" | json_get device_token)
[ -n "$device_token" ] || fail "pairing confirm missing token" "$status" "$body"

echo "Lookup device..."
resp=$(call "GET" "$BASE/api/v1/devices/lookup/$device_uid" "" "$token")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
[ "$status" = "200" ] || fail "lookup" "$status" "$body"

echo "Run simulator for $SIM_SECONDS seconds..."
python -m tools.device_sim --base "$BASE" --device-uid "$device_uid" --device-token "$device_token" --seconds "$SIM_SECONDS"

echo "OK: e2e complete"
echo "DEVICE_UID=$device_uid"
echo "DEVICE_ID=$device_id"
echo "DEVICE_TOKEN=$device_token"
