# HUBEX Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application + Alembic config
COPY app/ app/
COPY scripts/ scripts/
COPY alembic/ alembic/
COPY alembic.ini .

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Entrypoint: run migrations, then start app
RUN chmod +x scripts/docker-entrypoint.sh
ENTRYPOINT ["scripts/docker-entrypoint.sh"]
