#!/usr/bin/env sh
set -eu

TOKEN="${HUBEX_TOKEN:-}"
JTI="${HUBEX_JTI:-}"
REASON="${HUBEX_REVOKE_REASON:-}"

if [ -z "$TOKEN" ] && [ -z "$JTI" ]; then
  echo "Missing token or jti. Set HUBEX_TOKEN or HUBEX_JTI." >&2
  exit 1
fi

args=""
if [ -n "$TOKEN" ]; then
  args="$args --token $TOKEN"
fi
if [ -n "$JTI" ]; then
  args="$args --jti $JTI"
fi
if [ -n "$REASON" ]; then
  args="$args --reason $REASON"
fi

python -m app.scripts.revoke_token $args
