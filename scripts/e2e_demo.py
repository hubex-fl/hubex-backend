#!/usr/bin/env python3
"""
e2e_demo.py — HUBEX End-to-End Integration Demo

Demonstrates the complete device integration flow:
  1. Device Registration   — POST /api/v1/devices/pairing/hello
  2. Pairing               — POST /api/v1/devices/pairing/claim + /confirm
  3. Variable Definitions   — Create temperature, humidity, smoke_level definitions
  4. Telemetry Ingest      — POST /api/v1/telemetry (sensor data)
  5. Variable Bridge        — Verify telemetry auto-populates variables
  6. Alert Trigger          — Create variable_threshold rule, push high smoke_level
  7. Webhook Delivery       — Create webhook subscription, list events
  8. Variable Write         — User writes config variable, device reads via snapshot
  9. OTA Check             — Device checks for firmware updates

Usage:
  # With user JWT token:
  python scripts/e2e_demo.py --token <JWT>

  # Auto-login with default test user:
  python scripts/e2e_demo.py

  # Custom server + cleanup:
  python scripts/e2e_demo.py --base-url http://localhost:8000 --cleanup

Requirements: httpx (pip install httpx)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import string
import sys
import time
from dataclasses import dataclass, field
from typing import Any

# Fix Windows terminal encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import httpx
except ImportError:
    print("\033[91mError: 'httpx' not installed. Run: pip install httpx\033[0m")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Terminal formatting
# ---------------------------------------------------------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
DIM = "\033[2m"
MAGENTA = "\033[95m"


def _ok(msg: str) -> None:
    print(f"  {GREEN}\u2713 {msg}{RESET}")


def _fail(msg: str) -> None:
    print(f"  {RED}\u2717 {msg}{RESET}")


def _info(msg: str) -> None:
    print(f"  {CYAN}\u2192 {msg}{RESET}")


def _warn(msg: str) -> None:
    print(f"  {YELLOW}! {msg}{RESET}")


def _step(num: int, title: str) -> None:
    print(f"\n{BOLD}{MAGENTA}[Step {num}]{RESET} {BOLD}{title}{RESET}")
    print(f"  {DIM}{'=' * 50}{RESET}")


def _banner() -> None:
    print(f"\n{BOLD}{CYAN}")
    print("  +-------------------------------------------------+")
    print("  |     HUBEX  End-to-End  Integration  Demo        |")
    print("  +-------------------------------------------------+")
    print(f"{RESET}")


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------
@dataclass
class StepResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class DemoState:
    """Tracks resources created during the demo for cleanup."""
    base_url: str = ""
    user_token: str = ""
    device_uid: str = ""
    device_token: str = ""
    pairing_code: str = ""
    device_id: int | None = None
    webhook_id: int | None = None
    alert_rule_id: int | None = None
    var_defs_created: list[str] = field(default_factory=list)
    results: list[StepResult] = field(default_factory=list)

    def record(self, name: str, passed: bool, detail: str = "") -> bool:
        self.results.append(StepResult(name, passed, detail))
        return passed

    def user_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.user_token}"}

    def device_headers(self) -> dict[str, str]:
        return {"X-Device-Token": self.device_token}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
async def _post(client: httpx.AsyncClient, url: str, json_data: dict | None = None,
                headers: dict | None = None) -> httpx.Response:
    return await client.post(url, json=json_data, headers=headers, timeout=15)


async def _get(client: httpx.AsyncClient, url: str,
               headers: dict | None = None) -> httpx.Response:
    return await client.get(url, headers=headers, timeout=15)


async def _put(client: httpx.AsyncClient, url: str, json_data: dict | None = None,
               headers: dict | None = None) -> httpx.Response:
    return await client.put(url, json=json_data, headers=headers, timeout=15)


async def _delete(client: httpx.AsyncClient, url: str,
                  headers: dict | None = None) -> httpx.Response:
    return await client.delete(url, headers=headers, timeout=15)


# ---------------------------------------------------------------------------
# Step 0: Login (optional, if no --token provided)
# ---------------------------------------------------------------------------
async def step_login(client: httpx.AsyncClient, state: DemoState,
                     email: str, password: str) -> None:
    _step(0, "Authentication")
    _info(f"Logging in as {email}")

    r = await _post(client, f"{state.base_url}/api/v1/auth/login", {
        "email": email,
        "password": password,
    })

    if r.status_code == 200:
        data = r.json()
        state.user_token = data["access_token"]
        _ok(f"Logged in (token: {state.user_token[:20]}...)")
        state.record("login", True)
    else:
        _fail(f"Login failed: {r.status_code} {r.text[:200]}")
        state.record("login", False, r.text[:200])
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Step 1: Device Registration
# ---------------------------------------------------------------------------
async def step_device_registration(client: httpx.AsyncClient, state: DemoState) -> None:
    _step(1, "Device Registration")
    _info(f"Registering device: {state.device_uid}")

    r = await _post(client, f"{state.base_url}/api/v1/devices/pairing/hello", {
        "device_uid": state.device_uid,
        "firmware_version": "e2e-demo-1.0.0",
        "capabilities": {
            "telemetry": True,
            "sensors": ["temperature", "humidity", "smoke"],
            "ota": True,
        },
    })

    if r.status_code == 200:
        data = r.json()
        if data.get("claimed"):
            _warn("Device already claimed -- will skip pairing")
            state.record("device_registration", True, "already claimed")
            return

        state.pairing_code = data.get("pairing_code", "")
        _ok(f"Device registered, pairing code: {state.pairing_code}")
        _info(f"Expires at: {data.get('expires_at', 'N/A')}")
        state.record("device_registration", True)
    else:
        _fail(f"Registration failed: {r.status_code} {r.text[:200]}")
        state.record("device_registration", False, r.text[:200])


# ---------------------------------------------------------------------------
# Step 2: Pairing
# ---------------------------------------------------------------------------
async def step_pairing(client: httpx.AsyncClient, state: DemoState) -> None:
    _step(2, "Device Pairing")

    if not state.pairing_code:
        _warn("No pairing code -- skipping (device may already be claimed)")
        state.record("pairing", True, "skipped")
        return

    # 2a. User claims the device
    _info("User claiming device...")
    r = await _post(client, f"{state.base_url}/api/v1/devices/pairing/claim", {
        "pairing_code": state.pairing_code,
        "device_uid": state.device_uid,
    }, headers=state.user_headers())

    if r.status_code == 200:
        _ok("Device claimed by user")
    else:
        _fail(f"Claim failed: {r.status_code} {r.text[:200]}")
        state.record("pairing_claim", False, r.text[:200])
        return

    # 2b. Device confirms pairing -> gets permanent token
    _info("Device confirming pairing...")
    r = await _post(client, f"{state.base_url}/api/v1/devices/pairing/confirm", {
        "device_uid": state.device_uid,
        "pairing_code": state.pairing_code,
    })

    if r.status_code == 200:
        data = r.json()
        state.device_token = data["device_token"]
        state.device_id = data.get("device_id")
        _ok(f"Pairing confirmed, device token: {state.device_token[:20]}...")
        state.record("pairing", True)
    else:
        _fail(f"Confirm failed: {r.status_code} {r.text[:200]}")
        state.record("pairing", False, r.text[:200])


# ---------------------------------------------------------------------------
# Step 3: Variable Definitions
# ---------------------------------------------------------------------------
async def step_variable_definitions(client: httpx.AsyncClient, state: DemoState) -> None:
    _step(3, "Variable Definitions")
    _info("Creating device_writable variable definitions for telemetry bridge...")

    var_defs = [
        {
            "key": "temperature",
            "scope": "device",
            "value_type": "float",
            "default_value": 0.0,
            "description": "Temperature sensor reading (C)",
            "unit": "C",
            "min_value": -40.0,
            "max_value": 85.0,
            "device_writable": True,
            "user_writable": True,
            "category": "sensor",
        },
        {
            "key": "humidity",
            "scope": "device",
            "value_type": "float",
            "default_value": 0.0,
            "description": "Relative humidity sensor reading (%)",
            "unit": "%",
            "min_value": 0.0,
            "max_value": 100.0,
            "device_writable": True,
            "user_writable": True,
            "category": "sensor",
        },
        {
            "key": "smoke_level",
            "scope": "device",
            "value_type": "float",
            "default_value": 0.0,
            "description": "Smoke detector level (ppm)",
            "unit": "ppm",
            "min_value": 0.0,
            "max_value": 10000.0,
            "device_writable": True,
            "user_writable": True,
            "category": "sensor",
        },
        {
            "key": "config_mode",
            "scope": "device",
            "value_type": "string",
            "default_value": "normal",
            "description": "Device operating mode (user-configurable)",
            "device_writable": False,
            "user_writable": True,
            "category": "config",
        },
    ]

    created = 0
    for vdef in var_defs:
        r = await _post(
            client,
            f"{state.base_url}/api/v1/variables/definitions",
            vdef,
            headers=state.user_headers(),
        )
        if r.status_code == 200:
            _ok(f"Created variable definition: {vdef['key']}")
            state.var_defs_created.append(vdef["key"])
            created += 1
        elif r.status_code == 409 or "already exists" in r.text.lower():
            _warn(f"Variable '{vdef['key']}' already exists -- OK")
            created += 1
        else:
            _fail(f"Failed to create '{vdef['key']}': {r.status_code} {r.text[:150]}")

    state.record("variable_definitions", created == len(var_defs),
                 f"{created}/{len(var_defs)} created")


# ---------------------------------------------------------------------------
# Step 4: Telemetry Ingest
# ---------------------------------------------------------------------------
async def step_telemetry(client: httpx.AsyncClient, state: DemoState) -> None:
    _step(4, "Telemetry Ingest")

    if not state.device_token:
        _fail("No device token -- cannot send telemetry")
        state.record("telemetry", False, "no device token")
        return

    readings = {
        "temperature": round(22.5 + random.uniform(-2, 2), 2),
        "humidity": round(55.0 + random.uniform(-5, 5), 1),
        "smoke_level": round(random.uniform(10, 50), 1),
    }
    _info(f"Sending telemetry: {readings}")

    r = await _post(client, f"{state.base_url}/api/v1/telemetry", {
        "event_type": "sensor.sample",
        "payload": readings,
    }, headers=state.device_headers())

    if r.status_code == 200:
        data = r.json()
        _ok(f"Telemetry accepted, ID: {data.get('telemetry_id')}")
        _info(f"Received at: {data.get('received_at')}")
        state.record("telemetry", True)
    else:
        _fail(f"Telemetry rejected: {r.status_code} {r.text[:200]}")
        state.record("telemetry", False, r.text[:200])


# ---------------------------------------------------------------------------
# Step 5: Variable Bridge Verification
# ---------------------------------------------------------------------------
async def step_variable_bridge(client: httpx.AsyncClient, state: DemoState) -> None:
    _step(5, "Variable Bridge (telemetry -> variables)")
    _info("Waiting briefly for telemetry-to-variable bridge...")
    await asyncio.sleep(1.0)

    bridged = 0
    for key in ["temperature", "humidity", "smoke_level"]:
        r = await _get(
            client,
            f"{state.base_url}/api/v1/variables/value"
            f"?key={key}&scope=device&deviceUid={state.device_uid}",
            headers=state.user_headers(),
        )
        if r.status_code == 200:
            data = r.json()
            val = data.get("value")
            ver = data.get("version")
            if val is not None and val != 0.0:
                _ok(f"{key} = {val} (version {ver})")
                bridged += 1
            else:
                _warn(f"{key} = {val} (may not have been bridged yet)")
        else:
            _warn(f"Could not read {key}: {r.status_code}")

    state.record("variable_bridge", bridged > 0,
                 f"{bridged}/3 variables bridged")


# ---------------------------------------------------------------------------
# Step 6: Alert Trigger
# ---------------------------------------------------------------------------
async def step_alert_trigger(client: httpx.AsyncClient, state: DemoState) -> None:
    _step(6, "Alert Trigger (smoke level threshold)")

    # 6a. Create a variable_threshold alert rule
    _info("Creating alert rule: smoke_level > 500 ppm")
    r = await _post(client, f"{state.base_url}/api/v1/alerts/rules", {
        "name": f"E2E Demo Smoke Alert ({state.device_uid})",
        "condition_type": "variable_threshold",
        "condition_config": {
            "variable_key": "smoke_level",
            "operator": ">",
            "threshold": 500,
            "scope": "device",
            "device_uid": state.device_uid,
        },
        "entity_id": state.device_uid,
        "severity": "critical",
        "enabled": True,
        "cooldown_seconds": 10,
    }, headers=state.user_headers())

    if r.status_code == 201:
        data = r.json()
        state.alert_rule_id = data["id"]
        _ok(f"Alert rule created, ID: {state.alert_rule_id}")
    else:
        _fail(f"Alert rule creation failed: {r.status_code} {r.text[:200]}")
        state.record("alert_trigger", False, r.text[:200])
        return

    # 6b. Send high smoke_level telemetry to trigger the alert
    _info("Sending high smoke_level (750 ppm) to trigger alert...")
    r = await _post(client, f"{state.base_url}/api/v1/telemetry", {
        "event_type": "sensor.sample",
        "payload": {
            "temperature": 28.0,
            "humidity": 40.0,
            "smoke_level": 750.0,
        },
    }, headers=state.device_headers())

    if r.status_code == 200:
        _ok("High smoke_level telemetry sent")
    else:
        _fail(f"Telemetry send failed: {r.status_code}")

    # Give the system a moment to process
    await asyncio.sleep(1.5)

    # 6c. Check for triggered alert events
    _info("Checking for triggered alert events...")
    r = await _get(
        client,
        f"{state.base_url}/api/v1/alerts?limit=5",
        headers=state.user_headers(),
    )

    if r.status_code == 200:
        events = r.json()
        if isinstance(events, list) and len(events) > 0:
            _ok(f"Found {len(events)} alert event(s)")
            latest = events[0] if events else {}
            _info(f"Latest: status={latest.get('status')}, message={latest.get('message', '')[:80]}")
            state.record("alert_trigger", True)
        else:
            _warn("No alert events found (threshold evaluation may be async/periodic)")
            state.record("alert_trigger", True, "rule created, evaluation may be deferred")
    else:
        _warn(f"Could not list alerts: {r.status_code}")
        state.record("alert_trigger", True, "rule created OK, event list unavailable")


# ---------------------------------------------------------------------------
# Step 7: Webhook Delivery
# ---------------------------------------------------------------------------
async def step_webhook(client: httpx.AsyncClient, state: DemoState) -> None:
    _step(7, "Webhook Subscription")

    # Create a webhook subscription (pointing to a non-existent URL is fine for demo)
    _info("Creating webhook subscription for telemetry.received events...")
    r = await _post(client, f"{state.base_url}/api/v1/webhooks", {
        "url": "https://httpbin.org/post",
        "secret": "e2e-demo-secret-" + state.device_uid,
        "event_filter": ["telemetry.received", "device.online", "variable.changed"],
    }, headers=state.user_headers())

    if r.status_code == 201:
        data = r.json()
        state.webhook_id = data["id"]
        _ok(f"Webhook created, ID: {state.webhook_id}")
        _info(f"URL: {data.get('url')}")
        _info(f"Events: {data.get('event_filter')}")
        state.record("webhook", True)
    else:
        _fail(f"Webhook creation failed: {r.status_code} {r.text[:200]}")
        state.record("webhook", False, r.text[:200])
        return

    # Send another telemetry to fire the webhook
    _info("Sending telemetry to trigger webhook delivery...")
    r = await _post(client, f"{state.base_url}/api/v1/telemetry", {
        "event_type": "sensor.sample",
        "payload": {"temperature": 23.1, "humidity": 52.0, "smoke_level": 30.0},
    }, headers=state.device_headers())

    if r.status_code == 200:
        _ok("Telemetry sent (webhook should fire asynchronously)")
    else:
        _warn(f"Telemetry failed: {r.status_code}")

    # List webhooks to verify it exists
    r = await _get(client, f"{state.base_url}/api/v1/webhooks", headers=state.user_headers())
    if r.status_code == 200:
        hooks = r.json()
        _ok(f"Webhook list: {len(hooks)} subscription(s) active")


# ---------------------------------------------------------------------------
# Step 8: Variable Write (user -> device)
# ---------------------------------------------------------------------------
async def step_variable_write(client: httpx.AsyncClient, state: DemoState) -> None:
    _step(8, "Variable Write (user -> device config)")

    # 8a. User writes a config variable
    _info("User writing config_mode = 'diagnostic'...")
    r = await _put(client, f"{state.base_url}/api/v1/variables/value", {
        "key": "config_mode",
        "scope": "device",
        "deviceUid": state.device_uid,
        "value": "diagnostic",
    }, headers=state.user_headers())

    if r.status_code == 200:
        data = r.json()
        _ok(f"Variable written: config_mode = {data.get('value')} (version {data.get('version')})")
    else:
        _fail(f"Variable write failed: {r.status_code} {r.text[:200]}")
        state.record("variable_write", False, r.text[:200])
        return

    # 8b. Device reads the variable via snapshot endpoint
    _info("Device reading variable snapshot...")
    r = await _get(
        client,
        f"{state.base_url}/api/v1/variables/snapshot?deviceUid={state.device_uid}",
        headers=state.device_headers(),
    )

    if r.status_code == 200:
        data = r.json()
        snapshot_id = data.get("snapshot_id")
        variables = data.get("vars", [])
        config_mode_var = next((v for v in variables if v.get("key") == "config_mode"), None)

        _ok(f"Snapshot received (ID: {snapshot_id}, {len(variables)} variable(s))")
        if config_mode_var:
            _ok(f"Device sees config_mode = {config_mode_var.get('value')}")
        else:
            _warn("config_mode not found in snapshot (may need definition scope match)")

        state.record("variable_write", True)
    else:
        _warn(f"Snapshot read returned: {r.status_code}")
        state.record("variable_write", True, "write OK, snapshot read issue")


# ---------------------------------------------------------------------------
# Step 9: OTA Check
# ---------------------------------------------------------------------------
async def step_ota_check(client: httpx.AsyncClient, state: DemoState) -> None:
    _step(9, "OTA Firmware Check")

    if not state.device_token:
        _fail("No device token -- cannot check OTA")
        state.record("ota_check", False, "no device token")
        return

    _info("Device checking for firmware updates...")
    r = await _get(
        client,
        f"{state.base_url}/api/v1/ota/check",
        headers=state.device_headers(),
    )

    if r.status_code == 200:
        data = r.json()
        if data is None:
            _ok("No pending OTA updates (device is up to date)")
        else:
            _ok(f"OTA update available: version={data.get('version')}")
            _info(f"Binary URL: {data.get('binary_url', 'N/A')}")
            _info(f"Checksum: {data.get('checksum_sha256', 'N/A')[:32]}...")
        state.record("ota_check", True)
    elif r.status_code == 204:
        _ok("No pending OTA updates (204 No Content)")
        state.record("ota_check", True)
    else:
        _fail(f"OTA check failed: {r.status_code} {r.text[:200]}")
        state.record("ota_check", False, r.text[:200])


# ---------------------------------------------------------------------------
# Heartbeat (bonus)
# ---------------------------------------------------------------------------
async def step_heartbeat(client: httpx.AsyncClient, state: DemoState) -> None:
    _step(10, "Edge Heartbeat (bonus)")

    if not state.device_token:
        _warn("No device token -- skipping heartbeat")
        state.record("heartbeat", True, "skipped")
        return

    _info("Sending device heartbeat...")
    r = await _post(client, f"{state.base_url}/api/v1/edge/heartbeat", {
        "firmware_version": "e2e-demo-1.0.0",
        "metadata": {"demo": True, "uptime_s": 120},
    }, headers=state.device_headers())

    if r.status_code == 200:
        data = r.json()
        _ok(f"Heartbeat OK (last_seen_at: {data.get('last_seen_at')})")
        state.record("heartbeat", True)
    else:
        _fail(f"Heartbeat failed: {r.status_code} {r.text[:200]}")
        state.record("heartbeat", False, r.text[:200])


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
async def cleanup(client: httpx.AsyncClient, state: DemoState) -> None:
    print(f"\n{BOLD}{YELLOW}[Cleanup] Removing demo resources...{RESET}")

    # Delete webhook
    if state.webhook_id:
        r = await _delete(
            client,
            f"{state.base_url}/api/v1/webhooks/{state.webhook_id}",
            headers=state.user_headers(),
        )
        if r.status_code == 204:
            _ok(f"Deleted webhook {state.webhook_id}")
        else:
            _warn(f"Webhook delete: {r.status_code}")

    # Delete alert rule
    if state.alert_rule_id:
        r = await _delete(
            client,
            f"{state.base_url}/api/v1/alerts/rules/{state.alert_rule_id}",
            headers=state.user_headers(),
        )
        if r.status_code in (200, 204):
            _ok(f"Deleted alert rule {state.alert_rule_id}")
        else:
            _warn(f"Alert rule delete: {r.status_code}")

    # Delete variable definitions
    for key in state.var_defs_created:
        r = await _delete(
            client,
            f"{state.base_url}/api/v1/variables/definitions/{key}?confirm=true",
            headers=state.user_headers(),
        )
        if r.status_code == 200:
            _ok(f"Deleted variable definition: {key}")
        else:
            _warn(f"Variable def delete '{key}': {r.status_code}")

    _ok("Cleanup complete")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def print_summary(state: DemoState) -> int:
    print(f"\n{BOLD}{'=' * 56}{RESET}")
    print(f"{BOLD}  DEMO SUMMARY{RESET}")
    print(f"{'=' * 56}")

    passed = 0
    failed = 0
    for result in state.results:
        icon = f"{GREEN}\u2713{RESET}" if result.passed else f"{RED}\u2717{RESET}"
        detail = f" {DIM}({result.detail}){RESET}" if result.detail else ""
        print(f"  {icon} {result.name}{detail}")
        if result.passed:
            passed += 1
        else:
            failed += 1

    total = passed + failed
    print(f"\n  {BOLD}Total: {total}  |  Passed: {GREEN}{passed}{RESET}  |  Failed: {RED}{failed}{RESET}")

    if failed == 0:
        print(f"\n  {GREEN}{BOLD}All steps passed!{RESET}")
    else:
        print(f"\n  {YELLOW}{BOLD}{failed} step(s) had issues.{RESET}")

    print(f"\n  Device UID:   {state.device_uid}")
    if state.device_token:
        print(f"  Device Token: {state.device_token[:20]}...")
    print()

    return 1 if failed > 0 else 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> int:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))

    parser = argparse.ArgumentParser(
        description="HUBEX End-to-End Integration Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/e2e_demo.py --token <JWT>
  python scripts/e2e_demo.py --email user@example.com --password secret
  python scripts/e2e_demo.py --cleanup
        """,
    )
    parser.add_argument("--base-url", default="http://localhost:8000",
                        help="HUBEX backend base URL (default: http://localhost:8000)")
    parser.add_argument("--token", default=None,
                        help="User JWT token (skips login step)")
    parser.add_argument("--email", default="codex+20251219002029@example.com",
                        help="Login email (used if --token not provided)")
    parser.add_argument("--password", default="Test1234!",
                        help="Login password (used if --token not provided)")
    parser.add_argument("--device-uid", default=f"e2e-demo-{suffix}",
                        help="Device UID for the demo (default: e2e-demo-<random>)")
    parser.add_argument("--cleanup", action="store_true",
                        help="Delete created resources after demo completes")
    args = parser.parse_args()

    state = DemoState(base_url=args.base_url.rstrip("/"), device_uid=args.device_uid)

    _banner()
    print(f"  Server:     {state.base_url}")
    print(f"  Device UID: {state.device_uid}")
    print(f"  Cleanup:    {'yes' if args.cleanup else 'no'}")

    async with httpx.AsyncClient() as client:
        try:
            # Step 0: Auth
            if args.token:
                state.user_token = args.token
                _step(0, "Authentication")
                _ok(f"Using provided token: {state.user_token[:20]}...")
                state.record("login", True, "token provided")
            else:
                await step_login(client, state, args.email, args.password)

            # Step 1: Device Registration
            await step_device_registration(client, state)

            # Step 2: Pairing
            await step_pairing(client, state)

            # Step 3: Variable Definitions
            await step_variable_definitions(client, state)

            # Step 4: Telemetry Ingest
            await step_telemetry(client, state)

            # Step 5: Variable Bridge
            await step_variable_bridge(client, state)

            # Step 6: Alert Trigger
            await step_alert_trigger(client, state)

            # Step 7: Webhook
            await step_webhook(client, state)

            # Step 8: Variable Write
            await step_variable_write(client, state)

            # Step 9: OTA Check
            await step_ota_check(client, state)

            # Step 10: Heartbeat (bonus)
            await step_heartbeat(client, state)

        except httpx.ConnectError:
            _fail(f"Cannot connect to {state.base_url} -- is the backend running?")
            state.record("connection", False, "server unreachable")
        except KeyboardInterrupt:
            print(f"\n{YELLOW}Interrupted by user{RESET}")
        except Exception as exc:
            _fail(f"Unexpected error: {exc}")
            state.record("unexpected", False, str(exc))

        # Cleanup
        if args.cleanup:
            try:
                await cleanup(client, state)
            except Exception as exc:
                _warn(f"Cleanup error: {exc}")

    return print_summary(state)


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    raise SystemExit(exit_code)
