---
name: HUBEX Project Overview
description: Core architecture, tech stack, and current state of the HUBEX IoT control plane
type: project
---

HUBEX is a universal IoT Device Hub — FastAPI backend + Vue 3 frontend + Postgres + Redis,
deployed as docker-compose.full.yml. "Device" is the overarching concept with four kinds:
Hardware, Service, Bridge, Agent. Vision: Anbinden → Verstehen → Visualisieren → Automatisieren.

**Architecture:**
- Backend: Python/FastAPI, async SQLAlchemy, Alembic migrations, JWT + capability-based auth,
  48 routes gated by `CAPABILITY_MAP` + `ROUTE_FEATURES` (feature-flag gating via `capability_guard`)
- Frontend: Vue 3 + Vite + TypeScript + Tailwind + Pinia, fully interactive (not read-only)
- Data: Postgres 16 (primary), Redis 7 (cache/rate-limit/streams), SecretV1 table for namespaced secrets
- Deploy: docker-compose.full.yml runs backend/frontend/postgres/redis/n8n/portainer on one network
- ESP SDK lives in a separate repo (hubex-esp-sdk), server-side ESP codegen is in Sprint 2
- Tests: pytest with in-memory SQLite + httpx AsyncClient (count no longer tracked in memory)

**Current state (post Sprint 3):**
- Phase 1-9 all shipped (core, UX, enterprise, release-readiness)
- Sprint Track: S1 feature flags + wizard, S2 ESP codegen, S3 Plugin Manager v2 (service+connector,
  portainer orchestration, 3-entry catalog) — all committed + pushed on `claude/suspicious-raman`
- Next: Sprint 4 firmware_builder (PlatformIO sidecar via the same `portainer_client`)

**Key files:**
- `app/core/capabilities.py` — cap registry + route map + role inheritance
- `app/core/features.py` — feature flag registry + ROUTE_FEATURES gating
- `app/core/portainer_client.py` — async REST wrapper, reused by sprint 4
- `app/core/plugin_catalog.py` — ship-with plugin definitions
- `app/main.py` `_COLUMN_PATCHES` — idempotent startup column additions (Sprint 3 added 3 plugin cols)

**Ground rules:**
- Settings via pydantic-settings with `HUBEX_` env prefix
- Capability enforcement is ON by default (`settings.caps_enforce = True`)
- Device tokens use HMAC-SHA256 keyed by JWT secret
- `.env` and `.env.docker` are gitignored; `.env.example` documents all vars
