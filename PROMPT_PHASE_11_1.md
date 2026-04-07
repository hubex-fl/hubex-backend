# Phase 11.1 — n8n Webhook Templates

## Goal
Create ready-to-import n8n workflow JSON templates that automate common HUBEX scenarios:
1. Alert → Email notification
2. Telemetry → Google Sheets logging
3. Device offline → Slack message

These templates lower the barrier for users who want automation without writing code.

## Files to Create

### `docs/n8n/` directory with:

1. `hubex_alert_to_email.json` — n8n workflow
2. `hubex_telemetry_to_sheets.json` — n8n workflow
3. `hubex_device_offline_slack.json` — n8n workflow
4. `N8N_TEMPLATES.md` — setup guide

## Workflow Specs

### 1. `hubex_alert_to_email.json`
**Trigger:** Webhook node (POST, path `/hubex-alert`)
**Nodes:**
1. Webhook — receives HUBEX webhook payload (`event_type`, `device_uid`, `rule_name`, `message`, `severity`, `timestamp`)
2. IF — filter: only continue if `event_type == "alert.fired"`
3. Send Email (SMTP) — subject: `[HUBEX Alert] {{ $json.rule_name }}`, body: HTML with device_uid, message, severity, timestamp
4. Respond to Webhook — 200 OK

### 2. `hubex_telemetry_to_sheets.json`
**Trigger:** Webhook node (POST, path `/hubex-telemetry`)
**Nodes:**
1. Webhook — receives HUBEX telemetry event (`event_type: "telemetry.received"`, `device_uid`, `payload`, `timestamp`)
2. IF — filter: only `event_type == "telemetry.received"`
3. Code node — flatten `payload` fields into columns: `timestamp`, `device_uid`, `field1`, `field2`, ...
4. Google Sheets — Append Row to configured spreadsheet
5. Respond to Webhook — 200 OK

### 3. `hubex_device_offline_slack.json`
**Trigger:** Webhook node (POST, path `/hubex-device`)
**Nodes:**
1. Webhook — receives HUBEX device event
2. IF — filter: `event_type == "device.offline"`
3. Slack — send to `#alerts` channel: `⚠ Device offline: {{ $json.device_uid }} at {{ $json.timestamp }}`
4. Respond to Webhook — 200 OK

## n8n Workflow JSON Format
Use n8n v1.x format:
```json
{
  "name": "...",
  "nodes": [...],
  "connections": {...},
  "active": false,
  "settings": {"executionOrder": "v1"},
  "tags": ["hubex"]
}
```

Each node requires: `id` (UUID), `name`, `type` (e.g. `n8n-nodes-base.webhook`), `typeVersion`, `position` [x, y], `parameters`.

## After Completion
1. Update ROADMAP.md: Step 1 done, Step 2 ← AKTUELL
2. Write report to REPORTS.md
3. Generate PROMPT_PHASE_11_2.md (Custom n8n Node for HUBEX)
