# Phase 11.2 — Custom n8n Node for HUBEX

## Goal
Build a custom n8n community node package (`n8n-nodes-hubex`) that allows n8n users to interact with HUBEX directly from the n8n node palette — without manually constructing HTTP requests.

## Files to Create

### `n8n-nodes-hubex/` (npm package)

```
n8n-nodes-hubex/
├── package.json
├── tsconfig.json
├── .eslintrc.js
├── nodes/
│   └── Hubex/
│       ├── Hubex.node.ts       ← main node
│       ├── HubexTrigger.node.ts ← trigger/webhook node
│       └── hubex.svg           ← node icon
└── credentials/
    └── HubexApi.credentials.ts
```

## Node Specs

### `HubexApi.credentials.ts`
Credential type: `hubexApi`
Fields:
- `serverUrl` — string, default `http://localhost:8000`
- `email` — string
- `password` — string (sensitive/password type)

Auth flow: on credential test, POST `/api/v1/auth/login` and verify `access_token` returned.

### `Hubex.node.ts` — Regular Node
Display name: `HUBEX`
Description: `Interact with HUBEX IoT platform`
Icon: `hubex.svg`
Category: `Communication`

**Resources and Operations:**

1. **Device**
   - `list` — GET `/api/v1/devices` — params: `page`, `limit`, `health` filter
   - `get` — GET `/api/v1/devices/{uid}` — param: `uid`
   - `getConfig` — GET `/edge/config` (device token auth)
   - `pushTelemetry` — POST `/api/v1/telemetry` (device token auth) — param: `payload` (JSON string)

2. **Telemetry**
   - `list` — GET `/api/v1/telemetry?device_uid=...` — params: `device_uid`, `limit`
   - `latest` — GET `/api/v1/telemetry/latest/{device_uid}`

3. **Alert**
   - `listRules` — GET `/api/v1/alerts/rules`
   - `listEvents` — GET `/api/v1/alerts/events` — params: `device_uid`, `limit`
   - `ackEvent` — POST `/api/v1/alerts/events/{id}/ack`

4. **Variable** (device variables)
   - `list` — GET `/api/v1/devices/{uid}/variables`
   - `set` — PUT `/api/v1/devices/{uid}/variables/{key}`
   - `delete` — DELETE `/api/v1/devices/{uid}/variables/{key}`

Auth: JWT — auto-login with credentials on each request (or cache token in node context).

### `HubexTrigger.node.ts` — Trigger Node
Display name: `HUBEX Trigger`
Description: `Receive HUBEX events via webhook`

Behavior:
- On activate: registers a webhook subscription via `POST /api/v1/webhooks` with the n8n webhook URL
- On deactivate: deletes the subscription via `DELETE /api/v1/webhooks/{id}`
- Webhook path: `/hubex-trigger`
- `event_types` parameter: multi-select of available event types

## package.json
```json
{
  "name": "n8n-nodes-hubex",
  "version": "0.1.0",
  "description": "n8n community node for HUBEX IoT platform",
  "keywords": ["n8n-community-node-package", "hubex", "iot"],
  "n8n": {
    "n8nNodesApiVersion": 1,
    "credentials": ["dist/credentials/HubexApi.credentials.js"],
    "nodes": ["dist/nodes/Hubex/Hubex.node.js", "dist/nodes/Hubex/HubexTrigger.node.js"]
  },
  "main": "index.js",
  "scripts": {
    "build": "tsc -p tsconfig.json",
    "dev": "tsc -p tsconfig.json --watch"
  }
}
```

## After Completion
1. Update ROADMAP.md: Step 2 done → Milestone 11 COMPLETE
2. Write report to REPORTS.md
3. Generate PROMPT_PHASE_12_1.md (API Docs Landing Page)
