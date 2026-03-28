# Variable Bridge

## Overview

The Variable Bridge automatically maps incoming telemetry data to typed HUBEX variables. When a device sends telemetry, the bridge inspects the payload and updates matching variable definitions -- no explicit variable API calls needed from the device side.

## How It Works

```
Device sends telemetry:
  POST /api/v1/telemetry
  { event_type: "sensor", payload: { temperature: 23.5, humidity: 65 } }

Bridge matches against variable definitions:
  1. Try "{event_type}.{key}" -> "sensor.temperature"
  2. Try "{key}" -> "temperature"
  3. If match found with writable="device_writable" -> update value
  4. Record history entry (source: "telemetry")
```

## Matching Rules

The bridge tries two patterns for each payload key, in order:

1. **Qualified key**: `{event_type}.{key}` (e.g., `sensor.temperature`)
2. **Plain key**: `{key}` (e.g., `temperature`)

The first matching variable definition with `writable = "device_writable"` wins.

### Requirements for a Match

- A `VariableDefinition` must exist with the matching key
- The definition must have `writable` set to `device_writable`
- The definition `scope` must be `device`
- The device must be paired and belong to the same organization

## Value Coercion

Values are coerced to the definition's `value_type`:

| Definition type | Coercion behavior |
|----------------|-------------------|
| `int` | `int(value)` -- truncates decimals |
| `float` | `float(value)` |
| `bool` | Truthy check: `"true"`, `"1"`, `1`, `true` -> `True` |
| `string` | `str(value)` |
| `json` | Stored as-is (must be valid JSON) |

If coercion fails, the value is skipped (no error raised to avoid blocking telemetry).

## Nested Payload Support

The bridge flattens nested JSON payloads using dot-notation, up to 3 levels deep:

```json
// Telemetry payload:
{
  "sensors": {
    "temperature": 23.5,
    "location": {
      "lat": 48.137,
      "lng": 11.576
    }
  }
}

// Flattened keys generated:
// "sensors.temperature" -> 23.5
// "sensors.location.lat" -> 48.137
// "sensors.location.lng" -> 11.576
```

Each flattened key is matched against variable definitions using the same rules above.

## Bulk Variable Set

For setting multiple variables at once (e.g., from an n8n flow or external integration):

```bash
curl -X POST http://localhost:8000/api/v1/variables/bulk-set \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      { "key": "temperature", "value": "23.5", "scope": "device", "device_uid": "my-sensor" },
      { "key": "humidity", "value": "65", "scope": "device", "device_uid": "my-sensor" },
      { "key": "alert_threshold", "value": "40", "scope": "org" }
    ],
    "allow_partial": true
  }'
```

Response includes per-item success/failure status:
```json
{
  "total": 3,
  "succeeded": 3,
  "failed": 0,
  "results": [
    { "key": "temperature", "ok": true },
    { "key": "humidity", "ok": true },
    { "key": "alert_threshold", "ok": true }
  ]
}
```

## Variable History

Every value change is recorded in `variable_history` with:

- `recorded_at` -- Timestamp
- `numeric_value` -- Denormalized float for efficient time-series queries
- `value` -- Original string value
- `source` -- One of: `user`, `device`, `telemetry`

Query history via:

```bash
curl "http://localhost:8000/api/v1/variables/history?key=temperature&scope=device&device_uid=my-sensor&limit=100" \
  -H "Authorization: Bearer $TOKEN"
```

Optional time range: `&from=2024-01-01T00:00:00Z&to=2024-01-02T00:00:00Z`

History is automatically pruned by a background retention task (default: 30 days, configurable via `HUBEX_HISTORY_RETENTION_DAYS`).

## Webhook Integration

When a variable value changes, a `variable.changed` system event is emitted. Webhook subscriptions filtering on this event type will receive notifications automatically.

## Further Reading

- [ESP SDK](ESP_SDK.md) -- Device lifecycle and telemetry
- [Integration Guide](INTEGRATION_GUIDE.md) -- n8n, Python agents, webhooks
- [Getting Started](GETTING_STARTED.md) -- Full setup guide
