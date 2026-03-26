# BUILD NEXT STEP — Universal Auto-Mode Prompt

Du bist der HUBEX Build-Agent. Deine Aufgabe: Den nächsten offenen Step in der ROADMAP.md vollständig umsetzen, testen und abschließen.

## Workflow (strikt in dieser Reihenfolge)

### 1. ROADMAP lesen & Step identifizieren
```bash
cat ROADMAP.md
```
- Finde den Step mit `← AKTUELL`
- Lies den Step-Namen, die Milestone-Nummer und was genau zu tun ist
- Falls kein `← AKTUELL` markiert ist: Finde den ersten `[ ]` Step und nimm diesen

### 2. Kontext sammeln
- Lies alle relevanten bestehenden Dateien die vom Step betroffen sind
- Lies die Design System Components: `frontend/src/components/ui/`
- Lies bestehende Pages als Referenz: `frontend/src/pages/DashboardPage.vue`, `frontend/src/pages/Devices.vue`
- Lies Composables als Pattern: `frontend/src/composables/useMetrics.ts`, `frontend/src/composables/useDevices.ts`
- Lies API-Routen: `app/api/v1/` für relevante Endpoints
- Lies `frontend/src/router.ts` für bestehende Routen

### 3. Implementieren
- Halte dich an das Mission Control Design System (dark theme, UCard, UButton, UBadge, UTable, etc.)
- Nutze `<script setup lang="ts">` Pattern
- Nutze CSS Custom Properties (nicht hardcoded colors)
- Nutze `apiFetch` aus `../lib/api` für API-Calls
- Nutze `createPoller` aus `../lib/poller` für Polling
- Nutze `useCapabilities` und `hasCap` für Capability-Checks
- Extrahiere Daten-Logik in Composables (`useXxx.ts`)
- Page-Component soll nur UI-State handeln (search, filter, modals)
- Mobile responsive (horizontal scroll für Tables, stacking für Formulare)
- Loading states: USkeleton, refreshing indicators
- Empty states: UEmpty Component
- Alle bestehende Funktionalität MUSS erhalten bleiben

### 4. Tests ausführen — ALLE MÜSSEN BESTEHEN

#### Backend Tests
```bash
.venv/Scripts/python.exe -m pytest tests/ -x -q
```

#### Frontend Unit Tests
```bash
cd frontend && npx vitest run
```

#### TypeScript Type Check
```bash
cd frontend && npx vue-tsc --noEmit
```
**MUSS 0 Errors haben. Nicht abschließen bis das passt.**

#### Frontend Build
```bash
cd frontend && npx vite build
```

### 5. Live UI Verification

```bash
# Backend starten
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &

# Frontend starten
cd frontend && npx vite --port 5173 &

# Warten und Health Checks
sleep 5
curl -s -o /dev/null -w "Backend: %{http_code}\n" http://127.0.0.1:8000/docs
curl -s -o /dev/null -w "Frontend: %{http_code}\n" http://127.0.0.1:5173/
```

#### Test-User erstellen und API testen:
```bash
# Register (ignoriere Fehler falls User existiert)
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"autotest@hubex.local","password":"Test1234!","org_name":"AutoTest"}'

# Login
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"autotest@hubex.local","password":"Test1234!"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || \
  curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"autotest@hubex.local","password":"Test1234!"}' | .venv/Scripts/python.exe -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Alle relevanten API-Endpoints testen
curl -s -w "\n%{http_code}" -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/metrics
curl -s -w "\n%{http_code}" -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/devices
curl -s -w "\n%{http_code}" -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/entities
curl -s -w "\n%{http_code}" -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/alert-rules
curl -s -w "\n%{http_code}" -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/events/recent
```

#### Alle UI-Seiten prüfen:
```bash
for path in "/" "/system-stage" "/devices" "/events" "/effects" "/trace" "/executions" "/correlation" "/observability" "/audit" "/auth-settings" "/token-inspector"; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:5173${path}")
  echo "$path -> $STATUS"
done
```
**Alle müssen 200 zurückgeben.**

### 6. ROADMAP.md updaten
- Aktuellen Step auf `[x]` setzen
- `← AKTUELL` zum nächsten `[ ]` Step verschieben
- Falls der Milestone komplett ist: Status auf `[done]` setzen und nächsten Milestone auf `[in-progress]`

### 7. Git Commit
```bash
git add -A
git commit -m "feat(phase-X.Y): <kurze Beschreibung>

- <was implementiert wurde>
- <tests: X passed>
- <UI verified>

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 8. Abschlussbericht (im Chat ausgeben)
```
=== STEP X.Y COMPLETE ===
Step:           <Name>
Files created:  <Anzahl>
Files modified: <Anzahl>
Backend tests:  PASS (X passed)
Frontend tests: PASS (X passed)
TypeScript:     PASS (0 errors)
Vite build:     PASS
API endpoints:  PASS (X/Y OK)
UI pages:       PASS (X/Y returned 200)
Git commit:     <hash>
Next step:      <nächster Step Name>
==============================
```

**WICHTIG: Falls IRGENDEIN Test fehlschlägt → fixen und nochmal laufen lassen. Nicht abschließen bis alles grün ist.**
