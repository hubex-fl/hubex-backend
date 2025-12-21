#!/usr/bin/env sh
set -eu

BASE=${HUBEX_BASE:-http://127.0.0.1:8000}
TOKEN=${HUBEX_TOKEN:-}
DEVICE_UID=${HUBEX_DEVICE_UID:-}
INCLUDE_SECRETS=${HUBEX_INCLUDE_SECRETS:-}

if [ -z "$TOKEN" ]; then
  echo "FAIL: HUBEX_TOKEN missing"
  exit 1
fi

if [ -z "$DEVICE_UID" ]; then
  echo "FAIL: HUBEX_DEVICE_UID missing"
  exit 1
fi

query="deviceUid=${DEVICE_UID}"
if [ -n "$INCLUDE_SECRETS" ]; then
  query="${query}&includeSecrets=true"
fi

resp=$(curl -sS -w "\n%{http_code}" -H "Authorization: Bearer ${TOKEN}" "${BASE}/api/v1/variables/effective?${query}")
status=$(printf "%s" "$resp" | tail -n 1)
body=$(printf "%s" "$resp" | sed '$d')

if [ "$status" != "200" ]; then
  echo "FAIL: effective variables"
  echo "Status: $status"
  echo "Body: $body"
  exit 1
fi

echo "OK"
echo "$body"
