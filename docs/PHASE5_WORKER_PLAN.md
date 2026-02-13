# Phase 5 Worker Plan

## Slice 5.1: Execution Worker v1 (MVP)
- Service module using Phase-4 APIs only.
- Claim-next + lease heartbeat + finalize + release on failure.
- Worker registry heartbeat.
- Deterministic run control via MAX_RUNS.

## Slice 5.2: Worker Observability (minimal)
- Structured log aggregation guidance.
- Metrics mapping for claim/lease/finalize outcomes.

## Slice 5.3: Deployment Packaging
- Container/Dockerfile guidance and env contract.
- Healthcheck and runbook.

## Slice 5.4: Ops Guardrails
- Basic backoff guidance (no retries as feature).
- Resource limits and shutdown behavior.
