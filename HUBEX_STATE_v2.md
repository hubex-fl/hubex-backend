# HUBEX — Single Source of Truth

> **GOVERNANCE (bindend)**
>
> Diese Datei ist die **verbindliche Referenz** für Architektur, Contracts, Roadmap und Entscheidungen.
>
> **nderungsregel:**
> - Jede fachliche/technische nderung an HUBEX **MUSS** hier eingepflegt werden.
> - Jede Chat-Ausgabe, die bestehende Punkte verändert oder ergänzt, **MUSS** explizit sagen:
>   - **welcher Abschnitt** betroffen ist
>   - **was konkret zu ändern ist** (Add/Modify/Deprecate)
> - nderungen ohne Update dieser Datei gelten als **nicht beschlossen**.

---

## 0. Meta

- Supersedes: HUBEX_STATE.md

- Projekt: **HUBEX**
- Ziel: High-End, High-Security, deterministische Control Plane für Devices/Entities/Automations
- Betriebsmodus: **Self-hosted first**, SaaS-ready ohne Architekturbruch
- Leitprinzipien:
  - Core-first (SSOT im Core)
  - Determinismus vor Komfort
  - Capabilities statt impliziter Rollen
  - Append-only Events/Audit, kein Magic State
  - Module sind **Consumer**, keine Core-Bypässe

---

## 1. Core-Idee (1 Satz)

> “Ein Device kann sich pairen, erhält deterministische Effective-Konfiguration (Snapshot), applied idempotent, ack’t per Revision zurück — Backend bleibt stabil, nachvollziehbar, erweiterbar.”

---

## 2. Public Contract Governance

### 2.1 Contract-Familien (public & versioniert)

- pairing.v1
- vars.v3
- ack.v1
- events.v1
- audit.v1
- mic.v1 (Module Integration Contract)

### 2.2 SemVer-Regeln (Public Contracts)

**MAJOR (breaking)**: Feld entfernt/umbenannt, Typ geändert, Semantik geändert, Pflichtfeld neu.  
**MINOR (compatible)**: optionale Felder, neue Endpoints, neue Enum-Werte nur mit Safe-Default.  
**PATCH**: Bugfix/Performance/Logging/Doku ohne Semantikänderung.

**Regel:** Public Felder sind append-only innerhalb einer Major-Version.

---

## 3. Scope-Grenzen: Core vs Module

### 3.1 Core ist verantwortlich für

- **SSOT-Datenmodelle** (Device/Entity/Vars/Signals/Executions/Trace/Audit)
- **Public Contracts** + Versionierung (Kap. 2)
- **Enforcement** (Capabilities deny-by-default, Ownership, Ordering, Idempotenz)
- **Deterministische Read-Models** (Effective/Snapshot/Cursor Reads)
- **Append-only** Streams/Logs (events/audit/effects/executions traces)
- **Recovery-Policies** (z.B. Token-Reissue) als produktkritische Invarianten

### 3.2 Core ist NICHT verantwortlich für

- UI/UX “Reparatur” von Backend-Fehlzuständen
- Automations-Logik als implizite Side-Effects im Core (Engine/Worker gehören als Services/Module)
- Vendor-spezifische Device-Details (ESP/Arduino Code) — nur Contracts im Core

### 3.3 Module sind verantwortlich für

- UI/UX “Reparatur” von Backend-Fehlzuständen
- Provider/Signals Sources (Time/Webhook/MQTT/…)
- Rules/Engine (deterministische Ausführung basierend auf Core-State)
- Observability/Support Views (read-only Auswertung)
- Templates/Testbench/Simulator
- Admin Console / Backup / Plugins / Registry / Mobile

**Regel:** Module dürfen nur über **MIC v1** und capability-gated handeln. Kein Bypass.

---

## 4. Capability-Modell (verbindlich)

### 4.1 Naming

`<domain>.<resource>.<action>`

Domains: core, vars, entities, events, audit, secrets, config, mic, modules, module.<module_key>

### 4.2 Beispiele

- vars.read
- vars.ack
- events.read / events.ack
- audit.read
- modules.read / modules.write
- devices.token.reissue

**Verboten:** `effects.invoke:*`

---

## 5. Roadmap 2.0 (Track-basiert, eindeutig)

> Ziel: Phase-/Begriffs-Verwirrung eliminieren. Wir steuern über **Tracks** mit klaren Gates.

### Track A — Core Platform (SSOT & Enforcement)

A1 Pairing device-first, canonical routes, invariants  
A2 Vars v3 snapshot/ack deterministisch  
A3 Capabilities enforced deny-by-default  
A4 Entities/Events/Audit/Secrets/Config Grundgerüst  
A5 MIC v1 minimal: module registry + lifecycle + module enabled gate + audit

### Track B — Runtime Services (deterministische Ausführung, als Services)

B1 Execution storage foundation  
B2 Execution worker v1 deployable (docker/env/run-once)  
B3 Worker ops hardening + runbook/demo  
B4 Engine v1 (Rules→Executions) als separater Service/Modul (später)

### Track C — Module Suite (funktional, capability-gated)

C1 UI Module (System Stage) — consumer-first  
C2 Providers/Signals Module — sources + health  
C3 Rules/Engine Module — artifacts + deterministic execution  
C4 Observability/Support Module — read-only ops  
C5 Templates/Experiments Module  
C6 Simulator/Testbench Module  
C7 Admin/Backup/Plugins/Registry/Mobile Modules

### Track D — Device Integration (parallel, contract-driven)

D1 Provisioning Portal (WLED-first, stable)  
D2 Pairing E2E on device  
D3 Recovery on device (token reissue consumption)  
D4 ESP SDK hardening (timeouts, storage, backoff)  
D5 Optional Arduino bridge protocol

### Track E — Productization (Ops/Release)

E1 Repro install/run (self-hosted)  
E2 Release gates + compatibility tests (N-1)  
E3 Support bundles + retention policy basics  
E4 Security rollout plan (HTTPS – optional mTLS) — arch-ready, gated

---

## 6. Vertical Demo v1 (Leitstern)

> **Ein** End-to-End Use-Case, der jederzeit “zeigt ob das System lebt”.

Webhook/Time Signal → Rule (min) → Execution Run → Worker claim/finalize → Device receives change (vars) → ACK → UI zeigt Trace.

**Gate:** Demo v1 läuft reproduzierbar auf fresh setup (ohne DB-Handarbeit).

Status: Delivered (code) (script + demo bridge + audit)

SSOT UPDATE
Abschnitt: 6. Vertical Demo v1
Art: Add
Breaking: No
Begruendung:
- Demo trace needs correlation across events and audit without new contracts.
Aenderung:
- events.v1 read items include optional trace_id for correlation.
- demo scripts: scripts/demo-vertical-v1.ps1 and app/demo/vertical_demo_v1.py (signal->execution bridge + audit).

---

## 7. Recovery Gate (produktkritisch)

### 7.1 Token-Loss Recovery (claimed device, token missing)

**Problem:** Device kann claimed sein, aber token ist weg (NVS erase/flash).  
**Policy:** Owner/Admin kann **device token reissue** auslösen (audited), alte Tokens invalidieren, Device übernimmt neuen Token.  
**Gate:** “claimed + token missing” ist recoverbar (Backend + Device).

SSOT UPDATE
Abschnitt: 7. Recovery Gate
Art: Add
Breaking: No
Begruendung:
- Provide audited token reissue for claimed devices (owner/admin only).
Aenderung:
- Add POST /api/v1/devices/{device_id}/token/reissue (reason required) gated by devices.token.reissue.
- Old device tokens are invalidated; audit entry with actor, device_uid, reason, revoked_count.


---

## 8. nderungsprotokoll

| Datum      | Abschnitt | Art | Kurzbeschreibung |
| ---------- | --------- | --- | ---------------- |
| 2026-02-22 | 6 | Add | Vertical Demo v1 script + trace_id support |
| 2026-02-22 | 7.1 | Add | Recovery Gate: device token reissue (devices.token.reissue, audited) |
| YYYY-MM-DD | —         | —   | Initiale Erstellung |




