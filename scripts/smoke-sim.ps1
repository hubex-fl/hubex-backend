$ErrorActionPreference = "Stop"

Write-Host "SMOKE_SIM: import app.simulator"
python -c "import app.simulator" | Out-Host

Write-Host "SMOKE_SIM: run help"
python -m app.simulator --help | Out-Host
