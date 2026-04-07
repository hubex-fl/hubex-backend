# Phase 8b.1 — Device Detail Rewrite: Grafische Ansicht

## Context
HUBEX IoT hub — Vue 3 + TypeScript + Tailwind CSS frontend. Phase 2 Milestone 8 (UI Reboot) is complete. Milestone 8b focuses on UX depth: making the UI visually rich, intuitive and device-type-aware. This is Step 1: the Device Detail page.

## Current State
- `frontend/src/pages/DeviceDetail.vue` exists — a complex page with tabs, telemetry, tasks, variables
- Design system available: UCard, UBadge, UButton, UInput, USelect, UModal, UTabs, UToggle, USkeleton, UEmpty
- Dark theme with CSS custom properties
- The current DeviceDetail uses the design system but is text-heavy/table-heavy

## Goal
Rewrite/enhance `DeviceDetail.vue` to be visually compelling and immediately useful at a glance. Inspired by IoT dashboards (like Grafana device panels, Home Assistant entity cards).

## Requirements

### 1. Hero Section — Status Ring
- Large SVG status ring at the top (similar to Dashboard donut but for ONE device):
  - Color = device health: green (ok), amber (stale), red (dead/offline)
  - Center: device alias/UID (truncated) + health badge
  - Ring animates subtly (pulse for "online", static for offline)
- Beside the ring: key stats in a 2×2 mini-grid:
  - Last seen (relative time, e.g. "2m ago")
  - State badge (claimed / busy / pairing_active etc.)
  - Signal / RSSI (if available in telemetry/variables)
  - Battery % (if available in telemetry/variables)

### 2. Input Panel (Sensors / Telemetry)
- Card titled "Inputs" or "Telemetry"
- Shows latest telemetry values as compact metric tiles:
  - Icon (generic sensor icon)
  - Label (key name)
  - Value + unit
  - Mini sparkline bar (last 5 values, or just color indicator)
- Max 8 tiles visible, overflow hidden with "show all" toggle
- Empty state: "No telemetry data received yet"

### 3. Output Panel (Variables / Actuators)
- Card titled "Variables / Outputs"
- Shows device variables (from `/api/v1/devices/{id}/variables`)
- Each variable: label, current value, type badge
- For writable variables: inline edit (click-to-edit, UInput, save on blur/enter)
- Empty state: "No variables configured"

### 4. Live Traffic (Event Feed)
- Card titled "Recent Activity"
- Last 10 events for this device (filter by device_uid in event payload)
- Each row: timestamp, event type badge, brief payload preview
- "View in Events" button linking to /events?device=...
- Auto-refresh every 10s

### 5. Tasks / Executions
- Compact card: last 5 tasks with status badges
- "New Task" button opens existing task creation modal
- Links to /executions for full history

### 6. Page Header Improvements
- Back button (← Devices)
- Device name/alias as page title (not just "Device Detail")
- Edit alias inline (pencil icon → UInput → save)
- Action buttons row: Unclaim, Purge, Pair (visible by capability)

## Technical Constraints
- `<script setup lang="ts">`
- DO NOT add new UI components — use existing design system
- DO NOT modify backend code
- Keep all existing functionality (do not remove any working features)
- Use Tailwind responsive prefixes (`sm:`, `md:`, `lg:`)
- Gracefully handle missing data (signal/battery not always present)

## Files to Modify
1. `frontend/src/pages/DeviceDetail.vue` — primary rewrite
2. No other files need changes

## After Completion
1. Run `npx tsc --noEmit` + `npx vite build`
2. Verify at 375px (mobile) and 1280px (desktop)
3. Update ROADMAP.md: mark Step 1 done, set Step 2 ← AKTUELL
4. Generate `PROMPT_PHASE_8B_2.md`
5. Write report to REPORTS.md
