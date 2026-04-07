# HUBEX — Business & Product Analysis

*Stand: 2026-03-25 | Roadmap-Progress: 33% (23/69 Steps)*

---

## 1. Produkt-Positionierung

**HUBEX** = Open-Source IoT Device Hub für Product Builders

| Dimension | HUBEX | AWS IoT Core | Home Assistant | ThingsBoard |
|-----------|-------|-------------|----------------|-------------|
| Zielgruppe | Product Builders, Startups, Integratoren | Enterprise DevOps | Endverbraucher (Smart Home) | Enterprise IoT Analytics |
| Self-Hosted | ✅ First-class | ❌ Cloud-only | ✅ | ✅ aber komplex |
| API-First | ✅ REST + künftig MCP | SDK-heavy | ❌ YAML-driven | REST aber alt |
| Device-Typen | MCU + OS-Agent + Software-SDK + Bridge | MCU/Gateway | Zigbee/Z-Wave/WiFi Consumer | MQTT/HTTP Devices |
| Automation | Delegiert an n8n/Node-RED | Lambda/Rules Engine | YAML Automations | Rule Chains |
| Preis | Free / Open Source | Pay-per-message | Free | Community vs PE |
| Security Model | Capability-based, Multi-Tenant | IAM Policies | User-based | Tenant-based |

### Marktlücke die HUBEX füllt:
> **"Der Device-Backend-Stack den jedes IoT-Startup von Scratch baut — als fertige Plattform."**

Konkret:
- **Kein AWS Lock-in**: Self-hosted, keine Cloud-Abhängigkeit
- **Kein Home-Assistant-Clone**: Nicht für Endverbraucher, sondern für Entwickler die Produkte bauen
- **Polyglot Device Support**: ESP32, Raspberry Pi, Windows/Linux Agents, Hardware-Bus Bridges — alles über ein einheitliches Protocol
- **MCP-native**: Als erste IoT-Plattform nativ MCP-fähig → AI-Agents können Devices direkt steuern
- **Dashboard Builder**: Endanwender können eigene Interfaces bauen ohne Code

---

## 2. Modul-Analyse (C1–C7e)

### Mapping → Roadmap

| Modul | Roadmap-Milestone | Status | Bewertung |
|-------|-------------------|--------|-----------|
| **C1 — UI Module** | M8 (UI Reboot) + M19 (Dashboard Builder) | 🔵 In Progress (Step 2/9 done) | ✅ Sinnvoll, Core-Prio |
| **C2 — Providers/Signals** | M14 (Provider/Signal System) | ⬜ Todo | ✅ Essentiell — ohne Signals keine Rules |
| **C3 — Rules Engine** | M15 (Rules Engine) | ⬜ Todo | ✅ Essentiell — Kernmehrwert der Plattform |
| **C4 — Observability** | M18 (Advanced Observability) | ⬜ Todo | ✅ Differentiator für Support/Debug |
| **C5 — Templates/Experiments** | M23 (Templates/Blueprints) | ⬜ Todo | ⚠️ Nice-to-have, nach Core-Modules |
| **C6 — Simulator/Testbench** | M22 (Simulator) | ⬜ Todo | ✅ Sinnvoll für Demos + CI |
| **C7a — Admin Console** | M21 (Admin Console) | ⬜ Todo | ✅ Nötig für Multi-Tenant-Betrieb |
| **C7b — Backup** | M25 Step 1-2 | ⬜ Todo | ✅ Enterprise-Requirement |
| **C7c — Plugins Framework** | M24 Step 1-2 | ⬜ Todo | ⚠️ Spät, nach Core stabilisiert |
| **C7d — Registry/Marketplace** | M24 Step 3 | ⬜ Todo | ⚠️ Erst relevant mit Community |
| **C7e — Mobile** | M25 Step 3 | ⬜ Todo | ✅ PWA reicht initial |

### Zusätzliche Module (User-Anforderungen):

| Neues Modul | Roadmap-Milestone | Bewertung |
|-------------|-------------------|-----------|
| **Universal Agent SDK** (RPi, Win, Linux) | M16 | ✅ Bereits geplant — Killer-Feature |
| **Bridge/Gateway** (Serial, Modbus, BLE) | M17 | ✅ Bereits geplant — Hardware-ohne-Internet |
| **MCP Integration** | M13 | ✅ Bereits geplant — AI-native Differentiator |
| **Dashboard Builder** (Custom UIs) | M19 | ✅ Bereits geplant — Low-Code Mehrwert |

### Fehlende Module — Empfehlung:

| Vorschlag | Begründung | Priorität |
|-----------|-----------|-----------|
| **Notification System** | Push/Email/SMS bei Alerts — fehlt komplett, essentiell für Ops | 🔴 Hoch |
| **Data Export/Analytics** | Telemetry-Daten CSV/JSON export, einfache Zeitreihen-Charts | 🟡 Mittel |
| **Webhook Templates Library** | Vorgefertigte n8n/Zapier Flows für Quick-Start | 🟡 Mittel |
| **Device Provisioning Profiles** | Batch-Provisioning für Produktion (100+ Devices gleichzeitig) | 🟡 Mittel |

---

## 3. Architektur-Bewertung

### Stärken ✅
- **Capability-based Security**: Feingranularer als RBAC, zukunftssicher
- **Multi-Tenancy von Anfang an**: Org-Isolation in JWT — Enterprise-ready
- **Async-first Backend**: FastAPI + SQLAlchemy async = skalierbar
- **OTA + Staged Rollouts**: Professioneller als viele Enterprise-Tools
- **Rate Limiting + Caching**: Production-grade ab Tag 1

### Risiken & Optimierungspotential ⚠️
1. **WebSocket/Realtime fehlt**: Aktuell nur Polling — für IoT essentiell
   → **Empfehlung**: WebSocket-Layer in Phase 4 einplanen (vor Rules Engine)
2. **MQTT Broker fehlt**: IoT-Standard, aktuell nur HTTP
   → **Empfehlung**: Als Built-in Provider in M14 (C2) priorisieren
3. **Device Twin / Shadow State**: Variables-System ist flat — kein reported/desired/effective Pattern
   → **Empfehlung**: In Agent SDK (M16) als Core-Konzept einbauen
4. **Kein Background Job System**: Celery/ARQ fehlt für Rules-Execution
   → **Empfehlung**: Vor M15 (Rules Engine) einplanen

### Security-Bewertung
- ✅ JWT + HMAC device tokens
- ✅ Capability enforcement
- ✅ Rate limiting, CORS, brute-force protection
- ✅ Refresh token rotation
- ⚠️ Fehlt: 2FA/MFA (geplant M20)
- ⚠️ Fehlt: API Keys für Service-to-Service (geplant M20)
- ⚠️ Fehlt: Audit-Log UI (geplant M8 Step 8)

---

## 4. UX/UI Bewertung

### Aktueller Stand
- ✅ Mission Control Design System: 16 Komponenten, konsistentes Dark Theme
- ✅ Dashboard mit Live-Metriken, Health Ring, Event Stream
- ⚠️ Nur 2/9 Pages im neuen Design (Dashboard, teilweise Devices)
- ⚠️ Mobile Responsive noch nicht umgesetzt

### Empfehlungen
1. **Onboarding Flow**: Erster Login → Wizard der durch Device-Pairing führt
2. **Empty States**: Jede Page braucht hilfreiche Empty-States statt leerer Tabellen
3. **Keyboard Shortcuts**: Power-User-Feature, differenziert von Consumer-Tools
4. **Command Palette** (Ctrl+K): Quick-Navigation, Device-Suche — professionell
5. **Contextual Help**: Tooltips/Docs-Links bei komplexen Konzepten (Capabilities, OTA Strategies)

---

## 5. Business-Strategie & Pitch-Timing

### Go-to-Market Phasen

| Phase | Zeitpunkt | Aktion |
|-------|-----------|--------|
| **Alpha Demo** | Nach M9 (ESP32 Demo) | Erste Live-Demo möglich |
| **MVP Pitch** | Nach M12 (Docs fertig) | ⭐ **Beste Zeit für Kurzpräsentation** |
| **Beta Launch** | Nach M15 (Rules Engine) | Feature-complete genug für Early Adopters |
| **Partner Pitch** | Nach M17 (Bridge Framework) | Full-Stack IoT Platform Story |
| **Enterprise Ready** | Nach M20 (Security v2) | SOC2-level Security Story |

### Empfehlung: Kurzpräsentation vorbereiten
**Optimaler Zeitpunkt: Nach Milestone 12 (Developer Docs)**

Begründung:
- UI ist komplett (M8)
- ESP32 Live-Demo verfügbar (M9)
- CI/CD läuft (M10)
- n8n Integration zeigt Ökosystem-Denken (M11)
- Docs machen es greifbar (M12)
- **= Phase 3 abgeschlossen = 55% Roadmap = vorzeigbares Produkt**

→ In der Roadmap als Milestone einplanen: "M12.5: Investor/Partner Pitch Deck"

### Revenue-Modell Optionen
1. **Open Core**: Community Edition free, Enterprise (RBAC, SSO, Audit, Backup) kostenpflichtig
2. **Managed Hosting**: Self-hosted free, Cloud-hosted als SaaS
3. **Marketplace Revenue Share**: Plugin/Template-Verkauf auf Registry
4. **Support/Consulting**: Enterprise Support Packages

---

## 6. Marktlücken-Analyse

### Aktueller IoT-Plattform-Markt (2026)

| Bedarf | Marktangebot | HUBEX-Chance |
|--------|-------------|-------------|
| **Self-hosted IoT Backend** | Wenig (ThingsBoard PE teuer, AWS cloud-only) | 🟢 Direkte Lücke |
| **MCU + OS Agent + Software SDK** unified | Keiner bietet alle drei | 🟢 Unique Selling Point |
| **MCP/AI-native IoT** | Nicht existent | 🟢 First Mover |
| **Hardware Bus ohne Internet** | Industrial-only (Siemens, Beckhoff) | 🟢 Open-Source Alternative |
| **Low-Code IoT Dashboard Builder** | Grafana (komplex), Node-RED (Flows) | 🟡 Differenzierung nötig |
| **n8n/Zapier IoT Integration** | Fragmentiert, keine native Bridge | 🟢 Connector-Story |

### Top-3 Differenziatoren für Pitch:
1. **"Von ESP32 bis Windows Server — ein Protocol"** (Universal Agent SDK)
2. **"AI steuert deine Devices"** (MCP-native)
3. **"Industrial-grade, Open-Source Preis"** (Self-hosted, Capability-Security)

---

## 7. Nächste Schritte (Empfehlung)

1. ✅ Phase 2 fertigstellen (UI Reboot — 7 Steps verbleibend)
2. ✅ Phase 3 durchziehen (ESP Demo + CI/CD + Docs)
3. 📊 Nach Phase 3: **Pitch Deck erstellen** (→ neuer Milestone)
4. 🔧 Phase 4 mit Prio: MCP → Providers → Rules → Agent SDK → Bridge
5. 💰 Nach Phase 4: Beta-Launch + erste Partner-Gespräche
