#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"
COUNT="${HUBEX_DEVICE_COUNT:-3}"
PREFIX="${HUBEX_DEVICE_PREFIX:-dev-seed}"
CLAIM_ONE="${HUBEX_CLAIM_ONE:-0}"

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

uids=""
ids=""
claimed_uid=""
claimed_id=""
claimed_token=""

for i in $(seq 1 "$COUNT"); do
  uid="${PREFIX}-$(date +%Y%m%d%H%M%S)-$i"
  hello_body=$(printf '{"device_uid":"%s","firmware_version":"1.0.%s","capabilities":{"wifi":true,"sensors":{"temp":true}}}' "$uid" "$i")
  resp=$(call "POST" "$BASE/api/v1/devices/hello" "$hello_body" "")
  status=$(printf "%s" "$resp" | head -n 1)
  body=$(printf "%s" "$resp" | tail -n +2)
  [ "$status" = "200" ] || fail "devices/hello" "$status" "$body"
  id=$(printf "%s" "$body" | json_get device_id)
  uids="$uids$uid,"
  ids="$ids$id,"

  if [ "$CLAIM_ONE" = "1" ] && [ -z "$claimed_uid" ]; then
    [ -n "$TOKEN" ] || fail "HUBEX_TOKEN required to claim"
    pair_body=$(printf '{"device_uid":"%s"}' "$uid")
    resp=$(call "POST" "$BASE/api/v1/pairing/start" "$pair_body" "$TOKEN")
    status=$(printf "%s" "$resp" | head -n 1)
    body=$(printf "%s" "$resp" | tail -n +2)
    if [ "$status" != "200" ] && [ "$status" != "409" ]; then
      fail "pairing start" "$status" "$body"
    fi
    code=$(printf "%s" "$body" | json_get pairing_code)
    [ -n "$code" ] || fail "pairing start missing pairing_code" "$status" "$body"
    confirm_body=$(printf '{"device_uid":"%s","pairing_code":"%s"}' "$uid" "$code")
    resp=$(call "POST" "$BASE/api/v1/pairing/confirm" "$confirm_body" "")
    status=$(printf "%s" "$resp" | head -n 1)
    body=$(printf "%s" "$resp" | tail -n +2)
    [ "$status" = "200" ] || fail "pairing confirm" "$status" "$body"
    claimed_uid="$uid"
    claimed_id=$(printf "%s" "$body" | json_get device_id)
    claimed_token=$(printf "%s" "$body" | json_get device_token)
  fi
done

uids=${uids%,}
ids=${ids%,}

echo "OK: provisioned $COUNT device(s)"
echo "DEVICE_UIDS=$uids"
echo "DEVICE_IDS=$ids"
if [ -n "$claimed_uid" ]; then
  echo "CLAIMED_DEVICE_UID=$claimed_uid"
  echo "CLAIMED_DEVICE_ID=$claimed_id"
  echo "CLAIMED_DEVICE_TOKEN=$claimed_token"
fi
