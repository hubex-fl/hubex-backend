# Phase 9.2 — End-to-End Demo: Device → Telemetry → Alert → Webhook → n8n

## Context
HUBEX IoT hub — Phase 3 Integration Demo. ESP32 SDK is done (Step 1). Step 2 creates a runnable end-to-end demo that shows the full HUBEX data pipeline using a Python simulation script (since we can't run real hardware here).

## Goal
Create a Python E2E demo script that simulates an ESP32 device, triggers the full HUBEX pipeline:
1. **Pair** — device announces itself, gets claimed (automated via API)
2. **Telemetry** — device pushes sensor readings
3. **Alert** — a pre-configured alert rule fires when a threshold is crossed
4. **Webhook** — alert event triggers a webhook delivery to a test endpoint
5. **n8n** — webhook payload lands in n8n workflow (documented, not executed)

## Files to Create
1. `scripts/demo_e2e.py` — Python demo script (uses `httpx` or `requests`)
2. `docs/E2E_DEMO.md` — step-by-step walkthrough with curl commands

## Script Behavior (`demo_e2e.py`)
The script takes `--server`, `--email`, `--password` args and:
1. **Auth**: login to get JWT
2. **Pair**: POST /api/v1/devices/pairing/start → get pairing session; POST /api/v1/devices/pairing/claim → get device token
3. **Create alert rule**: POST /api/v1/alert-rules (temperature > 28 → trigger)
4. **Create webhook**: POST /api/v1/webhooks (listen for alert.fired)
5. **Push telemetry**: POST /api/v1/telemetry with temperature=30 (above threshold)
6. **Check alert events**: GET /api/v1/alert-events (should show fired event)
7. **Check webhook deliveries**: GET /api/v1/webhooks/{id}/deliveries
8. **Cleanup**: unclaim device, delete alert rule + webhook
9. Print colored summary: ✅ / ❌ per step

## Technical Constraints
- Python 3.11+, use `httpx` (sync) or `requests`
- Colorized output via ANSI codes (no extra deps)
- `--dry-run` flag: print all steps without making API calls
- Handle errors gracefully: if a step fails, skip dependents and continue to cleanup

## Files to Modify
None — new files only.

## After Completion
1. Update ROADMAP.md: Step 2 done, Step 3 ← AKTUELL
2. Generate PROMPT_PHASE_9_3.md
3. Write report to REPORTS.md
