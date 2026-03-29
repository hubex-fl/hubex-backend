# HUBEX Build Reports

---

## M12.5: Pitch & Go-to-Market — 2026-03-28
**Status:** Done

### Deliverables

| Step | Deliverable |
|------|-------------|
| 1 | Pitch Deck (`docs/PITCH_DECK.md`) — 13-slide Marp-compatible deck with speaker notes, problem/solution/market/competition/business model/ask |
| 2 | Landing Page (`frontend/src/pages/Landing.vue`) — Full dark-themed public page at `/landing` with hero, features, architecture, comparison, pricing, CTA |
| 3 | Competitive Analysis (`docs/COMPETITIVE_ANALYSIS.md`) — 7 competitors, 11-dimension matrix, detailed per-competitor analysis |
| 4 | Pricing Model (`docs/PRICING.md`) — 3-tier Open Core (Free/Pro/Enterprise), FAQ, Build vs. Buy ROI, add-on pricing |

### Files changed
- `docs/PITCH_DECK.md` — New: 13-slide pitch deck
- `docs/COMPETITIVE_ANALYSIS.md` — New: 7 competitors, matrix + detailed analysis
- `docs/PRICING.md` — New: 3-tier pricing, FAQ, ROI calculation
- `frontend/src/pages/Landing.vue` — New: public landing page (hero, features, architecture, comparison, pricing)
- `frontend/src/router.ts` — Added `/landing` route with `meta: { layout: "public" }`
- `frontend/src/App.vue` — Added public layout bypass (no sidebar/auth wrapper)
- `ROADMAP.md` — M12.5 marked done, AKTUELL moved to M13

### Build verification
- TypeScript: 0 errors
- Vite build: success (Landing.vue = 24.45 kB / 6.95 kB gzip)

---

## M11 + M12: n8n Integration Complete + Developer Docs — 2026-03-28
**Status:** Done

### Milestone 11: n8n Integration (all 3 steps)

| Step | Deliverable |
|------|-------------|
| 1 | n8n Webhook Templates — HubexTrigger node with 8 event types |
| 2 | Custom n8n Node — Hubex.node.ts: Device, Telemetry, Alert, Variable CRUD |
| 3 | Variable Stream data source — getHistory, getSnapshot, getDefinitions, bulkSet |

**Files changed:**
- `n8n-nodes-hubex/nodes/Hubex/Hubex.node.ts` — Added "Variable Stream" resource with 4 operations + 7 parameters
- `n8n-nodes-hubex/package.json` — Added `variableStream` keyword

### Milestone 12: Developer Docs (all 4 steps)

| Step | Deliverable |
|------|-------------|
| 1 | API Docs Landing Page (`/api-docs`) — Swagger/ReDoc links, 10 API sections, auth flow, rate limits |
| 2 | Getting Started Guide (`docs/GETTING_STARTED.md`) — Prerequisites, setup, 6 first-steps with curl examples |
| 3 | ESP SDK + Variable Bridge (`docs/ESP_SDK.md`, `docs/VARIABLE_BRIDGE.md`) — Device lifecycle, bridge rules, coercion |
| 4 | Integration Guide (`docs/INTEGRATION_GUIDE.md`) — Python agent, n8n, webhooks, MQTT, automations |

**Frontend files:**
- `frontend/src/pages/ApiDocs.vue` — New page (UCard, UButton, UBadge components)
- `frontend/src/router.ts` — Added `/api-docs` route
- `frontend/src/layouts/DefaultLayout.vue` — Added "API Docs" sidebar entry in Admin group

**Build verification:**
- TypeScript check: passed (no errors)
- Vite build: passed (3.21s)

---

## M10 + M10.5: CI/CD Complete + Automation Engine — 2026-03-28
**Status:** ✅ Done

### Milestone 10: CI/CD & Deployment (all 4 steps marked done)

| Step | Deliverable |
|------|-------------|
| 1 | GitHub Actions (test, build, lint, coverage) |
| 2 | Docker Production Compose (Traefik, SSL, PostgreSQL, Redis) |
| 3 | One-Click Deploy Script + .env Generator |
| 4 | System Health Dashboard — `/system-health` page |

### Milestone 10.5: Automation Engine

**Backend:**
- `app/db/models/automation.py` — `AutomationRule` + `AutomationFireLog` models (JSONB, FK to organizations)
- `app/schemas/automation.py` — Pydantic schemas: Create / Patch / Out / FireLogOut
- `app/api/v1/automations.py` — Full CRUD + test-fire + history (last 50 entries)
- `app/core/automation_engine.py` — Background loop (5s polling, system events from events_v1)
  - Triggers: `variable_threshold`, `variable_geofence` (Haversine distance + Ray-Casting polygon), `device_offline`, `telemetry_received`
  - Actions: `set_variable`, `call_webhook` (httpx, fire-and-forget), `create_alert_event`, `emit_system_event`
  - Cooldown check, fire_count tracking, AutomationFireLog entries per firing
- `app/main.py` — `automation_task` added to background tasks
- `app/api/v1/router.py` — automations router registered
- `app/db/models/__init__.py` — AutomationRule + AutomationFireLog exported
- Alembic migration: `b876f187b765_add_automation_rules_and_automation_.py`

**Frontend:**
- `frontend/src/pages/SystemHealth.vue` — `/system-health` page
  - Polls `GET /health` + `GET /ready` + `GET /api/v1/metrics`
  - Overall status banner (green/yellow/red with animated dot)
  - Component status row: Backend API, Database, Redis
  - Metrics grid: Devices online, stale/offline, alerts, events 24h, uptime, entities, webhooks
  - Auto-refresh every 30s + manual refresh button + last checked timestamp
- `frontend/src/pages/Automations.vue` — `/automations` page
  - Rules list as IF→THEN cards with trigger summary + action summary
  - Enable/disable toggle, Test Fire (two-step confirm), Edit, Delete, History buttons
  - Create/Edit modal: Trigger picker (4 types with icons + descriptions) + dynamic config forms
  - Geofence config: Circle (lat/lng + radius slider) or Polygon (JSON textarea)
  - History modal: last 50 fire events with success/error status
- `frontend/src/lib/automations.ts` — typed API functions for all endpoints
- `frontend/src/router.ts` — `/system-health` + `/automations` routes added
- `frontend/src/layouts/DefaultLayout.vue` — "Automations" (Automation group) + "System Health" (Admin group) sidebar links

**TypeScript:** clean (0 errors)
**Vite build:** successful (SystemHealth: 10.47 kB, Automations: 34.71 kB)

---

## M9: Device Integration Demo — Complete
**Datum:** 2026-03-28 | **Status:** ✅ Done

### Ergebnis
Alle 5 M9-Steps waren bereits implementiert — nur Lücken geschlossen:

| Step | Was | Status |
|------|-----|--------|
| 1 | ESP SDK / Device Simulator | `app/simulator/__main__.py` — 287 Zeilen, Hello/Telemetry/Tasks/Variables/Ack |
| 2 | E2E Demo | `scripts/demo_e2e.py` + neues `scripts/e2e_demo.py` (9-Step httpx Demo) |
| 3 | QR Provisioning | `app/api/v1/pairing.py` — 615 Zeilen, Hello/Start/Claim/Confirm/QR |
| 4 | API-Device Demo | `scripts/api_device.py` + `docs/API_DEVICE.md` |
| 5 | MQTT Bridge | `scripts/mqtt_bridge.py` + `docs/MQTT_BRIDGE.md` |

### Neu implementiert
- **Variable Threshold Alert UI** (`frontend/src/pages/Alerts.vue`):
  - `variable_threshold` als neuer condition_type im Create/Edit Modal
  - Dynamische Felder: variable_key, threshold_operator (6 Ops mit Symbolen), threshold_value, device_uid
  - Rule Cards zeigen Threshold als lesbaren Ausdruck: `temperature > 40`
- **E2E Demo** erweitert um `variable_threshold` Alert + `variable.changed` Webhook
- **CC Dashboard** Parser komplett überarbeitet (flexible Regex für alle ROADMAP-Formate)

### Commits
- `d0c2114` — feat(m9): Device Integration Demo — mark complete
- `452d425` — feat(m9): comprehensive E2E demo script
- `eb04e2e` — feat(alerts): add variable_threshold UI to alert rules
- `7fbbb64` — fix(cc-dashboard): rewrite ROADMAP parser

---

## M8d: Data Hub Gap Fills — 7 Steps
**Datum:** 2026-03-28 | **Status:** ✅ Done | **Commit:** `975dacb`

### Was wurde gemacht

**Step 1 — History Retention Policy**
- `app/core/history_retention.py` — `history_retention_loop()` läuft stündlich
- Löscht `variable_history` Einträge älter als `HUBEX_HISTORY_RETENTION_DAYS` (default 30)
- In `app/main.py` lifespan als `retention_task` eingebunden

**Step 2 — DeviceDetail Inline Sparklines**
- `loadSparklines()` nach `loadVariables()` — lädt 1h History für alle int/float Variablen
- `VizSparkline` neben jedem numerischen Wert (72px × 22px, kein Extra-Request wenn keine Daten)
- "View in Streams →" Footer-Link im Variable-Panel

**Step 3 — Variable-basierte Alert Rules**
- Neuer `condition_type = "variable_threshold"` im Alert Worker registriert
- `_eval_variable_threshold()` prüft aktuellen Variablenwert gegen Schwellwert
- Operators: `gt`, `gte`, `lt`, `lte`, `eq`, `ne` — Fehler/Fehlkonfiguration wird graceful behandelt
- `VALID_CONDITION_TYPES` in `alerts.py` erweitert

**Step 4 — Variable → Webhook Bridge**
- `emit_system_event(db, "variable.changed", {...})` nach jedem Value-Write
- Payload: `variable_key`, `scope`, `device_uid`, `value`, `source`, `value_type`
- Webhook Dispatcher filtert `event_type = "variable.changed"` automatisch

**Step 5 — Telemetry Bridge: Nested Payload Support**
- `_flatten_payload(payload, max_depth=3)` mit Dot-Notation
- `{"sensors": {"temp": 23.5}}` → Variable Key `sensors.temp` wird gefunden
- Auch `{event_type}.sensors.temp` wird als Kandidat-Key geprüft

**Step 6 — Streams: Device Selector**
- `USelect` Dropdown mit `availableDevices` aus `GET /api/v1/devices`
- Nur `state === "claimed"` Devices erscheinen
- Letzte Auswahl in `localStorage["streams_device_uid"]` persistiert

**Step 7 — Bulk Variable Set Endpoint**
- `POST /api/v1/variables/bulk-set` mit max. 50 Items
- `allow_partial=true` → partial failure tracking; `false` → Rollback bei Fehler
- Antwort: `BulkSetResult { succeeded[], failed[], total, success_count }`

**USelect Fix**
- `options` prop von required auf optional (`options?:`) geändert
- `<slot v-else />` Fallback für native `<option>` children hinzugefügt
- Alle vorherigen Vue prop-warnings damit behoben

### Commits
- `f49c8c4` — feat(m8c): Variable Stream Visualization System — V1-V5 complete
- `975dacb` — feat(m8d): Data Hub gap fills — 7 steps complete

### Nächster Schritt
`PROMPT_PHASE_9_1.md` — Variable-Alert UI + GitHub Actions CI

---

## Variable Stream Visualization System — M8c V1-V5
**Datum:** 2026-03-28 | **Status:** ✅ Done

### Was wurde gemacht

**V1 — Backend CRUD + History** (in Main)
- `display_hint` + `category` in VariableDefinition
- `variable_history` Tabelle (BigInt, Zeitreihe, numeric_value denormalisiert)
- `PATCH/DELETE /variables/definitions/{key}` + `GET /variables/history`
- History-Recording nach jedem Value-Write (source: user/device/telemetry)

**V2 — Widget-Komponenten (Grafana/HA/n8n-Design)**
- `lib/viz-types.ts`, `lib/viz-resolve.ts`, `composables/useVariableHistory.ts`
- `VizSparkline.vue` — Pure SVG (Area Fill, Gradient, Dot)
- `VizLineChart.vue` — Chart.js + date-fns Zeitachse
- `VizGauge.vue` — SVG Radial 210°→330° (HA-style, dynamische Farbe)
- `VizBoolIndicator.vue` — Status Dot + Timeline Bar
- `VizLogView.vue` — Mono-Log mit Source-Badges (n8n-style)
- `VizJsonViewer.vue` — Klappbarer JSON-Baum (renderless)
- `VizMapView.vue` — Leaflet lazy-loaded, dark tiles
- `VizImageView.vue` — URL-Image mit Auto-Refresh
- `VizWidget.vue` — Grafana Panel Container (Header, TimeRange, Skeleton, Footer)

**V3 — Variables.vue Full CRUD + Inline Viz**
- Create/Edit-Definition/Set-Value-Modals mit Version-Conflict-Flow
- Echtes DELETE mit Cascade, Sparkline-Spalte, Expandable-Detail-Row
- Komplette Neuentwicklung mit Design System

**V4 — Telemetry Bridge**
- `_bridge_telemetry_to_variables()` — fire-and-forget asyncio.create_task
- Matching: `{event_type}.{key}` und `{key}` gegen device_writable Definitionen
- Wert-Coercion + Upsert VariableValue + record_history(source="telemetry")

**V5 — VariableStreams.vue**
- Grafana-style Real-Time Grid: 2/3/4 Spalten
- TimeRange-Tabs, Card-Selection, Fullscreen-Overlay, Auto-Refresh 15s
- "Data" Gruppe in Sidebar (Variables + Streams)

**Roadmap-Update**
- M8c als ✅ Done markiert
- M8d neu: History-Retention, DeviceDetail-Vars, Variable-Alerts, Variable→Webhook
- M20: explizite Abhängigkeit zu VizWidget dokumentiert
- Abhängigkeits-Graph + nächste-3-Sprints Tabelle

### Tests
- TypeScript: ✅ 0 errors
- Vite Build: ✅ 3.14s, 0 warnings
  - Variables.vue: 23KB gzip (vorher 255KB vor Code-Split)
  - VizWidget (Chart.js): 75KB gzip — lazy chunk
  - Leaflet: 43KB gzip — lazy chunk (nur wenn Map-Widget)

### Design-Leitsätze umgesetzt
- n8n: Monospace-Logs, Source-Badges, Daten-zentriert
- Grafana: Panel-Container, TimeRange-Tabs, Skeleton
- Home Assistant: Radial Gauge, Status Dot, Bool-Timeline

### Nächster Sprint (M8d)
1. History Retention Policy (Background-Task, 30d default)
2. DeviceDetail Variable-Panel (Sparklines + VizWidget)
3. Variable-basierte Alert-Rules (threshold_operator)

---

## Milestone 9 Step 5 — Standard-Device Connector PoC: Shelly/Tasmota MQTT Bridge
**Date:** 2026-03-27
**Status:** ✅ Done — **Milestone 9 COMPLETE**

### Files Created

#### `scripts/mqtt_bridge.py` (~290 lines)
Python MQTT bridge that subscribes to Shelly/Tasmota topics and forwards data to HUBEX as telemetry.

**Architecture:**
- `BridgeState` class: thread-safe accumulator + rate limiter; accumulates fields per MQTT device within the interval window, then pushes as a batch
- MQTT loop runs in background thread (`client.loop_start()`); main thread runs heartbeat loop + graceful shutdown
- On exit: `flush_all()` pushes any accumulated but not-yet-sent fields before disconnecting

**Field extraction (`_parse_payload`):**
- Tries JSON parse first; falls back to plain float string (Shelly per-relay topics like `power`, `energy`)
- Recursive `_extract_numeric()` extracts all numeric leaf values from nested JSON
- All fields namespaced as `{device_id}.{field}` — multi-device data in one telemetry stream
- `cmnd/#` topics silently ignored (Tasmota command topics)

**Rate limiting:** configurable per-device interval (default 10s); fields accumulated between pushes (last value wins)

**Supported formats:**
- Shelly: `shellies/{device-id}/relay/0/power` → `"12.5"` (plain) or `shellies/{device-id}/status` → JSON
- Tasmota: `tele/{device-id}/SENSOR`, `tele/{device-id}/STATE`, `stat/{device-id}/STATUS` → JSON

**CLI Args:** `--mqtt-host`, `--mqtt-port`, `--mqtt-user`, `--mqtt-pass`, `--topic`, `--device-type`, `--interval`, `--auto-pair`, `--token`

#### `docs/MQTT_BRIDGE.md`
Usage guide with quick start, full options table, Shelly/Tasmota topic format tables, rate limiting explanation, and architecture diagram.

### Milestone 9 Status
🎉 **Milestone 9: Device Integration Demo — COMPLETE** (all 5 steps done)
- Step 1: ESP32 SDK (single-header HubexClient.h)
- Step 2: E2E Demo script (8-step automated walkthrough)
- Step 3: QR-Code Pairing (backend endpoint + frontend display)
- Step 4: API-Device Demo (REST API as virtual device)
- Step 5: MQTT Bridge (Shelly/Tasmota → HUBEX telemetry)

### Next Step
**PROMPT_PHASE_10_1.md** — CI/CD: GitHub Actions (test, build, lint)

---

## Milestone 9 Step 4 — API-Device Demo: External REST API as Virtual Device
**Date:** 2026-03-27
**Status:** ✅ Done

### Files Created

#### `scripts/api_device.py` (~315 lines)
Runnable Python script that connects any external REST JSON API as a HUBEX virtual device.

**Features:**
- Full auto-pair flow: login (JWT) → hello → user-claim → confirm → persist device token
- Poll loop: `GET --source-url` → extract numeric fields → `POST /api/v1/telemetry` → `POST /edge/heartbeat`
- `poll_interval_s` override from `GET /edge/config` — adjustable from dashboard without restart
- `_extract_fields()` — recursive JSON walker: auto-detects all numeric leaf fields if `--fields` not specified; handles nested objects (first level flattened), arrays (first element only)
- Signal handler (SIGINT/SIGTERM) → graceful exit, sleep in 0.5s chunks for fast Ctrl+C response
- Colorized terminal output (ANSI codes): ✓ ok, ✗ error, → info, ⚠ warn

**CLI Arguments:**
`--server`, `--email`, `--password`, `--uid`, `--source-url`, `--fields`, `--interval`, `--auto-pair`, `--token`

Default `--source-url`: Open-Meteo Munich weather API (no key required)

#### `docs/API_DEVICE.md`
Usage guide with quick start, full options table, three example invocations (weather station, service monitor, pre-paired), and field auto-detection documentation.

### Next Step
**PROMPT_PHASE_9_5.md** — Standard-Device Connector PoC (Shelly/Tasmota via MQTT)

---

## Milestone 9 Step 3 — Provisioning Flow: QR-Code Pairing
**Date:** 2026-03-27
**Status:** ✅ Done

### Files Changed

#### `app/api/v1/pairing.py`
Added new endpoint: `GET /api/v1/devices/pairing/{pairing_code}/qr`
- Validates pairing session exists (404) and is not expired (410)
- Encodes `{"code": pairing_code, "uid": device_uid}` as compact JSON into QR code SVG
- Uses `qrcode[svg]` with `SvgPathImage` factory (box_size=4, border=2, error_correction=M)
- Returns `image/svg+xml` response — embeddable directly via `v-html`

#### `requirements.txt`
Added: `qrcode[svg]==8.0`

#### `frontend/src/pages/Devices.vue`
- `pairingQrSvg` ref + `pairingQrLoading` ref
- `watch(pairingClaimCode)`: fetches QR SVG from backend when code ≥6 chars, clears on reset
- Template: white 88×88px box with `v-html="pairingQrSvg"`, animated skeleton while loading, "Scan to pair from mobile" label — hidden when no QR available

### Next Step
**PROMPT_PHASE_9_4.md** — API-Device Demo

---

## Milestone 9 Step 2 — End-to-End Demo: ESP → Telemetry → Alert → Webhook → n8n
**Date:** 2026-03-27
**Status:** ✅ Done

### Files Created

#### `scripts/demo_e2e.py` (~380 lines)
8-step automated E2E demo script with full color output.

**Steps executed:**
1. Auth (login → JWT)
2. Pair device (hello → user-claim → confirm → device_token)
3. Push 5 telemetry readings with simulated sensor data
4. Create alert rule (device_offline threshold, 60s window)
5. Register webhook subscription (all events → localhost:9999/webhook)
6. Fetch event stream (last 20 events, show device/telemetry events)
7. Push edge config variable (`poll_interval_s = 10`)
8. Cleanup (delete alert rule, webhook, unclaim device) — skipped with `--keep`

**Args:** `--server`, `--email`, `--password`, `--dry-run` (prints plan without executing), `--keep` (skip cleanup)

#### `docs/E2E_DEMO.md`
Full curl walkthrough for each of the 8 steps + n8n integration section (webhook node setup, HTTP Request node for HUBEX API calls, example automation flow for alert→email).

### Next Step
**PROMPT_PHASE_9_3.md** — Provisioning Flow (QR-Code Pairing)

---

## Milestone 9 Step 1 — ESP32 SDK: Pairing, Heartbeat, Edge Config, Telemetry, OTA
**Date:** 2026-03-28
**Status:** ✅ Done

### Files Created

#### `sdk/esp32/HubexClient.h` (single-header C++ library, ~330 lines)
Full Arduino/ESP32 library. Dependencies: ArduinoJson ≥7, HTTPClient, WiFiClientSecure, Preferences, Update.

**Public API:**
- `HubexClient(serverUrl, deviceUid)` — constructor
- `begin(firmwareVersion, skipTls)` — load stored token from NVS
- `isPaired()` — true if device has stored token
- `clearToken()` — force re-pairing
- `ensurePaired()` — blocking loop: POST /api/v1/devices/pairing/hello until claimed; shows pairing code on Serial; stores token in NVS via Preferences
- `heartbeat()` — POST /edge/heartbeat with firmware_version
- `getConfig(outVars, outTasks)` — GET /edge/config, populates two JsonDocuments
- `getVar(key, default)` — convenience: single variable as String
- `pushTelemetry({{"key", float}, ...})` — POST /api/v1/telemetry with initializer list
- `pushTelemetry(JsonDocument&)` — overload for pre-built payload
- `checkOtaInfo(outInfo)` — GET /ota/check, populates HubexOtaInfo
- `checkOta()` — full flow: check → download → Update.writeStream → ESP.restart on success; ACKs rollout status at each step

**Implementation notes:**
- Token stored in NVS namespace `"hubex"` (survives power cycle)
- HTTPS: creates WiFiClientSecure per request; `setInsecure()` when skipTls=true
- `HubexResult` = `{bool ok, int httpCode, String error}` — all methods return this
- `HubexField = std::pair<const char*, float>` for telemetry

#### `sdk/esp32/examples/basic_device/basic_device.ino`
Minimal working sketch showing full lifecycle: WiFi connect → `ensurePaired()` → loop with heartbeat + simulated sensor readings + telemetry push + config var read + OTA check.

### Next Step
**PROMPT_PHASE_9_2.md** — End-to-End Demo Script: Device → Telemetry → Alert → Webhook → n8n

---

## Hotfix — Device Health Thresholds + DeviceDetail Visual Polish
**Date:** 2026-03-28
**Status:** ✅ Done
**TS Check:** ✅ 0 errors
**Vite Build:** ✅ 124 modules, built in 1.80s (DeviceDetail: 43.07 kB → 12.94 kB gzip)

### Changes Made

#### `app/api/v1/devices.py` — Backend health threshold fix
- `online_window`: `timedelta(seconds=30)` → `timedelta(seconds=60)`
- List endpoint: `age_seconds <= 30` → `age_seconds <= 60` (ok), `age_seconds <= 120` → `age_seconds <= 300` (stale)
- Detail endpoint: same threshold changes applied
- **Fixes**: device badge flickering between `stale` and `ok` every 30s during normal operation

#### `frontend/src/pages/DeviceDetail.vue` — Visual polish
- **Page header**: Simplified to breadcrumb only (`← Devices / <device uid>`) — removed duplicate action buttons (were also in hero card)
- **Telemetry panel**: Label changed from "Telemetry" to "↓ Input · Telemetry" with cyan `↓` arrow + blue left border (`border-l-[var(--accent-cyan)]`)
- **Variables panel**: Label changed from "Variables" to "↑ Output · Variables" with lime `↑` arrow + lime left border (`border-l-[var(--accent-lime)]`)

### Root Cause of Badge Flickering
The backend used `ok` threshold of `≤30s`. With a 30s poll interval on the device, the backend flip-flopped between `ok` and `stale` each cycle. Raising to `≤60s` (ok) and `≤300s` (stale) gives proper stability.

---

## Phase 8b Step 6 — Dashboard Rewrite: Hero Stats, Online Arc, Quick Action Cards
**Date:** 2026-03-28
**Status:** ✅ Done — **Milestone 8b COMPLETE**
**TS Check:** ✅ 0 errors
**Vite Build:** ✅ 124 modules, built in 1.79s (DashboardPage: 23.40 kB → 5.98 kB gzip, was 16.46 kB)

### Changes Made

#### `frontend/src/pages/DashboardPage.vue`
Replaced flat 6-card metric grid with a two-row graphical hero layout. All existing logic (event stream, health ring, alerts panel) preserved.

**New script additions:**
- `ARC_R`, `ARC_CIRC` constants (R=30)
- `arcDash`, `arcGap` computed — maps `onlinePct` to SVG stroke-dasharray
- `arcStroke` computed — `var(--status-ok)` ≥80%, `var(--status-warn)` ≥50%, `var(--status-bad)` otherwise

**Section 1 — Hero Stats (3 large tiles, `grid-cols-1 md:grid-cols-3`):**
- **Total Devices**: `text-5xl` count + color-segmented health bar (green/amber/red) + breakdown text
- **Online Now**: `text-5xl` count (green) + contextual label ("Fleet healthy" / "Partial outage" / "Major outage") + inline SVG arc showing `onlinePct%` with dynamic stroke color
- **Active Alerts**: `text-5xl` count (red if firing, muted if 0) + "All clear" or "X rules firing" sub-label + pulsing UBadge when firing

**Section 2 — Info Stats (3 compact tiles, `grid-cols-1 sm:grid-cols-3`):**
- Entities (clickable → `/entities`), Events 24h (clickable → `/events`), Uptime
- Icon + `text-2xl` number + label pattern
- Hover border tint on clickable tiles

**Section 3 — Quick Actions (4 cards, `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`):**
- Replaced 3 plain UButtons with 4 icon cards using `group-hover` transitions
- Cards: Pair Device, View Devices, Create Alert, View Entities
- Each card: colored icon + title + description + chevron arrow

**Unchanged:** welcome banner, device health ring (donut SVG), recent alerts panel, event stream

### Milestone Status
🎉 **Milestone 8b: UI/UX Redesign — Intuitive & Grafisch — COMPLETE** (all 6 steps done)

### Next Step
**Milestone 9 Step 1** — ESP SDK Update (OTA check, edge config, heartbeat)

---

## Phase 8b Step 5 — Empty States & Onboarding
**Date:** 2026-03-28
**Status:** ✅ Done
**TS Check:** ✅ 0 errors
**Vite Build:** ✅ 124 modules, built in 1.92s

### Changes Made

#### `frontend/src/pages/EntitiesPage.vue`
- Improved empty state: title "No entities yet", description explains what entities are ("Entities represent logical things — rooms, machines, systems — that group your devices")
- Added cube/grid SVG icon to empty state
- Filter-empty state now has a search/magnifying icon instead of generic icon

#### `frontend/src/pages/Alerts.vue`
- Imported `UEmpty` component
- Events tab: replaced raw SVG+text div with `<UEmpty>` — title "No alert events", description "Alert events appear here when a rule is triggered. They are generated automatically when conditions are met."
- Rules tab: replaced raw SVG+text div with `<UEmpty>` — title "No alert rules", description "Alert rules notify you when devices go offline or metrics cross thresholds. Create your first rule to get started." + "Create Rule" CTA button inside the empty state

#### `frontend/src/pages/Events.vue`
- Updated `UEmpty` description from "Start polling on a stream to see events here." → "Events are emitted when devices connect, send telemetry, or tasks run. Enter a stream name and start polling to see them here."

#### `frontend/src/pages/Audit.vue`
- Updated `UEmpty` description from "No entries match the current filters." → "Every API action is logged here for traceability. Audit entries will appear as you use the platform."

#### `frontend/src/pages/DashboardPage.vue`
- Added welcome banner above the metrics grid: shown when `!metricsLoading && metrics && metrics.devices.total === 0`
- Banner: cyan-tinted card with rocket icon, "Welcome to HUBEX" title, "No devices yet — pair your first device to start monitoring." + "Pair Device" button → `/devices`
- Banner disappears automatically once any device exists

### Next Step
**PROMPT_PHASE_8B_6.md** — Dashboard Rewrite: grafische Device-Kacheln, Online%-Arc, Echtzeit-Ring-Diagramm (Milestone 8b Step 6)

---

## Phase 8b Step 4 — Server Offline UX: Backend-weg-Indikator, Reconnect
**Date:** 2026-03-27
**Status:** ✅ Done
**TS Check:** ✅ 0 errors
**Vite Build:** ✅ 124 modules (+4 new), built in 1.78s

### Changes Made

#### `frontend/src/stores/serverHealth.ts` (new)
New Pinia store:
- `serverOnline` ref (default `true`)
- `lastOfflineAt` ref — timestamp when server first went offline
- `markOffline()` — sets `serverOnline = false`, records timestamp, starts background poller
- `markOnline()` — sets `serverOnline = true`, stops poller, returns `wasOffline` boolean
- Background poller: `setInterval` at 5s, hits `GET /health` with 3s timeout (AbortController), calls `markOnline()` on success

#### `frontend/src/lib/api.ts`
- Import `useServerHealthStore`
- `apiFetch` now wraps `fetch()` in try/catch: network error → `markOffline()` + rethrow
- Status 502/503/504 → `markOffline()` + throw
- Any successful response → `markOnline()`

#### `frontend/src/components/ui/UOfflineBanner.vue` (new)
- Fixed `top-0 inset-x-0 z-[200]` amber banner
- Amber `bg-amber-900/90 backdrop-blur-sm` with wifi-off icon, "Server unreachable" label, spinning reconnect indicator
- Elapsed timer (ticks every 1s via `setInterval`, starts/stops with `serverOnline` watcher)
- `Transition name="offline-banner"` — slides in from top, fades out on recovery

#### `frontend/src/stores/toast.ts`
- Suppresses `variant === "error"` toasts when `!serverOnline` — prevents cascading "Failed to load" errors while the banner already explains the situation

#### `frontend/src/layouts/DefaultLayout.vue`
- Import `useServerHealthStore` + `UOfflineBanner`
- `<UOfflineBanner />` rendered at top of layout (before mobile backdrop)
- `watch(serverHealth.serverOnline)`: shows "Server reconnected" success toast (3s) when coming back online
- `<main>` gets `relative` class + dim overlay `<div v-if="!serverHealth.serverOnline" class="absolute inset-0 bg-[var(--bg-base)]/60 z-10 pointer-events-none" />`

### Next Step
**PROMPT_PHASE_8B_5.md** — Empty States & Onboarding: hilfreiche Erklärungen auf Entities, Alerts, Events, Audit, Dashboard (Milestone 8b Step 5)

---

## Phase 8b Step 3 — Sidebar Navigation: Grouping, Coming Soon, Cleanup
**Date:** 2026-03-27
**Status:** ✅ Done
**TS Check:** ✅ 0 errors
**Vite Build:** ✅ 120 modules, built in 1.81s

### Changes Made

#### `frontend/src/layouts/DefaultLayout.vue`
Replaced flat `navItems` array with `navGroups` structure. Removed clutter (System Stage, Token Inspector) from main nav. Added Entities (was in router but missing from nav).

**New data structure:**
```ts
type NavItem = { to, label, icon, cap, comingSoon? }
type NavGroup = { label: string; items: NavItem[] }
const navGroups: NavGroup[] = [ /* 4 groups */ ]
const visibleNavGroups = computed(() => navGroups filtered by cap, comingSoon items always shown)
```

**4 Navigation Groups:**
- **Core**: Dashboard, Devices, Entities
- **Automation**: Alerts, Automations (Soon), Executions (Soon)
- **Observability**: Events, Audit, Trace Hub (Soon), Correlation (Soon)
- **Admin**: Settings

**Coming Soon items** (`comingSoon: true`):
- Non-interactive (`cursor-not-allowed opacity-40 select-none`)
- Show "Soon" chip when sidebar is expanded
- Tooltip shows "— Coming Soon" when collapsed
- Automations (was Effects), Executions, Trace Hub, Correlation

**Section labels** (desktop expanded + mobile):
- `text-[10px] uppercase tracking-widest` above each group
- Hidden when desktop sidebar is collapsed — replaced by subtle `border-t` divider
- First group has no top padding

Both desktop nav and mobile overlay nav updated to use groups.

**Removed from nav:**
- System Stage (replaced by Entities with proper route `/entities`)
- Token Inspector (developer tool, not needed in main nav)
- Observability (Coming Soon — listed in Observability section as Correlation instead)

### Next Step
**PROMPT_PHASE_8B_4.md** — Server Offline UX: backend-unreachable banner, content dimming, auto-reconnect (Milestone 8b Step 4)

---

## Phase 8b Step 2 — Device List: Card View, Empty States, UX Improvements
**Date:** 2026-03-27
**Status:** ✅ Done
**TS Check:** ✅ 0 errors
**Vite Build:** ✅ 120 modules, built in 1.79s (Devices: 32.52 kB → 9.47 kB gzip)

### Changes Made

#### `frontend/src/pages/Devices.vue`
Added card-view toggle, improved empty states, mobile pairing always-visible behavior, and skeleton loading states.

**New script additions:**
- `deviceView` ref — persisted to `localStorage` (`hubex:device-view`), default `"table"`
- `watch(deviceView)` — syncs to localStorage on change
- `hasActiveFilter` computed — `searchQuery !== "" || filterBy !== "all"`
- `cardHealthBorder(health)` — returns left-border CSS class (green/amber/red/gray by health)
- `clearFilters()` — resets searchQuery + filterBy to defaults
- `onMounted`: auto-opens pairing panel on mobile (`window.innerWidth < 768`)

**Template changes:**

1. **View Toggle** — toolbar now has `[≡ Table]  [⊞ Cards]` buttons, active button highlighted with accent-cyan tint
2. **Pairing Section** — collapse toggle hidden on mobile (`hidden md:flex`); content `:class` logic keeps pairing always visible on mobile regardless of `pairingOpen`; "First time? Start here →" hint shown when `devices.length === 0`
3. **Empty States (table view)** — two contextual states:
   - No devices + no filter: "No devices yet" + description + "Pair Device" button (scrolls to pairing)
   - Filtered + no results: "No devices match" + description + "Clear filters" button
4. **Table view** — wrapped in `v-if="deviceView === 'table'"`, existing table preserved intact
5. **Card grid view** — `v-else`, `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`:
   - Loading: 8 USkeleton placeholder cards
   - Empty: contextual UEmpty with action buttons (same logic as table)
   - Device cards: left-border health color, device UID (monospace truncated), health+state UBadge pair, last-seen/online indicator (pulsing dot), action button (Open/Pair by state), bulk checkbox when `bulkMode` active, hover glow + cursor-pointer, `v-memo` for performance

**Preserved intact:**
- All existing functionality: bulk unclaim, bulk purge, pairing flow, sort/filter/search, row click navigation, all API calls

### Next Step
**PROMPT_PHASE_8B_3.md** — Sidebar Navigation: Grouping (Core/Automation/OTA/Observability/Admin), Coming Soon badges, section labels (Milestone 8b Step 3)

---

## Phase 8b Step 1 — Device Detail Rewrite: Graphical View
**Date:** 2026-03-27
**Status:** ✅ Done
**TS Check:** ✅ 0 errors
**Vite Build:** ✅ 120 modules, built in 2.13s (DeviceDetail: 39.48 kB → 12.30 kB gzip)

### Changes Made

#### `frontend/src/pages/DeviceDetail.vue`
Full template rewrite from legacy CSS (`.card`, `.pill`, `.btn`) to design system. All existing logic preserved exactly.

**New computed helpers added to script:**
- `heroRingColor` — CSS var string based on device health (ok/stale/dead)
- `heroRingOnline` — boolean, triggers ring pulse animation
- `healthBadgeStatus`, `stateBadgeStatus`, `taskBadgeStatus` — badge status mappers
- `latestPayloadFields` — extracts latest telemetry payload as `{key, value}` tiles
- `visibleTelemetryFields` — sliced to MAX_TILES=8 with show-all toggle
- `showAllTelemetry` ref — for expand/collapse of telemetry tiles
- `historyStatusBadge` — replaces `historyStatusClass` with badge-compatible return type
- `variableSourceLabel` — returns "override" / "default" (shortened)

**Template structure (new):**
1. **Page Header** — Back button (← Devices), device UID as title, health + state badges, Refresh/Copy UID/Pairing Panel actions
2. **Unclaimed warning** — amber banner with icon when device not claimed
3. **Hero Section** — `md:grid-cols-[200px_1fr]` layout:
   - Left: SVG status ring (R=52, full arc, color=health, pulse animation when online)
   - Right: 2×2 stat cards (Last Seen, State, Current Task, Lease Expires)
4. **Main Panels** — `lg:grid-cols-2` layout:
   - Telemetry card: live dot indicator, metric tiles grid (2-col), fallback to raw table, UEmpty state
   - Variables card: inline edit with pencil/delete/reveal icon buttons, add-override form with USelect+UInput, source badge
5. **Recent Tasks** — table with UBadge status, responsive (hidden columns on mobile)
6. **Recovery** — reissue token flow with new token display card, audit entries list
7. **Danger Zone** — red-border card, unclaim confirm flow

**Removed:**
- All legacy CSS classes (`.card`, `.card-header-row`, `.pill`, `.pill-ok`, etc.)
- Inline `style=""` attributes replaced with Tailwind utilities
- `<style scoped>` reduced to single `ring-pulse` keyframe animation

### Next Step
**PROMPT_PHASE_8B_2.md** — Device List: Card-View Toggle, Empty States, UX Improvements (Milestone 8b Step 2)

---

## Phase 8 Step 9 — Mobile Responsive + Final Polish
**Date:** 2026-03-27
**Status:** ✅ Done
**TS Check:** ✅ 0 errors
**Vite Build:** ✅ 120 modules, built in 1.84s

### Changes Made

#### `frontend/src/layouts/DefaultLayout.vue`
- Added `mobileOpen` ref for mobile overlay state
- Hamburger button (visible `md:hidden`) in header — opens mobile sidebar
- Desktop sidebar unchanged (collapsed/expanded behavior retained)
- Mobile: full-width `w-64` overlay sidebar with `z-40`, animated slide-in from left
- Semi-transparent backdrop (`bg-black/60 backdrop-blur-sm`) with click-outside-to-close
- Close button (X) inside mobile sidebar header
- Nav links on mobile are `py-3` (44px+ touch targets, h-5 icons)
- Route changes auto-close the mobile sidebar (`handleNavClick`)
- CSS transitions: `backdrop` (fade), `slide` (translateX)
- Page content padding: `p-3 md:p-6` (tighter on mobile)

#### `frontend/src/pages/DashboardPage.vue`
- Metric cards grid: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`
- Event stream rows: timestamp hidden on `<sm`, stream hidden on `<md` — cleaner on mobile

#### `frontend/src/pages/Events.vue`
- Full rewrite from legacy CSS (`.page`, `.card`, `.btn`) to design system
- Uses: `UCard`, `UButton`, `UInput`, `UBadge`, `USkeleton`, `UEmpty`
- Form rows stack vertically on mobile, horizontal on `sm:`+
- Status bar shows cursor, next_cursor, caught-up, polling indicator
- Table: `Trace` column hidden on `<md`, `overflow-x-auto` for scroll
- Error state uses red-border card pattern
- Loading state with skeleton rows

#### `frontend/src/pages/Audit.vue`
- Full rewrite from legacy CSS to design system
- Filter bar stacks vertically on mobile, horizontal on `sm:`+
- Table: `Time` hidden on `<sm`, `Resource` hidden on `<md`
- Selected row highlighted with cyan tint
- Detail panel closes with X button, JSON formatted with `JSON.stringify(detail, null, 2)`
- Loading skeletons, empty state with icon

#### `frontend/src/components/ui/UToast.vue`
- Mobile: full-width `right-2 left-2`, desktop: `sm:right-4 sm:left-auto sm:w-80`
- Toasts now properly fill screen width on mobile instead of overflowing

### Next Step
**PROMPT_PHASE_8B_1.md** — Device Detail Rewrite: grafische Ansicht mit Status-Ring, Input/Output Panels, Live Traffic (Milestone 8b Step 1)

---

## M16 — Kontextuelles Arbeiten (2026-03-29)

### Implementiert
**Step 1 — Connect-Panel (Slide-Over)**
- `useConnectPanel.ts` — module-level singleton composable (isOpen, context refs)
- `ConnectPanel.vue` — Teleport-to-body, backdrop + right-side slide-over (translateX animation)
- Fetches: variables via `/api/v1/variables/device/{uid}`, alerts/rules, automations
- Quick Actions grid + Connected Variables + Alert Rules + Automations sections
- Mounted globally in App.vue

**Step 2 — Kontextmenüs**
- `ContextMenu.vue` — floating dropdown, outside-click + Escape close, `@keyframes ctx-in`
- `Devices.vue` — "..." button on cards (group-hover), deviceMenuItems() mit View/Connections/Alerts/Automations/Unclaim
- `Variables.vue` — "..." in actions column, varMenuItems() mit Edit/Connections/Alert/Automation

**Step 3 — Proaktive Empty States**
- `Devices.vue` — dual CTAs "Pair Hardware Device" + "Add Device/API Device", guidance text
- `Variables.vue` — icon + h3 + guidance + dual CTAs + auto-discover hint
- `Alerts.vue` — warning icon + "Get notified when something happens" + Create Alert CTA
- `Automations.vue` — 3 clickable quick-template cards + "Start from scratch" button; `openFromTemplate()` pre-fills form

**Step 4 — Progressive Action-Bars**
- `useActionBar.ts` — localStorage-backed per-device dismissal (`hubex_action_bar` key)
- `ActionBar.vue` — 4 contextual suggestions, individual × dismiss + header × for full bar hide
- `DeviceDetail.vue` — ActionBar nach Breadcrumb, Connections-Button im Header

### Neue Dateien
- `frontend/src/composables/useConnectPanel.ts`
- `frontend/src/composables/useActionBar.ts`
- `frontend/src/components/ContextMenu.vue`
- `frontend/src/components/ConnectPanel.vue`
- `frontend/src/components/ActionBar.vue`

### Verifikation
- `tsc --noEmit` → EXIT 0
- `vite build` → 503+ modules, EXIT 0, ✓ built in ~10s
- Build-Größe DeviceDetail.js: 63.44 kB, Devices.js: 54.07 kB

### Next Step
**M17 — Realtime & Notifications**: WebSocket Layer + Notification Center

---

## M17 — Realtime & Notifications Steps 1+2 (2026-03-30)

### Implementiert

**Backend — WebSocket Layer**
- `app/realtime.py` — `UserHub` class: `push()`, `push_notification()`, `broadcast_event()`, `connection_count`
- `app/api/v1/ws_user.py` — User WS endpoint `/api/v1/ws?token=JWT` mit JWT-Auth, 30s ping keepalive, max 100 connections
- `app/main.py` — `user_ws_router` eingebunden, CORS auf Port 5174 erweitert

**Backend — Notification Center**
- `app/db/models/notifications.py` — `Notification` model (user_id, type, severity, title, message, entity_ref, read_at, created_at)
- `app/core/notification_service.py` — `create_notification()` + `create_notification_all_users()` mit WS-Push
- `app/api/v1/notifications.py` — CRUD: GET list, GET unread-count, PATCH read, PATCH read-all, DELETE
- `app/api/v1/router.py` — notifications router included
- `alembic/versions/54b50ffdaa88_add_notifications_table.py` — Migration, applied ✅
- `app/core/alert_worker.py` — `create_notification_all_users()` bei Alert-Fire

**Frontend — useWebSocket + NotificationBell**
- `frontend/src/composables/useWebSocket.ts` — Module-level singleton, Auto-Reconnect mit Backoff (1s→30s), Notification + Event handler sets
- `frontend/src/lib/notifications.ts` — API client: fetchNotifications, fetchUnreadCount, markRead, markAllRead, deleteNotification
- `frontend/src/components/NotificationBell.vue` — Bell + Badge + Dropdown Panel; WS-Handler für Live-Updates; formatTime()
- `frontend/src/layouts/DefaultLayout.vue` — NotificationBell eingebunden, `ws.start()` in onMounted

### Verifikation
- `alembic upgrade head` → notifications table erstellt
- `tsc --noEmit` → EXIT 0 (main + worktree)
- `vite build` → EXIT 0, ✓ ~10s (main + worktree)

### Steps 3+4 (Preferences + Email) → TODO für späteres Milestone-Update

### Next Step
**M18 — Dashboard Builder**: Dashboard/Widget Model + Grid Editor + Steuerungs-Widgets


---

## M18: Dashboard Builder � 2026-03-30

### Status: DONE (Steps 1�5)

### Was gebaut

**Backend (neu):**
-  +  SQLAlchemy Models mit 12-Spalten CSS-Grid-Layout
  (grid_col, grid_row, grid_span_w, grid_span_h)
- Alembic Migration  � erstellt dashboards + dashboard_widgets Tabellen
- Vollst�ndige CRUD API :
  - GET/POST /dashboards, GET/PUT/DELETE /dashboards/{id}
  - GET /dashboards/default
  - POST /dashboards/{id}/widgets, PUT/DELETE /dashboards/{id}/widgets/{wid}
  - PUT /dashboards/{id}/layout (Bulk-Positions-Update)

**Frontend (neu):**
-  � typsicherer API-Client + 5 built-in Templates
-  � �bersichtsliste mit 2-Step Create-Wizard:
  Step 1: Template-Auswahl (Blank / Climate / Server / Fleet / Energy)
  Step 2: Name, Description, Default-Flag
-  � 12-Spalten CSS-Grid Dashboard:
  - Edit Mode Toggle (Overlays f�r L�schen/Konfigurieren)
  - Add Widget Modal: Typ (8 Viz + 2 Control), Variable Key, Device UID, Label, Unit, Min/Max, Grid-Gr��e
  - History-Daten via getVariableHistory pro Widget (Zeit-Range: 1h/6h/24h/7d/30d)
  - Refresh-Button, Time-Range-Tabs
-  � animierter Toggle-Switch f�r bool read_write Variablen
-  � Slider mit Live-Value-Anzeige f�r int/float
-  � neue Typen: control_toggle, control_slider
-  � Mapping + Labels f�r neue Typen
-  � Control-Widget-Rendering, control-change Event, controlValue ref
-  � /dashboards + /dashboards/:id Routen
-  � Dashboards Nav-Link in Data-Gruppe

### Tests
- TypeScript:  � 0 Fehler
- Vite Build: Erfolgreich, 10.43s
  - Dashboards-Bundle: 5.73 kB (gzip: 2.39 kB)
  - DashboardView-Bundle: 11.10 kB (gzip: 3.87 kB)
- UI-Verifikation (preview_eval):
  - /dashboards l�dt korrekt (Titel + Sub-Text sichtbar)
  - Empty State rendert korrekt (keine Dashboards vorhanden)
  - New Dashboard �ffnet Modal mit allen 5 Templates
  - Nav-Link Dashboards erscheint in Sidebar

### Offen (Step 6�7, folgende Milestones)
- Step 6: VariableStreams-Migration ? Default-Dashboard-Redirect
- Step 7: Dashboard Sharing + Embed-Mode + Export

### N�chster Milestone
**M19: Unified Automation Engine** � Typsystem-Integration f�r Trigger, Rules Engine
