# Hubex Backend

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run Postgres (Docker)

```powershell
docker compose up -d
```

## Migrate DB

```powershell
alembic upgrade head
```

## Run API

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
