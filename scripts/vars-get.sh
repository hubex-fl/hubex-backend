#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"
KEY="${HUBEX_VAR_KEY:-}"
SCOPE="${HUBEX_VAR_SCOPE:-global}"
DEVICE_UID="${HUBEX_DEVICE_UID:-}"

if [ -z "$TOKEN" ]; then
  echo "FAIL: HUBEX_TOKEN missing"
  exit 1
fi
if [ -z "$KEY" ]; then
  echo "FAIL: HUBEX_VAR_KEY missing"
  exit 1
fi

url="$BASE/api/v1/variables/value?key=$KEY&scope=$SCOPE"
if [ "$SCOPE" = "device" ]; then
  if [ -z "$DEVICE_UID" ]; then
    echo "FAIL: HUBEX_DEVICE_UID missing"
    exit 1
  fi
  url="$url&deviceUid=$DEVICE_UID"
fi

resp=$(curl -sS -X GET "$url" -H "Authorization: Bearer $TOKEN" -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
body=$(printf "%s" "$resp" | sed '$d')

if [ "$status" != "200" ]; then
  echo "FAIL: get value"
  echo "Status: $status"
  echo "Body: $body"
  exit 1
fi

echo "OK"
echo "$body"
