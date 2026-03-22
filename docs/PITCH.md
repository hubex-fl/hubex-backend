# HUBEX — The Open-Source Device Hub for Product Builders

---

## Was ist HUBEX?

HUBEX ist eine **selbst-gehostete Plattform, die Hardware mit Software verbindet**. Jedes Unternehmen, das ein IoT-Produkt baut — ob Sensor, Smart Device, oder industrieller Controller — braucht einen "Device Backend Stack": Pairing, Authentifizierung, State Management, Firmware Updates, APIs.

**Diesen Stack bauen die meisten von Null. HUBEX liefert ihn fertig.**

---

## Das Problem

| Ohne HUBEX | Mit HUBEX |
|-----------|-----------|
| 3-6 Monate eigenen Device-Stack bauen | **Tage** bis zum ersten verbundenen Device |
| Pairing, Token, OTA, State Sync selbst implementieren | Alles out-of-the-box, security-hardened |
| Vendor Lock-in bei AWS IoT / Azure IoT Hub | **Self-hosted**, volle Datenkontrolle |
| Jedes Protokoll einzeln integrieren | **Connector-System**: MQTT, HTTP, WebSocket, BLE, Serial |
| Eigene Automation bauen | **n8n/Node-RED Integration** für komplexe Flows |
| Security nachträglich patchen | **Deny-by-default** Capability System, Audit Trail, Token Rotation |

---

## Für wen?

**IoT Startups & Product Teams**
> "Wir bauen einen smarten Sensor. Wir wollen uns auf die Hardware und die App konzentrieren — nicht auf den Device-Backend-Stack."

**System Integratoren & Industrie 4.0**
> "Wir vernetzen 15 verschiedene Maschinentypen. Jede spricht ein anderes Protokoll. Wir brauchen eine einheitliche Schnittstelle."

**Maker & Power-User**
> "Ich habe 20 ESP32s im Haus. Home Assistant ist mir zu Consumer, eigener Code ist mir zu viel Aufwand."

---

## Was kann HUBEX?

### Heute (v0.1)
- **Device Pairing**: Sicherer, deterministischer Pairing-Flow (Device Hello → Code → Claim → Confirm)
- **Device Management**: Ownership, Token Rotation, Unclaim, Purge — alles auditiert
- **State Management**: Variables mit Snapshot/ACK-Modell (desired → effective → reported)
- **Task Execution**: Queue, Claim, Lease, Finalize — mit Worker-Support
- **Event System**: Append-only Event Stream mit Cursor-Pagination
- **Module System**: Plugin-Architektur mit Capability-Gating
- **Security**: JWT + HMAC Token Hashing, Deny-by-Default Capabilities, Token Revocation
- **Audit Trail**: Jede sicherheitsrelevante Aktion wird protokolliert
- **REST API**: Vollständig, dokumentiert, OpenAPI-kompatibel

### Morgen (Roadmap)
- **Multi-Protocol Connectors**: MQTT, WebSocket, BLE, Serial/Modbus
- **Device Twins**: AWS IoT Shadow-Konzept, aber self-hosted und einfacher
- **Webhook System**: n8n/Zapier/Make.com Integration
- **Grafana/Prometheus**: Monitoring out-of-the-box
- **Device SDKs**: ESP-IDF, Arduino, Python (Raspberry Pi)
- **Basic Rule Engine**: Einfache Event-driven Rules für schnelle Automations
- **Multi-Tenant**: Workspace-Isolation für SaaS-Betrieb

---

## Warum nicht AWS IoT / Azure IoT Hub?

| | AWS IoT Core | HUBEX |
|-|-------------|-------|
| **Kosten** | $1.00 pro Million Messages + Connection Fees | **Kostenlos** (self-hosted) |
| **Datenhoheit** | Amazon Datacenter | **Dein Server** |
| **Lock-in** | AWS SDK required | **Open API + jedes Protokoll** |
| **Komplexität** | IAM + Thing Registry + Rules + Shadows + ... | **Ein Binary, ein `docker compose up`** |
| **Für wen** | Enterprise mit AWS-Budget | **Jeder der Devices verbinden will** |

---

## Warum nicht Home Assistant?

Home Assistant ist **fantastisch für Enduser**. HUBEX ist für **Produktbauer**:

- HA hat kein API-first Device Provisioning
- HA hat keine Capability-basierte Security
- HA hat keine Device Twin / State Sync Semantik
- HA ist nicht designed als Backend-Service für eigene Apps
- HA skaliert nicht für 10.000+ Devices

HUBEX und Home Assistant sind **komplementär**: HUBEX managed die Devices, HA kann als Consumer/UI dienen.

---

## Technologie

- **Backend**: Python/FastAPI — async, performant, ecosystem-rich
- **Database**: PostgreSQL — robust, battle-tested
- **Security**: JWT + HMAC-SHA256 + Capability-based Access Control
- **Device SDKs**: ESP-IDF (C), Arduino (C++), Python
- **Deployment**: Docker/Kubernetes, self-hosted
- **Integration**: REST API, WebSocket, MQTT, Webhooks

---

## Business Model (Potenzial)

### Open-Core
- **Community Edition**: Alles was ein Maker/Startup braucht — kostenlos, open-source
- **Pro Edition**: Multi-Tenant, SSO/SAML, Priority Support, SLA
- **Cloud Edition**: Managed HUBEX — für Teams die nicht self-hosten wollen

### Connector Marketplace
- Community-built Connectors (BLE, Modbus, CAN, Zigbee, LoRa)
- Zertifizierte Connectors für Industrieprotokolle

---

## In einem Satz

> **HUBEX ist für IoT-Produkte, was Stripe für Payments ist: Der Stack den jeder braucht, aber keiner selbst bauen will.**
