# HUBEX Scaling Guide

## Architecture Overview

HUBEX consists of:
- **Stateless API layer** — FastAPI (uvicorn) serving REST endpoints
- **Stateful background tasks** — async loops running in the API process
- **PostgreSQL** — primary data store
- **Redis** (optional) — rate limiting, response cache, telemetry queue

### Component Map

```
                     ┌─────────────┐
                     │   Clients   │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │  Uvicorn    │
                     │  (FastAPI)  │
                     ├─────────────┤
                     │ Background  │
                     │  Tasks (12) │
                     └──┬─────┬────┘
                        │     │
               ┌────────▼┐  ┌─▼────────┐
               │PostgreSQL│  │  Redis   │
               │          │  │(optional)│
               └──────────┘  └──────────┘
```

## Environment Variables

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `HUBEX_DATABASE_URL` | (required) | PostgreSQL async connection string |
| `HUBEX_DB_POOL_SIZE` | 5 | SQLAlchemy connection pool size |
| `HUBEX_DB_MAX_OVERFLOW` | 20 | Max overflow connections |

### Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `HUBEX_REDIS_URL` | "" | Redis connection URL. If empty, rate limiting uses in-memory fallback, caching disabled |

### Scaling Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `HUBEX_HISTORY_RETENTION_DAYS` | 30 | Variable history retention (older records pruned daily) |
| `HUBEX_AUDIT_RETENTION_DAYS` | 90 | Variable audit log retention |
| `HUBEX_TELEMETRY_QUEUE_ENABLED` | false | Enable Redis Streams for async telemetry processing |
| `HUBEX_AUTOMATION_CONCURRENCY` | 10 | Max concurrent automation action executions |
| `HUBEX_AUTOMATION_BATCH_SIZE` | 200 | Max system events processed per automation engine cycle |
| `HUBEX_RATE_LIMIT_ENABLED` | true | Enable rate limiting |
| `HUBEX_CACHE_ENABLED` | true | Enable response caching |

## Background Tasks

All background tasks run as `asyncio.create_task()` coroutines in the main process.

| Task | Interval | Purpose | Singleton? |
|------|----------|---------|-----------|
| `_token_cleanup_loop` | 6h | Prune expired revoked JWT tokens | Yes |
| `webhook_dispatcher_loop` | continuous | Dispatch queued webhook deliveries | Yes |
| `alert_worker_loop` | 30s | Evaluate alert rules, fire alert events | Yes |
| `health_worker_loop` | continuous | Device health monitoring | Yes |
| `ota_worker_loop` | continuous | OTA firmware rollout management | Yes |
| `history_retention_loop` | 1h | Prune variable_history older than retention | Yes |
| `automation_engine_loop` | 5s | Evaluate automation rules against system events | Yes |
| `partition_maintenance_loop` | 24h | Create/drop DB partitions, prune audit logs | Yes |
| `telemetry_worker_loop` | continuous | Redis Stream consumer for telemetry (if enabled) | Yes |
| `_demo_heartbeat_loop` | 60s | Update demo device last_seen_at | No (dev only) |
| `_api_poll_worker_loop` | 30s | Poll service-type device endpoints | Yes |
| `_computed_variables_loop` | 30s | Recompute formula-based variables | Yes |

**Important:** All singleton tasks must run on exactly ONE instance. If running multiple uvicorn processes, only one should run background tasks (use `--workers 1` or a separate worker process).

## Deployment Patterns

### Single Node (Development/Small)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- 1 uvicorn process, 1 worker
- All background tasks run in-process
- Suitable for < 50 devices, < 10 req/s

### Single Node + Redis (Production Small)

```bash
# .env
HUBEX_REDIS_URL=redis://localhost:6379/0
HUBEX_TELEMETRY_QUEUE_ENABLED=true
HUBEX_DB_POOL_SIZE=10
HUBEX_DB_MAX_OVERFLOW=30

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Redis enables: rate limiting (distributed), response caching, telemetry queueing
- Suitable for < 200 devices, < 50 req/s

### Multi-Process (Production Medium)

```bash
# Process 1: API + Background Tasks
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Process 2-N: API Only (no background tasks)
# TODO: Add HUBEX_DISABLE_BACKGROUND_TASKS=true flag
# For now, run only 1 process with background tasks
```

**Current limitation:** Background tasks are tightly coupled to the API process. Running multiple workers (`--workers N`) will duplicate all background tasks. This is planned for future separation.

### Kubernetes (Production Large)

```yaml
# 1 Deployment for API + Tasks (replicas: 1)
# 1 Deployment for API only (replicas: N, when task separation is implemented)
# 1 StatefulSet for PostgreSQL
# 1 Deployment for Redis
```

## Database Optimization

### Connection Pool

The default pool (5 connections, 20 overflow) is sufficient for single-process deployments. For multi-process:

```
Total connections = processes × (pool_size + max_overflow)
```

PostgreSQL `max_connections` must exceed this total. Default PostgreSQL max is 100.

### Partitioning

The `variable_history` table supports PostgreSQL range partitioning on `recorded_at`. When partitioned:

- Monthly partitions created automatically by `partition_maintenance_loop`
- Expired partitions dropped instantly (vs slow DELETE)
- Queries on recent data only scan relevant partitions

To enable partitioning, run the migration that converts `variable_history` to a partitioned table. This requires PostgreSQL 12+.

### Indexes

Key indexes for performance:
- `variable_history(variable_key, device_id, recorded_at)` — history queries
- `variable_history(device_id, recorded_at)` — device-scoped queries
- `events_v1(stream, id)` — automation engine polling
- `api_keys(key_hash)` — API key authentication

## Telemetry Pipeline

### Default (Synchronous)

```
POST /telemetry → DB Write → Variable Bridge → History Write
```

Each telemetry message triggers 1 + N + N database operations inline.

### With Redis Streams (Async)

```
POST /telemetry → DB Write → Redis XADD
                                    ↓
            telemetry_worker → Variable Bridge → Batch History Write
```

Set `HUBEX_TELEMETRY_QUEUE_ENABLED=true` to enable. The API responds faster, variable processing happens asynchronously.

## Monitoring

### Health Endpoints

- `GET /health` — liveness probe (always 200 if process alive)
- `GET /ready` — readiness probe (checks DB + Redis connectivity)
- `GET /api/v1/metrics` — device counts, online/offline stats

### Key Metrics to Watch

- **Database connections:** `pg_stat_activity` count vs `max_connections`
- **Variable history size:** `SELECT count(*) FROM variable_history`
- **Event processing lag:** compare `max(events_v1.id)` with automation engine's `last_event_id`
- **Redis memory:** `INFO memory` — watch for cache + stream growth
- **API latency:** P95 response time from reverse proxy logs
