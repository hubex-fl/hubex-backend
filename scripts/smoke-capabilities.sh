#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"

export HUBEX_CAPS_ENFORCE=1

echo "SMOKE_CAPS base=$BASE"

uid="smoke-caps-$(date +%s)"
hello_status=$(curl -s -o /tmp/smoke_caps_hello.json -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -X POST "$BASE/api/v1/devices/hello" \
  -d "{\"device_uid\":\"$uid\"}")
if [ "$hello_status" != "200" ]; then
  echo "FAIL whitelist /devices/hello expected 200 got $hello_status"
  cat /tmp/smoke_caps_hello.json
  exit 1
fi
echo "OK whitelist /devices/hello"

noauth_status=$(curl -s -o /tmp/smoke_caps_noauth.json -w "%{http_code}" \
  -X GET "$BASE/api/v1/devices")
if [ "$noauth_status" != "401" ]; then
  echo "FAIL non-whitelist without token expected 401 got $noauth_status"
  cat /tmp/smoke_caps_noauth.json
  exit 1
fi
echo "OK non-whitelist without token => 401"

if [ -z "$TOKEN" ]; then
  echo "HUBEX_TOKEN missing; cannot verify 403 on insufficient caps"
  exit 0
fi

forbidden_status=$(curl -s -o /tmp/smoke_caps_forbidden.json -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  -X GET "$BASE/api/v1/devices")
if [ "$forbidden_status" != "403" ]; then
  echo "FAIL non-whitelist with token expected 403 got $forbidden_status"
  cat /tmp/smoke_caps_forbidden.json
  exit 1
fi
echo "OK non-whitelist with token lacking caps => 403"
