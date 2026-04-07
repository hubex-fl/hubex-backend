# Phase 8b.2 — Device List: Card View, Empty States, UX Improvements

## Context
HUBEX IoT hub — Vue 3 + TypeScript + Tailwind CSS frontend. Milestone 8b Step 1 (Device Detail graphical redesign) is done. Step 2 focuses on the Device List page (`Devices.vue`): adding a card-view option, improving empty states, and generally making the list more intuitive.

## Current State
- `frontend/src/pages/Devices.vue` — fully functional, table-based device list with filter/sort/bulk/pairing
- Design system available: UCard, UBadge, UButton, UInput, USelect, UModal, UTabs, UToggle, USkeleton, UEmpty
- Device fields: device_uid, health (ok/stale/dead), state (claimed/busy/pairing_active/etc.), last_seen_age_seconds, online, pairing_active

## Goal
Improve the Device List page to be more visually useful, especially when devices have different states. Add a card-view toggle so users can switch between table and grid-card layout. Improve empty states with helpful context.

## Requirements

### 1. View Toggle (Table vs Cards)
- Add a toggle in the toolbar: `[≡ Table]  [⊞ Cards]`
- Store preference in `localStorage` (key: `hubex:device-view`)
- Default: table view
- Cards view: responsive grid `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`

### 2. Device Card Design
Each card shows:
- **Status indicator**: Left border or top strip colored by health (green/amber/red)
- **Device UID**: Prominent, monospace font, truncated
- **Health badge + State badge** side by side
- **Last seen**: Relative time (e.g. "2m ago" or "offline")
- **Online indicator**: Pulsing dot when online
- **Row action button**: "Open" (claimed), "Pair" (pairing_active), etc.
- If device is selected (bulk mode): checkbox visible, card highlighted
- Hoverable: cursor pointer, subtle glow on hover
- Click → same `onRowClick(d)` behavior as table row

### 3. Table View Improvements
- Keep existing table but improve:
  - Add UID column with monospace font + truncate
  - Color-code health column with UBadge
  - "Open" action column at the right
  - Mobile: hide lower-priority columns (health details, last_seen_age text) below `sm:`

### 4. Empty States
- When `visibleDevices.length === 0` AND no filter active:
  - Title: "No devices yet"
  - Description: "Pair your first device to get started. Devices will appear here once they connect."
  - Action button: "Pair Device" → opens pairing section
- When filtered and no results:
  - Title: "No devices match"
  - Description: "Try adjusting your search or filter."
  - Action button: "Clear filters"

### 5. Pairing Section
- On mobile: always visible (expanded by default), not collapsible
- On desktop: keep existing collapsible behavior
- Add a subtle "First time? Start here →" hint when device list is empty

### 6. Loading State
- When `loading === true` (initial load): show skeleton cards (card view) or skeleton rows (table view) instead of empty state

## Technical Constraints
- `<script setup lang="ts">`
- DO NOT add new UI components — use existing design system
- DO NOT modify backend code
- Keep all existing functionality intact (bulk unclaim, bulk purge, pairing, etc.)
- Use Tailwind responsive prefixes

## Files to Modify
1. `frontend/src/pages/Devices.vue` — primary changes

## After Completion
1. Run `npx tsc --noEmit` + `npx vite build`
2. Update ROADMAP.md: mark Step 2 done, Step 3 ← AKTUELL
3. Generate `PROMPT_PHASE_8B_3.md`
4. Write report to REPORTS.md
