# HUBEX n8n Workflow Templates

Ready-to-import n8n workflows for common HUBEX automation scenarios.

## Available Templates

| File | Scenario | Trigger |
|------|----------|---------|
| `hubex_alert_to_email.json` | Alert fired → send email | `alert.fired` event |
| `hubex_telemetry_to_sheets.json` | Telemetry received → append to Google Sheets | `telemetry.received` event |
| `hubex_device_offline_slack.json` | Device offline → Slack message | `device.offline` event |

## Prerequisites

- n8n instance (self-hosted or n8n Cloud)
- HUBEX instance with webhooks enabled
- Credentials configured in n8n (SMTP, Google Sheets, or Slack depending on template)

## Quick Setup

### 1. Import a Template

In n8n:
1. **Workflows** → **Import from File**
2. Select the `.json` file from `docs/n8n/`
3. Click **Import**

### 2. Register the Webhook in HUBEX

After importing, copy the webhook URL from the Webhook node in n8n (e.g. `https://n8n.example.com/webhook/hubex-alert`).

In HUBEX:
1. **Webhooks** → **New Webhook**
2. Paste the n8n URL as the target
3. Select the event types to subscribe to (see table above)
4. Save — HUBEX will now POST to n8n on every matching event

### 3. Configure Credentials

Each template uses placeholder credential IDs. Replace them:

**Alert to Email:**
- Open the `Send Alert Email` node
- Select or create an **SMTP** credential
- Set the `HUBEX_EMAIL_FROM` and `HUBEX_EMAIL_TO` variables in n8n Settings → Variables

**Telemetry to Sheets:**
- Open the `Append to Sheets` node
- Select or create a **Google Sheets OAuth2** credential
- Set `HUBEX_SHEETS_ID` variable to your spreadsheet ID (from the URL)
- Create a sheet named `Telemetry` in your spreadsheet (or change the sheet name in the node)

**Device Offline → Slack:**
- Open the `Slack Alert` node
- Select or create a **Slack** credential (Bot Token)
- Set `HUBEX_SLACK_CHANNEL` variable (default: `#alerts`)

### 4. Activate

Toggle the workflow to **Active** in n8n.

## HUBEX Webhook Payload Reference

HUBEX sends a JSON body on each event:

```json
{
  "event_type": "alert.fired",
  "device_uid": "esp32-abc123",
  "rule_name": "High Temperature",
  "message": "temperature_c exceeded threshold 40.0",
  "severity": "warning",
  "timestamp": "2026-03-28T12:00:00Z",
  "data": { ... }
}
```

Common `event_type` values:
- `device.paired` — new device paired
- `device.offline` — device missed heartbeat
- `device.online` — device came back online
- `telemetry.received` — device pushed telemetry (payload in `data.payload`)
- `alert.fired` — alert rule triggered
- `alert.resolved` — alert rule condition no longer met
- `task.completed` — device completed a task

## Customizing Templates

All templates filter by `event_type` using an IF node. To subscribe multiple templates to the same webhook endpoint, either:
- Register multiple HUBEX webhooks (one per n8n workflow), or
- Add a Switch node at the top to route by `event_type` into multiple branches

## Example: All-in-One Webhook

```
Webhook → Switch (by event_type)
  → alert.fired     → Send Email
  → device.offline  → Slack
  → telemetry.*     → Google Sheets
```
