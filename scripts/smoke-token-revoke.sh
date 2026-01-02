#!/usr/bin/env sh
set -eu

BASE="${HUBEX_BASE:-http://127.0.0.1:8000}"
TOKEN="${HUBEX_TOKEN:-}"

if [ -z "$TOKEN" ]; then
  echo "HUBEX_TOKEN missing" >&2
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

sh "$(dirname "$0")/revoke-token.sh" >/dev/null

status2=$(curl -s -o /tmp/revoke_post.json -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  -X GET "$BASE/api/v1/users/me")
if [ "$status2" != "401" ]; then
  echo "FAIL revoked token expected 401 got $status2"
  cat /tmp/revoke_post.json
  exit 1
fi
echo "OK token revoked immediately"
