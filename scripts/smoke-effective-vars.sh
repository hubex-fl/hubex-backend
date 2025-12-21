#!/usr/bin/env sh
set -eu

BASE=${HUBEX_BASE:-http://127.0.0.1:8000}
TOKEN=${HUBEX_TOKEN:-}
if [ -z "$TOKEN" ]; then
  echo "FAIL: HUBEX_TOKEN missing"
  exit 1
fi

DEVICE_UID="sim-effective-$(date +%s)"

fail() {
  echo "FAIL: $1"
  if [ -n "${2:-}" ]; then
    echo "Status: $2"
    echo "Body: $3"
  fi
  exit 1
}

call_api() {
  method=$1
  url=$2
  body=$3
  shift 3
  headers="$@"
  if [ -n "$body" ]; then
    resp=$(printf "%s" "$body" | curl -sS -X "$method" "$url" -w "\n%{http_code}" $headers --data-binary '@-')
  else
    resp=$(curl -sS -X "$method" "$url" -w "\n%{http_code}" $headers)
  fi
  status=$(printf "%s" "$resp" | tail -n 1)
  body_out=$(printf "%s" "$resp" | sed '$d')
  echo "$status"
  echo "$body_out"
}

json_get() {
  python - <<'PY'
import json,sys
print(json.loads(sys.stdin.read()))
PY
}

printf "Provision device...\n"
hello_body=$(python - <<PY
import json
print(json.dumps({"device_uid": "$DEVICE_UID", "firmware_version": "sim-1.0", "capabilities": {"vars": True}}))
PY
)
read status body <<EOF
$(call_api POST "$BASE/api/v1/devices/hello" "$hello_body" -H "Content-Type: application/json")
EOF
[ "$status" = "200" ] || fail "devices/hello" "$status" "$body"

printf "Ensure definitions...\n"
ensure_def() {
  key=$1
  scope=$2
  value_type=$3
  default_value=$4
  payload=$(python - <<PY
import json
print(json.dumps({"key": "$key", "scope": "$scope", "valueType": "$value_type", "defaultValue": $default_value}))
PY
)
  read status body <<EOF
$(call_api POST "$BASE/api/v1/variables/definitions" "$payload" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")
EOF
  if [ "$status" = "200" ]; then return; fi
  if [ "$status" = "409" ]; then return; fi
  fail "create definition $key" "$status" "$body"
}

enable_json_string() {
  python - <<'PY'
import json
print(json.dumps("metric"))
PY
}

ensure_def system.units global string "\"metric\""
ensure_def device.temp_offset device float 0.0

printf "Set global system.units...\n"
payload=$(python - <<'PY'
import json
print(json.dumps({"key": "system.units", "scope": "global", "value": "metric"}))
PY
)
read status body <<EOF
$(call_api PUT "$BASE/api/v1/variables/value" "$payload" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")
EOF
[ "$status" = "200" ] || fail "set system.units" "$status" "$body"

printf "Set device.temp_offset override...\n"
payload=$(python - <<PY
import json
print(json.dumps({"key": "device.temp_offset", "scope": "device", "deviceUid": "$DEVICE_UID", "value": 1.5}))
PY
)
read status body <<EOF
$(call_api PUT "$BASE/api/v1/variables/value" "$payload" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")
EOF
[ "$status" = "200" ] || fail "set temp_offset" "$status" "$body"

printf "Effective variables...\n"
read status body <<EOF
$(call_api GET "$BASE/api/v1/variables/effective?deviceUid=$DEVICE_UID" "" -H "Authorization: Bearer $TOKEN")
EOF
[ "$status" = "200" ] || fail "effective variables" "$status" "$body"

python - <<PY
import json,sys
payload=json.loads("""$body""")
items=payload.get("items", [])
by_key={item["key"]: item for item in items}
if "device.temp_offset" not in by_key:
    print("FAIL: missing device.temp_offset")
    sys.exit(1)
if by_key["device.temp_offset"].get("source")!="device_override":
    print("FAIL: device.temp_offset source")
    sys.exit(1)
if float(by_key["device.temp_offset"].get("value"))!=1.5:
    print("FAIL: device.temp_offset value")
    sys.exit(1)
if "system.units" not in by_key:
    print("FAIL: missing system.units")
    sys.exit(1)
if by_key["system.units"].get("source")!="global_default":
    print("FAIL: system.units source")
    sys.exit(1)
if by_key["system.units"].get("value")!="metric":
    print("FAIL: system.units value")
    sys.exit(1)
print("Effective vars OK")
PY

printf "Pairing start...\n"
payload=$(python - <<PY
import json
print(json.dumps({"device_uid": "$DEVICE_UID"}))
PY
)
read status body <<EOF
$(call_api POST "$BASE/api/v1/pairing/start" "$payload" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")
EOF
[ "$status" = "200" ] || fail "pairing start" "$status" "$body"

pairing_code=$(python - <<PY
import json
print(json.loads("""$body""").get("pairing_code",""))
PY
)
[ -n "$pairing_code" ] || fail "missing pairing_code" "$status" "$body"

printf "Pairing confirm...\n"
payload=$(python - <<PY
import json
print(json.dumps({"device_uid": "$DEVICE_UID", "pairing_code": "$pairing_code"}))
PY
)
read status body <<EOF
$(call_api POST "$BASE/api/v1/pairing/confirm" "$payload" -H "Content-Type: application/json")
EOF
[ "$status" = "200" ] || fail "pairing confirm" "$status" "$body"

device_token=$(python - <<PY
import json
print(json.loads("""$body""").get("device_token",""))
PY
)
[ -n "$device_token" ] || fail "missing device_token" "$status" "$body"

printf "Run simulator...\n"
python -m app.simulator --base "$BASE" --device-uid "$DEVICE_UID" --device-token "$device_token" --user-token "$TOKEN" --vars-effective --vars-poll-seconds 2 --seconds 8 --interval 2

printf "OK\n"
