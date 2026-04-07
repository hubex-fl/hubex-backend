# HubEx — Universal IoT Device Hub

> Verbinde alles. Verstehe alles. Steuere alles.

HubEx ist eine self-hosted IoT-Plattform die Hardware, APIs, Protokolle und Software-Agents in einem System vereint. Keine Cloud-Abhängigkeit, keine Geräte-Gebühren.

## Features

- **4 Device-Typen**: Hardware (ESP32), Service (REST API), Bridge (MQTT), Agent (Software)
- **20+ Semantische Typen**: Temperatur, GPS, Prozent, Spannung — automatische Erkennung
- **Dashboard Builder**: 9 Widget-Typen, Drag & Drop, Public Links, Kiosk-Modus
- **Automation Engine**: 7 Trigger + 7 Actions, AND/OR Logik, Cron, Email-Versand
- **RBAC**: 6 Rollen (Owner, Admin, Operator, Member, Viewer, Kiosk)
- **White-Label**: Eigenes Logo, Farben, Produktname — per UI konfigurierbar
- **Export/Import**: Konfiguration als JSON sichern und wiederherstellen
- **i18n**: Deutsch + Englisch

## Quick Start

```bash
# Docker Compose starten
cp .env.example .env
# .env anpassen: HUBEX_JWT_SECRET ändern!
docker-compose -f docker-compose.prod.yml up -d

# Öffne http://localhost
```

Detaillierte Anleitung: [docs/QUICKSTART.md](docs/QUICKSTART.md)

## Dokumentation

| Guide | Beschreibung |
|-------|-------------|
| [Quick Start](docs/QUICKSTART.md) | 15 Minuten zum laufenden System |
| [User Guide](docs/USER_GUIDE.md) | Alle Features erklärt |
| [API Guide](docs/API_GUIDE.md) | REST API, Webhooks, n8n |
| [Operator Runbook](docs/OPERATOR_RUNBOOK.md) | Deploy, Backup, Monitoring |
| [FAQ](docs/FAQ.md) | Häufige Fragen |
| [Scaling](docs/SCALING.md) | Performance & Skalierung |
| [Editions](docs/EDITIONS.md) | Community vs Enterprise |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy |
| Frontend | Vue 3, TypeScript, Tailwind CSS |
| Database | PostgreSQL 16 |
| Cache | Redis 7 (optional) |
| Deployment | Docker Compose |

## Editionen

**Community Edition** — Kostenlos, forever. Unbegrenzte Devices, Variables, Dashboards. 5 User.

**Enterprise Edition** — White-Label, Multi-Tenant, Custom API, Reports, Plugins. [Details](docs/EDITIONS.md)

## Contributing

Siehe [CONTRIBUTING.md](CONTRIBUTING.md) für Entwickler-Setup und PR-Prozess.

## License

Community Edition: [AGPL v3](LICENSE)
Enterprise Edition: Commercial License — Kontakt für Details.

---

Built with precision. Designed for makers, engineers, and enterprises.
