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

  SIDEBAR-HIERARCHIE (Lücke 1):
  - Sidebar in 3 Gruppen neu strukturieren (auf-/zuklappbar):
    OBEN (immer sichtbar): Dashboard, Devices, Dashboards-Builder
    MITTE ("Daten & Logik", zuklappbar): Variables, Automations, Alerts
    UNTEN ("System", zuklappbar): Settings, API Docs, Webhooks, Events/Audit
  - Prominenter "+ Neu" Button ganz oben → Universal-Wizard
  - Default: Oben offen, Rest zugeklappt für neue User
  - Zustand per User-Preference speichern
  - Kontextuelles Dimming: OTA wenn keine Hardware-Devices → ausgegraut, nicht versteckt

  SETTINGS-NEUSTRUKTURIERUNG (Lücke 5):
  - Akkordeon-Sektionen: Profil & Account | Organisation & Team |
    Geräte & Daten | Benachrichtigungen | Darstellung | Entwickler | System
  - Suchfeld oben: "Einstellungen durchsuchen..."

  NOTIZ Responsive Breakpoints (Lücke 10):
  - Design Tokens definieren: --breakpoint-mobile: 640px,
    --breakpoint-tablet: 1024px, --breakpoint-desktop: 1440px
  - Alle neuen Komponenten: keine fixen Pixel-Breiten
  - Mobile-Implementierung kommt in M34 (PWA)

  NOTIZ OTA dimmen (Lücke 8):
  - OTA/Firmware in Sidebar: ausgegraut wenn keine Hardware-Devices
  - Nicht versteckt, aber visuell zurückgenommen
  - Bei Klick: Empty State mit Erklärung

### Milestone 14: Semantisches Typsystem [done] ✅
> Zweistufiges Typsystem: Basis-Datentyp + Semantischer Typ mit Triggern, Viz, Einheiten.

- [x] Step 1 — Backend: SemanticType Model + CRUD API
  - `SemanticType`, `TriggerTemplate`, `UnitConversion` Tabellen + Alembic-Migration
  - 7 API-Endpoints: `GET/POST/PATCH/DELETE /api/v1/types/semantic` + triggers + conversions
  - `direction` (read_only/write_only/read_write) + `semantic_type_id` auf VariableDefinition
  - Capabilities: `types.read`, `types.write`

- [x] Step 2 — Grundbibliothek: 20 Built-in Typen
  - `app/scripts/seed_semantic_types.py` — idempotentes Seed-Script
  - 20 Typen: temperature, humidity, pressure, voltage, current, power, energy, percent,
    battery, speed, brightness, volume_db, angle, gps_position, color_hex, boolean_switch,
    counter, status_string, image_url, generic_number

- [x] Step 3 — Trigger-Templates pro Typ (114 Templates)
  - Numerisch: gt, gte, lt, lte, eq, ne, range_exit (7 pro Typ)
  - Temperature: + rate_of_change
  - Boolean: changed_to_true, changed_to_false, toggled
  - GPS: entered/exited_geofence, speed_exceeded, distance_from_point
  - Counter: + increment_exceeded

- [x] Step 4 — Einheiten-Konvertierung (14 Konvertierungen)
  - °C→°F, °C→K, hPa→mmHg, km/h→mph, lux→fc, kWh→Wh, W→kW, V→mV, A→mA u.a.

- [x] Step 5 — Frontend: Type Management UI
  - `/settings/types` — SemanticTypes.vue mit Card-Grid, Filter (base_type, origin)
  - Create/Edit Modal, expandierbare Trigger-Templates + Konvertierungen
  - `lib/semantic-types.ts` API-Wrapper, Sidebar-Eintrag

### Milestone 15: Device Experience Reboot [done] ✅
> Devices mit reicherer Identität, Onboarding-Wizard und kontextuellen Verbindungen.

- [x] Step 1 — Device Identity erweitern
  - DB: `category` (hardware/service/bridge/agent), `icon`, `location_name`, `location_lat/lng`, `auto_discovery`
  - `PATCH /api/v1/devices/{id}` — alle neuen Felder + name updatebar
  - DeviceListItem + DeviceDetailItem Schemas erweitert

- [x] Step 2 — Device Cards Redesign
  - Card-Grid mit Name, Kategorie-Badge (--cat-* Farben), pulsierendem Status-Dot
  - Location-Pin, Variable-Count, Gruppen-Chips, Quick-Actions
  - Kategorie-Filter (All/Hardware/Service/Bridge/Agent), Suche inkl. Name

- [x] Step 3 — Inline-Gruppierung
  - Mehrfachauswahl mit Group-Mode, Selection-Toolbar
  - "Add to group" Dropdown + "Create new group" Modal
  - Bulk-Bind via POST /entities/{id}/devices

- [x] Step 4 — Universal "Add Device" Wizard
  - AddDeviceWizard.vue: 3-Step Modal (Kategorie → Setup → Summary)
  - Hardware: Pairing, Service: URL+Auth, Bridge: Protokoll, Agent: SDK
  - Name, Icon, Location, Auto-Discovery Toggle

- [x] Step 5 — Auto-Discovery
  - 27+ Keyword-Mappings in Telemetry-Bridge (temperature→Temperature, etc.)
  - Automatische VariableDefinition-Erstellung mit semantic_type_id
  - `variable.auto_discovered` System-Event

- [x] Step 6 — Device Detail: "Platinen-Ansicht"
  - Connections-Card: Device → Variables → Alerts + Automations (Flow-Darstellung)
  - Technical View Toggle (raw JSON)
  - Edit Device Modal (Name, Category, Icon, Location)

- [ ] Step 7 — Variables Page Redesign
  > Variablen gruppiert und mit Kontext, nicht als flache Liste.

  GRUPPIERUNG (umschaltbar):
  - "Nach Device" (Default) | "Nach Typ" | "Flat" (klassische Liste)

  BULK-AKTIONEN:
  - Mehrfachauswahl → Toolbar: "Typ ändern", "Zum Dashboard hinzufügen",
    "Alert-Regel erstellen", "Löschen"

  SCHNELLVERGLEICH:
  - 2-3 Variablen auswählen → "Vergleichen"
  - Overlay: Variablen als überlagerte Lines in einem Chart

  FILTER:
  - Nach Device, nach semantischem Typ, nach Direction (read/write/rw),
    nach Status (aktiv/inaktiv), nach letztem Update

### Milestone 16: Kontextuelles Arbeiten [done]
> Von überall aus weiterverketten — der "rote Faden" durch die ganze Plattform.
> Kein Navigieren durch 8 Menüs, sondern: Klick → nächster Schritt → fertig.

- [x] Step 1 — Connect-Panel (Slide-Over)
  > Jedes Element (Variable, Device, Automation, Alert) bekommt ein ausklappbares
  > Seitenpanel: "Was hängt dran? Was kann ich anhängen?"
  - Panel zeigt: bestehende Verbindungen als Mini-Liste
  - "+"-Button: "Alert erstellen", "Automation erstellen", "Zum Dashboard hinzufügen",
    "Webhook einrichten" — kontextabhängig, nur was Sinn macht
  - Klick auf "+" öffnet Inline-Formular IM Panel — kein Seitenwechsel
  - Kontext bleibt erhalten: Variable X ist vorausgewählt, User muss nur
    die Bedingung/Aktion konfigurieren

- [x] Step 2 — Kontextmenüs
  > Rechtsklick / "..."-Menü auf jedes Element zeigt sinnvolle nächste Aktionen.
  - Variable: "Alert wenn Schwellwert", "Automation erstellen", "Im Dashboard",
    "History anzeigen", "Typ ändern"
  - Device: "Variablen ansehen", "Alert-Regeln", "Automationen", "Standort setzen",
    "Zur Gruppe hinzufügen"
  - Automation: "Testen", "Deaktivieren", "Flow anzeigen", "Duplizieren"
  - Alert: "Bestätigen", "Stummschalten", "Regel bearbeiten", "Device anzeigen"

- [x] Step 3 — Proaktive Empty States
  > Leere Zustände sind Einstiegspunkte, nicht Sackgassen.
  > ABER: immer auch der direkte Weg für erfahrene User sichtbar.
  - Jede leere Seite zeigt: konkreten CTA UND normalen "+"-Button
  - Devices leer: "Verbinde dein erstes Device →" + "+ Device hinzufügen"
  - Variables leer: "Devices senden automatisch Variablen. Oder erstelle
    eine manuell →" + "+ Variable erstellen"
  - Alerts leer: "Werde benachrichtigt wenn etwas passiert →" + "+ Alert-Regel"
  - Automations leer: Klickbare Templates + "+ Neue Automation" Button

- [x] Step 4 — Progressive Action-Bars
  > Jede Detail-Seite zeigt kontextuelle "Nächste Schritte" — aber nur
  > wenn relevant und nie aufdringlich. Skipbar, ausblendbar.
  - Device-Detail (neues Device): Action-Bar mit Vorschlägen
    (Daten ansehen, Automation erstellen, Dashboard-Widget, Alert)
  - "×" zum dauerhaften Ausblenden (User-Preference pro Device)
  - Aktionen verschwinden einzeln wenn erledigt
  - Variable-Detail: "Was möchtest du mit diesem Datenpunkt tun?"
  - Dashboard leer: Template wählen ODER "Leer starten" mit Auto-Suggest
  - Automation leer: 3 klickbare vorbefüllte Templates
  - In Settings: "Hilfe-Hinweise zurücksetzen" Button
  - Prinzip: unterstützend, nie blockierend, alles mit einem Klick skippbar

  NACH ALERT-AKTION (Lücke 3):
  - Nach "Acknowledge": Inline-Hinweis mit Links zu Device, Automation erstellen,
    Alert stummschalten
  - Nach "Resolve": Links zu Problem-Historie, ähnliche Alerts
  - Bei wiederkehrenden Alerts (>3x in 24h): "Automation erstellen?" CTA

  FEHLER-FEEDBACK (Lücke 4):
  - Action-Bars zeigen auch "Probleme" bei fehlerhaften Elementen:
  - Automation fehlgeschlagen: Roter Banner mit Kurz-Grund + Links
  - Webhook nicht zugestellt: Warnung mit Delivery-Log-Link
  - Device offline: Warnung mit letztem Timestamp + Verbindungstest-Link
  - Banner-Farben: Rot = Fehler, Orange = Warnung, Blau = Info
  - Alle Banner per "×" dismissbar (kommt zurück bei neuem Fehler)

- [ ] Step 5 — Globale Suche (Cmd+K)
  > Schnellzugriff auf alles in HubEx — Devices, Variablen, Alerts,
  > Automationen, Dashboards. Für Power-User der schnellste Weg.

  - Shortcut: Cmd+K / Ctrl+K öffnet Such-Overlay (zentriertes Modal)
  - Suche über: Device-Namen, Variable-Keys, Alert-Rule-Namen,
    Automation-Namen, Dashboard-Namen
  - Ergebnisse gruppiert nach Typ mit Icons, Status-Badge, Kurzinfo
  - Enter → Navigation zum Element
  - Backend: ILIKE-Suche über relevante name/key/description Felder
  - Später: Fuzzy-Search, letzte Suchen, Slash-Commands (/device:, /var:, /alert:)

  NOTIZ Keyboard Shortcuts (Lücke 9):
  - Cmd+K / Ctrl+K → Globale Suche
  - Escape → Modal/Panel/Overlay schließen
  - Cmd+N / Ctrl+N → Neues Element im aktuellen Kontext
  - ? → Shortcut-Übersicht
  - Zentrale Shortcut-Registry, kein Hardcoding pro Seite

### Milestone 17: Realtime & Notifications [done]
> WebSocket-Layer für Echtzeit-Updates und ein zentrales Notification Center.

- [x] Step 1 — WebSocket Layer
  > Basis für Echtzeit-Updates in UI, ersetzt Polling.
  - FastAPI WebSocket Endpoint `/api/v1/ws?token=JWT` mit JWT-Auth
  - UserHub (realtime.py): broadcast_event + push_notification
  - Channels: device_events, variable_stream, alert_events, automation_events
  - Frontend: `useWebSocket` Composable mit Auto-Reconnect + Backoff
  - WS gestartet in DefaultLayout.vue onMounted

- [x] Step 2 — Notification Center
  > Zentrale Inbox für alle wichtigen Events — wie Handy-Notifications.
  - `notifications` Tabelle: type, severity, title, message, entity_ref,
    read_at, created_at, user_id (+ Alembic Migration)
  - API: GET /notifications, GET /unread-count, PATCH /{id}/read, PATCH /read-all, DELETE /{id}
  - UI: Glocke im Header mit Badge-Count, Dropdown-Panel mit Notification-Liste
  - WS-Push für neue Notifications (Echtzeit) via useWebSocket
  - Alert-Worker: Notification bei Alert-Fire erstellt + gepusht

- [ ] Step 3 — Notification Preferences
  - Pro User: welche Event-Typen als Notification, welche per Email, welche still
  - Pro Alert-Rule: Notification-Kanal konfigurierbar
  - Mute-Funktion: Device/Gruppe/Alert-Rule temporär stummschalten

- [ ] Step 4 — Email-Notification-Dispatch
  - SMTP-Integration (konfigurierbar in Settings)
  - Email-Templates: Alert gefeuert, Device offline, Daily Summary
  - Rate-Limiting: max 1 Email pro Alert-Rule pro Stunde (konfigurierbar)

### Milestone 18: Dashboard Builder [done]
> DAS zentrale Visualisierungs- und Steuerungstool. Ersetzt/absorbiert VariableStreams.
> Direkte Abhängigkeit von M8c (VizWidget) und M14 (Typsystem).

- [x] Step 1 — Dashboard/Widget Model + CRUD API
  - `Dashboard` Tabelle: name, description, layout_config (JSON), is_default,
    owner_id, org_id, sharing_mode (private/org/public)
  - `DashboardWidget` Tabelle: dashboard_id, widget_type (aus VizType + neue),
    data_source_config (JSON), position (grid x/y/w/h), display_config (JSON)
  - CRUD API: Dashboards + Widgets
  - Widget-Types: alle bestehenden VizTypes + Steuerungs-Widgets (siehe Step 3)

- [x] Step 2 — CSS Grid Editor (vue-grid-layout verschoben auf M18.2)
  - CSS Grid (12-Spalten) mit konfigurierbaren grid_col/grid_row/grid_span_w/grid_span_h
  - Widgets hinzufügen: "+" → Typ wählen → Variable/Device → Größe wählen → platzieren
  - Edit Mode Toggle: im View-Mode keine Edit-Overlays sichtbar
  - Widget entfernen mit Confirm-Dialog, Widget konfigurieren per Overlay-Button

- [x] Step 3 — Steuerungs-Widgets
  - VizControlToggle: Toggle-Switch für Boolean read_write
  - VizControlSlider: Slider für int/float mit min/max, schreibt Variable zurück
  - control_toggle / control_slider als neue VizTypes in viz-types.ts + viz-resolve.ts
  - VizWidget erweitert: writable prop, onControlChange Event, handleControlChange()

- [x] Step 4 — Auto-Suggest / Widget-Typ-Dropdown bei Widget-Erstellung
  - Widget-Typ Selector mit Gruppen: Visualizations / Controls
  - Einheit + Min/Max Felder für numerische Widgets
  - Grid-Größe (Width/Height in Spalten/Zeilen) direkt im Formular wählbar

- [x] Step 5 — Dashboard-Templates (5 built-in)
  - Blank, Climate Monitor, Server Monitor, Fleet Tracking, Energy Dashboard
  - Template wählt Widgets vor, User mappt eigene Variable Keys nach Erstellung
  - Wizard: Step 1 Template-Auswahl → Step 2 Name + Optionen → Dashboards anlegen

- [ ] Step 6 — VariableStreams Migration (pending M19)
  > Bestehende Streams-Seite wird zum "Quick View" innerhalb des Dashboard Builders.

- [ ] Step 7 — Dashboard Sharing + Embed (pending)
  - Sharing: per Link (read-only), per Org, per Capability
  - Embed Mode: iframe mit Public Link, Kiosk-Modus (keine Sidebar/Header)
  - Export: Dashboard als PNG/PDF Screenshot

### Milestone 19: Unified Automation Engine [done]
> Zusammenlegung der bestehenden Automation Engine (M10.5) mit der geplanten
> Rules Engine (M16 alt). Ein System, nicht zwei. Darstellung wächst mit Komplexität.

- [x] Step 1 — Typsystem-Integration
  > Trigger sind nicht mehr hardcoded, sondern kommen aus dem SemanticType.
  - GET /automations/trigger-templates — lädt aus TriggerTemplate + SemanticType
  - Frontend: listTriggerTemplates() API-Client + TriggerTemplateOut Typ
  - Bestehende 4 Trigger-Types bleiben als Built-in, TriggerTemplates ergänzen

- [x] Step 2 — Ketten & Sequenzen
  > Multi-Step-Automationen: IF → THEN → THEN → THEN
  - `AutomationStep` Tabelle: rule_id, step_order, action_type, action_config,
    delay_seconds, condition_type, condition_config
  - Alembic Migration e8f9a0b1c2d3
  - CRUD API: GET/POST/PUT/DELETE /automations/{id}/steps
  - Frontend: listSteps(), createStep(), deleteStep() API-Client

- [ ] Step 3 — Bedingungsgruppen (AND/OR)
  - Trigger-Conditions können gruppiert werden:
    "WENN (Temp > 40 UND Fenster == geschlossen) ODER (Alarm == aktiv)"
  - `ConditionGroup` mit Operator (AND/OR) und verschachtelten Conditions
  - UI: Visueller Condition-Builder mit Drag & Drop Gruppierung

- [ ] Step 4 — Verzweigungen (If/Else)
  - "WENN Temperatur > 40 → Aktion A, SONST → Aktion B"
  - Step kann Typ "branch" haben mit true_action und false_action
  - UI: Verzweigung als visueller Split im Flow

- [x] Step 5 — Automation-Templates (5 Built-in Quick-starts)
  - GET /automations/templates — 5 vordefinierte Templates
  - Threshold Alert, Device Offline Alert, Variable Forwarding, Webhook on Telemetry, Geofence Alert
  - Frontend: listAutomationTemplates() API-Client + AutomationTemplateOut Typ
  - Visueller Builder (Flow/Ketten-Darstellung) → folgt in M19.2

- [ ] Step 6 — Externe Flows sichtbar machen
  > Wenn eine Automation per Webhook an n8n geht, wird das in HubEx sichtbar.
  - Webhook-Action zeigt "→ extern (n8n)" mit Link
  - Eingehende n8n-Aktionen (Variable setzen via API) werden als
    "← extern" im Automation-Flow angezeigt
  - Kein aktives Tracking von n8n-Flows, sondern passive Sichtbarkeit
    basierend auf Webhook-Dispatches und API-Calls

### Milestone 20: System-Übersicht & Mission Control [done]
> Dashboard wird echtes Mission Control �� nicht nur Charts, sondern Überblick.

- [x] Step 1 — Dashboard Redesign: Quick Actions
  - Quick-Action Buttons: Active Alerts, Offline Devices, Automations, Dashboards
  - Bestehende Metrics bleiben: Device Health Ring, Online%, Alerts, Entities, Events, Uptime
  - CSS quick-action-btn Styling (border, hover mit primary-color)

- [ ] Step 2 ��� Fokusbasierte Flow-Ansicht
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

- [x] Step 4 — Demo-Datensatz
  - `python -m app.scripts.seed_demo_data` — seed / `--delete` entfernen
  - 3 Devices (Temp-Sensor/Hardware, Wetter-API/Service, MQTT-Bridge/Bridge)
  - 8 Variablen (temperature, humidity, pressure, online, gps, log, target_temp, heater_on)
  - 2 Automationen (High Temp Alert, Device Offline Webhook)
  - 1 Dashboard "Demo Dashboard" mit 6 Widgets (Gauges, Chart, Slider, Toggle)
  - 1 Entity "Lab Room 1"

---

> **Offene Steps aus Phase 5 — Zuordnung:**
> Die folgenden Steps stehen noch als `[ ]` in M15-M20 und werden in Phase 5b oder 7 adressiert:
> - M15 Step 7 (Variables Page Redesign) → **Teilweise erledigt** (Gruppierung ✓), Rest in UX-C Step 4
> - M16 Step 5 (Globale Suche Cmd+K) → **Phase 7** (eigenes Feature, niedrigere Prio)
> - M17 Step 3 (Notification Preferences) → **Phase 7** (M17 erweitern)
> - M17 Step 4 (Email-Dispatch) → **Phase 7** (M19b Step 1 enthält Email-Action)
> - M18 Step 6 (Streams Migration) → **Phase 7** (niedrige Prio, Streams funktioniert)
> - M18 Step 7 (Dashboard Sharing) → **Phase 7** M18b (Embed + Sicherheitsstufen)
> - M19 Step 3 (AND/OR Groups) → **Phase 7** (M19b erweitert die Engine)
> - M19 Step 4 (If/Else Branching) → **Phase 7** (M19b erweitert die Engine)
> - M19 Step 6 (Externe Flows) → **Phase 7** (M21 Steps 4-7 deckt Integration ab)
> - M20 Step 2 (Flow-Ansicht) → **Phase 7** M36 (Flow Editor)
> - M20 Step 3 (System Map) → **Phase 5b** UX-E Step 1-2 (vereinfacht als Node-Graph)

---

## Phase 6: Erweiterung & Anbindung [done] ✅

- [x] Step 1 — n8n Node Update: Semantische Typen
  - n8n Node v2: Semantic Type resource (list, get, triggers, conversions)
  - Auto-Discovery + Variable Changed + Automation events als Trigger
  - Variable Definitions include semantic type info

- [x] Step 2 — n8n Node: Dashboard & Automation Integration
  - Automation resource: list, toggle, test, history, templates
  - Dashboard resource: list, get, create, delete
  - Bidirektionale Steuerung über n8n möglich

- [x] Step 3 — n8n Kompatibilitäts-Tests
  - `tests/api-compat.test.ts` — automatisierte Tests aller Endpoints
  - 13 Endpoint-Tests gegen laufende API
  - Fix: Automation template/trigger-template Route-Ordering (vor /{rule_id})

### Milestone 22: MCP Server Integration [done] ✅
- [x] Step 1 — MCP Tool Definitions: 15 Tools (Device, Alert, Variable, Automation, Metrics, Dashboard, SemanticType)
- [x] Step 2 — MCP Endpoint Layer: `POST /api/v1/mcp/tools/list` + `POST /api/v1/mcp/tools/call` mit JWT Auth
- [x] Step 3 — MCP Handler: Alle Tools gegen SQLAlchemy-Models implementiert, user-scoped
- [x] Step 4 — Capabilities: `mcp.read` + `mcp.execute` in Registry + Route Map

### Milestone 23: Universal Agent SDK [done] ✅
> Agents sind gleichwertige Device-Typen neben MCUs, API-Devices und Standard-Devices.
- [x] Step 1 — Agent Protocol: `POST /api/v1/agent/handshake` + `POST /api/v1/agent/heartbeat` (Device-Token Auth)
- [x] Step 2 — Python SDK Agent: `sdk/python/hubex_agent/` — HubexAgent Klasse mit Heartbeat, Telemetrie, Collectors
- [x] Step 3 — Built-in Collectors: system_collector (CPU, Memory, Disk), network_collector (IP, Traffic)
- [x] Step 4 — Agent Features: Threaded loop, configurable intervals, psutil integration optional
- [x] Step 5 — Setup.py + CLI entry point, pip-installierbar

### Milestone 24: Bridge/Gateway Framework [done] ✅
- [x] Step 1 — Bridge Architecture: `HubexBridge` Klasse, Plugin-System mit `BridgePlugin` ABC
- [x] Step 2 — Serial/UART Bridge Plugin: `SerialBridgePlugin` Stub mit Port/Baud config
- [x] Step 3 — Modbus RTU/TCP Plugin: `ModbusBridgePlugin` Stub (pymodbus-ready)
- [x] Step 4 — BLE Bridge Plugin: `BLEBridgePlugin` Stub (bleak-ready)
- [x] Step 5 — Multi-Plugin Support: Per-Plugin Poll-Loops, Auto-Prefix, Setup/Teardown Lifecycle

### ~~Milestone 25: Onboarding~~ → GESTRICHEN (verteilt in M15/M16/M19/M20)

---

## Phase 5b: UX Completion [done] ✅
> **Leitsatz:** Die Milestones M13-M20 sind als "done" markiert, aber viele Steps sind noch "pending"
> und die UX-Vision aus der Gesamtspezifikation ist nicht erfüllt. Diese Phase schließt ALLE Lücken
> bevor Enterprise-Features beginnen. Kontextuelles Arbeiten, Erklärungen, Wizards — alles was der
> User sofort spürt.
>
> **UX-Grundregel für ALLE zukünftigen Features:**
> 1. Progressive Disclosure: Default zugeklappt, aufklappbar per Klick
> 2. Selektoren statt ID-Eingabe: ÜBERALL
> 3. Kontextuelles Arbeiten: Von jedem Element zum nächsten Schritt MIT Kontext
> 4. Unterstützend, nie aufdringlich: Wizards skippbar, Hilfe ausblendbar
> 5. Minimalistisch: Nur was relevant ist, keine rohen JSON-Fehler
> 6. Wächst mit Komplexität: Einfache Setups = einfach, komplexe = detaillierter
> 7. Verständliche Sprache: Tooltips, klare Buttons, Bestätigung bei Destruktivem

### Milestone UX-A: Flow-Korrekturen & Foundation [done] ✅
> Kontextuelles Arbeiten reparieren — der "rote Faden" muss funktionieren.

- [x] Step 1 — ActionBar Context-Navigation (~2h)
  - DeviceDetail ActionBar: `/alerts?create=true&device_uid=X`, `/automations?create=true&device_uid=X`
  - Nicht mehr nur `/alerts` ohne Kontext
  - Datei: `components/ActionBar.vue`

- [x] Step 2 — Alert Post-Acknowledge Action-Bar (~2h)
  - Nach Ack: Inline-Bar "Alert bestätigt → [Zum Device] [Automation erstellen] [Stummschalten]"
  - Bei wiederkehrenden Alerts (>3x in 24h): "Automation erstellen?" CTA
  - Datei: `pages/Alerts.vue`

- [x] Step 3 — Alert-Events klickbar + verlinkt (~1h)
  - Alert-Event-Zeile: Device/Variable-Name als `<router-link>` zum Device
  - Klick → springt zum betroffenen Device
  - Datei: `pages/Alerts.vue`

- [x] Step 4 — Alerts→Automations Link (~1h)
  - "Create Automation" Button auf Alerts-Seite
  - Navigiert mit `?create=true&variable_key=X` zum Automations-Builder
  - Datei: `pages/Alerts.vue`

- [x] Step 5 — DeviceDetail Input/Output zugeklappt (~1h)
  - Beide UCard-Panels (Input/Telemetry + Output/Variables) default collapsed
  - Aufklappbar per Chevron-Klick
  - Datei: `pages/DeviceDetail.vue`

- [x] Step 6 — Selektoren-Audit abschließen (~1h)
  - Grep nach `<UInput` in Formularen, jedes Entity-Referenz-Feld → UEntitySelect
  - Automations: `trigVarKey`, `actVarKey`, `trigDeviceUid` verifizieren
  - Alert Rules: `vtKey`, `vtDeviceUid` verifizieren

### Milestone UX-B: Erklärungen, Tooltips & Bug-Fixes [done] ✅
> Jede Seite erklärt sich selbst. Keine unklaren Icons. Keine JSON-Fehler.

- [x] Step 1 — Events-Seite Erklärungstext + Tooltips (~1h)
  - Header: "Events zeigen System-Ereignisse in Echtzeit"
  - Tooltips auf: "Set cursor", "Jump to next", "ACK", "Stream"
  - Datei: `pages/Events.vue`

- [x] Step 2 — Audit-Seite Erklärungstext (~0.5h)
  - Header: "Das Audit-Log zeigt wer wann was im System geändert hat"
  - Visuell von Events unterscheiden
  - Datei: `pages/Audit.vue`

- [x] Step 3 — Entities Tooltips (~0.5h)
  - "Priority": Tooltip "Reihenfolge bei mehreren Bindings (höher = wichtiger)"
  - "Enable Binding": Tooltip "Deaktivierte Bindings bleiben gespeichert, werden aber ignoriert"
  - Datei: `pages/EntitiesPage.vue`

- [x] Step 4 — Automations Builder Tooltips (~1h)
  - Geofence Polygon: "JSON-Array von Koordinaten [[lat,lng], ...]"
  - Webhook Headers: "JSON-Objekt mit HTTP-Headern"
  - Cooldown: "Wartezeit in Sekunden bevor die Regel erneut feuern kann"
  - Datei: `pages/Automations.vue`

- [ ] Step 5 — Bug-Fixes: Dashboard-Template JSON-Fehler (~2h)
  - Root Cause analysieren und fixen
  - Dateien: `pages/DashboardView.vue`, Backend-Endpoints

- [ ] Step 6 — Bug-Fixes: API-Docs/Swagger 404 + Useful Links (~1h)
  - Links zu `/api/v1/docs` und Redoc verifizieren und reparieren
  - Useful Links in Settings prüfen
  - Dateien: `pages/ApiDocs.vue`, `pages/Settings.vue`

- [ ] Step 7 — Bug-Fix: Acknowledge-Alert (~1h)
  - Alert-Acknowledge schlägt fehl → Backend-Endpoint prüfen
  - Dateien: `pages/Alerts.vue`, Backend

- [ ] Step 8 — Grafik-Bug Suchfeld-Placeholder (~0.5h)
  - Placeholder-Rendering in Suchfeldern prüfen
  - Dateien: `pages/Devices.vue`, `pages/EntitiesPage.vue`

- [x] Step 9 — Secrets Toggle Tooltip + Streams-Seite Erklärung (~1h)
  - Variables: Tooltip auf Secrets-Toggle
  - VariableStreams: Erklärungstext oben, Progressive Disclosure

- [x] Step 10 — System Health: Redis Tooltip + klickbare Links (~0.5h)
  - Redis → Tooltip "In-Memory Cache"
  - Devices Online/Offline → klickbarer Link zur Devices-Seite (gefiltert)
  - Active Alerts → Link zur Alerts-Seite

- [ ] Step 11 — Dashboard Home aufräumen (~2h)
  - Minimalistischer: nur wichtigste KPIs sichtbar
  - Weniger Kacheln, klarere Aussage

### Milestone UX-C: DeviceDetail Komplett-Überholung [done] ✅
> Das Herzstück der "Verstehen"-Ebene — Device als Platine mit klickbaren Elementen.

- [x] Step 1 — System Context mit echten Elementen (~4h)
  - Statt "Variables 21" → Liste der tatsächlichen Variablen mit Name, Wert, Typ-Icon
  - Jede klickbar (Link zur Variable oder Connect-Panel)
  - Verknüpfte Alerts und Automations anzeigen als Nodes
  - Datei: `pages/DeviceDetail.vue`

- [x] Step 2 — Variable-Typ editierbar (~2h)
  - Edit-Modal erweitern: Typ (string/int/float/bool/json), Einheit, Direction
  - Nicht nur Value, sondern auch Metadaten änderbar
  - Datei: `pages/DeviceDetail.vue`

- [x] Step 3 — Connect-Button pro Variable (~1h)
  - 🔗 Icon pro Variable-Zeile → öffnet ConnectPanel mit dieser Variable
  - Datei: `pages/DeviceDetail.vue`

- [x] Step 4 — Variablen-Bereich: Typ-Icons + Einheiten (~2h)
  - Jede Variable: Typ-Icon (🌡️/💧/🔋), Name, Wert MIT Einheit, Sparkline
  - Kein "Default" Badge mehr
  - Datei: `pages/DeviceDetail.vue`

- [x] Step 5 — Offline-Fehlerzustand ActionBar (~1h)
  - Bei Offline: "🔴 Offline seit 3h · Letzter Kontakt: 14:23"
  - Buttons: [Verbindung testen] [Alert einrichten]
  - Datei: `pages/DeviceDetail.vue`

### Milestone UX-D: Add Device Wizard [done] ✅
> Ebene 1 der Vision: "Was willst du anbinden?" — 4 geführte Flows.

- [x] Step 1 — Wizard-Komponente (~3h)
  - Multi-Step-Wizard: Step-Indicator, Back/Next/Skip, ein Feld pro Screen
  - Datei: `components/DeviceWizard.vue` (neu)

- [x] Step 2 — Flow A: Hardware (ESP32/Shelly) (~3h)
  - Verbindungsart → Pairing/MQTT → Live-Status → Benennen → Geschafft
  - 5 Steps mit "Überspringen →" auf jedem

- [x] Step 3 — Flow B: Service/API (~3h)
  - URL eingeben → Auth wählen → Testen + Felder erkennen → Benennen → Geschafft

- [x] Step 4 — Flow C: Bridge (MQTT/Modbus/CAN) (~2h)
  - Protokoll wählen → Config → Testen → Benennen → Geschafft

- [x] Step 5 — Flow D: Agent (Software) (~2h)
  - System wählen → Install-Command (Copy-to-Clipboard) → Warten → Benennen → Geschafft

- [x] Step 6 — WelcomeScreen + Devices Integration (~1h)
  - WelcomeScreen: Klick auf Kategorie → startet Wizard mit richtigem Flow
  - Devices-Seite: "+ Device" Button → öffnet Wizard

### Milestone UX-E: System Context Platinen-Ansicht + Dashboard Intelligence [done] ✅
> Ebene 2 + 3 der Vision: Visueller Schaltplan + smartes Dashboard.

- [x] Step 1 — Node-Graph-Komponente (~4h)
  - SVG-basiert: Device-Node → Variable-Nodes → Alert/Automation-Nodes
  - Verbindungslinien, klickbare Nodes
  - Datei: `components/SystemContextGraph.vue` (neu)

- [x] Step 2 — Integration in DeviceDetail (~2h)
  - Ersetzt die aktuellen statischen Boxen
  - API: GET `/devices/{id}/context` → variables, alerts, automations

- [x] Step 3 — Dashboard Widget Auto-Suggest (~2h)
  - Nach Variable-Auswahl: Widget-Typ basierend auf `display_hint`/`value_type`
  - Label + Unit Auto-Fill aus Variable-Definition

- [x] Step 4 — Connect-Panel Inline-Forms (~3h)
  - "[+ Alert]" im Panel → Inline-Formular IM Panel, kein Navigation weg
  - Variable vorausgewählt, nur Bedingung konfigurieren

---

## Phase 6: Erweiterung & Anbindung [done] ✅
> M11 und M21 werden langfristig generalisiert zu "Externe Integrationen"
> und "Deep Integrations & Ecosystem" (nicht nur n8n).
> **Grundprinzip:** Jedes neue Feature MUSS per REST-API, Webhook und
> ggf. MQTT erreichbar sein. Universelle Kompatibilität mit n8n, Node-RED,
> Home Assistant, Make, Zapier, Power Automate und Custom Scripts.

### Milestone 21: n8n Deep Integration → Externe Integrationen [done] ✅
> Langfristig generalisiert: Node-RED, Home Assistant, Make/Zapier Support geplant.
- [x] Step 1 — n8n Node Update: Semantische Typen
- [x] Step 2 — n8n Node: Dashboard & Automation Integration
- [x] Step 3 — n8n Kompatibilitäts-Tests
- [ ] Step 4 — Node-RED Node Package (npm: node-red-contrib-hubex)
- [ ] Step 5 — MQTT Integration erweitern (Home Assistant Discovery Protocol)
- [ ] Step 6 — Webhook-System härten (Payload-Templates, Custom Headers, Auth)
- [ ] Step 7 — Integrations-Dokumentation (n8n, Node-RED, HA, Make, Python, curl)

### Milestone 22: MCP Server Integration [done] ✅
- [x] Step 1 — MCP Tool Definitions: 15 Tools
- [x] Step 2 — MCP Endpoint Layer
- [x] Step 3 — MCP Handler
- [x] Step 4 — Capabilities

### Milestone 23: Universal Agent SDK [done] ✅
- [x] Step 1 — Agent Protocol
- [x] Step 2 — Python SDK Agent
- [x] Step 3 — Built-in Collectors
- [x] Step 4 — Agent Features
- [x] Step 5 — Setup.py + CLI

### Milestone 24: Bridge/Gateway Framework [done] ✅
- [x] Step 1 — Bridge Architecture
- [x] Step 2 — Serial/UART Bridge Plugin
- [x] Step 3 — Modbus RTU/TCP Plugin
- [x] Step 4 — BLE Bridge Plugin
- [x] Step 5 — Multi-Plugin Support

---

## Phase 5c: Stabilität, Simulation & Integration [todo] ← AKTUELL
> **Leitsatz:** Bevor Enterprise-Features kommen, muss die Basis stabil und testbar sein.
> Echte Device-Simulationen, API-Config-Panel, Entities-Integration in DeviceDetail,
> System Context als Node-Graph, Automations-Builder-Stabilität.

### Milestone UX-F: Quick Fixes [done] ✅
- [x] Step 1 — Dashboard Gauge ViewBox Fix (Bogen abgeschnitten)
- [x] Step 2 — Variable Slider Scroll-Bug (Seite springt nach oben bei Änderung)
- [x] Step 3 — Dashboard Device Health Donut entfernen (redundant zu Total Devices)

### Milestone SIM-1: Device-Simulatoren [done] ✅
> Echte Simulationen für alle 4 Device-Typen — Plattform end-to-end testbar.
- [x] Step 1 — ESP32-Simulator (`scripts/sim_esp32.py`: Auto-Pair, Heartbeat, Telemetrie mit realistischen Sensordaten)
- [x] Step 2 — API-Poll-Worker (`scripts/api_device.py`: Open-Meteo Weather API, auto-pair, field extraction)
- [x] Step 3 — MQTT-Bridge-Simulator (`scripts/sim_mqtt_bridge.py`: 6 Topics, realistische Sensordaten, auto-pair)
- [x] Step 4 — Agent-Simulator (`scripts/sim_agent.py`: CPU/RAM/Disk Monitoring, auto-pair)
- [x] Step 5 — Fleet-Launcher (`scripts/sim_all.py`: Startet alle 4 Simulatoren parallel)

### Milestone SIM-2: API-Device Config-Panel [done] ✅
> Devices vom Typ "Service" und "Bridge" brauchen editierbare Konfigurationsfelder.
- [x] Step 1 — DB-Schema: `config` JSON-Feld am Device-Model (JSONB column, category-spezifische Struktur)
- [x] Step 2 — Backend: Config via PATCH /devices/{id} (DevicePatch.config), DeviceDetailItem.config
- [x] Step 3 — Frontend: Config-Panel auf DeviceDetail (Service: URL/Method/Auth/Poll, Bridge: Broker/Topic/Protocol, Agent: Interval/Install)
- [x] Step 4 — "Test Connection" Button (fetch + timeout + Status-Anzeige)
- [x] Step 5 — Config-Panels für Bridge-Devices (Broker URL, Topic, Protocol, Port) + Agent (Interval, Install Command)

### Milestone UX-G: Entities → DeviceDetail Integration [done] ✅
> Entities dürfen nicht auf einer eigenen Insel leben — sie gehören zum Device.
- [x] Step 1 — "Groups & Memberships" auf DeviceDetail: Chips + "Add to Group" Button + Remove (×)
- [x] Step 2 — Entity.tags als Properties in EntityOut Schema (location, tags sichtbar)
- [x] Step 3 — Quick-Create Entity direkt aus DeviceDetail (Toggle "Create New" im Modal, ID+Name+Type)
- [x] Step 4 — Entity-Location (location_lat/lng/name Felder auf Entity-Model + DB + Schemas)
- [x] Step 5 — Entity-Variablen-Scope: designed as "entity" scope in variable system (implementation deferred to Phase 7)

### Milestone UX-H: System Context Node-Graph [done] ✅
> Die "Platinen-Ansicht" — visueller Fluss von Device → Variables → Alerts → Automations.
- [x] Step 1 — Visual flow layout with dashed SVG arrows (Device → Variables → Actions)
- [x] Step 2 — Node-Typen: Device (mit Status-Dot), Variable (mit Wert+Einheit), Action-Buttons
- [x] Step 3 — 5-column grid layout: Device | Arrow | Variables | Arrow | Actions
- [x] Step 4 — Klick-Navigation: Variable-Nodes → /variables mit highlight + device filter
- [x] Step 5 — Datenquelle: getEffectiveVariables (gefiltert auf Variablen mit Wert)

### Milestone UX-I: Automations-Builder Stabilität [todo]
> Der Builder muss intuitiver und stabiler werden bevor neue Trigger/Actions kommen.
- [ ] Step 1 — Builder-UX als Karten statt Formular (visuell geschlossene IF/THEN Blöcke)
- [ ] Step 2 — Validierung + verständliche Fehlermeldungen
- [ ] Step 3 — 3 neue Trigger: variable_change, device_online, schedule (cron)
- [ ] Step 4 — 2 neue Actions: send_notification, log_to_audit
- [ ] Step 5 — Inline-Test-Vorschau ("Was würde diese Rule auslösen?")

### Milestone UX-J: Dashboard Builder Verbesserungen [todo]
> Widget-System braucht grundlegende Verbesserungen für produktive Nutzung.
- [ ] Step 1 — Widget Drag & Drop Reordering (sort_order via Layout-Update API)
- [ ] Step 2 — Intelligentes Grid-Layout: neue Widgets neben bestehende setzen statt immer neue Zeile
- [ ] Step 3 — Device-Filter bei Variable-Auswahl: erst Device wählen, dann gefilterte Variablen
- [ ] Step 4 — Image-Widget entfernen oder als URL-Input direkt (nicht über Variable)
- [ ] Step 5 — Time-Range nur bei Chart-Widgets anzeigen (nicht bei Toggle/Slider)

---

## Phase 7: Enterprise, Business & Advanced [todo]
> Erweitert um Business-kritische Features aus der Lücken-Analyse:
> Computed Variables, Snapshots, erweiterte Automations, sicheres Daten-Sharing,
> Custom API Builder, Mandanten-Hierarchie, Report-Generator.

### Milestone 14b: Computed Variables & Snapshots [todo]
> Business-kritisch: Backend-berechnete Variablen + unveränderliche Stichtagswerte.
- [ ] Step 1 — Computed Variables Backend (Scope: computed/system, Formel-Engine)
- [ ] Step 2 — Berechnungs-Trigger (reaktiv, Cron/Schedule, manuell)
- [ ] Step 3 — Computed Variables UI (Formel-Editor, Preview, Dashboard-nutzbar)
- [ ] Step 4 — Variable Snapshots (Stichtagswerte, immutable, Timeline)

### Milestone 19b: Automation Engine Erweiterung [todo]
> 8 neue Action-Typen, 5 neue Trigger, visueller Builder.
- [ ] Step 1 — Neue Actions (Email, HTTP, Data Export, Snapshot, Delay, Push, Audit)
- [ ] Step 2 — Neue Trigger (Cron, Snapshot-Created, Webhook, Computed-Changed, Multi-Var)
- [ ] Step 3 — Visueller Builder UX (Kachel-Katalog, Live-Preview, Test-Modus)

### Milestone 18b: Dashboard Embed & Sicheres Daten-Sharing [todo]
> 3 Sicherheitsstufen: Public, PIN-geschützt, Token-authentifiziert.
- [ ] Step 1 — Public Link (kryptographischer Token, read-only)
- [ ] Step 2 — PIN-geschützt (4-6 Stellen, QR-Code-druckbar)
- [ ] Step 3 — Token-authentifiziert (Scoped Access, Rate-Limited, Audit)

### Milestone 26: Security Hardening v2 [todo]
- [ ] Step 1 — 2FA/MFA (TOTP, WebAuthn)
- [ ] Step 2 — Scoped API Key Management (service-to-service + Embed-Tokens)
- [ ] Step 3 — RBAC Roles (admin, operator, viewer, custom)
- [ ] Step 4 — Session Management UI + Device Token Rotation

### Milestone 27: Skalierungs-Grundlagen [todo]
> Vorbereitung für Enterprise-Scale.
- [ ] Step 1 — variable_history Partitioning (zeitbasiert)
- [ ] Step 2 — Telemetrie-Ingestion Pipeline (Redis Streams/Celery)
- [ ] Step 3 — Automation-Engine Worker Pool
- [ ] Step 4 — Horizontal Scaling Documentation

### Milestone 27b: Custom API Builder [todo]
> Visuell konfigurierbare API-Endpoints die HubEx-Daten in eigenem Format ausgeben.
- [ ] Step 1 — Endpoint-Builder (Route, Method, Params, Response-Mapping)
- [ ] Step 2 — Token-Management + Rate-Limiting pro Endpoint
- [ ] Step 3 — Auto-generierte Swagger/OpenAPI Doku für Custom Endpoints
- [ ] Step 4 — API Traffic Dashboard (Requests/Tag, Latenz, Fehlerrate)

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

### Milestone 28b: Report-Generator (PDF) [todo]
> Template-basierter Report-Generator für Abrechnungen, Übersichten, Berichte.
- [ ] Step 1 — Report-Template System (Layout, Logo, Tabellen, Charts, Platzhalter)
- [ ] Step 2 — Datenquellen (Variablen, Computed Variables, Snapshots, Aggregationen)
- [ ] Step 3 — PDF-Generierung (serverseitig, WeasyPrint/Puppeteer)
- [ ] Step 4 — Automation-Action: "Report generieren + per Email senden"
- [ ] Step 5 — Scheduled Reports ("Am 15.01. Jahresabrechnung für alle Einheiten")

### Milestone 31: Multi-User & Mandanten-Hierarchie [todo]
> Erweitert um Mandanten-Hierarchie mit Sichtbarkeits-Steuerung.
- [ ] Step 1 — Rollen-basierte Sichtbarkeit (wer sieht welches Dashboard/Device)
- [ ] Step 2 — Mandanten-Hierarchie (Organisation → Kunden → Gebäude → Einheiten → Devices)
- [ ] Step 3 — Sichtbarkeit nach Hierarchie-Ebene (Admin/Vermieter/Mieter)
- [ ] Step 4 — Dashboard-Zuweisung pro Hierarchie-Ebene
- [ ] Step 5 — Aktivitäts-Feed ("Max hat Alert-Rule X geändert")
- [ ] Step 6 — Team-Dashboards vs. persönliche Dashboards

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

## Phase 8: Hardware-Plattform & Produkt-Modus [todo]
> HubEx wird vom Software-Tool zum vollständigen IoT-Ökosystem.
> ESP32 als universeller Hardware-Baustein, Integration bestehender Smart-Systeme,
> und die Möglichkeit, eigene Produkte für Endkunden auf HubEx aufzubauen.
>
> **Abhängigkeiten:** M14 (Typsystem), M15 (Device Wizard), M18 (Dashboard Builder),
> M19 (Automations-Engine), M13.2 (Branding), M26.3 (RBAC)

### Milestone H1: Hardware Abstraction Layer [todo]
> Grundlage für alle Hardware-Features. Board-Profile, Pin-Mapping, Shield-Definitionen.

- [ ] Step 1 — Board-Profile System
  - `BoardProfile` Model: name, chip (esp32/esp32s3/esp32c3/atmega328/atmega2560),
    pins (JSON: [{number, capabilities: [digital_io, adc, pwm, i2c, spi, uart]}]),
    flash_size, ram_size, wifi_capable, bluetooth_capable
  - Built-in Profile: ESP32 DevKit, ESP32-S3, ESP32-C3, Arduino Uno, Nano, Mega,
    Raspberry Pi Pico W
  - CRUD API + Frontend: Board-Verwaltung in Settings

- [ ] Step 2 — Shield/Hat-Definitionen
  - `ShieldProfile` Model: name, target_board, occupied_pins, exposed_pins,
    bus_type (serial/spi/i2c), description
  - Built-in: "HubEx Arduino Bridge Shield", "HubEx RS485 Gateway Module"
  - UI: Shield auswählen → belegte Pins automatisch ausgeblendet

- [ ] Step 3 — Visueller Pin-Konfigurator
  - UI-Komponente: Board-Grafik mit klickbaren Pins
  - Pin auswählen → Funktion zuweisen (Sensor-Input, Aktor-Output, Bus-Pin)
  - Farbkodierung: belegte / freie / Bus / Power Pins
  - Validierung: Warnung bei inkompatiblen Pin-Funktionen

### Milestone H2: Bridge Protocol & Firmware [todo]
> ESP als WiFi-Bridge für nicht-internet-fähige Mikrocontroller.

- [ ] Step 1 — HubEx Bridge Protocol Spec
  - Textbasiertes Serial-Protokoll (Arduino-kompatibel, geringer RAM-Verbrauch)
  - Befehle: VAR, SET, ACK, NACK, PING/PONG, META
  - Checksummen pro Nachricht, Retry bei Timeout
  - Beispiel: `>V:temperature:23.5:A3\n` / `<ACK:A3\n`
  - Dokumentation als Teil der Developer Docs

- [ ] Step 2 — HubEx Bridge OS (ESP-Firmware)
  - Feste Firmware für ESP im Bridge-Modus
  - WiFi + HubEx API-Client + OTA (für sich selbst)
  - Serial-Bridge: Bridge-Protokoll → HubEx-Variablen
  - Remote-Flash des angeschlossenen MC (STK500 für AVR)
  - Dualer Betrieb: ESP-eigene Pins + Bridge gleichzeitig

- [ ] Step 3 — Arduino Client Library
  - Lightweight Library: `HubExBridge.h`
  - API: `hubex.send("temperature", 23.5)` | `hubex.get("target_temp")` |
    `hubex.onChange("heater_on", callback)`
  - Automatisches Heartbeat, Reconnect, Checksum-Handling
  - Beispiel-Sketches: Sensor-Auslese, Aktor-Steuerung, Bidirektional

- [ ] Step 4 — Bridge-Mode im Device Wizard
  - Neue Option: "ESP als Bridge für Arduino/anderen MC"
  - Flow: Ziel-Board → Shield (optional) → Pins → Bridge-Firmware flashen →
    Arduino-Sketch generieren

### Milestone H3: Component Library (Hardware-Bausteine) [todo]
> Visuelle Bausteine für Sensoren, Aktoren und Module.

- [ ] Step 1 — Baustein-Manifest-Format
  - JSON pro Komponente: name, category (sensor/actuator/display/module),
    pin_requirements, libraries_required, code_template,
    semantic_type_output, wiring_diagram (SVG optional)

- [ ] Step 2 — Built-in Bausteine (20-30 Stück)
  - Sensoren: DHT22, BME280, DS18B20, BH1750, HC-SR04, PIR, Analog-Input, Button
  - Aktoren: Relais, Servo, LED (PWM), Neopixel/WS2812, Buzzer, Motor, Magnetventil
  - Module: SSD1306 Display, SD-Card, GPS NEO-6M, RFID RC522
  - Jeder Baustein: Code-Template, Pinbelegung, semantischer Typ, Default-Widget

- [ ] Step 3 — Community-Bausteine
  - Import/Export (JSON)
  - Marketplace-Vorbereitung: taggen, bewerten, teilen
  - Custom-Code-Baustein: eigenen Code einbetten der mit HubEx-Variablen interagiert

### Milestone H4: Code Generator [todo]
> Aus UI-Konfiguration wird funktionierender Mikrocontroller-Code.

- [ ] Step 1 — Code-Generator Engine
  - Input: Board-Profil + Pin-Config + Bausteine + Variable-Mappings
  - Output: Vollständiger Arduino/ESP-Sketch (.ino) oder PlatformIO-Projekt
  - Enthält: WiFi, HubEx-Verbindung, OTA, Sensor-Logik, Telemetrie,
    Variable-Empfang, Heartbeat, Error-Handling
  - Bridge-Modus: zwei separate Sketches (Arduino + ESP)

- [ ] Step 2 — Code-Export & Download
  - "Code generieren" Button in Device-Config
  - Download als .zip (Sketch + Libraries + platformio.ini + README)
  - Inline-Code-Preview (Syntax-highlighted, read-only)
  - Anleitung: "So flashst du den Code auf dein Board"

- [ ] Step 3 — Cloud-Compile (Premium/Enterprise)
  - PlatformIO CLI auf dem HubEx-Server
  - Generierter Code → serverseitig kompiliert → .bin-Download oder
    direkt per OTA auf das Device
  - Sandboxed Compilation, Build-Log im UI

### Milestone H5: Retrofit Gateway & Smart-Device Integration [todo]
> Bestehende Geräte smart machen — industriell und Consumer.

- [ ] Step 1 — Device-Profile System
  - `DeviceProfile` Model: name, manufacturer, protocol
    (modbus_rtu/modbus_tcp/canbus/mqtt/rest_api/ir),
    connection_config, register_map/topic_map/endpoint_map,
    variables (auto-generiert mit semantischen Typen), writable_registers

- [ ] Step 2 — Built-in Profile (30+ Geräte)
  - Industrie: Energiezähler (DDM18SD, Eastron SDM), Wechselrichter (Sungrow,
    GoodWe, Fronius), SPS-Grundtypen (Siemens S7 Basis)
  - Smart Home: Shelly (gängige Modelle), Tasmota, Broadlink (IR), Sonoff
  - Sensoren: Modbus-Temperatur, Modbus-Luftqualität

- [ ] Step 3 — Wizard: "Bestehendes Gerät anbinden"
  - Neue Suboption im Device Wizard: "Bestehendes Gerät (Profil auswählen)"
  - Suche/Browse Device-Profile → Profil wählen → Verbindung konfigurieren →
    Test → Variablen auto-angelegt
  - Fallback: "Mein Gerät ist nicht in der Liste" → manuelles Profil

- [ ] Step 4 — Community Device-Profile Marketplace
  - Profile hochladen, taggen, bewerten
  - Qualitäts-Stufen: Community (ungeprüft), Verified (getestet), Official (Hersteller)

### Milestone H6: Produkt-Modus (White-Label) [todo]
> HubEx als Plattform, um eigene IoT-Produkte für Endkunden auszuliefern.

- [ ] Step 1 — Rollenbasierte Ansichten
  - RBAC-Erweiterung (baut auf M26 Step 3 auf):
    Developer (voller Zugang) | Operator (reduziert) | Viewer (nur Dashboards) |
    Kiosk (kein UI-Chrome)
  - Operator: reduzierte Sidebar, keine Config-Seiten, Steuerung möglich
  - Viewer: kein Sidebar, nur zugewiesene Dashboards, Fullscreen
  - Kiosk: kein UI-Chrome, Auto-Rotate, Touch-optimiert

- [ ] Step 2 — Dashboard-Zuweisung pro Rolle/User
  - Developer weist Dashboards Rollen zu
  - Viewer sieht NUR zugewiesene Dashboards
  - Default Dashboard pro Rolle konfigurierbar

- [ ] Step 3 — White-Label Branding pro Organisation
  - Baut auf M13 Step 2 (Branding-Abstraction) auf
  - Pro Organisation: Logo, Produktname, Primärfarbe, Favicon
  - Im Viewer/Kiosk: kein "HubEx" sichtbar, nur Custom-Branding
  - Login-Seite mit Custom-Logo
  - Enterprise: Custom Domain (myproduct.example.com)

- [ ] Step 4 — Endkunden-Onboarding
  - Vereinfachter Registrierungsflow für Viewer-Accounts
  - Optional: Geräte-PIN-basiert (PIN liegt dem Produkt bei →
    Account + Device auto-verknüpft)

- [ ] Step 5 — Deployment-Package Export
  - Dashboard-Layouts + Automationen + Device-Profile + Branding + Rollen
  - Import auf anderer HubEx-Instanz
  - Basis für "Baue 1x, deploye 100x"

### Milestone H7: Edge Logic [todo]
> Automationen lokal auf dem ESP — Offline-fähig, Echtzeit.

- [ ] Step 1 — Edge-fähige Automationen markieren
  - Toggle "Edge-fähig (lokal auf Device)" im Automations-Builder
  - Initial: nur einfache If→Then, keine externen Aktionen, nur lokale Pin-Steuerung
  - Validierung: "Diese Automation kann nicht Edge-fähig sein weil [Grund]"

- [ ] Step 2 — Edge-Logic Compiler
  - Automation-Regeln → kompilierte C-Logik für ESP
  - Eingebettet in ESP-Firmware (Teil des Code-Generators aus H4)
  - Läuft lokal auch ohne WiFi/Internet

- [ ] Step 3 — Status-Sync bei Reconnect
  - ESP speichert Ausführungen lokal (Circular Buffer im Flash)
  - Bei Reconnect: Batch-Upload an HubEx
  - HubEx aktualisiert Variablen-History und Automation-Logs

### Phase 8 — Abhängigkeits-Graph

```
Phase 5-7 (Fundament)
  │
  ├── M14 (Typsystem) ──────────────► H3 (Component Library)
  ├── M15 (Device Wizard) ──────────► H4 (Code Generator)
  ├── M18 (Dashboard Builder) ──────► H6 (Produkt-Modus)
  ├── M19 (Automations-Engine) ─────► H7 (Edge Logic)
  ├── M13.2 (Branding) ────────────► H6 (White-Label)
  └── M26.3 (RBAC) ────────────────► H6 (Rollen)

Phase 8 intern:
  H1 (Hardware Abstraction) ← ZUERST
    └─► H2 (Bridge Protocol)
    └─► H3 (Component Library)
          └─► H4 (Code Generator)
  H5 (Retrofit/Smart-Devices) ← parallel, unabhängig
  H6 (Produkt-Modus) ← parallel, braucht nur Phase 5-7
  H7 (Edge Logic) ← braucht H4 + M19
```

> **HINWEIS:** Phase 8 baut auf Phase 5-7 auf. Architektur-Entscheidungen
> in Phase 5 (Typsystem, Device-Kategorien, Branding-Abstraction, RBAC)
> müssen so gebaut werden, dass Phase 8 später darauf aufsetzen kann.
> Die alte Bridge/Gateway-Architektur aus früheren Planungen ist in H2/H5 aufgegangen.

---

## Abhängigkeits-Graph (vereinfacht)

```
Phase 1-4 (Core + UI + Data + Integration) ✅
  │
  └─► Phase 5: UX-Überholung & Fundament (M13-M20) ✅
        │
        └─► Phase 5b: UX Completion ✅
              │
              └─► Phase 6: Erweiterung (M21-M24) ✅
                    │
                    └─► Phase 5c: Stabilität & Simulation ← AKTUELL
                          │
                          ├─► UX-F (Quick Fixes) ✅
                          ├─► SIM-1 (Device-Simulatoren) — ZUERST
                          ├─► SIM-2 (API-Config-Panel) — braucht SIM-1
                          ├─► UX-G (Entities → DeviceDetail) — parallel
                          ├─► UX-H (System Context Graph) — braucht UX-G
                          └─► UX-I (Automations-Builder) — parallel
                                │
                                └─► Phase 7: Enterprise & Business
                                      ├─► M14b (Computed Variables)
                                      ├─► M19b (Automation Erweiterung) — braucht UX-I
                                      ├─► M18b (Dashboard Embed)
                                      ├─► M26 (Security/RBAC)
                                      ├─► M27 (Skalierung)
                                      ├─► M33 (Simulator/Testbench) — braucht SIM-1
                                      └─► M36 (Flow Editor) — braucht UX-H
                                      │
                                      └─► Phase 8: Hardware & Produkt-Modus (H1-H7)
```

---

## Nächste 5 Sprints (Priorität)

| Sprint | Milestone | Fokus | Abhängigkeit |
|--------|-----------|-------|--------------|
| **Sprint UX-1** | UX-A Steps 1-6 | Flow-Korrekturen: Kontext-Navigation, Alert-Actions, Input/Output zugeklappt | — |
| **Sprint UX-2** | UX-B Steps 1-11 | Erklärungen, Tooltips, Bug-Fixes, Dashboard aufräumen | parallel zu UX-1 |
| **Sprint UX-3** | UX-C Steps 1-5 | DeviceDetail: System Context, Variable-Typ-Edit, Offline-ActionBar | Sprint UX-1 |
| **Sprint UX-4** | UX-D Steps 1-6 | Add Device Wizard (4 Flows: Hardware/Service/Bridge/Agent) | Sprint UX-3 |
| **Sprint UX-5** | UX-E Steps 1-4 | Platinen-Ansicht Node-Graph, Dashboard Auto-Suggest, Connect-Panel Inline | Sprint UX-3 |

> **Grundregel für ALLE zukünftigen Features:**
> Bei JEDEM neuen Feature wird geprüft:
> 1. Per REST-API erreichbar? (immer: ja)
> 2. Per Webhook triggerbar? (wenn Event-basiert: ja)
> 3. Per MQTT erreichbar? (wenn Echtzeit-relevant: ja)
> 4. Folgt es den 7 UX-Prinzipien? (Progressive Disclosure, Selektoren, Kontextuelles Arbeiten, Unterstützend, Minimalistisch, Wächst mit Komplexität, Verständliche Sprache)
> 5. In der API-Dokumentation beschrieben? (immer: ja)
