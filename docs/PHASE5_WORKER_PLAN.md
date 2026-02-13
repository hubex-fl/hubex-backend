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

## Slice 5.3: Ops Hardening
- Shutdown/exitcode semantics.
- run_once/MAX_RUNS deterministic modes.
- Clean task cancellation (no long waits on stop).

## Slice 5.4: Docs/Demo Alignment
- Canonical docs aligned with worker demo script.
