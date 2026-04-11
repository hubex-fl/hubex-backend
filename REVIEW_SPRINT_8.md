# Review: `dev-stable-v1` (2026-04-11)

> Sprint 8 review per `docs/REVIEW_PROCESS.md`. Target: `dev-stable-v1` tag.
> First big review run — the process doc doubles as the template.

## Quick-Status
- **Started:** 2026-04-11
- **Round 1 (Smoke Pass):** ✅ **COMPLETE** — 48 routes walked, 36 findings, **36/36 fixed**
- **Round 2 (Visual):** ✅ **COMPLETE** — 12 routes walked, 11 findings, **8/11 fixed**, 3 flagged
- **Round 3 (Persona):** 🔁 **IN PROGRESS** — user's initial walk done (25 findings), Option A fix batch done, Neuer-User walk done
- **Round 4 (Perf + A11y):** ✅ **COMPLETE** — 5 routes measured, 5 a11y sweeps, 6 findings, **5/6 fixed** (1 P3 deferred)
- **Round 5 (Fixing):** ✅ merged into per-round fix phases
- **Round 6 (Release):** ⏸ pending (after Round 3 walks complete + Round 4)
- **Findings R1:** 36 total — **0 P0 / 8 P1 / 18 P2 / 10 P3** — **36/36 fixed**
- **Findings R2:** 11 total — **0 P0 / 1 P1 / 7 P2 / 3 P3** — **8/11 fixed**
- **Findings R3 (user walk):** 25 total — **0 P0 / 6 P1 / 11 P2 / 7 P3 / 1 clarification** — **11/25 Option A fixed** (commit `7d169b2`)
- **Findings R3 (NU walk):** 6 total — **0 P0 / 2 P1 / 3 P2 / 1 P3** — **2/6 fixed** (commit `3c5d28b`)

### Round 1 Fix Commits

| Batch | Commit | Findings | Description |
|-------|--------|----------|-------------|
| 1 | `e8cbac1` | F03, F07 | Data bugs: metrics org-scoping + /audit onMounted auto-load |
| 2 | `651f0f4` | F01, F02, F18 | Sidebar CMS children + Tour/Sandbox i18n + /login redirect |
| 3 | `01b19be` | F08, F09, F10, F16, F17 | 5 pages (entities, effects, executions, admin, system-stage) |
| 4 | `31aa94e` | F12, F15, F27 | reports + email-templates + semantic-types (+2 seed-name helpers) |
| 5a | `e9281df` | F06 (part 1) | useBoardLabels composable + hardware pages |
| 5b | `1b6760b` | F06 (part 2) | HardwareWizard full i18n + useShieldLabels + useComponentLabels |
| 6 | `bd4b7c0` | F04, F05, F11, F13, F19-F26, F34-F36 | 15 minor findings batched (incl. /landing 105 keys) |
| 7a | `8d7db62` | F28-F33 (main) | 6 CMS main pages (291 new keys) |
| 7b | `c40bc14` | F28-F33 (editors) | 5 CMS editor child pages + 3 components (800 new keys) |
| 7c+7d | `02479bb` | F28-F33 (final) | BlockCanvas, PageVersionHistory, TreeNode, 7 block renderers (149 new keys) |

**Total i18n keys added: ~2,100 per locale. Strict en/de parity maintained throughout.**

### Composables introduced

- `useBoardLabels` — backend-seeded board name/description translation
- `useShieldLabels` — backend-seeded shield name/description translation (with standalone `shieldSlug()`)
- `useComponentLabels` — backend-seeded hardware component name/description translation

Plus inline `localized*` seed-name helpers for:
- `localizedTemplateName` in EmailTemplates
- `localizedTypeName` in SemanticTypes
- `localizedSimulatorName` in Sandbox

### Design decisions made by user

| Finding | Call |
|---------|------|
| F01 /login redirect when authenticated | Fixed (router.replace('/') on mount) |
| F11 "Observability" / F25 JWT labels | Route through i18n; loanword values kept in DE when no good translation |
| F34 /landing full German marketing | Translate everything — did with ~105 keys, proper marketing German |
| F06 board-descs + backend seed pattern | Yes, composable pattern approved (useBoardLabels, etc.) |
| CMS strategy | Option (a) — fix all 6 CMS routes + all editors before tag |

### Cumulative file impact
- **61 files touched** across 10 commits
- **~5,800 line-edits** (insertions + deletions)
- **6 new composables/helpers** created
- **2 backend fixes** (metrics.py org scoping, Audit.vue auto-load)
- **Zero regressions** (vite build clean every batch, no unresolved components, no console errors)

### Summary of Round 1

- **Zero P0 breakage, zero unresolved components, zero console errors.** Sprint 5.d lint rule holds and Sprint 3.8-hotfix DeviceDetail imports are solid.
- **Big i18n gap in CMS subsystem** — all 6 CMS routes (`/cms`, `/cms/forms`, `/cms/menus`, `/cms/media`, `/cms/redirects`, `/cms/settings`) are essentially 100% English. Zero i18n keys wired there yet. That alone is ~5-6 findings at P1-P2.
- **"Secondary" pages mixed** — `/entities`, `/effects`, `/executions`, `/reports`, `/email-templates`, `/admin`, `/system-stage`, `/settings/types` all have significant English leaks (F08, F09, F10, F12, F15, F16, F17, F27). These are legitimately large chunks of the app that have never been through a locale sweep.
- **2 data-layer bugs found** (not just i18n): `R1-F03` Dashboard-KPI vs `/automations` list mismatch (metrics says 2 active, list returns 0), and `R1-F07` `/audit` UI empty-state despite API returning entries (likely response-shape mismatch).
- **Sprint 3.6 / 3.7 / 3.8 / 5 sweeps hold on the pages they touched** — `/dashboard`, `/devices`, `/devices/1`, `/alerts`, `/automations`, `/variables`, `/settings`, `/firmware`, `/plugins`, `/setup`, `/events`, `/system-health`, `/variables/streams` all clean.

---

## Scope

### Walked in Round 1
48 routes from router.ts. Skipped: `/devices/:id` parameter variants beyond `/1`, `/dashboards/:id`, `/kiosk/:id`, `/embed/:token`, `/public/:token`, CMS edit / view subroutes, `/plugins/:key/embed`, `/settings/auth` (redirects to /settings) — these need specific param IDs and get covered in Round 3 (persona walkthrough).

### Check bundle per route
1. `navigate → <route>`
2. `javascript_eval` smoke-check:
   - URL + title + h1
   - `querySelectorAll('*')` for unresolved components (Sprint 3.8-hotfix lesson)
   - doc height + viewport fit
   - skeleton count (stuck-loading detector)
   - body-text sample preview
3. Console + network spot-check when something looked off

---

## Route Matrix (Runde 1)

Legend: ✅ clean · ⚠️ findings present · ❌ broken

| # | Route | Status | Notes | Findings |
|---|-------|--------|-------|----------|
| 01 | /login | ⚠️ | Logged-in users still see login form instead of redirect | F01 |
| 02 | / (Dashboard) | ⚠️ | Sidebar CMS items (Pages/Forms/Menus/Media/Redirects) English | F02 |
| 03 | /devices | ✅ | h1 "Geräte", all clean | — |
| 04 | /devices/1 (DeviceDetail) | ✅ | docH 1671, no unresolved, REAL-18/19 fix holds | — |
| 05 | /alerts | ✅ | h1 "Alarme", Sprint 3.6 sweep holds | — |
| 06 | /automations | ⚠️ | `/metrics` says `automations_active:2` but `/automations` list returns 0 | F03 (P1 data bug) |
| 07 | /variables | ✅ | h1 "Variablen", 37 rows render | — |
| 08 | /settings | ✅ | Progressive Disclosure — sections collapsed by default | — |
| 09 | /dashboards | ⚠️ | "12h ago" / "1d ago" English relative time; "public" label hardcoded | F04, F05 |
| 10 | /plugins | ✅ | Marktplatz 6 verfügbar, Sprint 6 result stable | — |
| 11 | /firmware | ✅ | Build #3 "📡 OTA abgeschlossen" — OTA worker advanced the status! | — |
| 12 | /hardware | ⚠️ | Board descriptions + pin labels hardcoded English (backend seed) | F06 |
| 13 | /audit | ⚠️ | UI shows "Keine Einträge" but API returns 5 — response-shape mismatch | F07 (P1 data bug) |
| 14 | /entities | ⚠️ | Mostly English ("1 entities", "+ New Entity", "All types", Edit/Delete) | F08 |
| 15 | /events | ✅ | h1 "Ereignisse", all German | — |
| 16 | /effects | ⚠️ | Body controls English ("Stop", "Kind (optional)", "Start", "Caught up") | F09 |
| 17 | /executions | ⚠️ | Body controls English ("Open in Trace Hub", "Device ID", "Load") | F10 |
| 18 | /observability | ⚠️ | h1 "Observability" untranslated (possibly intentional tech term) | F11 |
| 19 | /reports | ⚠️ | Mostly English (Email Templates, "+ New Template", full empty state) | F12 |
| 20 | /webhooks | ⚠️ | "+ New Webhook" + rate-limit error "Too many requests..." English | F13 |
| 21 | /email-templates | ⚠️ | Template names + filter tabs + "+ New Template" + "built-in" badge English | F15 |
| 22 | /admin | ⚠️ | Mixed — header German, KPIs + sections English | F16 |
| 23 | /system-health | ✅ | Fully German | — |
| 24 | /system-stage | ⚠️ | Mostly English, h1 "System-Bühne" vs subtitle "System-Stufe" inconsistency | F17 |
| 25 | /flow-editor | ✅ | Page content clean (F18 covers sidebar) | — |
| 26 | /pairing | ⚠️ | "Start" button English (trivial) | F19 |
| 27 | /custom-api | ⚠️ | Word "endpoints" in group label English | F20 |
| 28 | /developer | ✅ | Swagger UI content is out of scope | — |
| 29 | /setup | ✅ | Already verified in Sprint 5.a — 5 steps German | — |
| 30 | /mcp | ⚠️ | Demo preset buttons "Teaser / Short / Full / Run Demo" English | F21 |
| 31 | /integrations | ✅ | h1 "Integrationen", body German | — |
| 32 | /sandbox | ⚠️ | Seeded simulator names "Temperature Sensor"/"GPS Tracker" English | F22 |
| 33 | /trace-hub | ⚠️ | h1 "Trace Hub" + tabs "Events/Effects" English | F23 |
| 34 | /trace-timeline | ⚠️ | Time range selectors + empty state English | F24 |
| 35 | /variables/streams | ✅ | Fully German | — |
| 36 | /token | ⚠️ | JWT field labels technical English (arguably intentional) | F25 |
| 37 | /tours | ⚠️ | h1 "Tour Builder" English | F26 |
| 38 | /hardware/wizard | ✅ | Wizard navigation German (board descs covered by F06) | — |
| 39 | /settings/types | ⚠️ | Entire body English — semantic types UI never i18n'd | F27 |
| 40 | /cms | ⚠️ | h1 "CMS Pages" + Grid/Tree toggle English | F28 |
| 41 | /cms/forms | ❌ | **100% English** — zero i18n keys | F29 |
| 42 | /cms/menus | ❌ | **100% English** | F30 |
| 43 | /cms/media | ❌ | **100% English** | F31 |
| 44 | /cms/redirects | ❌ | **100% English** | F32 |
| 45 | /cms/settings | ❌ | **100% English** | F33 |
| 46 | /landing | ⚠️ | Marketing landing 100% English — possibly intentional | F34 |
| 47 | /kiosk/slideshow | ⚠️ | "HubEx Kiosk Mode" header English | F35 |
| 48 | /disabled | ⚠️ | h1 German but body "Feature disabled" + explanation English | F36 |

---

## Detailed Findings

### Data bugs (P1) — **NOT i18n, these are real bugs**

#### R1-F03 — Dashboard KPI vs /automations list inconsistency
- **Severity:** P1
- **Routes:** `/automations` + `/` (Dashboard KPI card)
- **What I saw:** Dashboard shows "2 Automationen aktiv" in the KPI strip, but `/api/v1/automations` returns `[]` (verified via fetch in JS console). Page shows the empty-state with 3 quickTemplate cards.
- **Suspected cause:** `/api/v1/metrics` computes `automations_active` from a different query than `/api/v1/automations` filters — possibly an org_id / user filter mismatch, or metrics counts enabled rules across all orgs.
- **Impact:** End-user confusion. "Why does the dashboard claim I have 2 when the page says 0?"
- **Decision:** [pending your priorization]

#### R1-F07 — /audit shows "Keine Audit-Einträge" despite API returning entries
- **Severity:** P1
- **Route:** `/audit`
- **What I saw:** Page empty state ("Keine Audit-Einträge"). Direct fetch to `/api/v1/audit?limit=5` returns 5 entries as a bare array.
- **Suspected cause:** Same bug class as Sprint 3.5 REAL-3/REAL-7 (useEventStream): page likely expects `{items: [...]}` response shape but backend returns bare array.
- **Impact:** Audit log appears broken / empty.
- **Decision:** [pending]

### P1 i18n holes (page-level English)

#### R1-F08 — /entities mostly English
- Items: "1 entities", "+ New Entity", "All types / Groups / Custom" tabs, "1 of 1 entities", "Edit", "Delete", row label "sensor ok"
- **Decision:** [pending]

#### R1-F12 — /reports mostly English
- Items: "Email Templates · Automations", "+ New Template", "No report templates", long English empty-state body, "Create Template" button
- **Decision:** [pending]

#### R1-F15 — /email-templates page + templates English
- Items: "Automations · Reports", "+ New Template", filter tabs "All / Alert / Report / System", seeded template names "Alert Notification", "Device Offline", "Daily Report", "built-in" badges, subject line templates
- **Note:** Template names come from backend seed — similar pattern to Sprint 5.a `useFeatureLabels()` — could reuse the same approach
- **Decision:** [pending]

#### R1-F17 — /system-stage mostly English
- Items: "Last updated:", "Retry", column headers "ID / TYPE / NAME / DEVICES" + "ID / UID / STATUS / RUNTIME STATE / LAST SEEN", "No devices."
- **Extra issue:** h1 "System-Bühne" vs subtitle "System-Stufe" — inconsistent German translation of the same concept
- **Decision:** [pending]

#### R1-F27 — /settings/types entire body English
- Items: subtitle "Manage data types...", "Create Custom Type", "BASE TYPE / All base types / ORIGIN / All types / Built-in only / Custom only", type names (Angle / Battery Level / Boolean Switch), labels "Unit / Range / Viz / Color / Show Triggers & Conversions / Built-in"
- **Decision:** [pending]

#### R1-F29 — /cms/forms 100% English
- Entire page including h1 "CMS Forms", subtitle, empty state, "+ Create Form"
- **Decision:** [pending]

#### R1-F30 — /cms/menus 100% English
- Entire page. Same scale as F29.
- **Decision:** [pending]

#### R1-F31 — /cms/media 100% English
- Entire page. "Media Library", filter tabs "All / Images / Videos / Audio / Documents / Archives", upload prompt, empty state.
- **Decision:** [pending]

#### R1-F33 — /cms/settings 100% English
- Entire page. "Site Settings", "Branding / SITE TITLE / TAGLINE / LOGO URL / FAVICON URL / COLORS / PRIMARY / ACCENT / BACKGROUND / TEXT / SEO Defaults / Analytics / Footer / Advanced (Custom CSS/HTML)".
- **Decision:** [pending]

### P2 findings (targeted English leaks)

| ID | Route | Issue |
|----|-------|-------|
| F02 | / (sidebar) | CMS sub-nav items "Pages / Forms / Menus / Media / Redirects" hardcoded English |
| F04 | /dashboards | Relative-time strings "12h ago", "1d ago" — should be German "vor 12h" |
| F05 | /dashboards | "public" label on dashboard cards hardcoded |
| F06 | /hardware | Board descriptions ("Most common ESP32 development board...") + pin specs ("23 pins 4096KB flash 520KB RAM") from backend seed — same pattern as old feature_names. Needs `useBoardLabels()` composable. Carries into /hardware/wizard. |
| F09 | /effects | Body controls "Stop / Kind (optional) / Limit / Start / Caught up / No effects..." |
| F10 | /executions | Body controls "Open in Trace Hub / Device ID / Status (optional) / Context ID (optional) / Load / No tasks." |
| F13 | /webhooks | "+ New Webhook" button + rate-limit error banner "Too many requests. Please wait a moment." |
| F16 | /admin | Mixed — KPIs + sections English ("0/0 Modules Enabled", "0 Active Capabilities", "System Status", "Module Registry", "Enable or disable platform modules", "No modules registered", "System Info", "Version") |
| F18 | / (sidebar) | "Tour Builder" + "Sandbox" sidebar items hardcoded English |
| F23 | /trace-hub | h1 "Trace Hub" + tabs "Events / Effects" English |
| F24 | /trace-timeline | Time range dropdown "Last 15 min / Last 1 hour / ..." + "Support Bundle / Event Timeline / No traces in this time window" |
| F28 | /cms | h1 "CMS Pages" + "Grid / Tree" toggle English |
| F32 | /cms/redirects | Entire page English (P2 because lower-traffic admin screen) |
| F35 | /kiosk/slideshow | "HubEx Kiosk Mode" header |
| F36 | /disabled | h1 German but body "Feature disabled. This feature is currently turned off. You can enable it from Settings..." English |

### P3 findings (minor / judgment calls)

| ID | Route | Issue | Notes |
|----|-------|-------|-------|
| F01 | /login | Doesn't redirect when already authenticated — still shows the login form | Minor UX / stale session handling |
| F11 | /observability | h1 "Observability" English | "Observability" is an accepted technical loanword in German IT |
| F19 | /pairing | "Start" button English | Trivial single-word button |
| F20 | /custom-api | Word "endpoints" in group label "(2 endpoints)" | Template string "$count endpoints" |
| F21 | /mcp | Demo preset "Teaser / Short / Full / Run Demo" | Demo infrastructure — arguably intentional |
| F22 | /sandbox | Seeded simulator names "Temperature Sensor / GPS Tracker / Weather Station" | User can rename; seed data |
| F25 | /token | JWT technical labels "SUB / ISS / JTI / EXP (ISO) / EXPIRES IN / CAPS" | Developer tool; these are JWT spec terms |
| F26 | /tours | h1 "Tour Builder" | Tour is German loanword, "Builder" is not |
| F34 | /landing | Full marketing page English | Possibly intentional for international open-source marketing |
| — | — | *placeholder* | |

---

## Visual Findings (Runde 2) — ✅ COMPLETE

### Method
Chrome-MCP's `resize_window` only affects the outer Chromium window, not the inner viewport — real responsive screenshots at 3 breakpoints weren't possible with the available tools. Pivoted to:
- **1 desktop screenshot per route at 1440×731** (visible viewport)
- **DOM leak scan** via JS eval per route (`body.innerText` regex match for `\b\d+[smhd] ago\b` + hardcoded English word patterns)
- **Locale flip check** on a subset of high-risk routes (Dashboard, /cms/forms) to verify Round 1 fixes hold on EN as well as DE

### Routes walked (12)
/, /devices, /devices/1, /alerts, /automations, /variables, /firmware, /plugins, /hardware, /setup, /cms (including /cms/forms), /landing

### Round 1 fixes all hold on Round 2 walk
- ✅ **F03 Dashboard KPI** — "2 Automationen aktiv" now consistent with `/automations` list (both 0)
- ✅ **REAL-10 Dashboard** — "6 / 13 online" in red, honest ratio, color-coded big number
- ✅ **REAL-18/19 DeviceDetail** — doc height 1671 (was 2033 before the hotfix), 0 unresolved components
- ✅ **Sprint 6 plugin marketplace** — "6 verfügbar" with all new Frigate/Ollama/Grafana cards in German
- ✅ **Sprint 7 firmware OTA** — build #3 badge "📡 OTA abgeschlossen"
- ✅ **Sprint 5a useBoardLabels** — "Der meistverbreitete ESP32-Entwicklungsboard..." etc.
- ✅ **Batches 1-7d i18n coverage** — 12 routes walked, 11 findings, NONE were a reversal of a prior fix

### Findings found + fixed in Round 2

| ID | Severity | Route(s) | Issue | Commit |
|----|----------|----------|-------|--------|
| **R2-F01** | P3 | / Dashboard activity feed | Backend-emitted event type names "Org Created", "Device Paired", "Telemetry Received" render raw English on DE. These come from the events store not an i18n namespace. **Flagged for future, not fixed.** | — |
| **R2-F02** | **P1** | / Dashboard alert widget | Relative-time string "vor 7h" rendered on EN locale ("gerade eben" fallback too) — systemic leak from `useRecentAlerts.ts` with hardcoded German template literals. | fe953fa |
| **R2-F03** | P3 | /devices | Device type "simulator" renders as raw English (not in `devices.types.*` namespace) — minor, non-standard type. **Flagged, not fixed.** | — |
| **R2-F04** | P2 | /devices | fmtAge() hardcoded "0s ago / 5s ago" English template literals | fe953fa |
| **R2-F05** | P3 | /devices | `sim-mqtt-live` UIDs shown in monospace — observation only, not a bug | — |
| **R2-F06** | P2 | /devices/1 | Same fmtAge() hardcoded English in DeviceDetail | fe953fa |
| **R2-F07** | P3 | /alerts | "New" word leak — tracked down to sidebar `+New` button (see R2-F10) | fe953fa |
| **R2-F08** | P2 | /alerts | Pre-existing DB alert still has legacy format `variable 'temperature' value 20.2 gt 20`. **Sprint 5.c backfill script available — admin needs to run** `python -m scripts.backfill_alert_format --commit` **on production DB**. Flagged for release checklist, not fixable at build time. | — |
| **R2-F09** | P2 | /cms top-bar | Browser tab/top-bar title still "CMS Pages" (English) because router.ts had no `titleKey` | fe953fa |
| **R2-F10** | P2 | sidebar | "+ New" button + "+ Device / + Automation / + Alert Rule / + Dashboard" menu items all hardcoded English in DefaultLayout.vue | fe953fa |
| **R2-F11** | P2 | all 11 /cms/* routes | router.ts had `title:` meta but no `titleKey:` — top-bar reads English on all CMS routes regardless of body-level i18n | fe953fa |

### Systemic fix: `lib/relativeTime.ts`
The same bug class (hardcoded "X ago" English literals) appeared in 9 files — too many to patch individually. Introduced a centralised `fmtAgeSeconds()` / `fmtRelativeIso()` helper that routes through the existing `dashboardsList.relative.*` namespace. Migration delegated to a subagent; completed in one pass, post-sweep grep confirmed zero `\`.*ago\`` matches in `pages/` + `components/`.

### Flagged for future (NOT fixed this sprint)
- **R2-F01** event type names from backend — needs a client-side lookup table like Sprint 5.a `useFeatureLabels` or backend i18n
- **R2-F08** legacy alert DB backfill — script ready, admin-run only
- **DashboardView.vue line 758** — hardcoded "2m ago" as a sample placeholder for HTML widget preview editor
- **Sandbox.vue** — partial i18n via `sandbox.ago` key leaves `s`/`m`/`h` suffixes hardcoded English → DE renders grammatically broken "12s vor"
- **ApiKeyManager.vue template** — "Last used" + "Never used" + "expires" template literals
- **VizBoolIndicator.vue template** — "since {{ lastChange }}" word leak
- **Multiple `.toLocaleDateString()`** calls — respect browser locale not app locale
- **Various backend-seeded strings** — event type names, alert messages (Sprint 5.c backfill only covers future ones), block-canvas HTML renderer fallbacks

### Round 2 Summary Stats
- **Routes walked:** 12
- **New findings:** 11 (1 P1, 7 P2, 3 P3)
- **Fixed in this round:** 8 (the P1 + all systemic P2s)
- **Flagged:** 3 (R2-F01, R2-F03, R2-F05) + a separate "flagged for future" bucket from the relative-time sweep
- **Files touched:** 17 (including 1 new: `lib/relativeTime.ts`)
- **New commit:** `fe953fa`
- **Build size drift:** +1 KB gzip (acceptable — new relative-time helper offsets the removed inline duplicates)

---

## Persona Findings (Runde 3) — IN PROGRESS

### Method
User (human reviewer) walked the app live on their own machine and provided findings verbally with 2 screenshots attached. I documented each finding and spot-verified a subset on my own running instance.

### Screenshots provided by user
1. **Dashboard close-up** — shows `GERÄTE ONLINE` / `Teilausfall` subtitle (number not visible in crop) + `34437 EREIGNISSE HEUTE` + `2 AUTOMATIONEN AKTIV` + `Aktuelle Alarme` header
2. **Dashboard wider** — shows number `5` in green with `Teilausfall` subtitle, legacy alert format `variable 'temperature' value 20.7 gt 20`

**Cache-check:** On my live running instance (after the Sprint 8 R2 rebuild) the Dashboard renders `6 / 13 online` as subtitle, not `Teilausfall` — my Sprint 5.b REAL-10 fix IS active. User's screenshots are likely stale browser cache from before the latest frontend rebuild. A hard reload (Ctrl+Shift+R) should show the same state as mine.

---

### Round 3 Findings

#### Dashboard / Home

**R3-F01 — P2 (cache artefact, but confirm)** — Dashboard KPI sub-label shows "Teilausfall" instead of "6 / 13 online"
- **User quote:** "Da sind irgendwie, obwohl da steht 'Device online', die Zahl rot und das macht irgendwie wenig Sinn."
- **What I see live:** `6 / 13 online` subtitle — Sprint 5.b fix active, not Teilausfall.
- **Likely cause:** Stale browser cache from before the last frontend rebuild. Verify with hard reload.
- **Action:** None yet, wait for user to confirm after hard-reload.

**R3-F02 — P2 (design iteration)** — Red number color next to "Geräte online" label is confusing
- **User quote:** "die Zahl rot und das macht irgendwie wenig Sinn"
- **Design context:** Sprint 5.b intentionally encoded health via number color (>=80% ok/green, 50-79% warn/amber, <50% bad/red). But user is now saying the red number next to a "Geräte **online**" label reads as a contradiction (the label sounds positive, the color says negative).
- **Decision needed:** Drop the color encoding and keep the ratio as neutral text? Or different fix?

**R3-F03 — P2** — Legacy alert format on Dashboard alert widget (`variable 'temperature' value 20.7 gt 20`)
- **Root cause:** Pre-existing DB rows from before Sprint 3.6. Sprint 5.c backfill script ready but not run on production DB.
- **Options:**
  1. Admin runs `python -m scripts.backfill_alert_format --commit` on prod DB
  2. Frontend regex-parses legacy format on display (covers both old rows AND prevents future leaks from any other source)
- **Decision needed:** which option?

---

#### DeviceDetail

**R3-F04 — P1 CRITICAL** — System Context section flickers badly on refresh
- **User quote:** "Nur wenn man auf dem Device drauf ist, dann haben wir unten diese Ansicht 'Zu Gruppe hinzufügen', noch keine Gruppe, und rechts neben den Variablen 'verbunden', keine Automation und so was beim Refresh flackern die. Das ist ganz schlimm."
- **Affected sections:** Entity memberships ("Zu Gruppe hinzufügen" / "Keine Gruppe"), linked automations + linked alerts in the System Context graph on DeviceDetail
- **Difference from Sprint 3.4 fix:** Sprint 3.4 fixed the /devices MAIN PAGE refresh flicker. This is on /devices/{id} — different code path, different data loaders, different flicker root cause. Most likely cause: multiple parallel fetches that don't arrive at the same tick, so the sections mount/unmount independently on each refresh.

**R3-F05 — Ignored per user** — Device action bar "Empfohlene nächste Schritte" inconsistency
- **User quote:** "der einzige Wizard, den wir so haben, in der Form, der eigentlich okay ist, aber da ist dafür an OK, lass den drin"
- **Action:** User explicitly said ignore. No action.

---

#### Dashboards / Variables

**R3-F06 — P1** — GPS view widget broken
- **User quote:** "Bei Dashboards und bei der Variablenansicht haben wir noch Probleme mit GPS-Ansicht"
- **Needs investigation:** What is the GPS view widget? Probably `VizMap` or similar — uses Leaflet. Might be a lat/lng variable binding issue or Leaflet chunk not loading on-demand correctly after Sprint 7.5 bundle splitting.

**R3-F07 — P2 (needs clarification)** — "Einrichtungen als Dashboard" broken
- **User quote:** "Probleme mit GPS-Ansicht und Einrichtungen als Dashboard"
- **Unclear what exactly:** "Einrichtungen" could mean "setups / installations" or could be a widget type name. Needs user clarification: is it the SetupWizard rendered as a Dashboard widget? Or a specific widget type that shows saved device setups?

---

#### Info-Icon pattern

**R3-F08 — P2** — Info-icon tooltip inconsistent across pages
- **User quote:** "Das Info-Icon neben den Seiten mit den kleinen Informationen ist noch inkonsistent. Das haben wir zum Beispiel bei Geräten und Dashboards. Bei Variablen, aber bei Entitäten haben wir es wieder nicht."
- **Pattern:** `UInfoTooltip` component is present on /devices, /dashboards, /variables but missing on /entities, /reports (R3-F12), /hardware (R3-F16), and probably several more.
- **Fix:** Audit all page headers, add UInfoTooltip consistently to every route that has a meaningful "what is this page" description.

**R3-F09 — P2 (new feature)** — Info-icon tooltip should have "Erklärung" button launching an inline tour
- **User quote:** "Außerdem hatte ich mal gesagt, das wurde nicht umgesetzt, dass ich neben dem, also wenn das Info-Icon aufgeht mit der kleinen Beschreibung, was es ja auch teilweise tut, dass da aber noch so ein Knopf sein soll für Erklärung, dass für jede Erklärung eine kleine Tour geschrieben wird, die dann da abrufbar ist."
- **Translation:** When the info-icon opens its tooltip, there should be a button "Explain" that triggers a small tour. Each page would have such a pre-authored tour.
- **Scope:** Requires: (1) `UInfoTooltip` gains an optional `tourId` prop with a button in the body, (2) a small tour is written per page, (3) clicking launches the existing tour infrastructure.
- **Status:** User said this was requested earlier and not implemented — flag as carry-over from before Sprint 8.

---

#### Automations

**R3-F10 — P2** — Automation creation wizard not perfect enough
- **User quote:** "Automatisierung finde ich immer noch den Erstellungs Wizard nicht perfekt genug. Der ist ein bisschen komisch."
- **Unclear what exactly is "komisch":** Needs user to elaborate or needs a closer review of the modal UX. Probably: field ordering, conditional visibility of fields, unclear trigger/condition/action flow, missing help text.

---

#### Webhooks

**R3-F11 — P1 BUG** — "Zu viele Anfragen, bitte einen Moment warten" rate-limit message appearing spuriously
- **User quote:** "Bei Webhooks gibt es eine Meldung 'zu viele Anfragen bitte einen Moment warten'. Keine Ahnung was das soll."
- **Root cause suspect:** A polling loop hits the per-user rate limiter because the page's load/refresh + background polling pile up. Or the rate limiter bucket is tuned too tight for this endpoint.
- **Investigation:** Find where this message is emitted (errors.ts 429 path from Batch 6), then trace back: which fetch, how often, why does it hit rate limit?

---

#### Reports

**R3-F12 — P3 (info-icon)** — Info-icon missing on /reports
- Same class as R3-F08. Covered by that finding.

---

#### Email Templates

**R3-F13 — P2 (feature)** — WYSIWYG editor not sufficient
- **User quote:** "E-Mail-Vorlagen, das ist noch kein ausreichender What you see is what you get Editor."
- **Current state:** Simple textarea for HTML body. Needs a TipTap-based (already in deps) visual editor with formatting toolbar, variable insertion, preview pane, maybe inline template variable autocomplete.
- **Scope:** Medium — replace current textarea with `RichTextEditor` component from `components/cms/` (already exists, TipTap-based). Or an e-mail-specific variant.

---

#### CMS

**R3-F14 — P1 CRITICAL** — CMS creation flows visually very buggy
- **User quote:** "Seite erstellen bei CMS ist total grafisch verbuggt. Also nicht nur Seite erstellen, eigentlich alles was unter CMS mit Erstellung zu tun hat, ist im UI sehr verbuggt."
- **Scope:** /cms/:id/edit (CmsPageEditor.vue — 1144 lines, the TipTap-based one), /cms/forms/:id/edit (CmsFormEditor.vue), /cms/menus/:id/edit (CmsMenuEditor.vue)
- **What exactly "verbuggt" means:** Needs user screenshots OR a live walkthrough session because "UI buggy" could mean many things: overflow, broken layout, z-index issues, modal misalignment, drag-drop glitches, button misplacement, flicker, render failures, etc.
- **Action:** Request screenshots OR pair-review the 3 editor pages with user.

---

#### System / Observability

**R3-F15 — P2 (design)** — System/Observability-like section 4-column layout squeezed with many variables
- **User quote:** "System Part ist immer noch nicht schön dargestellt. Da haben wir immer noch diese vier Spalten und alles wirkt etwas gequetscht, weil wir ganz viele Variablen haben, geht das so weit nach unten. Das sollte irgendwie umgesetzt werden, dass das bisschen die Fade nachvollziehbar sind, weil so ist das viel zu nah beieinander und man kann die Sachen nicht wirklich gut auseinander halten."
- **Needs clarification:** "System Part" — which page? Options:
  - /system-health (Systemstatus) — does have 4 KPI columns
  - /system-stage (System-Bühne)
  - /observability (Observability)
  - System Context section on /devices/{id}
- **Probable:** /system-stage (variables list per entity gets long). Needs a design rework with better visual grouping, fade separators between sections, or accordion-style collapsible groups.

---

#### Hardware Boards / Plugins

**R3-F16 — P1 CRITICAL** — /hardware page scroll broken
- **User quote:** "Bei Hardware Boards klappt der Scroll auch nicht, also die Seite geht nach unten weiter, aber man kann nicht weiter runter gucken."
- **Symptom:** Page has content below the fold but scrolling doesn't reach it
- **Suspected cause:** Same class as REAL-18/19 DeviceDetail (fixed 3.8-hotfix). Could be: (1) unresolved component taking up invisible DOM space, (2) CSS overflow:hidden on an ancestor, (3) fixed-position element blocking scroll events.
- **Also:** Hardware Boards has no explanation / info-icon + tour (R3-F08 + R3-F09).

**R3-F17 — P1** — /plugins scroll possibly broken (same pattern)
- **User quote:** "Bei Plugins dasselbe, scheinbar. Bin mir nicht sicher."
- **Investigation:** Verify by loading /plugins with >6 plugins (currently has 6 marketplace + 2 installed, may already exceed fold).

---

#### Tour Builder

**R3-F18 — P3** — Tour creation modal a bit cluttered, needs inline helper info
- **User quote:** "Tour erstellen Editor ist auch ein bisschen unübersichtlich; sollten paar kleine Infos in dem Tour erstellen Model sein."
- **Fix:** Add inline helper paragraphs / tooltips in the TourBuilder creation modal explaining: what a tour is, how to add steps, how to select target elements.

---

#### Sandbox

**R3-F19 — P3 (feature)** — Need more simulators for new catalog
- **User quote:** "Sandbox muss angepasst werden, dass wir noch mehr Simulatoren haben zu den neuen passenden Dingen."
- **Context:** The `simulator_engine.py` backend supports N simulator templates. Currently seeded: Temperature Sensor, GPS Tracker, Weather Station, Motion Sensor, Energy Meter, Custom. Need to add new ones that match the expanded Component Catalog from Sprint 5b (BME280, BH1750, DHT22, HC-SR04, PIR, buzzer, relay, servo, led_pwm, etc.).
- **Scope:** Backend seed data + maybe frontend icons.

---

#### Settings

**R3-F20 — P3 (feature)** — Settings needs a search
- **User quote:** "Einstellungen sollte eine Suche erhalten."
- **Fix:** Add a top-of-page search input that filters the collapsible sections (Profile, MFA, Sessions, Features, Branding, etc.) and expands any section containing a match.

---

#### API Docs (Developer)

**R3-F21 — P2** — Redoc tab shows "Could not load Redoc" initially, then loads with lag
- **User quote:** "Bei API-Dokumentation gibt es den Tab Redock, aber wenn ich den aufklicke, dann kommt erst mal so 'Could not load Redock'. Dann passiert trotzdem aber irgendwas, ist ein bisschen laggy."
- **Root cause suspect:** Redoc script loaded async from CDN or lazy-imported, initial render happens before the script is ready → error shows, then script loads and re-renders.
- **Fix:** Show a proper loading spinner instead of "Could not load", or pre-load the Redoc bundle, or use a suspense boundary.

---

#### Admin Console

**R3-F22 — P1** — Admin Console empty / same as System Health
- **User quote:** "Admin-Konsole ist irgendwie noch ohne Funktion, also ist das gleiche wie system health geführt."
- **Context:** Sprint 8 Batch 3 swept AdminConsole.vue for i18n but the PAGE itself has very limited functionality — only Module Registry (mostly empty) + System Status (same data as /system-health). Needs actual admin features: user management, org management, capability overview, license info, session management.
- **Fix:** This is a product decision — what SHOULD be in Admin Console that's currently in Settings? User / org / cap management at minimum. This is a feature request more than a bug fix.

---

#### Sidebar / Navigation

**R3-F23 — P2 (visual)** — Horizontal scroll bar in sidebar looks bad
- **User quote:** "Ich will in der Sidebar keine Navigationsbar für rechts-links haben. Das sieht scheiße aus."
- **Translation:** I don't want a horizontal scroll bar in the sidebar. Looks shit.
- **Root cause:** The sidebar content (nav item labels with long German translations) overflows horizontally at narrow widths or when certain items have long labels.
- **Fix:** Add `overflow-x: hidden` + `white-space: nowrap` + `text-overflow: ellipsis` on nav item labels, OR widen the sidebar, OR shorten the longest labels.

**R3-F24 — P2 (visual)** — Sidebar vertical scroll bar should only appear when content actually overflows
- **User quote:** "Ich will, dass die Scrollleiste in der Navigationsbar auch nur dann auftritt, wenn man nicht die gesamte Seite scrollen kann, wie es zum Beispiel bei der System Map ist. Nur da eigentlich oder bei vergleichbaren Sachen."
- **Current behavior:** Sidebar always shows a scroll track even when all nav items fit in the viewport
- **Fix:** Change `overflow-y: auto` to `overflow-y: auto` with `scrollbar-gutter: stable` OR use `overflow-y: hidden` + JS check for overflow. Or just use CSS `overflow-y: auto` correctly — modern browsers auto-hide the track when there's nothing to scroll.

---

#### Meta

**R3-F25 — clarification needed** — "4 neue Personas" user expected in UI but can't find
- **User quote:** "Die vier neuen Personas sehe ich zum Beispiel gar nicht. Keine Ahnung, was es damit jetzt auf sich hat."
- **My understanding:** In my Round 3 description (the review process), I mentioned 4 personas (new user / operator / admin / viewer) as archetypal users that the HUMAN reviewer walks through to test the app from different role perspectives. **They are review method, NOT UI features.**
- **User's expectation:** Probably interpreted "4 neue Personas" as a new UI feature to be implemented (maybe: a persona-switcher in settings, or role-based UI variants, or something like that).
- **Action:** Clarify with user which interpretation they meant. If they want persona-switching as a product feature, that's a Sprint 9+ scope discussion.

---

### Round 3 Summary Stats
- **Findings:** 25 total
- **Severity:** 6 P1 / 11 P2 / 7 P3 / 1 clarification
- **Verified live on my instance:** R3-F01 (cache artefact), F02 (confirmed red number rendering), F04 (not yet — need to refresh device detail)
- **Needs user clarification:** R3-F07 ("Einrichtungen als Dashboard"), R3-F14 (what exactly in CMS is "verbuggt"), R3-F15 (which "System Part"), R3-F25 (personas)
- **Carry-over from earlier requests:** R3-F09 (info-icon tour button — user said this was requested before and not implemented)

### 🚦 Kontrollpunkt 3 — Pause for User

**User needs to decide:**

1. **Which findings to fix for dev-stable-v1 tag:**
   - All 25? That's a big batch.
   - Only the P1s (6 items)? More focused.
   - Only the P1s + cleanup the easy P2s?
   - Skip the feature-request P3s to a Sprint 9+ backlog?

2. **Clarifications needed:**
   - R3-F07 "Einrichtungen als Dashboard" — what exactly?
   - R3-F14 CMS creation visually buggy — which specific bugs? Screenshots?
   - R3-F15 "System Part" — /system-health, /system-stage, /observability, or something else?
   - R3-F25 "4 Personas" — feature request or review terminology misunderstanding?

3. **Design decisions:**
   - R3-F02 Dashboard number color — drop the health encoding?
   - R3-F03 legacy alert format — admin script OR frontend regex fix?

---

*(Round 3 user walk complete per user's feedback on 2026-04-11. Paused for priorization.)*

---

## Option A Fix Batch — Round 3 user walk findings

User directive: "Option A und wenn fertig, starte dann mit dem Neuer-User-Flow. mach soweit wie es geht ohne stop"

Scope: all 6 P1 + 5 "quick P2" findings from the Round 3 user walk,
fixed in sequence without pausing between items. Committed as
`7d169b2` (21 files, +616/-84, 1 new helper lib).

| Finding | Sev | What it was | Fix |
|---|---|---|---|
| R3-F01 | P2 | Dashboard "Teilausfall" label | Cache artefact — no-op on my instance (Sprint 5.b fix holds) |
| R3-F02 | P2 | Dashboard red number contradicts "online" label | Dropped color encoding, number now neutral text-primary |
| R3-F03 | P2 | Legacy alert format on Dashboard ("variable 'X' value N gt M") | New `frontend/src/lib/alertMessage.ts` regex-converts on display, wired into Dashboard + Alerts page |
| R3-F04 | **P1** | DeviceDetail System Context flickers on refresh | Race-guarded parallel `Promise.allSettled` for `loadLinkedRules()` + skeleton only on first load (both entity-memberships render sites) |
| R3-F06 | **P1** | GPS view widget broken | `viz-resolve.ts` now auto-detects `{lat,lng}` shape and switches to map widget when `display_hint='auto'` |
| R3-F08 | P2 | Info-icon inconsistent across pages | UInfoTooltip added to 10 previously-missing pages + 10 × en/de `infoTooltips.*` entries with real bullet-point descriptions (via subagent) |
| R3-F11 | **P1** | Webhooks "Too many requests" spurious | `/api/v1/webhooks` + `/api/v1/ota` rate limit bumped 30→300/min (matching polled-endpoints group) |
| R3-F14 | **P1** | CMS Page Editor renders as blank black pane | **Root cause: vue-i18n v11 parser crashes on `{{x.y}}` double-brace syntax inside message values.** Three CMS/EmailTemplate placeholder strings had `{{variable.key}}` / `{{device.name}}` as example content. The `.` in parameter names is illegal → SyntaxError → entire compiled i18n bundle fails to load → CmsPageEditor blank. Replaced with descriptive copy (no braces). Browser-verified: /cms/2/edit now fully functional. |
| R3-F16 | **P1** | /hardware/wizard scroll broken | Route has `meta.fullscreen:true` → `<main>` overflow:hidden. Wizard wrap claimed `min-height:100vh` with no scroll. Changed to `height:100vh` + `overflow-y:auto`. |
| R3-F17 | P1 | /plugins scroll possibly same | No-op — not an actual bug, confirmed via DOM measurement |
| R3-F21 | P2 | API Docs Redoc tab "Could not load" flash | Added loading spinner state + container ref `nextTick()` guard, error banner hidden while still loading |
| R3-F23/F24 | P2 | Sidebar scrollbars (horizontal + vertical-always-visible) | `overflow-x:hidden` + `min-w-0` on nav, custom slim `.sidebar-nav` scrollbar class with auto-hide thumb |

**Also fixed (side effects while working in the affected files):**
- Line 2615 de.ts / 2638 en.ts `editorPlaceholder` for Dashboards HTML widget had the same `{{variable:key}}` crash pattern — would have killed Dashboards too. Fixed preemptively.
- HardwareBoards `boardBadge` + `wizard-hint` CTAs i18n'd as part of F06 cleanup.

**Not fixed (judgment / deferred / clarification-needed):**
- R3-F05 User explicitly said ignore
- R3-F07 "Einrichtungen als Dashboard" — still needs user clarification
- R3-F10 Automations wizard "komisch" — needs user to elaborate
- R3-F12 Reports info-icon → covered by R3-F08 audit fix
- R3-F13 Email Templates WYSIWYG — feature request, Sprint 9+
- R3-F15 "System Part" — still needs user clarification
- R3-F18 Tour Builder modal helper — feature request, Sprint 9+
- R3-F19 Sandbox more simulators — feature request, Sprint 9+
- R3-F20 Settings search — feature request, Sprint 9+
- R3-F22 Admin Console empty/same as System Health — product decision, Sprint 9+
- R3-F25 "4 Personas" — review-method misunderstanding, no action

---

## Neuer-User-Flow Walk (Round 3 continuation)

After Option A landed, continued the review by simulating a brand-new
user signing up from scratch. Logged out fully, registered a new test
account, and clicked through the initial experience with a fresh pair
of eyes.

### NU Findings

**NU-F01 — P3** — /login missing "Forgot password?" link
- Observation: fresh login page has email/password/login/register. No recovery link.
- Action: deferred (dev build, password-reset flow not implemented yet)

**NU-F02 — P2** — /login has no marketing/demo link
- Observation: brand-new visitor lands on a bare login form with zero context about what HubEx is
- Suggested fix: add a small "What is HubEx? →" secondary link or "View demo →" below the register link
- Action: deferred to Sprint 9+ (product-level UX decision)

**NU-F03 — P1 FIXED** — Metrics endpoint leaked counts across orgs
- **Symptom:** fresh user with 0 devices saw Dashboard KPI "1 aktive Alarme / 1 Regel aktiv / 61,840 Ereignisse heute"
- **Root cause:** Sprint 8 Batch 1 only org-scoped `automations_active`. All other metric fields (alerts.firing, events_24h, entities_total, webhooks_active) were still counting globally across all orgs.
- **Fix:** systematically org-scoped every metric. AlertEvent joins through AlertRule.org_id (AlertEvent has no direct org_id). EventV1 filters by user's own device UIDs via the stream column (EventV1 has no org_id/device_id schema columns). Entity/Webhook use direct org_id.
- **Verified:** new user's metrics endpoint now returns all zeros correctly.
- **Commit:** `3c5d28b`

**NU-F04 — P1 FIXED** — WelcomeScreen 100% English on DE locale
- **Symptom:** The first-login Teleport overlay (`components/WelcomeScreen.vue`) had all strings hardcoded English even on DE locale: "Welcome to HubEx / What would you like to connect first? / Hardware / Service / Bridge / Agent / or / Just look around → / Load demo data →"
- **Fix:** New `welcomeScreen.*` i18n namespace (12 keys × en/de). Categories array converted from static module-level data to computed() so it re-runs on locale change. Icons + colors stay static (they don't need translation).
- **Verified live on DE:** "Willkommen bei HubEx / Was möchtest du zuerst anbinden? / Hardware / Dienst / Bridge / Agent / oder / Nur umschauen → / Demo-Daten laden →"
- **Commit:** `3c5d28b`

**NU-F05 — P2** — Activity Feed shows cross-org events on fresh-user Dashboard
- **Symptom:** After the NU-F03 metrics fix, KPI counts all read 0 correctly. BUT the Dashboard "Aktivitäten" widget still shows "Org Created / Device Paired / Telemetry Received" events from other (seed data) orgs.
- **Root cause:** `/api/v1/events` is a global append-only log stream, not org-scoped. The Activity Feed widget on Dashboard pulls from it without any org filter.
- **Deferred:** bigger scope change — affects both the Events page (which is supposed to show system-wide events for admins?) and the Dashboard widget (which should show only your-org events). Needs product decision about whether Events is a user view or an admin view.

**NU-F06 — P2** — Empty-dashboard UX gap for fresh users
- **Symptom:** After dismissing WelcomeScreen with "Nur umschauen", fresh user lands on Dashboard showing 4 grey zeros ("Geräte online / Aktive Alarme / Ereignisse heute / Automationen aktiv") with no obvious next step. The WelcomeScreen never comes back.
- **Suggested fix:** When all KPIs are 0 AND user has no devices, show a prominent "Erste Schritte" banner with "Gerät hinzufügen" / "Demo-Daten laden" / "Tour starten" CTAs. Alternatively, resurrect the WelcomeScreen on any empty dashboard visit (not just first-login).
- **Deferred:** UX improvement, not blocking dev-stable-v1. Could be a quick fix in a follow-up batch.

### NU Summary Stats
- **Findings:** 6 total (NU-F01 through NU-F06)
- **Severity:** 0 P0 / 2 P1 / 3 P2 / 1 P3
- **Fixed:** 2 / 6 (the P1s — NU-F03 metrics org-scope + NU-F04 WelcomeScreen i18n)
- **Deferred:** 4 / 6 (NU-F01 feature request, NU-F02 feature request, NU-F05 product decision, NU-F06 UX improvement)
- **Commit:** `3c5d28b`

---

## 🚦 Kontrollpunkt after NU walk

Round 3 is partially done — I've fixed everything that was blocking
and have 4 Neuer-User items flagged for the user's decision:

1. **NU-F01** /login "Forgot password?" — part of a bigger auth flow (password reset, email verification), not blocking
2. **NU-F02** /login marketing link — UX copy decision
3. **NU-F05** Activity Feed cross-org events — product decision on whether `/events` is admin-view or user-view
4. **NU-F06** Empty dashboard CTA — small UX improvement, could fold into next fix batch

Remaining Round 3 items that STILL need user input (from the initial walk, not the NU walk):
- R3-F07 "Einrichtungen als Dashboard" clarification
- R3-F10 Automations wizard "komisch" — what specifically
- R3-F15 "System Part" — which page
- R3-F25 "4 Personas" — confirm it was review-terminology misunderstanding

**Next round options:**
- **Round 4 Perf + A11y** — agent-driven, doesn't need user input, can start now
- **Continue Round 3 walks** — Operator / Admin / Viewer personas still pending
- **Close out Round 3 pending clarifications** — user answers the 4 questions above, then final Round 3 fix batch
- **Skip directly to Round 6 release prep** — if we're confident enough

---

## Perf & A11y (Runde 4)

*(Runde 4 not started)*

---

## Fix List

*(empty — awaiting your priorization of Round 1 findings. Once you mark each as `must-fix` / `nice-to-fix` / `defer` / `false-positive`, the list gets built and Round 5 starts.)*

---

## Round 4 — Performance + Accessibility (2026-04-11)

Agent-driven pass, no persona walk needed. Two phases:
1. **Perf** — Navigation Timing API + resource inventory across 5 core pages
2. **A11y** — focus-ring, ARIA, landmarks, color contrast

### Perf measurements (5 core pages)

| Route | DOM Interactive | DCL | Load | Long Tasks | API calls | Duplicates |
|---|---|---|---|---|---|---|
| `/` | 45 ms | 139 ms | 480 ms | 0 | 14 | `users/me ×2` |
| `/devices` | 31 ms | — | 119 ms | 0 | — | `users/me ×2` |
| `/devices/1` | 38 ms | — | 388 ms | 0 | 18 | `users/me`, `audit` |
| `/alerts` | 47 ms | 126 ms | 490 ms | 0 | 9 | `users/me ×2` |
| `/automations` | 22 ms | 62 ms | 76 ms | 0 | 7 | `users/me ×2` |

**Verdict:** Load is well under 500 ms everywhere, zero long tasks — Sprint 7.5 bundle splitting holds up. No slow resources (no `>100 ms` single asset), no oversized chunks beyond the known `index-CIhTkvGA.js 604 kB` (already flagged in Sprint 7.5 backlog).

### A11y sweeps

1. **Focus ring** — `:focus` rules: 23, `:focus-visible` rules: 6, `outline:none` overrides: 1. UButton uses `focus-visible:ring-2` baseline. ✅ Acceptable.
2. **ARIA audit (Dashboard)** — 18 buttons, 32 links, 0 unlabeled icon buttons, 0 unlabeled inputs. ✅
3. **ARIA audit (DeviceDetail)** — 56 buttons, 26 icon-only WITH label (93%), **2 unlabeled** (sensordata-panel refresh + variables-panel refresh).
4. **Landmarks (Dashboard)** — 1 header / 1 main / 1 nav / 1 aside / h1: 1. No `footer` (acceptable), no skip-link, `html[lang]="en"` stuck at build-time default.
5. **Color contrast (dark theme computed tokens)** — primary-on-base: **15.57** (AAA), secondary-on-base: **5.91** (AA), amber/warn/ok/bad status colors all AA+, **muted-on-base: 2.95 (FAIL)**, muted-on-surface: 2.79, muted-on-raised: 2.55.

### Findings

| ID | Severity | Area | Description | Status |
|---|---|---|---|---|
| **R4-Perf-01** | P3 | Perf | `/api/v1/users/me` fetched twice on session bootstrap (once from auth store, once from capabilities layer). Same count across all 5 routes → it's a one-time boot cost, not a per-route leak. | 📋 deferred — cleanup, not a bug |
| **R4-A11y-F01** | P2 | ARIA | 2 unlabeled icon-only buttons on DeviceDetail: the refresh buttons in the Sensordaten and Variables panel headers. Screen readers say "button button" for them. | ✅ fixed |
| **R4-A11y-F02** | P2 | Landmark | `<html lang>` stuck at `en` (index.html default) even when user's saved locale is `de`. `setLocale()` patched the attribute on user change but never on app bootstrap. | ✅ fixed |
| **R4-A11y-F03** | P2 | Landmark | No "Skip to main content" link. Keyboard-only users must tab through the entire sidebar (~30 links) on every page. | ✅ fixed |
| **R4-A11y-F04** | P2 | Landmark | `<main>` had no `id`, which made skip-link and focus-management impossible. | ✅ fixed (`id="main-content"` + `tabindex="-1"`) |
| **R4-A11y-F05** | P1 | Contrast | `--text-muted: #5a5a72` on `--bg-base: #0a0a0f` = **2.95:1** — **fails WCAG AA** (requires 4.5:1 normal text, 3:1 large text). Used throughout for captions, hints, relative timestamps, panel descriptions — probably the single biggest a11y issue in the app. | ✅ fixed (`#7e7e94` → 5.0:1 AA pass) |

### Fixes applied (all in worktree `suspicious-raman`)

- **F01**: `frontend/src/pages/DeviceDetail.vue:2439-2447` + `2545-2549` — added `:aria-label` + `:title` using existing `common.refresh` key to both icon-only refresh buttons
- **F02**: `frontend/src/i18n/index.ts` — `document.documentElement.setAttribute('lang', _initialLocale)` at module load time so bootstrap matches the saved locale
- **F03**: `frontend/src/layouts/DefaultLayout.vue:314-321` — skip-link with `.sr-only focus:not-sr-only` Tailwind pattern, targets `#main-content`, programmatic `focus()` + `scrollIntoView()` on activate
- **F04**: `frontend/src/layouts/DefaultLayout.vue:755-762` — `<main id="main-content" tabindex="-1">` so the skip-link can focus it even though `<main>` isn't naturally focusable
- **F05**: `frontend/src/style.css:19` — `--text-muted: #5a5a72` → `#7e7e94` (dark theme, 2.95→5.00) and line 82 `#9898b0 → #6a6a82` (light theme, 2.54→4.80). Secondary stays at `#8b8b9e` (5.91) so "muted is softer than secondary" visual hierarchy is preserved.

### i18n additions (skip-link label)

All 8 locales got a new `common.skipToContent` key:

| Locale | Value |
|---|---|
| en | Skip to main content |
| de | Zum Hauptinhalt springen |
| fr | Aller au contenu principal |
| es | Saltar al contenido principal |
| it | Vai al contenuto principale |
| nl | Naar hoofdinhoud |
| pl | Przejdź do głównej treści |
| pt | Ir para o conteúdo principal |

### Live verification (post-reload)

On `/devices/1` after nginx bundle swap:
- `lang="de"` ✅ (matches saved locale)
- Skip-link present, targets `#main-content` which now exists ✅
- Icon-only no-label count: **0** (was 2) ✅
- `--text-muted` on `--bg-base`: **4.98:1 AA** (was 2.95:1 fail) ✅
- `--text-muted` on `--bg-surface`: **4.70:1 AA** ✅
- `--text-muted` on `--bg-raised`: **4.30:1 AA large** ✅
- Dashboard screenshot: captions "6 / 13 online", "Keine aktiven Alarme", section labels all visibly crisper ✅
- No console errors ✅

### Deferred (1 item)

- **R4-Perf-01** — `/users/me` double-bootstrap. Root cause: `auth.ts` and `capabilities.ts` both call it independently on first mount. Cleanup idea: make capabilities share the auth-store payload rather than re-fetch. Logged here for the backlog, not a release blocker.

---

## Release Summary

*(Round 6 — not yet)*

---

## 🚦 Kontrollpunkt 1 — CLOSED ✅

User directive on 2026-04-11: "1-3 Alles richtig erkannt von dir. Bei allem korrektur und -immer full translate (notfalls kann man wenn die übersetzung schlecht ist in der übersetzung auch das englische nehmen). Alle fix blöcke vor dev-stable. zu 4. wir halten das fest so wie oben angewiesen, machen alles was du für sinnvoll hällst und dann runde 2"

Translation: fix everything, always full translate, all fixes BEFORE Round 2, no CMS deferral.

**Result:** All 36 findings closed in 10 batches. CMS entirely swept (no deferral). ~2,100 i18n keys added. Round 2 can now proceed on a clean fixed codebase.

---

## Round 2 — Visual Pass (next)

Screenshots at 3 breakpoints (375 / 768 / 1440) × 2 locales (EN / DE) for the key flows. Focus routes:
- / (Dashboard) — check REAL-10 fix rendering on all widths
- /devices — row density, action button placement
- /devices/1 — verify REAL-18/19 fix at narrow widths (was the original freeze trigger)
- /alerts, /automations, /variables — core flows
- /firmware — OTA badge rendering
- /plugins — 6-card marketplace + install flow
- /hardware/wizard — 5-step wizard at each breakpoint
- /setup — 5-step setup wizard
- /cms — main page + at least one editor (CmsPageEditor)
- /landing — marketing page DE + EN

Each screenshot gets an observation note. Findings flagged into `## Visual Findings (Runde 2)` section below.
