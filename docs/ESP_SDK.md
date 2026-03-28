# ESP SDK Documentation

## Overview

HUBEX provides a device protocol that any microcontroller (ESP32, STM32, RPi Pico, etc.) or software agent can implement. The reference implementation is a Python CLI simulator at `app/simulator/__main__.py`.

## Device Lifecycle

```
Device                          HUBEX Server
  |                                 |
  |-- POST /pairing/hello --------->|  (uid, fw_version)
  |                                 |  Creates pending pairing
  |         User claims device      |
  |         via UI or API           |
  |                                 |
  |-- POST /pairing/confirm ------->|  (uid)
  |<-------- device_token ----------|  Device is now paired
  |                                 |
  |-- POST /telemetry ------------->|  (with X-Device-Token)
  |-- GET /edge/config ------------>|  (periodic config sync)
  |-- GET /ota/check -------------->|  (firmware update check)
  |                                 |
```

### 1. Hello (Registration)

The device announces itself:

```bash
curl -X POST http://localhost:8000/api/v1/pairing/hello \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "esp32-sensor-01",
    "fw_version": "1.0.0",
    "hw_version": "rev3",
    "model": "ESP32-WROOM-32"
  }'
```

### 2. Claim (User Action)

A user claims the device through the UI (`/pairing`) or API:

```bash
curl -X POST http://localhost:8000/api/v1/pairing/claim \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"uid": "esp32-sensor-01", "label": "Office Sensor"}'
```

### 3. Confirm (Device Action)

The device confirms and receives its token:

```bash
curl -X POST http://localhost:8000/api/v1/pairing/confirm \
  -H "Content-Type: application/json" \
  -d '{"uid": "esp32-sensor-01"}'
# Response: { "device_token": "hmac-xxx-xxx" }
```

### 4. Heartbeat

Devices send periodic telemetry to maintain their "online" status. A device is marked stale/dead if no telemetry is received within the configured interval.

## Sending Telemetry

```bash
curl -X POST http://localhost:8000/api/v1/telemetry \
  -H "X-Device-Token: $DEVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_uid": "esp32-sensor-01",
    "event_type": "sensor",
    "payload": {
      "temperature": 23.5,
      "humidity": 65,
      "pressure": 1013.25
    }
  }'
```

The telemetry bridge automatically maps payload fields to matching variable definitions. See [Variable Bridge](VARIABLE_BRIDGE.md) for details.

## Variable Bridge

When a device sends telemetry, HUBEX matches payload keys against `device_writable` variable definitions and auto-populates variable values. This means devices do not need to explicitly call the variable API.

### Reading Variables

Devices can read their current variable values:

```bash
curl http://localhost:8000/api/v1/variables/snapshot?scope=device&device_uid=esp32-sensor-01 \
  -H "X-Device-Token: $DEVICE_TOKEN"
```

## OTA Check

Devices periodically check for firmware updates:

```bash
curl http://localhost:8000/api/v1/ota/check?device_uid=esp32-sensor-01&current_version=1.0.0 \
  -H "X-Device-Token: $DEVICE_TOKEN"
```

Response (when update available):
```json
{
  "update_available": true,
  "version": "1.1.0",
  "download_url": "/api/v1/ota/firmware/1.1.0/download",
  "checksum": "sha256:abc123..."
}
```

## Edge Config Sync

Devices can fetch their configuration:

```bash
curl http://localhost:8000/api/v1/edge/config \
  -H "X-Device-Token: $DEVICE_TOKEN"
```

This returns device-specific configuration including variable overrides, poll intervals, and feature flags.

## Python Simulator

The reference simulator demonstrates the full device lifecycle:

```bash
# Basic usage
python -m app.simulator --url http://localhost:8000 --uid sim-device-01

# With auto-pairing (creates + claims + confirms)
python -m app.simulator --url http://localhost:8000 --uid sim-device-01 --auto-pair \
  --email user@example.com --password yourpass

# Options
#   --duration <seconds>    Simulation duration (default: 60)
#   --interval <seconds>    Telemetry interval (default: 5)
#   --fw-version <ver>      Firmware version string
#   --fail-rate <0-1>       Probability of simulated failures
#   --verbose               Show all events including telemetry
```

## Further Reading

- [Variable Bridge](VARIABLE_BRIDGE.md) -- Detailed telemetry-to-variable mapping
- [Getting Started](GETTING_STARTED.md) -- Full setup guide
- [Integration Guide](INTEGRATION_GUIDE.md) -- Python agents, n8n, webhooks
