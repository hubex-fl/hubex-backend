# UI Smoke Validation (HUBEX Frontend)

Prereqs
- Backend running at http://localhost:8000
- Frontend API base set: VITE_API_BASE=http://localhost:8000/api/v1

Run
1) cd frontend
2) npm install
3) npm run dev
If you don't use .env, you can also run:
- bash: VITE_API_BASE=http://localhost:8000/api/v1 npm run dev
- PowerShell: $env:VITE_API_BASE="http://localhost:8000/api/v1"; npm run dev

Checks

Login happy path
1) Go to /login
2) Enter valid credentials
3) Expect redirect to /devices

Login failure
1) Use a wrong password
2) Expect a visible error message (API detail if available)

Token expiry behavior
1) If backend supports short-lived tokens, set it:
   - PowerShell: $env:ACCESS_TOKEN_EXPIRE_SECONDS=2
2) Login
3) Wait for expiry
4) Go to /devices
5) Expect redirect to /login with no loop

Devices list
1) /devices loads
2) Expect list (can be empty)
3) Click a device -> goes to /devices/:id

Device detail
1) Detail page renders fields
2) JSON blobs render safely in a pre block

Pairing confirm
1) Go to /pairing
2) Enter device_uid + pairing_code
3) Expect success panel with device_id + device_token
4) Token is copyable

401 behavior
1) Clear token in devtools (or set invalid token string)
2) Reload /devices
3) Expect redirect to /login

Pass criteria
- No blank screens
- No uncaught promise errors in console
- 401 always logs out and redirects cleanly
