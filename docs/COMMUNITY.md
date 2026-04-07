# Community Setup Guide

## GitHub

### Discussions
1. Gehe zu Repository → Settings → Features → Discussions aktivieren
2. Kategorien erstellen:
   - **Announcements** (nur Maintainer) — Releases, wichtige Updates
   - **Support** (Q&A) — Fragen zur Installation und Nutzung
   - **Feature Requests** (Ideas) — Neue Feature-Vorschläge
   - **Show & Tell** — Community-Projekte zeigen

### Issues
- Bug Reports: Template mit Steps to Reproduce
- Feature Requests: Template mit Use Case + Proposed Solution
- Security: Hinweis auf private Meldung (kein öffentliches Issue)

### Releases
- Semantic Versioning (MAJOR.MINOR.PATCH)
- CHANGELOG.md bei jedem Release aktualisieren
- Docker Images taggen: `hubex/backend:v0.1.0`, `hubex/frontend:v0.1.0`

## Discord

### Server-Struktur
```
#announcements    — Release Notes, wichtige Updates (read-only)
#general          — Allgemeine Diskussion
#support          — Hilfe bei Installation, Konfiguration
#showcase         — "Schaut was ich gebaut habe"
#dev              — Technische Diskussion, PRs, Architecture
#hardware         — ESP32, Arduino, Sensoren, Shields
#integrations     — n8n, Home Assistant, KNX, MQTT
```

### Rollen
- **Maintainer** — Core Team
- **Contributor** — Hat mindestens 1 PR merged
- **Community** — Alle anderen

## Marketplace (Zukunft)

### Content-Typen
- **Templates**: Dashboard + Automation + Variable-Defs
- **Blueprints**: Komplette Projekte mit Hardware-Liste
- **Plugins**: Eigene Logik/UI-Erweiterungen
- **Device Profiles**: Modbus/MQTT Gerätekonfigurationen

### Quality Levels
- **Community**: Ungeprüft, peer-reviewed
- **Verified**: Getestet vom Core Team
- **Official**: Vom Hersteller/Partner
