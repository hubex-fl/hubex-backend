# User Guide

## Devices

### 4 Device-Typen
- **Hardware**: ESP32, Shelly, physische Sensoren/Aktoren. Kommuniziert via Telemetry-API.
- **Service**: REST APIs (Wetter, Börse, etc.). HubEx pollt periodisch den konfigurierten Endpoint.
- **Bridge**: MQTT Broker, Modbus Gateway. Leitet Protokoll-Daten als Variables weiter.
- **Agent**: Software auf Raspberry Pi, Linux, Windows. Nutzt HubEx SDK (Python/Node/Go).

### Device hinzufügen
1. **"+ New"** oder **"+ Device"** → Device Wizard öffnet sich
2. Typ wählen → Konfiguration eingeben → Name vergeben → Create
3. Device erscheint in der Liste mit Status (Online/Offline/Stale)

### DeviceDetail
- **System Context**: Visualisiert Verbindungen zu Variables, Alerts, Automations
- **Telemetry**: Eingehende Sensordaten (Rohdaten)
- **State**: Variable-Werte (verarbeitet, mit Semantic Types)
- **Config**: Gerätespezifische Einstellungen (API URL, MQTT Topic, etc.)

## Variables

### Konzept
Jede Messgröße ist eine **Variable** mit:
- **Key**: Eindeutiger Bezeichner (z.B. `temperature`, `humidity`)
- **Semantic Type**: Was die Variable bedeutet (Temperatur → °C, Gauge-Widget)
- **Scope**: `global` (systemweit) oder `device` (pro Gerät)
- **Direction**: `read` (Sensor), `write` (Aktor), `read_write` (bidirektional)

### Auto-Discovery
Wenn ein Device Telemetrie sendet, erkennt HubEx automatisch neue Variablen und erstellt Variable Definitions mit passenden Semantic Types.

## Dashboards

### Widgets
| Typ | Verwendung |
|-----|-----------|
| **Gauge** | Momentanwert mit Min/Max (Temperatur, Prozent) |
| **Line Chart** | Zeitreihe mit 5 Range-Optionen (1h-30d) |
| **Sparkline** | Kompakte Trendlinie |
| **Bool / Status** | An/Aus, True/False Anzeige |
| **Log** | Letzte Werte als Liste |
| **JSON** | Rohdaten-Viewer |
| **Map** | GPS-Position auf Karte |
| **Toggle** | Schalter (bidirektional) |
| **Slider** | Regler (bidirektional) |

### Dashboard teilen
- **Public Link**: Settings → Share → Token generieren
- **PIN-geschützt**: 4-6 stellige PIN für sensible Daten
- **Kiosk-Mode**: `/kiosk/{id}` → Fullscreen ohne Sidebar

## Automations

### Trigger (IF)
| Trigger | Beschreibung |
|---------|-------------|
| Variable Threshold | Wenn Wert über/unter Schwelle |
| Variable Geofence | Wenn GPS-Position Zone verlässt/betritt |
| Device Offline | Wenn Gerät nicht mehr erreichbar |
| Device Online | Wenn Gerät wieder erreichbar |
| Telemetry Received | Bei jedem eingehenden Datenpunkt |
| Variable Change | Bei jeder Wertänderung |
| Schedule (Cron) | Zeitgesteuert (täglich, wöchentlich, etc.) |

### Actions (THEN)
| Action | Beschreibung |
|--------|-------------|
| Set Variable | Variable-Wert ändern |
| Call Webhook | HTTP-Request an externe URL |
| Create Alert | Alert-Event erstellen |
| Emit System Event | System-Event broadcasten |
| Send Notification | In-App Benachrichtigung |
| Log to Audit | Audit-Eintrag schreiben |
| Send Email | Email via Template versenden |

### AND/OR Bedingungen
Zusätzlich zum Haupt-Trigger können **Condition Groups** definiert werden:
- **ALL (AND)**: Alle Bedingungen müssen erfüllt sein
- **ANY (OR)**: Mindestens eine Bedingung muss erfüllt sein
- Mehrere Gruppen werden AND-verknüpft

## Alerts

- **Rules**: Definieren wann ein Alert feuert (Variable Threshold, Zeitbereich)
- **Events**: Gefeuerte Alerts mit Status (Firing → Acknowledged → Resolved)
- **Severity**: Info, Warning, Critical

## Settings

- **Profile & Account**: Email, 2FA (TOTP), Sessions
- **Organization**: Team-Mitglieder, Rollen, Branding (White-Label)
- **Developer**: API Keys, Capabilities, Useful Links
- **System**: Demo Data, Export/Import, Language (EN/DE)
