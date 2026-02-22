# Vertical Demo v1 (Minimal)

This runbook executes the SSOT v2 Vertical Demo v1 chain on a fresh setup without manual DB edits.

## Prerequisites
- Backend running (`HUBEX_BASE_URL`, default `http://127.0.0.1:8000`).
- DB reachable via `DATABASE_URL` (backend config).
- Python venv present at `.venv`.
- Worker v1 service available (already in repo).

## What the demo does
1) Emit `signal.demo_v1` (events.v1) with a correlation ID.
2) Bridge the signal to an execution run (`demo.v1`) via the demo bridge.
3) Run the worker once (claim/finalize).
4) Set a device variable and simulate device snapshot + ack.
5) Emit trace events to `tenant.system` with the same correlation ID.

## Run
```powershell
# Optional overrides
$env:HUBEX_BASE_URL = "http://127.0.0.1:8000"
$env:DEMO_DEVICE_UID = "demo-device-1"
$env:DEMO_DEFINITION_KEY = "demo.v1"
$env:WORKER_ID = "demo-worker-1"

# Execute
.\scripts\demo-vertical-v1.ps1
```

## Outputs
- Prints `CORRELATION_ID` and a Trace Hub hint.
- Use the UI Trace Hub ? Events Viewer:
  - Stream: `tenant.system`
  - Trace ID filter: the printed correlation ID

## Notes
- The script issues a demo access token with capabilities for the run (not for production use).
- If the device was already claimed, set `HUBEX_DEVICE_TOKEN` to skip pairing.
