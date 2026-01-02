# DEV

Single entry point for local development.

## Quickstart
PowerShell:
```
.\.venv\Scripts\Activate.ps1
python -m pip install -U -r requirements.txt -r requirements-dev.txt
```

bash:
```
source .venv/bin/activate
python -m pip install -U -r requirements.txt -r requirements-dev.txt
```

## Phase-1 gates (local)
PowerShell:
```
.\scripts\run-phase1-gates.ps1
```

bash:
```
./scripts/run-phase1-gates.sh
```

## Environment variables
See `docs/ENV.md`.

## Smoke scripts
See `docs/SMOKE.md`.

## CI gates
See `.github/workflows/phase1_gates.yml`.

## Release
See `docs/RELEASE.md`.
