#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"
DEVICE_UID="sim-var-1"

if [ -z "$TOKEN" ]; then
  echo "FAIL: HUBEX_TOKEN missing"
  exit 1
fi

fail() {
  echo "FAIL: $1"
  if [ -n "${2:-}" ]; then
    echo "Status: $2"
    echo "Body: $3"
  fi
  exit 1
}

api() {
  method="$1"
  url="$2"
  body="$3"
  if [ -n "$body" ]; then
    resp=$(printf "%s" "$body" | curl -sS -X "$method" "$url" \
      -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
      --data-binary '@-' -w "\n%{http_code}")
  else
    resp=$(curl -sS -X "$method" "$url" -H "Authorization: Bearer $TOKEN" -w "\n%{http_code}")
  fi
  status=$(printf "%s" "$resp" | tail -n 1)
  body=$(printf "%s" "$resp" | sed '$d')
  printf "%s\n%s" "$status" "$body"
}

echo "Provision device..."
hello_body="{\"device_uid\":\"$DEVICE_UID\",\"firmware_version\":\"sim-1.0\",\"capabilities\":{\"vars\":true}}"
resp=$(printf "%s" "$hello_body" | curl -sS -X POST "$BASE/api/v1/devices/hello" \
  -H "Content-Type: application/json" --data-binary '@-' -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
body=$(printf "%s" "$resp" | sed '$d')
[ "$status" = "200" ] || fail "devices/hello" "$status" "$body"

echo "Ensure definitions..."
def1="{\"key\":\"system.units\",\"scope\":\"global\",\"valueType\":\"string\",\"defaultValue\":\"metric\"}"
resp=$(api "POST" "$BASE/api/v1/variables/definitions" "$def1")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
if [ "$status" != "200" ]; then
  code=$(printf "%s" "$body" | python -c "import sys, json; obj=json.load(sys.stdin); print(obj.get('detail',{}).get('code',''))" || true)
  [ "$status" = "409" ] && [ "$code" = "VAR_DEF_EXISTS" ] || fail "create definition system.units" "$status" "$body"
fi

def2="{\"key\":\"device.temp_offset\",\"scope\":\"device\",\"valueType\":\"float\",\"defaultValue\":0.0}"
resp=$(api "POST" "$BASE/api/v1/variables/definitions" "$def2")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
if [ "$status" != "200" ]; then
  code=$(printf "%s" "$body" | python -c "import sys, json; obj=json.load(sys.stdin); print(obj.get('detail',{}).get('code',''))" || true)
  [ "$status" = "409" ] && [ "$code" = "VAR_DEF_EXISTS" ] || fail "create definition device.temp_offset" "$status" "$body"
fi

echo "Get device variables..."
resp=$(api "GET" "$BASE/api/v1/variables/device/$DEVICE_UID" "")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
[ "$status" = "200" ] || fail "variables device" "$status" "$body"

echo "Set temp_offset=1.5..."
set1="{\"key\":\"device.temp_offset\",\"scope\":\"device\",\"deviceUid\":\"$DEVICE_UID\",\"value\":1.5}"
resp=$(api "PUT" "$BASE/api/v1/variables/value" "$set1")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
[ "$status" = "200" ] || fail "set temp_offset" "$status" "$body"
version=$(printf "%s" "$body" | python -c "import sys, json; obj=json.load(sys.stdin); print(obj.get('version',''))")
[ -n "$version" ] || fail "missing version" "$status" "$body"

echo "Update temp_offset=2.5 with expectedVersion..."
set2="{\"key\":\"device.temp_offset\",\"scope\":\"device\",\"deviceUid\":\"$DEVICE_UID\",\"value\":2.5,\"expectedVersion\":$version}"
resp=$(api "PUT" "$BASE/api/v1/variables/value" "$set2")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
[ "$status" = "200" ] || fail "update temp_offset" "$status" "$body"
version2=$(printf "%s" "$body" | python -c "import sys, json; obj=json.load(sys.stdin); print(obj.get('version',''))")

echo "Update with stale expectedVersion (expect 409)..."
set3="{\"key\":\"device.temp_offset\",\"scope\":\"device\",\"deviceUid\":\"$DEVICE_UID\",\"value\":3.0,\"expectedVersion\":$version}"
resp=$(api "PUT" "$BASE/api/v1/variables/value" "$set3")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
if [ "$status" != "409" ]; then
  fail "stale version should 409" "$status" "$body"
fi
code=$(printf "%s" "$body" | python -c "import sys, json; obj=json.load(sys.stdin); print(obj.get('detail',{}).get('code',''))" || true)
[ "$code" = "VAR_VERSION_CONFLICT" ] || fail "stale version code" "$status" "$body"

echo "Audit..."
resp=$(api "GET" "$BASE/api/v1/variables/audit?key=device.temp_offset&scope=device&deviceUid=$DEVICE_UID" "")
status=$(printf "%s" "$resp" | head -n 1)
body=$(printf "%s" "$resp" | tail -n +2)
[ "$status" = "200" ] || fail "audit" "$status" "$body"

echo "OK"
