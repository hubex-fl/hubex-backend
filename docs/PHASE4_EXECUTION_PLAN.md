# Phase 4 Execution Plan

## Constraints (Non-Negotiable)
- No streaming.
- No worker/queue/background processing.
- No UI work.
- Storage-first, deterministic foundation only.
- No new public APIs/routes/contracts in Slice 4.1.

## Slice 4.1: Execution Model Foundation (Storage-First)

Status set (Option A): `requested | completed | failed | canceled`.

Tables (implemented shape):
- `execution_definitions`
  - `id` (pk)
  - `key` (string, UNIQUE)
  - `name` (string)
  - `version` (string)
  - `enabled` (bool)
  - `created_at`, `updated_at` (tz-aware)
- `execution_runs`
  - `id` (pk, monotonic cursor)
  - `definition_id` (fk -> execution_definitions.id)
  - `idempotency_key` (string)
  - `requested_by` (nullable string)
  - `status` (string; allowed states above)
  - `input_json` (json)
  - `output_json` (nullable json)
  - `error_json` (nullable json)
  - `created_at`, `updated_at` (tz-aware)
  - Idempotency: `UNIQUE(definition_id, idempotency_key)`
  - Scan index: `(definition_id, id)`

Deterministic cursor read contract (internal):
- after_cursor semantics: only `id > cursor` (null => 0)
- ORDER BY `id ASC`
- limit+1 for `next_cursor`
- `next_cursor` only if more rows exist, else `null`
- limits clamped server-side: DEFAULT=50, MAX=200

Invariants (enforced in code, no DB triggers):
- `input_json` is write-once.
- `output_json` OR `error_json` can be set at most once (never both).
- Final states are immutable (completed/failed/canceled cannot transition).
