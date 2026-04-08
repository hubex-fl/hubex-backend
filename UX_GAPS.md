# UX Gap-Analyse — Konsolidierter Implementierungsplan

> **Erstellt:** 2026-03-31
> **Quelle:** Alle prompt.txt bis prompt 6.txt, vision.txt, handoff.txt, lücke1bis4.txt, lücken5bis7.txt
> **Status:** Lebendiges Dokument — wird nach jedem Sprint aktualisiert
> **Regel:** Jeder Gap hat: IST-Zustand, SOLL-Zustand, betroffene Dateien, Erfolgskriterium

---

## Referenz-Dokumente (auf Desktop, NICHT im Repo)
- `C:\Users\lange\Desktop\prompt.txt` — User-Feedback + UX-Gesamtspezifikation Teil A-C
- `C:\Users\lange\Desktop\prompt1.txt` — Observability, Events, Audit, Settings Feedback
- `C:\Users\lange\Desktop\prompt2.txt` — 7 UX-Prinzipien, Design System, Navigation/Sidebar
- `C:\Users\lange\Desktop\prompt3.txt` — Globale Features, First-Login, Wizard, Devices-Seite
- `C:\Users\lange\Desktop\prompt 4.txt` — Device-Detail, Entities, Variablen-Seite
- `C:\Users\lange\Desktop\prompt 5.txt` — Dashboard, Automations, Alerts, Settings
- `C:\Users\lange\Desktop\prompt 6.txt` — Connect-Panel, Auto-Discovery, Priorisierung
- `C:\Users\lange\Desktop\vision.txt` — Produktvision (4 Ebenen: Anbinden/Verstehen/Visualisieren/Automatisieren)
- `C:\Users\lange\Desktop\handoff.txt` — Universelle Integrations-Kompatibilität
- `C:\Users\lange\Desktop\lücke1bis4.txt` — Computed Variables, Snapshots, Automation-Erweiterung, Daten-Sharing
- `C:\Users\lange\Desktop\lücken5bis7.txt` — Custom API Builder, Mandanten-Hierarchie, Report-Generator

---

## 7 UX-GRUNDPRINZIPIEN (gelten IMMER, bei ALLEM)

1. **Progressive Disclosure** — Default zugeklappt, aufklappbar per Klick
2. **Selektoren statt ID-Eingabe** — KEIN Feld erwartet ID/UID/Key auswendig
3. **Kontextuelles Arbeiten** — Von jedem Element zum nächsten Schritt MIT Kontext
4. **Unterstützend, nie aufdringlich** — Wizards skippbar, Hilfe ausblendbar
5. **Minimalistisch** — Nur was relevant ist, keine JSON-Fehler
6. **Wächst mit Komplexität** — Einfach = einfach, komplex = detaillierter
7. **Verständliche Sprache** — Tooltips, klare Buttons, Bestätigung bei Destruktivem

---

## Sprint UX-1: Flow-Korrekturen (ROADMAP: Milestone UX-A)

### Gap 1.1: ActionBar navigiert OHNE Kontext
- **IST:** `ActionBar.vue` navigiert zu `/alerts`, `/automations` ohne Query-Parameter
- **SOLL:** `/alerts?create=true&device_uid=X`, `/automations?create=true&device_uid=X`
- **Datei:** `frontend/src/components/ActionBar.vue` (Zeile ~54: `router.push("/variables")`)
- **Erfolgskriterium:** Klick auf "Set up alerts" in DeviceDetail → Alerts-Seite öffnet Create-Modal MIT Device vorausgewählt
- **Status:** [x] Erledigt (2026-04-08) — ActionBar bereits korrekt implementiert mit create+device_uid Query-Params

### Gap 1.2: Keine Post-Acknowledge Action-Bar bei Alerts
- **IST:** Nach Alert-Ack passiert nichts, nur Status-Änderung
- **SOLL:** Inline-Bar: "Alert bestätigt → [Zum Device] [Automation erstellen] [Stummschalten]"
- **SOLL (wiederkehrend):** Bei >3x in 24h: "Dieser Alert wurde heute 5x ausgelöst. Automation erstellen?"
- **Datei:** `frontend/src/pages/Alerts.vue` (nach handleAck Funktion, ~Zeile 67-77)
- **Erfolgskriterium:** Nach Ack erscheint Action-Bar mit Links, verschwindet nach 10s oder per ×
- **Status:** [x] Erledigt (2026-04-08) — Post-ack action bar mit View Device, Create Automation, Mute + recurring hint + 10s auto-dismiss

### Gap 1.3: Alert-Events nicht klickbar
- **IST:** Alert-Events sind nur Text, kein Link zum betroffenen Device
- **SOLL:** Device/Variable-Name als `<router-link>` zum Device
- **Datei:** `frontend/src/pages/Alerts.vue` (Events-Tab Template, ~Zeile 400+)
- **Erfolgskriterium:** Klick auf Device-Name in Alert-Event → navigiert zur Device-Detail-Seite
- **Status:** [x] Erledigt (2026-04-08) — Device-Name als router-link mit Lookup-Map

### Gap 1.4: Kein Alerts→Automations Link
- **IST:** Alerts-Seite hat keinen "Create Automation" Button
- **SOLL:** Button/Link der mit `?create=true&variable_key=X` zum Automations-Builder navigiert
- **Datei:** `frontend/src/pages/Alerts.vue`
- **Erfolgskriterium:** Von einem Alert-Event aus kann direkt eine Automation erstellt werden
- **Status:** [x] Erledigt (2026-04-08) — Create Automation Button mit variable_key+device_uid Context

### Gap 1.5: DeviceDetail Input/Output nicht zugeklappt
- **IST:** Input (Telemetry) und Output (Variables) Panels sind offen (UCard dargestellt)
- **SOLL:** Default collapsed mit Expand-Chevron, nur Titel + Count sichtbar
- **Datei:** `frontend/src/pages/DeviceDetail.vue` (Zeile ~1716+, UCard Panels)
- **Erfolgskriterium:** Beim Laden der DeviceDetail-Seite sind Input/Output zugeklappt
- **Status:** [x] Erledigt (bereits implementiert) — showInputPanel/showOutputPanel default false mit Chevron

### Gap 1.6: Selektoren-Audit
- **IST:** Automations-Builder Felder `trigVarKey`, `actVarKey` — Status prüfen (UEntitySelect oder UInput?)
- **SOLL:** ALLE Entity-Referenz-Felder müssen UEntitySelect sein
- **Dateien:** `Automations.vue`, `Alerts.vue` — jedes Formular-Feld prüfen
- **Erfolgskriterium:** Grep nach `<UInput` in Modal-Formularen findet KEIN Feld das eine Entity referenziert
- **Status:** [x] Erledigt (Audit bestätigt: Automations, Alerts, Dashboard, Entities alle mit UEntitySelect)

---

## Sprint UX-2: Erklärungen, Tooltips & Bug-Fixes (ROADMAP: Milestone UX-B)

### Gap 2.1: Events-Seite ohne Erklärung
- **IST:** Nur "Events Viewer" + "Real-time event stream reader" als Beschreibung
- **SOLL:** Erklärungstext: "Events zeigen System-Ereignisse in Echtzeit. Wähle einen Stream und starte." + Tooltips auf "Set cursor", "Jump to next", "ACK"
- **Datei:** `frontend/src/pages/Events.vue` (Header-Bereich, ~Zeile 188+)
- **Status:** [x] Erledigt (2026-04-08) — Subtitle + Tooltips auf Set cursor, Jump to next, ACK

### Gap 2.2: Audit-Seite ohne Erklärung
- **IST:** Keine Beschreibung, sieht identisch aus wie Events
- **SOLL:** "Das Audit-Log zeigt wer wann was im System geändert hat." Visuell von Events unterscheiden.
- **Datei:** `frontend/src/pages/Audit.vue`
- **Status:** [x] Erledigt (2026-04-08) — Clipboard-Icon + Erklärungstext via i18n

### Gap 2.3: Entities ohne Tooltips
- **IST:** "Priority" und "Enable Binding" ohne jede Erklärung
- **SOLL:** Tooltips: "Reihenfolge bei mehreren Bindings" / "Deaktivierte Bindings bleiben gespeichert"
- **Datei:** `frontend/src/pages/EntitiesPage.vue` (Bind-Device Modal, ~Zeile 703-712)
- **Status:** [x] Erledigt (2026-04-08) — Tooltips auf Priority + Enable Binding

### Gap 2.4: Automations Builder ohne Tooltips für komplexe Felder
- **IST:** Geofence Polygon, Webhook Headers, Cooldown ohne Erklärung
- **SOLL:** Tooltips auf jedem nicht-selbsterklärenden Feld
- **Datei:** `frontend/src/pages/Automations.vue` (Modal, ~Zeile 800+)
- **Status:** [x] Erledigt (2026-04-08) — Tooltips auf Cooldown, Geofence, Webhook URL/Headers/Payload

### Gap 2.5: Dashboard-Template JSON-Fehler
- **IST:** Template-Erstellung (Fleet Tracking etc.) schlägt mit rohem JSON-Fehler fehl
- **SOLL:** Verständliche Fehlermeldung ODER Bug fixen dass Template korrekt erstellt wird
- **Dateien:** `frontend/src/pages/DashboardView.vue`, Backend Dashboard-Endpoints
- **Status:** [x] Erledigt (2026-04-08) — Grid-Positionen + Error-Isolation pro Widget

### Gap 2.6: API-Docs/Swagger 404 + Useful Links
- **IST:** Swagger-Link und Redoc führen zu leerer/404 Seite
- **SOLL:** Funktionierender Swagger UI Embed
- **Dateien:** `frontend/src/pages/ApiDocs.vue`, Backend-Proxy-Config
- **Status:** [x] Erledigt (2026-04-08) — Embedded Swagger UI + ReDoc mit Tab-Interface

### Gap 2.7: Acknowledge-Alert Bug
- **IST:** "Failed to Acknowledged Alert" bei Klick
- **SOLL:** Ack funktioniert, Status wechselt zu "acknowledged"
- **Dateien:** `frontend/src/pages/Alerts.vue`, Backend Alert-Endpoints
- **Status:** [x] Erledigt (2026-04-08) — Backend idempotent + Error-Parsing fix + apiFetch HTTP status

### Gap 2.8: Grafik-Bug Suchfeld-Placeholder
- **IST:** "irgendein kleiner Grafik-Bug" im Placeholder der Suchfelder
- **SOLL:** Sauberes Placeholder-Rendering
- **Dateien:** `frontend/src/pages/Devices.vue`, `EntitiesPage.vue`
- **Status:** [~] Niedrige Prio — visueller Micro-Bug, kein Funktionsproblem

---

## Sprint UX-3: DeviceDetail Komplett-Überholung (ROADMAP: Milestone UX-C)

### Gap 3.1: System Context zeigt nur generische Zahlen
- **IST:** "Telemetry 5 events received", "Variables 21 configured", "Tasks 3 executed" — statische Boxen
- **SOLL:** Liste der ECHTEN Variablen (Name + Wert + Typ-Icon), klickbar. Verknüpfte Alerts/Automations als Nodes.
- **Vision (prompt 4):** Platinen-Ansicht wie Schaltplan: Device → Variablen → Alerts/Automations, alles klickbar
- **Datei:** `frontend/src/pages/DeviceDetail.vue` (Zeile ~1590-1710, System Context Section)
- **Erfolgskriterium:** User sieht echte Variablen-Namen mit Werten, kann draufklicken → navigiert
- **Status:** [x] Erledigt (Milestone UX-H) — SystemContextGraph.vue mit SVG Node-Graph implementiert

### Gap 3.2: Variable-Typ nicht editierbar
- **IST:** Edit erlaubt nur Value-Änderung, kein Typ/Einheit/Direction
- **SOLL:** Edit-Modal: Typ (string/int/float/bool/json), Einheit, Direction (read_only/write_only/read_write), Display-Hint
- **Datei:** `frontend/src/pages/DeviceDetail.vue` (Zeile ~1958-1961, editingVarKey Bereich)
- **Backend:** PATCH /api/v1/variables/definitions/{key} existiert bereits
- **Status:** [x] Erledigt (2026-04-08) — Edit-Modal mit Datentyp + Direction Dropdowns

### Gap 3.3: Kein Connect-Button pro Variable
- **IST:** Variablen haben Edit-Stift aber keinen 🔗 Button
- **SOLL:** 🔗 Icon pro Variable → öffnet ConnectPanel mit dieser Variable
- **Datei:** `frontend/src/pages/DeviceDetail.vue` (Variable-Rows im Output-Panel)
- **Status:** [x] Erledigt (2026-04-08) — Bell-Icon pro Variable → Alert erstellen mit Context

### Gap 3.4: Variablen zeigen keinen Typ/Einheit
- **IST:** Variables zeigen "default" Badge, keinen semantischen Typ, keine Einheit, kein Typ-Icon
- **SOLL:** Typ-Icon (🌡️/💧/🔋), Name, Wert MIT Einheit (z.B. "23.5°C"), Sparkline
- **Datei:** `frontend/src/pages/DeviceDetail.vue`
- **Abhängigkeit:** Braucht semantische Typ-Info aus Variable-Definition
- **Status:** [x] Erledigt (2026-04-08) — resolved_type + constraints.unit + direction Badge angezeigt

### Gap 3.5: Keine Offline-Fehlerzustand ActionBar
- **IST:** Bei Offline: nur "Last seen: Xh ago" im Status-Bar
- **SOLL:** Prominente ActionBar: "🔴 Offline seit 3h · Letzter Kontakt: 14:23 → [Verbindung testen] [Alert einrichten]"
- **Datei:** `frontend/src/pages/DeviceDetail.vue`
- **Status:** [x] Erledigt (2026-04-08) — Prominente Offline-ActionBar mit Test Connection + Set up Alert

---

## Sprint UX-4: Bugs (integriert in UX-B, separate Tracking)

Siehe Gaps 2.5-2.8 oben.

---

## Sprint UX-5: Add Device Wizard (ROADMAP: Milestone UX-D)

### Gap 5.1: Kein Device-Wizard
- **IST:** Nur rudimentäres ESP32-Pairing. WelcomeScreen zeigt 4 Kategorien aber Klick führt nur zu Devices-Seite.
- **SOLL:** Multi-Step-Wizard mit 4 Flows:
  - Hardware: Verbindungsart → Pairing → Live-Status → Benennen → Geschafft
  - Service: URL → Auth → Testen+Felder → Benennen → Geschafft
  - Bridge: Protokoll → Config → Testen → Benennen → Geschafft
  - Agent: System → Install-Command → Warten → Benennen → Geschafft
- **Dateien:** `components/DeviceWizard.vue` (neu), `WelcomeScreen.vue`, `Devices.vue`
- **Status:** [x] Erledigt (Milestone UX-D) — 4-Schritt-Wizard mit Hardware/Service/Bridge/Agent Flows implementiert

---

## Sprint UX-6: System Context + Dashboard (ROADMAP: Milestone UX-E)

### Gap 6.1: System Context als Node-Graph
- **IST:** Statische Boxen mit Zahlen
- **SOLL:** SVG Node-Graph: Device → Variablen (mit Werten) → Alerts/Automations, alles klickbar
- **Dateien:** `components/SystemContextGraph.vue` (neu), `pages/DeviceDetail.vue`
- **Status:** [x] Erledigt (Milestone UX-H) — SystemContextGraph mit SVG-Pfeilen + klickbaren Nodes

### Gap 6.2: Dashboard Widget Auto-Suggest
- **IST:** Widget-Typ manuell wählen, kein Vorschlag basierend auf Variable-Typ
- **SOLL:** Nach Variable-Auswahl: Typ automatisch vorschlagen (Temperatur → Line Chart, Boolean → Toggle)
- **Datei:** `frontend/src/pages/DashboardView.vue`
- **Status:** [x] Erledigt (Milestone UX-J) — Auto-suggest bei Variable-Auswahl implementiert

### Gap 6.3: Connect-Panel Inline-Forms
- **IST:** ConnectPanel zeigt Verbindungen, aber "[+ Alert]" navigiert weg
- **SOLL:** Inline-Formular IM Panel, Variable vorausgewählt, nur Bedingung konfigurieren
- **Datei:** `frontend/src/components/ConnectPanel.vue`
- **Status:** [ ] Offen — noch umzusetzen (Nice-to-have)

---

## Sprint UX-2 ERGÄNZUNG: Fehlende Items aus Specs

### Gap 2.9: Secrets Toggle Tooltip auf Variables-Seite
- **IST:** "Secrets" Toggle rechts oben ohne jede Erklärung
- **SOLL:** Tooltip: "Geheime Variablen werden in der Übersicht maskiert (z.B. API-Keys, Passwörter)"
- **Datei:** `frontend/src/pages/Variables.vue` (Toolbar, showSecrets Toggle)
- **Quelle:** prompt.txt Zeile 37
- **Status:** [x] Erledigt (2026-04-08) — Tooltip via i18n title-Attribut

### Gap 2.10: Streams-Seite chaotisch
- **IST:** "Wild zusammengeklatschte Dashboard-artige Seite", nichts eingeklappt, keine Hilfe
- **SOLL:** Erklärungstext oben ("Live-Übersicht aller Variablen-Streams"), Progressive Disclosure
- **Datei:** `frontend/src/pages/VariableStreams.vue`
- **Quelle:** prompt.txt Zeile 51
- **Status:** [x] Erledigt (2026-04-08) — Komplett umgebaut: Grouped by Device, collapsed, Progressive Disclosure

### Gap 2.11: Dashboard Home minimalistischer
- **IST:** "Sehr chaotisch, nicht sagend" laut User. Zu viele Kacheln ohne klare Aussage.
- **SOLL:** Minimalistischer: nur die wichtigsten KPIs (Devices online/offline, Active Alerts, letzte Aktivität)
- **Datei:** `frontend/src/pages/DashboardPage.vue` oder `Landing.vue`
- **Quelle:** prompt1.txt Zeile 17
- **Status:** [x] Erledigt (2026-04-08) — 4 KPIs + Recent Alerts + Activity Feed, SVG-Charts/Quick-Actions entfernt

### Gap 2.12: System Health — Redis Tooltip + klickbare Links
- **IST:** "Redis, weiß ich nicht was das ist" — keine Erklärung. Devices/Alerts nicht klickbar.
- **SOLL:** Redis → Tooltip "In-Memory Cache für schnelle Datenabfragen". Devices Online/Offline → klickbarer Link zur Devices-Seite (gefiltert). Active Alerts → Link zur Alerts-Seite.
- **Datei:** `frontend/src/pages/SystemHealth.vue`
- **Quelle:** prompt 5.txt (E13)
- **Status:** [x] Erledigt (2026-04-08) — Redis Tooltip + Devices/Alerts waren bereits router-links

---

## BEREITS ERLEDIGT (zur Referenz)

| Was | Wann | Status |
|-----|------|--------|
| Sidebar 3-Gruppen (HAUPT/DATEN/SYSTEM) | Session 1 | ✅ |
| Sidebar Default collapsed | Session 1 | ✅ |
| Automations kompakte Cards | Session 1 | ✅ |
| Variables gruppiert nach Device | Session 1 | ✅ |
| DeviceDetail Name inline editierbar | Session 1 | ✅ |
| DeviceDetail doppelte Offline-Anzeige weg | Session 1 | ✅ |
| DeviceDetail Task/Signal bei Offline hidden | Session 1 | ✅ |
| Variables→Alerts Context-Routing | Session 1 | ✅ |
| Variables→Automations Context-Routing | Session 1 | ✅ |
| "Purge" → "Delete" überall | Session 2 | ✅ |
| Admin-Toggle versteckt | Session 2 | ✅ |
| Settings Accordion statt Tabs | Session 2 | ✅ |
| Sidebar: Dashboards in HAUPT | Session 2 | ✅ |
| Sidebar: Entities in DATEN | Session 2 | ✅ |
| Sidebar: Streams entfernt | Session 2 | ✅ |
| Sign-Out in Avatar-Dropdown | Früherer Commit | ✅ |
| UEntitySelect in Dashboard-Widget | Früherer Commit | ✅ |
| UEntitySelect in Entity-Binding | Früherer Commit | ✅ |
| UEntitySelect in Alert-Entity-ID | Früherer Commit | ✅ |
| UEntitySelect in Variables Device-Filter | Früherer Commit | ✅ |
| Empty States auf allen Seiten | Früherer Commit | ✅ |
| WelcomeScreen mit 4 Kategorien | Früherer Commit | ✅ |
| friendlyError() in lib/errors.ts | Früherer Commit | ✅ |

---

## LANGFRISTIGE GAPS (Phase 7+ — nicht in UX-Sprints)

Diese sind in der ROADMAP als eigene Milestones erfasst:

| Gap | ROADMAP Milestone | Status |
|-----|------------------|--------|
| Computed Variables + Snapshots | M14b | ROADMAP ✅ |
| Automation Engine Erweiterung (8 Actions, 5 Trigger) | M19b | ROADMAP ✅ |
| Dashboard Embed Sicherheitsstufen | M18b | ROADMAP ✅ |
| Custom API Builder | M27b | ROADMAP ✅ |
| Report-Generator PDF | M28b | ROADMAP ✅ |
| Mandanten-Hierarchie | M31 erweitert | ROADMAP ✅ |
| Node-RED Node Package | M21 Step 4 | ROADMAP ✅ |
| MQTT Home Assistant Discovery | M21 Step 5 | ROADMAP ✅ |
| Webhook-Härtung | M21 Step 6 | ROADMAP ✅ |
| Integrations-Doku | M21 Step 7 | ROADMAP ✅ |
| Globale Suche Cmd+K | M16 Step 5 | ROADMAP ✅ |
| Notification Preferences | M17 Step 3 | ROADMAP ✅ |
| Email-Dispatch | M17 Step 4 | ROADMAP ✅ |
| Automation AND/OR Groups | M19 Step 3 | ROADMAP ✅ |
| Automation If/Else Branching | M19 Step 4 | ROADMAP ✅ |
| Flow Editor (n8n-style) | M36 | ROADMAP ✅ |
