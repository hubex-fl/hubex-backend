# Quick-Start Guide

> 15 Minuten: Docker installieren → System läuft → erstes Device

## Voraussetzungen

- Docker Desktop ([download](https://docs.docker.com/get-docker/))
- Ein Webbrowser (Chrome/Firefox/Edge)

## 1. System starten (2 Minuten)

```bash
# Repository klonen
git clone https://github.com/hubex-fl/hubex-backend.git
cd hubex-backend

# Konfiguration erstellen
cp .env.example .env
# WICHTIG: HUBEX_JWT_SECRET ändern! (mindestens 32 Zeichen)

# System starten
docker-compose up -d
```

Das startet: PostgreSQL + Redis + HubEx Backend + Frontend

Öffne: **http://localhost:5173**

## 2. Account erstellen (1 Minute)

1. Klicke "Sign In"
2. Erstelle einen Account mit Email + Passwort
3. Du wirst automatisch eingeloggt

## 3. Erstes Device verbinden (5 Minuten)

1. Klicke **"+ New"** in der Sidebar oder **"Pair Device"** auf dem Dashboard
2. Wähle den Device-Typ:
   - **Hardware** — ESP32, Shelly, Sensoren
   - **Service** — REST APIs, Wetter-Dienste
   - **Bridge** — MQTT, Modbus, Protokolle
   - **Agent** — Software auf Raspberry Pi, Linux, Windows
3. Folge dem Wizard (Name eingeben, UID zuweisen)
4. Dein Device erscheint in der Device-Liste

## 4. Erste Daten sehen (2 Minuten)

- Gehe zu **Variables** → Deine Sensor-Werte erscheinen automatisch (Auto-Discovery)
- Jede Variable hat einen **semantischen Typ** (Temperatur, Feuchtigkeit, GPS, etc.)
- Klicke auf eine Variable für Details und Historie

## 5. Erstes Dashboard bauen (3 Minuten)

1. Gehe zu **Dashboards** → **"New Dashboard"**
2. Gib einen Namen ein → **Create**
3. Klicke **"Edit"** → **"Add Widget"**
4. Wähle Widget-Typ (Gauge, Line Chart, Toggle, etc.)
5. Wähle Device + Variable
6. **Save** → Dein Widget erscheint im Dashboard

## 6. Erste Automation (2 Minuten)

1. Gehe zu **Automations** → **"+ New Rule"**
2. Name: "Temperatur-Alarm"
3. **IF**: Variable Threshold → temperature > 40
4. **THEN**: Create Alert → Severity: warning
5. Speichern → Automation läuft automatisch

## Nächste Schritte

- **Alerts** einrichten für kritische Werte
- **Webhooks** für externe Integration (n8n, Zapier)
- **Entities** für Geräte-Gruppierung (Räume, Standorte)
- **Settings** für Branding, Export/Import, 2FA
