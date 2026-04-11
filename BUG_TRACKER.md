# HubEx Bug Tracker

> **Erstellt:** Sprint 3.4 (nach user-browser-session 2026-04-11)
> **Scope:** Lebendiges dokument für bugs, UX issues, hardcoded strings,
> performance, fehlerhafte features. Jeder eintrag hat: severity, symptom,
> root cause (wenn known), betroffene files, fix plan oder status.
>
> **Nicht zu verwechseln mit** `UX_GAPS.md` (historisches dokument für
> Phase 5b UX Completion, archiviert). Neue bugs → hier rein.

---

## Severity legende

- **🔴 P0 blocker** — funktion kaputt oder unbenutzbar, usertext blockiert
- **🟠 P1 major** — funktion arbeitet aber falsch, datenverlust möglich, frustrierend
- **🟡 P2 minor** — cosmetisch, hardcoded strings, doppelte einträge, glitch
- **🔵 P3 nice-to-have** — UX polish, animation, wording
- **✅ FIXED** — behoben, mit commit-ref

---

## User-reported (Sprint 3.4 kickoff session)

### 🟠 P1 — Hardcoded English in modals (Automations + Create Alert)
- **Symptom:** Bei DE locale ist Automations-Builder und Create-Alert-modal teilweise englisch
- **User quote:** "Wenn ich auf Deutsch stelle, habe ich trotzdem in den Modals teilweise Englisch, zum Beispiel bei Automatisierungen oder create alert. Vielleicht ist das hard coded."
- **Root cause:** vermutlich `<button>Save</button>` statt `{{ t('...') }}`
- **Files:** `frontend/src/pages/Automations.vue`, `frontend/src/pages/Alerts.vue`, evtl. modals component dir
- **Fix plan:** grep alle .vue files nach hardcoded english words in modal scope, durch t() ersetzen, neue i18n keys
- **Status:** ☐

### 🟠 P1 — MCP Alert encoding/formatting issues
- **Symptom:** Wenn MCP alerts sendet → kryptische zeichen, formatierungsfehler
- **User quote:** "Bei MCP wenn er Alerts sendet, dann ist das immer kryptisch. Da sind irgendwie die Zeichen nicht richtig übergeben, Formatierungsfehler oder so."
- **Root cause candidates:** UTF-8 encoding verlust im MCP transport, oder markdown/html mix nicht escaped, oder n8n webhook payload serialisierung
- **Files:** `app/core/webhook_dispatcher.py`, MCP server integration, alert notification formatter
- **Fix plan:** reproduzieren (alert via automation → MCP webhook), payload inspizieren, encoding + serialisierung fixen
- **Status:** ☐

### ✅ P2 — Hardware Boards: jeder ESP doppelt — FIXED
- **Symptom:** In Hardware Boards page erscheint jeder ESP-variant zweimal
- **User quote:** "Da steht jeder ESP, den es gibt, zweimal drin."
- **Root cause:** `_ensure_builtins()` in `app/api/v1/hardware.py` hatte einen check-then-create race: request A sieht leere table → inserts 4 boards → commit. Gleichzeitig request B (oder der zweite seed call beim alembic+startup-patches) sieht auch "keine is_builtin=true rows" und inserts nochmal 4. Ergebnis: 8 rows, jeder ESP doppelt.
- **DB vor fix:** 8 rows (4 distinct names × 2)
- **Fix:** rewrite von `_ensure_builtins` mit (1) de-dup DELETE per name keeping MIN(id), (2) per-name existence check statt table-level check. Idempotent, race-safe. Cleanup läuft auf erstem GET /boards nach dem upgrade automatisch.
- **DB nach fix:** 4 rows (4 distinct names × 1) ✓ verifiziert
- **File:** `app/api/v1/hardware.py`
- **Status:** ✅ Sprint 3.4

### 🟠 P1 — Camera zoom broken (fly_to_node / zoom animations)
- **Symptom:** Zoom klappt überhaupt nicht, landet irgendwo nicht fokussiert, nicht smooth
- **User quote:** "Bei den Kamerafahrten, zum Beispiel. Da klagt der Zoom immer noch überhaupt nicht. Der zoomt irgendwohin, überhaupt nicht fokussiert, sinnlos. Das läuft nicht smooth."
- **Vorgeschichte:** mehrere commits an dem ding: `bcebea4` (targets element position), `215031e` (uses document.body + fix .kpi-card selector), `e6292cc` (camera zoom on #camera-viewport), `e90c44c` (scrollIntoView + center origin)
- **Root cause:** offenbar wiederholt nicht fixed, fundamental design problem
- **Files:** `frontend/src/lib/camera.ts` oder ähnlich, component die zoom nutzt
- **Fix plan:** von grund auf rewrite: transform-origin + scale + translate-berechnung anhand bounding-rect des target elements, smooth via CSS transition oder requestAnimationFrame
- **Status:** ☐

### 🟡 P2 — MCP communication speed
- **Symptom:** MCP steuerung zu langsam
- **User quote:** "Die MCP Steuerung Kommunikation ein bisschen langsamer als ich mir das wünschen würde. Ich würde wünschen dass es schneller ginge."
- **Fix plan:** profilen, bottleneck finden: polling-interval, http roundtrip, serialisierung, db-queries per call
- **Status:** ☐

### 🟠 P1 — Devices > Variables > Groups: zittert bei refresh, zweck unklar
- **Symptom:** Groups-bereich auf Devices-seite innerhalb Variables flackert bei refresh hin und her; plus sinnhaftigkeit/funktion unklar
- **User quote:** "Bei Devices, unter den Variablen, diesem Bereich Gruppen, der Spackt beim Refresh. Der zittert hin und her und die Sinnhaftigkeit und die Funktion davon ist halt auch immer noch nicht geklärt."
- **Root cause candidates:** reactive array neu-erstellt statt mutated → Vue re-mount, oder fetch returns different order → layout shift
- **Files:** `frontend/src/pages/DeviceDetail.vue`, variable groups component
- **Fix plan:** 1) stable keys + computed statt data-reassign fix den zitter, 2) separate discussion: was ist der zweck? Wahrscheinlich erklärungs-tooltip + empty-state-guidance fehlt
- **Status:** ☐

---

## Sprint 3.4 code-tour audit findings (from simulated new-user walkthrough)

> **Methodology:** Systematic code-inspection across 10 key pages (Login,
> SetupWizard, DashboardPage, Devices, DeviceDetail, Variables, Automations,
> Alerts, Dashboards, Plugins, Settings). Agent reported ~50 findings;
> summarized here grouped by severity pattern. Individual items not
> tabulated exhaustively — the patterns are the actionable item.

### 🔴🟠 P0/P1 cross-cutting patterns (affect 5+ pages each)

1. **Hardcoded English strings in modals + forms** (SetupWizard, Devices, Variables, Automations, Alerts, Plugins, Settings)
   - ~15+ occurrences per page on average
   - Particularly egregious in SetupWizard (20+), Automations (trigger/action type labels rendered raw), Devices (context menu items)
   - **Status:** Started (Automations IF/THEN + severity + Alerts severity fixed in Sprint 3.4). Remaining 80%+ of strings still todo → Sprint 3.5 i18n pass
   - **Files:** all pages, but audit surfaced concrete line numbers

2. **`confirm()` instead of `UModal` for destructive actions** (9+ pages)
   - Horrible on mobile
   - Affects: Variables (delete definition), Automations, Dashboards, Settings (reset onboarding)
   - **Fix:** Generic `UConfirmModal` component + migration in one pass
   - **Status:** ☐ not started

3. **Missing loading states on async actions** (Devices, Alerts, Automations, Plugins, Settings, Dashboards)
   - Buttons stay clickable during request → double-submission risk
   - **Fix:** `:disabled="loading"` + loading-text consistent across all forms
   - **Status:** ☐ not started

4. **No form validation before submit** (SetupWizard, Dashboards, Settings, Automations)
   - Empty names, missing required fields, invalid hex colors all get sent to backend
   - **Fix:** Lightweight `validate(form)` helpers + error display, not full validation framework
   - **Status:** ☐ not started

5. **Index-based v-for keys** (Automations: `:key="gi"`, `:key="ci"` in condition groups)
   - Causes reorder bugs — add/delete shuffles state between rows
   - **Fix:** Generate stable ids when adding items
   - **Status:** ☐ not started

6. **Silent error handling** (SetupWizard: feature load, Devices: QR fetch, Plugins: status)
   - `.catch(() => {})` or no catch at all; user sees empty UI with no explanation
   - **Fix:** Error toast + user-facing message pattern everywhere
   - **Status:** ☐ not started

### 🟡 P2 — degraded UX patterns

7. **Inconsistent / missing empty states** (Login, Dashboards — first dashboard)
   - **Fix:** `UEmpty` component with CTAs pointing at logical next step

8. **Async race conditions** (Devices: pairing timer on unmount, Alerts: deviceMap populated async after template renders)
   - **Fix:** abort controllers / watchEffect patterns

9. **Emoji as icons** (Variables category icons)
   - Font-substitution breaks alignment on systems without emoji
   - **Fix:** Inline SVG icons per category (Sprint 3.4 plugin icons are actually also emoji-SVG and should evolve too)

10. **Delete/destructive confirms lack destructive visual** even when modal exists

11. **No field descriptions / help text** in Plugin configure modal (Sprint 3.1 partially addressed — helper text visible but no per-field descriptions)

12. **Widget ordering not persistent** (Dashboards) — drag-drop works in UI but doesn't save to backend

13. **`relativeTime()` can return NaN** if fired_at is null (DashboardPage alerts list)

### 🔵 P3 — polish

14. Magic numbers (SetupWizard: `totalSteps = 5` hardcoded in 3 places)
15. "Coming Soon" badges without version-check (DashboardPage)
16. MFA code length check only on submit button
17. Password placeholder not i18n'd
18. LocalStorage keys not namespaced (revealedKeys in Variables etc.)

### Page-specific verdicts (agent assessment)

| Page | Verdict | Top blocker |
|---|---|---|
| Login.vue | ⚠️ needs work | No forgot-password, silent registration errors |
| SetupWizard.vue | 🔴 broken (rel.) | 20+ hardcoded strings, feature-deps not validated on preset apply |
| DashboardPage.vue (home) | ⚠️ needs work | Wizard logic too simple (no skip-if-devices-exist), silent dismisses |
| Devices.vue | ⚠️ needs work | Hardcoded context menu, timer race on unmount, QR silent fail |
| Variables.vue | ⚠️ needs work | Delete uses browser `confirm()`, emoji icons, conflict modal incomplete |
| Automations.vue | ⚠️ needs work | Trigger/action type labels raw, index keys, no validation |
| Alerts.vue | ⚠️ needs work | deviceMap async race, severity badges not i18n'd, no counts in filter tabs |
| Dashboards.vue | ⚠️ needs work | No name validation, missing CTA for first widget, widget order not persistent |
| Plugins.vue | ⚠️ needs work | Uninstall modal exists but lacks destructive visual, no per-field descriptions (partial fix in 3.1) |
| Settings.vue | ⚠️ needs work | Hardcoded language list, no hex color validation |

**Overall:** A new user can technically use the app, but runs into friction at nearly every page — missing confirmations, silent errors, mixed language, slow perceived feedback, occasional broken flows.

---

## ✅ Fixed in Sprint 3.4 (this session)

| Bug | Fix | File |
|---|---|---|
| Hardware boards — every ESP duplicated (8 rows of 4 distinct names) | Rewrote `_ensure_builtins` with per-name existence check + de-dup DELETE keeping MIN(id). Race-safe, idempotent. | `app/api/v1/hardware.py` |
| Camera zoom broken (every previous fix-attempt failed) | Math-based rewrite: transform-origin `0 0`, compute translate from `getBoundingClientRect` of vp + target, single transition. | `frontend/src/composables/useAiCommands.ts` |
| MCP alert encoding → kryptische zeichen | `str(result)` → `json.dumps(result, ensure_ascii=False, default=str)` on legacy `POST /tools/call` endpoint. SSE transport got same `ensure_ascii=False` improvement. Umlauts, emoji, and German text now pass through correctly. | `app/mcp/endpoint.py` |
| Devices > Variables > Groups zittert bei refresh | Race-guarded parallel fetch + stable sort. Old: N+1 sequential requests, list cleared-and-rewritten every refresh, re-mount flicker. New: `Promise.all` for bindings, load-sequence guard against stale writes, `sort((a,b)=>a.entity_id.localeCompare(b.entity_id))` so v-for keys stay stable. | `frontend/src/pages/DeviceDetail.vue` |
| Automations modal: IF/THEN labels + severity options hardcoded English | Added `automations.ifLabel/thenLabel/severity*/headersJsonLabel/payloadJsonLabel/alertMessagePlaceholder` keys to en + de, wired through template. | `frontend/src/pages/Automations.vue`, `frontend/src/i18n/locales/{en,de}.ts` |
| Alerts modal: severity options hardcoded English | Added `alerts.severityInfo/Warning/Critical` + `entityIdLabel` keys. | `frontend/src/pages/Alerts.vue`, `frontend/src/i18n/locales/{en,de}.ts` |
| Plugin catalog cards had no icons | Added data-URL SVG emoji icons (n8n 🌀, Claude 🧠, OpenAI ✨). Plugins.vue marketplace card template renders `<img :src="entry.icon_url">` with `.charAt(0)` text fallback. | `app/core/plugin_catalog.py`, `frontend/src/pages/Plugins.vue` |
