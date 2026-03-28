# Getting Started with HUBEX

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Backend runtime |
| Node.js | 20+ | Frontend build |
| PostgreSQL | 15+ | Primary database |
| Redis | 7+ | Rate-limiting, caching |
| Docker | 24+ | Optional: production deployment |

## Quick Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-org/hubex.git
cd hubex

# 2. Backend setup
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env: set DATABASE_URL, REDIS_URL, JWT_SECRET

# 4. Run database migrations
alembic upgrade head

# 5. Start backend
uvicorn app.main:app --reload --port 8000

# 6. Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`, backend at `http://localhost:8000`.

## First Steps

### 1. Create an Account

Open `http://localhost:5173/login` and register. The first user gets admin capabilities automatically.

### 2. Register a Device (Pairing Flow)

Navigate to `/pairing` in the UI, or use the API:

```bash
# Device sends hello
curl -X POST http://localhost:8000/api/v1/pairing/hello \
  -H "Content-Type: application/json" \
  -d '{"uid": "my-sensor-01", "fw_version": "1.0.0"}'

# User claims the device (needs JWT)
curl -X POST http://localhost:8000/api/v1/pairing/claim \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"uid": "my-sensor-01", "label": "Temperature Sensor"}'

# Device confirms pairing
curl -X POST http://localhost:8000/api/v1/pairing/confirm \
  -H "Content-Type: application/json" \
  -d '{"uid": "my-sensor-01"}'
```

### 3. Create Variable Definitions

Variables define what data your devices track:

```bash
curl -X POST http://localhost:8000/api/v1/variables/definitions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "temperature",
    "value_type": "float",
    "scope": "device",
    "writable": "device_writable",
    "unit": "C",
    "display_hint": "gauge",
    "description": "Ambient temperature"
  }'
```

### 4. Send Telemetry

Devices send telemetry using their device token:

```bash
curl -X POST http://localhost:8000/api/v1/telemetry \
  -H "X-Device-Token: $DEVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_uid": "my-sensor-01",
    "event_type": "sensor",
    "payload": {
      "temperature": 23.5,
      "humidity": 65
    }
  }'
```

The telemetry bridge automatically populates matching variables.

### 5. Set Up an Alert Rule

```bash
curl -X POST http://localhost:8000/api/v1/alerts/rules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High Temperature",
    "condition_type": "variable_threshold",
    "condition_config": {
      "variable_key": "temperature",
      "threshold_operator": "gt",
      "threshold_value": 40,
      "device_uid": "my-sensor-01"
    },
    "severity": "warning"
  }'
```

### 6. Create an Automation Rule

```bash
curl -X POST http://localhost:8000/api/v1/automations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alert on high temp",
    "trigger_type": "variable_threshold",
    "trigger_config": {
      "variable_key": "temperature",
      "operator": "gt",
      "value": 40,
      "device_uid": "my-sensor-01"
    },
    "action_type": "create_alert_event",
    "action_config": {
      "rule_id": "<alert-rule-id>",
      "message": "Temperature exceeded 40C"
    },
    "cooldown_seconds": 300
  }'
```

## API Authentication

```bash
# Login to get tokens
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "yourpass"}' \
  | jq -r .access_token)

# Use token for authenticated requests
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/devices
```

## Further Reading

- [ESP SDK Documentation](ESP_SDK.md) -- Device lifecycle, telemetry, OTA
- [Variable Bridge](VARIABLE_BRIDGE.md) -- How telemetry auto-populates variables
- [Integration Guide](INTEGRATION_GUIDE.md) -- Python agents, n8n, webhooks, MQTT
- [E2E Demo](E2E_DEMO.md) -- Full end-to-end demonstration script
- Interactive API docs: `/docs` (Swagger) or `/redoc` (ReDoc)
