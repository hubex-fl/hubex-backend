# Phase 8b.4 — Server Offline UX: Backend-weg-Indikator, Reconnect

## Context
HUBEX IoT hub — Vue 3 + TypeScript + Tailwind CSS frontend. Milestone 8b Steps 1–3 are done (Device Detail, Device List, Sidebar Navigation). Step 4 focuses on what the user sees when the backend is unreachable: dim/disable page content, show a persistent reconnect banner, and prevent confusing error states when the server is simply offline.

## Current State
- API calls use `fetch` via `frontend/src/lib/api.ts`
- Pages use `createPoller` / `runRefresh` for data fetching
- Errors are shown per-page (red cards, `UEmpty` states)
- There is no global "server is offline" indicator
- When backend is down, pages silently fail or show per-component errors

## Goal
Add a global server-health layer:
1. Detect when the backend is unreachable (network error / 502 / 503 / 504)
2. Show a persistent top banner: "Server unreachable — reconnecting…"
3. Dim page content (overlay or reduced opacity) while offline
4. Automatically retry connection and dismiss banner when backend recovers
5. Avoid cascading error toasts while offline

## Requirements

### 1. Server Health Store (`frontend/src/stores/serverHealth.ts`)
New Pinia store:
```ts
const serverOnline = ref(true);
const lastChecked = ref<Date | null>(null);
const checkInterval = 5000; // ms

function markOffline() { serverOnline.value = false; }
function markOnline() { serverOnline.value = true; lastChecked.value = new Date(); }
```
- Export `useServerHealthStore()`
- The store runs a background poller (`setInterval`) that hits `GET /health` every 5s when offline, to detect recovery
- When the health check succeeds: `markOnline()`
- Expose `serverOnline`, `lastChecked`

### 2. API Layer Integration (`frontend/src/lib/api.ts`)
- When a fetch throws `TypeError` (network error) OR returns status 502/503/504: call `useServerHealthStore().markOffline()`
- When a fetch succeeds (any 2xx or even 4xx — the server is reachable): call `useServerHealthStore().markOnline()`
- Do NOT suppress errors — still propagate them to callers as before

### 3. Offline Banner Component (`frontend/src/components/ui/UOfflineBanner.vue`)
New component:
- Shown when `!serverOnline`
- Fixed position: `fixed top-0 inset-x-0 z-[200]`
- Style: amber/warning background (`var(--status-warn-bg)` or `bg-amber-900/80 backdrop-blur-sm`)
- Content: wifi-off icon + "Server unreachable" text + spinning reconnect indicator + elapsed time ("Retrying… 3s ago")
- Smooth slide-in from top (`Transition name="offline-banner"`)
- Does NOT have a close/dismiss button (auto-dismisses when server comes back)

### 4. Layout Integration (`frontend/src/layouts/DefaultLayout.vue`)
- Import and render `<UOfflineBanner />` at the top of the layout (above the header)
- Add an overlay to the `<main>` content area when offline:
  ```html
  <div v-if="!serverOnline" class="absolute inset-0 bg-[var(--bg-base)]/60 z-10 pointer-events-none" />
  ```
  (main must have `relative` class for this to work)
- The overlay dims content but doesn't block interaction (pointer-events-none)

### 5. Toast Suppression
- In `frontend/src/lib/api.ts` or the toast store: when `!serverOnline`, suppress network-error toasts (don't show "Failed to load devices" etc. while the banner already explains why)
- Re-enable toasts once server comes back online

### 6. Recovery UX
- When `serverOnline` transitions from `false` → `true`:
  - Dismiss the banner (Transition out)
  - Show a brief success toast: "Server reconnected" (auto-dismiss after 3s)
  - Pages with pollers will naturally refresh on their next poll cycle — no forced refresh needed

## Technical Constraints
- `<script setup lang="ts">`
- DO NOT add new UI components besides `UOfflineBanner.vue`
- DO NOT modify backend code
- Keep all existing functionality intact
- Use Tailwind + CSS Custom Properties

## Files to Create/Modify
1. `frontend/src/stores/serverHealth.ts` — new Pinia store
2. `frontend/src/lib/api.ts` — integrate offline detection
3. `frontend/src/components/ui/UOfflineBanner.vue` — new component
4. `frontend/src/layouts/DefaultLayout.vue` — render banner + content overlay

## After Completion
1. Run `npx tsc --noEmit` + `npx vite build`
2. Update ROADMAP.md: mark Step 4 done, Step 5 ← AKTUELL
3. Generate `PROMPT_PHASE_8B_5.md`
4. Write report to REPORTS.md
