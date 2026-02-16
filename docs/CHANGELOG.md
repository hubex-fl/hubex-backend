# CHANGELOG

## Unreleased
- Fix legacy pairing status alias capability mapping + readonly catalog entries.
- Device-first pairing finalized: hello idempotent + single active session + invariants enforced (legacy alias retained).
- Device-first pairing: canonical /devices/pairing with legacy /pairing alias + hello idempotency.
- Frontend dev reachability: Vite dev host/target env alignment + UI smoke docs.
- Phase-5 slice 5.4: runbook + demo script alignment for worker/UI/dev.
- Module Kit scaffold + example module (MIC-compliant, no public contracts).
- Make gate runner deterministic across platforms.
- JWT now includes user caps claim to enable UI capability gating.
- Reduce soft capability enforcement log noise; clarify caps flow for UI.
- Docs/gates consolidation and changelog gate enforcement for Phase-1.5.
- Add phase1 tag guard workflow and release tagging guidance.
- Add Windows CI job for phase1 gates.
- Add app boot smoke to phase1 gate suite.
- Add DB connectivity smoke to phase1 gate suite.
- Phase-1.5 consolidation: gates + smokes hardened.
- Phase-2 UI baseline frozen (System Stage, Events, Effects, Observability, Audit, Executions, TraceHub, Correlation).
- Phase-3 kickoff slice 3.1: provider/instance storage models + migration + capability placeholders.
- Phase-3 slice 3.2: signal ingestion persistence with idempotency dedupe + monotonic cursor tests.
- Phase-3 slice 3.3: signal read surface (cursor-based pagination) + signals_v1 stream/id index.
- Phase-3 closeout: scope signals idempotency to stream (UNIQUE(stream, idempotency_key)).
- Phase-4 complete: executions v1 storage + read/write surfaces, claim/lease/claim-next/release, ownership guards, worker registry/subscriptions/filters, indexes, and tests.
- Phase-5 slice 5.1: execution worker v1 service (MVP).
- Phase-5 SSOT/plan alignment: deployable artifact + ops hardening + docs/demo alignment.
- Phase-5 slice 5.3: worker ops hardening (shutdown/exitcodes/run_once).
- Phase-5 slice 5.2: deployable artifact (container/runtime + env contract).

## 2026-01-03 (Phase-1 COMPLETE / FEATURE-FROZEN)
- Phase-1 marked complete; feature freeze enforced.
