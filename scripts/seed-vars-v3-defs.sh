#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  echo "FAIL: HUBEX_TOKEN missing"
  exit 1
fi

curl_json() {
  method="$1"
  url="$2"
  body="${3:-}"
  if [ -n "$body" ]; then
    resp="$(printf "%s" "$body" | curl -sS -X "$method" "$url" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" --data-binary @- -w "\n%{http_code}")"
  else
    resp="$(curl -sS -X "$method" "$url" -H "Authorization: Bearer $TOKEN" -w "\n%{http_code}")"
  fi
  status="$(printf "%s" "$resp" | tail -n 1)"
  body_out="$(printf "%s" "$resp" | sed '$d')"
  printf "%s\n%s" "$status" "$body_out"
}

defs='[
  {"key":"system.units","scope":"global","valueType":"string","defaultValue":"metric","enumValues":["metric","imperial"]},
  {"key":"device.telemetry_interval_ms","scope":"device","valueType":"int","defaultValue":5000,"unit":"ms","minValue":500,"maxValue":60000,"deviceWritable":true,"userWritable":true},
  {"key":"device.temp_offset","scope":"device","valueType":"float","defaultValue":0.0,"minValue":-5,"maxValue":5,"deviceWritable":true,"userWritable":true},
  {"key":"device.label","scope":"device","valueType":"string","defaultValue":"","deviceWritable":true,"userWritable":true}
]'

echo "$defs" | python - <<'PY'
import json, sys, os, subprocess
BASE = os.getenv("HUBEX_BASE", "http://127.0.0.1:8000")
TOKEN = os.getenv("HUBEX_TOKEN", "")
defs = json.load(sys.stdin)
for d in defs:
    body = json.dumps(d, separators=(",", ":"))
    cmd = ["curl", "-sS", "-X", "POST", f"{BASE}/api/v1/variables/defs",
           "-H", f"Authorization: Bearer {TOKEN}",
           "-H", "Content-Type: application/json",
           "--data-binary", body, "-w", "\n%{http_code}"]
    out = subprocess.check_output(cmd).decode("utf-8")
    status = int(out.splitlines()[-1])
    if status in (200, 201):
        print(f"OK: {d['key']}")
    elif status == 409:
        print(f"SKIP: {d['key']} already exists")
    else:
        print(f"FAIL: {d['key']}")
        print("Status:", status)
        print("Body:", "\n".join(out.splitlines()[:-1]))
        raise SystemExit(1)
PY

resp="$(curl -sS -X GET "$BASE/api/v1/variables/defs" -H "Authorization: Bearer $TOKEN" -w "\n%{http_code}")"
status="$(printf "%s" "$resp" | tail -n 1)"
body="$(printf "%s" "$resp" | sed '$d')"
if [ "$status" != "200" ]; then
  echo "FAIL: list defs after seed"
  echo "Status: $status"
  echo "Body: $body"
  exit 1
fi

count="$(python - <<PY
import json, sys
try:
    items = json.loads(sys.argv[1])
except Exception:
    print(0)
    raise SystemExit(0)
print(len(items))
PY
"$body")"

if [ "$count" = "0" ]; then
  echo "FAIL: /variables/defs returned empty after seed"
  echo "$body"
  exit 1
fi

python - <<'PY' "$body"
import json, sys
items = json.loads(sys.argv[1])
counts = {}
for item in items:
    counts[item.get("scope")] = counts.get(item.get("scope"), 0) + 1
summary = " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
print("Defs by scope:", summary)
PY
echo "DONE"
