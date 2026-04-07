# HubEx — Praesentationsplan v2

## "The Universal IoT Device Hub"
### Build. Connect. Orchestrate.

---

## Marktanalyse & Positionierung

### Das Problem im Markt

Der IoT-Markt ist fragmentiert. Wer heute smarte Produkte bauen will, steht vor einem Dilemma: Entweder du nutzt eine Cloud-Plattform wie AWS IoT oder Azure IoT Hub — dann bist du eingesperrt in deren Oekosystem, zahlst pro Nachricht, und hast null Kontrolle. Oder du bastelst dir alles selbst zusammen — ESP32-Firmware hier, MQTT-Broker da, eigenes Backend dort, und irgendwie noch ein Dashboard. Das Ergebnis: Monate an Infrastrukturarbeit, bevor du dich ueberhaupt um dein eigentliches Produkt kuemmern kannst.

Gleichzeitig gibt es Automatisierungsplattformen wie n8n, die fantastisch darin sind, Web-Services miteinander zu verknuepfen — aber die kennen keine physischen Geraete. Und es gibt Smart-Home-Plattformen wie Home Assistant, die Geraete steuern koennen — aber nicht fuer Produktentwicklung oder professionelle Anwendungen gedacht sind.

**Niemand verbindet alle drei Welten**: eigene Geraeteentwicklung, Integration kommerzieller Hardware und workflow-basierte Automatisierung. Das ist die Luecke, die HubEx fuellt.

### Marktdaten

- IoT Device Management Markt: ~$11 Mrd. (2026), CAGR 24,4% bis 2035
- Edge Computing Markt: $28,5 Mrd. (2026), CAGR 28%
- 45% der Unternehmen kaempfen damit, Custom-Devices mit kommerziellen Geraeten und Automations-Workflows zu vereinen
- Google Cloud IoT wurde 2023 eingestellt — der Markt konsolidiert sich, aber die Luecke im Mittelfeld waechst

### Wettbewerbslandschaft

| Plattform | Staerke | Schwaeche | HubEx-Vorteil |
|-----------|---------|-----------|---------------|
| **AWS IoT Core** | Skalierung, Oekosystem | Vendor Lock-in, Pay-per-Message, komplex | Self-hosted, transparente Kosten, kein Lock-in |
| **ThingsBoard** | Open Source, Feature-reich | Steile Lernkurve, kein Fokus auf Device-Entwicklung | Developer-first, ESP32 SDK, einfacheres Onboarding |
| **Particle** | Hardware + Cloud Bundle | Hardware Lock-in, nur deren Chips | Device-agnostisch, jede Hardware willkommen |
| **Balena** | Docker auf Edge-Devices | Nur Linux-Geraete, keine MCUs | MCU + OS-Agent + Software-Devices |
| **Blynk** | Low-Code, Mobile-first | Limitiert bei komplexen Workflows | Webhook + n8n fuer beliebige Automatisierung |
| **Home Assistant** | Riesige Community, lokal | Nicht fuer Produktentwicklung, kein Multi-Tenancy | Multi-Tenant, OTA, professionelle API |
| **n8n** | 1000+ Integrationen, Automation | Kennt keine physischen Geraete | Native Device-Anbindung + n8n als Erweiterung |

### HubEx-Positionierung: Der unbesetzte Sweet Spot

```
                    Device-Entwicklung
                          |
                   [  HubEx  ]
                  /     |     \
       Custom Devices   |   Kommerzielle Geraete
       (ESP32, RPi,     |   (via API, Webhook,
        Software)        |    MQTT, Bridges)
                         |
                   Orchestrierung
                   (Rules, Webhooks,
                    n8n, Automation)
```

**HubEx ist die einzige Plattform, die alle drei Saeulen gleichwertig behandelt:**

1. **Build** — Eigene smarte Geraete entwickeln (Hardware wie ESP32 + Software-Agents)
2. **Connect** — Fertige kommerzielle Geraete ueber APIs, Webhooks, Bridges ankoppeln
3. **Orchestrate** — Alles miteinander vernetzen, automatisieren, steuern

---

## 1. Elevator Pitch (30 Sekunden)

### Fuer technisches Publikum:

> HubEx ist der universelle IoT Device Hub. Du entwickelst eigene smarte Geraete — ob ESP32, Raspberry Pi oder reine Software-Agents — und verbindest sie mit einem Klick. Gleichzeitig koppelst du fertige kommerzielle Geraete ueber APIs und Webhooks an. Und dann orchestrierst du alles von einem zentralen Punkt: Regeln, Automatisierungen, OTA-Updates, Alerts. Stell dir n8n vor, aber fuer die physische Welt — und mit n8n-Anbindung on top. Open Source, self-hosted, kein Vendor Lock-in.

### Fuer nicht-technisches Publikum:

> Stell dir vor, du baust ein smartes Produkt — zum Beispiel einen Sensor, der die Luftqualitaet misst. Du brauchst einen Ort, an dem dieses Geraet lebt, Daten sendet, Updates bekommt und mit anderen Systemen spricht. Gleichzeitig willst du vielleicht auch gekaufte Geraete einbinden — eine Wetterstation, eine Kamera. HubEx ist die Zentrale, die das alles verbindet: Deine eigenen Geraete, gekaufte Geraete, und die ganze digitale Welt drumherum. Ein Knotenpunkt fuer alles.

### One-Liner fuer LinkedIn / Pitch Deck:

> **HubEx** — Build custom IoT devices. Connect commercial hardware. Orchestrate everything from one hub.

---

## 2. Struktur fuer eine Kurzpraesentation (10-15 Min.)

### Narrativer Bogen: "Vom Problem zur Loesung zur Vision"

| Zeit | Abschnitt | Inhalt | Notizen |
|------|-----------|--------|---------|
| 0:00-1:30 | **Das Problem** | Geschichte: "Mein erster ESP32-Sensor funktionierte in 2 Stunden. Ihn produktionsreif zu machen dauerte 6 Monate. Firmware-Updates? Manuell per USB. Monitoring? SSH auf den Pi. Alerting? Ich hab auf mein Handy geschaut. Und als ich dann noch eine kommerzielle Wetterstation einbinden wollte — komplett andere API, anderes Protokoll, nochmal Wochen Arbeit." | Persoenlich, greifbar. Publikum nickt. |
| 1:30-3:00 | **Die Idee** | "Was wenn es EINEN Ort gaebe, an dem all deine Geraete leben? Egal ob selbstgebaut oder gekauft. Einen Hub, der so flexibel ist wie n8n — aber fuer die physische Welt." Ueberleitung: "Das ist HubEx." | Analogie zu n8n hier platzieren |
| 3:00-4:30 | **Die drei Saeulen** | BUILD: Eigene Geraete entwickeln (ESP32 SDK, Software-Agents). CONNECT: Kommerzielle Geraete einbinden (Webhooks, APIs, Bridges). ORCHESTRATE: Alles vernetzen (Rules, Automation, n8n). | 1 Slide mit dem Drei-Saeulen-Diagramm |
| 4:30-9:30 | **Live-Demo** | Konkretes Szenario durchspielen (siehe Abschnitt 4). Zeigt den gesamten Flow: Geraet anmelden → Daten sehen → Alert ausloesen → Automatisierung triggern → OTA-Update ausrollen. | Live im Browser + ESP32 auf dem Tisch |
| 9:30-11:00 | **Differenzierung** | Vergleich: "Bei AWS IoT zahlt ihr pro Nachricht und seid eingesperrt. Bei ThingsBoard braucht ihr 3 Wochen Einarbeitung. Bei Particle muesst ihr deren Hardware kaufen. HubEx: Open Source, Self-Hosted, jede Hardware, transparente Kosten." | Vergleichsslide, aber fair und sachlich |
| 11:00-13:00 | **Roadmap & Vision** | Wohin geht die Reise? Rules Engine fuer komplexe Automatisierung. Universal Agent SDK (jedes Geraet, jedes OS). Bridge Framework (Modbus, BLE, CAN Bus — industrielle Protokolle). MCP-Integration fuer AI-gesteuerte Geraete. Plugin Marketplace. | Timeline-Slide |
| 13:00-15:00 | **Call to Action + Q&A** | Je nach Zielgruppe: Partner → "Baut euer naechstes IoT-Produkt auf HubEx." Investor → "First Mover im 'n8n fuer IoT'-Segment." Beta-Tester → "Meldet euch fuer Early Access." | Kontaktdaten, QR-Code |

### Drei Kernbotschaften (immer wieder einfliessen lassen):

1. **"Jede Hardware, ein Hub"** — Device-agnostisch, vom ESP32 bis zum Industrie-Gateway
2. **"Von Prototyp zu Produktion"** — Gleiche Plattform fuer 1 Geraet und 10.000
3. **"Kein Lock-in, volle Kontrolle"** — Open Source, Self-Hosted, transparente Kosten

---

## 3. Analogien zum Erklaeren

### Primaere Analogie: "n8n fuer die physische Welt"

> n8n verbindet digitale Dienste miteinander — Gmail mit Slack mit Google Sheets. HubEx macht dasselbe, aber fuer physische Geraete: Dein Sensor spricht mit deiner Steuerung, die spricht mit deinem Dashboard, das spricht mit deinem Handy. Und weil wir n8n nativ anbinden, koennen deine Geraete auch mit der gesamten digitalen Welt sprechen.

**Warum diese Analogie funktioniert:** n8n ist bekannt, das Konzept "Dinge verbinden" ist sofort klar, und es positioniert HubEx im Automatisierungs-Mindset statt im reinen Monitoring-Mindset.

### Ergaenzende Analogie: "Das Betriebssystem fuer deine Geraete"

> Dein Laptop hat ein Betriebssystem, das sich um Updates, Sicherheit und App-Verwaltung kuemmert. Deine IoT-Geraete haben das nicht — es sei denn, du nutzt HubEx. HubEx ist das Betriebssystem fuer deine gesamte Geraeteflotte: Es verwaltet Updates, ueberwacht den Zustand, und stellt sicher, dass alles miteinander kommuniziert.

### Analogie fuer Investoren: "Shopify fuer IoT-Produkte"

> So wie Shopify jedem eroeffnet, einen Online-Shop zu betreiben — ohne eigene Infrastruktur — eroeffnet HubEx jedem, ein smartes Produkt zu betreiben. Du baust dein Geraet, verbindest es mit HubEx, und hast sofort: OTA-Updates, Monitoring, Alerting, Multi-Tenancy, API. Die ganze Infrastruktur, die sonst Monate dauert.

### Analogie fuer Nicht-Techniker: "Die Telefonzentrale"

> Frueher hatte jedes Buero eine Telefonzentrale — ein Knotenpunkt, an dem alle Leitungen zusammenlaufen und weitervermittelt werden. HubEx ist die Telefonzentrale fuer smarte Geraete. Egal welches Geraet anruft — ob selbstgebaut oder zugekauft — HubEx nimmt den Anruf entgegen, weiss was zu tun ist, und leitet die Information an die richtige Stelle weiter.

---

## 4. Konkretes Anwendungsbeispiel fuer die Demo

### Szenario: "Smart Workspace — Buero-Klimaueberwachung mit automatischer Reaktion"

**Warum dieses Szenario?** Es zeigt alle drei Saeulen (Build, Connect, Orchestrate) in einer nachvollziehbaren Alltagssituation. Jeder kennt ein Buero, jeder versteht "zu warm" oder "schlechte Luft".

### Setup auf dem Tisch:

| Geraet | Typ | Rolle |
|--------|-----|-------|
| ESP32 + DHT22 | **Custom Device (Build)** | Misst Temperatur + Luftfeuchtigkeit im Raum |
| Externer Wetter-API-Feed | **Kommerzielles System (Connect)** | Aussentemperatur via OpenWeatherMap Webhook |
| n8n Workflow | **Automatisierung (Orchestrate)** | Verarbeitet Alerts, sendet Benachrichtigungen |

### Demo-Ablauf (5 Minuten):

**Minute 1 — "Build": Das eigene Geraet einbinden**
- ESP32 liegt auf dem Tisch, LED blinkt
- Im HubEx-Dashboard: Pairing starten (Token oder QR-Code)
- ESP32 meldet sich an → erscheint als "Office-Sensor-01" mit Status "online"
- *Kernaussage: "In 30 Sekunden ist mein selbstgebauter Sensor in der Plattform."*

**Minute 2 — "Connect": Externe Datenquelle ankoppeln**
- Webhook-Subscription in HubEx zeigen: OpenWeatherMap liefert Aussenwetterdaten
- Oder: Einen zweiten "virtuellen Sensor" zeigen, der als Software-Agent laeuft (z.B. ein Python-Skript auf dem Laptop, das CPU-Temperatur meldet)
- *Kernaussage: "Nicht nur eigene Hardware — auch APIs, Software-Agents und Fremdgeraete kommen ueber den selben Hub."*

**Minute 3 — "Orchestrate": Alles verbinden**
- Alert-Regel anlegen: "Wenn Innentemperatur > 28 Grad UND Aussentemperatur > 30 Grad → Warnung"
- Entity/Gruppe zeigen: "Office Floor 2" enthaelt den physischen Sensor und den virtuellen Wetter-Feed
- *Kernaussage: "Geraete aus voellig verschiedenen Welten — eigene Hardware, externe API — in einer Logik vereint."*

**Minute 4 — Alert ausloesen + Automatisierung**
- Sensor erwaermen (Foehn/Anhauchung) → Temperatur steigt ueber Schwellwert
- Alert erscheint im Dashboard (roter Indikator)
- Webhook feuert → n8n Workflow empfaengt → sendet E-Mail/Slack-Nachricht
- E-Mail auf dem Handy zeigen
- *Kernaussage: "Vom physischen Ereignis zur digitalen Reaktion in Sekunden — vollautomatisch."*

**Minute 5 — OTA-Update ausrollen**
- Neue Firmware hochladen (z.B. v1.1 mit geaendertem Mess-Intervall)
- Staged Rollout starten: "Erst 1 Geraet, dann alle"
- ESP32 empfaengt Update, startet neu, meldet neue Version
- *Kernaussage: "Updates ueber die Luft, ohne ein Geraet anfassen zu muessen. Bei 1 Geraet praktisch, bei 10.000 ueberlebenswichtig."*

### Backup-Szenario (falls Hardware streikt):

Voraufgezeichneter Screencast des identischen Flows. Zusaetzlich kann die Demo auch rein software-basiert funktionieren: Zwei Python-Agents auf dem Laptop (simulieren Sensor + Wetter-API) statt physischer Hardware.

---

## 5. Aktueller Stand laut Roadmap

### Was bereits fertig ist (Phase 1 + Phase 2 fast komplett):

**Backend — 100% der Core-Features fertig:**

Die gesamte Plattform-Engine steht. Authentifizierung mit JWT und einem feingranularen Capability-System (ueber 60 Berechtigungen). Device Management mit Pairing, Heartbeat, Telemetrie. Ein vollstaendiges Variablen-System mit Definitionen, Werten, Snapshots und Acknowledgements. Task- und Execution-System mit verteilter Verarbeitung. Entity- und Gruppen-System fuer hierarchische Geraete-Organisation mit aggregierter Health-Berechnung. Event-System mit Cursor-basiertem Streaming. Webhook-Dispatcher mit Retry-Logik, HMAC-Signierung und Delivery-Tracking — fertig fuer n8n. Alert-System mit vier Regeltypen (device_offline, entity_health, effect_failure_rate, event_lag). Multi-Tenancy mit Organisationen, Mitgliederverwaltung und Plan-Limits (Free/Pro/Enterprise). OTA mit drei Rollout-Strategien (Immediate, Staged, Canary). Production-Hardening mit Redis Rate-Limiting, ETag-Caching, CORS, Structured Logging und Graceful Shutdown. Ueber 20 REST-API-Endpunktgruppen dokumentiert und funktional.

**Frontend — ~90% fertig:**

Vue 3 + Tailwind Design System mit 16+ wiederverwendbaren Komponenten. Dashboard, Devices, Entities, Alerts, OTA, Settings, Webhooks, Events, Audit — alles migriert auf das neue Design. Nur Mobile Responsive + Final Polish fehlt noch (M8/Step 9).

### Was das bedeutet:

HubEx ist kein Konzept oder Prototyp — es ist eine funktionsfaehige Plattform mit produktionsreifem Backend. Die Kernversprechen "Build" (Device-Anbindung, SDK) und "Orchestrate" (Webhooks, Events, Alerts) funktionieren bereits. "Connect" (Anbindung kommerzieller Geraete via Bridges/Provider) ist infrastrukturell vorbereitet (Webhook-System, Provider-Modelle existieren), aber die spezialisierten Bridges fehlen noch.

---

## 6. Fehlende Schritte bis zum perfekten Praesentationsstand

### Tier 1: Absolute Must-Haves (ohne diese keine Demo)

| # | Step | Aufwand | Warum? |
|---|------|---------|--------|
| 1 | **M8/Step 9** — Mobile Responsive + UI Polish | 2h | Die UI ist das Erste, was das Publikum sieht. Muss professionell wirken. |
| 2 | **M9/Step 1** — ESP32 SDK Update (OTA, Edge Config, Heartbeat) | 3h | Ohne aktuelles SDK kann der ESP32 nicht OTA empfangen und Edge Config nutzen. |
| 3 | **M9/Step 2** — End-to-End Demo Flow (ESP → Telemetrie → Alert → Webhook → n8n) | 4h | DAS Herzstueck. Ohne diesen Step gibt es keine Live-Demo. |
| 4 | **M9/Step 3** — QR-Code Provisioning | 2h | Der visuelle "Wow-Moment": Scan → verbunden. Zeigt wie einfach Onboarding ist. |

**Aufwand Tier 1: ~11h**

### Tier 2: Hochrelevant fuer die Botschaft "Connect + Orchestrate"

| # | Step | Aufwand | Warum? |
|---|------|---------|--------|
| 5 | **Software-Agent Demo** (kein Roadmap-Step, aber essentiell) | 2-3h | Ein simples Python-Skript als "virtuelles Geraet" zeigt: HubEx ist nicht nur fuer Hardware. Demonstriert die "Connect"-Saeule. |
| 6 | **M11/Step 1** — n8n Webhook Templates | 2h | Vorkonfigurierte Flows machen die Demo fluessig. Zeigt die n8n-Synergie. |
| 7 | **Externer API-Feed als Datenquelle** (kein Roadmap-Step) | 1-2h | Z.B. OpenWeatherMap-Daten via Webhook einspeisen. Zeigt "kommerzielle Systeme anbinden". |

**Aufwand Tier 2: ~6h**

### Tier 3: Professioneller Rahmen

| # | Step | Aufwand | Warum? |
|---|------|---------|--------|
| 8 | **M10/Step 2** — Docker Production Compose | 3h | Stabiles, reproduzierbares Setup fuer den Demo-Rechner. |
| 9 | **M12.5/Step 1** — Pitch Deck (Slides) | 3h | Die eigentlichen Praesentationsfolien. |
| 10 | **Demo-Screencast als Backup** | 1h | Falls Hardware oder Internet versagen. |

**Aufwand Tier 3: ~7h**

### Tier 4: Nice-to-Have (beeindruckend, nicht blockierend)

| # | Step | Aufwand | Warum? |
|---|------|---------|--------|
| 11 | **M12/Step 1+2** — API Docs + Getting Started | 4h | Leave-Behind-Material nach der Praesentation. |
| 12 | **M12.5/Step 2** — Product Landing Page | 4h | Gibt HubEx eine "Adresse" im Netz. |
| 13 | **M10/Step 1** — GitHub Actions CI/CD | 2h | Zeigt Professionalitaet, aber kein Demo-Blocker. |

**Aufwand Tier 4: ~10h**

---

## 7. Empfohlene Reihenfolge bis zur Praesentation

### Sprint 1 (Woche 1): Foundation — "Alles muss laufen"

```
Tag 1:  M8/Step 9 — UI Polish + Responsive               [2h]
Tag 2:  M9/Step 1 — ESP32 SDK Update                      [3h]
Tag 3:  M10/Step 2 — Docker Production Compose             [3h]
        → Checkpoint: Backend + Frontend + ESP SDK ready
```

### Sprint 2 (Woche 2): Demo-Flow — "Die Geschichte erzaehlen"

```
Tag 1-2: M9/Step 2 — End-to-End Demo Flow                 [4h]
Tag 2:   M9/Step 3 — QR-Code Provisioning                 [2h]
Tag 3:   Software-Agent Demo (Python Virtual Device)       [2h]
Tag 3:   Externer API-Feed einbinden                       [1h]
Tag 4:   M11/Step 1 — n8n Webhook Templates                [2h]
         → Checkpoint: Kompletter Demo-Flow laeuft
```

### Sprint 3 (Woche 3): Praesentation — "Die Buehne bauen"

```
Tag 1:   Pitch Deck erstellen                              [3h]
Tag 2:   Demo 3x komplett durchspielen + Timing            [2h]
Tag 2:   Backup-Screencast aufnehmen                       [1h]
Tag 3:   Generalprobe mit Testpublikum                     [1h]
         → READY
```

### Gesamtaufwand:

| Kategorie | Stunden |
|-----------|---------|
| Tier 1 (Must-Have) | 11h |
| Tier 2 (Connect-Story) | 6h |
| Tier 3 (Rahmen) | 7h |
| **Gesamt bis Demo-Ready** | **~24h** |
| Tier 4 (Nice-to-Have) | +10h |

---

## Business-Empfehlungen fuer die Praesentation

### Zielgruppen-spezifische Anpassungen:

**Fuer Investoren:**
- Fokus auf Marktluecke: "n8n fuer IoT" ist unbesetzt
- Marktgroesse nennen ($11 Mrd., 24% CAGR)
- First-Mover-Vorteil betonen
- Business Model: Freemium (Free/Pro/Enterprise) + Self-Hosted-Lizenz
- Frage beantworten: "Warum jetzt?" → Google Cloud IoT eingestellt, Vendor-Lock-in-Backlash, Edge Computing explodiert

**Fuer technische Partner / Integratoren:**
- Fokus auf Architektur: Capability-System, Multi-Tenancy, Module-System
- API-first Design zeigen (20+ Endpunktgruppen)
- Webhook + n8n Integration demonstrieren
- Open-Source-Strategie erklaeren

**Fuer potenzielle Kunden / IoT-Teams:**
- Fokus auf Time-to-Market: "Von ESP32-Prototyp zu Produktion in Tagen statt Monaten"
- Kostenvergleich: HubEx vs. AWS IoT bei 1.000 Geraeten
- Live-Demo steht im Mittelpunkt
- Getting-Started-Guide als Leave-Behind

### Dont's — Was man NICHT sagen sollte:

- Nicht "wir ueberwachen IoT-Geraete" — das ist generisch und kein Alleinstellungsmerkmal
- Nicht "wir sind wie AWS IoT, nur kleiner" — falsche Positionierung, falscher Vergleich
- Nicht zu tief in technische Details (JWT, Redis, HMAC) — das interessiert nur Entwickler im 1:1
- Nicht alle 27 Milestones aufzaehlen — Fokus auf die drei Saeulen und die Vision

### Do's — Was gut ankommt:

- **Geschichte erzaehlen**: "Ich hatte das Problem selbst" → Authentizitaet
- **Live-Demo**: Nichts ueberzeugt mehr als ein funktionierender Flow
- **Analogien nutzen**: "n8n fuer die physische Welt" ist sofort verstaendlich
- **Zukunft andeuten**: Rules Engine, AI-Agent-Steuerung, Plugin Marketplace
- **Vergleich fair gestalten**: Nicht gegen AWS/Azure bashen, sondern die eigene Nische betonen

---

## Checkliste vor der Praesentation

### Technik:
- [ ] ESP32 mit aktuellem SDK geflasht und getestet
- [ ] Zweiter ESP32 als Backup dabei
- [ ] Python Software-Agent getestet
- [ ] HubEx auf Demo-Rechner deployt (Docker Compose)
- [ ] n8n-Instanz mit Webhook-Template konfiguriert
- [ ] E-Mail-Empfang fuer Alert-Demo getestet
- [ ] Internet-Backup (Mobile Hotspot) dabei
- [ ] Screencast als Fallback aufgenommen

### Praesentation:
- [ ] Pitch Deck fertig (max. 10-12 Slides)
- [ ] Elevator Pitch auswendig geuebt (30 Sek.)
- [ ] Demo mindestens 3x komplett durchgespielt
- [ ] Timing geprueft (10-15 Min. gesamt)
- [ ] Generalprobe mit einer Person gemacht
- [ ] Q&A-Antworten vorbereitet: "Wie monetarisiert ihr?", "Warum nicht AWS?", "Wie skaliert das?"

### Material:
- [ ] Visitenkarten / Kontaktdaten
- [ ] QR-Code zu Landing Page oder GitHub
- [ ] Leave-Behind: 1-Pager oder Getting-Started-Link
- [ ] USB-Stick mit Pitch Deck + Screencast als Backup

---

*Erstellt am 27. Maerz 2026 — basierend auf Codebase-Analyse, ROADMAP.md und Marktrecherche.*
