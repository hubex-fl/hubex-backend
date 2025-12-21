#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
EMAIL="${HUBEX_EMAIL:-dev@example.com}"
PASSWORD="${HUBEX_PASSWORD:-devdevdev}"

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
  if [ -n "$body" ]; then
    resp=$(printf "%s" "$body" | curl -sS -X "$method" "$url" -H "Content-Type: application/json" --data-binary @- -w "\n%{http_code}")
  else
    resp=$(curl -sS -X "$method" "$url" -w "\n%{http_code}")
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
resp=$(call "POST" "$BASE/api/v1/auth/login" "$payload")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
if [ "$status" != "200" ]; then
  echo "Register..."
  reg=$(call "POST" "$BASE/api/v1/auth/register" "$payload")
  rstatus=$(printf "%s" "$reg" | head -n 1)
  rbody=$(printf "%s" "$reg" | tail -n +2)
  [ "$rstatus" = "200" ] || fail "register" "$rstatus" "$rbody"
  resp=$(call "POST" "$BASE/api/v1/auth/login" "$payload")
  status=$(printf "%s" "$resp" | head -n 1)
  body=$(printf "%s" "$resp" | tail -n +2)
  [ "$status" = "200" ] || fail "login" "$status" "$body"
fi

token=$(printf "%s" "$body" | json_get access_token)
[ -n "$token" ] || token=$(printf "%s" "$body" | json_get token)
[ -n "$token" ] || fail "login token missing" "$status" "$body"

echo "OK: token acquired"
echo "HUBEX_TOKEN=$token"
echo "PowerShell:  $env:HUBEX_TOKEN=\"$token\""
echo "bash:        export HUBEX_TOKEN=\"$token\""
