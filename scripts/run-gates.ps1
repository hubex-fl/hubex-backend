param()

$ErrorActionPreference = "Stop"

$root = (git rev-parse --show-toplevel) 2>$null
if (-not $root) {
  throw "Not inside a git repo. Run from within the hubex repo."
}
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  throw "Missing .venv python at $py. Create venv and install deps first."
}
Write-Host "PY=$py"

function Run-Step([string]$name, [string[]]$cmd) {
  Write-Host "STEP $name"
  & $cmd[0] @($cmd[1..($cmd.Length - 1)])
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Run-Step "phase1 gates" @("$root\\scripts\\run-phase1-gates.ps1")
Run-Step "frontend typecheck" @("npm", "--prefix", "frontend", "run", "typecheck")
Run-Step "frontend test" @("npm", "--prefix", "frontend", "run", "test")
Run-Step "frontend build" @("npm", "--prefix", "frontend", "run", "build")

