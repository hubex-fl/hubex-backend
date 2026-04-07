# HUBEX — Umfassende Projekt-Analyse & Fahrplan

Stand: 2026-03-25

---

## 1. CC Roadmap Dashboard — Status

**Status: FUNKTIONAL, MINIMAL, VISUALIZE-ONLY** ✅

Das CC-System wurde bereits erfolgreich auf Visualisierung reduziert:
- `cc-system/cc-server.js` — 70 Zeilen, 0 Dependencies, reines Node.js `http`
- `cc-system/dashboard.html` — Dark-Theme Dashboard, Auto-Refresh 30s
- `cc-system/package.json` — Keine externen Abhängigkeiten
- Port 3131, parsed `ROADMAP.md` → JSON API + HTML View
- **Kein Job-Running, kein Scheduling, keine Automation**
- **Kein Eingriff in HUBEX-Projekt (kein git, keine rules)**

→ **Keine Aktion nötig.** Dashboard ist exakt wie gewünscht.

---

## 2. Modul-Analyse: IST vs. SOLL

### Was bereits implementiert ist (Backend):

| Bereich | Models | API Endpoints | Workers | Status |
|---------|--------|---------------|---------|--------|
| Auth/Users | User, RefreshToken, RevokedToken | 5 | token_cleanup | ✅ Vollständig |
| Devices | Device, DeviceToken, DeviceRuntime | 15+ | health_worker | ✅ Vollständig |
| Pairing | PairingSession | 5 | — | ✅ Vollständig |
| Telemetry | DeviceTelemetry | 3 + WS | — | ✅ Vollständig |
| Tasks | Task, ExecutionContext | 6 | — | ✅ Vollständig |
| Variables | VarDef, VarValue, VarAudit, VarSnapshot, VarEffect, VarAck | 15+ | — | ✅ Vollständig |
| Events | EventV1, Checkpoint | 5 | — | ✅ Vollständig |
| Effects | EffectV1 | 2 | — | ✅ Vollständig |
| Signals | SignalV1 | 1 | — | ⚠️ Basis vorhanden |
| Executions | ExecDef, ExecRun | 12 | — | ✅ Vollständig |
| Entities/Groups | Entity, Binding | 12 | — | ✅ Vollständig |
| Alerts | AlertRule, AlertEvent | 9 | alert_worker | ✅ Vollständig |
| Audit | AuditV1Entry | 2 | — | ✅ Vollständig |
| OTA | FirmwareVersion, OtaRollout, DeviceOtaStatus | 12 | ota_worker | ✅ Vollständig |
| Webhooks | WebhookSub, WebhookDelivery | 4 | webhook_dispatcher | ✅ Vollständig |
| Orgs | Organization, OrgUser | 9 | — | ✅ Vollständig |
| Secrets | SecretV1 | 2 | — | ✅ Basis |
| Config | ConfigV1 | 2 | — | ✅ Basis |
| Modules | ModuleRegistry | 4 | — | ✅ Basis |
| Providers | ProviderType, ProviderInstance | 0 (nur Model) | — | ⚠️ Nur Schema |
| Metrics | — | 1 | — | ✅ Vollständig |

### Modul-Mapping: C1–C7e gegen IST-Zustand

#### C1 — UI Module (System Stage) → 40% vorhanden
- ✅ Frontend existiert (Vue 3 + Tailwind + Mission Control Design)
- ✅ Capability-gated Nav in DefaultLayout.vue
- ✅ Event Streams konsumierbar (useEventStream composable)
- ✅ Metrics Dashboard (useMetrics composable)
- ❌ MIC-gated Module Visibility fehlt
- ❌ Execution Trace View fehlt (TraceHub.vue ist Placeholder)
- ❌ System Stage als echtes Ops-Dashboard fehlt
- **Wird durch Milestone 8 (UI Reboot) größtenteils abgedeckt**

#### C2 — Providers/Signals → 15% vorhanden
- ✅ Provider Model existiert (ProviderType, ProviderInstance)
- ✅ Signal Model existiert (SignalV1)
- ✅ Events-System für Signal-Propagation vorhanden
- ❌ Keine Provider API Endpoints
- ❌ Keine Provider Registration/Lifecycle
- ❌ Keine Signal Schema Validation
- ❌ Kein Health-Monitoring für Provider
- ❌ Keine Secrets/Config Integration für Provider
- **Neuer Milestone nötig**

#### C3 — Rules/Engine → 10% vorhanden
- ✅ Execution Framework (Definitions, Runs, Workers) → Runtime-Basis
- ✅ Alert Rules → primitive Regelauswertung
- ❌ Kein Rule Artifact Management
- ❌ Kein Signal → Rule → Execution Pipeline
- ❌ Keine deterministische Rule Engine
- ❌ Kein Rollback/Versioning für Rules
- **Neuer Milestone nötig**

#### C4 — Observability/Support → 35% vorhanden
- ✅ Audit Trail vorhanden
- ✅ Events/Effects read-only Views
- ✅ Alert Events
- ✅ Metrics Endpoint
- ❌ Kein Trace/Timeline View
- ❌ Kein Incident Management
- ❌ Kein Support Bundle Export
- ❌ Kein Cross-Entity Correlation
- **Teilweise durch UI Reboot Milestone 8 abdeckbar, Rest als eigener Milestone**

#### C5 — Templates/Experiments → 0% vorhanden
- ❌ Komplett neu zu bauen
- **Sinnvoll erst nach Rules Engine (C3)**

#### C6 — Simulator/Testbench → 0% vorhanden
- ❌ Komplett neu zu bauen
- **Hoher Wert für Demo/Sales/CI**

#### C7a — Admin Console → 25% vorhanden
- ✅ Module enable/disable API
- ✅ Capability System (69 caps)
- ✅ Org Management
- ❌ Kein Admin-spezifisches UI
- ❌ Keine Policy-UI
- ❌ Kein Provider Health Dashboard

#### C7b — Backup → 0%
#### C7c — Plugins Framework → 5% (Modules-Basis)
#### C7d — Registry/Marketplace → 0%
#### C7e — Mobile → 0%

---

## 3. Test-Devices Cleanup — ERLEDIGT ✅

- 101 Test-Devices gelöscht (alle device-*, test*, sim-*, smoke-*, dev-*, etc.)
- Zugehörige Daten bereinigt: Telemetrie, Tasks, Variables, Snapshots, Tokens, Pairings, OTA-Status
- **Verbleibt:** 1 echtes Device → `80f3da5440a8` (ESP32, claimed)

---

## 4. Software Clients (RPi, Windows, Linux) — Bewertung

### Konzept: "Universal Agent"
Neben ESP32/MCU-Devices soll HUBEX auch vollwertige OS-Systeme anbinden können. Das bedeutet:

**Agent-Typen:**
1. **MCU Agent** (ESP32, STM32) → Bereits vorhanden (hello/heartbeat/telemetry/OTA)
2. **OS Agent** (RPi, Linux, Windows, macOS) → NEU
3. **SDK Agent** (In eigene Software integrierbar) → NEU

**Was ein OS Agent können muss:**
- System-Telemetrie (CPU, RAM, Disk, Network, Uptime, Processes)
- OS-Event Triggers (Service crashed, Disk full, Login detected, etc.)
- Command Execution (Remote Shell, Script Runner)
- File Sync / Config Push
- Software Updates (apt, winget, etc.)
- Service Management (systemctl, Windows Services)
- Auto-Discovery & Self-Registration

**Was ein SDK Agent können muss:**
- Lightweight Library (Python, Node.js, Go, Rust, C#)
- `hubex.connect(url, token)` → WebSocket/HTTP
- `hubex.emit_signal(type, payload)` → Signal an HUBEX senden
- `hubex.on_command(handler)` → Commands empfangen
- `hubex.report_health()` → Periodischer Health Check
- Embeddable in bestehende Applikationen

### Architektur-Impact:
- Device Model braucht `device_type` Enum: `mcu | os_agent | sdk_agent | virtual`
- Telemetry Schema wird polymorph (MCU-Sensoren vs. OS-Metrics vs. Custom)
- OTA wird zu "Update Management" (Firmware für MCU, Packages für OS, SDK-Version für SDK)
- Tasks werden universell (Flash-Firmware vs. Run-Script vs. API-Call)

### Empfehlung: **Milestone 14 — Universal Agent SDK**

---

## 5. Non-Internet Interfaces (Hardware Bus, IO) — Bewertung

### Konzept: "Transport Layer Abstraction"

Aktuell: Nur HTTP/HTTPS + WebSocket (Internet-basiert)

**Gewünschte Erweiterungen:**
- **Serial/UART** — Direkte Verbindung zu MCUs
- **I2C/SPI** — Sensor-Bus
- **CAN Bus** — Industrie/Automotive
- **Modbus RTU/TCP** — Industrieautomation
- **BLE** — Bluetooth Low Energy (Proximity)
- **Zigbee/Z-Wave** — Smart Home Protocols
- **LoRaWAN** — Long Range IoT
- **GPIO** — Direct Pin Control (RPi)

### Architektur-Ansatz: "Bridge/Gateway Pattern"

```
[Physical Device] ←→ [Bus Protocol] ←→ [HUBEX Bridge Agent] ←→ [HUBEX API]
                                              ↑
                                     Läuft auf RPi/PC
                                     als OS Agent + Bridge Plugin
```

**Nicht HUBEX-Core erweitern**, sondern:
1. Bridge-Agent läuft auf Gateway-Hardware (RPi, Industrial PC)
2. Bridge hat Protocol-Plugins (CAN, Modbus, BLE, Serial, etc.)
3. Bridge übersetzt Bus-Daten → HUBEX Signals/Events
4. Bridge empfängt HUBEX Commands → Bus-Commands

**Vorteile:**
- Core bleibt Internet/API-only (sauber, skalierbar)
- Bus-Komplexität ist isoliert im Bridge-Agent
- Verschiedene Bridges für verschiedene Protokolle
- Bridge ist selbst ein OS-Agent (Punkt 4)

### Empfehlung: **Milestone 15 — Bridge/Gateway Framework**

---

## 6. MCP (Model Context Protocol) Integration — Bewertung

### Wert für HUBEX:

**HUBEX als MCP Server** (Höchste Priorität):
- AI-Assistenten können direkt mit HUBEX interagieren
- "Zeig mir alle offline Devices" → MCP Tool → `/api/v1/devices?status=offline`
- "Erstelle eine Alert Rule für Temperatur > 40°C" → MCP Tool → Alert API
- "Starte OTA Rollout für alle ESP32" → MCP Tool → OTA API
- Natürliche Sprach-Schnittstelle für HUBEX ohne eigenes LLM
- **Claude, ChatGPT, Copilot, lokale LLMs** können HUBEX steuern

**HUBEX als MCP Client** (Mittlere Priorität):
- HUBEX konsumiert externe MCP Server (z.B. für Enrichment)
- Beispiel: Device-Telemetrie → MCP-Server für Anomalie-Erkennung
- Beispiel: Alert → MCP-Server für intelligente Empfehlung

**Implementierung:**
- Neuer Endpoint-Layer: `/mcp/v1/tools` mit Tool-Definitionen
- Wrapper um bestehende API-Endpoints als MCP Tools
- Kein neuer Code nötig, nur Mapping
- ~20-30 MCP Tools aus bestehenden ~150 API Endpoints

### Empfehlung: **Milestone 13 — MCP Server Integration** (vor Agent SDK, da low effort / high value)

---

## 7. Custom UI/Interface Builder — Bewertung

### Konzept: "HUBEX Dashboards"

User baut eigene Interfaces aus vorgefertigten Widgets:

**Widget-Typen:**
- Metric Card (Wert, Trend, Threshold-Farbe)
- Device Status Grid
- Chart (Line, Bar, Gauge, Heatmap)
- Alert Feed
- Command Button (löst Task/Execution aus)
- Toggle Switch (setzt Variable)
- Input Field (setzt Variable)
- Map (Device-Locations)
- Kamera-Feed (MJPEG/RTSP)
- Custom HTML/JS Block

**Architektur:**
- Dashboard Definition = JSON (widgets, layout, bindings)
- Gespeichert in DB (neues Model: `Dashboard`, `DashboardWidget`)
- Frontend: Drag & Drop Grid-Editor
- Capability-gated: Wer darf welches Dashboard sehen/editieren
- Widgets binden an bestehende APIs (Metrics, Variables, Devices, etc.)
- Sharing: Dashboard-Link generieren

**Vergleich Markt:**
- Grafana → Fokus auf Metrics/Logs, kein Device Management
- Node-RED Dashboard → Fokus auf Flows, schwer zu bedienen
- Home Assistant → Smart Home only
- **HUBEX Dashboards** → IoT Device Management + Custom UI = Alleinstellung

### Empfehlung: **Milestone 18 — Dashboard Builder** (spät, weil Aufwand hoch, aber USP)

---

## 8. Sicherheit, UX/UI, Business-Analyse

### Sicherheit — Aktueller Stand: GUT (7/10)

**Vorhanden:**
- ✅ JWT mit Refresh Tokens + Revocation
- ✅ Brute-Force Protection (Redis-backed)
- ✅ CORS + Security Headers Middleware
- ✅ Rate Limiting (sliding window)
- ✅ Capability-based Access Control (69 Caps)
- ✅ Tenant Isolation (org_id in JWT)
- ✅ HMAC-signed Webhooks
- ✅ Password Hashing (bcrypt)

**Fehlt / Verbesserungswürdig:**
- ❌ **2FA/MFA** — Kritisch für Production
- ❌ **API Key Management** — Für Service-to-Service Auth
- ❌ **IP Whitelisting** — Für Orgs
- ❌ **Audit auf Login/Auth Events** — Wer hat wann von wo eingeloggt
- ❌ **Secrets Encryption at Rest** — SecretV1 Werte verschlüsseln
- ❌ **RBAC Roles** — Aktuell nur flat Caps, keine Rollen-Gruppen
- ❌ **Session Management UI** — Aktive Sessions sehen/revoken
- ⚠️ **Device Token Rotation** — Auto-Rotate nach X Tagen
- ⚠️ **CSP Headers** — Content Security Policy für Frontend

### UX/UI — Aktueller Stand: BEFRIEDIGEND (6/10)

**Vorhanden:**
- ✅ Mission Control Dark Theme (professionell)
- ✅ 16 Custom UI Components
- ✅ Responsive Sidebar + Navigation
- ✅ Capability-gated Navigation

**Fehlt / Verbesserungswürdig:**
- ❌ **Onboarding Flow** — Erster Login → Guided Setup
- ❌ **Empty States** — Schöne Leerzustände statt leerer Tabellen
- ❌ **Keyboard Shortcuts** — Power-User Feature
- ❌ **Search/Command Palette** — Cmd+K für schnelle Navigation
- ❌ **Breadcrumbs** — Wo bin ich?
- ❌ **Toast/Notification Center** — Gesammelte Benachrichtigungen
- ❌ **Dark/Light Toggle** — Store existiert, aber kein echtes Light Theme
- ❌ **Loading States konsistent** — Skeleton Loader teilweise defekt (Dashboard Issue)
- ❌ **Error Boundaries** — Fehler-Handling im Frontend
- ❌ **i18n** — Deutsch/Englisch Mischmasch bereinigen

### Business / Marktanalyse

**Positionierung:** Self-Hosted-First IoT Device Hub

**Marktsegment:** SMB + Maker + Enterprise Edge
- Zu groß für Arduino Cloud
- Zu klein/speziell für AWS IoT Core / Azure IoT Hub
- Flexibler als Balena / Particle

**Marktlücken die HUBEX bedient:**
1. **Self-Hosted IoT Management** — Keine Cloud-Abhängigkeit, DSGVO-konform
2. **Universal Device Support** — ESP32 UND Raspberry Pi UND Windows/Linux
3. **No-Code Automation** — Rules Engine + Dashboard Builder
4. **AI-Native (MCP)** — Als erstes IoT-System MCP-nativ
5. **Developer + Non-Developer** — API-first ABER auch UI-first nutzbar

**Wettbewerber-Schwächen die HUBEX nutzen kann:**
- **Balena**: Nur Container-Deployment, kein Device Management UI
- **Particle**: Cloud-only, teuer, kein Self-Hosted
- **ThingsBoard**: Komplex, Java-Monolith, schwer zu deployen
- **Home Assistant**: Smart Home Fokus, nicht für Custom IoT
- **AWS IoT**: Vendor Lock-in, Kosten explodieren bei Scale

**Revenue-Modell (Empfehlung):**
- Free Tier: 10 Devices, 1 User, Community Support
- Pro: 100 Devices, 5 Users, Priority Support — 29€/mo
- Enterprise: Unlimited, SSO/SAML, SLA, Custom Integrations — Custom Pricing
- Self-Hosted: Kostenlos (Community), Paid Support Subscription

---

## Aktualisierter Projektfahrplan

### Phase 1: CORE PLATFORM (Milestone 1-7) ✅ DONE
Alles bereits umgesetzt.

### Phase 2: UI REBOOT (Milestone 8) 🔄 IN PROGRESS
Aktuell bei Step 2 von 9.

### Phase 3: INTEGRATION & DEMO (Milestone 9-12) → wie geplant

### Phase 4: NEW — Plattform-Erweiterung (Milestone 13-19)

**Milestone 13: MCP Server Integration** — 8h
- Step 1 — MCP Tool Definitions (Device, Alert, Variable, OTA Tools) — 3h
- Step 2 — MCP Endpoint Layer + Auth — 3h
- Step 3 — MCP Client für externe Server — 2h

**Milestone 14: Provider/Signal System (C2)** — 12h
- Step 1 — Provider API (CRUD, Registration, Health) — 3h
- Step 2 — Signal Schema + Validation + Ingestion — 3h
- Step 3 — Provider Lifecycle (enable/disable/revoke) — 2h
- Step 4 — Built-in Providers (Webhook, Timer, MQTT) — 4h

**Milestone 15: Rules Engine (C3)** — 14h
- Step 1 — Rule Artifact Model (validate, version, activate, rollback) — 4h
- Step 2 — Signal → Rule Matching + Condition Evaluation — 4h
- Step 3 — Rule → Execution Pipeline (deterministic) — 3h
- Step 4 — Rule UI (create, test, monitor) — 3h

**Milestone 16: Universal Agent SDK (C2 Extension)** — 16h
- Step 1 — Agent Protocol Spec (HTTP + WebSocket) — 2h
- Step 2 — Python SDK Agent (RPi, Linux) — 4h
- Step 3 — Node.js SDK Agent — 3h
- Step 4 — OS Agent (System Telemetry, Service Management) — 4h
- Step 5 — Device Type Polymorph (mcu/os_agent/sdk_agent) — 3h

**Milestone 17: Bridge/Gateway Framework** — 10h
- Step 1 — Bridge Agent Architecture (Plugin System) — 3h
- Step 2 — Serial/UART Bridge Plugin — 2h
- Step 3 — Modbus RTU/TCP Bridge Plugin — 3h
- Step 4 — BLE Bridge Plugin — 2h

**Milestone 18: Advanced Observability (C4)** — 8h
- Step 1 — Trace/Timeline View — 3h
- Step 2 — Incident Management + Correlation — 3h
- Step 3 — Support Bundle Export — 2h

**Milestone 19: Dashboard Builder (C5/Custom UI)** — 16h
- Step 1 — Dashboard/Widget Model + API — 3h
- Step 2 — Widget Library (Metric, Chart, Status, Control) — 4h
- Step 3 — Drag & Drop Grid Editor — 5h
- Step 4 — Dashboard Sharing + Permissions — 2h
- Step 5 — Embed Mode (iframe-fähig) — 2h

### Phase 5: ENTERPRISE (Milestone 20-23) — Zukunft

**Milestone 20: Security Hardening v2** — 10h
- 2FA/MFA, API Keys, RBAC Roles, Session Management, Secrets Encryption

**Milestone 21: Admin Console (C7a)** — 8h
- Module Lifecycle UI, Policy Management, Provider Health Dashboard

**Milestone 22: Simulator/Testbench (C6)** — 10h
- Sim-Entities, Sim-Providers, Testbench Orchestration, Report Generation

**Milestone 23: Templates/Blueprints (C5)** — 8h
- Katalog, Installer, Preflight Checks, Rollback

**Milestone 24: Plugins Framework (C7c)** — 12h
- MIC v1 Lifecycle, Sandboxed Execution, Registry/Marketplace

**Milestone 25: Backup & Mobile (C7b + C7e)** — 8h
- Config Snapshots, Scheduled Backups, Mobile PWA/App

---

## Priorisierte Empfehlung: Nächste Schritte

1. **Milestone 8 fertig machen** (UI Reboot) — Aktuell wichtigste Basis
2. **Milestone 9** (ESP32 Demo) — Proof of Concept, zeigbar
3. **Milestone 13** (MCP) — Low Effort, High Value, Differenzierung
4. **Milestone 10** (CI/CD) — Stabilität
5. **Milestone 14** (Providers/Signals) — Enabler für Rules
6. **Milestone 15** (Rules Engine) — Core Feature
7. **Milestone 16** (Agent SDK) — Plattform erweitern
8. Rest nach Bedarf/Feedback
