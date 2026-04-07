# Phase 8b.6 — Dashboard Rewrite: Grafische Device-Kacheln, Ring-Diagramm, Quick Actions

## Context
HUBEX IoT hub — Vue 3 + TypeScript + Tailwind CSS frontend. Milestone 8b Steps 1–5 are done. Step 6 is a full visual rewrite of the Dashboard to be graphical and informative at a glance instead of just numbers.

## Current State
- Dashboard has 6 metric cards (total/online devices, entities, alerts, events, uptime)
- Device Health: SVG donut ring with legend (already good, keep as is)
- Recent Alerts: list (already good, keep as is)
- Quick Actions: 3 buttons (Pair Device, Create Alert Rule, View All Devices)
- Event Stream: live feed at bottom (already good, keep as is)
- Welcome banner when 0 devices (added in Step 5)

## Goal
Make the dashboard graphical, informative, and modern — a proper Mission Control view.

## Requirements

### 1. Device Status Tiles (replace plain metric cards)
Replace the flat `grid` of metric cards with **graphical device status tiles**:

**Top row — 3 hero stats** (`grid-cols-1 md:grid-cols-3`):
- **Total Devices** tile: large number + horizontal health bar (green/amber/red segments) + breakdown legend (online/stale/offline counts)
- **Devices Online** tile: large number with accent-green color + circular progress indicator (arc, shows online%) + "X% healthy" sub-label
- **Active Alerts** tile: large number, red if > 0 (with pulse animation) or muted if 0 + "All clear" / "X firing" label

**Second row — 3 info stats** (`grid-cols-1 sm:grid-cols-3`):
- **Entities**: number + entities icon
- **Events 24h**: number + events icon
- **Uptime**: formatted string + clock icon

### 2. Device Health Ring — keep existing SVG donut, improve layout
- Wrap in a card with `title="Device Health"`
- When `devices.total === 0`: show `UEmpty` with message "No devices — health will appear here once devices connect."
- Keep the legend (Online / Stale / Offline counts)

### 3. Quick Actions bar — improve visually
- Keep existing 3 buttons: Pair Device, Create Alert Rule, View All Devices
- Make them visually distinct: each button gets an icon + label, consistent size `size="md"`
- Add a 4th button: "View Entities" → `/entities`
- Arrange as `flex flex-wrap gap-3`

### 4. Online % Arc (for the Online tile)
SVG arc showing online percentage:
```
R=30, cx=36 cy=36, full circle circ=2*PI*R
arc length = pct * circ, gap = circ - arc
start at -90deg rotation
stroke: var(--status-ok) if pct >= 80, var(--status-warn) if pct >= 50, var(--status-bad) otherwise
background ring: var(--bg-raised)
```

### 5. Loading States
- Hero stats: skeleton cards (3 rectangles) when `metricsLoading`
- Info stats: 3 skeleton badges
- Keep existing skeleton for health ring

## Technical Constraints
- `<script setup lang="ts">`
- DO NOT add new UI components — use UCard, UButton, UBadge, UEmpty, USkeleton
- DO NOT modify backend code
- Keep all existing logic (donut chart, event stream, alerts list, welcome banner)
- The welcome banner from Step 5 stays (keep `v-if="!metricsLoading && metrics && metrics.devices.total === 0"`)

## Files to Modify
1. `frontend/src/pages/DashboardPage.vue` — complete template rewrite of metric cards section, keep script

## After Completion
1. Run `npx tsc --noEmit` + `npx vite build`
2. Update ROADMAP.md: mark Step 6 done (Milestone 8b complete), update ← AKTUELL to next milestone
3. Report to REPORTS.md
