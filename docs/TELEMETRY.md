# Telemetry & Analytics

## Philosophy

HubEx collects **zero data by default**. Telemetry is fully opt-in and anonymized.

## What We Collect (when enabled)

| Data Point | Purpose | PII? |
|-----------|---------|------|
| HubEx version | Know which versions are in use | No |
| Device count (range) | Understand deployment size | No |
| Feature usage (which pages visited) | Prioritize development | No |
| Error counts (not details) | Quality monitoring | No |
| OS + Architecture | Build compatibility | No |

## What We NEVER Collect

- Device names, UIDs, or data
- Variable values or history
- User emails, passwords, or tokens
- IP addresses or geolocation
- Dashboard content or automation rules
- Any personally identifiable information

## How to Enable

```bash
# In .env:
HUBEX_TELEMETRY_ENABLED=true  # Default: false
```

## How to Verify

All telemetry data is logged locally before sending:
```
tail -f logs/telemetry.log
```

## How to Disable

Remove or set to false:
```bash
HUBEX_TELEMETRY_ENABLED=false
```

No data is collected after disabling. No stored data is sent retroactively.

## Data Destination

Telemetry is sent to `https://telemetry.hubex.io/v1/ping` (when service exists).
Currently: no telemetry endpoint active. Data is only logged locally.
