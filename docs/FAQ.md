# FAQ & Troubleshooting

## Installation

**Q: Docker Compose startet nicht**
A: Prüfe ob Docker Desktop läuft. `docker info` sollte keine Fehler zeigen. Auf Windows: Docker Desktop als Administrator starten.

**Q: Backend zeigt "connection refused"**
A: PostgreSQL Container nicht gestartet. `docker start hubex-postgres` ausführen. Prüfe HUBEX_DATABASE_URL in .env.

**Q: Frontend zeigt "unavailable" Badge**
A: Backend nicht erreichbar. Prüfe ob Backend auf dem richtigen Port läuft (Default: 8000). Frontend proxied zu diesem Port.

**Q: "Internal Server Error" beim Login**
A: Wahrscheinlich fehlende DB-Spalten. Führe das DB-Migrations-Script aus oder starte mit der neuesten Version die automatisch migriert.

## Devices

**Q: Device zeigt "offline" obwohl es läuft**
A: Heartbeat-Timeout ist 300 Sekunden. Prüfe ob das Device regelmäßig Telemetrie sendet. Prüfe Netzwerk-Verbindung.

**Q: Variables erscheinen nicht automatisch**
A: Auto-Discovery braucht mindestens eine Telemetrie-Nachricht. Sende einen Test-Payload: `POST /api/v1/telemetry` mit `{"event_type": "test", "payload": {"temperature": 23.5}}`.

**Q: Device kann sich nicht verbinden**
A: Prüfe Firewall (Port 8000 offen?). Prüfe CORS-Einstellungen (HUBEX_CORS_ORIGINS in .env). Prüfe ob das Device-Token korrekt ist.

## Dashboards

**Q: Widgets zeigen "—" statt Werten**
A: Variable hat keinen aktuellen Wert. Entweder Device offline oder noch nie Daten gesendet. Prüfe Variable-History.

**Q: Dashboard lädt langsam**
A: Viele Widgets mit großer History → Redis aktivieren (HUBEX_REDIS_URL). History-Retention reduzieren (HUBEX_HISTORY_RETENTION_DAYS).

## Automations

**Q: Automation feuert nicht**
A: Prüfe ob die Regel aktiviert ist (Toggle). Prüfe Cooldown (Default: 300s zwischen Auslösungen). Prüfe ob der Trigger-Typ zum Event passt.

**Q: Email-Versand funktioniert nicht**
A: SMTP muss in der .env konfiguriert sein. Prüfe HUBEX_SMTP_HOST, HUBEX_SMTP_PORT, etc.

## Performance

**Q: System wird langsam bei vielen Devices**
A: 1. Redis aktivieren. 2. HUBEX_HISTORY_RETENTION_DAYS reduzieren. 3. HUBEX_DB_POOL_SIZE erhöhen. Siehe docs/SCALING.md.

**Q: Variable History füllt die Festplatte**
A: Retention-Policy prüfen (Default: 30 Tage). Alte Daten werden automatisch gelöscht. Für sofortige Bereinigung: History-Export → alte Daten löschen.

## Sicherheit

**Q: Wie ändere ich den JWT Secret?**
A: In .env: `HUBEX_JWT_SECRET=dein-neuer-secret-min-32-zeichen`. Backend neustarten. ACHTUNG: Alle bestehenden Tokens werden ungültig, User müssen sich neu einloggen.

**Q: Wie aktiviere ich 2FA?**
A: Settings → Profile & Account → Two-Factor Authentication → Enable 2FA → Authenticator App scannen → Code bestätigen.

**Q: Wie setze ich HTTPS auf?**
A: Nginx als Reverse Proxy mit Let's Encrypt. Siehe docs/OPERATOR_RUNBOOK.md. Oder: Cloudflare Tunnel (zero-config HTTPS).
