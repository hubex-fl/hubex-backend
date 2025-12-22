#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  echo "FAIL: HUBEX_TOKEN missing"
  exit 1
fi
DEVICE_UID="sim-var3-$(date +%s)"
SECONDS="${HUBEX_SIM_SECONDS:-12}"

fail() {
  echo "FAIL: $1"
  if [ -n "${2:-}" ]; then
    echo "Status: $2"
    echo "Body: ${3:-}"
  fi
  exit 1
}

invoke_api() {
  method="$1"
  url="$2"
  body="${3:-}"
  headers="${4:-}"
  if [ -n "$headers" ]; then
    hdr_args=""
    for h in $headers; do
      hdr_args="$hdr_args -H $h"
    done
  fi
  if [ -n "$body" ]; then
    resp="$(printf "%s" "$body" | curl -sS -X "$method" "$url" $hdr_args --data-binary @- -w "\n%{http_code}")"
  else
    resp="$(curl -sS -X "$method" "$url" $hdr_args -w "\n%{http_code}")"
  fi
  status="$(printf "%s" "$resp" | tail -n 1)"
  body_out="$(printf "%s" "$resp" | sed '$d')"
  printf "%s\n%s" "$status" "$body_out"
}

echo "Seeding v3 defs..."
./scripts/seed-vars-v3-defs.sh || fail "seed-vars-v3-defs failed"

defs_resp="$(curl -sS -X GET "$BASE/api/v1/variables/defs" -H "Authorization: Bearer $TOKEN" -w "\n%{http_code}")"
defs_status="$(printf "%s" "$defs_resp" | tail -n 1)"
defs_body="$(printf "%s" "$defs_resp" | sed '$d')"
if [ "$defs_status" != "200" ]; then
  fail "list defs" "$defs_status" "$defs_body"
fi

global_key="$(python - <<'PY' "$defs_body"
import json, sys
defs = json.loads(sys.argv[1])
global_def = next((d for d in defs if d.get("scope") in ("system", "global")), None)
print(global_def.get("key") if global_def else "")
PY
)"
global_scope="$(python - <<'PY' "$defs_body"
import json, sys
defs = json.loads(sys.argv[1])
global_def = next((d for d in defs if d.get("scope") in ("system", "global")), None)
print(global_def.get("scope") if global_def else "")
PY
)"
temp_key="$(python - <<'PY' "$defs_body"
import json, sys
defs = json.loads(sys.argv[1])
temp = next((d for d in defs if d.get("key") == "device.temp_offset"), None)
print(temp.get("key") if temp else "")
PY
)"
temp_scope="$(python - <<'PY' "$defs_body"
import json, sys
defs = json.loads(sys.argv[1])
temp = next((d for d in defs if d.get("key") == "device.temp_offset"), None)
print(temp.get("scope") if temp else "")
PY
)"
label_key="$(python - <<'PY' "$defs_body"
import json, sys
defs = json.loads(sys.argv[1])
label = next((d for d in defs if d.get("key") == "device.label"), None)
print(label.get("key") if label else "")
PY
)"
label_scope="$(python - <<'PY' "$defs_body"
import json, sys
defs = json.loads(sys.argv[1])
label = next((d for d in defs if d.get("key") == "device.label"), None)
print(label.get("scope") if label else "")
PY
)"

[ -n "$global_key" ] || fail "no global definition available" "$defs_status" "$defs_body"
[ -n "$temp_key" ] || fail "no device.temp_offset definition" "$defs_status" "$defs_body"
[ -n "$label_key" ] || fail "no device.label definition" "$defs_status" "$defs_body"

hello_body="$(python - <<'PY' "$DEVICE_UID"
import json, sys
print(json.dumps({"device_uid": sys.argv[1], "firmware_version":"sim", "capabilities":{"sim": True}}, separators=(",", ":")))
PY
)"
hello="$(printf "%s" "$hello_body" | curl -sS -X POST "$BASE/api/v1/devices/hello" -H "Content-Type: application/json" --data-binary @- -w "\n%{http_code}")"
hello_status="$(printf "%s" "$hello" | tail -n 1)"
hello_body_out="$(printf "%s" "$hello" | sed '$d')"
[ "$hello_status" = "200" ] || fail "devices/hello" "$hello_status" "$hello_body_out"
echo "OK: hello $DEVICE_UID"

start_body="$(python - <<'PY' "$DEVICE_UID"
import json, sys
print(json.dumps({"device_uid": sys.argv[1]}, separators=(",", ":")))
PY
)"
start="$(printf "%s" "$start_body" | curl -sS -X POST "$BASE/api/v1/pairing/start" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" --data-binary @- -w "\n%{http_code}")"
start_status="$(printf "%s" "$start" | tail -n 1)"
start_body_out="$(printf "%s" "$start" | sed '$d')"
[ "$start_status" = "200" ] || fail "pairing/start" "$start_status" "$start_body_out"
code="$(python - <<'PY' "$start_body_out"
import json, sys
print(json.loads(sys.argv[1]).get("pairing_code", ""))
PY
)"
[ -n "$code" ] || fail "pairing/start missing pairing_code" "$start_status" "$start_body_out"
echo "OK: pairing_code=$code"

confirm_body="$(python - <<'PY' "$DEVICE_UID" "$code"
import json, sys
print(json.dumps({"device_uid": sys.argv[1], "pairing_code": sys.argv[2]}, separators=(",", ":")))
PY
)"
confirm="$(printf "%s" "$confirm_body" | curl -sS -X POST "$BASE/api/v1/pairing/confirm" -H "Content-Type: application/json" --data-binary @- -w "\n%{http_code}")"
confirm_status="$(printf "%s" "$confirm" | tail -n 1)"
confirm_body_out="$(printf "%s" "$confirm" | sed '$d')"
[ "$confirm_status" = "200" ] || fail "pairing/confirm" "$confirm_status" "$confirm_body_out"
device_token="$(python - <<'PY' "$confirm_body_out"
import json, sys
print(json.loads(sys.argv[1]).get("device_token", ""))
PY
)"
[ -n "$device_token" ] || fail "pairing/confirm missing device_token" "$confirm_status" "$confirm_body_out"
echo "OK: device token issued"

lookup="$(curl -sS -X GET "$BASE/api/v1/devices/lookup/$DEVICE_UID" -H "Authorization: Bearer $TOKEN" -w "\n%{http_code}")"
lookup_status="$(printf "%s" "$lookup" | tail -n 1)"
lookup_body="$(printf "%s" "$lookup" | sed '$d')"
[ "$lookup_status" = "200" ] || fail "devices/lookup" "$lookup_status" "$lookup_body"
claimed="$(python - <<'PY' "$lookup_body"
import json, sys
print(json.loads(sys.argv[1]).get("claimed"))
PY
)"
[ "$claimed" = "True" ] || fail "pairing confirm did not persist claim" "$lookup_status" "$lookup_body"
echo "OK: claim persisted"

set_global="$(python - <<'PY' "$global_key" "$global_scope"
import json, sys
print(json.dumps({"key": sys.argv[1], "scope": sys.argv[2], "value": "metric"}, separators=(",", ":")))
PY
)"
resp="$(printf "%s" "$set_global" | curl -sS -X POST "$BASE/api/v1/variables/set" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" --data-binary @- -w "\n%{http_code}")"
resp_status="$(printf "%s" "$resp" | tail -n 1)"
resp_body="$(printf "%s" "$resp" | sed '$d')"
[ "$resp_status" = "200" ] || fail "set global var" "$resp_status" "$resp_body"

set_temp="$(python - <<'PY' "$temp_key" "$temp_scope" "$DEVICE_UID"
import json, sys
print(json.dumps({"key": sys.argv[1], "scope": sys.argv[2], "deviceUid": sys.argv[3], "value": 1.5}, separators=(",", ":")))
PY
)"
resp="$(printf "%s" "$set_temp" | curl -sS -X POST "$BASE/api/v1/variables/set" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" --data-binary @- -w "\n%{http_code}")"
resp_status="$(printf "%s" "$resp" | tail -n 1)"
resp_body="$(printf "%s" "$resp" | sed '$d')"
[ "$resp_status" = "200" ] || fail "set device temp var" "$resp_status" "$resp_body"

set_label="$(python - <<'PY' "$label_key" "$label_scope" "$DEVICE_UID"
import json, sys
print(json.dumps({"key": sys.argv[1], "scope": sys.argv[2], "deviceUid": sys.argv[3], "value": "kitchen-1"}, separators=(",", ":")))
PY
)"
resp="$(printf "%s" "$set_label" | curl -sS -X POST "$BASE/api/v1/variables/set" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" --data-binary @- -w "\n%{http_code}")"
resp_status="$(printf "%s" "$resp" | tail -n 1)"
resp_body="$(printf "%s" "$resp" | sed '$d')"
[ "$resp_status" = "200" ] || fail "set device label" "$resp_status" "$resp_body"
echo "OK: vars set"

snapshot="$(curl -sS -X GET "$BASE/api/v1/variables/snapshot?deviceUid=$DEVICE_UID" -H "X-Device-Token: $device_token" -w "\n%{http_code}")"
snap_status="$(printf "%s" "$snapshot" | tail -n 1)"
snap_body="$(printf "%s" "$snapshot" | sed '$d')"
[ "$snap_status" = "200" ] || fail "variables/snapshot" "$snap_status" "$snap_body"
schema="$(python - <<'PY' "$snap_body"
import json, sys
print(json.loads(sys.argv[1]).get("schema"))
PY
)"
effective_rev="$(python - <<'PY' "$snap_body"
import json, sys
print(json.loads(sys.argv[1]).get("effective_rev"))
PY
)"
server_time_ms="$(python - <<'PY' "$snap_body"
import json, sys
print(json.loads(sys.argv[1]).get("server_time_ms"))
PY
)"
[ "$schema" = "vars.snapshot.v3" ] || fail "snapshot schema mismatch" "$snap_status" "$snap_body"
[ -n "$effective_rev" ] || fail "snapshot missing effective_rev" "$snap_status" "$snap_body"
[ -n "$server_time_ms" ] || fail "snapshot missing server_time_ms" "$snap_status" "$snap_body"
echo "OK: snapshot rev=$effective_rev"

ack_body="$(python - <<'PY' "$snap_body" "$DEVICE_UID"
import json, sys
payload = json.loads(sys.argv[1])
device_uid = sys.argv[2]
results = []
for item in payload.get("vars", []):
    key = item.get("key")
    if key:
        results.append({"key": key, "status": "OK"})
print(json.dumps({"deviceUid": device_uid, "effectiveRev": payload.get("effective_rev"), "results": results}, separators=(",", ":")))
PY
)"
ack="$(printf "%s" "$ack_body" | curl -sS -X POST "$BASE/api/v1/variables/ack" -H "X-Device-Token: $device_token" -H "Content-Type: application/json" --data-binary @- -w "\n%{http_code}")"
ack_status="$(printf "%s" "$ack" | tail -n 1)"
ack_body_out="$(printf "%s" "$ack" | sed '$d')"
[ "$ack_status" = "200" ] || fail "variables/ack" "$ack_status" "$ack_body_out"
failed="$(python - <<'PY' "$ack_body_out"
import json, sys
print(json.loads(sys.argv[1]).get("failed", 0))
PY
)"
[ "$failed" = "0" ] || fail "ack returned failed results" "$ack_status" "$ack_body_out"
echo "OK: ack applied"

ack2="$(printf "%s" "$ack_body" | curl -sS -X POST "$BASE/api/v1/variables/ack" -H "X-Device-Token: $device_token" -H "Content-Type: application/json" --data-binary @- -w "\n%{http_code}")"
ack2_status="$(printf "%s" "$ack2" | tail -n 1)"
ack2_body="$(printf "%s" "$ack2" | sed '$d')"
[ "$ack2_status" = "200" ] || fail "variables/ack idempotent" "$ack2_status" "$ack2_body"
stale="$(python - <<'PY' "$ack2_body"
import json, sys
print(json.loads(sys.argv[1]).get("stale", 0))
PY
)"
applied="$(python - <<'PY' "$ack2_body"
import json, sys
print(json.loads(sys.argv[1]).get("applied", 0))
PY
)"
if [ "$stale" -lt 1 ] && [ "$applied" -gt 0 ]; then
  fail "ack idempotency not detected" "$ack2_status" "$ack2_body"
fi
echo "OK: ack idempotent"

echo "Running simulator..."
python -m app.simulator --base "$BASE" --device-uid "$DEVICE_UID" --device-token "$device_token" --user-token "$TOKEN" --vars-effective --vars-ack --vars-poll-seconds 5 --seconds "$SECONDS"
echo "OK"
