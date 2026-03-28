# HUBEX MQTT Bridge

Connect Shelly, Tasmota, or any MQTT-enabled device to HUBEX — no firmware changes required.

## Concept

Standard IoT devices like Shelly plugs or Tasmota flashed hardware publish telemetry to an MQTT broker. The HUBEX MQTT bridge:

1. Subscribes to MQTT topics from your devices
2. Parses JSON or plain numeric payloads
3. Forwards data as HUBEX telemetry (namespaced by device ID)
4. Appears as a single paired HUBEX device — the bridge itself

This means any MQTT-capable device becomes visible in the HUBEX dashboard without code changes.

## Quick Start

```bash
pip install paho-mqtt requests

# Connect all Shelly devices (broker on localhost)
python scripts/mqtt_bridge.py --auto-pair

# Watch in HUBEX → Devices → mqtt-bridge-xxxx
```

## Usage

```bash
python scripts/mqtt_bridge.py [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--server` | `http://localhost:8000` | HUBEX server URL |
| `--email` | test user | HUBEX user email |
| `--password` | test password | HUBEX user password |
| `--uid` | `mqtt-bridge-xxxx` | HUBEX device UID for this bridge |
| `--mqtt-host` | `localhost` | MQTT broker hostname or IP |
| `--mqtt-port` | `1883` | MQTT broker port |
| `--mqtt-user` | none | MQTT broker username (optional) |
| `--mqtt-pass` | none | MQTT broker password (optional) |
| `--topic` | `shellies/#` | MQTT topic to subscribe to |
| `--device-type` | `auto` | Format hint: `auto`, `shelly`, `tasmota` |
| `--interval` | `10` | Min seconds between telemetry pushes per device |
| `--auto-pair` | false | Auto-pair bridge with HUBEX on first run |
| `--token` | none | HUBEX device token (skip pairing) |

## Examples

### Shelly Devices (all)
```bash
python scripts/mqtt_bridge.py \
  --uid "shelly-bridge" \
  --mqtt-host 192.168.1.10 \
  --topic "shellies/#" \
  --device-type shelly \
  --interval 15 \
  --auto-pair
```

### Tasmota Devices
```bash
python scripts/mqtt_bridge.py \
  --uid "tasmota-bridge" \
  --mqtt-host 192.168.1.10 \
  --topic "tele/#" \
  --device-type tasmota \
  --interval 10 \
  --auto-pair
```

### Specific Device Only
```bash
python scripts/mqtt_bridge.py \
  --topic "shellies/shelly1-abc123/#" \
  --auto-pair
```

### With MQTT Authentication
```bash
python scripts/mqtt_bridge.py \
  --mqtt-host broker.example.com \
  --mqtt-port 8883 \
  --mqtt-user myuser \
  --mqtt-pass mypassword \
  --topic "shellies/#" \
  --auto-pair
```

### Already-Paired Bridge
```bash
python scripts/mqtt_bridge.py \
  --token "your_device_token_here" \
  --mqtt-host 192.168.1.10
```

## Supported Topic Formats

### Shelly
| Topic | Payload | Extracted Field |
|-------|---------|-----------------|
| `shellies/{id}/relay/0/power` | `"12.5"` | `{id}.power` |
| `shellies/{id}/relay/0/energy` | `"1024"` | `{id}.energy` |
| `shellies/{id}/temperature` | `"23.4"` | `{id}.temperature` |
| `shellies/{id}/status` | `{"temperature": 23.4, ...}` | `{id}.temperature`, ... |

### Tasmota
| Topic | Payload | Extracted Fields |
|-------|---------|-----------------|
| `tele/{id}/SENSOR` | `{"SHT3X-0x44":{"Temperature":22.1,"Humidity":55.0}}` | `{id}.SHT3X-0x44.Temperature`, etc. |
| `tele/{id}/STATE` | `{"Wifi":{"RSSI":-65},...}` | `{id}.Wifi.RSSI`, etc. |
| `stat/{id}/STATUS` | `{"Status":{"Power":1}}` | `{id}.Status.Power` |

## Telemetry Namespacing

All fields are prefixed with the MQTT device ID:

```
shellies/shelly1-abc123/relay/0/power → {"shelly1-abc123.power": 12.5}
shellies/shelly1-def456/temperature  → {"shelly1-def456.temperature": 21.3}
```

This means a single HUBEX bridge device carries data from all your MQTT devices in one telemetry stream.

## Rate Limiting

The `--interval` option prevents flooding HUBEX with a telemetry push for every MQTT message. Fields received within the window are **accumulated** (last value wins), then pushed as a batch when the interval expires.

Example with `--interval 10`:
- Messages arrive every 1s from shelly1-abc123
- Only one telemetry push every 10s
- Each push includes the latest value of all fields seen in that window

## How It Works

```
MQTT Broker                    HUBEX MQTT Bridge              HUBEX Server
    │                               │                              │
    │  shellies/shelly1/power: 12.5 │                              │
    │──────────────────────────────>│                              │
    │  shellies/shelly1/power: 11.8 │                              │
    │──────────────────────────────>│  POST /api/v1/telemetry      │
    │  (10s interval expires)       │  {"shelly1.power": 11.8}     │
    │                               │─────────────────────────────>│
    │                               │  POST /edge/heartbeat        │
    │                               │─────────────────────────────>│ (every 60s)
```
