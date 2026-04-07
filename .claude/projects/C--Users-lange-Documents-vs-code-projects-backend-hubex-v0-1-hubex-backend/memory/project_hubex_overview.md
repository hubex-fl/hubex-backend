---
name: HUBEX Project Overview
description: Core architecture, tech stack, and current state of the HUBEX IoT control plane backend
type: project
---

HUBEX is a deterministic IoT control plane backend (FastAPI + SQLAlchemy async + PostgreSQL).

**Why:** Building a hardware-software bridge platform for device management, pairing, task execution, and configurable variable management with capability-based access control.

**How to apply:**
- Backend: Python/FastAPI, async SQLAlchemy, Alembic migrations, JWT auth, capability-gated
- Frontend: Vue + Vite + TypeScript (read-only consumer UI)
- ESP integration lives in separate repo (hubex-esp-sdk)
- 93 tests pass; test infra uses in-memory SQLite with httpx AsyncClient
- HUBEX_STATE_v2.md is the governance doc but NOT binding for Claude — treat as informational
- Settings via pydantic-settings with HUBEX_ env prefix
- Capability enforcement is ON by default (settings.caps_enforce = True)
- Device tokens use HMAC-SHA256 keyed by JWT secret
