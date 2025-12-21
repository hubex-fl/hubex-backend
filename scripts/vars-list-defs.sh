#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"
SCOPE="${HUBEX_VAR_SCOPE:-}"

if [ -z "$TOKEN" ]; then
  echo "FAIL: HUBEX_TOKEN missing"
  exit 1
fi

url="$BASE/api/v1/variables/definitions"
if [ -n "$SCOPE" ]; then
  url="$url?scope=$SCOPE"
fi

resp=$(curl -sS -X GET "$url" -H "Authorization: Bearer $TOKEN" -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
body=$(printf "%s" "$resp" | sed '$d')

if [ "$status" != "200" ]; then
  echo "FAIL: list definitions"
  echo "Status: $status"
  echo "Body: $body"
  exit 1
fi

echo "OK"
echo "$body"
