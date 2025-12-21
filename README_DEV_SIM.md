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
