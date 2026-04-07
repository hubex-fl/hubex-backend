# Marketplace Konzept

## Content-Typen

### Templates
Dashboard-Layout + Variable-Definitionen + Alert-Regeln als Bundle.
Beispiel: "Smart Home Temperatur-Monitoring" mit 3 Widgets + 2 Alerts.

### Blueprints
Komplettes Projekt-Paket: Devices + Dashboards + Automationen + Verdrahtungsplan + BOM.
Beispiel: "Gewächshaus-Automatisierung" mit ESP32, DHT22, Relay, Bewässerungslogik.

### Plugins
Eigene Logik/UI-Erweiterungen die IN HubEx laufen.
Beispiel: "Energy Dashboard Plugin" mit eigener Abrechnungsansicht.

### Device Profiles
Modbus/MQTT Gerätekonfigurationen für bestehende Hardware.
Beispiel: "Eastron SDM630 Energiezähler" mit Register-Map + Variablen.

## Quality Levels

| Level | Badge | Prüfung | Wer |
|-------|-------|---------|-----|
| **Community** | 🟡 | Keine Prüfung | Jeder |
| **Verified** | 🟢 | Getestet, funktional | Core Team Review |
| **Official** | 🔵 | Hersteller-verifiziert | Partner/Hersteller |

## Monetarisierung (WordPress-Modell)

- **Free Items**: Jeder kann kostenlose Inhalte teilen
- **Paid Items**: Ersteller setzt Preis, Plattform nimmt Provision (z.B. 20%)
- **Enterprise Only**: Bestimmte Items nur für EE-Lizenznehmer

## Technische Umsetzung

### Phase 1 (MVP)
- Export/Import Format als Basis (bereits implementiert)
- GitHub Repository als Katalog (Markdown-basiert)
- Manuelle Installation (Download → Import)

### Phase 2 (In-App)
- Marketplace-Tab in HubEx UI
- Suche + Filter + Bewertungen
- One-Click Install (API-basiert)

### Phase 3 (Ökosystem)
- Ersteller-Dashboard (Upload, Stats, Revenue)
- Review-Prozess für Verified-Status
- API für externe Marketplace-Clients
