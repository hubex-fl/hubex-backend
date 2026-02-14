# UI Smoke Validation (HUBEX Frontend)

## Prereqs
- Backend running: http://localhost:8000
- Frontend running (Vite): e.g. http://localhost:5173
- Frontend API proxy target:
  - .env: VITE_API_TARGET=http://127.0.0.1:8000
  - or run:
    - bash: VITE_API_TARGET=http://127.0.0.1:8000 npm run dev
    - PowerShell: $env:VITE_API_TARGET="http://127.0.0.1:8000"; npm run dev
- Dev server bind:
  - default: VITE_DEV_HOST=0.0.0.0, VITE_DEV_PORT=5173
  - local-only: set VITE_DEV_HOST=127.0.0.1

## Token key
Frontend stores the user JWT in LocalStorage key: **hubex_access_token**

## Checks

### 1) Login happy path
- Go to /login
- Enter valid credentials
- Expect redirect to /devices

### 2) Login failure
- Use wrong password
- Expect a visible error message (API detail if available)

### 3) Devices list
- /devices loads
- Expect list (can be empty)
- Click a device -> /devices/:id

### 4) Device detail + telemetry (owner)
- Open /devices/:id
- Expect telemetry recent loads using **user Bearer token** (not X-Device-Token)
- Endpoint: GET /api/v1/devices/{device_id}/telemetry/recent?limit=5

### 5) 401 behavior
- Delete localStorage key hubex_token
- Reload /devices
- Expect redirect to /login (no loop)

## Pass criteria
- No blank screens
- No uncaught promise errors in console
- 401 always logs out and redirects cleanly
