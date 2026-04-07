# Phase 9.4 — API-Device Demo: External REST API as Virtual Device

## Goal
Create a Python demo showing how to connect an external REST API (e.g. a weather API, stock API, or any HTTP service) as a virtual HUBEX device. The virtual device:
1. Pairs with HUBEX like a real device
2. Periodically fetches data from an external API
3. Pushes the data as telemetry to HUBEX
4. Can receive variable overrides (e.g. "poll_interval_s") from HUBEX edge config

This demonstrates that HUBEX is not just for hardware — any data source can be a "device".

## Files to Create
1. `scripts/api_device.py` — runnable Python script
2. `docs/API_DEVICE.md` — explanation + usage

## Script (`api_device.py`)
Arguments: `--server`, `--email`, `--password`, `--uid`, `--source-url`, `--interval`, `--auto-pair`

Behavior:
1. Login (JWT) + auto-pair (hello + user-claim + confirm, all from same script with `--auto-pair`)
2. Loop every `--interval` seconds:
   - `GET /edge/config` → read `poll_interval_s` variable (overrides --interval if set)
   - `GET --source-url` → fetch JSON from external API
   - Extract numeric fields from the response (auto-detected or via `--fields key1,key2`)
   - `POST /api/v1/telemetry` with extracted fields as payload
   - `POST /edge/heartbeat`
3. Ctrl+C → graceful exit

Default `--source-url`: `https://api.open-meteo.com/v1/forecast?latitude=48.1&longitude=11.6&current=temperature_2m,wind_speed_10m`
(Open-Meteo public API — no key required, returns Munich weather)

## After Completion
1. Update ROADMAP.md: Step 4 done, Step 5 ← AKTUELL
2. Generate PROMPT_PHASE_9_5.md
3. Write report to REPORTS.md
