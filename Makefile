.PHONY: test lint format type-check fe-build fe-lint fe-typecheck ci install install-dev

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt

test:
	pytest tests/ -q

test-cov:
	pytest tests/ --cov=app --cov-report=term-missing -q

lint:
	ruff check app/ tests/
	ruff format --check app/ tests/

format:
	ruff format app/ tests/
	ruff check --fix app/ tests/

type-check:
	mypy app/ --ignore-missing-imports --no-strict-optional

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

fe-install:
	cd frontend && npm ci

fe-build:
	cd frontend && npm run build

fe-lint:
	cd frontend && npm run lint

fe-typecheck:
	cd frontend && npm run typecheck

# ---------------------------------------------------------------------------
# Combined
# ---------------------------------------------------------------------------

ci: lint type-check test fe-lint fe-typecheck fe-build
	@echo ""
	@echo "All CI checks passed."
