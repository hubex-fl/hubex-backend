# Operator Runbook

## Deployment

### Docker Compose (empfohlen)
```bash
cp .env.example .env
# .env anpassen: HUBEX_JWT_SECRET, HUBEX_DATABASE_URL, etc.
docker-compose -f docker-compose.prod.yml up -d
```

### Minimum Ressourcen
| Devices | CPU | RAM | Disk |
|---------|-----|-----|------|
| bis 50 | 1 Core | 1 GB | 10 GB |
| bis 200 | 2 Cores | 4 GB | 20 GB |
| bis 1000 | 4 Cores | 8 GB | 50 GB |

### Ports
| Service | Port | Protokoll |
|---------|------|-----------|
| Backend API | 8000 | HTTP |
| Frontend | 5173 | HTTP |
| PostgreSQL | 5432 | TCP |
| Redis | 6379 | TCP |

## Backup

### Datenbank
```bash
# Backup erstellen
docker exec hubex-postgres pg_dump -U hubex hubex | gzip > backup_$(date +%Y%m%d).sql.gz

# Backup wiederherstellen
gunzip < backup_20260407.sql.gz | docker exec -i hubex-postgres psql -U hubex hubex
```

### Konfiguration
- Export: Settings → System → Export Config (JSON Download)
- Import: Settings → System → Import Config (JSON Upload)

### Automatische Backups
```bash
# Crontab: Täglich um 3:00 Uhr
0 3 * * * docker exec hubex-postgres pg_dump -U hubex hubex | gzip > /backups/hubex_$(date +\%Y\%m\%d).sql.gz
# 30 Tage aufbewahren
0 4 * * * find /backups -name "hubex_*.sql.gz" -mtime +30 -delete
```

## Update

```bash
# 1. Backup erstellen (IMMER vor Update!)
docker exec hubex-postgres pg_dump -U hubex hubex > pre_update_backup.sql

# 2. Neue Version ziehen
docker-compose pull

# 3. Neustart (DB-Migrations laufen automatisch)
docker-compose up -d

# 4. Health prüfen
curl http://localhost:8000/health
```

## Monitoring

### Health Endpoints
- `GET /health` → `{"status": "ok", "version": "0.1.0"}`
- `GET /ready` → Prüft DB + Redis Connectivity

### Wichtige Metriken
- **API Latenz**: P95 < 200ms
- **DB Connections**: `SELECT count(*) FROM pg_stat_activity` < max_connections
- **Disk Usage**: Variable History wächst ~1GB/Monat pro 100 Devices
- **Memory**: Backend ~200MB Base + ~50MB pro 100 concurrent connections

## Troubleshooting

### Backend startet nicht
```bash
# Logs prüfen
docker logs hubex-backend --tail 50

# Häufige Ursachen:
# - HUBEX_DATABASE_URL falsch → "connection refused"
# - Port belegt → "address already in use"
# - JWT Secret zu kurz → CRITICAL log
```

### Devices offline
1. Device Last Seen prüfen (Devices-Liste)
2. Heartbeat-Intervall: Default 60s, "dead" nach 300s
3. Netzwerk: Kann das Device den Server erreichen?

### Performance
1. System Health Seite prüfen
2. Redis aktivieren (HUBEX_REDIS_URL setzen) für Caching
3. Variable History Retention prüfen (HUBEX_HISTORY_RETENTION_DAYS)
