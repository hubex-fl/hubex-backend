#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"
SECONDS="${HUBEX_SIM_SECONDS:-12}"
if [ -z "$TOKEN" ]; then
  echo "FAIL: HUBEX_TOKEN missing"
  exit 1
fi

DEVICE_UID="sim-var2-$(date +%s)"

fail() {
  echo "FAIL: $1"
  if [ -n "${2:-}" ]; then
    echo "Status: $2"
    echo "Body: $3"
  fi
  exit 1
}

call_api() {
  method="$1"; url="$2"; body="$3"; shift 3
  resp=$(printf "%s" "$body" | curl -sS -X "$method" "$url" "$@" --data-binary '@-' -w "\n%{http_code}")
  status=$(printf "%s" "$resp" | tail -n 1)
  body_out=$(printf "%s" "$resp" | sed '$d')
  printf "%s\n%s" "$status" "$body_out"
}

# Seed defs
for def in \
  '{"key":"system.units","scope":"global","valueType":"string","defaultValue":"metric","enumValues":["metric","imperial"]}' \
  '{"key":"device.telemetry_interval_ms","scope":"device","valueType":"int","defaultValue":5000,"unit":"ms","minValue":500,"maxValue":60000,"deviceWritable":true,"userWritable":true}' \
  '{"key":"device.temp_offset","scope":"device","valueType":"float","defaultValue":0.0,"minValue":-5,"maxValue":5,"deviceWritable":true,"userWritable":true}'; do
  resp=$(printf "%s" "$def" | curl -sS -X POST "$BASE/api/v1/variables/defs" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    --data-binary '@-' -w "\n%{http_code}")
  status=$(printf "%s" "$resp" | tail -n 1)
  if [ "$status" != "200" ] && [ "$status" != "201" ] && [ "$status" != "409" ]; then
    fail "seed defs" "$status" "$(printf "%s" "$resp" | sed '$d')"
  fi
done

echo "OK: seeded defs"

# Fetch defs and select keys
defs=$(curl -sS -X GET "$BASE/api/v1/variables/defs" -H "Authorization: Bearer $TOKEN" -w "\n%{http_code}")
defs_status=$(printf "%s" "$defs" | tail -n 1)
defs_body=$(printf "%s" "$defs" | sed '$d')
if [ "$defs_status" != "200" ]; then
  fail "list defs" "$defs_status" "$defs_body"
fi
global_key=$(printf "%s" "$defs_body" | python -c "import sys,json;data=json.load(sys.stdin);print(next((d.get('key') for d in data if d.get('scope') in ('system','global')),''))")
global_scope=$(printf "%s" "$defs_body" | python -c "import sys,json;data=json.load(sys.stdin);print(next((d.get('scope') for d in data if d.get('scope') in ('system','global')),''))")
device_key=$(printf "%s" "$defs_body" | python -c "import sys,json;print(next((d['key'] for d in json.load(sys.stdin) if d.get('scope')=='device'),''))")
device_scope=$(printf "%s" "$defs_body" | python -c "import sys,json;print(next((d.get('scope') for d in json.load(sys.stdin) if d.get('scope')=='device'),''))")
if [ -z "$global_key" ]; then
  fail "no global variable definitions available" "$defs_status" "$defs_body"
fi
if [ -z "$device_key" ]; then
  fail "no device variable definitions available" "$defs_status" "$defs_body"
fi

# Provision device
hello='{"device_uid":"'"$DEVICE_UID"'","firmware_version":"sim","capabilities":{"sim":true}}'
resp=$(printf "%s" "$hello" | curl -sS -X POST "$BASE/api/v1/devices/hello" \
  -H "Content-Type: application/json" --data-binary '@-' -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
if [ "$status" != "200" ]; then
  fail "devices/hello" "$status" "$(printf "%s" "$resp" | sed '$d')"
fi

echo "OK: hello $DEVICE_UID"

# Pairing start
start='{"device_uid":"'"$DEVICE_UID"'"}'
resp=$(printf "%s" "$start" | curl -sS -X POST "$BASE/api/v1/pairing/start" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data-binary '@-' -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
body=$(printf "%s" "$resp" | sed '$d')
if [ "$status" != "200" ]; then
  fail "pairing/start" "$status" "$body"
fi
code=$(printf "%s" "$body" | python -c "import sys,json;print(json.load(sys.stdin).get('pairing_code',''))")
if [ -z "$code" ]; then
  fail "pairing/start missing pairing_code" "$status" "$body"
fi

echo "OK: pairing_code=$code"

# Pairing confirm
confirm='{"device_uid":"'"$DEVICE_UID"'","pairing_code":"'"$code"'"}'
resp=$(printf "%s" "$confirm" | curl -sS -X POST "$BASE/api/v1/pairing/confirm" \
  -H "Content-Type: application/json" --data-binary '@-' -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
body=$(printf "%s" "$resp" | sed '$d')
if [ "$status" != "200" ]; then
  fail "pairing/confirm" "$status" "$body"
fi
DEVICE_TOKEN=$(printf "%s" "$body" | python -c "import sys,json;print(json.load(sys.stdin).get('device_token',''))")
if [ -z "$DEVICE_TOKEN" ]; then
  fail "pairing/confirm missing device_token" "$status" "$body"
fi

echo "OK: device token issued"

# Verify claim persisted
resp=$(curl -sS -X GET "$BASE/api/v1/devices/lookup/$DEVICE_UID" \
  -H "Authorization: Bearer $TOKEN" -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
body=$(printf "%s" "$resp" | sed '$d')
if [ "$status" != "200" ]; then
  fail "devices/lookup" "$status" "$body"
fi
claimed=$(printf "%s" "$body" | python -c "import sys,json;print(json.load(sys.stdin).get('claimed'))")
if [ "$claimed" != "True" ] && [ "$claimed" != "true" ]; then
  fail "pairing confirm did not persist claim" "$status" "$body"
fi
echo "OK: claim persisted"

# Set vars
set_global='{"key":"'"$global_key"'","scope":"'"$global_scope"'","value":"metric"}'
resp=$(printf "%s" "$set_global" | curl -sS -X POST "$BASE/api/v1/variables/set" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data-binary '@-' -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
if [ "$status" != "200" ]; then
  fail "set global" "$status" "$(printf "%s" "$resp" | sed '$d')"
fi

set_device='{"key":"'"$device_key"'","scope":"'"$device_scope"'","deviceUid":"'"$DEVICE_UID"'","value":1.5}'
resp=$(printf "%s" "$set_device" | curl -sS -X POST "$BASE/api/v1/variables/set" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data-binary '@-' -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
if [ "$status" != "200" ]; then
  fail "set device" "$status" "$(printf "%s" "$resp" | sed '$d')"
fi

echo "OK: vars set"

resp=$(curl -sS -X GET "$BASE/api/v1/variables/effective?deviceUid=$DEVICE_UID" \
  -H "Authorization: Bearer $TOKEN" -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
if [ "$status" != "200" ]; then
  fail "effective vars" "$status" "$(printf "%s" "$resp" | sed '$d')"
fi

echo "OK: effective vars"

echo "Running simulator..."
python -m app.simulator --base "$BASE" --device-uid "$DEVICE_UID" --device-token "$DEVICE_TOKEN" --user-token "$TOKEN" --vars-effective --vars-ack --vars-poll-seconds 5 --seconds "$SECONDS"

echo "OK"
