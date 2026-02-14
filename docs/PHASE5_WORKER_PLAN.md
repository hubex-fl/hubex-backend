# Phase 5 Worker Plan (Execution Worker v1)

## Slice 5.1: Execution Worker v1 (MVP)
- Service module using Phase-4 APIs only.
- Claim-next + lease heartbeat + finalize + release on failure.
- Worker registry heartbeat.
- Deterministic run control via MAX_RUNS.

## Slice 5.2: Deployable Artifact
- Dockerfile/container guidance.
- Non-root runtime and entrypoint.
- Env contract documented.

### Env Contract
Required:
- HUBEX_TOKEN
- WORKER_ID

Optional:
- HUBEX_BASE_URL (default http://127.0.0.1:8000)
- LEASE_SECONDS (default 60)
- HEARTBEAT_EVERY (default 20, 1..LEASE_SECONDS)
- POLL_DELAY (default 2.0)
- DEFINITION_KEY (optional; omit to use subscriptions)
- MAX_RUNS (optional int)
- RUN_ONCE (if set, max_runs=1)

Exit codes:
- 0: normal completion
- 1: runtime error
- 2: misconfiguration
- 130: keyboard interrupt

Example:
- docker build -t hubex-worker-v1 -f Dockerfile.worker_v1 .
- docker run --rm \
    -e HUBEX_BASE_URL=http://host.docker.internal:8000 \
    -e HUBEX_TOKEN=... \
    -e WORKER_ID=worker-1 \
    -e RUN_ONCE=1 \
    hubex-worker-v1

## Slice 5.3: Ops Hardening
- Shutdown/exitcode semantics.
- run_once/MAX_RUNS deterministic modes.
- Clean task cancellation (no long waits on stop).

## Slice 5.4: Docs/Demo Alignment
- Canonical docs aligned with worker demo script.
- See `docs/PHASE5_RUNBOOK.md` and `scripts/demo-phase5.ps1`.
