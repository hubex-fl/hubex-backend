#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
EMAIL="${HUBEX_EMAIL:-dev@example.com}"
PASSWORD="${HUBEX_PASSWORD:-devdevdev}"
KNOWN_UID="${HUBEX_KNOWN_UID:-debug-test-1}"

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

echo "Login..."
login_body=$(printf '{"email":"%s","password":"%s"}' "$EMAIL" "$PASSWORD")
login_resp=$(call "POST" "$BASE/api/v1/auth/login" "$login_body" "")
login_status=$(printf "%s" "$login_resp" | head -n 1)
login_body_out=$(printf "%s" "$login_resp" | tail -n +2)
if [ "$login_status" != "200" ]; then
  fail "login" "$login_status" "$login_body_out"
fi

token=$(printf "%s" "$login_body_out" | json_get access_token)
if [ -z "$token" ]; then
  fail "login token missing" "$login_status" "$login_body_out"
fi

echo "Lookup without token (expect 401)..."
resp=$(call "GET" "$BASE/api/v1/devices/lookup/$KNOWN_UID" "" "")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
[ "$status" = "401" ] || fail "lookup without token" "$status" "$body"

echo "Lookup known UID..."
resp=$(call "GET" "$BASE/api/v1/devices/lookup/$KNOWN_UID" "" "$token")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
[ "$status" = "200" ] || fail "lookup known UID" "$status" "$body"

echo "Lookup unknown UID..."
resp=$(call "GET" "$BASE/api/v1/devices/lookup/___does_not_exist___" "" "$token")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
[ "$status" = "404" ] || fail "lookup unknown UID" "$status" "$body"
code=$(printf "%s" "$body" | json_get detail.code)
msg=$(printf "%s" "$body" | json_get detail.message)
[ "$code" = "DEVICE_UNKNOWN_UID" ] || fail "lookup unknown UID detail code" "$status" "$body"
[ "$msg" = "Unknown device UID" ] || fail "lookup unknown UID detail message" "$status" "$body"

echo "Pairing start..."
pair_body=$(printf '{"device_uid":"%s"}' "$KNOWN_UID")
resp=$(call "POST" "$BASE/api/v1/pairing/start" "$pair_body" "$token")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
if [ "$status" = "200" ]; then
  code=$(printf "%s" "$body" | json_get pairing_code)
  [ -n "$code" ] || fail "pairing start missing pairing_code" "$status" "$body"
elif [ "$status" = "409" ]; then
  code=$(printf "%s" "$body" | json_get detail.code)
  [ "$code" = "PAIRING_ALREADY_ACTIVE" ] || fail "pairing start conflict code" "$status" "$body"
else
  fail "pairing start" "$status" "$body"
fi

echo "OK"
