# Integration Guide

HUBEX is designed as a universal device hub. This guide covers the main integration paths: Python agents, n8n workflows, webhooks, MQTT bridges, and automation rules.

## 1. Python Agent SDK

Use `scripts/api_device.py` as a reference for building virtual devices that poll external APIs:

```bash
# Munich weather (Open-Meteo, no API key needed)
python scripts/api_device.py --auto-pair

# Custom API source
python scripts/api_device.py \
  --source-url https://api.example.com/data \
  --fields temperature,pressure \
  --uid my-virtual-sensor \
  --auto-pair
```

### Building a Custom Agent

The key steps to create a Python-based virtual device:

```python
import requests

BASE = "http://localhost:8000"

# 1. Login
token = requests.post(f"{BASE}/api/v1/auth/login", json={
    "email": "user@example.com", "password": "pass"
}).json()["access_token"]

# 2. Auto-pair device
requests.post(f"{BASE}/api/v1/pairing/hello", json={
    "uid": "my-agent", "fw_version": "1.0"
})
requests.post(f"{BASE}/api/v1/pairing/claim", json={
    "uid": "my-agent", "label": "My Agent"
}, headers={"Authorization": f"Bearer {token}"})
device_token = requests.post(f"{BASE}/api/v1/pairing/confirm", json={
    "uid": "my-agent"
}).json()["device_token"]

# 3. Send telemetry in a loop
requests.post(f"{BASE}/api/v1/telemetry", json={
    "device_uid": "my-agent",
    "event_type": "metrics",
    "payload": {"cpu_usage": 45.2, "memory_pct": 72.1}
}, headers={"X-Device-Token": device_token})
```

## 2. n8n Integration

### Custom n8n Node

HUBEX ships a community node package at `n8n-nodes-hubex/`. Install it in your n8n instance:

```bash
cd n8n-nodes-hubex && npm run build
# Copy dist/ to your n8n custom nodes directory
```

The node provides two components:

**HUBEX Node** -- CRUD operations:
- Device: list, get
- Telemetry: list, latest
- Alert: list rules, list events, acknowledge
- Variable: list, set, delete
- Variable Stream: get history, get snapshot, get definitions, bulk set

**HUBEX Trigger** -- Webhook-based real-time events:
- `device.paired`, `device.online`, `device.offline`
- `telemetry.received`
- `alert.fired`, `alert.resolved`
- `task.completed`
- `variable.changed`

### n8n Workflow Examples

**Alert-to-Email**: HUBEX Trigger (alert.fired) -> Email node

**Variable Change to Google Sheets**: HUBEX Trigger (variable.changed) -> Google Sheets append row

**Scheduled Data Export**: Schedule Trigger -> HUBEX (Variable Stream: getHistory) -> Google Sheets

## 3. Webhook Subscriptions

Subscribe to HUBEX events for real-time notifications:

```bash
# Create subscription
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-server.com/webhook",
    "event_types": ["alert.fired", "variable.changed", "device.offline"],
    "secret": "your-hmac-secret"
  }'
```

### HMAC Signature Verification

Every webhook delivery includes an `X-Hubex-Signature` header (HMAC-SHA256). Verify it:

```python
import hmac, hashlib

def verify_signature(payload_bytes: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### Event Types

| Event | Trigger |
|-------|---------|
| `device.paired` | Device completes pairing |
| `device.online` | Device sends first telemetry after being offline |
| `device.offline` | Device exceeds stale/dead threshold |
| `telemetry.received` | New telemetry ingested |
| `alert.fired` | Alert rule condition met |
| `alert.resolved` | Alert condition cleared |
| `variable.changed` | Variable value updated |
| `task.completed` | Async task finished |

### Delivery & Retry

- Webhooks are delivered with exponential backoff (3 retries)
- Delivery logs are available via `GET /api/v1/webhooks/deliveries`
- Failed deliveries are tracked with status codes and error messages

## 4. Automation Rules

HUBEX includes a native automation engine for simple if-then rules:

```bash
# When temperature > 40, call an external webhook
curl -X POST http://localhost:8000/api/v1/automations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Overtemp webhook",
    "trigger_type": "variable_threshold",
    "trigger_config": {
      "variable_key": "temperature",
      "operator": "gt",
      "value": 40,
      "device_uid": "my-sensor"
    },
    "action_type": "call_webhook",
    "action_config": {
      "url": "https://hooks.slack.com/...",
      "method": "POST",
      "body": {"text": "Temperature alert!"}
    },
    "cooldown_seconds": 300
  }'
```

### Available Triggers

| Trigger | Config |
|---------|--------|
| `variable_threshold` | `variable_key`, `operator` (gt/gte/lt/lte/eq/ne), `value`, `device_uid` |
| `variable_geofence` | `variable_key` (lat/lng), `fence_type` (circle/polygon), `center`/`radius` or `polygon` |
| `device_offline` | `device_uid` |
| `telemetry_received` | `device_uid`, `event_type` (optional) |

### Available Actions

| Action | Config |
|--------|--------|
| `set_variable` | `key`, `value`, `scope`, `device_uid` |
| `call_webhook` | `url`, `method`, `body`, `headers` |
| `create_alert_event` | `rule_id`, `message` |
| `emit_system_event` | `event_type`, `payload` |

## 5. MQTT Bridge

Use `scripts/mqtt_bridge.py` to connect Shelly or Tasmota devices:

```bash
# Shelly devices on local broker
python scripts/mqtt_bridge.py --auto-pair

# Tasmota on remote broker
python scripts/mqtt_bridge.py \
  --mqtt-host 192.168.1.100 \
  --topic "tele/#" \
  --device-type tasmota \
  --auto-pair
```

The bridge registers itself as a HUBEX device, subscribes to MQTT topics, and forwards data as telemetry. Each MQTT device's data is namespaced by device ID in the payload.

## 6. Building a Custom Integration in 5 Steps

1. **Authenticate**: `POST /api/v1/auth/login` to get a JWT token
2. **Register device**: Use the pairing flow (hello -> claim -> confirm) to get a device token
3. **Define variables**: `POST /api/v1/variables/definitions` for each data point you want to track
4. **Send data**: `POST /api/v1/telemetry` with your device token -- the bridge handles variable mapping
5. **React to changes**: Subscribe webhooks or create automation rules

## Further Reading

- [ESP SDK](ESP_SDK.md) -- Device protocol details
- [Variable Bridge](VARIABLE_BRIDGE.md) -- Telemetry-to-variable mapping
- [Getting Started](GETTING_STARTED.md) -- Setup and first steps
- [API Device Demo](API_DEVICE.md) -- External API as virtual device
- [MQTT Bridge](MQTT_BRIDGE.md) -- Shelly/Tasmota integration
