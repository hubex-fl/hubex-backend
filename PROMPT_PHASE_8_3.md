# Phase 8.3 — Devices Page Migration (Mission Control Design)

## Context
You are working on HUBEX, an IoT device hub backend with a Vue 3 + TypeScript + Tailwind CSS frontend. Phase 8.1 established the design system (16 UI components in `frontend/src/components/ui/`, Tailwind config with CSS custom properties, dark theme). Phase 8.2 built the Dashboard page with live metrics. Now we migrate the Devices page to the new Mission Control design.

## Current State
- The existing `frontend/src/pages/Devices.vue` is a functional but unstyled page (~988 lines) with raw HTML `<input>`, `<select>`, `<button>`, `<table>` elements and scoped CSS
- It already has full business logic: device list, search, sort, filter, pairing, bulk unclaim/purge, device lookup, capability checks
- Backend API endpoints all work: `GET /api/v1/devices`, device pairing, unclaim, purge, lookup
- Design system components available: UButton, UCard, UBadge, UInput, USelect, UTable, UModal, UDropdown, USkeleton, UEmpty, UToggle, UTooltip, UTabs, UTab, UKbd, UAvatar, UToast

## Goal
Rewrite `frontend/src/pages/Devices.vue` to use the Mission Control design system. Keep ALL existing business logic intact. The page should feel like it belongs next to the Dashboard.

## Requirements

### 1. Layout & Structure
- Use `UCard` for the main content sections
- Split into logical sections: Pairing panel (collapsible), Toolbar, Device Table, Bulk Actions
- Use the same spacing/gap patterns as DashboardPage (`space-y-6`, `gap-4`)

### 2. Pairing Section
- Wrap in a `UCard` with header "Pair Device"
- Use `UInput` for Device UID and Pairing Code fields
- Use `UButton` for Claim action
- Show `UBadge` for pairing status/warnings
- Make this section collapsible (collapsed by default, expandable)

### 3. Toolbar
- Replace raw `<input>` and `<select>` with `UInput` (search) and `USelect` (sort, filter)
- Add a device count badge showing "X devices" / "X of Y shown"
- Keep the admin toggle for showing unclaimed devices
- Add a refresh button with loading indicator

### 4. Device Table
- Use `UTable` component for the device list
- Use `UBadge` for health status (ok=green, stale=amber, dead=red), device state, and online/offline
- Make rows clickable for claimed devices (navigate to detail)
- Show `USkeleton` rows while loading
- Show `UEmpty` when no devices match
- Keep checkbox selection for bulk actions
- Keep the existing `v-memo` optimization for performance

### 5. Bulk Actions Bar
- Show as a sticky bottom bar when items are selected
- Use `UButton` for actions (unclaim, purge)
- Use `UModal` for the purge confirmation dialog instead of `window.prompt`
- Show selected count and action status with `UBadge`

### 6. Mobile Responsive
- Table scrolls horizontally on small screens
- Pairing section stacks vertically
- Toolbar wraps gracefully

### 7. Composable Extraction
- Create `frontend/src/composables/useDevices.ts` to extract the device fetching/polling logic from the page
- Pattern: same as `useMetrics.ts` — returns `{ devices, loading, error }` with `createPoller`
- Keep the `reconcileById` optimization for smooth updates
- The page component should only handle UI state (search, sort, filter, selection, modals)

### 8. Visual Polish
- Status indicators: green pulse dot for online devices in the table
- Health badges with appropriate colors matching the design system CSS vars (`--status-ok`, `--status-warn`, `--status-bad`)
- Monospace font for UIDs and timestamps (`font-mono`)
- Smooth transitions on filter/sort changes
- Loading states: skeleton rows, refreshing indicator (subtle, non-blocking)

## Technical Constraints
- Keep `<script setup lang="ts">` pattern
- Use existing CSS custom properties from the design system (not hardcoded colors)
- Keep ALL existing functionality: search, sort, filter, pairing, claim, bulk unclaim, bulk purge, admin toggle, device lookup, navigation to detail page
- Use `apiFetch` from `../lib/api` for API calls
- Use `useCapabilities` and `hasCap` for capability checks
- Use `createPoller` from `../lib/poller` for polling
- DO NOT modify any backend code
- DO NOT modify any existing UI components
- DO NOT create new UI components (use the 17 existing ones)

## Files to Create/Modify
1. **CREATE** `frontend/src/composables/useDevices.ts` — Device list composable with polling
2. **MODIFY** `frontend/src/pages/Devices.vue` — Complete rewrite using design system

## Testing
After implementation:
1. Run `cd frontend && npx vitest run` to ensure no component tests break
2. Verify the page renders at `http://localhost:5173/devices`
3. Test: search filtering works
4. Test: sort dropdown changes order
5. Test: filter dropdown filters correctly
6. Test: clicking a claimed device navigates to `/devices/:id`
7. Test: pairing section expands/collapses
8. Test: bulk selection checkboxes work
9. Test: loading skeleton shows on initial load
10. Test: empty state shows when no devices match filter

## Reference
- Dashboard page for design patterns: `frontend/src/pages/DashboardPage.vue`
- Design system components: `frontend/src/components/ui/`
- Current devices page (all business logic): `frontend/src/pages/Devices.vue`
- Device detail page: `frontend/src/pages/DeviceDetail.vue`
- API types/helpers: `frontend/src/lib/api.ts`, `frontend/src/lib/errors.ts`, `frontend/src/lib/capabilities.ts`

## After Completion
Update `ROADMAP.md`: mark Step 2 as done `[x]`, set Step 3 as `← AKTUELL`
