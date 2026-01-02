# ENV

This document lists environment variables used by HUBEX core, smokes, and dev tooling.
Values shown are examples only. Do not commit real secrets.

## Local installs
```
python -m pip install -U -r requirements.txt -r requirements-dev.txt
```

## Core runtime
- `HUBEX_ENV` (default: `dev`) — runtime environment label.
- `HUBEX_HOST` (default: `127.0.0.1`) — bind host.
- `HUBEX_PORT` (default: `8000`) — bind port.
- `HUBEX_DATABASE_URL` / `DATABASE_URL` (default: empty) — SQLAlchemy DB URL.
- `HUBEX_REDIS_URL` (default: empty) — Redis URL (if used).
- `HUBEX_JWT_SECRET` (default: `change-me-now`) — JWT signing secret.
- `HUBEX_JWT_ISSUER` (default: `hubex`) — JWT issuer.
- `HUBEX_JWT_EXP_MINUTES` (default: `1440`) — access token TTL in minutes.

## Capability enforcement
- `HUBEX_CAPS_ENFORCE` (default: `0`) — enable deny-by-default capability enforcement when `1`.

## Rate limiting (opt-in)
- `HUBEX_RL_ENABLED` (default: `0`) — enable rate limiting when `1`.
- `HUBEX_RL_PER_MIN` (default: `60`) — requests per minute per key.

## Dev tools gate
- `HUBEX_DEV_TOOLS` (default: `0`) — enable dev-only endpoints/paths when `1`.

## Simulator
- `HUBEX_SIM_SECONDS` (default: `30`) — runtime duration in seconds for simulator scripts.
- `HUBEX_FAIL_RATE_TIMEOUT` (default: `0`) — failure injection rate (timeouts).
- `HUBEX_FAIL_RATE_TYPE` (default: `0`) — failure injection rate (type mismatch).
- `HUBEX_FAIL_BUSY_RATE` (default: `0`) — failure injection rate (busy retryable).
- `HUBEX_FAIL_TIMEOUT_RATE` (default: `0`) — alias for timeout rate (if present).
- `HUBEX_FAIL_TYPE_MISMATCH_RATE` (default: `0`) — alias for type mismatch rate (if present).

## Smoke / scripts
- `HUBEX_BASE` (default: `http://127.0.0.1:8000`) — base URL for scripts.
- `HUBEX_TOKEN` — user JWT for authenticated scripts.
- `HUBEX_EMAIL` (default: `dev@example.com`) — login email for scripts.
- `HUBEX_PASSWORD` (default: `devdevdev`) — login password for scripts.
- `HUBEX_DEVICE_UID` — target device UID for device-scoped scripts.
- `HUBEX_DEVICE_ID` — target device ID for task scripts.
- `HUBEX_DEVICE_TOKEN` — device token for device-auth scripts.
- `HUBEX_CONTEXT_KEY` (default: `default`) — task context key.
- `HUBEX_DEVICE_COUNT` (default: `3`) — number of devices to seed.
- `HUBEX_DEVICE_PREFIX` (default: `dev-seed`) — UID prefix for seeded devices.
- `HUBEX_CLAIM_ONE` (default: `0`) — claim one seeded device when `1`.
- `HUBEX_TELEMETRY_COUNT` (default: `5`) — telemetry count in push script.
- `HUBEX_TELEMETRY_INTERVAL_MS` (default: `1000`) — telemetry interval in ms.
- `HUBEX_VAR_KEY` — variable key.
- `HUBEX_VAR_SCOPE` — variable scope.
- `HUBEX_VAR_VALUE` — variable value (string).
- `HUBEX_VAR_VALUE_JSON` — variable value (JSON).
- `HUBEX_VAR_EXPECTED_VERSION` — optimistic concurrency value.
- `HUBEX_VAR_FORCE` — force flag for variable set.
- `HUBEX_VAR_LIMIT` (default: `50`) — audit limit.
- `HUBEX_INCLUDE_SECRETS` (default: `0`) — include secrets on effective vars.
- `HUBEX_JTI` — explicit token jti (revoke script).
- `HUBEX_REVOKE_REASON` — revoke reason.
- `HUBEX_KNOWN_UID` (default: `debug-test-1`) — known UID for lookup smoke.

## Local quick start
PowerShell:
```
$env:HUBEX_BASE="http://127.0.0.1:8000"
$env:HUBEX_TOKEN="<JWT>"
$env:HUBEX_CAPS_ENFORCE="0"
$env:HUBEX_RL_ENABLED="0"
```

bash:
```
export HUBEX_BASE="http://127.0.0.1:8000"
export HUBEX_TOKEN="<JWT>"
export HUBEX_CAPS_ENFORCE=0
export HUBEX_RL_ENABLED=0
```
