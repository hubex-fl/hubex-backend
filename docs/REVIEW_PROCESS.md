# HubEx — Großes Review Process

**Zweck:** Dokumentierter 6-Runden-Prozess für umfassende Reviews vor einem
Stability-Tag (z. B. `dev-stable-v1`, `beta-v1`, `release-v1`). Entwickelt
in Sprint 8 (2026-04-11) für den ersten Dev-Stable-Tag.

Dieses Dokument ist ein **Template**. Wenn das Review-System gut funktioniert,
wird es für zukünftige Stability-Reviews wiederverwendet — einfach eine neue
`REVIEW_<TAG>.md` Datei anlegen, diesem Ablauf folgen, am Ende taggen.

---

## Grundprinzipien

1. **Review in Runden, nicht in einem Rutsch** — Menschliche Aufmerksamkeit
   reicht nicht für 40+ Seiten am Stück. Runden haben natürliche Pausen.
2. **Agent + Human Reviewer teilen sich die Arbeit** — Der Agent macht die
   mechanischen Smoke-Checks (Runden 1, 2, 4). Der Mensch macht das
   Gefühls-/Flow-Review (Runde 3). Der Mensch entscheidet Prioritäten nach
   jeder Runde.
3. **Dokumentation läuft parallel** — Eine einzige `REVIEW_<TAG>.md` Datei
   wächst Runde für Runde. Am Ende ist sie die historische Quelle für den
   Tag-Zustand.
4. **Nichts wird in den ersten 4 Runden gefixt** — Erst sammeln, priorisieren,
   dann fixen. Sonst verliert man den Überblick und fixt das Falsche zuerst.
5. **Jede Runde hat einen klaren Pause-Punkt** — Nach dem Pause-Punkt darf
   der Mensch weggehen, was anderes tun, später zurückkommen. Die Review-Datei
   ist der rote Faden.

---

## Die 6 Runden im Detail

### Runde 1 — Automated Smoke Pass
**Wer:** Agent allein
**Dauer:** ~60-90 min
**Ziel:** Jede Route der App einmal anfassen, beobachten, dokumentieren.

**Checks pro Route:**
- Navigation → lädt die Seite?
- Console errors oder `[Vue warn]` Meldungen?
- Network 4xx / 5xx auf den fetches?
- `querySelectorAll('*')` → unresolved Components (Lesson aus Sprint 3.8-hotfix: Tags wie `<umodal>` die nicht importiert wurden)?
- Document scrollHeight vs viewport fit (giant blank areas?)
- Top-bar Titel korrekt lokalisiert (DE locale)?
- Alle sichtbaren Badges / Buttons / Labels sind i18n'd (keine raw English reste)
- Gibt es offensichtliche Layout-Breakage (überlappende Elemente, abgeschnittener Text)?

**Output:** `REVIEW_<TAG>.md` mit Status-Matrix-Tabelle über alle Routes:

```
| Route | Status | Notes | Findings → |
|-------|--------|-------|-------------|
| /     | ✅     | ...   | —           |
| /foo  | ⚠️     | ...   | R1-F01, R1-F02 |
| /bar  | ❌     | ...   | R1-F03      |
```

Plus detaillierte Findings-Einträge `R1-F01`, `R1-F02`, etc. mit:
- Severity (P0/P1/P2/P3)
- Route(s) affected
- What I saw (raw observation)
- Suggested fix (optional)
- Decision: `[pending user priorization]`

**KEINE Fixes in dieser Runde.** Nur dokumentieren. Commit am Ende: nur das Review-Doc.

**Pause-Punkt:** Agent committet + stoppt. Mensch liest die Matrix, entscheidet:
- Welche ⚠️/❌ Findings sind real vs false positives
- Welche sind P0/P1/P2/P3
- Welche sind "must-fix vor Tag" vs "kann nach Tag gefixt werden"

---

### Runde 2 — Visual / UX Pass
**Wer:** Agent allein
**Dauer:** ~90 min
**Ziel:** Visuelle Qualität an 3 Breakpoints × 2 Locales pro Route prüfen.

**Checks pro Route:**
- Screenshot bei `375×812` (Mobile), `768×1024` (Tablet), `1440×900` (Desktop)
- Beides in EN und DE (also 6 Shots pro Route)
- Per Screenshot: padding, overflow, alignment, emoji font-substitution, typography hierarchy, color consistency, focus-states

**Tool:** `preview_resize` oder `mcp__Claude_in_Chrome__resize_window` vor jedem Screenshot.

**Output:** Screenshots in `docs/review/<tag>/<route>/<locale>-<breakpoint>.jpg` + Ergänzungen im Review-Doc pro Route unter `## Visual Findings`.

**Pause-Punkt:** Mensch schaut sich die Screenshots an, ergänzt eigene Findings per Kommentar im Review-Doc oder direkt per Chat.

---

### Runde 3 — User Walkthrough (Mensch führt)
**Wer:** Mensch führt, Agent hört zu & dokumentiert
**Dauer:** ~45-60 min pro Persona, in separaten Sessions
**Ziel:** Das "Gefühl" der App testen entlang echter User-Journeys.

**Die 4 Personas:**
- **Neuer User** — frischer Login, noch nichts da. Wo blockiert's? Wo fehlt Kontext?
- **Operator** — täglicher Betrieb. Claim Device → Variablen ansehen → Alert erstellen → Automation bauen. Wo stolpert man?
- **Admin** — Settings, Users, Audit, Features, Capabilities. Ist alles sichtbar/steuerbar?
- **Viewer** — nur Read-Access. Zeigt die UI Edit-Buttons die Viewer nicht nutzen können? Gibt das verwirrte Fehler?

**Ablauf:** Mensch klickt sich durch, erzählt live was er sieht und was nervt. Agent hört zu und übernimmt die Beobachtungen wörtlich in `## Persona Findings` im Review-Doc. Keine Live-Fixes.

**Pause-Punkt:** Nach jeder Persona ein kurzer Status-Check. Mensch kann auch "Pause, ich mach morgen weiter" sagen.

---

### Runde 4 — Perf + A11y Quick-Pass
**Wer:** Agent allein
**Dauer:** ~45 min
**Ziel:** Performance + Accessibility auf den 5 Kern-Seiten spot-checken.

**Kern-Seiten (anpassen je nach App):** Dashboard, Devices, DeviceDetail, Alerts, Automations

**Checks:**
- **Performance Trace** via `preview_eval` mit Performance API (Paint timings, Layout shifts, Long tasks)
- **Keyboard-Navigation** — Tab-Reihenfolge sinnvoll? Kann man alle Actions per Tastatur erreichen?
- **Focus-Ring** sichtbar auf allen interactive elements?
- **ARIA-Labels** auf Icon-Buttons die nur ein SVG haben und sonst keinen Text?
- **Color-Contrast** spot-check auf Key-Texten (text-muted auf bg-base etc.)

**Output:** `## Perf & A11y` Sektion im Review-Doc.

**Pause-Punkt:** Agent committet. Mensch priorisiert die Perf/A11y Findings ebenfalls (P0/P1/P2/P3).

---

### Runde 5 — Fixing-Pass
**Wer:** Agent (mit Eingriffsmöglichkeit vom Menschen)
**Dauer:** Scope-abhängig — 2-8h, eventuell über mehrere Sessions
**Ziel:** Die priorisierten Findings tatsächlich fixen.

**Kategorien:**
- **MUST-FIX vor Tag** — P0/P1 Bugs, broken Flows, Security-Issues, unresolved Components, major i18n holes
- **NICE-TO-FIX** — P2 UX-Polish — reinpacken wenn schnell, sonst auf Backlog
- **DEFERRED** — P3, Design-Decisions, neue Features die aus dem Review aufgetaucht sind → Backlog für nächste Sprints

**Ablauf:**
1. Agent schlägt eine Fix-Reihenfolge vor (meist: P0 → P1 → P2 nach Flow-Reihenfolge)
2. Mensch bestätigt oder adjustiert
3. Agent fixt einzeln, commit pro Finding oder gebündelt nach Thema
4. Mensch sieht jeden Commit, kann "stop" sagen

**Output:** Neue commits mit `fix: Sprint X review R<runde>-F<nr>: <was>` Muster. Review-Doc wird live aktualisiert — gefixte Findings kriegen `✅ FIXED in <commit-sha>`.

**Pause-Punkt:** Nach jedem Commit oder nach Themen-Block. Mensch kann abbrechen wenn genug.

---

### Runde 6 — Release
**Wer:** Agent mit Mensch-Approval
**Dauer:** ~15 min
**Ziel:** Den Tag setzen.

**Ablauf:**
1. Final smoke-test der gefixten Routes (quick pass über die must-fixes)
2. `CHANGELOG.md` Eintrag für den neuen Tag
3. `git tag <tag>` + push
4. Kurzer "Release Summary" in `ROADMAP.md` unter "Tags & Milestones"
5. Review-Doc wird abgeschlossen mit `## Release Summary` — Zusammenfassung aller Findings, was gefixt wurde, was in den Backlog ging

**Pause-Punkt:** Mensch gibt finalen Approval vor dem Tag-Push. Nach dem Tag: Sprint-Track geht weiter (z. B. Sprint 8.5 Maturity Badges, dann neue Features).

---

## Format der `REVIEW_<TAG>.md` Datei

```markdown
# Review: <TAG-Name> (<Datum>)

> Sprint X review per docs/REVIEW_PROCESS.md. Ziel: <Tag-Name>

## Quick-Status
- Start: <Datum>
- Current Round: <1-6>
- Routes reviewed: X / Y
- Findings open: N (Px×N Pz×N)
- Findings fixed: M
- Tag target date: <optional>

## Route Matrix (Runde 1)
<Tabelle aller Routes mit Status>

## Detailed Findings
### R1-F01: <Kurztitel>
**Severity:** P0 / P1 / P2 / P3
**Round:** 1-smoke / 2-visual / 3-persona / 4-perf-a11y
**Routes:** /foo, /bar
**What I saw:**
  (detail)
**Suggested fix:**
  (detail)
**Decision:** [pending] / [must-fix] / [nice-to-fix] / [defer]
**Status:** open / ✅ FIXED in <sha>

### R2-F15: ...
<...>

## Visual Findings (Runde 2)
<summary je Route>

## Persona Findings (Runde 3)
### New User walkthrough
- ...

### Operator walkthrough
- ...

## Perf & A11y (Runde 4)
<findings>

## Fix List
<working checklist>

## Release Summary (Runde 6)
<am Ende>
```

---

## Wann den Prozess anwenden?

- **Vor jedem Stability-Tag** (`dev-stable-v1`, `beta-v1`, `rc-v1`, `release-v1`)
- **Vor einer öffentlichen Demo** (komprimierte Version — nur Runden 1 + 3 + 5)
- **Nach einem großen Refactoring-Sprint** der viele Seiten berührt
- **Nicht** vor kleinen Feature-Sprints — dann reicht Agent-Smoke-Check auf die betroffenen Seiten

## Wann NICHT anwenden?

- Wenn gerade Features in Arbeit sind die noch nicht fertig sind (dann macht ein Review keinen Sinn — es würde eh nur "in progress" rausbekommen)
- Wenn der Scope zu klein ist (3-5 Seiten Änderungen → normaler Feature-Sprint QA reicht)
- Wenn die App in einem komplett kaputten Zustand ist (dann erst repareren, dann reviewen)

## Historische Reviews

| Tag | Datum | Review-Datei | Outcome |
|---|---|---|---|
| `dev-stable-v1` | 2026-04-11 | `REVIEW_SPRINT_8.md` | (in progress) |
