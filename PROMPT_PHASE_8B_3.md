# Phase 8b.3 — Sidebar Navigation: Grouping, Coming Soon, Cleanup

## Context
HUBEX IoT hub — Vue 3 + TypeScript + Tailwind CSS frontend. Milestone 8b Steps 1 and 2 are done (Device Detail graphical rewrite + Device List card view). Step 3 focuses on the sidebar navigation in `DefaultLayout.vue`: grouping nav items into logical sections, marking incomplete/placeholder pages as "Coming Soon" (visually disabled), and hiding items that have no meaningful content yet.

## Current State
- `frontend/src/layouts/DefaultLayout.vue` — fully rewritten with desktop collapsed/expanded sidebar + mobile overlay. Nav links are a flat list with icons and labels.
- Current nav items (from router): Dashboard, Devices, Entities, Alerts, OTA, Webhooks, Events, Audit, Settings (org/auth/plan pages)
- Several pages exist as stubs or are largely empty (TraceHub, Correlation, Observability, SystemStage, Effects, TokenInspector, Pairing, Variables, Executions)

## Goal
Make the sidebar navigation cleaner, more intuitive, and honest about what is implemented. Group items into sections, add "Coming Soon" badges on placeholder items, and optionally hide items that add noise without value.

## Requirements

### 1. Navigation Groups
Organize nav items into labeled groups. Groups should have a subtle section label (visible when sidebar is expanded, hidden when collapsed):

**Core**
- Dashboard (`/dashboard`)
- Devices (`/devices`)
- Entities (`/entities`)

**Automation**
- Alerts (`/alerts`)
- Webhooks (`/webhooks`)

**OTA & Config**
- OTA (`/ota`)

**Observability**
- Events (`/events`)
- Audit (`/audit`)

**Admin**
- Settings (sub-items or single entry for `/settings/org`, `/settings/auth`, `/settings/plan`)

### 2. "Coming Soon" Items
These items should be shown in the sidebar but visually disabled (muted text, no click, "Coming Soon" chip):
- Any nav items pointing to stub/empty pages that are not yet useful

Candidates (verify by checking which pages exist and have meaningful content):
- Trace Hub (`/trace`)
- Correlation (`/correlation`)
- Observability (`/observability`)

Coming Soon item style:
- `opacity-50 cursor-not-allowed pointer-events-none`
- Small inline chip: `text-[10px] px-1 rounded bg-[var(--bg-card)] text-[var(--text-muted)]` with text "Soon"
- Only show chip when sidebar is expanded (`!sidebarCollapsed`)

### 3. Section Labels
- Only visible when sidebar is NOT collapsed (`!sidebarCollapsed`)
- Style: `text-[10px] uppercase tracking-widest font-semibold text-[var(--text-muted)] px-3 pt-4 pb-1`
- First section has no top padding

### 4. Collapsed Sidebar
- When `sidebarCollapsed === true`: section labels are hidden, Coming Soon items show only their icon (muted)
- Icon tooltip (title attribute) should still reflect the Coming Soon state

### 5. Active State
- Keep existing active link highlight (`router-link-active` or manual `isActive` check)
- Active item: `bg-[var(--accent-cyan)]/10 text-[var(--accent-cyan)]` with left border `border-l-2 border-[var(--accent-cyan)]`

### 6. Settings Handling
- Settings has sub-pages (org, auth, plan). Show as single "Settings" link to `/settings/org` (already active for all `/settings/*` routes due to partial match)

## Technical Constraints
- `<script setup lang="ts">`
- DO NOT add new UI components
- DO NOT modify backend code
- Keep mobile sidebar behavior intact
- Keep collapsed/expanded desktop behavior intact
- Use Tailwind + CSS Custom Properties

## Files to Modify
1. `frontend/src/layouts/DefaultLayout.vue` — primary changes

## After Completion
1. Run `npx tsc --noEmit` + `npx vite build`
2. Update ROADMAP.md: mark Step 3 done, Step 4 ← AKTUELL
3. Generate `PROMPT_PHASE_8B_4.md`
4. Write report to REPORTS.md
