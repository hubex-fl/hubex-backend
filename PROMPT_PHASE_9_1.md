# PROMPT PHASE 9 — Sprint 1: M9 + M10 Kickoff

## Kontext
Phase 3 (Variable Data Hub, M8c + M8d) ist vollständig abgeschlossen.
Phase 4 startet mit M9 (Device Integration Demo) und M10 (CI/CD).

Das Ziel dieser Phase: HUBEX wird **deploybar** und zeigt den vollständigen
End-to-End-Flow von echter Hardware (ESP32) bis zur Visualisierung.

## Was implementiert werden soll

### Prio 1: Variable Threshold Alert UI (M8d Step 3 — fehlende Frontend-Hälfte)
Die Backend-Seite ist done (`variable_threshold` condition_type).
Jetzt die UI:
- In `Alerts.vue` → Alert Rule Create/Edit Modal:
  - Dropdown für `condition_type` erweitern: `variable_threshold` Option hinzufügen
  - Wenn `variable_threshold` gewählt: dynamische Felder zeigen:
    - `variable_key` (Text-Input oder Select aus verfügbaren Definitions)
    - `threshold_operator` (Select: gt/gte/lt/lte/eq/ne mit Labels)
    - `threshold_value` (Number-Input)
    - `device_uid` (Optional, Select aus Devices)
  - `condition_config` JSON automatisch zusammenbauen

### Prio 2: Alerts.vue — Variable-Alert Cards zeigen
- Wenn `condition_type === "variable_threshold"`: In der Regel-Karte anzeigen:
  - `variable_key` + Operator + Threshold Value als lesbarer Satz
  - Z.B.: "smoke_level gt 80"

### Prio 3: M10 Step 1 — GitHub Actions CI
Neue Datei `.github/workflows/backend.yml`:
```yaml
name: Backend CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: hubex_test
          POSTGRES_USER: hubex
          POSTGRES_PASSWORD: hubex
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest tests/ -x -q
        env:
          DATABASE_URL: postgresql+asyncpg://hubex:hubex@localhost:5432/hubex_test
          REDIS_URL: redis://localhost:6379/0
          JWT_SECRET: test-secret-key
```

Neue Datei `.github/workflows/frontend.yml`:
```yaml
name: Frontend CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd frontend && npm ci
      - run: cd frontend && npx tsc --noEmit
      - run: cd frontend && npx vite build
```

### Prio 4: Streams Page — USelect `options` prop cleanup
In allen anderen Seiten die noch `<USelect>` mit `<option>` Slot-Children
nutzen: Auf `options` prop konvertieren (Variables.vue hat mehrere).
Stellt sicher, dass keine Vue prop-warnings mehr vorkommen.

## Files
- `frontend/src/pages/Alerts.vue` — Variable-Trigger in Create/Edit Modal
- `.github/workflows/backend.yml` — CI Pipeline (falls noch nicht existiert)
- `.github/workflows/frontend.yml` — CI Pipeline (falls noch nicht existiert)
- `frontend/src/pages/Variables.vue` — USelect auf options prop umstellen

## Verifikation
1. `npx tsc --noEmit` + `npx vite build` — clean
2. Preview: Neues Alert Rule erstellen → condition_type "variable_threshold" wählen → dynamische Felder erscheinen
3. Alert Rule Card zeigt Variable-Trigger Bedingung lesbar an
4. GitHub Actions YAML valide (kein Syntax-Error)
