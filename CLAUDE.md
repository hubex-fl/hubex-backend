# HUBEX — Claude Code Instructions

## Projekt
HUBEX ist ein universeller IoT Device Hub (FastAPI Backend + Vue 3 Frontend).
**Device = Oberbegriff** mit 4 Unterkategorien: Hardware, Service, Bridge, Agent.
**Vision:** Anbinden → Verstehen → Visualisieren → Automatisieren (4 Ebenen)

## Bei Session-Start: Kontext laden
1. Lese `memory/project_complete_context.md` — enthält Vision, UX-Prinzipien, aktuellen Stand
2. Lese `UX_GAPS.md` im Projekt-Root — enthält alle offenen Gaps mit IST/SOLL/Dateien
3. Lese `ROADMAP.md` — finde Phase 5b und den Step mit `← AKTUELL`

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
1. Lese `ROADMAP.md` — finde den Step mit `← AKTUELL`
2. Lese `UX_GAPS.md` für Details zum aktuellen Sprint
3. Lese zugehörige `PROMPT_PHASE_X_Y.md` falls vorhanden
4. Implementiere
5. Vite build: `cd frontend && npx vite build`
6. UI verify: preview_start → Screenshots → Console errors
7. ROADMAP.md updaten + UX_GAPS.md Status updaten
8. Report ausgeben

## Grundregel für JEDES neue Feature
1. Per REST-API erreichbar? (ja)
2. Per Webhook triggerbar? (wenn Event-basiert: ja)
3. Folgt den 7 UX-Prinzipien? (ja)
4. In API-Doku beschrieben? (ja)

## Wichtige Pfade
- Backend: `app/` (FastAPI, Python)
- Frontend: `frontend/src/` (Vue 3 + TypeScript + Tailwind)
- UI Components: `frontend/src/components/ui/`
- Gap-Analyse: `UX_GAPS.md` (Projekt-Root)
- UX-Specs: `C:\Users\lange\Desktop\prompt.txt` bis `prompt 6.txt` (nicht im Repo)
- Vision: `C:\Users\lange\Desktop\vision.txt` (nicht im Repo)
- Test User: `codex+20251219002029@example.com` / `Test1234!`
- Backend Port: 8000 | Frontend Port: 5173

## Aktueller Stand
- Phase 1–4 (M1–M12.5): ✅ Done
- Phase 5 (M13–M20): ✅ Done (mit offenen Steps)
- Phase 6 (M21–M24): ✅ Done
- **Phase 5b: UX Completion** ← AKTUELL (Sprints UX-1 bis UX-5)
- Phase 7: Enterprise (M14b, M19b, M18b, M26-M36) → danach

## Design System — "Warm Depth"
- Primary: Amber/Gold (#F5A623) | Accent: Teal (#2DD4BF) | BG: #111110
- Fonts: Satoshi (Display), Inter (Body), IBM Plex Mono (Data)
