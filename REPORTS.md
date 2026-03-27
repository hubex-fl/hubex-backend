# HUBEX Build Reports

---

## Hotfix — Device Health Thresholds + DeviceDetail Visual Polish
**Date:** 2026-03-28
**Status:** ✅ Done
**TS Check:** ✅ 0 errors
**Vite Build:** ✅ 124 modules, built in 1.80s (DeviceDetail: 43.07 kB → 12.94 kB gzip)

### Changes Made

#### `app/api/v1/devices.py` — Backend health threshold fix
- `online_window`: `timedelta(seconds=30)` → `timedelta(seconds=60)`
- List endpoint: `age_seconds <= 30` → `age_seconds <= 60` (ok), `age_seconds <= 120` → `age_seconds <= 300` (stale)
- Detail endpoint: same threshold changes applied
- **Fixes**: device badge flickering between `stale` and `ok` every 30s during normal operation

#### `frontend/src/pages/DeviceDetail.vue` — Visual polish
- **Page header**: Simplified to breadcrumb only (`← Devices / <device uid>`) — removed duplicate action buttons (were also in hero card)
- **Telemetry panel**: Label changed from "Telemetry" to "↓ Input · Telemetry" with cyan `↓` arrow + blue left border (`border-l-[var(--accent-cyan)]`)
- **Variables panel**: Label changed from "Variables" to "↑ Output · Variables" with lime `↑` arrow + lime left border (`border-l-[var(--accent-lime)]`)

### Root Cause of Badge Flickering
The backend used `ok` threshold of `≤30s`. With a 30s poll interval on the device, the backend flip-flopped between `ok` and `stale` each cycle. Raising to `≤60s` (ok) and `≤300s` (stale) gives proper stability.

---

## Phase 8b Step 6 — Dashboard Rewrite: Hero Stats, Online Arc, Quick Action Cards
**Date:** 2026-03-28
**Status:** ✅ Done — **Milestone 8b COMPLETE**
**TS Check:** ✅ 0 errors
**Vite Build:** ✅ 124 modules, built in 1.79s (DashboardPage: 23.40 kB → 5.98 kB gzip, was 16.46 kB)

### Changes Made

#### `frontend/src/pages/DashboardPage.vue`
Replaced flat 6-card metric grid with a two-row graphical hero layout. All existing logic (event stream, health ring, alerts panel) preserved.

**New script additions:**
- `ARC_R`, `ARC_CIRC` constants (R=30)
- `arcDash`, `arcGap` computed — maps `onlinePct` to SVG stroke-dasharray
- `arcStroke` computed — `var(--status-ok)` ≥80%, `var(--status-warn)` ≥50%, `var(--status-bad)` otherwise

**Section 1 — Hero Stats (3 large tiles, `grid-cols-1 md:grid-cols-3`):**
- **Total Devices**: `text-5xl` count + color-segmented health bar (green/amber/red) + breakdown text
- **Online Now**: `text-5xl` count (green) + contextual label ("Fleet healthy" / "Partial outage" / "Major outage") + inline SVG arc showing `onlinePct%` with dynamic stroke color
- **Active Alerts**: `text-5xl` count (red if firing, muted if 0) + "All clear" or "X rules firing" sub-label + pulsing UBadge when firing

**Section 2 — Info Stats (3 compact tiles, `grid-cols-1 sm:grid-cols-3`):**
- Entities (clickable → `/entities`), Events 24h (clickable → `/events`), Uptime
- Icon + `text-2xl` number + label pattern
- Hover border tint on clickable tiles

**Section 3 — Quick Actions (4 cards, `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`):**
- Replaced 3 plain UButtons with 4 icon cards using `group-hover` transitions
- Cards: Pair Device, View Devices, Create Alert, View Entities
- Each card: colored icon + title + description + chevron arrow

**Unchanged:** welcome banner, device health ring (donut SVG), recent alerts panel, event stream

### Milestone Status
🎉 **Milestone 8b: UI/UX Redesign — Intuitive & Grafisch — COMPLETE** (all 6 steps done)

### Next Step
**Milestone 9 Step 1** — ESP SDK Update (OTA check, edge config, heartbeat)

---

## Phase 8b Step 5 — Empty States & Onboarding
**Date:** 2026-03-28
**Status:** ✅ Done
**TS Check:** ✅ 0 errors
**Vite Build:** ✅ 124 modules, built in 1.92s

### Changes Made

#### `frontend/src/pages/EntitiesPage.vue`
- Improved empty state: title "No entities yet", description explains what entities are ("Entities represent logical things — rooms, machines, systems — that group your devices")
- Added cube/grid SVG icon to empty state
- Filter-empty state now has a search/magnifying icon instead of generic icon

#### `frontend/src/pages/Alerts.vue`
- Imported `UEmpty` component
- Events tab: replaced raw SVG+text div with `<UEmpty>` — title "No alert events", description "Alert events appear here when a rule is triggered. They are generated automatically when conditions are met."
- Rules tab: replaced raw SVG+text div with `<UEmpty>` — title "No alert rules", description "Alert rules notify you when devices go offline or metrics cross thresholds. Create your first rule to get started." + "Create Rule" CTA button inside the empty state

#### `frontend/src/pages/Events.vue`
- Updated `UEmpty` description from "Start polling on a stream to see events here." → "Events are emitted when devices connect, send telemetry, or tasks run. Enter a stream name and start polling to see them here."

#### `frontend/src/pages/Audit.vue`
- Updated `UEmpty` description from "No entries match the current filters." → "Every API action is logged here for traceability. Audit entries will appear as you use the platform."

#### `frontend/src/pages/DashboardPage.vue`
- Added welcome banner above the metrics grid: shown when `!metricsLoading && metrics && metrics.devices.total === 0`
- Banner: cyan-tinted card with rocket icon, "Welcome to HUBEX" title, "No devices yet — pair your first device to start monitoring." + "Pair Device" button → `/devices`
- Banner disappears automatically once any device exists

### Next Step
**PROMPT_PHASE_8B_6.md** — Dashboard Rewrite: grafische Device-Kacheln, Online%-Arc, Echtzeit-Ring-Diagramm (Milestone 8b Step 6)

---

## Phase 8b Step 4 — Server Offline UX: Backend-weg-Indikator, Reconnect
**Date:** 2026-03-27
**Status:** ✅ Done
**TS Check:** ✅ 0 errors
**Vite Build:** ✅ 124 modules (+4 new), built in 1.78s

### Changes Made

#### `frontend/src/stores/serverHealth.ts` (new)
New Pinia store:
- `serverOnline` ref (default `true`)
- `lastOfflineAt` ref — timestamp when server first went offline
- `markOffline()` — sets `serverOnline = false`, records timestamp, starts background poller
- `markOnline()` — sets `serverOnline = true`, stops poller, returns `wasOffline` boolean
- Background poller: `setInterval` at 5s, hits `GET /health` with 3s timeout (AbortController), calls `markOnline()` on success

#### `frontend/src/lib/api.ts`
- Import `useServerHealthStore`
- `apiFetch` now wraps `fetch()` in try/catch: network error → `markOffline()` + rethrow
- Status 502/503/504 → `markOffline()` + throw
- Any successful response → `markOnline()`

#### `frontend/src/components/ui/UOfflineBanner.vue` (new)
- Fixed `top-0 inset-x-0 z-[200]` amber banner
- Amber `bg-amber-900/90 backdrop-blur-sm` with wifi-off icon, "Server unreachable" label, spinning reconnect indicator
- Elapsed timer (ticks every 1s via `setInterval`, starts/stops with `serverOnline` watcher)
- `Transition name="offline-banner"` — slides in from top, fades out on recovery

#### `frontend/src/stores/toast.ts`
- Suppresses `variant === "error"` toasts when `!serverOnline` — prevents cascading "Failed to load" errors while the banner already explains the situation

#### `frontend/src/layouts/DefaultLayout.vue`
- Import `useServerHealthStore` + `UOfflineBanner`
- `<UOfflineBanner />` rendered at top of layout (before mobile backdrop)
- `watch(serverHealth.serverOnline)`: shows "Server reconnected" success toast (3s) when coming back online
- `<main>` gets `relative` class + dim overlay `<div v-if="!serverHealth.serverOnline" class="absolute inset-0 bg-[var(--bg-base)]/60 z-10 pointer-events-none" />`

### Next Step
**PROMPT_PHASE_8B_5.md** — Empty States & Onboarding: hilfreiche Erklärungen auf Entities, Alerts, Events, Audit, Dashboard (Milestone 8b Step 5)

---

## Phase 8b Step 3 — Sidebar Navigation: Grouping, Coming Soon, Cleanup
**Date:** 2026-03-27
**Status:** ✅ Done
**TS Check:** ✅ 0 errors
**Vite Build:** ✅ 120 modules, built in 1.81s

### Changes Made

#### `frontend/src/layouts/DefaultLayout.vue`
Replaced flat `navItems` array with `navGroups` structure. Removed clutter (System Stage, Token Inspector) from main nav. Added Entities (was in router but missing from nav).

**New data structure:**
```ts
type NavItem = { to, label, icon, cap, comingSoon? }
type NavGroup = { label: string; items: NavItem[] }
const navGroups: NavGroup[] = [ /* 4 groups */ ]
const visibleNavGroups = computed(() => navGroups filtered by cap, comingSoon items always shown)
```

**4 Navigation Groups:**
- **Core**: Dashboard, Devices, Entities
- **Automation**: Alerts, Automations (Soon), Executions (Soon)
- **Observability**: Events, Audit, Trace Hub (Soon), Correlation (Soon)
- **Admin**: Settings

**Coming Soon items** (`comingSoon: true`):
- Non-interactive (`cursor-not-allowed opacity-40 select-none`)
- Show "Soon" chip when sidebar is expanded
- Tooltip shows "— Coming Soon" when collapsed
- Automations (was Effects), Executions, Trace Hub, Correlation

**Section labels** (desktop expanded + mobile):
- `text-[10px] uppercase tracking-widest` above each group
- Hidden when desktop sidebar is collapsed — replaced by subtle `border-t` divider
- First group has no top padding

Both desktop nav and mobile overlay nav updated to use groups.

**Removed from nav:**
- System Stage (replaced by Entities with proper route `/entities`)
- Token Inspector (developer tool, not needed in main nav)
- Observability (Coming Soon — listed in Observability section as Correlation instead)

### Next Step
**PROMPT_PHASE_8B_4.md** — Server Offline UX: backend-unreachable banner, content dimming, auto-reconnect (Milestone 8b Step 4)

---

## Phase 8b Step 2 — Device List: Card View, Empty States, UX Improvements
**Date:** 2026-03-27
**Status:** ✅ Done
**TS Check:** ✅ 0 errors
**Vite Build:** ✅ 120 modules, built in 1.79s (Devices: 32.52 kB → 9.47 kB gzip)

### Changes Made

#### `frontend/src/pages/Devices.vue`
Added card-view toggle, improved empty states, mobile pairing always-visible behavior, and skeleton loading states.

**New script additions:**
- `deviceView` ref — persisted to `localStorage` (`hubex:device-view`), default `"table"`
- `watch(deviceView)` — syncs to localStorage on change
- `hasActiveFilter` computed — `searchQuery !== "" || filterBy !== "all"`
- `cardHealthBorder(health)` — returns left-border CSS class (green/amber/red/gray by health)
- `clearFilters()` — resets searchQuery + filterBy to defaults
- `onMounted`: auto-opens pairing panel on mobile (`window.innerWidth < 768`)

**Template changes:**

1. **View Toggle** — toolbar now has `[≡ Table]  [⊞ Cards]` buttons, active button highlighted with accent-cyan tint
2. **Pairing Section** — collapse toggle hidden on mobile (`hidden md:flex`); content `:class` logic keeps pairing always visible on mobile regardless of `pairingOpen`; "First time? Start here →" hint shown when `devices.length === 0`
3. **Empty States (table view)** — two contextual states:
   - No devices + no filter: "No devices yet" + description + "Pair Device" button (scrolls to pairing)
   - Filtered + no results: "No devices match" + description + "Clear filters" button
4. **Table view** — wrapped in `v-if="deviceView === 'table'"`, existing table preserved intact
5. **Card grid view** — `v-else`, `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`:
   - Loading: 8 USkeleton placeholder cards
   - Empty: contextual UEmpty with action buttons (same logic as table)
   - Device cards: left-border health color, device UID (monospace truncated), health+state UBadge pair, last-seen/online indicator (pulsing dot), action button (Open/Pair by state), bulk checkbox when `bulkMode` active, hover glow + cursor-pointer, `v-memo` for performance

**Preserved intact:**
- All existing functionality: bulk unclaim, bulk purge, pairing flow, sort/filter/search, row click navigation, all API calls

### Next Step
**PROMPT_PHASE_8B_3.md** — Sidebar Navigation: Grouping (Core/Automation/OTA/Observability/Admin), Coming Soon badges, section labels (Milestone 8b Step 3)

---

## Phase 8b Step 1 — Device Detail Rewrite: Graphical View
**Date:** 2026-03-27
**Status:** ✅ Done
**TS Check:** ✅ 0 errors
**Vite Build:** ✅ 120 modules, built in 2.13s (DeviceDetail: 39.48 kB → 12.30 kB gzip)

### Changes Made

#### `frontend/src/pages/DeviceDetail.vue`
Full template rewrite from legacy CSS (`.card`, `.pill`, `.btn`) to design system. All existing logic preserved exactly.

**New computed helpers added to script:**
- `heroRingColor` — CSS var string based on device health (ok/stale/dead)
- `heroRingOnline` — boolean, triggers ring pulse animation
- `healthBadgeStatus`, `stateBadgeStatus`, `taskBadgeStatus` — badge status mappers
- `latestPayloadFields` — extracts latest telemetry payload as `{key, value}` tiles
- `visibleTelemetryFields` — sliced to MAX_TILES=8 with show-all toggle
- `showAllTelemetry` ref — for expand/collapse of telemetry tiles
- `historyStatusBadge` — replaces `historyStatusClass` with badge-compatible return type
- `variableSourceLabel` — returns "override" / "default" (shortened)

**Template structure (new):**
1. **Page Header** — Back button (← Devices), device UID as title, health + state badges, Refresh/Copy UID/Pairing Panel actions
2. **Unclaimed warning** — amber banner with icon when device not claimed
3. **Hero Section** — `md:grid-cols-[200px_1fr]` layout:
   - Left: SVG status ring (R=52, full arc, color=health, pulse animation when online)
   - Right: 2×2 stat cards (Last Seen, State, Current Task, Lease Expires)
4. **Main Panels** — `lg:grid-cols-2` layout:
   - Telemetry card: live dot indicator, metric tiles grid (2-col), fallback to raw table, UEmpty state
   - Variables card: inline edit with pencil/delete/reveal icon buttons, add-override form with USelect+UInput, source badge
5. **Recent Tasks** — table with UBadge status, responsive (hidden columns on mobile)
6. **Recovery** — reissue token flow with new token display card, audit entries list
7. **Danger Zone** — red-border card, unclaim confirm flow

**Removed:**
- All legacy CSS classes (`.card`, `.card-header-row`, `.pill`, `.pill-ok`, etc.)
- Inline `style=""` attributes replaced with Tailwind utilities
- `<style scoped>` reduced to single `ring-pulse` keyframe animation

### Next Step
**PROMPT_PHASE_8B_2.md** — Device List: Card-View Toggle, Empty States, UX Improvements (Milestone 8b Step 2)

---

## Phase 8 Step 9 — Mobile Responsive + Final Polish
**Date:** 2026-03-27
**Status:** ✅ Done
**TS Check:** ✅ 0 errors
**Vite Build:** ✅ 120 modules, built in 1.84s

### Changes Made

#### `frontend/src/layouts/DefaultLayout.vue`
- Added `mobileOpen` ref for mobile overlay state
- Hamburger button (visible `md:hidden`) in header — opens mobile sidebar
- Desktop sidebar unchanged (collapsed/expanded behavior retained)
- Mobile: full-width `w-64` overlay sidebar with `z-40`, animated slide-in from left
- Semi-transparent backdrop (`bg-black/60 backdrop-blur-sm`) with click-outside-to-close
- Close button (X) inside mobile sidebar header
- Nav links on mobile are `py-3` (44px+ touch targets, h-5 icons)
- Route changes auto-close the mobile sidebar (`handleNavClick`)
- CSS transitions: `backdrop` (fade), `slide` (translateX)
- Page content padding: `p-3 md:p-6` (tighter on mobile)

#### `frontend/src/pages/DashboardPage.vue`
- Metric cards grid: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`
- Event stream rows: timestamp hidden on `<sm`, stream hidden on `<md` — cleaner on mobile

#### `frontend/src/pages/Events.vue`
- Full rewrite from legacy CSS (`.page`, `.card`, `.btn`) to design system
- Uses: `UCard`, `UButton`, `UInput`, `UBadge`, `USkeleton`, `UEmpty`
- Form rows stack vertically on mobile, horizontal on `sm:`+
- Status bar shows cursor, next_cursor, caught-up, polling indicator
- Table: `Trace` column hidden on `<md`, `overflow-x-auto` for scroll
- Error state uses red-border card pattern
- Loading state with skeleton rows

#### `frontend/src/pages/Audit.vue`
- Full rewrite from legacy CSS to design system
- Filter bar stacks vertically on mobile, horizontal on `sm:`+
- Table: `Time` hidden on `<sm`, `Resource` hidden on `<md`
- Selected row highlighted with cyan tint
- Detail panel closes with X button, JSON formatted with `JSON.stringify(detail, null, 2)`
- Loading skeletons, empty state with icon

#### `frontend/src/components/ui/UToast.vue`
- Mobile: full-width `right-2 left-2`, desktop: `sm:right-4 sm:left-auto sm:w-80`
- Toasts now properly fill screen width on mobile instead of overflowing

### Next Step
**PROMPT_PHASE_8B_1.md** — Device Detail Rewrite: grafische Ansicht mit Status-Ring, Input/Output Panels, Live Traffic (Milestone 8b Step 1)
