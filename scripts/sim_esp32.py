#!/usr/bin/env python3
"""
sim_esp32.py — HUBEX ESP32 Hardware Simulator

Simulates a real ESP32 temperature/humidity sensor:
  - Auto-pairs with HUBEX
  - Sends periodic telemetry (temperature, humidity, pressure)
  - Values follow realistic daily cycles with noise
  - Sends heartbeat to stay online
  - Updates variables via PUT /variables/value

Usage:
  python scripts/sim_esp32.py --server http://localhost:8002
  python scripts/sim_esp32.py --server http://localhost:8002 --uid my-esp32

Requirements: requests (pip install requests)
"""

from __future__ import annotations
import argparse, json, math, random, signal, string, sys, time
from datetime import datetime, timezone
from typing import Any

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

RESET = "\033[0m"; BOLD = "\033[1m"
GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"; CYAN = "\033[96m"; DIM = "\033[2m"

def _ok(m): print(f"  {GREEN}✓ {m}{RESET}")
def _err(m): print(f"  {RED}✗ {m}{RESET}")
def _info(m): print(f"  {CYAN}→ {m}{RESET}")
def _warn(m): print(f"  {YELLOW}⚠ {m}{RESET}")

_running = True
def _stop(*_): global _running; _running = False; print(f"\n{YELLOW}Stopping…{RESET}")
signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)

def _get_requests():
    try:
        import requests
        return requests
    except ImportError:
        print(f"{RED}Error: pip install requests{RESET}")
        sys.exit(1)


def _login(requests, server, email, password):
    r = requests.post(f"{server}/api/v1/auth/login",
                      json={"email": email, "password": password}, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


def _do_pair(requests, server, uid, jwt):
    auth = {"Authorization": f"Bearer {jwt}"}
    r = requests.post(f"{server}/api/v1/devices/pairing/hello",
                      json={"device_uid": uid, "firmware_version": "sim-esp32-1.0",
                            "capabilities": {"sensors": ["temperature", "humidity", "pressure"]}},
                      timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("claimed"):
        raise RuntimeError("Device already claimed")
    code = data["pairing_code"]
    _info(f"Pairing code: {code}")

    r = requests.post(f"{server}/api/v1/devices/pairing/claim",
                      headers=auth, json={"pairing_code": code, "device_uid": uid}, timeout=15)
    r.raise_for_status()
    _ok("Claimed by user")

    r = requests.post(f"{server}/api/v1/devices/pairing/confirm",
                      json={"device_uid": uid, "pairing_code": code}, timeout=15)
    r.raise_for_status()
    token = r.json()["device_token"]
    _ok(f"Got token: {token[:16]}…")

    # Set device type and category
    device_id = r.json()["device_id"]
    requests.patch(f"{server}/api/v1/devices/{device_id}",
                   headers=auth,
                   json={"name": "ESP32 Sensor (Sim)", "device_type": "esp32", "category": "hardware"},
                   timeout=10)
    return token, device_id


def _heartbeat(requests, server, token):
    try:
        r = requests.post(f"{server}/api/v1/edge/heartbeat",
                          headers={"X-Device-Token": token},
                          json={"firmware_version": "sim-esp32-1.0"}, timeout=10)
        return r.status_code == 200
    except: return False


def _push_telemetry(requests, server, token, payload):
    try:
        r = requests.post(f"{server}/api/v1/telemetry",
                          headers={"X-Device-Token": token},
                          json={"event_type": "sensor_reading", "payload": payload}, timeout=10)
        return r.status_code in (200, 201)
    except Exception as e:
        _warn(f"Telemetry failed: {e}")
        return False


def _set_variable(requests, server, jwt, key, value, device_uid):
    try:
        r = requests.put(f"{server}/api/v1/variables/value",
                         headers={"Authorization": f"Bearer {jwt}"},
                         json={"key": key, "scope": "device", "deviceUid": device_uid, "value": value},
                         timeout=10)
        return r.status_code == 200
    except: return False


def _simulate_sensors(cycle: int) -> dict:
    """Generate realistic sensor readings with daily cycle + noise."""
    now = datetime.now(timezone.utc)
    hour_frac = (now.hour + now.minute / 60) / 24

    # Temperature: 18-28°C sinusoidal with noise
    temp = 23 + 5 * math.sin(2 * math.pi * (hour_frac - 0.25)) + random.gauss(0, 0.3)
    # Humidity: inverse of temp, 45-85%
    humidity = 65 - 15 * math.sin(2 * math.pi * (hour_frac - 0.25)) + random.gauss(0, 1.5)
    # Pressure: slow drift 1008-1018 hPa
    pressure = 1013 + 5 * math.sin(2 * math.pi * hour_frac * 0.3) + random.gauss(0, 0.3)
    # Battery: slowly decreasing from 100
    battery = max(10, 100 - cycle * 0.05 + random.gauss(0, 0.5))
    # WiFi RSSI: -30 to -80 dBm with jitter
    rssi = -50 + random.gauss(0, 5)

    return {
        "temperature": round(temp, 1),
        "humidity": round(max(0, min(100, humidity)), 1),
        "pressure": round(pressure, 1),
        "battery": round(battery, 1),
        "rssi": round(rssi, 0),
    }


def run(server, email, password, uid, interval, auto_pair, token):
    requests = _get_requests()

    print(f"\n{BOLD}{CYAN}╔═══════════════════════════════════════╗")
    print(f"║   HUBEX ESP32 Sensor Simulator        ║")
    print(f"╚═══════════════════════════════════════╝{RESET}")
    print(f"  Server:     {server}")
    print(f"  Device UID: {uid}")
    print(f"  Interval:   {interval}s\n")

    jwt = None
    device_id = None
    if auto_pair or not token:
        _info("Authenticating…")
        try:
            jwt = _login(requests, server, email, password)
            _ok("Logged in")
        except Exception as e:
            _err(f"Login failed: {e}"); return

    if auto_pair:
        _info(f"Pairing '{uid}'…")
        try:
            import sys, os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from sim_helpers import robust_pair
            token = robust_pair(requests, server, uid, jwt,
                                name="ESP32 Sensor (Sim)", device_type="esp32", category="hardware",
                                firmware="sim-esp32-1.0",
                                capabilities={"sensors": ["temperature", "humidity", "pressure"]})
            if not token:
                _err("Pairing failed"); return
        except Exception as e:
            _err(f"Pairing failed: {e}"); return
    elif not token:
        _err("No token. Use --auto-pair or --token"); return

    # Create variable definitions so telemetry bridge can match
    if jwt:
        try:
            from sim_helpers import ensure_variable_definitions, ESP32_VARIABLES
            n = ensure_variable_definitions(requests, server, jwt, ESP32_VARIABLES)
            if n: _ok(f"Created {n} variable definitions")
        except Exception:
            pass

    _ok(f"ESP32 Simulator running — Ctrl+C to stop\n")

    cycle = 0
    while _running:
        cycle += 1
        sensors = _simulate_sensors(cycle)

        print(f"{DIM}── Cycle {cycle} ──────────────────────────────{RESET}")
        _info(f"Sensors: T={sensors['temperature']}°C  H={sensors['humidity']}%  P={sensors['pressure']}hPa  Bat={sensors['battery']}%  RSSI={sensors['rssi']}dBm")

        # Heartbeat
        if _heartbeat(requests, server, token):
            _ok("Heartbeat")
        else:
            _warn("Heartbeat failed")

        # Push telemetry
        if _push_telemetry(requests, server, token, sensors):
            _ok(f"Telemetry sent ({len(sensors)} fields)")

        # Also update device-scoped variables (if jwt available)
        if jwt:
            for key, val in [("sim.temperature", sensors["temperature"]),
                              ("sim.humidity", sensors["humidity"]),
                              ("sim.pressure", sensors["pressure"])]:
                _set_variable(requests, server, jwt, key, val, uid)
            _ok("Variables updated")

        if not _running: break
        print(f"  {DIM}Next in {interval}s…{RESET}")
        for _ in range(interval * 2):
            if not _running: break
            time.sleep(0.5)

    print(f"\n{GREEN}ESP32 Simulator stopped.{RESET}")


if __name__ == "__main__":
    sfx = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    parser = argparse.ArgumentParser(description="HUBEX ESP32 Sensor Simulator")
    parser.add_argument("--server", default="http://localhost:8002")
    parser.add_argument("--email", default="codex+20251219002029@example.com")
    parser.add_argument("--password", default="Test1234!")
    parser.add_argument("--uid", default=f"sim-esp32-{sfx}")
    parser.add_argument("--interval", type=int, default=15, help="Seconds between readings")
    parser.add_argument("--auto-pair", action="store_true", default=True)
    parser.add_argument("--token", default=None)
    args = parser.parse_args()

    run(server=args.server.rstrip("/"), email=args.email, password=args.password,
        uid=args.uid, interval=args.interval, auto_pair=args.auto_pair, token=args.token)
