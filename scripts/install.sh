#!/bin/bash
# HUBEX One-Line Installer
# Usage: curl -fsSL https://get.hubex.io | bash
# Or: bash scripts/install.sh

set -e

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║       HUBEX Installer v0.1.0         ║"
echo "  ║    Universal IoT Device Hub          ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker Desktop first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi
echo "✅ Docker found: $(docker --version | head -1)"

# Check Docker Compose
if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found."
    exit 1
fi
echo "✅ Docker Compose found"

# Create directory
INSTALL_DIR="${HUBEX_DIR:-$HOME/hubex}"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"
echo "📁 Installing to: $INSTALL_DIR"

# Download docker-compose.prod.yml if not exists
if [ ! -f docker-compose.yml ]; then
    echo "📥 Downloading docker-compose.yml..."
    # In production: curl from GitHub release
    # For now: copy from repo
    echo "   Please copy docker-compose.prod.yml to $INSTALL_DIR/docker-compose.yml"
fi

# Create .env if not exists
if [ ! -f .env ]; then
    echo "🔧 Creating .env configuration..."
    JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || head -c 64 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 64)
    cat > .env << EOF
HUBEX_ENV=production
HUBEX_JWT_SECRET=$JWT_SECRET
HUBEX_DB_PASSWORD=$(openssl rand -hex 16 2>/dev/null || echo "hubex-$(date +%s)")
HUBEX_CORS_ORIGINS=http://localhost
HUBEX_PORT=8000
HUBEX_FRONTEND_PORT=80
EOF
    echo "✅ .env created with secure JWT secret"
else
    echo "✅ .env already exists"
fi

# Start services
echo ""
echo "🚀 Starting HUBEX..."
docker compose up -d 2>/dev/null || docker-compose up -d

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║       HUBEX is starting!             ║"
echo "  ║                                      ║"
echo "  ║  Frontend: http://localhost           ║"
echo "  ║  Backend:  http://localhost:8000      ║"
echo "  ║  Health:   http://localhost:8000/health║"
echo "  ║                                      ║"
echo "  ║  Wait ~30 seconds for all services   ║"
echo "  ║  to become healthy.                  ║"
echo "  ╚══════════════════════════════════════╝"
echo ""
echo "📖 Quick Start: https://github.com/hubex-fl/hubex-backend/docs/QUICKSTART.md"
echo ""
