#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"
KEY="${HUBEX_VAR_KEY:-}"
SCOPE="${HUBEX_VAR_SCOPE:-global}"
DEVICE_UID="${HUBEX_DEVICE_UID:-}"
VALUE_JSON="${HUBEX_VAR_VALUE_JSON:-}"
VALUE_RAW="${HUBEX_VAR_VALUE:-}"
EXPECTED="${HUBEX_VAR_EXPECTED_VERSION:-}"
FORCE="${HUBEX_VAR_FORCE:-}"
DEVICE_TOKEN="${HUBEX_DEVICE_TOKEN:-}"

if [ -z "$TOKEN" ] && [ -z "$DEVICE_TOKEN" ]; then
  echo "FAIL: HUBEX_TOKEN or HUBEX_DEVICE_TOKEN missing"
  exit 1
fi
if [ -z "$KEY" ]; then
  echo "FAIL: HUBEX_VAR_KEY missing"
  exit 1
fi
if [ "$SCOPE" = "device" ] && [ -z "$DEVICE_UID" ]; then
  echo "FAIL: HUBEX_DEVICE_UID missing"
  exit 1
fi
if [ -z "$VALUE_JSON" ] && [ -z "$VALUE_RAW" ]; then
  echo "FAIL: HUBEX_VAR_VALUE or HUBEX_VAR_VALUE_JSON missing"
  exit 1
fi

if [ -n "$VALUE_JSON" ]; then
  VALUE="$VALUE_JSON"
else
  VALUE="\"$VALUE_RAW\""
fi

payload="{\"key\":\"$KEY\",\"scope\":\"$SCOPE\",\"value\":$VALUE"
if [ "$SCOPE" = "device" ]; then
  payload="$payload,\"deviceUid\":\"$DEVICE_UID\""
fi
if [ -n "$EXPECTED" ]; then
  payload="$payload,\"expectedVersion\":$EXPECTED"
fi
if [ -n "$FORCE" ]; then
  payload="$payload,\"force\":true"
fi
payload="$payload}"

if [ -n "$DEVICE_TOKEN" ]; then
  AUTH_HEADER="X-Device-Token: $DEVICE_TOKEN"
else
  AUTH_HEADER="Authorization: Bearer $TOKEN"
fi

resp=$(printf "%s" "$payload" | curl -sS -X POST "$BASE/api/v1/variables/set" \
  -H "$AUTH_HEADER" -H "Content-Type: application/json" \
  --data-binary '@-' -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
body=$(printf "%s" "$resp" | sed '$d')

if [ "$status" != "200" ]; then
  echo "FAIL: set value"
  echo "Status: $status"
  echo "Body: $body"
  exit 1
fi

echo "OK"
echo "$body"
