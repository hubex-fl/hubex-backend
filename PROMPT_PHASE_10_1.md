# Phase 10.1 — CI/CD: GitHub Actions (Test, Build, Lint)

## Goal
Set up GitHub Actions workflows for automated testing, building, and linting of the HUBEX backend and frontend. This makes the project production-ready and enables safe, automated quality gates.

## Files to Create

### `.github/workflows/backend.yml`
CI pipeline for the FastAPI backend.

**Triggers:** push to `main`/`develop`, all pull requests

**Jobs:**
1. `lint` — ruff (linting) + ruff format --check (formatting)
2. `test` — pytest with coverage
   - Services: `postgres:15` + `redis:7` (via `services:`)
   - Env vars from `env:` block (TEST_DATABASE_URL, REDIS_URL, SECRET_KEY, etc.)
   - Run: `pip install -r requirements.txt`, `pytest tests/ --cov=app --cov-report=xml`
   - Upload coverage to Codecov (optional, add if CODECOV_TOKEN available)
3. `type-check` — mypy (strict mode on `app/`)

**Python version:** 3.11

### `.github/workflows/frontend.yml`
CI pipeline for the Vue 3 + TypeScript frontend.

**Triggers:** push to `main`/`develop`, all pull requests (only run if `frontend/**` changed)

**Jobs:**
1. `lint` — ESLint (`npm run lint`)
2. `type-check` — `vue-tsc --noEmit`
3. `build` — `npm run build` (verify Vite build succeeds, upload dist as artifact)

**Node version:** 20

### `.github/workflows/docker.yml`
Docker build + push pipeline.

**Triggers:** push to `main` only (not PRs)

**Jobs:**
1. Build Docker image for backend (`docker build -t hubex-backend .`)
2. Verify image starts and `/health` responds (smoke test via `docker run -d` + `curl`)

## Additional Files

### `Makefile` (root)
Developer shortcuts:
```makefile
test:        cd backend && pytest tests/
lint:        cd backend && ruff check . && ruff format --check .
format:      cd backend && ruff format .
type-check:  cd backend && mypy app/
fe-build:    cd frontend && npm run build
fe-lint:     cd frontend && npm run lint
fe-typecheck:cd frontend && npx vue-tsc --noEmit
ci:          make lint type-check test fe-lint fe-typecheck fe-build
```

## Backend Requirements
- `ruff` and `mypy` must be added to `requirements-dev.txt` (create if not exists)
- Verify `pytest` and `pytest-cov` are in requirements
- Backend tests must pass: `pytest tests/` should exit 0 against a test database

## Frontend Requirements
- `"lint"` script must exist in `frontend/package.json` (add ESLint if missing)
- `"type-check"` or `"build"` script must exit 0

## After Completion
1. Update ROADMAP.md: Milestone 10 Step 1 done, Step 2 ← AKTUELL
2. Write report to REPORTS.md
3. Generate PROMPT_PHASE_10_2.md (Docker Production Compose: Traefik, SSL, backups)
