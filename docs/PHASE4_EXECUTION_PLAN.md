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
- GET `/api/v1/executions/runs?definition_key=<string>&status=<string?>&cursor=<int?>&limit=<int?>`
- Capability: `executions.read` (deny-by-default)

Cursor semantics:
1) cursor is exclusive after_cursor: only rows with id > cursor are returned (null => 0).
2) Ordering is deterministic by id ASC; pagination uses limit+1 to avoid duplicates across pages.
3) next_cursor is the last returned id only when more rows exist; otherwise null.

Optional filter:
- If status is provided, filter runs by exact status (requested | completed | failed | canceled).

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

## Slice 4.5: Execution Definitions Read Surface (Read-only)

Route:
- GET `/api/v1/executions/definitions?cursor=<int?>&limit=<int?>`
- Capability: `executions.read` (deny-by-default)

Cursor semantics:
1) cursor is exclusive after_cursor: only rows with id > cursor are returned (null => 0).
2) Ordering is deterministic by id ASC; pagination uses limit+1 to avoid duplicates across pages.
3) next_cursor is the last returned id only when more rows exist; otherwise null.

## Slice 4.6: Execution Run Read-by-ID (Read-only)

Route:
- GET `/api/v1/executions/runs/{run_id}`
- Capability: `executions.read` (deny-by-default)

Semantics:
- Return the single run by id; 404 if missing.
- No mutation or side effects; response shape = ExecutionRunOut.

## Slice 4.7: Execution Definition Read-by-Key (Read-only)

Route:
- GET `/api/v1/executions/definitions/{definition_key}`
- Capability: `executions.read` (deny-by-default)

Semantics:
- Return the single definition by key; 404 if missing.
- No mutation or side effects; response shape = ExecutionDefinitionOut.

## Slice 4.8: Execution Run Claim/Lease (Write minimal)

Route:
- POST `/api/v1/executions/runs/{run_id}/claim`
- Capability: `executions.write` (deny-by-default)

Rules:
- Claimable only when status="requested".
- Available if claimed_by is NULL or lease_expires_at < now.
- Atomic claim uses single UPDATE ... WHERE ... RETURNING.
- Idempotent: same worker + valid lease returns existing (no lease extension).
- Conflict: different worker + valid lease returns 409.

Payload:
- worker_id (1..96)
- lease_seconds (1..3600, default 60)

## Slice 4.9: Execution Run Lease Extend/Heartbeat (Write minimal)

Route:
- POST `/api/v1/executions/runs/{run_id}/lease`
- Capability: `executions.write` (deny-by-default)

Rules:
- Only when status="requested" and claimed_by == worker_id.
- Only when lease_expires_at > now (NULL treated as expired).
- CAS update extends lease_expires_at.

Payload:
- worker_id (1..96)
- lease_seconds (1..3600, default 60)

## Slice 4.10: Execution Run Claim-Next/Dequeue (Write minimal)

Route:
- POST `/api/v1/executions/runs/claim-next`
- Capability: `executions.write` (deny-by-default)

Rules:
- Eligible runs: status="requested".
- Available if claimed_by is NULL or lease_expires_at is NULL or lease_expires_at < now.
- Deterministic selection by lowest id for the definition.
- Uses CAS claim rules; conflict retries up to max_attempts.
- If no available run: 404 "no run available".

Payload:
- definition_key (1..96)
- worker_id (1..96)
- lease_seconds (1..3600, default 60)

## Slice 4.11: Finalize Ownership Guard (Write minimal hardening)

Route:
- POST `/api/v1/executions/runs/{run_id}/finalize`

Rules:
- Finalize allowed when unclaimed or lease expired/NULL.
- If lease_expires_at > now, worker_id must be provided and match claimed_by.
