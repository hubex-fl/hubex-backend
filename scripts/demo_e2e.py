#!/usr/bin/env python3
"""
demo_e2e.py — HUBEX End-to-End Integration Demo

Simulates the full HUBEX device pipeline:
  1. Auth     — login, get JWT
  2. Pair     — device hello → user claim → device confirm → device token
  3. Telemetry — push simulated sensor readings (5 batches)
  4. Alert Rule — create a device_offline rule
  5. Webhook  — create a webhook listening for device.* events
  6. Events   — verify events were emitted
  7. Cleanup  — unclaim device, delete alert rule + webhook

Usage:
  python scripts/demo_e2e.py
  python scripts/demo_e2e.py --server http://localhost:8000
  python scripts/demo_e2e.py --email admin@example.com --password secret
  python scripts/demo_e2e.py --dry-run   (print steps without executing)
  python scripts/demo_e2e.py --keep      (skip cleanup)

Requirements: requests (pip install requests)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import random
import string
from typing import Any

# Fix Windows terminal encoding (cp1252 can't handle Unicode box-drawing/emoji)
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Terminal colors
# ---------------------------------------------------------------------------

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
DIM    = "\033[2m"


def ok(msg: str)   -> None: print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg: str) -> None: print(f"  {RED}❌ {msg}{RESET}")
def info(msg: str) -> None: print(f"  {CYAN}ℹ  {msg}{RESET}")
def warn(msg: str) -> None: print(f"  {YELLOW}⚠  {msg}{RESET}")
def step(n: int, title: str) -> None:
    print(f"\n{BOLD}Step {n}: {title}{RESET}")
    print(f"  {DIM}{'─' * 50}{RESET}")


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _req(method: str, url: str, headers: dict | None = None,
         json_body: Any = None, dry_run: bool = False) -> tuple[int, Any]:
    """Make an HTTP request. Returns (status_code, response_json_or_text)."""
    if dry_run:
        info(f"[DRY-RUN] {method} {url}")
        if json_body:
            info(f"          body: {json.dumps(json_body)[:120]}")
        return (200, {})

    try:
        import requests  # type: ignore
    except ImportError:
        print(f"{RED}Error: 'requests' is not installed.{RESET}")
        print("  Run: pip install requests")
        sys.exit(1)

    resp = requests.request(
        method, url,
        headers={**(headers or {}), "Content-Type": "application/json"},
        json=json_body,
        timeout=15,
    )
    try:
        data = resp.json()
    except Exception:
        data = resp.text
    return resp.status_code, data


# ---------------------------------------------------------------------------
# Demo steps
# ---------------------------------------------------------------------------

def run_demo(server: str, email: str, password: str,
             dry_run: bool, keep: bool) -> None:

    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════╗")
    print(f"║     HUBEX End-to-End Integration Demo    ║")
    print(f"╚══════════════════════════════════════════╝{RESET}")
    print(f"  Server:   {server}")
    print(f"  User:     {email}")
    if dry_run:
        print(f"  {YELLOW}Mode: DRY-RUN (no actual API calls){RESET}")

    device_uid   = "demo-esp32-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    jwt_token    = ""
    device_token = ""
    device_id    = -1
    pairing_code = ""
    alert_rule_id = -1
    webhook_id    = -1

    # ──────────────────────────────────────────────────────────────────────
    # Step 1: Auth
    # ──────────────────────────────────────────────────────────────────────
    step(1, "Authentication — Login")
    code, data = _req("POST", f"{server}/api/v1/auth/login",
                      json_body={"email": email, "password": password},
                      dry_run=dry_run)
    if code == 200 and isinstance(data, dict):
        jwt_token = data.get("access_token", "DRY-RUN-TOKEN")
        ok(f"Logged in — token starts with: {jwt_token[:20]}…")
    else:
        fail(f"Login failed ({code}): {data}")
        return

    auth_headers = {"Authorization": f"Bearer {jwt_token}"}

    # ──────────────────────────────────────────────────────────────────────
    # Step 2: Pairing
    # ──────────────────────────────────────────────────────────────────────
    step(2, f"Pairing — Device UID: {device_uid}")

    # 2a: Device hello (no auth)
    info("2a. Device → hello")
    code, data = _req("POST", f"{server}/api/v1/devices/pairing/hello",
                      json_body={"device_uid": device_uid, "firmware_version": "1.0.0"},
                      dry_run=dry_run)
    if code == 200 and isinstance(data, dict):
        pairing_code = data.get("pairing_code") or "DRY-PAIRING-CODE"
        ok(f"Device announced — pairing code: {pairing_code}")
    else:
        fail(f"Pairing hello failed ({code}): {data}")
        return

    # 2b: User claims the device (with JWT)
    info("2b. User → claim")
    code, data = _req("POST", f"{server}/api/v1/devices/pairing/claim",
                      headers=auth_headers,
                      json_body={"pairing_code": pairing_code, "device_uid": device_uid},
                      dry_run=dry_run)
    if code == 200 and isinstance(data, dict):
        ok(f"User claimed device — pairing_code: {data.get('pairing_code', pairing_code)}")
    else:
        fail(f"User claim failed ({code}): {data}")
        return

    # 2c: Device confirms → gets permanent token
    info("2c. Device → confirm (get token)")
    code, data = _req("POST", f"{server}/api/v1/devices/pairing/confirm",
                      json_body={"device_uid": device_uid, "pairing_code": pairing_code},
                      dry_run=dry_run)
    if code == 200 and isinstance(data, dict):
        device_token = data.get("device_token", "DRY-DEVICE-TOKEN")
        device_id    = data.get("device_id", -1)
        ok(f"Token received — device_id={device_id}, token={device_token[:16]}…")
    else:
        fail(f"Confirm failed ({code}): {data}")
        return

    device_headers = {"X-Device-Token": device_token}

    # ──────────────────────────────────────────────────────────────────────
    # Step 3: Telemetry
    # ──────────────────────────────────────────────────────────────────────
    step(3, "Telemetry — Push 5 sensor readings")

    for i in range(1, 6):
        temp     = round(random.uniform(18.0, 32.0), 1)
        humidity = round(random.uniform(40.0, 80.0), 1)
        rssi     = random.randint(-80, -30)
        payload  = {"temperature": temp, "humidity": humidity, "rssi": rssi, "seq": i}

        code, data = _req("POST", f"{server}/api/v1/telemetry",
                          headers=device_headers,
                          json_body={"payload": payload},
                          dry_run=dry_run)
        if code in (200, 201) or dry_run:
            ok(f"Reading {i}/5 — temp={temp}°C  humidity={humidity}%  rssi={rssi} dBm")
        else:
            warn(f"Telemetry {i} failed ({code}): {data}")
        time.sleep(0.2)

    # Step 3b: Heartbeat
    info("Sending heartbeat…")
    code, _ = _req("POST", f"{server}/api/v1/edge/heartbeat",
                   headers=device_headers,
                   json_body={"firmware_version": "1.0.0"},
                   dry_run=dry_run)
    if code == 200 or dry_run:
        ok("Heartbeat acknowledged — device is ONLINE")
    else:
        warn(f"Heartbeat failed ({code})")

    # ──────────────────────────────────────────────────────────────────────
    # Step 4: Alert Rule
    # ──────────────────────────────────────────────────────────────────────
    step(4, "Alert Rule — Create device_offline rule")

    rule_payload = {
        "name":             f"[Demo] Device offline: {device_uid}",
        "condition_type":   "device_offline",
        "condition_config": {"threshold_seconds": 120},
        "severity":         "warning",
        "enabled":          True,
        "cooldown_seconds": 300,
    }
    code, data = _req("POST", f"{server}/api/v1/alerts/rules",
                      headers=auth_headers,
                      json_body=rule_payload,
                      dry_run=dry_run)
    if code == 201 and isinstance(data, dict):
        alert_rule_id = data.get("id", -1)
        ok(f"Alert rule created — id={alert_rule_id}, name={data.get('name')}")
    elif dry_run:
        alert_rule_id = 0
        ok(f"Alert rule would be created")
    else:
        warn(f"Alert rule creation failed ({code}): {data}")

    # ──────────────────────────────────────────────────────────────────────
    # Step 5: Webhook
    # ──────────────────────────────────────────────────────────────────────
    step(5, "Webhook — Register n8n listener")

    # In production, replace with your n8n webhook URL
    webhook_url = "https://n8n.example.com/webhook/hubex-demo"
    wh_payload = {
        "url":          webhook_url,
        "secret":       "demo-secret-change-me",
        "event_filter": ["device.claimed", "device.telemetry", "alert.fired"],
    }
    code, data = _req("POST", f"{server}/api/v1/webhooks",
                      headers=auth_headers,
                      json_body=wh_payload,
                      dry_run=dry_run)
    if code == 201 and isinstance(data, dict):
        webhook_id = data.get("id", -1)
        ok(f"Webhook created — id={webhook_id}")
        ok(f"Listening for: {', '.join(wh_payload['event_filter'])}")
        info(f"n8n URL (configure in your n8n instance): {webhook_url}")
    elif dry_run:
        webhook_id = 0
        ok(f"Webhook would be created")
    else:
        warn(f"Webhook creation failed ({code}): {data}")

    # ──────────────────────────────────────────────────────────────────────
    # Step 6: Events
    # ──────────────────────────────────────────────────────────────────────
    step(6, "Events — Verify pipeline events were emitted")

    code, data = _req("GET", f"{server}/api/v1/events?stream=device&limit=10",
                      headers=auth_headers,
                      dry_run=dry_run)
    if code == 200 and isinstance(data, dict):
        events = data.get("items", data) if isinstance(data, dict) else data
        if isinstance(events, list):
            ok(f"Found {len(events)} recent device events")
            for ev in events[:3]:
                info(f"  [{ev.get('event_type','?')}] {ev.get('stream','?')} — {ev.get('created_at','?')[:19]}")
        else:
            ok("Events endpoint reachable")
    elif dry_run:
        ok("Events would be checked")
    else:
        warn(f"Events check failed ({code})")

    # ──────────────────────────────────────────────────────────────────────
    # Step 7: Edge Config
    # ──────────────────────────────────────────────────────────────────────
    step(7, "Edge Config — Device fetches variables + tasks")

    code, data = _req("GET", f"{server}/api/v1/edge/config",
                      headers=device_headers,
                      dry_run=dry_run)
    if (code == 200 and isinstance(data, dict)) or dry_run:
        vars_  = data.get("variables", {}) if isinstance(data, dict) else {}
        tasks_ = data.get("tasks", [])     if isinstance(data, dict) else []
        ok(f"Config received — {len(vars_)} variable(s), {len(tasks_)} pending task(s)")
    else:
        warn(f"Edge config failed ({code}): {data}")

    # ──────────────────────────────────────────────────────────────────────
    # Step 8: Cleanup
    # ──────────────────────────────────────────────────────────────────────
    if keep:
        warn("Skipping cleanup (--keep flag set)")
        print(f"\n{BOLD}Demo device preserved:{RESET}")
        info(f"  device_uid={device_uid}")
        info(f"  device_id={device_id}")
        info(f"  device_token={device_token[:20]}…")
    else:
        step(8, "Cleanup — Remove demo resources")

        # Unclaim device
        if device_id > 0:
            code, _ = _req("POST", f"{server}/api/v1/devices/{device_id}/unclaim",
                           headers=auth_headers, dry_run=dry_run)
            if code in (200, 404) or dry_run:
                ok(f"Device {device_uid} unclaimed")
            else:
                warn(f"Unclaim failed ({code})")

        # Delete alert rule
        if alert_rule_id > 0:
            code, _ = _req("DELETE", f"{server}/api/v1/alerts/rules/{alert_rule_id}",
                           headers=auth_headers, dry_run=dry_run)
            if code in (200, 204, 404) or dry_run:
                ok(f"Alert rule {alert_rule_id} deleted")
            else:
                warn(f"Alert rule delete failed ({code})")

        # Delete webhook
        if webhook_id > 0:
            code, _ = _req("DELETE", f"{server}/api/v1/webhooks/{webhook_id}",
                           headers=auth_headers, dry_run=dry_run)
            if code in (200, 204, 404) or dry_run:
                ok(f"Webhook {webhook_id} deleted")
            else:
                warn(f"Webhook delete failed ({code})")

    # ──────────────────────────────────────────────────────────────────────
    # Summary
    # ──────────────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{GREEN}{'═' * 50}{RESET}")
    print(f"{BOLD}{GREEN}  Demo complete!{RESET}")
    print(f"{BOLD}{GREEN}{'═' * 50}{RESET}")
    print(f"""
  Pipeline demonstrated:
  {GREEN}ESP32 Device{RESET} → pairing_hello
         ↓
  {CYAN}HUBEX Dashboard{RESET} → user claim
         ↓
  {GREEN}ESP32 Device{RESET} → confirm → {BOLD}device_token{RESET}
         ↓
  {GREEN}ESP32{RESET} → heartbeat + telemetry × 5
         ↓
  {CYAN}HUBEX{RESET} → emit events → trigger alert rule
         ↓
  {YELLOW}Webhook{RESET} → POST to n8n endpoint
         ↓
  {YELLOW}n8n{RESET} → workflow execution (email / Slack / etc.)

  To connect n8n:
    1. Create a Webhook node in n8n with any URL
    2. Update the webhook URL in this script
    3. Run again — events will flow through
""")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HUBEX E2E Integration Demo")
    parser.add_argument("--server",   default="http://localhost:8000",
                        help="HUBEX server base URL")
    parser.add_argument("--email",    default="codex+20251219002029@example.com",
                        help="User email")
    parser.add_argument("--password", default="Test1234!",
                        help="User password")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Print all steps without making API calls")
    parser.add_argument("--keep",     action="store_true",
                        help="Skip cleanup (preserve demo device/rules)")
    args = parser.parse_args()

    run_demo(
        server=args.server.rstrip("/"),
        email=args.email,
        password=args.password,
        dry_run=args.dry_run,
        keep=args.keep,
    )
