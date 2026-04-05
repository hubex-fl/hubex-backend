#!/usr/bin/env python3
"""
sim_mqtt_bridge.py — HUBEX MQTT Bridge Simulator

Simulates an MQTT Bridge device that:
  - Auto-pairs as a Bridge-type device
  - Simulates receiving MQTT messages (no real broker needed)
  - Publishes parsed sensor data as telemetry to HUBEX
  - Reports bridge status (connected topics, message rate)

In a real scenario this would connect to an MQTT broker via paho-mqtt.
This simulator generates realistic MQTT-like data without a broker dependency.

Usage:
  python scripts/sim_mqtt_bridge.py --server http://localhost:8002
  python scripts/sim_mqtt_bridge.py --server http://localhost:8002 --uid my-bridge

Requirements: requests (pip install requests)
Optional: paho-mqtt (pip install paho-mqtt) for real broker connection
"""

from __future__ import annotations
import argparse, json, math, random, signal, string, sys, time
from datetime import datetime, timezone
from typing import Any

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

RESET = "\033[0m"; BOLD = "\033[1m"
GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"; CYAN = "\033[96m"; DIM = "\033[2m"; MAGENTA = "\033[95m"

def _ok(m): print(f"  {GREEN}✓ {m}{RESET}")
def _err(m): print(f"  {RED}✗ {m}{RESET}")
def _info(m): print(f"  {CYAN}→ {m}{RESET}")
def _warn(m): print(f"  {YELLOW}⚠ {m}{RESET}")
def _mqtt(m): print(f"  {MAGENTA}⬡ {m}{RESET}")

_running = True
def _stop(*_): global _running; _running = False; print(f"\n{YELLOW}Stopping…{RESET}")
signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)

def _get_requests():
    try: import requests; return requests
    except ImportError: print(f"{RED}pip install requests{RESET}"); sys.exit(1)

def _login(requests, server, email, password):
    r = requests.post(f"{server}/api/v1/auth/login", json={"email": email, "password": password}, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]

def _do_pair(requests, server, uid, jwt):
    auth = {"Authorization": f"Bearer {jwt}"}
    r = requests.post(f"{server}/api/v1/devices/pairing/hello",
                      json={"device_uid": uid, "firmware_version": "sim-mqtt-bridge-1.0",
                            "capabilities": {"protocols": ["mqtt"], "topics": ["sensors/#", "actuators/#"]}},
                      timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("claimed"):
        raise RuntimeError("Already claimed")
    code = data["pairing_code"]
    _info(f"Pairing code: {code}")
    r = requests.post(f"{server}/api/v1/devices/pairing/claim",
                      headers=auth, json={"pairing_code": code, "device_uid": uid}, timeout=15)
    r.raise_for_status()
    r = requests.post(f"{server}/api/v1/devices/pairing/confirm",
                      json={"device_uid": uid, "pairing_code": code}, timeout=15)
    r.raise_for_status()
    resp = r.json()
    token = resp["device_token"]
    _ok(f"Got token: {token[:16]}…")
    requests.patch(f"{server}/api/v1/devices/{resp['device_id']}",
                   headers=auth,
                   json={"name": "MQTT Bridge (Sim)", "device_type": "mqtt_bridge", "category": "bridge"},
                   timeout=10)
    return token

def _heartbeat(requests, server, token):
    try:
        r = requests.post(f"{server}/api/v1/edge/heartbeat",
                          headers={"X-Device-Token": token},
                          json={"firmware_version": "sim-mqtt-bridge-1.0"}, timeout=10)
        return r.status_code == 200
    except: return False

def _push_telemetry(requests, server, token, payload):
    try:
        r = requests.post(f"{server}/api/v1/telemetry",
                          headers={"X-Device-Token": token},
                          json={"event_type": "mqtt_message", "payload": payload}, timeout=10)
        return r.status_code in (200, 201)
    except: return False


# ── Simulated MQTT topics and messages ────────────────────────────────────────

SIMULATED_TOPICS = [
    "sensors/outdoor/temperature",
    "sensors/outdoor/humidity",
    "sensors/indoor/co2",
    "sensors/indoor/light",
    "actuators/hvac/status",
    "sensors/energy/power_watts",
]

def _simulate_mqtt_message(topic: str, cycle: int) -> dict:
    """Generate a realistic MQTT payload for the given topic."""
    now = datetime.now(timezone.utc)
    hour = now.hour + now.minute / 60

    if "temperature" in topic:
        val = 15 + 10 * math.sin(2 * math.pi * (hour / 24 - 0.25)) + random.gauss(0, 0.5)
        return {"topic": topic, "value": round(val, 1), "unit": "°C", "qos": 1}
    elif "humidity" in topic:
        val = 70 - 20 * math.sin(2 * math.pi * (hour / 24 - 0.25)) + random.gauss(0, 2)
        return {"topic": topic, "value": round(max(20, min(99, val)), 1), "unit": "%", "qos": 1}
    elif "co2" in topic:
        val = 400 + 200 * math.sin(2 * math.pi * (hour / 24 - 0.35)) + random.gauss(0, 20)
        return {"topic": topic, "value": round(max(350, val)), "unit": "ppm", "qos": 0}
    elif "light" in topic:
        # Daylight: high during day, low at night
        daylight = max(0, math.sin(2 * math.pi * (hour / 24 - 0.25)))
        val = daylight * 800 + random.gauss(0, 30)
        return {"topic": topic, "value": round(max(0, val)), "unit": "lux", "qos": 0}
    elif "hvac" in topic:
        return {"topic": topic, "status": random.choice(["heating", "cooling", "idle", "idle", "idle"]),
                "setpoint": 22.0, "qos": 1}
    elif "power" in topic:
        base = 500 + 300 * math.sin(2 * math.pi * (hour / 24 - 0.5))
        val = base + random.gauss(0, 50)
        return {"topic": topic, "value": round(max(50, val)), "unit": "W", "qos": 0}
    else:
        return {"topic": topic, "value": random.uniform(0, 100), "qos": 0}


def run(server, email, password, uid, interval, auto_pair, token):
    requests = _get_requests()

    print(f"\n{BOLD}{MAGENTA}╔═══════════════════════════════════════╗")
    print(f"║   HUBEX MQTT Bridge Simulator         ║")
    print(f"╚═══════════════════════════════════════╝{RESET}")
    print(f"  Server:     {server}")
    print(f"  Device UID: {uid}")
    print(f"  Interval:   {interval}s")
    print(f"  Topics:     {len(SIMULATED_TOPICS)} subscribed\n")

    jwt = None
    if auto_pair or not token:
        _info("Authenticating…")
        try: jwt = _login(requests, server, email, password); _ok("Logged in")
        except Exception as e: _err(f"Login failed: {e}"); return

    if auto_pair:
        _info(f"Pairing '{uid}'…")
        try: token = _do_pair(requests, server, uid, jwt)
        except Exception as e: _err(f"Pairing failed: {e}"); return
    elif not token:
        _err("No token"); return

    _ok(f"MQTT Bridge running — Ctrl+C to stop\n")

    cycle = 0
    msg_count = 0
    while _running:
        cycle += 1
        print(f"{DIM}── Cycle {cycle} ──────────────────────────────{RESET}")

        # Heartbeat
        if _heartbeat(requests, server, token): _ok("Heartbeat")

        # Simulate receiving 2-4 MQTT messages per cycle
        num_messages = random.randint(2, min(4, len(SIMULATED_TOPICS)))
        topics = random.sample(SIMULATED_TOPICS, num_messages)

        for topic in topics:
            msg = _simulate_mqtt_message(topic, cycle)
            _mqtt(f"RECV {topic}: {json.dumps({k:v for k,v in msg.items() if k != 'topic'})}")

            # Forward as telemetry
            payload = {
                "mqtt_topic": topic,
                **{k: v for k, v in msg.items() if k != "topic"},
            }
            if _push_telemetry(requests, server, token, payload):
                msg_count += 1

        _ok(f"Forwarded {num_messages} messages (total: {msg_count})")

        if not _running: break
        print(f"  {DIM}Next in {interval}s…{RESET}")
        for _ in range(interval * 2):
            if not _running: break
            time.sleep(0.5)

    print(f"\n{GREEN}MQTT Bridge stopped. Total messages: {msg_count}{RESET}")


if __name__ == "__main__":
    sfx = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    parser = argparse.ArgumentParser(description="HUBEX MQTT Bridge Simulator")
    parser.add_argument("--server", default="http://localhost:8002")
    parser.add_argument("--email", default="codex+20251219002029@example.com")
    parser.add_argument("--password", default="Test1234!")
    parser.add_argument("--uid", default=f"sim-mqtt-{sfx}")
    parser.add_argument("--interval", type=int, default=12, help="Seconds between message batches")
    parser.add_argument("--auto-pair", action="store_true", default=True)
    parser.add_argument("--token", default=None)
    args = parser.parse_args()
    run(server=args.server.rstrip("/"), email=args.email, password=args.password,
        uid=args.uid, interval=args.interval, auto_pair=args.auto_pair, token=args.token)
