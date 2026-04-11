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

## 🔴 Sprint 3.5 — Real browser walkthrough findings

> **Methodology:** Sprint 3.5 I actually drove Chrome via the MCP extension
> (I had wrongly assumed I didn't have browser access in 3.4). Each finding
> below was seen with my own eyes in a live browser session on 2026-04-11,
> not code-inspected. Screenshots captured for evidence. This is the kind
> of pass Sprint 3.4 should have had.

### 🔴 REAL-3 P0 — Dashboard: TypeError "h.value.slice is not a function" on every load — **FIXED 3.5**
- **Root cause:** `useEventStream.ts` was `events.value = await apiFetch<StreamEvent[]>(...)` but backend `GET /api/v1/events` returns `{stream, cursor, next_cursor, items}` NOT a bare array. `events.value` became a dict, then `visibleEvents.computed` called `.slice()` on it and threw. Whole Activity Feed widget was invisible (the `<template v-else-if>` branch broke render).
- **Fix:** unwrap `.items` with forward-compat for bare arrays + empty fallback
- **File:** `frontend/src/composables/useEventStream.ts`

### 🔴 REAL-7 P0 — DashboardPage: TypeError "startsWith of undefined" after 3 fix — **FIXED 3.5**
- **Root cause:** Second wave of same pattern. After fixing `.items`, the code then called `event.event_type.startsWith(...)` in `eventIcon()`/`eventIconColor()` — but the backend events use `type` not `event_type`, and `ts` not `created_at`. Interface was totally wrong.
- **Fix:** Added `eventTypeOf(event)`, `eventTimestampOf(event)` helpers + safety-null checks in `eventBadgeStatus` + null-safe `eventRelativeTime`
- **File:** `frontend/src/composables/useEventStream.ts`, `frontend/src/pages/DashboardPage.vue`

### 🔴 REAL-4 P0 — Dashboard alert widget: every alert shows "gerade eben" regardless of age — **FIXED 3.5**
- **Root cause:** `useRecentAlerts.ts` interface said `fired_at: string` but backend returns `triggered_at`. `relativeTime(alert.fired_at)` got undefined → `NaN` → fell through to the final `return "gerade eben"` in the if-chain. Users saw "gerade eben" for alerts from 42 minutes ago.
- **Fix:** Added optional `triggered_at` + `fired_at` both; `firedAtFor(a)` helper resolves; `relativeTime` now returns "" on empty/NaN input instead of "gerade eben"
- **File:** `frontend/src/composables/useRecentAlerts.ts`, `frontend/src/pages/DashboardPage.vue`
- **Verified:** alert now shows "vor 19m" ✓

### 🔴 REAL-17/REAL-28/REAL-26 P0 — Automations + DeviceDetail ActionBar: hardcoded English despite DE locale — **FIXED 3.5**
- **Symptom:** User's original report: "in den Modals teilweise Englisch, zum Beispiel bei Automatisierungen oder create alert"
- **Root cause A — DeviceDetail "Suggested Next Steps" (ActionBar.vue):** every label + description was a hardcoded English string in an `Action[]` array at module level. 100% of users saw "Set up alerts", "Automate actions", etc.
- **Root cause B — Automations quick-start templates:** `quickTemplates: AutomationTemplate[]` was a static module-level array of English strings ("Alert when variable exceeds threshold", etc.)
- **Root cause C — Automations create-modal grid:** `TRIGGER_TYPES` and `ACTION_TYPES` and `OPERATOR_OPTIONS` were ALL static English arrays. Every trigger + action card in the Create Rule modal was English.
- **Discovery:** when fixing C, found that the de.ts + en.ts files already contained `automations.triggerTypes.*`, `automations.actionTypes.*`, `automations.templates.*` keys with full German translations. **They were just never wired to the Vue code.** Dead i18n code.
- **Fix:** Wire Vue code to existing keys by wrapping the arrays in `computed(() => [... t(...)])`. Update `.find()` callers to `.value.find()`. New `operators.*` keys in en+de. Add `actionBar.*` key block in en+de (ActionBar had no pre-existing keys).
- **Files:** `frontend/src/components/ActionBar.vue`, `frontend/src/pages/Automations.vue`, `frontend/src/i18n/locales/{en,de}.ts`
- **Verified live:** Automations empty-state cards now say "Alarm bei Schwellwertüberschreitung", Create modal shows "Variablen-Schwellwert / Wenn eine Variable einen Wert über- oder unterschreitet", etc. ✓

### 🟠 REAL-10 P1 — Dashboard "Großer Ausfall" label confusing next to "6 online"
- **Symptom:** User sees "6 GERÄTE ONLINE / Großer Ausfall" which looks contradictory (6 is plural, looks healthy)
- **Root cause:** `onlinePct` = online / total. With 6/13 = 46%, the `< 50` branch hits and shows "majorOutage" label. Semantically correct but visually jarring when the big number is positive-looking.
- **Status:** ☐ deferred — design decision needed (separate warn banner? redesign the KPI card? drop the label entirely?)

### 🔴 REAL-18/REAL-19 P0 — DeviceDetail: giant blank area after scroll + Chrome renderer freeze
- **Symptom:** Navigate to /devices/{id}, scroll down — above-fold ~70% blank. Then chrome `Page.captureScreenshot` timed out after 30s ("renderer may be frozen").
- **Root cause:** Unknown — not investigated. Likely a flex/viewport height calculation interacting badly with the collapsible "Technische Details" panel.
- **Status:** ☐ deferred — needs proper devtools performance trace to diagnose

### 🟠 REAL-37 P1 — Top-bar page titles in English (router meta.title)
- **Symptom:** Every page has its top header in German (e.g. "Geräte") but the top-bar shows "Devices", "Variables", "Automations", "Plugins", "Settings" in English. Visual inconsistency on every page.
- **Root cause:** `router.ts` routes have static `meta: { title: "Devices" }` etc. and `document.title` gets set from that. Not i18n'd.
- **Status:** ☐ deferred — mechanical fix, one-line per route, plus a locale-aware wrapper in main.ts beforeEach

### 🟡 P2 findings (english strings not yet i18n'd)

- **REAL-1** Dashboard alert: "variable 'temperature' value 20.3 gt 20" is backend-generated english in `app/core/alert_worker.py` line 196. Needs i18n at backend.
- **REAL-6** Backend alert_worker.py hardcoded English format string
- **REAL-11/12/13/14/15** Devices page: top-bar "Devices", section header duplicate, "Unclaim mode"/"Select all"/"Last seen"/"Open" buttons, column headers DEVICE/TYPE/HEALTH/STATE/ONLINE/LAST SEEN/ACTIONS, status badges `ok`/`ready`/`online`/`Simuliert` — all hardcoded english
- **REAL-20/21/22/23/24** Variables page: top-bar "Variables", variable descriptions "CPU usage"/"Battery level" etc. (backend seed-data english), tag labels (`actuator`/`power`/`system`), status badges (`device`/`float`)
- **REAL-25** Automations top-bar "Automations" vs header "Automatisierungen"
- **REAL-29/30** Automations create modal: Name placeholder "e.g. High temperature alert" + Description placeholder "What does this rule do?" — keys exist in en.ts but template doesn't use them
- **REAL-31** Alerts filter buttons: "Firing"/"Acknowledged"/"Resolved" english
- **REAL-32** Alerts status badges: "CRITICAL"/"FIRING"/"RESOLVED" english
- **REAL-33** Same as REAL-1 (backend alert message format)
- **REAL-34** Plugin catalog descriptions: `plugin_catalog.py` has English `description=` fields. Should be i18n-aware (serve-time translation or per-locale map).
- **REAL-35** Settings → Features "Runtime Feature Flags" / "Toggle subsystems" / "Open Setup Wizard" english
- **REAL-36** `features.py` FEATURE registry descriptions all English — surfaces in Settings → Features UI

### 🔵 Minor / observation
- **REAL-2** Dashboard "Großer Ausfall" sub-label under a number is confusing (see REAL-10)
- **REAL-5** Backend AlertEvent response shape has `status` not `severity` field — the `severity` comes from joined AlertRule. Dashboard widget used to error out from this. Fixed implicitly by REAL-4 fix making severity optional.
- **REAL-8** Dashboard "Aktivitäten" widget has a green dot without explanation. Is it "live"?
- **REAL-9** Activity feed events rendered as "Org Created", "Device Paired" (English) — should come through an event-type-to-label mapping
- **REAL-27** Clicking an empty-state template card in Automations doesn't always open modal — might be dead-zone around card border

---

## ✅ Verified still working in Sprint 3.5 real-browser pass

- ✅ Sprint 3.1 configure modal: rich intro, "API-Key holen ↗" link, provider hint, visible help text, lock icon privacy line, "Speichern & schließen" button
- ✅ Sprint 3.2 Settings deep-link: `/settings?section=features&highlight=orchestrator` auto-expands Features section
- ✅ Sprint 3.3 Plugins: n8n shows "Öffnen ↗" external-tab icon button (allow_iframe=false honored); Claude in installed list shows "braucht Setup" badge + "Einrichten" CTA; plugin icons render (🌀 🧠 ✨)
- ✅ Sprint 3.4 Hardware: exactly 4 boards (ESP32 V1/C3/S3 + Pi Pico W), no duplicates
- ✅ Sprint 3.4 Automations IF/THEN labels DE
- ✅ Sprint 3.4 Alerts severity DE
- ✅ Sprint 3.4 Devices > Groups: visited device 2, no visible flicker on refresh (though the page has other bugs REAL-18/19)
- ✅ Sprint 3.5 Dashboard: no console errors, activity feed now visible, alert timestamps correct

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
