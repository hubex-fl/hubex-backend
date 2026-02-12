# Phase 3 Execution Plan

## Assumptions Confirmed
- Readiness baseline exists in `docs/PHASE3_READINESS_REPORT.md`.
- Phase-1 and full gates are expected to stay green after each slice.
- Phase 3 starts with storage-first increments, no API breakage.

## Slice Checklist
- [x] 3.1 Provider and instance storage (models + migration + capability placeholders).
  Deliverables:
  - SQLAlchemy models `ProviderType` and `ProviderInstance`.
  - Alembic migration creating `provider_types` and `provider_instances`.
  - Capability registry placeholders for providers/signals.
  - Regression tests for metadata and capability registration.
  Acceptance criteria:
  - `python -m compileall app scripts tests` passes.
  - `pytest` passes.
  - `scripts/run-phase1-gates.ps1` passes.
- [x] 3.2 Signal ingestion persistence.
  Deliverables:
  - Signal storage schema with idempotency key and cursor fields.
  - Insert-only write path in core layer.
  - Tests for dedupe and ordering guarantees.
  Acceptance criteria:
  - Duplicate idempotency key does not create multiple rows. ✅
  - Cursor order is monotonic in tests. ✅
  - Existing event/effect endpoints remain unchanged. ✅
- [x] 3.3 Signal read/subscription surface.
  Deliverables:
  - Cursor-based read service and response schema wiring.
  - Capability-gated read mapping (`signals.read`).
  - Docs update for stream/cursor usage.
  Acceptance criteria:
  - Deterministic pagination semantics (`next_cursor` contract). ✅
  - Backward compatibility for existing consumers. ✅
  - Gates stay green without test flakiness. ✅

## Definition Of Done (Phase 3)
- All slice acceptance criteria complete and documented.
- Single Alembic head after each migration.
- No gate weakening and no bypasses introduced.
- Changelog updated for each merged slice.
