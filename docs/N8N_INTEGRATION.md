# n8n Integration Guide

Connect HUBEX with [n8n](https://n8n.io/) to build powerful workflow automations.
n8n is included as a companion service in `docker-compose.full.yml`.

---

## Prerequisites

| Component | Default URL | Notes |
|-----------|-------------|-------|
| HUBEX Backend | `http://localhost:8000` | API must be reachable from n8n |
| HUBEX Frontend | `http://localhost` | For dashboard links in notifications |
| n8n | `http://localhost:5678` | Included in `docker-compose.full.yml` |

Start the full stack:

```bash
docker-compose -f docker-compose.full.yml up -d
```

---

## How It Works

HUBEX dispatches events to registered webhook URLs whenever things happen in the system (device goes offline, alert fires, variable changes, etc.). n8n receives these events via its Webhook trigger node and can then route, transform, and act on them.

```
HUBEX Event  --->  Webhook Dispatcher  --->  n8n Webhook Node  --->  Your Workflow
                   (retries, HMAC sig)       (receives POST)        (email, Slack, API, ...)
```

### Payload Format

Every webhook delivery sends a JSON body like this:

```json
{
  "event": "alert.fired",
  "timestamp": "2025-01-15T10:30:00+00:00",
  "stream": "system",
  "event_id": 42,
  "data": { ... },
  "hubex_signature": "sha256=..."
}
```

The `X-Hubex-Signature` header contains an HMAC-SHA256 signature for verification.

---

## Step 1: Create a Webhook in HUBEX

1. Open HUBEX and navigate to **Tools > Webhooks**
2. Click **+ New Webhook**
3. Fill in:
   - **URL**: The n8n webhook URL (see Step 2)
   - **Secret**: A shared secret string (e.g., `my-hubex-secret`)
   - **Event Filter**: Comma-separated event types (leave empty for all events)
     - Examples: `alert.fired`, `device.offline`, `variable.changed`, `device.paired`
4. Click **Create**

Alternatively, use the API:

```bash
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://hubex-n8n:5678/webhook/hubex-alert",
    "secret": "my-hubex-secret",
    "event_filter": ["alert.fired"]
  }'
```

> **Note:** When running in Docker, use the container name `hubex-n8n` instead of `localhost` for the webhook URL.

---

## Step 2: Import a Workflow Template in n8n

1. Open n8n at `http://localhost:5678`
2. Click **Add workflow** (or the `+` button)
3. Click the `...` menu and select **Import from File**
4. Choose one of the template files from `docs/n8n/`:
   - `alert-to-email.json` — Send email notifications for alerts
   - `device-offline-slack.json` — Slack notifications when devices go offline
   - `data-to-google-sheets.json` — Export variable history to Google Sheets
   - `bidirectional-control.json` — Auto-control devices based on thresholds

---

## Step 3: Configure the Workflow

After importing, you need to configure credentials and URLs:

### For Webhook-triggered workflows

1. Click the **Webhook** node
2. Copy the **Production URL** (e.g., `http://localhost:5678/webhook/hubex-alert`)
3. Use this URL when creating the webhook in HUBEX (Step 1)

### For HTTP Request nodes (API calls to HUBEX)

1. Create an **HTTP Header Auth** credential in n8n:
   - Name: `HUBEX API Token`
   - Header Name: `Authorization`
   - Header Value: `Bearer YOUR_JWT_TOKEN`
2. Assign this credential to any HTTP Request node

### For Email (SMTP)

1. Create an **SMTP** credential in n8n with your email server settings
2. Update the `fromEmail` and `toEmail` in the Send Email node

### For Slack

1. Create a **Slack API** credential in n8n
2. Update the channel name in the Slack node

### For Google Sheets

1. Create a **Google Sheets OAuth2** credential in n8n
2. Update the spreadsheet ID in the Google Sheets node

---

## Step 4: Test the Integration

1. **Activate** the workflow in n8n (toggle in the top-right corner)
2. In HUBEX, go to **Tools > Webhooks** and click **Test** on your webhook
3. Check the n8n **Executions** tab to verify the workflow ran
4. Check HUBEX **Webhooks > Deliveries** to see delivery status

### Test via API

```bash
# Trigger a test event
curl -X POST http://localhost:5678/webhook-test/hubex-alert \
  -H "Content-Type: application/json" \
  -d '{
    "event": "alert.fired",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S+00:00)'",
    "stream": "system",
    "event_id": 999,
    "data": {
      "severity": "warning",
      "title": "Temperature High",
      "message": "Server room temperature is 35.2C",
      "device_name": "Sensor-Room-1"
    }
  }'
```

---

## Available Workflow Templates

### 1. Alert to Email (`alert-to-email.json`)

Sends formatted HTML email notifications when HUBEX alerts fire.

**Flow:** Webhook Trigger --> Format Email --> Send via SMTP

**Configure:** SMTP credentials, sender/recipient email addresses.

### 2. Device Offline to Slack (`device-offline-slack.json`)

Posts a Slack message when a device goes offline.

**Flow:** Webhook Trigger --> Filter (device.offline) --> Format Message --> Send to Slack

**Configure:** Slack API credentials, channel name.

### 3. Data to Google Sheets (`data-to-google-sheets.json`)

Exports variable history (e.g., temperature readings) to a Google Sheet every hour.

**Flow:** Schedule (hourly) --> HTTP GET /api/v1/variables/history --> Transform --> Append to Sheet

**Configure:** HUBEX API token, Google Sheets OAuth2 credentials, spreadsheet ID.

### 4. Bidirectional Control (`bidirectional-control.json`)

Automatically sets HVAC to cooling mode when temperature exceeds 30 degrees.

**Flow:** Webhook Trigger --> Extract Temperature --> Threshold Check --> POST /api/v1/variables/values

**Configure:** HUBEX API token for the HTTP Request node.

---

## Event Types Reference

| Event | Description | Typical Data |
|-------|-------------|--------------|
| `device.paired` | Device was paired | `uid`, `device_name`, `type` |
| `device.offline` | Device stopped sending data | `uid`, `device_name`, `last_seen` |
| `device.online` | Device came back online | `uid`, `device_name` |
| `alert.fired` | Alert condition triggered | `severity`, `title`, `message`, `device_name` |
| `alert.resolved` | Alert condition cleared | `severity`, `title`, `device_name` |
| `variable.changed` | Variable value changed | `key`, `value`, `device_uid`, `old_value` |
| `automation.executed` | Automation rule ran | `rule_id`, `rule_name`, `actions` |

---

## Troubleshooting

### Webhook not receiving events

1. Check that the webhook URL is correct and reachable from HUBEX
2. In Docker: use `hubex-n8n:5678` (container name), not `localhost:5678`
3. Verify the webhook is active: `GET /api/v1/webhooks`
4. Check delivery history: `GET /api/v1/webhooks/{id}/deliveries`

### n8n workflow not executing

1. Make sure the workflow is **activated** (toggle ON in n8n)
2. Check that you are using the **Production URL**, not the Test URL
3. Look at n8n Executions for errors

### HMAC signature verification

The signature is sent in the `X-Hubex-Signature` header. To verify in n8n:

```javascript
// In a Code node after the Webhook node:
const crypto = require('crypto');
const secret = 'my-hubex-secret';
const body = JSON.stringify($input.item.json);
const expected = crypto.createHmac('sha256', secret).update(body).digest('hex');
const received = $input.item.json.hubex_signature;
// Compare expected vs received
```

### Docker networking

When all services run in the same Docker Compose stack, use container names:
- HUBEX Backend: `http://hubex-backend:8000`
- n8n: `http://hubex-n8n:5678`

When running locally (not Docker), use `localhost` with the respective ports.

---

## Environment Variables

Add to your `.env` file:

```bash
# n8n URL (enables the integration card in HUBEX frontend)
HUBEX_N8N_URL=http://localhost:5678
```

Add to `frontend/.env`:

```bash
VITE_N8N_URL=http://localhost:5678
```
