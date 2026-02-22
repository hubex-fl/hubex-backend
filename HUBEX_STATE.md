HUBEX ? Single Source of Truth

ARCHIVED ? superseded by HUBEX_STATE_v2.md

WICHTIG ? GOVERNANCE-HINWEIS

Diese Datei ist die verbindliche Referenz für Architektur, Contracts, Roadmap und Entscheidungen.

 nderungsregel:

Jede fachliche oder technische nderung an HUBEX MUSS hier eingepflegt werden.

Jede Chat-Ausgabe, die bestehende Punkte verändert oder ergänzt, MUSS explizit sagen:

welcher Abschnitt betroffen ist

was konkret zu ändern ist (Add/Modify/Deprecate)

nderungen ohne Update dieser Datei gelten als nicht beschlossen.

0. Meta

Projekt: HUBEX

Ziel: High-End, High-Security, deterministische Control Plane für Devices, Entities & Automations

Betriebsmodus: Self-hosted first, SaaS-ready ohne Architekturbruch

Prinzipien:

Core-first

Determinismus vor Komfort

Capabilities statt impliziter Rollen

Append-only Events, kein Magic State

1. Core-Idee (1-Satz-Definition)

Ein Device kann sich pairen, erhält eine deterministische Effective-Konfiguration (Snapshot), applied diese idempotent, ack’t per Revision zurück – und das Backend bleibt stabil, nachvollziehbar und skalierbar.

2. Public Contract Governance

2.1 Contract-Familien

pairing.v1

vars.v3

ack.v1

events.v1

audit.v1

mic.v1 (Module Integration Contract)

2.2 SemVer-Regeln

MAJOR (breaking)

Feld entfernt/umbenannt

Typ geändert

Semantik geändert

Pflichtfeld neu

MINOR (compatible)

optionale Felder

neue Endpoints

neue Enum-Werte (nur mit Safe-Default)

PATCH

Bugfixes

Performance

Logging

Regel: Public Contracts sind append-only innerhalb einer Major-Version.

3. Core-Freeze Definition

Der Core gilt als freeze-fähig, wenn:

Pairing  Snapshot  Apply  ACK deterministisch läuft

vars.v2 & vars.v3 Smokes grün (Prod-Profile, ohne Devtools)

effective_rev monoton & typfest

Keine DB-Leaks, kein WS-Pool-Exhaustion

Alle Public Contracts versioniert & dokumentiert

Phase-1 COMPLETE / FEATURE-FROZEN (2025-12-24):
Phase-1.5 is consolidation only: no new APIs, no new contracts, no semantics changes.

4. Phase-0 / Phase-1 Trennung

Phase 0 — Core-Freeze

Beinhaltet:

Pairing / Ownership

Variable Definitions

Effective Resolution

Snapshot + ACK

Simulator / Smokes

Device-first Pairing (canonical)

- POST /api/v1/devices/pairing/hello
- POST /api/v1/devices/pairing/start
- POST /api/v1/devices/pairing/claim
- POST /api/v1/devices/pairing/confirm
- GET /api/v1/devices/pairing/status
- Legacy aliases: /api/v1/pairing/* (same behavior/caps)

Invariants:
- pairing_active => pairing_code != null AND expires_at != null
- !pairing_active => pairing_code == null
- active session => repeated hello returns same pairing_code

SSOT UPDATE
Abschnitt: 4. Phase-0 / Phase-1 Trennung (Pairing / Ownership)
Art: Modify
Breaking: No
Begründung:
- Device-first pairing makes /devices/pairing the canonical path; /pairing remains legacy alias.
nderung:
- Add /api/v1/devices/pairing/hello and canonicalize pairing routes under /devices/pairing.
- Document legacy alias behavior for /api/v1/pairing/*.

Pairing Status (read-only)

GET /api/v1/pairing/status

GET /api/v1/devices/pairing/status (legacy alias)

Capability: pairing.status

Semantik:
- 404 wenn pairing_code nicht existiert
- 410 wenn pairing_code abgelaufen
- liefert claimed + ttl_seconds

Phase 1 — Core Enablement (Pflicht, kein Modul)

Diese Fähigkeiten sind Teil des Core, niemals Module:

Capabilities Registry (deny-by-default)

RBAC minimal + Token-Revoke

Entities v1 + Bindings

Events v1 (Cursor + Ack)

Audit v1 (append-only)

Secrets v1 + Config v1

Quotas / Rate-Limits

5. Capability-Modell (verbindlich)

5.1 Naming

<domain>.<resource>.<action>

Domains:

core

vars

entities

events

audit

secrets

config

mic

module.<module_key>

Enforcement-Regel (hart, deny-by-default):
- Jede API-Route ist capability-gated.
- Wenn für eine Route keine Capability definiert ist  403 (deny).
- Die Capability-Prüfung passiert vor dem Handler (kein “best effort”, kein UI-hide).

Public Routes (auth-free whitelist, klein & statisch):
- Es gibt eine explizite Whitelist von auth-freien Routen (z. B. health, version, pairing.hello).
- Whitelist ist klein, statisch, dokumentiert.
- Alles auerhalb der Whitelist bleibt capability-gated.
- "public" bedeutet auth-free, nicht capability-free (d. h. whitelisted routes sind die einzige Ausnahme; keine impliziten Ausnahmen).

SubjectCapabilities (Dokumentations-Tabelle, minimal):
- UI: vars.read, entities.read, events.read, audit.read
- Device: vars.read, vars.ack, telemetry.emit
- Admin: cap.admin, secrets.write, config.write, audit.read, audit.write, mic.admin

5.2 Beispiele

vars.read

vars.ack

events.emit

entities.resolve

effects.invoke:device:apply_vars

Verboten:

effects.invoke:*

6. Variable System (vars.v3)

6.1 Key-Namespace-Regeln

lowercase ASCII

max 96 Zeichen

mindestens 2 Segmente

keine IDs im Key

Reservierte Präfixe:

core.*

device.*

user.*

module.<module_key>.*

6.2 State-Modell

desired

effective (read-only, deterministisch)

reported (ACK/Telemetry)

Runtime-Zustände:

PENDING

ACKED_OK

ACKED_NOOP

ACKED_RETRYABLE

ACKED_FAILED

STALE

OFFLINE

7. Events v1 (MVP, final)

Streams

tenant.system

entities.{entity_id}

executions.{execution_id}

Regeln

append-only

cursor monotonic

at-least-once

idempotent subscribers

Emit (device)

POST /api/v1/events/emit

Capability: events.emit

8. Entities v1 (minimal)

Entity

entity_id

type

name

tags

health.last_seen_at

health.status

Device Binding

1 Entity  n Devices

enabled + lowest priority wins

8.1 Executions v1 (read-only)

Reference flow: docs/EXECUTION_WORKER.md

GET /api/v1/executions/runsdefinition_key=<string>&status=<string>&cursor=<int>&limit=<int>

Capability: executions.read (deny-by-default)

Cursor semantics:
1) cursor is exclusive after_cursor: only rows with id > cursor are returned (null => 0).
2) Ordering is deterministic by id ASC; pagination uses limit+1 to avoid duplicates across pages.
3) next_cursor is the last returned id only when more rows exist; otherwise null.

Status filter semantics:
- If status is provided, filter runs by exact status.
- Allowed statuses: requested | completed | failed | canceled

8.2 Executions v1 (write minimal)

POST /api/v1/executions/definitions
Capability: executions.write (deny-by-default)

POST /api/v1/executions/runs
Capability: executions.write (deny-by-default)

State note: runs are created with status="requested"; no completion/failure APIs in 4.3.

8.3 Executions v1 (finalize run)

POST /api/v1/executions/runs/{run_id}/finalize
Capability: executions.write (deny-by-default)

Allowed statuses: completed | failed | canceled

Transition rules:
- Only requested -> final
- If already final:
  - if request exactly matches stored (status + output_json + error_json) => 200 return existing
  - else => 409 conflict

Payload rules (hard):
- completed: requires output_json, forbids error_json
- failed: requires error_json, forbids output_json
- canceled: forbids both output_json and error_json

Ownership guard:
- If claimed_by is NULL, lease_expires_at is NULL, or lease_expires_at <= now, finalize is allowed.
- If lease_expires_at > now, finalize requires worker_id and claimed_by must match.

8.4 Executions v1 (definitions read-only)

GET /api/v1/executions/definitionscursor=<int>&limit=<int>
Capability: executions.read (deny-by-default)

Cursor semantics:
1) cursor is exclusive after_cursor: only rows with id > cursor are returned (null => 0).
2) Ordering is deterministic by id ASC; pagination uses limit+1 to avoid duplicates across pages.
3) next_cursor is the last returned id only when more rows exist; otherwise null.

8.5 Executions v1 (run read-by-id)

GET /api/v1/executions/runs/{run_id}
Capability: executions.read (deny-by-default)

Semantics: returns the single run by id; 404 if missing; no mutation; response shape = ExecutionRunOut.

8.6 Executions v1 (definition read-by-key)

GET /api/v1/executions/definitions/{definition_key}
Capability: executions.read (deny-by-default)

Semantics: returns the single definition by key; 404 if missing; no mutation; response shape = ExecutionDefinitionOut.

8.7 Executions v1 (run claim/lease)

POST /api/v1/executions/runs/{run_id}/claim
Capability: executions.write (deny-by-default)

Claim semantics:
- Only claimable when run.status == "requested".
- A run is available if claimed_by is NULL or lease_expires_at < now.
- Atomic claim uses a single UPDATE ... WHERE ... RETURNING.

Idempotency:
- If already claimed by the same worker_id and lease is still valid, return existing (200, no lease extension).
- If claimed by a different worker and lease is still valid, return 409 conflict.

Payload:
- worker_id (string 1..96)
- lease_seconds (int 1..3600, default 60)

Response: ExecutionRunOut (includes claimed_by, claimed_at, lease_expires_at).

8.8 Executions v1 (run lease extend/heartbeat)

POST /api/v1/executions/runs/{run_id}/lease
Capability: executions.write (deny-by-default)

Rules:
- Only when status == "requested".
- Only when claimed_by == worker_id.
- Only when lease_expires_at > now.
- If lease_expires_at is NULL, treat as expired (409).

Payload:
- worker_id (string 1..96)
- lease_seconds (int 1..3600, default 60)

Response: ExecutionRunOut (lease_expires_at extended).

8.9 Executions v1 (run claim-next/dequeue)

POST /api/v1/executions/runs/claim-next
Capability: executions.write (deny-by-default)

Rules:
- Only runs with status="requested" are eligible.
- Available if claimed_by is NULL or lease_expires_at is NULL or lease_expires_at < now.
- If definition_key is provided: deterministic selection is lowest id among available for that definition.
- If definition_key is omitted: worker must have subscriptions; selection is deterministic by (definition_id ASC, id ASC).
- If worker has subscriptions and requests a different definition_key: 409 "worker not subscribed".
- Claim uses existing CAS claim rules (atomic UPDATE ... WHERE ... RETURNING).
- If no available run exists: 404 "no run available".

Payload:
- definition_key (string 1..96, optional when worker has subscriptions)
- worker_id (string 1..96)
- lease_seconds (int 1..3600, default 60)

Implementation note: index on (definition_id, status, id) supports claim-next scans.

8.10 Executions v1 (run release/unclaim)

POST /api/v1/executions/runs/{run_id}/release
Capability: executions.write (deny-by-default)

Rules:
- Only relevant when status == "requested".
- If claimed_by is NULL, return 200 (idempotent).
- If claimed_by != worker_id, return 409.
- If claimed_by == worker_id, clear claimed_by/claimed_at/lease_expires_at and return 200.

Payload:
- worker_id (string 1..96)

9. MIC v1 (Module Integration Contract)

Worker Registry (minimal)

POST /api/v1/executions/workers/heartbeat
Capability: executions.write (deny-by-default)

GET /api/v1/executions/workers
Capability: executions.read (deny-by-default)

Filter:
- Supports active_within_seconds=<int> (1..86400) for last_seen_at cutoff.

Worker Subscriptions (minimal)

POST /api/v1/executions/workers/{worker_id}/definitions
Capability: executions.write (deny-by-default)

GET /api/v1/executions/workers/{worker_id}/definitions
Capability: executions.read (deny-by-default)

GET /api/v1/executions/definitions/{definition_key}/workers
Capability: executions.read (deny-by-default)

Filter:
- Supports active_within_seconds=<int> (1..86400) for last_seen_at cutoff.

Prinzipien

Core ist Single Source of Truth

Module sind strikt capability-gated

Kein Core-Bypass

Lifecycle

install  configure  enable  disable  revoke  uninstall

Module Kit (repo convention)

- modules/_template (scaffold)
- modules/rules_min (example module)
- docs/MODULE_KIT.md (usage + rules)
- capability prefix recommendation: module.<module_key>.*

Module Registry + Lifecycle (minimal)

GET /api/v1/modules
Capability: modules.read (deny-by-default)

GET /api/v1/modules/{key}
Capability: modules.read (deny-by-default)

POST /api/v1/modules/{key}/enable
Capability: modules.write (deny-by-default)

POST /api/v1/modules/{key}/disable
Capability: modules.write (deny-by-default)

Default:
- enabled=false until explicitly enabled.

Module Enabled Gate (runtime)

Rule:
- Requests with module identity (JWT sub="module:<module_key>") are allowed only when module_registry.enabled=true.
- If disabled or missing: 403 with code MODULE_DISABLED (or MODULE_NOT_FOUND for missing).

SSOT UPDATE
Abschnitt: 9 MIC v1 (Module Integration Contract)
Art: Add
Breaking: No
Begründung:
- Standardized module scaffold reduces delivery time while staying MIC-compliant and capability-gated.
- Provide a minimal module lifecycle registry + enable/disable surface for MIC v1.
- Ensure disabled modules are hard-blocked from module-identity actions.
nderung:
- Add Module Kit repo convention: modules/_template, docs/MODULE_KIT.md
- Define recommended capability prefix for example module (module.rules_min.*) as examples only.
- Add /api/v1/modules (list/read) and /api/v1/modules/{key} (read) gated by modules.read.
- Add /api/v1/modules/{key}/enable and /api/v1/modules/{key}/disable gated by modules.write.
- Default enabled=false for newly discovered modules.
- Add module enabled gate for module identity (JWT sub="module:<module_key>") with MODULE_DISABLED on disabled modules.

Gate

demo_min Modul läuft auf Core N & N+1

10. Modul-Phasen-Roadmap (final)

Phase 2: UI

Phase 3: Providers / Signals (Mobile = Provider)

Phase 4: Rules / Engine

Phase 5: Execution Worker v1 as deployable service artifact

SSOT UPDATE
Abschnitt: Phase 5 (Execution Worker v1)
Art: Add
Breaking: No
Begründung:
- Canonical runbook + demo helper for local Phase-5 workflows.
nderung:
- Add docs/PHASE5_RUNBOOK.md
- Add scripts/demo-phase5.ps1 and scripts/smoke-ui.ps1

Phase 6: Templates / Testbench

Phase 7: Admin / Backup / Plugins

Regel: Module starten erst nach Phase-1 Gate.

11. Security Posture

Jetzt:

Token-basiert

Capability Enforcement

Keine impliziten Trusts

Später (arch-ready):

HTTPS

mTLS

Cert Lifecycle

Wichtig: Kein heutiger Contract darf Klartext voraussetzen.

Token Revoke (Phase-1 Enablement):
- Token-Revoke wird serverseitig unterstützt via jti denylist.
- Gate: Revoke wirkt sofort (global wirksam), ohne Neustart.

12. Änderungsprotokoll

JEDER CHANGE MUSS HIER EINGETRAGEN WERDEN

Datum

Abschnitt

Art

Kurzbeschreibung

YYYY-MM-DD



Initiale Erstellung

| 2025-12-24 | 5, 11 | Add | Capabilities Enforcement präzisiert (deny-by-default + public whitelist); Token revoke (jti denylist) ergänzt | compatible |
| 2026-02-12 | 8.1, 8.2 | Add | Executions v1 (read-only + write minimal) mit Cursor-Semantik und executions.read/write | compatible |
| 2026-02-13 | 8.3 | Add | Executions v1 finalize run (write) mit deterministischen Regeln und executions.write | compatible |
| 2026-02-14 | 4, 7, 9 | Add | Pairing status (read-only), Events emit (device), Module Kit scaffold/docs | compatible |
| 2026-02-14 | Phase 5 | Add | Phase-5 runbook + demo helpers (worker/UI dev flow) | compatible |
| 2026-02-16 | 4 | Modify | Device-first pairing: canonical /devices/pairing with /pairing legacy alias | compatible |
| 2026-02-13 | 8.4 | Add | Executions v1 definitions read-only mit Cursor-Semantik und executions.read | compatible |
| 2026-02-13 | 8.5 | Add | Executions v1 run read-by-id mit executions.read | compatible |
| 2026-02-13 | 8.6 | Add | Executions v1 definition read-by-key mit executions.read | compatible |
| 2026-02-13 | 8.7 | Add | Executions v1 claim/lease (claim/lease fields + CAS) | compatible |
| 2026-02-13 | 8.8 | Add | Executions v1 lease extend/heartbeat | compatible |
| 2026-02-13 | 8.9 | Add | Executions v1 claim-next (subscription-aware optional definition_key) | compatible |
| 2026-02-13 | 8.10 | Add | Executions v1 release/unclaim | compatible |
| 2026-02-13 | 9 | Add | MIC v1 worker registry + subscriptions + active worker filter | compatible |
| 2026-02-16 | 9 | Add | MIC v1 module registry + lifecycle (modules.read/write) | compatible |
| 2026-02-16 | 9 | Add | MIC v1 module enabled gate (MODULE_DISABLED) + audit on enable/disable | compatible |
| 2026-02-13 | Phase 5 / 5.1 | Add | Execution Worker v1 service (deployable artifact MVP) | compatible |
| 2026-02-13 | Phase 5 / 5.2 | Add | Deployable artifact (container/runtime + env contract) | compatible |
| 2026-02-13 | Phase 5 / 5.3 | Add | Ops hardening (shutdown/exitcodes/ci modes) | compatible |
| 2026-02-13 | Phase 5 / 5.4 | Add | Docs/demo alignment | compatible |

13. Entscheidungsregel (final)

Wenn etwas unklar ist:

Core klein halten

Determinismus vor Komfort

Capability statt impliziter Annahme

Lieber ein klares Nein als ein weiches Vielleicht

Ende der Datei
