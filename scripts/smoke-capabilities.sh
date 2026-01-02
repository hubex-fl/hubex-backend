#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"

echo "SMOKE_CAPS base=$BASE"

# Enforce=0 (log-only)
if [ "${HUBEX_CAPS_ENFORCE:-0}" != "1" ]; then
  echo "MODE enforce=0"
else
  echo "MODE enforce=0 (skipped: server enforcing)"
fi

if [ "${HUBEX_CAPS_ENFORCE:-0}" != "1" ]; then
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

  if [ -n "$TOKEN" ]; then
    ok_status=$(curl -s -o /tmp/smoke_caps_ok.json -w "%{http_code}" \
      -H "Authorization: Bearer $TOKEN" \
      -X GET "$BASE/api/v1/devices")
    if [ "$ok_status" != "200" ]; then
      echo "FAIL enforce=0 expected 200 got $ok_status"
      cat /tmp/smoke_caps_ok.json
      exit 1
    fi
    echo "OK enforce=0 non-whitelist with token => 200"
  else
    echo "HUBEX_TOKEN missing; skip enforce=0 token check"
  fi
fi

# Enforce=1 (real blocking)
echo "MODE enforce=1"

if [ -z "$TOKEN" ]; then
  echo "HUBEX_TOKEN missing; cannot verify 403 on insufficient caps"
  exit 0
fi

forbidden_status=$(curl -s -o /tmp/smoke_caps_forbidden.json -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  -X GET "$BASE/api/v1/devices")
if [ "$forbidden_status" != "403" ]; then
  echo "FAIL enforce=1 expected 403 got $forbidden_status"
  cat /tmp/smoke_caps_forbidden.json
  exit 1
fi
echo "OK enforce=1 non-whitelist with token lacking caps => 403"
