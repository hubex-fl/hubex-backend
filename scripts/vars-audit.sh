#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"
KEY="${HUBEX_VAR_KEY:-}"
SCOPE="${HUBEX_VAR_SCOPE:-}"
DEVICE_UID="${HUBEX_DEVICE_UID:-}"
LIMIT="${HUBEX_VAR_LIMIT:-50}"

if [ -z "$TOKEN" ]; then
  echo "FAIL: HUBEX_TOKEN missing"
  exit 1
fi
if [ -z "$KEY" ]; then
  echo "FAIL: HUBEX_VAR_KEY missing"
  exit 1
fi

url="$BASE/api/v1/variables/audit?key=$KEY&limit=$LIMIT"
if [ -n "$SCOPE" ]; then
  url="$url&scope=$SCOPE"
fi
if [ -n "$DEVICE_UID" ]; then
  url="$url&deviceUid=$DEVICE_UID"
fi

resp=$(curl -sS -X GET "$url" -H "Authorization: Bearer $TOKEN" -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
body=$(printf "%s" "$resp" | sed '$d')

if [ "$status" != "200" ]; then
  echo "FAIL: audit"
  echo "Status: $status"
  echo "Body: $body"
  exit 1
fi

echo "OK"
echo "$body"
