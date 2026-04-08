"""HTML email templates for HUBEX notifications.

All templates use inline CSS for maximum email client compatibility.
"""
from datetime import datetime, timezone

# ── Base layout ──────────────────────────────────────────────────────────────

_BASE_STYLE = """
body { margin: 0; padding: 0; background-color: #111110; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif; }
.container { max-width: 600px; margin: 0 auto; padding: 24px; }
.card { background-color: #1a1a19; border: 1px solid #2a2a28; border-radius: 12px; padding: 24px; margin-bottom: 16px; }
.header { text-align: center; padding: 16px 0 24px 0; }
.logo { color: #F5A623; font-size: 20px; font-weight: 700; letter-spacing: 1px; }
.title { color: #e8e4de; font-size: 18px; font-weight: 600; margin: 0 0 8px 0; }
.subtitle { color: #a8a29e; font-size: 14px; margin: 0 0 16px 0; }
.label { color: #a8a29e; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 4px 0; }
.value { color: #e8e4de; font-size: 14px; margin: 0 0 12px 0; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; }
.badge-critical { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; }
.badge-warning { background-color: rgba(245, 166, 35, 0.15); color: #F5A623; }
.badge-info { background-color: rgba(45, 212, 191, 0.15); color: #2DD4BF; }
.divider { border: none; border-top: 1px solid #2a2a28; margin: 16px 0; }
.btn { display: inline-block; padding: 10px 20px; background-color: #F5A623; color: #111110; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 8px; }
.footer { text-align: center; padding: 16px 0; }
.footer-text { color: #78716c; font-size: 12px; }
.digest-row { padding: 10px 0; border-bottom: 1px solid #2a2a28; }
.digest-row:last-child { border-bottom: none; }
"""


def _severity_badge(severity: str) -> str:
    css_class = {
        "critical": "badge-critical",
        "warning": "badge-warning",
        "info": "badge-info",
    }.get(severity, "badge-warning")
    return f'<span class="{css_class}" style="display:inline-block;padding:2px 10px;border-radius:6px;font-size:12px;font-weight:600;">{severity.upper()}</span>'


def _wrap(content: str) -> str:
    """Wrap content in the base email layout."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><style>{_BASE_STYLE}</style></head>
<body style="margin:0;padding:0;background-color:#111110;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Inter',Roboto,sans-serif;">
<div style="max-width:600px;margin:0 auto;padding:24px;">
  <div style="text-align:center;padding:16px 0 24px 0;">
    <span style="color:#F5A623;font-size:20px;font-weight:700;letter-spacing:1px;">HUBEX</span>
  </div>
  {content}
  <div style="text-align:center;padding:16px 0;">
    <p style="color:#78716c;font-size:12px;margin:0;">This is an automated notification from HUBEX. You can change your notification preferences in Settings.</p>
  </div>
</div>
</body>
</html>"""


# ── Alert notification ────────────────────────────────────────────────────────

def render_alert_email(
    *,
    rule_name: str,
    severity: str,
    message: str,
    rule_id: int,
    alert_event_id: int,
    variable_key: str | None = None,
    device_name: str | None = None,
) -> str:
    """Render HTML email for an alert event."""
    details = ""
    if variable_key:
        details += f"""
    <p style="color:#a8a29e;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;margin:0 0 4px 0;">Variable</p>
    <p style="color:#e8e4de;font-size:14px;margin:0 0 12px 0;font-family:'IBM Plex Mono',monospace;">{variable_key}</p>"""
    if device_name:
        details += f"""
    <p style="color:#a8a29e;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;margin:0 0 4px 0;">Device</p>
    <p style="color:#e8e4de;font-size:14px;margin:0 0 12px 0;">{device_name}</p>"""

    badge = _severity_badge(severity)

    return _wrap(f"""
  <div style="background-color:#1a1a19;border:1px solid #2a2a28;border-radius:12px;padding:24px;margin-bottom:16px;">
    <p style="color:#e8e4de;font-size:18px;font-weight:600;margin:0 0 8px 0;">Alert Fired</p>
    <p style="color:#a8a29e;font-size:14px;margin:0 0 16px 0;">{rule_name}</p>
    {badge}
    <hr style="border:none;border-top:1px solid #2a2a28;margin:16px 0;">
    <p style="color:#a8a29e;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;margin:0 0 4px 0;">Message</p>
    <p style="color:#e8e4de;font-size:14px;margin:0 0 12px 0;">{message}</p>
    {details}
    <p style="color:#a8a29e;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;margin:0 0 4px 0;">Event ID</p>
    <p style="color:#e8e4de;font-size:14px;margin:0 0 12px 0;">#{alert_event_id}</p>
  </div>
  <div style="text-align:center;margin-bottom:16px;">
    <a href="/alerts" style="display:inline-block;padding:10px 20px;background-color:#F5A623;color:#111110;font-size:14px;font-weight:600;text-decoration:none;border-radius:8px;">View in HUBEX</a>
  </div>""")


# ── Device offline notification ───────────────────────────────────────────────

def render_device_offline_email(
    *,
    device_name: str,
    device_uid: str,
    device_id: int,
    offline_seconds: int,
) -> str:
    """Render HTML email for a device-offline event."""
    minutes = offline_seconds // 60

    return _wrap(f"""
  <div style="background-color:#1a1a19;border:1px solid #2a2a28;border-radius:12px;padding:24px;margin-bottom:16px;">
    <p style="color:#e8e4de;font-size:18px;font-weight:600;margin:0 0 8px 0;">Device Offline</p>
    <p style="color:#a8a29e;font-size:14px;margin:0 0 16px 0;">A device has not been seen for {minutes} minute(s).</p>
    {_severity_badge("warning")}
    <hr style="border:none;border-top:1px solid #2a2a28;margin:16px 0;">
    <p style="color:#a8a29e;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;margin:0 0 4px 0;">Device</p>
    <p style="color:#e8e4de;font-size:14px;margin:0 0 12px 0;">{device_name}</p>
    <p style="color:#a8a29e;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;margin:0 0 4px 0;">UID</p>
    <p style="color:#e8e4de;font-size:14px;margin:0 0 12px 0;font-family:'IBM Plex Mono',monospace;">{device_uid}</p>
    <p style="color:#a8a29e;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;margin:0 0 4px 0;">Last Seen</p>
    <p style="color:#e8e4de;font-size:14px;margin:0 0 12px 0;">{minutes} minute(s) ago</p>
  </div>
  <div style="text-align:center;margin-bottom:16px;">
    <a href="/devices/{device_id}" style="display:inline-block;padding:10px 20px;background-color:#F5A623;color:#111110;font-size:14px;font-weight:600;text-decoration:none;border-radius:8px;">View Device</a>
  </div>""")


# ── Automation error notification ─────────────────────────────────────────────

def render_automation_error_email(
    *,
    rule_name: str,
    rule_id: int,
    error_message: str,
) -> str:
    """Render HTML email for an automation error."""
    return _wrap(f"""
  <div style="background-color:#1a1a19;border:1px solid #2a2a28;border-radius:12px;padding:24px;margin-bottom:16px;">
    <p style="color:#e8e4de;font-size:18px;font-weight:600;margin:0 0 8px 0;">Automation Error</p>
    <p style="color:#a8a29e;font-size:14px;margin:0 0 16px 0;">{rule_name}</p>
    {_severity_badge("critical")}
    <hr style="border:none;border-top:1px solid #2a2a28;margin:16px 0;">
    <p style="color:#a8a29e;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;margin:0 0 4px 0;">Error</p>
    <p style="color:#ef4444;font-size:14px;margin:0 0 12px 0;font-family:'IBM Plex Mono',monospace;">{error_message}</p>
    <p style="color:#a8a29e;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;margin:0 0 4px 0;">Rule ID</p>
    <p style="color:#e8e4de;font-size:14px;margin:0 0 12px 0;">#{rule_id}</p>
  </div>
  <div style="text-align:center;margin-bottom:16px;">
    <a href="/automations" style="display:inline-block;padding:10px 20px;background-color:#F5A623;color:#111110;font-size:14px;font-weight:600;text-decoration:none;border-radius:8px;">View Automations</a>
  </div>""")


# ── Digest email ──────────────────────────────────────────────────────────────

def render_digest_email(
    *,
    period: str,  # "daily" or "weekly"
    alert_count: int,
    device_offline_count: int,
    automation_error_count: int,
    top_alerts: list[dict],  # [{rule_name, severity, count}]
) -> str:
    """Render HTML email for a daily/weekly digest summary."""
    period_label = "Daily" if period == "daily" else "Weekly"
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    alert_rows = ""
    for a in top_alerts[:10]:
        badge = _severity_badge(a.get("severity", "info"))
        count = a.get("count", 0)
        name = a.get("rule_name", "Unknown")
        alert_rows += f"""
        <div style="padding:10px 0;border-bottom:1px solid #2a2a28;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="color:#e8e4de;font-size:14px;">{name}</span>
            <span style="color:#a8a29e;font-size:12px;">{count}x</span>
          </div>
          <div style="margin-top:4px;">{badge}</div>
        </div>"""

    if not alert_rows:
        alert_rows = '<p style="color:#a8a29e;font-size:14px;">No alerts in this period.</p>'

    return _wrap(f"""
  <div style="background-color:#1a1a19;border:1px solid #2a2a28;border-radius:12px;padding:24px;margin-bottom:16px;">
    <p style="color:#e8e4de;font-size:18px;font-weight:600;margin:0 0 8px 0;">{period_label} Digest</p>
    <p style="color:#a8a29e;font-size:14px;margin:0 0 16px 0;">{now_str}</p>
    <hr style="border:none;border-top:1px solid #2a2a28;margin:16px 0;">

    <div style="display:flex;gap:16px;margin-bottom:16px;">
      <div style="flex:1;text-align:center;padding:12px;background-color:#111110;border-radius:8px;">
        <p style="color:#F5A623;font-size:24px;font-weight:700;margin:0;">{alert_count}</p>
        <p style="color:#a8a29e;font-size:12px;margin:4px 0 0 0;">Alerts</p>
      </div>
      <div style="flex:1;text-align:center;padding:12px;background-color:#111110;border-radius:8px;">
        <p style="color:#ef4444;font-size:24px;font-weight:700;margin:0;">{device_offline_count}</p>
        <p style="color:#a8a29e;font-size:12px;margin:4px 0 0 0;">Offline</p>
      </div>
      <div style="flex:1;text-align:center;padding:12px;background-color:#111110;border-radius:8px;">
        <p style="color:#a78bfa;font-size:24px;font-weight:700;margin:0;">{automation_error_count}</p>
        <p style="color:#a8a29e;font-size:12px;margin:4px 0 0 0;">Errors</p>
      </div>
    </div>

    <p style="color:#a8a29e;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;margin:0 0 8px 0;">Top Alerts</p>
    {alert_rows}
  </div>
  <div style="text-align:center;margin-bottom:16px;">
    <a href="/alerts" style="display:inline-block;padding:10px 20px;background-color:#F5A623;color:#111110;font-size:14px;font-weight:600;text-decoration:none;border-radius:8px;">Open HUBEX</a>
  </div>""")
