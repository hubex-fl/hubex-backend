# HUBEX Virtual API Device

Connect any external REST API as a HUBEX device — no hardware required.

## Concept

HUBEX is not limited to physical sensors. Any HTTP data source can be registered as a "device":
- Weather APIs → temperature, humidity, wind speed as telemetry
- Financial APIs → stock price, volume as telemetry
- Internal monitoring endpoints → CPU, memory, request rate
- Any service with a JSON REST API

The virtual device behaves exactly like a real ESP32: it pairs, sends heartbeats, pushes telemetry, and reads variable overrides from the edge config.

## Quick Start

```bash
pip install requests

# Munich weather (Open-Meteo — no API key needed)
python scripts/api_device.py --auto-pair

# Watch it in HUBEX dashboard → Devices → api-device-xxxx
```

## Usage

```bash
python scripts/api_device.py [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--server` | `http://localhost:8000` | HUBEX server URL |
| `--email` | test user | HUBEX user email |
| `--password` | test password | HUBEX user password |
| `--uid` | `api-device-xxxx` | Unique device UID |
| `--source-url` | Open-Meteo weather | External API URL to poll |
| `--fields` | all numeric | Comma-separated field names |
| `--interval` | `30` | Poll interval in seconds |
| `--auto-pair` | false | Auto-pair on first run |
| `--token` | none | Device token (skip pairing) |

## Examples

### Weather Station
```bash
python scripts/api_device.py \
  --uid "weather-munich" \
  --source-url "https://api.open-meteo.com/v1/forecast?latitude=48.1&longitude=11.6&current=temperature_2m,wind_speed_10m,relative_humidity_2m" \
  --fields "temperature_2m,wind_speed_10m,relative_humidity_2m" \
  --interval 60 \
  --auto-pair
```

### Internal Service Monitor
```bash
python scripts/api_device.py \
  --uid "service-metrics" \
  --source-url "http://internal-service:8080/metrics/json" \
  --fields "cpu_usage,memory_mb,request_rate" \
  --interval 15 \
  --auto-pair
```

### Already-Paired Device (token from previous run)
```bash
python scripts/api_device.py \
  --uid "weather-munich" \
  --token "your_device_token_here" \
  --source-url "https://api.open-meteo.com/..."
```

## Remote Variable Overrides

You can control the poll interval from the HUBEX dashboard without restarting the script:

1. Open the device in HUBEX → Variables
2. Add variable: `poll_interval_s` = `10`
3. The script reads this on the next cycle and adjusts the sleep interval

## Field Auto-Detection

If `--fields` is not specified, all numeric top-level fields from the API response are extracted automatically. Nested fields are flattened (first level only).

Example response:
```json
{
  "current": {
    "temperature_2m": 12.3,
    "wind_speed_10m": 8.5,
    "relative_humidity_2m": 72
  }
}
```
→ Extracted: `{"temperature_2m": 12.3, "wind_speed_10m": 8.5, "relative_humidity_2m": 72.0}`
