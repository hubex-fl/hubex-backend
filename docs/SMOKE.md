# SMOKE

This document lists supported smoke scripts and expected behavior.

## smoke-capabilities.ps1 / smoke-capabilities.sh
**Purpose:** Verify capability guard behavior in report-only vs enforce mode.

Preconditions:
- HUBEX_BASE set (default http://127.0.0.1:8000)
- HUBEX_TOKEN set for authenticated checks
- HUBEX_CAPS_ENFORCE set to 0 or 1

Example (PowerShell):
```
$env:HUBEX_BASE="http://127.0.0.1:8000"
$env:HUBEX_TOKEN="<JWT>"
$env:HUBEX_CAPS_ENFORCE="0"
.\scripts\smoke-capabilities.ps1

$env:HUBEX_CAPS_ENFORCE="1"
.\scripts\smoke-capabilities.ps1
```

Expected output:
- enforce=0: log-only mode, requests pass (no hard 403)
- enforce=1: non-whitelisted unauthenticated requests -> 401; missing caps -> 403

Failure modes:
- Missing HUBEX_TOKEN for enforce=1 checks (script warns/skips)

## smoke-token-revoke.ps1 / smoke-token-revoke.sh
**Purpose:** Verify jti revoke denylist rejects tokens immediately.

Preconditions:
- HUBEX_BASE
- HUBEX_TOKEN OR HUBEX_EMAIL/HUBEX_PASSWORD for login

Example (PowerShell):
```
$env:HUBEX_BASE="http://127.0.0.1:8000"
$env:HUBEX_TOKEN="<JWT>"
.\scripts\smoke-token-revoke.ps1
```

Expected output:
- First authenticated call 200
- After revoke: same call returns 401

Failure modes:
- Token missing jti (script will fail)
- Missing HUBEX_TOKEN and login creds

## smoke-rate-limit.ps1 / smoke-rate-limit.sh
**Purpose:** Verify opt-in rate limit returns 429 deterministically.

Preconditions:
- HUBEX_BASE
- HUBEX_TOKEN
- HUBEX_RL_ENABLED controls mode

Example (PowerShell):
```
$env:HUBEX_BASE="http://127.0.0.1:8000"
$env:HUBEX_TOKEN="<JWT>"

$env:HUBEX_RL_ENABLED="0"
.\scripts\smoke-rate-limit.ps1

$env:HUBEX_RL_ENABLED="1"
.\scripts\smoke-rate-limit.ps1
```

Expected output:
- RL off: no 429 in burst
- RL on: at least one 429 in burst

Failure modes:
- Missing HUBEX_TOKEN

## phase1 local gate runners
**Purpose:** Run Phase-1 gates locally in one command.

Preconditions:
- .venv present (auto-detected) or system Python available
- dependencies installed

PowerShell:
```
.\scripts\run-phase1-gates.ps1
```

bash:
```
./scripts/run-phase1-gates.sh
```

Expected output:
- One line per step: "OK <step>" or "FAIL <step>"
- Non-zero exit on first failure
- Prints "PY=<path>" once, using repo .venv if present
- Includes "repo hygiene" as the final step
 - Includes "api readonly catalog" as the final step
