# CHANGELOG

## Unreleased
- Make gate runner deterministic across platforms.
- JWT now includes user caps claim to enable UI capability gating.
- Reduce soft capability enforcement log noise; clarify caps flow for UI.
- Docs/gates consolidation and changelog gate enforcement for Phase-1.5.
- Add phase1 tag guard workflow and release tagging guidance.
- Add Windows CI job for phase1 gates.
- Phase-4 slice 4.17: worker definition subscriptions (executions.read/write).
- Phase-4 slice 4.18: active worker view filter for worker lists/bindings.
- Add app boot smoke to phase1 gate suite.
- Add DB connectivity smoke to phase1 gate suite.
- Phase-1.5 consolidation: gates + smokes hardened.
- Phase-2 UI baseline frozen (System Stage, Events, Effects, Observability, Audit, Executions, TraceHub, Correlation).
- Phase-3 kickoff slice 3.1: provider/instance storage models + migration + capability placeholders.
- Phase-3 slice 3.2: signal ingestion persistence with idempotency dedupe + monotonic cursor tests.
- Phase-3 slice 3.3: signal read surface (cursor-based pagination) + signals_v1 stream/id index.
- Phase-3 closeout: scope signals idempotency to stream (UNIQUE(stream, idempotency_key)).
- Phase-4 slice 4.1: execution storage foundation (definitions + runs, deterministic cursor reads).
- Phase-4 slice 4.2: execution read surface (cursor pagination + executions.read).
- Phase-4 slice 4.3: execution write surface (definitions + runs, executions.write).
- Phase-4 slice 4.4: execution run finalization surface (executions.write).
- Hotfix 4.4: finalize idempotency exact-match handles empty JSON objects.
- Phase-4 slice 4.5: execution definitions read surface (executions.read).
- Phase-4 slice 4.6: execution run read-by-id (executions.read).
- Phase-4 slice 4.7: execution definition read-by-key (executions.read).
- Hotfix: finalize is atomic (CAS) to prevent concurrent overwrite of final runs.
- Hotfix: execution definition/run creation is DB-idempotent (unique constraints + IntegrityError fallback).
- Chore: clean up execution idempotent create helpers (no behavior change).
- Tests: deterministic IntegrityError fallback for execution idempotency.
- Chore: executions runs list supports optional status filter (read-only).
- Phase-4 slice 4.8: execution run claim/lease (executions.write).
- Phase-4 slice 4.9: execution run lease extend/heartbeat (executions.write).
- Hotfix: treat NULL lease_expires_at as expired in claim availability.
- Phase-4 slice 4.10: execution run claim-next/dequeue (executions.write).
- Phase-4 slice 4.11: finalize requires claim/lease ownership (executions.write).
- Phase-4 slice 4.12: execution run release/unclaim (executions.write).
- Docs/Scripts: add worker reference flow for executions claim/lease/dequeue.
- Perf: add claim-next dequeue index (definition_id,status,id).
- Tests: add E2E worker flow test for claim-next/lease/finalize ownership.
- Phase-4 slice 4.16: execution worker registry heartbeat + list (MIC v1).

## 2026-01-03 (Phase-1 COMPLETE / FEATURE-FROZEN)
- Phase-1 marked complete; feature freeze enforced.
