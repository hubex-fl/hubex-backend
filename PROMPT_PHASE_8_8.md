# Phase 8.8 — Webhooks + Events + Audit Pages (Mission Control Design)

## Context
HUBEX IoT hub backend, Vue 3 + TypeScript + Tailwind CSS frontend. Phases 8.1-8.7 done. Backend APIs for webhooks, events, and audit are fully implemented. Frontend has raw/unstyled Events.vue and Audit.vue pages plus no Webhooks page at all. Now we migrate all three to Mission Control design system.

## Current State
- Backend: webhooks CRUD (`/api/v1/webhooks`), events stream (`/api/v1/events`), audit log (`/api/v1/audit`)
- Frontend: Events.vue (raw HTML, 200+ lines), Audit.vue (raw HTML, 150+ lines), no Webhooks page
- Composable: `useEventStream.ts` exists (recent events for dashboard), but no `useWebhooks.ts`
- Capabilities: webhooks.read, webhooks.write, events.read, events.ack, audit.read

## Goal
Create a new WebhooksPage, and rewrite Events.vue and Audit.vue using the Mission Control design system components.

## Requirements

### 1. Composable: `useWebhooks.ts`
- Functions: `fetchWebhooks()`, `createWebhook(url, secret, eventFilter)`, `deleteWebhook(id)`
- Returns: `{ webhooks, loading, error }`
- Poll every 30s via `createPoller`

### 2. WebhooksPage.vue (NEW)
- Route: `/webhooks`
- Webhook list in UTable (columns: URL, Event Filter, Active, Created, Actions)
- URL column: truncated, monospace
- Event Filter: UBadge pills per filter, or "All events" badge
- Active: UBadge (ok=active, bad=inactive)
- Create webhook: UModal with UInput for URL + Secret, multi-line UInput for event filters (comma-separated)
- Delete: danger UButton with UModal confirmation
- Cap guards: webhooks.read, webhooks.write

### 3. Events.vue Rewrite
- Keep ALL existing functionality (stream selector, cursor pagination, polling, ACK, trace filter)
- Wrap in UCard sections
- Stream input → UInput, cursor → UInput type=number
- Polling toggle → UToggle
- Event table → UTable with columns: Cursor, Time, Type, Trace ID, Payload
- Type column: UBadge with `eventBadgeStatus()` colors
- Payload: monospace, truncated with click-to-expand
- ACK section: UButton + status UBadge
- USkeleton while loading, UEmpty when no events
- Trace filter → UInput variant=search

### 4. Audit.vue Rewrite
- Keep ALL existing functionality (actor filter, action filter, limit, detail view)
- Wrap in UCard sections
- Filters toolbar: UInput for actor + action, USelect for limit
- Audit table → UTable (columns: Time, Actor, Action, Resource, Trace ID)
- Actor column: UBadge for actor_type (user=info, device=ok, system=warn)
- Detail panel: UCard with formatted JSON, monospace
- USkeleton while loading, UEmpty when no entries

### 5. Navigation
- Add "Webhooks" nav item (cap: webhooks.read) — lightning bolt or webhook icon
- Events and Audit already in nav — keep them

## Technical Constraints
- `<script setup lang="ts">`
- Use CSS custom properties, not hardcoded colors
- Use `apiFetch`, `hasCap`, `useToastStore`, `createPoller`
- DO NOT modify backend code
- DO NOT create new UI components

## Files to Create/Modify
1. **CREATE** `frontend/src/composables/useWebhooks.ts`
2. **CREATE** `frontend/src/pages/WebhooksPage.vue`
3. **REWRITE** `frontend/src/pages/Events.vue`
4. **REWRITE** `frontend/src/pages/Audit.vue`
5. **MODIFY** `frontend/src/router.ts` — add `/webhooks` route
6. **MODIFY** `frontend/src/layouts/DefaultLayout.vue` — add Webhooks nav item

## API Reference
```
GET    /api/v1/webhooks                → list[WebhookOut]
POST   /api/v1/webhooks               → WebhookOut  {url, secret, event_filter?}
DELETE /api/v1/webhooks/{id}           → 204
GET    /api/v1/events                  → EventReadOut  ?stream=&cursor=&limit=
GET    /api/v1/events/recent           → list[RecentEventOut]  ?limit=
GET    /api/v1/events/{id}             → EventItemOut
POST   /api/v1/events/ack             → EventAckOut  {stream, subscriber_id, cursor}
GET    /api/v1/audit                   → list[AuditEntryOut]  ?actor_id=&action=&limit=
GET    /api/v1/audit/{id}              → AuditEntryOut
```

## After Completion
Update `ROADMAP.md`: mark Step 8 as done `[x]`
