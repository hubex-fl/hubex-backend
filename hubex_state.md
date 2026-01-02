HUBEX — Single Source of Truth

WICHTIG – GOVERNANCE-HINWEIS

Diese Datei ist die verbindliche Referenz für Architektur, Contracts, Roadmap und Entscheidungen.

🔁 Änderungsregel:

Jede fachliche oder technische Änderung an HUBEX MUSS hier eingepflegt werden.

Jede Chat-Ausgabe, die bestehende Punkte verändert oder ergänzt, MUSS explizit sagen:

welcher Abschnitt betroffen ist

was konkret zu ändern ist (Add/Modify/Deprecate)

Änderungen ohne Update dieser Datei gelten als nicht beschlossen.

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

„Ein Device kann sich pairen, erhält eine deterministische Effective-Konfiguration (Snapshot), applied diese idempotent, ack’t per Revision zurück – und das Backend bleibt stabil, nachvollziehbar und skalierbar.“

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

Pairing → Snapshot → Apply → ACK deterministisch läuft

vars.v2 & vars.v3 Smokes grün (Prod-Profile, ohne Devtools)

effective_rev monoton & typfest

Keine DB-Leaks, kein WS-Pool-Exhaustion

Alle Public Contracts versioniert & dokumentiert

4. Phase-0 / Phase-1 Trennung

Phase 0 – Core-Freeze

Beinhaltet:

Pairing / Ownership

Variable Definitions

Effective Resolution

Snapshot + ACK

Simulator / Smokes

Phase 1 – Core Enablement (Pflicht, kein Modul)

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
- Wenn für eine Route keine Capability definiert ist → 403 (deny).
- Die Capability-Prüfung passiert vor dem Handler (kein “best effort”, kein UI-hide).

Public Routes (auth-free whitelist, klein & statisch):
- Es gibt eine explizite Whitelist von auth-freien Routen (z. B. health, version, pairing.hello).
- Whitelist ist klein, statisch, dokumentiert.
- Alles außerhalb der Whitelist bleibt capability-gated.
- “public” bedeutet auth-free, nicht capability-free (d. h. whitelisted routes sind die einzige Ausnahme; keine impliziten Ausnahmen).

Subject→Capabilities (Dokumentations-Tabelle, minimal):
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

8. Entities v1 (minimal)

Entity

entity_id

type

name

tags

health.last_seen_at

health.status

Device Binding

1 Entity → n Devices

enabled + lowest priority wins

9. MIC v1 (Module Integration Contract)

Prinzipien

Core ist Single Source of Truth

Module sind strikt capability-gated

Kein Core-Bypass

Lifecycle

install → configure → enable → disable → revoke → uninstall

Gate

demo_min Modul läuft auf Core N & N+1

10. Modul-Phasen-Roadmap (final)

Phase 2: UI

Phase 3: Providers / Signals (Mobile = Provider)

Phase 4: Rules / Engine

Phase 5: Observability / Support

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

—

—

Initiale Erstellung

| 2025-12-24 | 5, 11 | Add | Capabilities Enforcement präzisiert (deny-by-default + public whitelist); Token revoke (jti denylist) ergänzt | compatible |

13. Entscheidungsregel (final)

Wenn etwas unklar ist:

Core klein halten

Determinismus vor Komfort

Capability statt impliziter Annahme

Lieber ein klares Nein als ein weiches Vielleicht

Ende der Datei
