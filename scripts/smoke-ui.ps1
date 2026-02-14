$ErrorActionPreference = "Stop"

param(
  [switch]$Build
)

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $repo
Set-Location -LiteralPath $repo

$frontend = Join-Path $repo "frontend"
$pkg = Join-Path $frontend "package.json"
if (-not (Test-Path -LiteralPath $pkg)) {
  throw "frontend/package.json not found"
}

if ($Build) {
  Push-Location $frontend
  try {
    npm install
    npm run build
  } finally {
    Pop-Location
  }
}

$dist = Join-Path $frontend "dist\\index.html"
if (-not (Test-Path -LiteralPath $dist)) {
  throw "frontend/dist/index.html missing (run: npm run build)"
}

Write-Host "OK: frontend build output present"
