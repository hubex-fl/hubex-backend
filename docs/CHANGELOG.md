# CHANGELOG

## Unreleased
- Dev: fix dev-backend.ps1 to avoid PowerShell reserved $Host variable.
- Dev: make dev-backend.ps1 logs pipeline-friendly (Tee-Object support).
- Dev: improve dev-backend.ps1 port-in-use diagnostics (process name/path).
- Dev: dev-backend.ps1 startup check now polls for reload readiness.
- Dev: dev-backend.ps1 supports follow/stop/status actions and avoids extra windows.
- Dev: refactor dev-backend.ps1 to a single action flow (start/follow/stop/status).
- UI: devices list rows are clickable (route to /devices/:id).
- Dev: harden dev-backend.ps1 (0.0.0.0 default, pidfile guard, log redirection).
- Dev: include uvicorn[standard] so local WebSocket upgrades are supported.
- UI: register device detail route and link devices list to /devices/:id.
- UI: device detail recovery reissue button (devices.token.reissue) with reason + one-time token display.
- SSOT v2 hygiene: UTF-8/mojibake cleanup + normalize status markers; HUBEX_STATE.md archived banner.
- Vertical Demo v1: demo script + bridge + trace_id support for events.
- Recovery Gate v7.1: device token reissue (audited, owner/admin only).
- MIC v1: module enabled gating (MODULE_DISABLED) + audit on enable/disable.
- MIC v1: module registry + lifecycle endpoints (list/read/enable/disable) with modules.read/write.
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
