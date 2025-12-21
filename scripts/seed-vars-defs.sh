#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  echo "FAIL: HUBEX_TOKEN missing"
  exit 1
fi

post_def() {
  key="$1"
  body="$2"
  resp=$(printf "%s" "$body" | curl -sS -X POST "$BASE/api/v1/variables/defs" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    --data-binary '@-' -w "\n%{http_code}")
  status=$(printf "%s" "$resp" | tail -n 1)
  if [ "$status" = "200" ] || [ "$status" = "201" ]; then
    echo "OK: $key"
    return
  fi
  if [ "$status" = "409" ]; then
    echo "SKIP: $key already exists"
    return
  fi
  echo "FAIL: $key"
  echo "Status: $status"
  echo "Body: $(printf "%s" "$resp" | sed '$d')"
  exit 1
}

post_def "system.units" '{"key":"system.units","scope":"global","valueType":"string","defaultValue":"metric","enumValues":["metric","imperial"]}'
post_def "device.telemetry_interval_ms" '{"key":"device.telemetry_interval_ms","scope":"device","valueType":"int","defaultValue":5000,"unit":"ms","minValue":500,"maxValue":60000,"deviceWritable":true,"userWritable":true}'
post_def "device.temp_offset" '{"key":"device.temp_offset","scope":"device","valueType":"float","defaultValue":0.0,"minValue":-5,"maxValue":5,"deviceWritable":true,"userWritable":true}'
post_def "device.label" '{"key":"device.label","scope":"device","valueType":"string","defaultValue":"","deviceWritable":true,"userWritable":true}'

resp=$(curl -sS -X GET "$BASE/api/v1/variables/defs" -H "Authorization: Bearer $TOKEN" -w "\n%{http_code}")
status=$(printf "%s" "$resp" | tail -n 1)
body=$(printf "%s" "$resp" | sed '$d')
if [ "$status" != "200" ]; then
  echo "FAIL: list defs after seed"
  echo "Status: $status"
  echo "Body: $body"
  exit 1
fi
if [ "$body" = "[]" ] || [ -z "$body" ]; then
  echo "FAIL: /variables/defs returned empty after seed"
  echo "$body"
  exit 1
fi
summary=$(printf "%s" "$body" | python -c "import sys,json;from collections import Counter;data=json.load(sys.stdin);c=Counter(d.get('scope') for d in data);print(' '.join(f\"{k}={v}\" for k,v in sorted(c.items())))")
echo "Defs by scope: $summary"
echo "DONE"
