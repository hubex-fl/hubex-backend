# Hubex Dev Simulation

## Prereqs
- Backend running at `http://127.0.0.1:8000`
- Python venv activated for scripts that call `python -m app.simulator`

## Quick start (PowerShell)
```powershell
# 1) Seed user
.\scripts\dev\seed-user.ps1
# set $env:HUBEX_TOKEN from output

# 2) Provision devices
.\scripts\dev\seed-devices.ps1

# 3) Pair and run simulator (one command)
.\scripts\e2e-dev.ps1
```

## Quick start (bash)
```bash
./scripts/dev/seed-user.sh
# export HUBEX_TOKEN from output
./scripts/dev/seed-devices.sh
./scripts/e2e-dev.sh
```

## Device simulator
```bash
python -m app.simulator --base http://127.0.0.1:8000 --device-uid sim-123 --device-token <token> --seconds 30
```

## Effective variables
```powershell
$env:HUBEX_DEVICE_UID="sim-123"
.\scripts\vars-effective.ps1

.\scripts\smoke-effective-vars.ps1
```

```bash
export HUBEX_DEVICE_UID="sim-123"
./scripts/vars-effective.sh

./scripts/smoke-effective-vars.sh
```

## Variables v2 quickstart
```powershell
# Define v2 registry keys (requires HUBEX_DEV_TOOLS=1)
$env:HUBEX_DEV_TOOLS="1"
.\scripts\seed-vars-defs.ps1

# Set and verify v2 values (requires HUBEX_TOKEN)
$env:HUBEX_VAR_KEY="device.temp_offset"
$env:HUBEX_VAR_SCOPE="device"
$env:HUBEX_VAR_VALUE="1.5"
$env:HUBEX_DEVICE_UID="sim-123"
.\scripts\vars-set.ps1

# Full v2 smoke (provision + pair + set + effective + simulator)
.\scripts\smoke-vars-v2.ps1
```

```bash
export HUBEX_DEV_TOOLS=1
./scripts/seed-vars-defs.sh

export HUBEX_VAR_KEY=device.temp_offset
export HUBEX_VAR_SCOPE=device
export HUBEX_VAR_VALUE=1.5
export HUBEX_DEVICE_UID=sim-123
./scripts/vars-set.sh

./scripts/smoke-vars-v2.sh
```

## Troubleshooting
- **401 Unauthorized**: token missing/expired. Re-run `seed-user` and export the token.
- **404 DEVICE_UNKNOWN_UID**: device was never provisioned; run `devices/hello` (seed-devices).
- **409 DEVICE_ALREADY_CLAIMED**: device already paired; use a new UID or reset the device.
- **409 PAIRING_ALREADY_ACTIVE**: pairing window already active; wait for expiry or reuse the same code.

## Env vars
- `HUBEX_BASE` (default `http://127.0.0.1:8000`)
- `HUBEX_EMAIL`, `HUBEX_PASSWORD`
- `HUBEX_TOKEN`, `HUBEX_DEVICE_TOKEN`
- `HUBEX_DEVICE_COUNT`, `HUBEX_DEVICE_PREFIX`
- `HUBEX_SIM_SECONDS`
