# HUBEX — Claude Code Instructions

## Projekt
HUBEX ist ein universeller IoT Device Hub (FastAPI Backend + Vue 3 Frontend).
**Device = Oberbegriff** mit 4 Unterkategorien: Hardware, Service, Bridge, Agent.

## Automode — wenn User "weiter" sagt

**SOFORT ausführen, NICHT nachfragen:**

1. Lese `ROADMAP.md` im Projekt-Root — finde den Step mit `← AKTUELL`
2. Lese zugehörige `PROMPT_PHASE_X_Y.md` falls vorhanden
3. Implementiere alles was im Step/PROMPT steht
4. TypeScript check: `cd frontend && npx tsc --noEmit`
5. Vite build: `npx vite build`
6. UI verify: preview_start → Screenshots → Console errors
7. ROADMAP.md updaten: aktuellen Step `[x]`, nächsten `← AKTUELL`
8. Report anhängen an `REPORTS.md` und an User ausgeben

**Niemals nach Kontext fragen** — immer selbst ROADMAP.md lesen.

## Wichtige Pfade
- Backend: `app/` (FastAPI, Python)
- Frontend: `frontend/src/` (Vue 3 + TypeScript + Tailwind)
- UI Components: `frontend/src/components/ui/`
- Test User: `codex+20251219002029@example.com` / `Test1234!`
- Backend Port: 8000 | Frontend Port: 5173

## Aktueller Stand
- Phase 1–4 (M1–M12.5): ✅ Done — Core, UI, Data Hub, Integration, CI/CD, Docs, Pitch
- **Phase 5: UX-Überholung & Plattform-Fundament** ← AKTUELL
- **Nächster Milestone: M13 Design System Reboot** (Warm Depth Tokens, Branding, i18n)

## Design System — "Warm Depth" (NEU ab M13)
- Primary: Amber/Gold (#F5A623) | Accent: Teal (#2DD4BF) | BG: #111110
- Fonts: Satoshi (Display), Inter (Body), IBM Plex Mono (Data)
- Design-Referenzen: brand_01–04 HTML-Dateien
- 17 bestehende UI Components werden auf neue Tokens migriert (M13 Step 4)

## Architektur-Grundsätze (verbindlich)
- Semantisches Typsystem: Basis-Datentypen + semantische Typen (M14)
- Bidirektional: read_only / write_only / read_write Variablen
- Auto-Discovery standardmäßig AN (M15 Step 5)
- Branding-Entkopplung: Produktname nie hardcoded (M13 Step 2)
- i18n-Foundation: vue-i18n, DE + EN (M13 Step 3)
- Kontextuelles Arbeiten: Connect-Panel, Kontextmenüs (M16)

## Verbindliche Entscheidungen
- KEIN Code-Änderung ohne explizite User-Anweisung für den konkreten Step
- Die ROADMAP.md ist der Plan, nicht der Startschuss
- Warte auf Sprint-/Step-Anweisung bevor du implementierst
