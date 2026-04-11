# Review: `dev-stable-v1` (2026-04-11)

> Sprint 8 review per `docs/REVIEW_PROCESS.md`. Target: `dev-stable-v1` tag.
> First big review run — the process doc doubles as the template.

## Quick-Status
- **Started:** 2026-04-11
- **Round 1 (Smoke Pass):** ✅ **COMPLETE** — 48 routes walked, 36 findings
- **Round 1 Fixes:** ✅ **ALL 36 FINDINGS FIXED** in 10 commits
- **Round 2 (Visual):** ✅ **COMPLETE** — 12 routes walked, 11 findings, 8 fixed inline (commit `fe953fa`), 3 flagged
- **Round 3 (Persona):** ⏸ pending (human-driven)
- **Round 4 (Perf + A11y):** ⏸ pending
- **Round 5 (Fixing):** ✅ merged into Round 1 + Round 2 fix phases
- **Round 6 (Release):** ⏸ pending (after Rounds 3-4)
- **Findings R1:** 36 total — **0 P0 / 8 P1 / 18 P2 / 10 P3** — **36/36 fixed**
- **Findings R2:** 11 total — **0 P0 / 1 P1 / 7 P2 / 3 P3** — **8/11 fixed, 3 flagged-for-future**

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

## Persona Findings (Runde 3)

*(Runde 3 not started — human-driven)*

---

## Perf & A11y (Runde 4)

*(Runde 4 not started)*

---

## Fix List

*(empty — awaiting your priorization of Round 1 findings. Once you mark each as `must-fix` / `nice-to-fix` / `defer` / `false-positive`, the list gets built and Round 5 starts.)*

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
