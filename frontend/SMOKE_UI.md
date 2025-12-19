# UI Smoke Validation (HUBEX Frontend)

## Prereqs
- Backend running: http://localhost:8000
- Frontend running (Vite): e.g. http://localhost:5173
- Frontend API base:
  - .env: VITE_API_BASE=http://localhost:8000/api/v1
  - or run:
    - bash: VITE_API_BASE=http://localhost:8000/api/v1 npm run dev
    - PowerShell: $env:VITE_API_BASE="http://localhost:8000/api/v1"; npm run dev

## Token key
Frontend stores the user JWT in LocalStorage key: **hubex_token**

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
