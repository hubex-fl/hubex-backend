# API Integration Guide

## Authentifizierung

### JWT Token
```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Response: {"access_token": "eyJ...", "refresh_token": "..."}

# Alle weiteren Requests:
curl -H "Authorization: Bearer eyJ..." http://localhost:8000/api/v1/devices
```

### API Keys (Service-to-Service)
```bash
# API Key erstellen (im UI: Settings → Developer → API Keys)
# Key-Format: hbx_<32 hex chars>

# Nutzen wie JWT:
curl -H "Authorization: Bearer hbx_abc123..." http://localhost:8000/api/v1/devices
```

## Wichtige Endpoints

### Devices
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| GET | `/api/v1/devices` | Alle Devices auflisten |
| GET | `/api/v1/devices/{id}` | Device Details |
| POST | `/api/v1/devices/pairing/start` | Pairing starten |
| POST | `/api/v1/telemetry` | Telemetrie senden (Device-Token) |

### Variables
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| GET | `/api/v1/variables/effective` | Aktuelle Werte |
| PUT | `/api/v1/variables/value` | Wert setzen |
| GET | `/api/v1/variables/history` | Verlaufsdaten |

### Dashboards
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| GET | `/api/v1/dashboards` | Alle Dashboards |
| POST | `/api/v1/dashboards` | Dashboard erstellen |
| GET | `/api/v1/dashboards/public/{token}` | Public Dashboard (kein Auth) |

## Webhooks

### Webhook erstellen
```bash
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"url":"https://your-server.com/webhook","secret":"my-secret","event_filter":["device.offline","alert.fired"]}'
```

### Webhook-Payload
```json
{
  "event_type": "device.offline",
  "timestamp": "2026-04-07T12:00:00Z",
  "payload": {"device_uid": "esp32-001", "device_id": 5},
  "signature": "hmac-sha256..."
}
```

## n8n Integration

### Trigger: HubEx Webhook → n8n
1. In n8n: Webhook-Node erstellen → URL kopieren
2. In HubEx: Webhooks → New → n8n URL einfügen
3. Events auswählen (device.offline, variable.changed, alert.fired)

### Action: n8n → HubEx API
1. In n8n: HTTP Request Node
2. URL: `http://hubex:8000/api/v1/variables/value`
3. Header: `Authorization: Bearer hbx_...`
4. Body: `{"key": "target_temp", "value": 22.5}`

## Export / Import

```bash
# Config exportieren
curl -H "Authorization: Bearer eyJ..." http://localhost:8000/api/v1/export > backup.json

# Config importieren
curl -X POST -F "file=@backup.json" \
  -H "Authorization: Bearer eyJ..." \
  http://localhost:8000/api/v1/export/import
```

## OpenAPI / Swagger
Vollständige API-Dokumentation: `http://localhost:8000/docs`
