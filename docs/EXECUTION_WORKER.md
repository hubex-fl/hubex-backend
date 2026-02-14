# Execution Worker Reference Flow

This document describes a minimal, deterministic worker loop for Executions v1 using the claim/lease APIs.
The run status remains `requested`; claim fields represent “in progress” (no separate running status).

## Canonical Flow
0) Register/heartbeat worker:
   - `POST /api/v1/executions/workers/heartbeat` (recommended cadence: same as lease heartbeat)
1) Dequeue a run:
   - `POST /api/v1/executions/runs/claim-next` with `worker_id`, `lease_seconds`
   - Include `definition_key` explicitly, or omit it when using worker subscriptions.
2) Heartbeat while processing:
   - `POST /api/v1/executions/runs/{run_id}/lease` every `lease_seconds/2`
3) Finalize on success/fail/cancel:
   - `POST /api/v1/executions/runs/{run_id}/finalize`
   - If a lease is active, include `worker_id` to satisfy ownership guard
4) Release on abort/early exit:
   - `POST /api/v1/executions/runs/{run_id}/release` with `worker_id`

## Error Handling
- `claim-next`:
  - `404 "no run available"`: sleep and retry
  - `409 conflict`: retry (another worker raced)
- `lease`:
  - `409 conflict`: lease expired or ownership mismatch; stop processing
- `finalize`:
  - `409 conflict`: not owner or already finalized; treat as terminal

## Recommended Defaults
- `lease_seconds = 60`
- `heartbeat_every = 30` (half of lease)
Rationale: keeps leases fresh without excessive overhead.

## Demo Helper
For a deterministic local demo (seeds a run, executes once, and verifies heartbeat):
```
.\scripts\demo-phase5.ps1
```

## Minimal Curl Examples
Claim next:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/executions/runs/claim-next \
  -H "Authorization: Bearer $HUBEX_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"definition_key":"my-def","worker_id":"worker-1","lease_seconds":60}'
```

Worker heartbeat:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/executions/workers/heartbeat \
  -H "Authorization: Bearer $HUBEX_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"worker_id":"worker-1","meta_json":{"hostname":"worker-a"}}'
```

Heartbeat:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/executions/runs/123/lease \
  -H "Authorization: Bearer $HUBEX_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"worker_id":"worker-1","lease_seconds":60}'
```

Finalize (completed):
```bash
curl -X POST http://127.0.0.1:8000/api/v1/executions/runs/123/finalize \
  -H "Authorization: Bearer $HUBEX_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"completed","output_json":{"ok":true},"worker_id":"worker-1"}'
```

Release:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/executions/runs/123/release \
  -H "Authorization: Bearer $HUBEX_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"worker_id":"worker-1"}'
```
