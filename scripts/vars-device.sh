#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"
DEVICE_UID="${HUBEX_DEVICE_UID:-}"

if [ -z "$TOKEN" ]; then
  echo "FAIL: HUBEX_TOKEN missing"
  exit 1
fi
if [ -z "$DEVICE_UID" ]; then
  echo "FAIL: HUBEX_DEVICE_UID missing"
  exit 1
fi

resp=$(curl -sS -X GET "$BASE/api/v1/variables/device/$DEVICE_UID" \
  -H "Authorization: Bearer $TOKEN" -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
body=$(printf "%s" "$resp" | sed '$d')

if [ "$status" != "200" ]; then
  echo "FAIL: device variables"
  echo "Status: $status"
  echo "Body: $body"
  exit 1
fi

echo "OK"
echo "$body"
