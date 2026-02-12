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

## Slice 4.2: Execution Read Surface (Read-only)

Read surface:
- GET `/api/v1/executions/runs?definition_key=<string>&cursor=<int?>&limit=<int?>`
- Capability: `executions.read` (deny-by-default)

Cursor semantics:
1) cursor is exclusive after_cursor: only rows with id > cursor are returned (null => 0).
2) Ordering is deterministic by id ASC; pagination uses limit+1 to avoid duplicates across pages.
3) next_cursor is the last returned id only when more rows exist; otherwise null.

## Slice 4.4: Execution Run Finalization (Write minimal)

Route:
- POST `/api/v1/executions/runs/{run_id}/finalize`
- Capability: `executions.write` (deny-by-default)

Rules:
- Allowed statuses: completed | failed | canceled
- Only requested -> final
- If already final:
  - exact match (status + output_json + error_json) => 200 return existing
  - otherwise => 409 conflict

Payload rules:
- completed: requires output_json, forbids error_json
- failed: requires error_json, forbids output_json
- canceled: forbids both output_json and error_json
