#!/usr/bin/env python3
"""
api_device.py — HUBEX Virtual API Device

Connects any external REST API as a HUBEX device:
  - Pairs with HUBEX (auto-pair flow)
  - Periodically GETs data from a source URL
  - Pushes numeric fields as telemetry to HUBEX
  - Reads poll_interval_s variable from edge config

Usage:
  # Munich weather via Open-Meteo (no API key required)
  python scripts/api_device.py --auto-pair

  # Custom source
  python scripts/api_device.py \\
    --source-url https://api.example.com/data \\
    --fields temperature,pressure,humidity \\
    --uid my-virtual-sensor \\
    --auto-pair

  # Without auto-pair (device must already be paired or claimed manually)
  python scripts/api_device.py --uid my-device

Requirements: requests (pip install requests)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import signal
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
RESET = "\033[0m"; BOLD = "\033[1m"
GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"; CYAN = "\033[96m"; DIM = "\033[2m"

def _ok(m: str)   -> None: print(f"  {GREEN}✓ {m}{RESET}")
def _err(m: str)  -> None: print(f"  {RED}✗ {m}{RESET}")
def _info(m: str) -> None: print(f"  {CYAN}→ {m}{RESET}")
def _warn(m: str) -> None: print(f"  {YELLOW}⚠ {m}{RESET}")

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
_running = True

def _stop(*_: Any) -> None:
    global _running
    _running = False
    print(f"\n{YELLOW}Stopping…{RESET}")

try:
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
except ValueError:
    pass

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get_requests():
    try:
        import requests  # type: ignore
        return requests
    except ImportError:
        print(f"{RED}Error: 'requests' not installed. Run: pip install requests{RESET}")
        sys.exit(1)

def _login(requests, server: str, email: str, password: str) -> str:
    r = requests.post(f"{server}/api/v1/auth/login",
                      json={"email": email, "password": password}, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]

def _do_pair(requests, server: str, uid: str, jwt: str) -> str:
    """Full pairing flow: hello → user-claim → confirm → return device_token."""
    auth = {"Authorization": f"Bearer {jwt}"}

    # 1. Device hello (creates pairing session)
    r = requests.post(f"{server}/api/v1/devices/pairing/hello",
                      json={"device_uid": uid, "firmware_version": "api-device-1.0"}, timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("claimed"):
        raise RuntimeError("Device already claimed — use --uid with existing token or unclaim first")
    pairing_code = data["pairing_code"]
    _info(f"Pairing code: {pairing_code}")

    # 2. User claim (JWT)
    r = requests.post(f"{server}/api/v1/devices/pairing/claim",
                      headers=auth,
                      json={"pairing_code": pairing_code, "device_uid": uid}, timeout=15)
    r.raise_for_status()
    _ok("Device claimed by user")

    # 3. Device confirm → get permanent token
    r = requests.post(f"{server}/api/v1/devices/pairing/confirm",
                      json={"device_uid": uid, "pairing_code": pairing_code}, timeout=15)
    r.raise_for_status()
    token = r.json()["device_token"]
    _ok(f"Got device token: {token[:16]}…")
    return token

def _heartbeat(requests, server: str, token: str) -> bool:
    try:
        r = requests.post(f"{server}/api/v1/edge/heartbeat",
                          headers={"X-Device-Token": token},
                          json={"firmware_version": "api-device-1.0"}, timeout=10)
        return r.status_code == 200
    except Exception as e:
        _warn(f"Heartbeat failed: {e}")
        return False

def _get_config(requests, server: str, token: str) -> dict:
    try:
        r = requests.get(f"{server}/api/v1/edge/config",
                         headers={"X-Device-Token": token}, timeout=10)
        if r.status_code == 200:
            return r.json().get("variables", {})
    except Exception:
        pass
    return {}

def _push_telemetry(requests, server: str, token: str, payload: dict) -> bool:
    try:
        r = requests.post(f"{server}/api/v1/telemetry",
                          headers={"X-Device-Token": token},
                          json={"payload": payload}, timeout=10)
        return r.status_code in (200, 201)
    except Exception as e:
        _warn(f"Telemetry failed: {e}")
        return False

def _fetch_source(requests, url: str) -> dict | None:
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        _warn(f"Source fetch failed: {e}")
        return None

def _extract_fields(data: Any, field_names: list[str] | None) -> dict[str, float]:
    """Recursively extract numeric fields from JSON response."""
    result: dict[str, float] = {}

    def _walk(obj: Any, prefix: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                full_key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
                if field_names and k not in field_names and full_key not in field_names:
                    _walk(v, full_key)
                    continue
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    result[k] = float(v)
                elif isinstance(v, dict):
                    _walk(v, full_key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj[:1]):  # only first element of arrays
                _walk(item, prefix)

    _walk(data)

    # If specific fields requested but not found at top level, do a flat search
    if field_names:
        def _flat(obj: Any) -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in field_names and isinstance(v, (int, float)) and not isinstance(v, bool):
                        result[k] = float(v)
                    else:
                        _flat(v)
            elif isinstance(obj, list):
                for item in obj:
                    _flat(item)
        if not result:
            _flat(data)

    return result

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run(server: str, email: str, password: str, uid: str,
        source_url: str, interval: int, fields: list[str] | None,
        auto_pair: bool, token: str | None) -> None:

    requests = _get_requests()

    print(f"\n{BOLD}{CYAN}╔═══════════════════════════════════════╗")
    print(f"║     HUBEX Virtual API Device          ║")
    print(f"╚═══════════════════════════════════════╝{RESET}")
    print(f"  Server:     {server}")
    print(f"  Device UID: {uid}")
    print(f"  Source:     {source_url}")
    print(f"  Interval:   {interval}s\n")

    # Auth
    if auto_pair or not token:
        _info("Authenticating…")
        try:
            jwt = _login(requests, server, email, password)
            _ok("Logged in")
        except Exception as e:
            _err(f"Login failed: {e}")
            return

    # Pair
    if auto_pair:
        _info(f"Pairing device '{uid}'…")
        try:
            import os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from sim_helpers import robust_pair, ensure_variable_definitions, WEATHER_API_VARIABLES
            token = robust_pair(requests, server, uid, jwt,
                                name="Weather API (Sim)", device_type="api_device", category="service",
                                firmware="api-device-1.0")
            if not token:
                _err("Pairing failed"); return
            ensure_variable_definitions(requests, server, jwt, WEATHER_API_VARIABLES)
        except ImportError:
            # Fallback to old pair if sim_helpers not available
            try:
                token = _do_pair(requests, server, uid, jwt)
            except Exception as e:
                _err(f"Pairing failed: {e}"); return
        except Exception as e:
            _err(f"Pairing failed: {e}")
            return
    elif not token:
        _err("No device token. Use --auto-pair or --token <token>")
        return

    _ok(f"Device ready — starting poll loop (Ctrl+C to stop)\n")

    cycle = 0
    while _running:
        cycle += 1
        print(f"{DIM}── Cycle {cycle} ──────────────────────────────{RESET}")

        # Read config (may override interval)
        config = _get_config(requests, server, token)
        poll_interval = int(config.get("poll_interval_s", interval))
        if poll_interval != interval:
            _info(f"poll_interval_s override from config: {poll_interval}s")

        # Heartbeat
        if _heartbeat(requests, server, token):
            _ok("Heartbeat")
        else:
            _warn("Heartbeat failed — device may appear offline")

        # Fetch source data
        _info(f"Fetching {source_url}")
        raw = _fetch_source(requests, source_url)
        if raw is None:
            _warn("Source unavailable — skipping telemetry this cycle")
        else:
            payload = _extract_fields(raw, fields)
            if not payload:
                _warn("No numeric fields found in response")
                _info(f"Response keys: {list(raw.keys()) if isinstance(raw, dict) else type(raw).__name__}")
            else:
                _info(f"Extracted fields: {payload}")
                if _push_telemetry(requests, server, token, payload):
                    _ok(f"Telemetry pushed ({len(payload)} field(s))")
                else:
                    _warn("Telemetry push failed")

        if not _running:
            break

        print(f"  {DIM}Sleeping {poll_interval}s…{RESET}")
        # Sleep in small chunks so Ctrl+C is responsive
        for _ in range(poll_interval * 2):
            if not _running:
                break
            time.sleep(0.5)

    print(f"\n{GREEN}API device stopped.{RESET}")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))

    parser = argparse.ArgumentParser(description="HUBEX Virtual API Device")
    parser.add_argument("--server",    default="http://localhost:8000")
    parser.add_argument("--email",     default="codex+20251219002029@example.com")
    parser.add_argument("--password",  default="Test1234!")
    parser.add_argument("--uid",       default=f"api-device-{_suffix}",
                        help="Unique device UID")
    parser.add_argument("--source-url",
                        default=(
                            "https://api.open-meteo.com/v1/forecast"
                            "?latitude=48.1&longitude=11.6"
                            "&current=temperature_2m,wind_speed_10m,relative_humidity_2m"
                        ),
                        help="External API URL to poll")
    parser.add_argument("--fields",    default=None,
                        help="Comma-separated field names to extract (default: all numeric)")
    parser.add_argument("--interval",  type=int, default=30,
                        help="Poll interval in seconds (default: 30)")
    parser.add_argument("--auto-pair", action="store_true",
                        help="Automatically pair the device (login + hello + claim + confirm)")
    parser.add_argument("--token",     default=None,
                        help="Device token (skip pairing if already paired)")
    args = parser.parse_args()

    run(
        server=args.server.rstrip("/"),
        email=args.email,
        password=args.password,
        uid=args.uid,
        source_url=args.source_url,
        interval=args.interval,
        fields=[f.strip() for f in args.fields.split(",")] if args.fields else None,
        auto_pair=args.auto_pair,
        token=args.token,
    )
