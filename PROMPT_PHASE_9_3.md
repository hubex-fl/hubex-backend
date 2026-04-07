# Phase 9.3 — Provisioning Flow: QR-Code Pairing

## Goal
Add QR code display to the pairing flow. When a device registers (pairing_hello) and shows a pairing code, the HUBEX dashboard should also show a scannable QR code containing the pairing code. Users can scan it with a phone to confirm faster.

## Backend
Add `GET /api/v1/devices/pairing/{pairing_code}/qr` endpoint:
- Returns SVG QR code as `image/svg+xml`
- QR payload: JSON string `{"code":"XXXXXXXX","uid":"<device_uid>","server":"<base_url>"}`
- Uses `qrcode[svg]` Python package (pure-Python, no PIL needed)
- Auth: JWT required (user must be logged in to fetch QR)

## Frontend
In `frontend/src/pages/Devices.vue` pairing section:
- After `pairingStarted === true` and `pairingCode` is set, show a QR code image
- Fetch `GET /api/v1/devices/pairing/{pairingCode}/qr` → render as `<img>` with SVG data URI
- Show alongside the pairing code text, in a small box (128×128px)
- Label: "Scan to pair from mobile"

## Files to Modify/Create
1. `app/api/v1/pairing.py` — add QR endpoint
2. `requirements.txt` — add `qrcode[svg]`
3. `frontend/src/pages/Devices.vue` — add QR image in pairing section

## After Completion
1. Run `npx tsc --noEmit` + `npx vite build`
2. Update ROADMAP.md: Step 3 done, Step 4 ← AKTUELL
3. Generate PROMPT_PHASE_9_4.md
4. Write report to REPORTS.md
