# Projekt-Roadmap

> **Vision:** HubEx ist ein universeller Device Hub — nicht nur für Custom-Hardware (ESP32),
> sondern gleichwertig für Standard-Devices, API-Integrationen, Software-Agents und
> Protokoll-Bridges. Alles spricht miteinander. Alles ist grafisch ansprechend, intuitiv
> und lückenlos nachvollziehbar. Jede Architektur- und UI-Entscheidung muss für ALLE
> Device-Typen funktionieren, nicht nur für Custom-MCUs.

> **Design-Leitsatz:** Orientierung an n8n (Flow-UX, Daten-Sichtbarkeit),
> Home Assistant (Card-basiert, Entity-Status) und Grafana (Time-Series, Panels).
> Kein Feature ohne visuellen Mehrwert. Keine Seite ohne Empty State.
> Die Darstellung wächst mit der Komplexität — einfache Setups sehen einfach aus,
> komplexe Setups werden progressiv detaillierter, nie überladen.

> **UX-Kernprinzip:** Daten einbinden → sammeln → analysieren → darstellen → interagieren
> lassen. Alles so, dass es physisch vorstellbar bleibt und auf den ersten Blick
> aussieht, als könnte es jeder. Kontextuelles Arbeiten statt isolierte Seiten —
> von jedem Punkt aus weiterverketten, ohne Seitenwechsel.

> **Design-System:** "Warm Depth" — Amber/Gold Primary (#F5A623), Teal Accent (#2DD4BF),
> warme dunkle Hintergründe (#111110). Fonts: Satoshi (Display), Inter (Body),
> IBM Plex Mono (Data). Hexagonales Logo-Konzept. Vollständige Design Tokens,
> Component Library und Screen-Mockups vorhanden (brand_01–04 HTML-Dateien).

> **Architektur-Grundsätze:**
> - Device als Oberbegriff mit 4 Unterkategorien: Hardware, Service, Bridge, Agent
> - Semantisches Typsystem: Basis-Datentypen + semantische Typen mit Triggern, Viz, Einheiten
> - Bidirektional: Input UND Output gleichwertig (Read/Write/Read-Write Variablen)
> - Auto-Discovery standardmäßig an (Switch, kein Approval-Step)
> - Skalierung für Enterprise mitplanen, aber nicht premature optimieren
> - i18n-Foundation jetzt, Übersetzungen später
> - Branding-Entkopplung: Produktname, Logo, Farben zentral konfiguriert, nie hardcoded
> - Multi-User vollumfassend geplant, Umsetzung Ende der Roadmap
> - Export/Import als Grundlage für Templates und Marketplace

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

## Phase 3: Variable Data Hub ✅ ABGESCHLOSSEN

### Milestone 8c: Variable Stream Visualization Foundation ✅
> Variablen sind der zentrale Datenpunkt. Devices senden Telemetrie, die automatisch
> in typisierte Variablen fließt — jeder Stream wird passend visualisiert.

- [x] V1 — Backend CRUD + History
  - `display_hint` + `category` Spalten in VariableDefinition
  - `variable_history` Tabelle (BigInt, time-series, numeric_value denormalisiert)
  - `PATCH /variables/definitions/{key}` — editierbare Metadaten
  - `DELETE /variables/definitions/{key}` — echtes Löschen mit Cascade
  - `GET /variables/history` — Zeitreihe mit SQL-Downsampling
  - History-Recording nach jedem Value-Write (source: user/device/telemetry)
  - Alembic-Migration

- [x] V2 — Widget-Komponenten (Grafana/HA/n8n-inspiriert)
  - `lib/viz-types.ts` — VizType, VizDataPoint, VizWidgetProps, Farb-Palette
  - `lib/viz-resolve.ts` — resolveVizType(), DISPLAY_HINT_OPTIONS
  - `composables/useVariableHistory.ts` — Polling mit TimeRange-Selector
  - VizSparkline, VizLineChart, VizGauge, VizBoolIndicator, VizLogView,
    VizJsonViewer, VizMapView, VizImageView, VizWidget (Grafana-Panel-Container)

- [x] V3 — Variables.vue Full CRUD + Inline Viz
- [x] V4 — Telemetry Bridge + DeviceDetail
- [x] V5 — VariableStreams.vue + Navigation

### Milestone 8d: Data Hub — Lücken schließen ✅
- [x] Step 1 — History Retention Policy
- [x] Step 2 — DeviceDetail Variable-Panel: Inline-Sparklines
- [x] Step 3 — Variable-basierte Alert-Rules
- [x] Step 4 — Variable → Webhook Bridge
- [x] Step 5 — Telemetry Bridge: Nested Payload-Support
- [x] Step 6 — Streams: Device-Selektor statt UID-Eingabe
- [x] Step 7 — Bulk-Variable-Set

---

## Phase 4: Integration & Demo ✅ ABGESCHLOSSEN

### Milestone 9: Device Integration Demo ✅
- [x] Step 1 — ESP SDK Update (OTA check, edge config, heartbeat, variable bridge demo)
- [x] Step 2 — End-to-End Demo (ESP → Telemetry → Variable → Alert → Webhook → n8n)
- [x] Step 3 — Provisioning Flow (QR-Code Pairing, App-freundlich)
- [x] Step 4 — API-Device Demo (externe REST-API als virtuelles Device)
- [x] Step 5 — Standard-Device Connector (Shelly/Tasmota via MQTT)

### Milestone 10: CI/CD & Deployment ✅
- [x] Step 1 — GitHub Actions (test, build, lint, coverage)
- [x] Step 2 — Docker Production Compose (Traefik, SSL, PostgreSQL, Redis, backups)
- [x] Step 3 — One-Click Deploy Script (Linux, .env Generator)
- [x] Step 4 — Health-Check Dashboard (uptime, DB-connections, Redis-latency)

### Milestone 10.5: Automation Engine — Native If→Then Rules ✅
- [x] Step 1 — Backend: AutomationRule Model + CRUD API + Engine
- [x] Step 2 — Frontend: Automations Page — Visual If→Then Builder

### Milestone 11: n8n Integration ✅
- [x] Step 1 — n8n Webhook Templates
- [x] Step 2 — Custom n8n Node für HubEx
- [x] Step 3 — n8n Node: Variable-Stream als Datenquelle

### Milestone 12: Developer Docs ✅
- [x] Step 1 — API Docs Landing Page (Swagger / Redoc)
- [x] Step 2 — Getting Started Guide
- [x] Step 3 — ESP SDK Docs + Variable Bridge Docs
- [x] Step 4 — SDK/Integration Guide (Python Agent, n8n, Webhooks)

### Milestone 12.5: Pitch & Go-to-Market ✅
- [x] Step 1 — Pitch Deck (Partner/Investoren)
- [x] Step 2 — Product Landing Page
- [x] Step 3 — Competitive Analysis
- [x] Step 4 — Pricing Model

---

## Phase 5: UX-Überholung & Plattform-Fundament [todo]
> **Leitsatz dieser Phase:** Bevor neue Features gebaut werden, muss das Fundament
> für gute UX stehen. Design System, Typsystem, Branding, i18n, Onboarding.
> Alles was danach kommt, baut darauf auf.

### Milestone 13: Design System Reboot [done] ✅
> "Warm Depth" Design System durchgängig implementiert.

- [x] Step 1 — Design Tokens Migration
  - `style.css`: Komplettes CSS Custom Properties System (--bg-*, --primary, --accent, --status-*, --border-*, --shadow-*, --radius-*, --duration-*, --font-*, --cat-*)
  - Dark + Light Theme, Noise-Texture Overlay, Google Fonts (Inter, IBM Plex Mono)
  - `tailwind.config.ts`: Farben, Fonts, Schatten referenzieren CSS-Variablen
  - Backward-Compat: --accent-cyan → --accent, --accent-amber → --primary

- [x] Step 2 — Branding-Abstraction Layer
  - `lib/branding.ts`: productName, tagline, logoSVG (Hexagon), Farben
  - `components/BrandLogo.vue`: Reusable Logo mit size/showText Props
  - DefaultLayout, AuthLayout, Landing, Dashboard: branding.productName statt Hardcoded

- [x] Step 3 — i18n Foundation
  - vue-i18n installiert, `i18n/index.ts` Setup mit localStorage-Persistence
  - `i18n/locales/en.ts` + `de.ts`: Nav, Common, Auth, Devices, Variables, Alerts, Automations, Dashboard, Settings, Health, Empty States, Time
  - Sidebar-Labels via `$t('nav.*')`, Settings: Sprach-Umschalter (EN/DE)

- [x] Step 4 — Component Library Migration
  - 17 UI Components auf Warm Depth Tokens migriert
  - UButton: Primary=Amber mit Glow, Focus=Primary-Ring
  - UCard: Hover-Glow, UBadge: Category-Prop (hardware/service/bridge/agent)
  - UInput/USelect: Amber Focus-Ring, UToggle: Primary=Amber
  - UTab: Active=Primary, UTable: Sort=Primary, CommandPalette: Active=Primary

- [x] Step 5 — Screen-by-Screen Redesign
  - 79 --accent-cyan Referenzen durch --primary ersetzt (9 Pages + 2 Layouts)
  - Konsistente Header (h1 + Subtitle) auf Alerts, Automations, Settings, SystemHealth
  - Status-Tokens (--status-ok/warn/bad) in SystemHealth, Alerts
  - Device-Kategorie-Farben (--cat-*) in useDevices

### Milestone 14: Semantisches Typsystem [todo] ← AKTUELL
> Variablen bekommen echte Typen mit Validierung, Einheiten, Default-Visualisierungen
> und automatischen Trigger-Templates. Das ist das Fundament für Dashboard Builder,
> Automationen und Device-Onboarding.

- [ ] Step 1 — Backend: SemanticType Model + CRUD API
  > Zweistufiges System: Basis-Datentyp (bool/int/float/string/json) +
  > Semantischer Typ (Temperatur, GPS, Geschwindigkeit, etc.)
  - `SemanticType` Tabelle: name, base_type, unit, unit_symbol, value_schema (JSON),
    min_value, max_value, default_viz_type, icon, color, is_builtin, is_custom
  - CRUD API: `GET/POST/PATCH/DELETE /api/v1/types/semantic`
  - `direction` Feld auf VariableDefinition: read_only / write_only / read_write
  - Migration: bestehende display_hint + value_type → SemanticType-Referenz

- [ ] Step 2 — Grundbibliothek: 20 Built-in Typen
  > Werden beim ersten Start automatisch angelegt (Seed-Data).
  - **Numerisch:** Temperatur (°C/°F), Luftfeuchtigkeit (%), Druck (hPa),
    Spannung (V), Strom (A), Leistung (W), Energie (kWh), Prozent/Batterie (%),
    Geschwindigkeit (km/h), Helligkeit (lux), Lautstärke (dB), Winkel (°)
  - **Komplex:** GPS-Position (json: {lat, lng, alt?}), Farbe (string: #RRGGBB)
  - **Diskret:** Boolean/Schalter, Zähler/Counter (int, monoton steigend)
  - **Text:** Status-String, Bild-URL
  - Jeder Typ definiert: default_viz_type, sinnvolle min/max, Icon, Farbe

- [ ] Step 3 — Trigger-Templates pro Typ
  > Jeder semantische Typ bringt seine verfügbaren Trigger-Operationen mit.
  - Basis-Trigger (alle numerischen Typen): gt, gte, lt, lte, eq, ne, rate_of_change
  - Boolean: changed_to_true, changed_to_false, toggled
  - GPS: entered_geofence, exited_geofence, speed_exceeded, distance_from_point
  - Temperatur/Prozent: zusätzlich range_exit (Wert verlässt definierten Bereich)
  - Counter: increment_exceeded (Zähler steigt um > X in Zeitraum Y)
  - `TriggerTemplate` Tabelle: semantic_type_id, trigger_name, config_schema,
    description, icon
  - API: `GET /api/v1/types/semantic/{id}/triggers`

- [ ] Step 4 — Einheiten-Konvertierung
  > Devices senden in einer Einheit, User sehen in einer anderen.
  - `UnitConversion` Tabelle: from_unit, to_unit, formula (z.B. "value * 9/5 + 32")
  - Konvertierung auf Display-Ebene (Frontend), nicht auf Storage-Ebene
  - User-Preference: bevorzugte Einheit pro semantischem Typ (z.B. "ich will °F")
  - Fallback: Anzeige in Originaleinheit wenn keine Konvertierung definiert

- [ ] Step 5 — Frontend: Type Management UI
  - Seite `/settings/types` — Übersicht aller semantischen Typen (Built-in + Custom)
  - Create-Modal für Custom Types: Name, Basis-Typ, Einheit, Bereich, Icon, Default-Viz
  - Trigger-Templates sichtbar pro Typ
  - Preview: "So würde eine Variable dieses Typs aussehen" (Mini-Widget)
  - Built-in Typen: read-only, aber kopierbar als Vorlage für Custom

### Milestone 15: Device Experience Reboot [todo]
> Devices bekommen eine reichere Identität, ein besseres Onboarding und
> kontextuelle Verbindungen zu allem was daran hängt.

- [ ] Step 1 — Device Identity erweitern
  > Jedes Device bekommt mehr als nur UID und Name.
  - DB: `category` Enum (hardware/service/bridge/agent), `icon` (string/emoji),
    `location_name` (Freitext), `location_lat`/`location_lng` (optional GPS),
    `location_hierarchy_id` (FK, optional)
  - `LocationHierarchy` Tabelle (optional): id, parent_id, name, level_type
    (building/floor/room/zone), Selbst-Referenz für Baumstruktur
  - Standort ist NIE Pflicht — Maker mit Arduino brauchen das nicht,
    Enterprise mit Liegenschaften schon
  - API: PATCH Device mit allen neuen Feldern

- [ ] Step 2 — Device Cards Redesign
  > Device-Liste zeigt auf einen Blick: was ist es, wo ist es, was tut es.
  - Jede Card zeigt: Sprechender Name, Kategorie-Badge (Hardware/Service/Bridge/Agent)
    mit Icon und Farbe, Status-Dot (Online grün pulsierend, Offline rot statisch),
    Standort (wenn gesetzt), letzte Aktivität ("23.5°C · 2 min ago"),
    Gruppenzugehörigkeit, Anzahl Variablen
  - Referenz: `brand_04_screen_device.html` Device-Liste
  - Ansichtsmodi: Cards (Grid) und kompakte Tabelle (Liste)
  - Filter: nach Kategorie, Status, Gruppe, Standort

- [ ] Step 3 — Inline-Gruppierung
  > Gruppierung direkt in der Device-Liste, nicht auf separater Entities-Seite.
  - Mehrfachauswahl (Checkboxen) → Toolbar: "Zur Gruppe hinzufügen"
  - Drag & Drop von Devices zwischen Gruppen (wenn Gruppen-Ansicht aktiv)
  - Schnell-Aktion: Rechtsklick → "Neue Gruppe aus Auswahl"
  - Entities/Groups-Seite bleibt für Detailmanagement, aber Grundaktionen
    sind direkt in der Device-Liste möglich

- [ ] Step 4 — Universal "Add Device" Wizard
  > Ein geführter Flow für JEDE Art von Anbindung.
  - Schritt 1: "Was willst du anbinden?" — 4 große Kacheln:
    🔧 Hardware (ESP32, Shelly, physische Sensoren)
    ☁️ Service (REST-API, Wetter, externe Dienste)
    🔗 Bridge (MQTT, Modbus, BLE Protokoll-Übersetzer)
    🖥️ Agent (Software auf Rechner, RPi, Windows-Service)
  - Schritt 2: Typspezifischer Setup (je nach Auswahl)
    - Hardware: Pairing-Code/QR oder manuelle UID-Eingabe
    - Service: URL, Auth (API-Key/OAuth/None), Poll-Intervall, Test-Request
    - Bridge: Protokoll-Config (MQTT Broker URL, Topics, Credentials)
    - Agent: SDK-Download-Link + Pairing-Token generieren
  - Schritt 3: "Verbindung testen" — visuelles Feedback ob Daten ankommen
  - Schritt 4: Zusammenfassung + "Device benennen, Icon wählen, Standort setzen"

- [ ] Step 5 — Auto-Discovery
  > Wenn ein Device zum ersten Mal Telemetrie sendet, erkennt HubEx die Felder
  > automatisch und legt Variable-Definitionen an.
  - Standardmäßig AN (pro Device als Toggle abschaltbar)
  - Bei eingehender Telemetrie: Felder extrahieren, Basis-Typ inferieren
    (Zahl → float, true/false → bool, String → string, Objekt → json)
  - Semantischen Typ vorschlagen: "temperature" → Typ Temperatur, "humidity" →
    Typ Luftfeuchtigkeit, "battery" → Typ Prozent (Keyword-Matching + Heuristik)
  - Variablen werden automatisch angelegt, Notification an User:
    "3 neue Variablen erkannt: temperature (Temperatur), humidity (Luftfeuchtigkeit),
    battery (Prozent)"
  - User kann nachträglich Typ ändern, Variable löschen oder Auto-Discovery ausschalten

- [ ] Step 6 — Device Detail: "Platinen-Ansicht"
  > Auf der Device-Detail-Seite: visuell sehen, was an diesem Device hängt.
  - Mini-Flow-Graph: Device → [Variable A, B, C] → [Alert X auf A] →
    [Automation Y] → [Webhook Z] → [n8n]
  - Kontextuelle Aktionen: Von jeder Variable "Alert erstellen",
    "Automation erstellen", "Im Dashboard anzeigen"
  - Toggle: "Technische Ansicht" für Power-User (raw JSON, UID, Firmware-Version,
    Connection-Details, Telemetry-Log) — standardmäßig verborgen
  - Empty State mit Vorschlägen: "Dieses Device hat noch keine Variablen —
    sende Telemetrie oder erstelle manuell eine Variable"

### Milestone 16: Kontextuelles Arbeiten [todo]
> Von überall aus weiterverketten — der "rote Faden" durch die ganze Plattform.
> Kein Navigieren durch 8 Menüs, sondern: Klick → nächster Schritt → fertig.

- [ ] Step 1 — Connect-Panel (Slide-Over)
  > Jedes Element (Variable, Device, Automation, Alert) bekommt ein ausklappbares
  > Seitenpanel: "Was hängt dran? Was kann ich anhängen?"
  - Panel zeigt: bestehende Verbindungen als Mini-Liste
  - "+"-Button: "Alert erstellen", "Automation erstellen", "Zum Dashboard hinzufügen",
    "Webhook einrichten" — kontextabhängig, nur was Sinn macht
  - Klick auf "+" öffnet Inline-Formular IM Panel — kein Seitenwechsel
  - Kontext bleibt erhalten: Variable X ist vorausgewählt, User muss nur
    die Bedingung/Aktion konfigurieren

- [ ] Step 2 — Kontextmenüs
  > Rechtsklick / "..."-Menü auf jedes Element zeigt sinnvolle nächste Aktionen.
  - Variable: "Alert wenn Schwellwert", "Automation erstellen", "Im Dashboard",
    "History anzeigen", "Typ ändern"
  - Device: "Variablen ansehen", "Alert-Regeln", "Automationen", "Standort setzen",
    "Zur Gruppe hinzufügen"
  - Automation: "Testen", "Deaktivieren", "Flow anzeigen", "Duplizieren"
  - Alert: "Bestätigen", "Stummschalten", "Regel bearbeiten", "Device anzeigen"

- [ ] Step 3 — Proaktive Empty States
  > Leere Zustände geben Vorschläge statt nur "Nichts hier".
  - Variable ohne Alert: "Möchtest du benachrichtigt werden, wenn dieser Wert
    einen Schwellwert überschreitet? → Alert erstellen"
  - Device ohne Variablen: "Sende Telemetrie oder erstelle manuell eine Variable"
  - Dashboard leer: "Füge dein erstes Widget hinzu — Vorschlag basierend auf
    deinen aktiven Variablen"
  - Automation-Seite leer: "Erstelle deine erste Automation — z.B. 'Wenn Temperatur
    > 30°C, dann sende Notification'"

### Milestone 17: Realtime & Notifications [todo]
> WebSocket-Layer für Echtzeit-Updates und ein zentrales Notification Center.

- [ ] Step 1 — WebSocket Layer
  > Basis für Echtzeit-Updates in UI, ersetzt Polling.
  - FastAPI WebSocket Endpoint mit JWT-Auth
  - Redis Pub/Sub für Multi-Instance-Koordination (von Anfang an!)
  - Channels: device_events, variable_stream, alert_events, automation_events
  - Frontend: `useWebSocket` Composable mit Auto-Reconnect
  - VariableStreams → Live-Updates statt 15s Polling

- [ ] Step 2 — Notification Center
  > Zentrale Inbox für alle wichtigen Events — wie Handy-Notifications.
  - `Notification` Tabelle: type, severity, title, message, entity_ref,
    read_at, created_at, user_id
  - Typen: device_offline, alert_fired, automation_failed, auto_discovery,
    system_warning
  - UI: Glocke im Header mit Badge-Count, Dropdown-Panel mit Notification-Liste
  - Quick-Actions pro Notification: "Bestätigen", "Zum Device", "Stummschalten"
  - WebSocket-Push für neue Notifications (Echtzeit)

- [ ] Step 3 — Notification Preferences
  - Pro User: welche Event-Typen als Notification, welche per Email, welche still
  - Pro Alert-Rule: Notification-Kanal konfigurierbar
  - Mute-Funktion: Device/Gruppe/Alert-Rule temporär stummschalten

- [ ] Step 4 — Email-Notification-Dispatch
  - SMTP-Integration (konfigurierbar in Settings)
  - Email-Templates: Alert gefeuert, Device offline, Daily Summary
  - Rate-Limiting: max 1 Email pro Alert-Rule pro Stunde (konfigurierbar)

### Milestone 18: Dashboard Builder [todo]
> DAS zentrale Visualisierungs- und Steuerungstool. Ersetzt/absorbiert VariableStreams.
> Direkte Abhängigkeit von M8c (VizWidget) und M14 (Typsystem).

- [ ] Step 1 — Dashboard/Widget Model + CRUD API
  - `Dashboard` Tabelle: name, description, layout_config (JSON), is_default,
    owner_id, org_id, sharing_mode (private/org/public)
  - `DashboardWidget` Tabelle: dashboard_id, widget_type (aus VizType + neue),
    data_source_config (JSON), position (grid x/y/w/h), display_config (JSON)
  - CRUD API: Dashboards + Widgets
  - Widget-Types: alle bestehenden VizTypes + Steuerungs-Widgets (siehe Step 3)

- [ ] Step 2 — Drag & Drop Grid Editor
  - vue-grid-layout Integration
  - Widgets hinzufügen: "+" → Typ wählen → Datenquelle wählen → platzieren
  - Widgets verschiedener Devices auf einem Dashboard mischbar
  - Resize, Reorder, Delete per Drag & Drop
  - "Edit Mode" Toggle: im View-Mode keine Drag-Handles sichtbar
  - Auto-Save der Layout-Änderungen

- [ ] Step 3 — Steuerungs-Widgets
  > Nicht nur Anzeige, auch Interaktion. Für write-fähige Variablen.
  - Toggle-Switch: für Boolean (read_write)
  - Slider: für numerische Werte (read_write) mit min/max aus SemanticType
  - Button: für Aktionen ("Relais AN", "Reset Counter")
  - Farbpicker: für Farb-Variablen (read_write)
  - Eingabefeld: für Zahlenwert direkt setzen
  - Widget-Typ wird automatisch aus SemanticType + Direction vorgeschlagen

- [ ] Step 4 — Auto-Suggest bei Widget-Erstellung
  > "Wähle eine Datenquelle" → HubEx schlägt automatisch den passenden Widget-Typ vor.
  - Temperatur → Line Chart, Prozent → Gauge, GPS → Map,
    Boolean → Toggle/Status-Dot, Counter → Bar Chart
  - Vorschlag ist änderbar — User kann jeden Widget-Typ für jede Variable wählen
  - "Empfohlen"-Badge auf dem vorgeschlagenen Typ

- [ ] Step 5 — Dashboard-Templates
  > Vorgefertigte Layouts als Schnelleinstieg.
  - Built-in: "Klimaüberwachung", "Server-Monitoring", "Flottentracking",
    "Energie-Dashboard", "Allgemein"
  - Template enthält: Layout + Widget-Platzhalter + empfohlene Datenquellen
  - User wählt Template → mappt eigene Variablen auf die Platzhalter → fertig
  - Custom Templates speichern: eigenes Dashboard als Template exportieren

- [ ] Step 6 — VariableStreams Migration
  > Bestehende Streams-Seite wird zum "Quick View" innerhalb des Dashboard Builders.
  - `/variables/streams` redirected auf Default-Dashboard oder wird Schnellansicht
  - Alle bestehenden Stream-Funktionalität im Dashboard Builder verfügbar
  - TimeRange-Selector, Auto-Refresh, Fullscreen — alles übernommen

- [ ] Step 7 — Dashboard Sharing + Embed
  - Sharing: per Link (read-only), per Org, per Capability
  - Embed Mode: iframe mit Public Link, Kiosk-Modus (keine Sidebar/Header)
  - Export: Dashboard als PNG/PDF Screenshot

### Milestone 19: Unified Automation Engine [todo]
> Zusammenlegung der bestehenden Automation Engine (M10.5) mit der geplanten
> Rules Engine (M16 alt). Ein System, nicht zwei. Darstellung wächst mit Komplexität.

- [ ] Step 1 — Typsystem-Integration
  > Trigger sind nicht mehr hardcoded, sondern kommen aus dem SemanticType.
  - Bestehende Trigger (variable_threshold, variable_geofence, device_offline,
    telemetry_received) als Built-in Trigger-Templates migrieren
  - Neue Trigger laden automatisch aus SemanticType.trigger_templates
  - UI: Trigger-Picker zeigt nur Trigger die zum gewählten Variablen-Typ passen

- [ ] Step 2 — Ketten & Sequenzen
  > Multi-Step-Automationen: IF → THEN → THEN → THEN
  - `AutomationStep` Tabelle: rule_id, step_order, action_type, action_config,
    delay_seconds (optional)
  - Kette: Step 1 ausgeführt → Delay → Step 2 → Delay → Step 3
  - Abbruchbedingung: "Stoppe Kette wenn Variable X sich ändert"
  - Backend: Step-Executor mit Status-Tracking pro Step

- [ ] Step 3 — Bedingungsgruppen (AND/OR)
  - Trigger-Conditions können gruppiert werden:
    "WENN (Temp > 40 UND Fenster == geschlossen) ODER (Alarm == aktiv)"
  - `ConditionGroup` mit Operator (AND/OR) und verschachtelten Conditions
  - UI: Visueller Condition-Builder mit Drag & Drop Gruppierung

- [ ] Step 4 — Verzweigungen (If/Else)
  - "WENN Temperatur > 40 → Aktion A, SONST → Aktion B"
  - Step kann Typ "branch" haben mit true_action und false_action
  - UI: Verzweigung als visueller Split im Flow

- [ ] Step 5 — Visueller Automations-Builder
  > Darstellung wächst mit Komplexität.
  - Einfache Automation (1 Trigger, 1 Action): kompakte Card-Ansicht wie bisher
  - Ketten (2+ Steps): vertikaler Flow mit Schritten und Pfeilen
  - Verzweigungen: Flow mit Split/Merge Darstellung
  - Komplexe Automationen: Mini-Flow-Graph (read-only Version der n8n-Ansicht)
  - Referenz: `brand_04_screen_automations.html`

- [ ] Step 6 — Externe Flows sichtbar machen
  > Wenn eine Automation per Webhook an n8n geht, wird das in HubEx sichtbar.
  - Webhook-Action zeigt "→ extern (n8n)" mit Link
  - Eingehende n8n-Aktionen (Variable setzen via API) werden als
    "← extern" im Automation-Flow angezeigt
  - Kein aktives Tracking von n8n-Flows, sondern passive Sichtbarkeit
    basierend auf Webhook-Dispatches und API-Calls

### Milestone 20: System-Übersicht & Mission Control [todo]
> Dashboard wird echtes Mission Control — nicht nur Charts, sondern Überblick.

- [ ] Step 1 — Dashboard Redesign: System Health
  - Devices Online/Offline Ratio mit Trend
  - Aktive Alerts nach Severity (Critical/Warning/Info)
  - Letzte Automation-Ausführungen (Erfolg/Fehler)
  - Datenvolumen (Telemetrie-Events heute vs. Durchschnitt)
  - Quick-Actions: "Letzte Alerts", "Offline Devices", "Fehlgeschlagene Automationen"

- [ ] Step 2 — Fokusbasierte Flow-Ansicht
  > "Die Platine mit den Kabeln" — ein ausgewähltes Element in der Mitte,
  > drumherum alles was daran hängt.
  - Aufrufbar von: Device-Detail, Variable-Detail, Automation-Detail
  - Darstellung: Zentrales Element → verbundene Elemente als Knoten mit Linien
  - Klick auf Knoten → Navigation zum Detail oder Focus-Wechsel
  - Read-only, nicht editierbar (editierbare Version → Phase 7)

- [ ] Step 3 — System Map (Gesamtansicht)
  > Alle Devices, Variablen, Automationen, Webhooks auf einer Seite.
  - Read-only Graph-Ansicht
  - Filter: nach Gerät, nach Gruppe, nach Automation-Kette
  - Zoom/Pan, Minimap
  - Farb-Kodierung: Online/Offline, Severity, Kategorie

---

## Phase 6: Erweiterung & Anbindung [todo]

### Milestone 21: n8n Deep Integration [todo]
> Audit und Optimierung der n8n-Anbindung, damit das Typsystem und alle
> neuen Features sauber durchgereicht werden.

- [ ] Step 1 — n8n Node Update: Semantische Typen
  - n8n Node kennt semantische Typen: Trigger-Events enthalten Typ-Info
  - Variable-Set Action: Typ-Validierung in n8n
  - Auto-Discovery Events als n8n Trigger verfügbar

- [ ] Step 2 — n8n Node: Dashboard & Automation Integration
  - n8n kann Dashboard-Widgets setzen/aktualisieren
  - n8n kann Automationen aktivieren/deaktivieren
  - Bidirektionale Status-Synchronisation

- [ ] Step 3 — n8n Kompatibilitäts-Tests
  - Automatisierte Tests: alle n8n-Node-Operationen gegen aktuelle API
  - Migrations-Guide: wenn API-Änderungen Breaking Changes für n8n sind
  - CI: n8n-Node-Tests in GitHub Actions Pipeline

### Milestone 22: MCP Server Integration [todo]
- [ ] Step 1 — MCP Tool Definitions (Device, Alert, Variable, OTA, Metrics, Automation Tools)
- [ ] Step 2 — MCP Endpoint Layer + Auth Integration
- [ ] Step 3 — MCP Client für externe Server (Enrichment, AI)
- [ ] Step 4 — MCP-based AI Agent Demo ("set variable temperature_threshold to 75")

### Milestone 23: Universal Agent SDK [todo]
> Agents sind gleichwertige Device-Typen neben MCUs, API-Devices und Standard-Devices.
- [ ] Step 1 — Agent Protocol Spec (HTTP + WebSocket, handshake, heartbeat)
- [ ] Step 2 — Python SDK Agent (RPi, Linux, system telemetry → variables)
- [ ] Step 3 — Node.js SDK Agent
- [ ] Step 4 — OS Agent Features (service mgmt, remote shell, config push via Variables)
- [ ] Step 5 — Windows Agent + Installer/Service

### Milestone 24: Bridge/Gateway Framework [todo]
- [ ] Step 1 — Bridge Agent Architecture (plugin system, auto-discovery)
- [ ] Step 2 — Serial/UART Bridge Plugin
- [ ] Step 3 — Modbus RTU/TCP Bridge Plugin (industrial sensors → Variables)
- [ ] Step 4 — BLE Bridge Plugin
- [ ] Step 5 — CAN Bus / I2C / SPI Bridge Plugin

### Milestone 25: Onboarding & Getting Started [todo]
> Neuer User sieht nicht "leeres Dashboard", sondern wird geführt.

- [ ] Step 1 — Welcome Wizard (skipbar)
  - Overlay-basiert, max 4 Schritte:
    1. "Willkommen bei [Produktname]"
    2. "Verbinde dein erstes Device" → Add Device Wizard
    3. "Sieh deine ersten Daten" → Variable-Ansicht
    4. "Baue dein erstes Dashboard" → Dashboard Builder
  - Jeder Schritt mit "Skip" und "Tutorial nochmal starten" in Settings
  - Fortschritt gespeichert pro User

- [ ] Step 2 — Demo-Datensatz
  - Per Klick ladbar: "Demo-Daten laden" in Settings
  - Simuliertes Setup: 3 Devices (Temp-Sensor, API-Service, MQTT-Bridge),
    6 Variablen, 2 Automationen, 1 Dashboard
  - Zeigt sofort, wie HubEx aussieht wenn es gefüllt ist
  - Entfernbar: "Demo-Daten löschen" Button

---

## Phase 7: Enterprise & Advanced [todo]

### Milestone 26: Security Hardening v2 [todo]
- [ ] Step 1 — 2FA/MFA (TOTP, WebAuthn)
- [ ] Step 2 — API Key Management (service-to-service auth)
- [ ] Step 3 — RBAC Roles (admin, operator, viewer, custom)
- [ ] Step 4 — Session Management UI + Device Token Rotation

### Milestone 27: Skalierungs-Grundlagen [todo]
> Vorbereitung für Enterprise-Scale (tausende bis Millionen Devices).
- [ ] Step 1 — variable_history Partitioning (zeitbasiert, monatlich)
  > PostgreSQL native Partitioning oder TimescaleDB Extension evaluieren
- [ ] Step 2 — Telemetrie-Ingestion Pipeline
  > Bei hohem Volumen: Message Queue (Redis Streams oder Celery) vor DB-Write
- [ ] Step 3 — Automation-Engine Worker Pool
  > Bestehenden asyncio-Loop abstrahieren für spätere Celery/Worker-Migration
- [ ] Step 4 — Horizontal Scaling Documentation
  > Docker Compose → Multi-Instance hinter Load Balancer, Redis-koordiniert

### Milestone 28: Advanced Observability [todo]
- [ ] Step 1 — Trace/Timeline View (execution traces, event correlation)
- [ ] Step 2 — Incident Management + Cross-Entity Correlation
- [ ] Step 3 — Support Bundle Export (diagnostics, config snapshot)
- [ ] Step 4 — Variable Anomaly Detection (ML-basiert, z-score, threshold learning)

### Milestone 29: Export/Import & Templates [todo]
> Grundlage für Marketplace und Konfigurationsmanagement.
- [ ] Step 1 — Export/Import Format definieren (JSON-basiert)
  > Exportierbar: Dashboards, Automationen, Variable-Definitionen,
  > semantische Typen, Device-Konfigurationen
- [ ] Step 2 — Template Catalog (browseable, searchable, tagged)
  > Templates bündeln Variable-Definitionen + Dashboard + Automationen
- [ ] Step 3 — Template Installer (preflight checks, dependency resolution)
- [ ] Step 4 — Config-Versionierung (Automation-Änderungen, Dashboard-Layouts)
  > Rollback bei Fehlern möglich
- [ ] Step 5 — Marketplace-Grundstruktur (Catalog, Upload, Download)

### Milestone 30: Admin Console [todo]
- [ ] Step 1 — Module Lifecycle UI (enable/disable/revoke, dependency view)
- [ ] Step 2 — Policy Management (capability policies, plan enforcement)
- [ ] Step 3 — Provider Health Dashboard + System Status

### Milestone 31: Multi-User Collaboration [todo]
> Vollumfassend, aber ganz am Ende der Roadmap.
- [ ] Step 1 — Rollen-basierte Sichtbarkeit (wer sieht welches Dashboard/Device)
- [ ] Step 2 — Aktivitäts-Feed ("Max hat Alert-Rule X geändert")
- [ ] Step 3 — Gleichzeitige Bearbeitung (Conflict Resolution bei Dashboard-Edits)
- [ ] Step 4 — Team-Dashboards vs. persönliche Dashboards

### Milestone 32: Plugins Framework [todo]
- [ ] Step 1 — Plugin Manifest + Lifecycle
- [ ] Step 2 — Sandboxed Plugin Execution (capability-gated)
- [ ] Step 3 — Plugin Registry/Marketplace (catalog, versioning, revocation)
- [ ] Step 4 — Plugin SDK + Developer Guide

### Milestone 33: Simulator/Testbench [todo]
- [ ] Step 1 — Sim-Entities + Sim-Providers (virtual devices, mock signals)
- [ ] Step 2 — Testbench Orchestrator (Given → Trigger → Expected Trace)
- [ ] Step 3 — Report Generation (pass/fail, coverage, CI integration)

### Milestone 34: Backup & Mobile [todo]
- [ ] Step 1 — Config/State Snapshot (policies, schedules, export/import)
- [ ] Step 2 — Scheduled Backups (cron, retention, S3/local)
- [ ] Step 3 — Mobile PWA (responsive dashboard, push notifications)

### Milestone 35: Data & Analytics [todo]
- [ ] Step 1 — Telemetry Time-Series Aggregation (ergänzt variable_history)
- [ ] Step 2 — Data Export (CSV, JSON, API bulk) für variable_history + telemetry
- [ ] Step 3 — Advanced Analytics Charts (Trend, Comparison, Heatmap via VizWidget)
- [ ] Step 4 — Device Provisioning Profiles (batch onboarding)

### Milestone 36: Editierbare Flow-Ansicht [todo]
> Die System Map wird editierbar — n8n-Style Flow Editor für das gesamte System.
> Ganz am Ende der Roadmap, da sehr aufwändig.
- [ ] Step 1 — Flow Editor Canvas (Nodes + Edges, Zoom/Pan)
- [ ] Step 2 — Node-Typen: Device, Variable, Trigger, Action, Webhook, External
- [ ] Step 3 — Edge-Erstellung: Verbindungen ziehen zwischen Nodes
- [ ] Step 4 — Inline-Konfiguration: Node anklicken → Settings direkt im Canvas
- [ ] Step 5 — Flow-Deployment: Änderungen im Canvas → Automationen/Alerts erstellen

---

## Abhängigkeits-Graph (vereinfacht)

```
Phase 1-4 (Core + UI + Data + Integration) ✅
  │
  └─► Phase 5: UX-Überholung & Fundament
        │
        ├─► M13 (Design System Reboot) — ZUERST, alles andere baut darauf auf
        │     └─► M14 (Typsystem) — braucht neue UI-Komponenten
        │           ├─► M15 (Device Experience) — braucht Typsystem für Auto-Discovery
        │           ├─► M18 (Dashboard Builder) — braucht Typsystem für Auto-Suggest
        │           └─► M19 (Automation Engine) — braucht Typsystem für Trigger-Templates
        │
        ├─► M16 (Kontextuelles Arbeiten) — parallel zu M15, baut auf neuen Components auf
        ├─► M17 (Realtime) — WebSocket unabhängig, Notifications brauchen neues Design
        └─► M20 (System-Übersicht) — braucht M17 (Realtime) + M18 (Dashboard Builder)
              │
              └─► Phase 6: Erweiterung
                    ├─► M21 (n8n Deep) — braucht M14 (Typsystem) + M19 (Automations)
                    ├─► M22 (MCP) — unabhängig
                    ├─► M23 (Agent SDK) — braucht M15 (Device Wizard)
                    ├─► M24 (Bridges) — braucht M23 (Agent SDK)
                    └─► M25 (Onboarding) — braucht M15 (Wizard) + M18 (Dashboard)
                          │
                          └─► Phase 7: Enterprise
                                ├─► M26 (Security) — unabhängig
                                ├─► M27 (Skalierung) — unabhängig
                                ├─► M29 (Export/Templates) — braucht M14 + M18 + M19
                                ├─► M31 (Multi-User) — braucht M26 (RBAC)
                                └─► M36 (Flow Editor) — braucht M20 (System Map)
```

---

## Nächste 5 Sprints (Priorität)

| Sprint | Milestone | Fokus | Abhängigkeit |
|--------|-----------|-------|--------------|
| **Sprint 1** | M13 Steps 1-3 | Design Tokens + Branding + i18n Foundation | — |
| **Sprint 2** | M13 Steps 4-5 | Component Library + Screen Redesign | Sprint 1 |
| **Sprint 3** | M14 Steps 1-3 | Typsystem Backend + Grundbibliothek + Triggers | Sprint 2 |
| **Sprint 4** | M14 Steps 4-5 + M15 Steps 1-3 | Typsystem Frontend + Device Identity + Gruppierung | Sprint 3 |
| **Sprint 5** | M15 Steps 4-6 + M16 | Device Wizard + Auto-Discovery + Kontextuelles Arbeiten | Sprint 4 |
