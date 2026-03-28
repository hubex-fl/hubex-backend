# Projekt-Roadmap

> **Vision:** HubEx ist ein universeller Device Hub — nicht nur für Custom-Hardware (ESP32),
> sondern gleichwertig für Standard-Devices, API-Integrationen, Software-Agents und
> Protokoll-Bridges. Alles spricht miteinander. Alles ist grafisch ansprechend, intuitiv
> und lückenlos nachvollziehbar. Jede Architektur- und UI-Entscheidung muss für ALLE
> Device-Typen funktionieren, nicht nur für Custom-MCUs.

> **Design-Leitsatz (Phase 2+):** Orientierung an n8n (Flow-UX, Daten-Sichtbarkeit),
> Home Assistant (Card-basiert, Entity-Status) und Grafana (Time-Series, Panels).
> Kein Feature ohne visuellen Mehrwert. Keine Seite ohne Empty State.

---

## Phase 1: Core Platform ✅ ABGESCHLOSSEN

### Milestone 1: Foundation ✅
- [x] Step 1 — Auth, JWT, Users, Capability System
- [x] Step 2 — Devices, Pairing, Variables, Tasks, Telemetry
- [x] Step 3 — Events, Audit, Modules
- [x] Step 4 — Security Hardening (HMAC tokens, caps enforce, JWT validation)

### Milestone 2: Connector Architecture ✅
- [x] Step 1 — Webhook Subscriptions API (CRUD)
- [x] Step 2 — Webhook Dispatcher (retry, HMAC signature, delivery log)
- [x] Step 3 — System Events emittieren (device/task/telemetry lifecycle)

### Milestone 3: Device Groups & Entities ✅
- [x] Step 1 — Entity CRUD + Device Bindings
- [x] Step 2 — Bulk Bind/Unbind mit Savepoints
- [x] Step 3 — Health Aggregation + Groups

### Milestone 4: Observability & Alerting ✅
- [x] Step 1 — Alert Rules/Events CRUD
- [x] Step 2 — Alert Worker (device_offline, entity_health, event_lag)
- [x] Step 3 — Metrics Endpoint

### Milestone 5: Multi-Tenancy ✅
- [x] Step 1 — Organization + OrganizationUser Models
- [x] Step 2 — Org CRUD + Members API
- [x] Step 3 — JWT org_id + Switch-Org + Tenant Isolation
- [x] Step 4 — Plan Limits (free/pro/enterprise)

### Milestone 6: Edge & OTA ✅
- [x] Step 1 — Firmware Versions CRUD
- [x] Step 2 — OTA Rollouts (immediate/staged/canary)
- [x] Step 3 — Device OTA Check + Edge Config Sync
- [x] Step 4 — Staged Rollout Worker

### Milestone 7: Production Ready ✅
- [x] Step 1 — Rate-Limiting (Redis sliding window)
- [x] Step 2 — Response Caching (Redis, ETag/304)
- [x] Step 3 — Security Hardening (CORS, headers, brute-force, refresh tokens)
- [x] Step 4 — Health/Ready Endpoints + Structured Logging
- [x] Step 5 — Graceful Shutdown

---

## Phase 2: UI Mission Control ✅ ABGESCHLOSSEN

### Milestone 8: UI Reboot — Mission Control ✅
- [x] Step 1 — Design System Foundation (Tailwind, Components, Layouts, Pinia)
- [x] Step 2 — Dashboard Page (live metrics, device overview, alerts summary)
- [x] Step 3 — Devices Page Migration (new design, filters, search, device types)
- [x] Step 4 — Entities/Groups Page (tree view, bindings, health)
- [x] Step 5 — Alerts Page (rules, events, ack/resolve)
- [x] Step 6 — OTA Page (firmware, rollouts, device status)
- [x] Step 7 — Org/Settings Pages (org management, members, plan)
- [x] Step 8 — Webhooks + Events + Audit Pages
- [x] Step 9 — Device-Type Classification + DeviceDetail System Context
- [x] Step 10 — Settings Page Hub (Account, Org, API Keys, Developer)

---

## Phase 3: Variable Data Hub [done] ✅

### Milestone 8c: Variable Stream Visualization Foundation ✅ DONE
> Variablen sind der zentrale Datenpunkt. Devices senden Telemetrie, die automatisch
> in typisierte Variablen fließt — jeder Stream wird passend visualisiert.
> Foundation für den Dashboard Builder (M20).

- [x] V1 — Backend CRUD + History (~4h)
  - `display_hint` + `category` Spalten in VariableDefinition
  - `variable_history` Tabelle (BigInt, time-series, numeric_value denormalisiert)
  - `PATCH /variables/definitions/{key}` — editierbare Metadaten
  - `DELETE /variables/definitions/{key}` — echtes Löschen mit Cascade
  - `GET /variables/history` — Zeitreihe mit SQL-Downsampling
  - History-Recording nach jedem Value-Write (source: user/device/telemetry)
  - Alembic-Migration

- [x] V2 — Widget-Komponenten (Grafana/HA/n8n-inspiriert) (~5h)
  - `lib/viz-types.ts` — VizType, VizDataPoint, VizWidgetProps, Farb-Palette
  - `lib/viz-resolve.ts` — resolveVizType(), DISPLAY_HINT_OPTIONS
  - `composables/useVariableHistory.ts` — Polling mit TimeRange-Selector
  - `VizSparkline.vue` — Pure SVG Sparkline (kein Chart.js)
  - `VizLineChart.vue` — Chart.js Time Series (date-fns Adapter)
  - `VizGauge.vue` — SVG Radial Gauge (HA-style, dynamische Farbe)
  - `VizBoolIndicator.vue` — Status Dot + Event Timeline
  - `VizLogView.vue` — Scrollendes Mono-Log (n8n-style)
  - `VizJsonViewer.vue` — Klappbarer JSON-Baum (VSCode-style)
  - `VizMapView.vue` — Leaflet Pin (lazy-loaded)
  - `VizImageView.vue` — URL-Image mit Auto-Refresh
  - `VizWidget.vue` — Grafana-Panel-Container (Header, Skeleton, Footer, Routing)

- [x] V3 — Variables.vue Full CRUD + Inline Viz (~3h)
  - Create-Modal: alle Felder inkl. display_hint, category, unit, min/max
  - Edit-Definition-Modal: PATCH mutable fields
  - Set-Value-Modal: mit Versionskonflikts-Auflösung
  - Delete-Definition: echtes Cascade-Delete mit Bestätigung
  - Sparkline-Spalte: inline Trend für numerische Variablen
  - Expandable-Detail-Row: VizWidget + Metadaten
  - Toolbar: Suche nach key/category/description

- [x] V4 — Telemetry Bridge + DeviceDetail (~2h)
  - `app/api/v1/telemetry.py`: fire-and-forget Bridge nach Telemetrie-Persist
  - Matching: `{event_type}.{key}` und `{key}` gegen `device_writable` Definitionen
  - Wert-Coercion zu definition.value_type
  - Upsert VariableValue + record_history(source="telemetry")
  - Non-blocking: asyncio.create_task

- [x] V5 — VariableStreams.vue + Navigation (~2h)
  - `/variables/streams` — Grafana-style Real-Time Monitoring Grid
  - CSS Grid: 2/3/4 Spalten (responsive, user-wählbar)
  - TimeRange-Selector: 1h/6h/24h/7d/30d
  - Card-Selection: Multi-Select für fokussiertes Monitoring
  - Fullscreen-Overlay: Klick → Fullscreen Chart
  - Auto-Refresh: 15s Polling
  - Keyboard: Esc schließt Fullscreen
  - Sidebar: "Data" Gruppe mit Variables + Streams

### Milestone 8d: Data Hub — Lücken schließen [done] ✅
> Offene Punkte aus der Variable-Visualisierung, die für Production-Reife wichtig sind.

- [x] Step 1 — History Retention Policy: Background-Task löscht Einträge > 30 Tage (~1h)
  - `app/core/history_retention.py` — `history_retention_loop()` läuft stündlich
  - Config: `HUBEX_HISTORY_RETENTION_DAYS` (default: 30), in main.py lifespan eingebunden

- [x] Step 2 — DeviceDetail Variable-Panel: Inline-Sparklines für Device-Variables (~2h)
  - `loadSparklines()` lädt 1h History für int/float Variablen
  - VizSparkline neben jedem numerischen Wert in der Variable-Tabelle
  - "View in Streams →" Link im Footer des Variable-Panels

- [x] Step 3 — Variable-basierte Alert-Rules: Alert wenn Variable Schwellwert überschreitet (~3h)
  - `condition_type = "variable_threshold"` im Alert Worker registriert
  - `condition_config`: `{variable_key, threshold_operator (gt/gte/lt/lte/eq/ne), threshold_value, device_uid?}`
  - `VALID_CONDITION_TYPES` in alerts.py erweitert

- [x] Step 4 — Variable → Webhook Bridge: Bei Variable-Change Webhook triggern (~2h)
  - `variable.changed` System-Event in `create_or_update_value` + `_v2` emittiert
  - Webhook-Dispatcher filtert event_type = "variable.changed" automatisch

- [x] Step 5 — Telemetry Bridge: Nested Payload-Support (~1h)
  - `_flatten_payload()` — Dot-Notation bis 3 Ebenen tief
  - `sensors.temperature` aus `{"sensors": {"temperature": 23.5}}` wird als Variable-Key gemappt

- [x] Step 6 — Streams: Device-Selektor statt UID-Eingabe (~1h)
  - USelect Dropdown mit `availableDevices` aus `/api/v1/devices`
  - Letzte Auswahl in `localStorage` ("streams_device_uid") gespeichert

- [x] Step 7 — Bulk-Variable-Set: Mehrere Variablen gleichzeitig setzen (~1h)
  - `POST /api/v1/variables/bulk-set` mit `allow_partial` + `BulkSetResult`
  - Bis zu 50 Items pro Request, partial-failure Tracking

---

## Phase 4: Integration & Demo [done] ✅

### Milestone 9: Device Integration Demo [done] ✅
> Zeigt dass HubEx nicht nur Custom-MCUs kann, sondern ein universeller Hub ist.
- [x] Step 1 — ESP SDK Update (OTA check, edge config, heartbeat, variable bridge demo)
  - `app/simulator/__main__.py` — Python CLI Simulator (hello, telemetry, tasks, variables, ack)
  - Configurable failure injection, simulation duration, firmware version
- [x] Step 2 — End-to-End Demo (ESP → Telemetry → Variable → Alert → Webhook → n8n)
  - `scripts/demo_e2e.py` — 8-Step Demo: Auth → Pair → Telemetry → Alerts → Webhooks → Events → Config → Cleanup
  - Inkl. `variable_threshold` Alert (temperature > 40°C) + `variable.changed` Webhook-Filter
  - `docs/E2E_DEMO.md` — Anleitung + Architektur
- [x] Step 3 — Provisioning Flow (QR-Code Pairing, App-freundlich)
  - `app/api/v1/pairing.py` — Hello/Start/Claim/Confirm/Status/QR Endpoints
  - `frontend/src/pages/Pairing.vue` — 2-Step Pairing UI
  - 10min TTL, Rate-Limiting (10/60s), Legacy-Routes kompatibel
- [x] Step 4 — API-Device Demo (externe REST-API als virtuelles Device)
  - `scripts/api_device.py` — Periodisches HTTP-Polling externer APIs als virtuelles Device
  - `docs/API_DEVICE.md` — Dokumentation + Beispiele (Wetter, Stocks, Metriken)
  - Auto-Pairing, Nested-JSON-Flattening, Variable-Override für Poll-Intervall
- [x] Step 5 — Standard-Device Connector (z.B. Shelly/Tasmota via MQTT)
  - `scripts/mqtt_bridge.py` — MQTT-zu-HUBEX Bridge (paho-mqtt)
  - `docs/MQTT_BRIDGE.md` — Shelly + Tasmota Topic-Formate dokumentiert
  - Bridge als HUBEX Device registriert, Namespace per MQTT Device ID

### Milestone 10: CI/CD & Deployment [done] ✅
- [x] Step 1 — GitHub Actions (test, build, lint, coverage)
- [x] Step 2 — Docker Production Compose (Traefik, SSL, PostgreSQL, Redis, backups)
- [x] Step 3 — One-Click Deploy Script (Linux, .env Generator)
- [x] Step 4 — Health-Check Dashboard (uptime, DB-connections, Redis-latency)

### Milestone 10.5: Automation Engine — Native If→Then Rules [done] ✅
> Native automation engine: wenn eine Bedingung erfüllt ist, wird eine Aktion ausgeführt.
> Kein externer Workflow-Editor nötig — direkt in HUBEX, grafisch und intuitiv.

- [x] Step 1 — Backend: AutomationRule Model + CRUD API + Engine (~4h)
  - `AutomationRule` Tabelle: trigger_type/config + action_type/config + cooldown
  - `AutomationFireLog` Tabelle: Ausführungshistorie pro Regel
  - `GET/POST/PATCH/DELETE /api/v1/automations` + Test + History Endpoints
  - Engine-Loop: evaluiert Regeln bei System-Events (variable.changed, device.offline, telemetry.received)
  - Trigger: variable_threshold, variable_geofence (Haversine + Ray-Casting), device_offline, telemetry_received
  - Actions: set_variable, call_webhook, create_alert_event, emit_system_event

- [x] Step 2 — Frontend: Automations Page — Visual If→Then Builder (~3h)
  - `/automations` — Regelübersicht als Cards mit [IF trigger] → [THEN action]
  - Modal: Trigger-Typ-Picker (Icons + Beschreibung) → dynamische Konfiguration
  - Geofence-Konfig: Circle (lat/lng + radius) oder Polygon (JSON)
  - Fire Count + Last Fired Timestamps
  - "Test Fire" Button

### Milestone 11: n8n Integration [done] ✅
- [x] Step 1 — n8n Webhook Templates (alert → email, variable.changed → sheets)
  - `n8n-nodes-hubex/nodes/Hubex/HubexTrigger.node.ts` — Webhook-basierter Trigger
  - Event Types: device.paired/online/offline, telemetry.received, alert.fired/resolved, variable.changed
- [x] Step 2 — Custom n8n Node für HubEx (Trigger: any event, Action: set variable)
  - `n8n-nodes-hubex/nodes/Hubex/Hubex.node.ts` — CRUD Node (Device, Telemetry, Alert, Variable)
  - `n8n-nodes-hubex/credentials/HubexApi.credentials.ts` — JWT Auth Credentials
- [x] Step 3 — n8n Node: Variable-Stream als Datenquelle
  - New "Variable Stream" resource in Hubex.node.ts
  - Operations: getHistory, getSnapshot, getDefinitions, bulkSet
  - Full parameter support: time ranges, scopes, limits, JSON bulk input

### Milestone 12: Developer Docs [done] ✅
- [x] Step 1 — API Docs Landing Page (Swagger / Redoc)
  - `frontend/src/pages/ApiDocs.vue` — Landing page at `/api-docs`
  - Links to Swagger UI + ReDoc, copy-to-clipboard OpenAPI URL
  - 10 API sections with base paths, descriptions, key endpoints
  - Authentication flow + rate limits documentation
  - Sidebar entry in Admin group
- [x] Step 2 — Getting Started Guide (Device Pairing, First Variable, First Alert)
  - `docs/GETTING_STARTED.md` — Prerequisites, quick setup, 6-step first-steps guide
  - curl examples for auth, pairing, variables, telemetry, alerts, automations
- [x] Step 3 — ESP SDK Docs + Variable Bridge Docs
  - `docs/ESP_SDK.md` — Device lifecycle, telemetry, OTA, edge config, simulator usage
  - `docs/VARIABLE_BRIDGE.md` — Bridge matching rules, value coercion, nested payloads, bulk-set, history
- [x] Step 4 — SDK/Integration Guide (Python Agent, n8n, Webhooks)
  - `docs/INTEGRATION_GUIDE.md` — Python agent, n8n node, webhooks (HMAC), automations, MQTT bridge
  - 5-step custom integration guide

### Milestone 12.5: Pitch & Go-to-Market [done] ✅
- [x] Step 1 — Pitch Deck (Partner/Investoren)
  - `docs/PITCH_DECK.md` — 13-slide Marp-compatible deck with speaker notes
  - Cover, Problem, Solution, Demo, How It Works, Architecture, Market, Competition, Business Model, Traction, Roadmap, Team, Ask
- [x] Step 2 — Product Landing Page (Branding, Demo-Video)
  - `frontend/src/pages/Landing.vue` — Full dark-themed landing at `/landing`
  - Hero with gradient, 6 feature cards, architecture flow, comparison table, 3-tier pricing, CTA
  - Public layout (no sidebar/auth), mobile-responsive, pure Tailwind CSS
  - Router + App.vue updated for `meta: { layout: "public" }` bypass
- [x] Step 3 — Competitive Analysis (vs. AWS IoT Core, ThingsBoard, Home Assistant, Datacake, Grafana, Blynk, Ubidots)
  - `docs/COMPETITIVE_ANALYSIS.md` — 11-dimension matrix + 7 detailed competitor analyses
  - Strengths, weaknesses, HUBEX advantage per competitor
- [x] Step 4 — Pricing Model (Free: 5 Devices; Pro: 50 Devices + History 90d; Enterprise: unlimited)
  - `docs/PRICING.md` — 3-tier Open Core model with feature table
  - FAQ, Build vs. Buy ROI calculation ($64K savings), add-on pricing concept

---

## Phase 5: Plattform-Erweiterung [todo]

### Milestone 13: Realtime & Notifications [todo] ← AKTUELL
- [ ] Step 1 — WebSocket Layer (device events, variable-stream, auth)
  > Basis für M8c Streams-Page in Echtzeit (aktuell Polling)
- [ ] Step 2 — Notification System (Email, Push, Webhook dispatch)
- [ ] Step 3 — Notification Preferences UI (per-user, per-alert-rule)

### Milestone 14: MCP Server Integration [todo]
- [ ] Step 1 — MCP Tool Definitions (Device, Alert, Variable, OTA, Metrics Tools)
- [ ] Step 2 — MCP Endpoint Layer + Auth Integration
- [ ] Step 3 — MCP Client für externe Server (Enrichment, AI)
- [ ] Step 4 — MCP-based AI Agent Demo ("set variable temperature_threshold to 75")

### Milestone 15: Provider/Signal System [todo]
- [ ] Step 1 — Provider API (CRUD, Registration, Health Monitoring)
- [ ] Step 2 — Signal Schema + Validation + Ingestion Pipeline
- [ ] Step 3 — Provider Lifecycle (enable/disable/revoke, MIC-gated)
- [ ] Step 4 — Built-in Providers (Webhook Receiver, Timer/Cron, MQTT Listener)

### Milestone 16: Rules Engine [todo]
- [ ] Step 1 — Rule Artifact Model (validate, version, activate, rollback)
- [ ] Step 2 — Signal → Rule Matching + Condition Evaluation
  > Variable-Wert kann als Signal dienen (aus M8d Step 3)
- [ ] Step 3 — Rule → Execution Pipeline (deterministic, traceable)
- [ ] Step 4 — Rule UI (create, test, monitor, trace view) — n8n-Stil

### Milestone 17: Universal Agent SDK [todo]
> Agents sind gleichwertige Device-Typen neben MCUs, API-Devices und Standard-Devices.
- [ ] Step 1 — Agent Protocol Spec (HTTP + WebSocket, handshake, heartbeat)
- [ ] Step 2 — Python SDK Agent (RPi, Linux, system telemetry → variables)
- [ ] Step 3 — Node.js SDK Agent
- [ ] Step 4 — OS Agent Features (service mgmt, remote shell, config push via Variables)
- [ ] Step 5 — Windows Agent + Installer/Service

### Milestone 18: Bridge/Gateway Framework [todo]
- [ ] Step 1 — Bridge Agent Architecture (plugin system, auto-discovery)
- [ ] Step 2 — Serial/UART Bridge Plugin
- [ ] Step 3 — Modbus RTU/TCP Bridge Plugin (industrial sensors → Variables)
- [ ] Step 4 — BLE Bridge Plugin
- [ ] Step 5 — CAN Bus / I2C / SPI Bridge Plugin

### Milestone 19: Advanced Observability [todo]
- [ ] Step 1 — Trace/Timeline View (execution traces, event correlation)
- [ ] Step 2 — Incident Management + Cross-Entity Correlation
- [ ] Step 3 — Support Bundle Export (diagnostics, config snapshot)
- [ ] Step 4 — Variable Anomaly Detection (ML-basiert, z-score, threshold learning)

### Milestone 20: Dashboard Builder [todo]
> **Direkte Abhängigkeit von M8c** — VizWidget, VizDataPoint, useVariableHistory
> werden vom Dashboard Builder wiederverwendet. Keine Neu-Implementierung nötig.
- [ ] Step 1 — Dashboard/Widget Model + CRUD API
  > Widget-Types: direkt aus VizType (sparkline/line_chart/gauge/bool/log/json/map/image)
- [ ] Step 2 — Widget-Library-Integration (VizWidget → Dashboard Card)
  > VizWidgetProps direkt als Dashboard Widget Config speichern
- [ ] Step 3 — Drag & Drop Grid Editor (vue-grid-layout + VizWidget)
- [ ] Step 4 — Dashboard Data Sources: Variable, Telemetry, Metrics, Entity Health
- [ ] Step 5 — Dashboard Sharing + Capability-gated Permissions
- [ ] Step 6 — Embed Mode (iframe, public link, kiosk)

---

## Phase 6: Enterprise [todo]

### Milestone 21: Security Hardening v2 [todo]
- [ ] Step 1 — 2FA/MFA (TOTP, WebAuthn)
- [ ] Step 2 — API Key Management (service-to-service auth)
- [ ] Step 3 — RBAC Roles (admin, operator, viewer, custom)
- [ ] Step 4 — Session Management UI + Device Token Rotation

### Milestone 22: Admin Console [todo]
- [ ] Step 1 — Module Lifecycle UI (enable/disable/revoke, dependency view)
- [ ] Step 2 — Policy Management (capability policies, plan enforcement)
- [ ] Step 3 — Provider Health Dashboard + System Status

### Milestone 23: Simulator/Testbench [todo]
- [ ] Step 1 — Sim-Entities + Sim-Providers (virtual devices, mock signals)
- [ ] Step 2 — Testbench Orchestrator (Given → Trigger → Expected Trace)
- [ ] Step 3 — Report Generation (pass/fail, coverage, CI integration)

### Milestone 24: Templates/Blueprints [todo]
- [ ] Step 1 — Template Catalog (browseable, searchable, tagged)
  > Templates können Variable-Definitionen + Streams + Dashboard in einem Deploy bündeln
- [ ] Step 2 — Template Installer (preflight checks, dependency resolution)
- [ ] Step 3 — Rollback/Uninstall + Experiment Mode (A/B, canary)

### Milestone 25: Plugins Framework [todo]
- [ ] Step 1 — Plugin Manifest + MIC v1 Lifecycle
- [ ] Step 2 — Sandboxed Plugin Execution (capability-gated)
- [ ] Step 3 — Plugin Registry/Marketplace (catalog, versioning, revocation)
- [ ] Step 4 — Plugin SDK + Developer Guide

### Milestone 26: Backup & Mobile [todo]
- [ ] Step 1 — Config/State Snapshot (policies, schedules, export/import)
- [ ] Step 2 — Scheduled Backups (cron, retention, S3/local)
- [ ] Step 3 — Mobile PWA (responsive dashboard, push notifications)
  > Basis: VariableStreams als PWA-taugliche Seite

### Milestone 27: Data & Analytics [todo]
- [ ] Step 1 — Telemetry Time-Series Aggregation (ergänzt variable_history)
  > variable_history ist bereits der Time-Series-Layer — Telemetry braucht separaten Store
- [ ] Step 2 — Data Export (CSV, JSON, API bulk) für variable_history + telemetry
- [ ] Step 3 — Advanced Analytics Charts (Trend, Comparison, Heatmap via VizWidget)
- [ ] Step 4 — Device Provisioning Profiles (batch onboarding)

---

## Abhängigkeits-Graph (vereinfacht)

```
M1-7 (Core)
  └─► M8 (UI) ✅
        └─► M8c (Variable Viz) ✅
              ├─► M8d (Data Hub Gaps) ✅
              ├─► M20 (Dashboard Builder) — nutzt VizWidget direkt
              └─► M13 (Realtime) — WebSocket ersetzt Polling in VariableStreams
M9 (Device Demo)
  └─► demonstriert Telemetry → Variable Bridge (M8c V4)
M14 (MCP)
  └─► steuert Variables + Alerts via natürlicher Sprache
M16 (Rules Engine)
  └─► Variable-Wert als Signal-Trigger (aus M8d Step 3)
M17 (Agent SDK)
  └─► Python Agent sendet System-Telemetrie → Variables automatisch
M24 (Templates)
  └─► bundles Variable-Definitions + Streams + Dashboard in einem Template
```

---

## Nächste 3 Sprints (Priorität)

| Sprint | Milestone | Fokus | Aufwand |
|--------|-----------|-------|---------|
| **Sprint 1** | M8d Step 1-3 | History-Retention + DeviceDetail Vars + Variable-Alerts | ~6h |
| **Sprint 2** | M9 | E2E Device Demo mit Variable Bridge | ~15h |
| **Sprint 3** | M10 | CI/CD + Docker Production | ~8h |
