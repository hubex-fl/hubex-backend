# Phase 8b.5 — Empty States & Onboarding: Hilfreiche Erklärungen auf allen Seiten

## Context
HUBEX IoT hub — Vue 3 + TypeScript + Tailwind CSS frontend. Milestone 8b Steps 1–4 are done. Step 5 focuses on making every page useful when there is no data yet: each page should explain what it does, why it's empty, and offer a clear next action.

## Current State
- Devices page: already has good empty states (Phase 8b Step 2)
- Other pages (Entities, Alerts, Webhooks, Events, Audit, OTA) show raw empty tables or nothing
- New users see blank pages with no context

## Goal
Every page that can be empty should show a helpful, consistent empty state with:
- **Title**: What is this page for?
- **Description**: Why is it empty and what needs to happen?
- **Action**: Primary CTA to create/add the first item (or navigate to a related page)

## Requirements

### Pages to Update

#### Entities (`/entities`)
- Empty state: "No entities yet"
- Description: "Entities represent logical things (rooms, machines, systems) that group your devices. Create your first entity to start organizing."
- Action: "Create Entity" button → opens create modal (if exists) or shows inline form

#### Alerts (`/alerts`)
- Rules tab empty: "No alert rules"
- Description: "Alert rules notify you when devices go offline or metrics cross thresholds."
- Action: "Create Rule" → opens rule creation form
- Events tab empty: "No alert events"
- Description: "Alert events appear here when rules are triggered."
- No action button needed (events are system-generated)

#### Events (`/events`)
- Already has `UEmpty` — review and improve copy if needed
- Empty state: "No events yet"
- Description: "Events are emitted when devices connect, send telemetry, or tasks run. They'll appear here in real time."
- No action button (events are system-generated)

#### Audit (`/audit`)
- Already has `UEmpty` — review and improve copy if needed
- Empty state: "No audit entries"
- Description: "Every API action is logged here for traceability. Audit entries will appear as you use the platform."
- No action button

#### Dashboard (`/dashboard`)
- When all metric counters are zero (fresh install): show a welcome banner above the metrics grid
- Banner: "Welcome to HUBEX — pair your first device to get started" with "Pair Device" → `/devices`
- Hide banner once any device has been seen (`totalDevices > 0`)

### Consistent Empty State Pattern
Use `UEmpty` component with:
```html
<UEmpty icon="<svg path>" title="..." description="...">
  <UButton v-if="hasAction" ...>Action Label</UButton>
</UEmpty>
```

### Icon Guidelines
- Entities: grid/cube icon
- Alerts: bell icon
- Events: list/stream icon
- Audit: clipboard icon
- Dashboard welcome: rocket/home icon

## Technical Constraints
- `<script setup lang="ts">`
- DO NOT add new UI components — use UEmpty, UButton, UCard
- DO NOT modify backend code
- Keep all existing functionality intact

## Files to Modify
1. `frontend/src/pages/EntitiesPage.vue`
2. `frontend/src/pages/Alerts.vue`
3. `frontend/src/pages/Events.vue` (review/update existing UEmpty)
4. `frontend/src/pages/Audit.vue` (review/update existing UEmpty)
5. `frontend/src/pages/DashboardPage.vue` (welcome banner)

## After Completion
1. Run `npx tsc --noEmit` + `npx vite build`
2. Update ROADMAP.md: mark Step 5 done, Step 6 ← AKTUELL
3. Generate `PROMPT_PHASE_8B_6.md`
4. Write report to REPORTS.md
