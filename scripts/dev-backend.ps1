param(
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
  Write-Host "Missing .venv. Create it with:" -ForegroundColor Yellow
  Write-Host "  python -m venv .venv"
  Write-Host "  .\.venv\Scripts\Activate.ps1"
  Write-Host "  python -m pip install -r requirements.txt"
  exit 1
}

Write-Host "Activating venv..."
. .\.venv\Scripts\Activate.ps1

Write-Host "Tip: install deps if needed: python -m pip install -r requirements.txt"
Write-Host "Starting backend on port $Port..."
python -m uvicorn app.main:app --reload --port $Port
