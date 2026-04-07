# HUBEX VPS Setup Guide (Clean Install)

Complete guide for deploying HUBEX on a fresh Ubuntu VPS.

## Prerequisites

- Ubuntu 22.04 or 24.04 VPS (min 2GB RAM, 20GB SSD)
- SSH access as root or sudo user
- Domain pointing to VPS IP (optional but recommended)

## Step 1: System Setup

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose (v2 plugin)
apt install -y docker-compose-plugin

# Verify
docker --version
docker compose version
```

## Step 2: Clone & Configure

```bash
# Clone repo
cd /opt
git clone https://github.com/YOUR_REPO/hubex-backend.git hubex
cd hubex

# Create .env file
cat > .env << 'EOF'
HUBEX_DB_PASSWORD=CHANGE_ME_STRONG_PASSWORD
HUBEX_JWT_SECRET=CHANGE_ME_RANDOM_64_CHARS
HUBEX_CORS_ORIGINS=http://YOUR_VPS_IP,http://YOUR_DOMAIN
HUBEX_PORT=8000
HUBEX_FRONTEND_PORT=80
EOF

# Generate secure values
sed -i "s/CHANGE_ME_STRONG_PASSWORD/$(openssl rand -base64 24)/" .env
sed -i "s/CHANGE_ME_RANDOM_64_CHARS/$(openssl rand -hex 32)/" .env
```

**IMPORTANT:** Edit `.env` and replace `YOUR_VPS_IP` / `YOUR_DOMAIN` with actual values:
```bash
nano .env
```

## Step 3: Build & Start

```bash
# Build all images from scratch (no cache)
docker compose -f docker-compose.prod.yml build --no-cache

# Start everything
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps
```

Wait 30 seconds for PostgreSQL + Redis to initialize, then verify:
```bash
# Check backend health
curl -s http://localhost:8000/health | python3 -m json.tool

# Check frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:80/

# Check logs for errors
docker compose -f docker-compose.prod.yml logs backend --tail 50
docker compose -f docker-compose.prod.yml logs frontend --tail 20
```

## Step 4: Create First User

Open `http://YOUR_VPS_IP` in your browser.

1. Click "Create one" on the login page
2. Enter email + password
3. You're logged in with an auto-created Organization

Or via API:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "YourPassword123!"}'
```

## Step 5: Run Simulators (Optional)

From your LOCAL machine (not VPS), to generate test data:

```bash
cd scripts
pip install requests websockets

# Run all 4 simulators against VPS
python sim_all.py --server http://YOUR_VPS_IP:8000 \
  --email admin@example.com \
  --password "YourPassword123!"
```

Simulators auto-pair devices and send telemetry every 10-30 seconds.

---

## Troubleshooting

### Login doesn't work / "email already registered"

```bash
# Full reset: remove all data volumes
docker compose -f docker-compose.prod.yml down -v

# Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build
```

Also clear your browser's localStorage:
- Open DevTools (F12) → Application → Local Storage → Clear

### i18n shows raw keys (auth.signIn instead of "Sign in")

This means the frontend Docker image is stale. Force rebuild:

```bash
docker compose -f docker-compose.prod.yml build --no-cache frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

### Variables don't appear for devices

Variables are auto-discovered from telemetry. No telemetry = no variables.

1. Run simulators (Step 5) or pair a real device
2. Wait for first telemetry message (10-30 seconds)
3. Refresh the Device Detail page

### Backend won't start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs backend --tail 100

# Common: PostgreSQL not ready yet - just wait and retry
docker compose -f docker-compose.prod.yml restart backend
```

### Port already in use

```bash
# Check what's using port 80/8000
ss -tlnp | grep -E ':80|:8000'

# Stop conflicting services
systemctl stop nginx apache2 2>/dev/null
```

### CORS errors in browser console

Edit `.env` and add your domain to HUBEX_CORS_ORIGINS:
```bash
HUBEX_CORS_ORIGINS=http://YOUR_IP,http://YOUR_DOMAIN,https://YOUR_DOMAIN
```
Then restart: `docker compose -f docker-compose.prod.yml up -d`

---

## Full Reset (Nuclear Option)

```bash
cd /opt/hubex

# Stop everything and delete ALL data
docker compose -f docker-compose.prod.yml down -v

# Remove images
docker rmi hubex-backend hubex-frontend 2>/dev/null

# Pull latest code
git pull origin main

# Rebuild from scratch
docker compose -f docker-compose.prod.yml build --no-cache

# Start fresh
docker compose -f docker-compose.prod.yml up -d
```

Clear browser localStorage after reset!

---

## Adding HTTPS (Optional)

Install Caddy as reverse proxy:

```bash
apt install -y caddy

cat > /etc/caddy/Caddyfile << 'EOF'
yourdomain.com {
    reverse_proxy localhost:80
}
EOF

systemctl restart caddy
```

Update `.env`:
```bash
HUBEX_CORS_ORIGINS=https://yourdomain.com
HUBEX_FRONTEND_PORT=3000  # Move frontend to avoid conflict with Caddy
```

---

## Quick Reference Commands

```bash
# Status
docker compose -f docker-compose.prod.yml ps

# Logs (follow)
docker compose -f docker-compose.prod.yml logs -f backend

# Restart single service
docker compose -f docker-compose.prod.yml restart backend

# Update code + rebuild
git pull && docker compose -f docker-compose.prod.yml up -d --build

# DB shell
docker exec -it hubex-postgres psql -U hubex hubex
```
