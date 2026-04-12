# HUBEX — Claude Code Instructions

## Projekt
HUBEX ist ein universeller IoT Device Hub (FastAPI Backend + Vue 3 Frontend).
**Device = Oberbegriff** mit 4 Unterkategorien: Hardware, Service, Bridge, Agent.
**Vision:** Anbinden → Verstehen → Visualisieren → Automatisieren (4 Ebenen)

## Bei Session-Start: Kontext laden
1. Lese `ROADMAP.md` — Section "Sprint Track" nach dem aktuell offenen Sprint (`← NÄCHSTER SCHRITT`) und dem Abhängigkeits-Graph
2. Lese `UX_GAPS.md` nur noch falls der offene Sprint auf Phase 5b/UX zurückkommt — fast alle UX gaps sind erledigt, nur 2 low-prio residuals offen (2.8, 6.3)
3. Bei sprint-spezifischen plan-files: Check `.claude/plans/` für z.B. `wild-tinkering-hearth.md` (Sprint 3) — falls ein aktiver plan existiert, ist er dort

## 7 UX-Grundprinzipien (gelten IMMER)
1. Progressive Disclosure — Default zugeklappt
2. Selektoren statt ID-Eingabe — ÜBERALL
3. Kontextuelles Arbeiten — Von Element zum nächsten Schritt MIT Kontext
4. Unterstützend, nie aufdringlich — Wizards skippbar
5. Minimalistisch — Keine JSON-Fehler, nur was relevant
6. Wächst mit Komplexität — Einfach=einfach, komplex=detaillierter
7. Verständliche Sprache — Tooltips, klare Buttons, Bestätigung

## WICHTIG: Keine Kosmetik vor Flow-Fixes
Flow-Fixes (kontextuelles Arbeiten, Navigation mit Kontext) > Layout/Darstellung.
Erklärungen/Tooltips > Farben/Fonts. Interaktive Elemente > statische Anzeigen.

## Automode — wenn User "weiter" sagt
**SOFORT ausführen, NICHT nachfragen:**
1. Lese `ROADMAP.md` — Section "Sprint Track", find sprint mit `◄── NÄCHSTER SCHRITT`
2. Falls `.claude/plans/<plan-name>.md` für den sprint existiert, lesen (sprint-spezifischer implementation plan)
3. TodoWrite mit allen Sprint-Steps aufsetzen, live abarbeiten
4. Per module: syntax-check → `docker cp` into running container → restart → **curl-test** (QA-Rigor aus Sprint 2.1 feedback)
5. Vite build am ende: `cd frontend && npx vite build`
6. Full e2e: `docker compose -f docker-compose.full.yml build backend frontend` + `up -d` + curl script gegen alle neuen endpoints
7. ROADMAP.md updaten (sprint track section + milestone extension)
8. Commit + push (NUR wenn user explizit "commit"/"push" sagt — safety rule)
9. Report ausgeben mit test-assertion counts

## Grundregel für JEDES neue Feature
1. Per REST-API erreichbar? (ja)
2. Per Webhook triggerbar? (wenn Event-basiert: ja)
3. Folgt den 7 UX-Prinzipien? (ja)
4. In API-Doku beschrieben? (ja)

## Wichtige Pfade
- Backend: `app/` (FastAPI, Python)
- Frontend: `frontend/src/` (Vue 3 + TypeScript + Tailwind)
- UI Components: `frontend/src/components/ui/`
- Gap-Analyse: `UX_GAPS.md` (Projekt-Root) — archive/reference only, Phase 5b ist done
- UX-Specs: `C:\Users\lange\Desktop\prompt.txt` bis `prompt 6.txt` (nicht im Repo)
- Vision: `C:\Users\lange\Desktop\vision.txt` (nicht im Repo)
- Sprint plans: `.claude/plans/<name>.md` (z.B. `wild-tinkering-hearth.md` für Sprint 3)
- Test User: `test@test.com` / `Test1234!` (role=owner, in full-docker setup)
- Backend Port: 8000
- Frontend Port: `80` im full-docker stack (`docker-compose.full.yml`) ODER `5173` bei `npm run dev`
- Portainer: `https://localhost:9443` (admin / `HUBEX_PORTAINER_PASS` aus .env, bootstrap via `HUBEX_PORTAINER_ADMIN_HASH`)

## Aktueller Stand (Stand: Sprint 3 shipped)
**Phasen-Roadmap (alle done):**
- Phase 1–4 (Core/UI/Data/Integration): ✅
- Phase 5 / 5b / 5c (UX + Completion + Stability): ✅
- Phase 6 (Erweiterung: n8n/MCP/Bridge): ✅
- Phase 7a / 7b / 7c (Production/Enterprise/Polish): ✅
- Phase 8 (Hardware-Konzepte): ✅ concept-done
- Phase 9 (Release-Readiness R1-R7): ✅

**Sprint Track (parallele feature sprints, commit-tagged):**
- Sprint 1: Feature Flags + Setup Wizard ✅ `ce50e84`
- Sprint 2: ESP Codegen (+2.1 bugfixes) ✅ `67d1f04`
- Sprint 3: Plugin Manager v2 (service+connector, portainer, catalog) ✅ `a42e481` → siehe M32b in ROADMAP
- **Sprint 4: firmware_builder** ◄── NÄCHSTER SCHRITT (PlatformIO-sidecar via portainer_client, feature-gated)

**Todo-Phasen (echte zukünftige arbeit):**
- Phase 10: Commercialization (License, CE/EE, Legal, Hardening) [todo]
- Phase 11a: Hardware Implementation Blocks A-H [coming soon]
- Phase 11b: Produkt-Evolution [brainstorm]

## Deploy-Checkliste (Tester-Safe) — PFLICHT vor jedem Deploy
Testnutzer sind aktiv auf hubextest.tech. Jeder Deploy MUSS diese Regeln einhalten:

- [ ] **Neue Sidebar-Items** → `comingSoon: true` ODER `cap: "cap.admin"` setzen
- [ ] **Neue Seiten** → `<RequireCap cap="cap.admin">` wrapper um den Content
- [ ] **Neue Sections auf bestehenden Seiten** → `v-if="hasCap('cap.admin')"` um neue Bereiche
- [ ] **Neue API-Endpoints** → In `CAPABILITY_MAP` (capabilities.py) mit `cap.admin` schützen
- [ ] **DB-Änderungen** → NUR `nullable=True` Columns (kein DROP, kein ALTER NOT NULL, kein Rename)
- [ ] **`tsc -b && vite build` erfolgreich?** (tsc ist strenger als vite alleine!)
- [ ] **Kein Breaking Change** an bestehenden API-Responses (keine Feld-Umbenennungen, keine Typ-Änderungen)
- [ ] **Bestehende Daten unberührt** → Keine Seed-Scripts die vorhandene Daten überschreiben

### Mechanismen zur Feature-Isolation
| Mechanismus | Wo | Wirkung |
|---|---|---|
| `cap: "cap.admin"` | DefaultLayout.vue Nav-Item | Seite nur für Owner/Admin |
| `comingSoon: true` | DefaultLayout.vue Nav-Item | Sichtbar aber ausgegraut + nicht klickbar |
| `<RequireCap cap="x">` | Beliebige Seite | Content-Block nur mit passender Cap |
| `v-if="hasCap('cap.admin')"` | Inline in Templates | Einzelne UI-Sections verstecken |
| `CAPABILITY_MAP` | capabilities.py | Backend blockt Route ohne passende Cap |

## Design System — "Warm Depth"
- Primary: Amber/Gold (#F5A623) | Accent: Teal (#2DD4BF) | BG: #111110
- Fonts: Satoshi (Display), Inter (Body), IBM Plex Mono (Data)
