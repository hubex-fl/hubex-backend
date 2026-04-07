# Phase 10.2 — Docker Production Compose: Traefik, SSL, Backups

## Goal
Create a production-ready Docker Compose setup with Traefik as reverse proxy (automatic SSL via Let's Encrypt), a hardened app/worker/frontend stack, and automated Postgres backups.

## Files to Create

### `docker-compose.prod.yml`
Production compose with these services:

1. **traefik** — reverse proxy + Let's Encrypt TLS
   - Image: `traefik:v3.2`
   - Ports: 80, 443
   - Volumes: `/var/run/docker.sock` (read-only), `traefik_acme` volume for cert storage
   - Config via CLI args: `--providers.docker`, `--entrypoints.web`, `--entrypoints.websecure`, `--certificatesresolvers.letsencrypt`
   - HTTP→HTTPS redirect via middleware

2. **api** — FastAPI backend
   - Build: `Dockerfile` (existing)
   - No exposed ports (only Traefik labels)
   - Traefik labels: host rule, TLS, HTTPS redirect, rate-limit middleware
   - Env: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY` via `.env.prod`
   - `depends_on: [db, redis]`
   - Healthcheck: `GET /health` every 30s
   - Restart: `unless-stopped`

3. **worker** — background task worker
   - Build: `Dockerfile.worker_v1`
   - Same env as api, no Traefik labels
   - `depends_on: [db, redis]`
   - Restart: `unless-stopped`

4. **frontend** — Nginx serving built Vue SPA
   - Build: `Dockerfile.frontend` (new, multi-stage: Node build + nginx:alpine serve)
   - Traefik labels: host rule for frontend, or same host as API with path prefix
   - Serves static files from `/usr/share/nginx/html`

5. **db** — Postgres 16
   - `postgres:16-alpine`
   - Named volume `hubex_pg_prod`
   - Env: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
   - No exposed ports (internal only)
   - Healthcheck: `pg_isready`

6. **redis** — Redis 7
   - `redis:7-alpine`
   - Named volume `hubex_redis_prod`
   - No exposed ports
   - Command: `redis-server --appendonly yes` (persistence)

7. **backup** — Postgres backup sidecar
   - Image: `postgres:16-alpine`
   - Runs daily `pg_dump` → compressed `.sql.gz` in `/backups`
   - Retention: keeps last 14 dumps, deletes older ones
   - Volume: `hubex_backups` (bind-mountable to host)

### `Dockerfile.frontend`
Multi-stage build:
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
```

### `deploy/nginx.conf`
Nginx config for SPA:
- `try_files $uri $uri/ /index.html` (client-side routing)
- Cache headers for static assets (`*.js`, `*.css`, `*.woff2`)
- Gzip compression
- API proxy: `location /api/ { proxy_pass http://api:8000; }`
- Security headers: `X-Frame-Options`, `X-Content-Type-Options`

### `deploy/.env.prod.example`
Template for production environment variables:
```
SECRET_KEY=change-me-to-a-random-64-char-string
DATABASE_URL=postgresql+asyncpg://hubex:CHANGE_PASSWORD@db:5432/hubex
REDIS_URL=redis://redis:6379/0
HUBEX_DOMAIN=hubex.example.com
POSTGRES_USER=hubex
POSTGRES_PASSWORD=CHANGE_PASSWORD
POSTGRES_DB=hubex
LETSENCRYPT_EMAIL=admin@example.com
```

### `deploy/traefik.yml` (optional static config)
Static Traefik configuration (alternative to CLI flags):
- `api.insecure: false`
- `providers.docker.exposedByDefault: false`
- `log.level: INFO`
- `accessLog: {}`

## After Completion
1. Update ROADMAP.md: Step 2 done, Step 3 ← AKTUELL
2. Write report to REPORTS.md
3. Generate PROMPT_PHASE_10_3.md (One-Click Deploy Script)
