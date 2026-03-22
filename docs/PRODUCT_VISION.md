# HUBEX — Product Vision & Roadmap

## 1. Kern-Positionierung

### Was HUBEX ist
**HUBEX ist ein Open-Source Hardware-Software Interface Hub** — eine selbst-gehostete Plattform, die physische Geräte (ESP32, Arduino, Raspberry Pi, industrielle Controller) mit Software-Systemen verbindet und eine einheitliche, sichere, deterministische Steuerungsschicht bereitstellt.

### Das Problem
Wer heute ein IoT-Produkt oder eine Automatisierung mit eigener Hardware baut, steht vor einem Dilemma:

1. **Cloud-Plattformen** (AWS IoT, Azure IoT Hub, Google IoT Core*): Vendor Lock-in, Kosten pro Device, keine Kontrolle über Datenhoheit, Overheadauf Overhead
2. **Home-Automation** (Home Assistant, openHAB): Fokus auf Consumer-Enduser, nicht auf Produktbau oder industrielle Vernetzung
3. **Eigenbau**: Jedes Startup baut seinen eigenen Device-Management-Stack — Pairing, Token, OTA, State Sync — von Null

HUBEX löst Kategorie 3: Es ist **der Stack, den jeder IoT-Entwickler ohnehin baut**, aber als fertiges, sicheres, erweiterbares Fundament.

### Differenzierung (was HUBEX anders macht)

| Feature | AWS IoT / Azure | Home Assistant | HUBEX |
|---------|----------------|----------------|-------|
| Self-hosted, datenhoheitlich | Nein | Ja | **Ja** |
| Device-Pairing out-of-box | Nein (DIY) | Plugin-abhängig | **Ja, deterministisch** |
| Capability-basierte Security | IAM (komplex) | Rudimentär | **Deny-by-default, feingranular** |
| Hardware-agnostisch | AWS-SDK only | Zigbee/Z-Wave/WiFi | **Jedes Protokoll via Connector** |
| API-first für Produktbau | Ja | Nein (UI-first) | **Ja** |
| Automation Engine | Greengrass/Rules | Automatisierungen | **n8n/Node-RED Delegation + Basic-Engine** |
| Kosten pro Device | $$ | Frei | **Frei** |
| Edge-to-Cloud Bridge | Ja | Nein | **Planned (Federation)** |

### Core Design Principles
1. **API-first**: Jede Funktion ist zuerst eine API, dann optional eine UI
2. **Protocol-agnostic Connectors**: MQTT, HTTP, WebSocket, BLE, Serial — alles via Connector-Interface
3. **Deterministic State**: Device State ist immer reproduzierbar (Snapshot → Apply → ACK)
4. **Security by default**: Capabilities statt Rollen, deny-by-default, Token-Rotation, Audit-Trail
5. **Composable**: HUBEX ist ein Hub — Automation lebt in n8n/Node-RED, Dashboards in Grafana, Alerts in PagerDuty

---

## 2. Zielgruppen

### Primär: IoT Product Builders
- Startups die Hardware-Produkte bauen (Smart Home, Industrial Sensor, Agritech, MedTech)
- Brauchen: Device Provisioning, State Management, OTA, User-Device-Binding, API für ihre App
- Pain: Bauen den gleichen Stack immer wieder

### Sekundär: System Integrators / Industrie 4.0
- Vernetzen heterogene Maschinen/Sensoren
- Brauchen: Protocol Bridge, unified API, Audit, deterministic State
- Pain: Jede Maschine hat ein anderes Protokoll

### Tertiär: Maker / Power-User
- Basteln mit ESP32, Raspberry Pi, Arduino
- Brauchen: Einfaches Pairing, WebSocket-Live-Updates, n8n-Integration
- Pain: Kein guter Self-Hosted Device Hub zwischen "Home Assistant" und "eigener Code"

---

## 3. Architektur-Kern (Zielzustand)

```
┌─────────────────────────────────────────────────────────┐
│                    HUBEX Core                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Identity │ │  State   │ │  Events  │ │   Audit   │  │
│  │ & Pairing│ │ (Vars v3)│ │ & Signals│ │ (append)  │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │Capability│ │Execution │ │ Connector│ │  Module   │  │
│  │  Engine  │ │  Engine  │ │  Manager │ │ Registry  │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
└──────────────────┬──────────────────────┬───────────────┘
                   │                      │
        ┌──────────▼──────────┐  ┌────────▼─────────┐
        │   Connector Layer   │  │  Integration API  │
        │ MQTT │ HTTP │ WS │  │  │ REST │ WS │ gRPC │
        │ BLE  │Serial│ TCP│  │  │ Webhooks │ SSE   │
        └──────────┬──────────┘  └────────┬─────────┘
                   │                      │
        ┌──────────▼──────────┐  ┌────────▼─────────┐
        │     Devices         │  │  External Systems │
        │ ESP32 │ RPi │ PLC  │  │ n8n │Grafana│Apps │
        └─────────────────────┘  └──────────────────┘
```

### Architektur-Entscheidungen

**Connector Manager (NEU, zentral)**
Der größte fehlende Baustein. Statt fest verdrahteter HTTP/WS-Telemetrie wird ein generisches Connector-Interface eingeführt:
- `ConnectorBase`: async connect/disconnect/send/receive
- Built-in: HTTP (existing), MQTT, WebSocket
- Community: BLE, Serial/UART, Modbus, CAN-Bus
- Jeder Connector registriert sich im Module Registry

**Execution Engine (VEREINFACHT)**
Statt einer eigenen Rule Engine: Ein schlanker Task-Executor der:
- Zeitgesteuerte Tasks (Cron-artig) ausführt
- Event-triggered Tasks (Signal → Action) verarbeitet
- Für alles Komplexere: Webhook an n8n/Node-RED

**State Sync Protocol (EVOLUTION von Vars v3)**
- Device meldet `reported_state`
- Backend berechnet `desired_state` (aus User-Eingaben, Rules, Defaults)
- Diff → `effective_config` → Push an Device → Device ACKs per Revision
- Identical to AWS IoT Shadow concept, but self-hosted and simpler

---

## 4. Roadmap

### Phase 1: Foundation Hardening (AKTUELL — ~2 Wochen)
**Ziel:** Solide Basis, alle Security-Issues gefixt, Tests grün

- [x] Security: JWT Secret Validation, HMAC Token Hashing, Caps Enforce ON
- [x] Bulk Operations: Atomic Transactions
- [x] Token Cleanup: TTL-basierte Revocation Cleanup
- [x] Test Infrastructure: conftest.py mit shared Fixtures
- [x] Modern FastAPI Patterns: lifespan statt on_event
- [ ] Pagination auf allen List-Endpoints (limit/offset mit sinnvollen Defaults + Max)
- [ ] Structured Error Responses auf allen Endpoints vereinheitlichen
- [ ] OpenAPI Spec: Vollständig, mit Beispielen, als Contract

**Gate:** Alle Tests grün, Security-Audit Checkliste bestanden, OpenAPI exportierbar

---

### Phase 2: Connector Architecture (~4 Wochen)
**Ziel:** HUBEX kann mit Devices über verschiedene Protokolle kommunizieren

**M1: Connector Interface**
- ConnectorBase ABC definieren (connect, disconnect, send, receive, health)
- Connector Registry im Module System
- Connector Lifecycle Management (start/stop/restart/health)
- Built-in HTTP Connector (refactored aus bestehender Telemetry)

**M2: MQTT Connector**
- MQTT Broker Integration (Mosquitto/EMQX)
- Topic Schema: `hubex/{device_uid}/telemetry`, `hubex/{device_uid}/command`
- Auto-Subscription bei Device Pairing
- QoS 1 für Commands, QoS 0 für Telemetry

**M3: WebSocket Connector**
- Bidirektionaler Channel pro Device
- Heartbeat/Reconnect
- Ersetzt das bestehende WS-Polling

**Gate:** ESP32 kann über MQTT und HTTP mit HUBEX kommunizieren, Live-Demo

---

### Phase 3: State Sync & Device Twins (~3 Wochen)
**Ziel:** Deterministic State Management wie AWS IoT Shadow, aber einfacher

**M1: Device Twin Model**
- `reported_state` (vom Device gemeldet)
- `desired_state` (vom User/System gesetzt)
- `effective_state` (berechneter Diff, readonly)
- `metadata` (Timestamps, Versionen pro Feld)

**M2: State Sync Protocol**
- Device → Backend: REPORT (state + revision)
- Backend → Device: DELTA (nur Änderungen, idempotent)
- Device → Backend: ACK (revision bestätigt)
- Conflict Resolution: last-writer-wins mit Audit

**M3: Vars v3 Migration**
- Bestehende Variables in Device Twin überführen
- Backwards-compatible API + Migration Script

**Gate:** Device Twin E2E: User setzt desired → Device erhält Delta → ACK → UI zeigt sync

---

### Phase 4: Integration Layer (~3 Wochen)
**Ziel:** HUBEX als Hub — verbindet sich mit externen Systemen

**M1: Webhook System**
- Outbound Webhooks bei Events (device.paired, state.changed, alert.triggered)
- Configurable per Event-Type + Filter
- Retry mit exponential Backoff
- n8n/Zapier/Make.com kompatibel

**M2: REST API Hardening**
- API Keys (nicht nur JWT)
- Rate Limiting per API Key
- Versioned API (v1, v2 parallel)
- SDK Generation (Python, TypeScript, Go)

**M3: Grafana/Prometheus Integration**
- Metrics Endpoint (/metrics, Prometheus-Format)
- Device Health Dashboards
- Alert Thresholds via Grafana

**Gate:** n8n Workflow der auf Device-Event reagiert, Grafana Dashboard zeigt Device-Health

---

### Phase 5: Basic Automation Engine (~2 Wochen)
**Ziel:** Einfache Event-Driven Rules ohne externe Tooling-Dependency

**M1: Rule Engine (Minimal)**
- IF condition THEN action Rules
- Conditions: Device State, Time, Signal Value
- Actions: Set Variable, Send Command, Trigger Webhook, Create Audit Entry
- Keine komplexen Flows — dafür gibt es n8n

**M2: Scheduled Tasks**
- Cron-ähnliche Task-Schedules
- "Jeden Tag um 8:00 setze Variable X auf Y"
- "Alle 5 Minuten prüfe Device Health"

**Gate:** Rule "wenn Temperatur > 40 → Webhook an n8n" funktioniert E2E

---

### Phase 6: Multi-Protocol Device SDK (~4 Wochen)
**Ziel:** Devices können HUBEX einfach integrieren

**M1: ESP-IDF SDK (existiert teilweise)**
- Provisioning Library (Pairing, Token, WiFi)
- State Sync Client (Report/Delta/ACK)
- MQTT + HTTP Transport auswählbar
- OTA Update Integration

**M2: Arduino Library**
- Simplified API für Hobbyisten
- `hubex.connect()`, `hubex.report(state)`, `hubex.onCommand(cb)`

**M3: Python SDK (für RPi/Linux Devices)**
- Async Client
- Device Twin Sync
- Telemetry + Command Channel

**Gate:** ESP32, Arduino Uno WiFi, Raspberry Pi — alle drei verbinden sich mit HUBEX

---

### Phase 7: Production Readiness (~3 Wochen)
**Ziel:** HUBEX ist deployment-ready

- Multi-Tenant Support (Workspace/Org Isolation)
- TLS/mTLS für Device-Communication
- Backup/Restore
- Deployment Guides (Docker Compose, Kubernetes Helm Chart)
- Rate Limiting per Tenant
- Monitoring & Alerting Stack

---

## 5. Architektur-Optimierungen (Sofort)

### Was sich jetzt schon ändern sollte

**1. Connector Abstraction vorbereiten**
Die aktuelle Telemetrie ist direkt in FastAPI-Endpoints verdrahtet. Bevor Phase 2 beginnt, sollte ein `TelemetryService` Layer zwischen Endpoint und DB eingeführt werden, der später zum Connector-Backend wird.

**2. Device State konsolidieren**
Aktuell: `device_state.py` berechnet State aus mehreren Queries. Das sollte ein `DeviceTwin` Model werden mit `reported`/`desired`/`effective` als JSON-Columns — vorbereitet für Phase 3.

**3. Provider/Signal Scaffolding aktivieren**
Die Provider-Models existieren aber sind nicht verdrahtet. Statt sie zu löschen: Sie werden die Connector-Adapter-Schicht. Signal-Ingest wird zum generischen Event-Bus.

**4. Event-System als Backbone**
Events v1 ist bereits append-only. Es sollte der zentrale Message-Bus werden: Jeder Connector, jede State-Änderung, jede Action emitted ein Event. Webhooks subscriben auf diesen Stream.

---

## 6. Was HUBEX NICHT sein soll

- **Kein Home Assistant Klon**: HUBEX ist für Produktbau, nicht für Enduser-Automatisierung
- **Kein Cloud-IoT-Service**: Immer self-hosted first, optional Federation
- **Keine eigene Dashboard-Plattform**: Grafana/Custom UI — HUBEX liefert Daten, nicht Dashboards
- **Keine vollwertige Automation Engine**: n8n/Node-RED für komplexe Flows, HUBEX für einfache Rules
- **Kein Protokoll-Konverter**: HUBEX managed Devices, nicht Protokoll-Translation (dafür gibt es Connectors)
