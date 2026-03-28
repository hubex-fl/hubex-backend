# HUBEX End-to-End Integration Demo

This guide walks through the full HUBEX device pipeline:
**ESP32 → Telemetry → Alert → Webhook → n8n**

## Prerequisites

- HUBEX backend running (`uvicorn app.main:app --reload`)
- A user account (default: `codex+20251219002029@example.com` / `Test1234!`)
- `requests` Python package: `pip install requests`

---

## Option A — Python Demo Script (recommended)

```bash
# Run against local dev server
python scripts/demo_e2e.py

# Run against remote server
python scripts/demo_e2e.py --server https://your-hubex.example.com

# Dry-run (print steps, no API calls)
python scripts/demo_e2e.py --dry-run

# Keep demo resources after run (don't cleanup)
python scripts/demo_e2e.py --keep
```

The script runs all 8 steps automatically and prints a colored summary.

---

## Option B — Manual curl walkthrough

### Step 1: Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"codex+20251219002029@example.com","password":"Test1234!"}' \
  | jq -r '.access_token'
```

Save the token: `export JWT=<token>`

### Step 2: Device Pairing

**2a. Device announces itself** (no auth required — simulates ESP32 boot):
```bash
curl -X POST http://localhost:8000/api/v1/devices/pairing/hello \
  -H "Content-Type: application/json" \
  -d '{"device_uid":"esp32-demo-001","firmware_version":"1.0.0"}'
```
Response: `{"claimed":false,"pairing_active":true,"pairing_code":"ABCD1234",...}`

Save the code: `export PAIRING_CODE=ABCD1234`

**2b. User claims the device** (JWT required — simulates dashboard click):
```bash
curl -X POST http://localhost:8000/api/v1/devices/pairing/claim \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d "{\"pairing_code\":\"$PAIRING_CODE\",\"device_uid\":\"esp32-demo-001\"}"
```

**2c. Device confirms and gets its permanent token**:
```bash
curl -X POST http://localhost:8000/api/v1/devices/pairing/confirm \
  -H "Content-Type: application/json" \
  -d "{\"device_uid\":\"esp32-demo-001\",\"pairing_code\":\"$PAIRING_CODE\"}"
```
Response: `{"device_id":5,"device_token":"<token>","device_uid":"esp32-demo-001",...}`

Save: `export DEVICE_TOKEN=<token>` and `export DEVICE_ID=5`

### Step 3: Push Telemetry

```bash
curl -X POST http://localhost:8000/api/v1/telemetry \
  -H "X-Device-Token: $DEVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"payload":{"temperature":30.5,"humidity":65,"rssi":-55}}'
```

### Step 4: Heartbeat

```bash
curl -X POST http://localhost:8000/edge/heartbeat \
  -H "X-Device-Token: $DEVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"firmware_version":"1.0.0"}'
```

### Step 5: Create Alert Rule

```bash
curl -X POST http://localhost:8000/api/v1/alerts/rules \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Demo — Device Offline",
    "condition_type": "device_offline",
    "condition_config": {"threshold_seconds": 120},
    "severity": "warning",
    "enabled": true
  }'
```

### Step 6: Create Webhook (for n8n)

```bash
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-n8n.example.com/webhook/hubex",
    "secret": "change-me",
    "event_filter": ["device.claimed","device.telemetry","alert.fired"]
  }'
```

### Step 7: Check Events

```bash
curl "http://localhost:8000/api/v1/events?stream=device&limit=10" \
  -H "Authorization: Bearer $JWT" | jq '.items[].event_type'
```

### Step 8: Get Edge Config (device perspective)

```bash
curl http://localhost:8000/edge/config \
  -H "X-Device-Token: $DEVICE_TOKEN" | jq
```

---

## Connecting n8n

1. In n8n, create a new workflow
2. Add a **Webhook** trigger node → copy the webhook URL
3. Update the webhook URL in `scripts/demo_e2e.py` (or via the HUBEX dashboard)
4. Run the demo — every `device.claimed` and `device.telemetry` event will trigger the workflow

### Example n8n workflow ideas:
- `device.telemetry` → **IF** temperature > 30 → **Send Email** alert
- `alert.fired` → **Slack** message to `#iot-alerts`
- `device.claimed` → **Google Sheets** → log new device registration

---

## ESP32 Arduino SDK

For real hardware, see `sdk/esp32/HubexClient.h` and `sdk/esp32/examples/basic_device/`.

The SDK handles all the above steps automatically — just call:
```cpp
hubex.begin("1.0.0");
hubex.ensurePaired();   // blocks until user claims
// Then in loop():
hubex.heartbeat();
hubex.pushTelemetry({{"temperature", 30.5f}, {"humidity", 65.0f}});
hubex.checkOta();
```
