#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
EMAIL="${HUBEX_EMAIL:-dev@example.com}"
PASSWORD="${HUBEX_PASSWORD:-devdevdev}"

login_resp=$(curl -s -X POST "$BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(python - <<'PY'
import json, sys, base64
resp = sys.stdin.read()
try:
    data = json.loads(resp)
except Exception:
    print("")
    sys.exit(0)
token = data.get("access_token", "")
if not token:
    print("")
    sys.exit(0)
parts = token.split(".")
if len(parts) < 2:
    print("")
    sys.exit(0)
pad = "=" * (-len(parts[1]) % 4)
payload = json.loads(base64.urlsafe_b64decode(parts[1] + pad).decode("utf-8"))
if not payload.get("jti"):
    print("")
    sys.exit(0)
print(token)
PY
<<EOF
$login_resp
EOF
)

if [ -z "$TOKEN" ]; then
  echo "LOGIN FAILED or missing jti (check HUBEX_EMAIL/HUBEX_PASSWORD)" >&2
  echo "$login_resp" >&2
  exit 1
fi

status1=$(curl -s -o /tmp/revoke_pre.json -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  -X GET "$BASE/api/v1/users/me")
if [ "$status1" != "200" ]; then
  echo "FAIL pre-check expected 200 got $status1"
  cat /tmp/revoke_pre.json
  exit 1
fi
echo "OK pre-check authenticated"

HUBEX_TOKEN="$TOKEN" sh "$(dirname "$0")/revoke-token.sh" >/dev/null

status2=$(curl -s -o /tmp/revoke_post.json -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  -X GET "$BASE/api/v1/users/me")
if [ "$status2" != "401" ]; then
  echo "FAIL revoked token expected 401 got $status2"
  cat /tmp/revoke_post.json
  exit 1
fi
echo "OK token revoked immediately"
