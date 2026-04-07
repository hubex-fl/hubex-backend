# Phase 9.5 — Standard-Device Connector PoC: Shelly/Tasmota via MQTT Bridge

## Goal
Create a Python MQTT bridge that subscribes to Shelly or Tasmota MQTT topics and forwards telemetry to HUBEX. This demonstrates that HUBEX can integrate standard off-the-shelf IoT devices (not just custom hardware or REST APIs) via MQTT.

## Files to Create
1. `scripts/mqtt_bridge.py` — runnable Python script
2. `docs/MQTT_BRIDGE.md` — explanation + usage

## Script (`mqtt_bridge.py`)

### Requirements
- `paho-mqtt` (MQTT client)
- `requests` (HUBEX API)

### Arguments
- `--server` — HUBEX server URL (default: `http://localhost:8000`)
- `--email` / `--password` — HUBEX user credentials
- `--uid` — HUBEX device UID (default: `mqtt-bridge-xxxx`)
- `--mqtt-host` — MQTT broker host (default: `localhost`)
- `--mqtt-port` — MQTT broker port (default: `1883`)
- `--mqtt-user` / `--mqtt-pass` — MQTT broker credentials (optional)
- `--topic` — MQTT topic to subscribe to (default: `shellies/#`)
- `--device-type` — hint for field extraction: `shelly`, `tasmota`, or `auto` (default: `auto`)
- `--interval` — min seconds between HUBEX telemetry pushes per device (default: `10`)
- `--auto-pair` — auto-pair the bridge device with HUBEX
- `--token` — HUBEX device token (skip pairing if already paired)

### Behavior
1. Login to HUBEX (JWT) + pair bridge device (if `--auto-pair`)
2. Connect to MQTT broker, subscribe to `--topic`
3. On each MQTT message:
   - Parse topic to extract device ID (e.g. `shellies/shelly1-abc123/relay/0/power` → `shelly1-abc123`)
   - Parse JSON payload and extract numeric fields (same logic as `api_device.py`)
   - Rate-limit: only push if ≥ `--interval` seconds since last push for that device
   - `POST /api/v1/telemetry` with `{"payload": {...fields...}}` and bridge device token
   - Tag fields with device prefix: `{device_id}.{field}` (e.g. `shelly1-abc123.power`)
4. Every 60s: `POST /edge/heartbeat`
5. Ctrl+C → graceful disconnect from MQTT + exit

### Topic/Payload Patterns to Support

**Shelly (default format):**
- `shellies/{device-id}/relay/0/power` → payload: `"12.5"` (plain float string)
- `shellies/{device-id}/relay/0/energy` → payload: `"1024"` (plain int string)
- `shellies/{device-id}/temperature` → payload: `"23.4"`
- `shellies/{device-id}/status` → payload: JSON `{"temperature": 23.4, "overtemperature": false, ...}`

**Tasmota (tele/ prefix):**
- `tele/{device-id}/SENSOR` → payload: JSON `{"SHT3X-0x44": {"Temperature": 22.1, "Humidity": 55.0}}`
- `tele/{device-id}/STATE` → payload: JSON `{"Time": "...", "Uptime": "...", "Wifi": {"RSSI": -65}}`

**Auto mode:** try JSON parse first, fall back to plain numeric string.

### Field Extraction
- JSON payload: extract all numeric leaf values (recursive, same as `api_device.py`)
- Plain string payload: if parseable as float, use topic's last segment as field name
- Prefix all fields with `{device_id}.` to namespace multi-device data

## After Completion
1. Update ROADMAP.md: Step 5 done → Milestone 9 COMPLETE
2. Write report to REPORTS.md
3. Generate PROMPT_PHASE_10_1.md (CI/CD: GitHub Actions — test, build, lint)
