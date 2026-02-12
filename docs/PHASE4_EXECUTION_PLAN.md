# Phase 4 Execution Plan

## Constraints (Non-Negotiable)
- No streaming.
- No worker/queue/background processing.
- No UI work.
- Deterministic execution model foundation only (storage-first).
- No breaking changes to existing APIs/contracts.

## Slice 4.1: Execution Model Foundation (Storage-First)

Objective: Add minimal persistence for execution definitions and execution runs, plus deterministic read semantics (internal), without introducing background processing.

Proposed tables (storage only):
- `execution_definitions`
  - `id` (pk)
  - `key` (string, unique)
  - `name` (string)
  - `version` (int or string)
  - `enabled` (bool)
  - `created_at`, `updated_at`
- `execution_runs`
  - `id` (pk, monotonic cursor)
  - `definition_id` (fk -> execution_definitions.id)
  - `requested_by` (nullable string, e.g. user_id/device_uid)
  - `status` (string; enum-ish)
  - `input_json` (json)
  - `output_json` (nullable json)
  - `idempotency_key` (string)
  - `created_at`, `updated_at`
  - Idempotency (recommended): `UNIQUE(definition_id, idempotency_key)` (scope to the definition).

Deterministic read contract (internal pattern):
- `read_execution_runs(definition_id, cursor, limit)`:
  - exclusive cursor: only `id > cursor`
  - deterministic ordering: `id ASC`
  - `next_cursor` only when more rows exist (limit+1 technique)
  - server-side clamp: default limit + max limit

Capability placeholders (no enforcement changes required in 4.1):
- `executions.read`
- `executions.write`

Acceptance criteria (docs / when implemented):
- Single Alembic head after migration.
- Deterministic pagination semantics (`exclusive after_cursor`, `id ASC`, `next_cursor` rules).
- Limit clamped server-side (default + max cap).
- Idempotency scoped deterministically (recommended unique scope above).
- Gates remain green (compileall/pytest/phase1/full).

