#!/usr/bin/env python3
"""
mqtt_bridge.py — HUBEX MQTT Bridge

Subscribes to Shelly/Tasmota MQTT topics and forwards telemetry to HUBEX.
The bridge itself is a paired HUBEX device; each MQTT device's data is
namespaced by device-id prefix in the telemetry payload.

Supported device formats:
  Shelly: shellies/{device-id}/...   (JSON status or plain numeric payloads)
  Tasmota: tele/{device-id}/...      (JSON SENSOR / STATE payloads)
  Auto: detect format from topic prefix

Usage:
  # Subscribe to all Shelly devices (broker on localhost)
  python scripts/mqtt_bridge.py --auto-pair

  # Tasmota devices on remote broker
  python scripts/mqtt_bridge.py \\
    --mqtt-host 192.168.1.100 \\
    --topic "tele/#" \\
    --device-type tasmota \\
    --auto-pair

  # Already-paired bridge
  python scripts/mqtt_bridge.py --token your_device_token_here

Requirements: paho-mqtt (pip install paho-mqtt), requests (pip install requests)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import signal
import random
import string
import threading
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

signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)

# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def _get_requests():
    try:
        import requests  # type: ignore
        return requests
    except ImportError:
        print(f"{RED}Error: 'requests' not installed. Run: pip install requests{RESET}")
        sys.exit(1)

def _get_mqtt():
    try:
        import paho.mqtt.client as mqtt  # type: ignore
        return mqtt
    except ImportError:
        print(f"{RED}Error: 'paho-mqtt' not installed. Run: pip install paho-mqtt{RESET}")
        sys.exit(1)

# ---------------------------------------------------------------------------
# HUBEX HTTP helpers
# ---------------------------------------------------------------------------

def _login(requests, server: str, email: str, password: str) -> str:
    r = requests.post(f"{server}/api/v1/auth/login",
                      json={"email": email, "password": password}, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]

def _do_pair(requests, server: str, uid: str, jwt: str) -> str:
    """Full pairing flow: hello → user-claim → confirm → return device_token."""
    auth = {"Authorization": f"Bearer {jwt}"}

    # 1. Device hello
    r = requests.post(f"{server}/api/v1/devices/pairing/hello",
                      json={"device_uid": uid, "firmware_version": "mqtt-bridge-1.0"}, timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("claimed"):
        raise RuntimeError("Device already claimed — use --token or unclaim first")
    pairing_code = data["pairing_code"]
    _info(f"Pairing code: {pairing_code}")

    # 2. User claim
    r = requests.post(f"{server}/api/v1/devices/pairing/claim",
                      headers=auth,
                      json={"pairing_code": pairing_code, "device_uid": uid}, timeout=15)
    r.raise_for_status()
    _ok("Device claimed by user")

    # 3. Device confirm → permanent token
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
                          json={"firmware_version": "mqtt-bridge-1.0"}, timeout=10)
        return r.status_code == 200
    except Exception as e:
        _warn(f"Heartbeat failed: {e}")
        return False

def _push_telemetry(requests, server: str, token: str, payload: dict) -> bool:
    try:
        r = requests.post(f"{server}/api/v1/telemetry",
                          headers={"X-Device-Token": token},
                          json={"payload": payload}, timeout=10)
        return r.status_code in (200, 201)
    except Exception as e:
        _warn(f"Telemetry push failed: {e}")
        return False

# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------

def _extract_numeric(data: Any) -> dict[str, float]:
    """Recursively extract all numeric leaf values from JSON data."""
    result: dict[str, float] = {}

    def _walk(obj: Any, prefix: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    result[key] = float(v)
                elif isinstance(v, (dict, list)):
                    _walk(v, key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _walk(item, f"{prefix}.{i}" if prefix else str(i))

    _walk(data)
    return result

def _parse_payload(topic: str, raw: bytes, device_type: str) -> tuple[str, dict[str, float]]:
    """
    Parse an MQTT message and return (device_id, fields).

    Topic patterns:
      shellies/{device-id}/...  (Shelly)
      tele/{device-id}/...      (Tasmota)
      stat/{device-id}/...      (Tasmota stat)
      cmnd/{device-id}/...      (ignored — command topics)
    """
    parts = topic.split("/")
    if len(parts) < 2:
        return ("unknown", {})

    prefix = parts[0]
    device_id = parts[1] if len(parts) > 1 else "unknown"
    field_hint = parts[-1] if len(parts) > 2 else "value"

    # Skip command topics
    if prefix == "cmnd":
        return (device_id, {})

    text = raw.decode("utf-8", errors="replace").strip()
    fields: dict[str, float] = {}

    # Try JSON parse first
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            fields = _extract_numeric(parsed)
        elif isinstance(parsed, (int, float)) and not isinstance(parsed, bool):
            fields = {field_hint: float(parsed)}
    except (json.JSONDecodeError, ValueError):
        # Plain numeric string (common in Shelly per-relay topics)
        try:
            fields = {field_hint: float(text)}
        except ValueError:
            pass  # non-numeric string payload — skip

    return (device_id, fields)

# ---------------------------------------------------------------------------
# Bridge state
# ---------------------------------------------------------------------------

class BridgeState:
    """Thread-safe state for the MQTT bridge."""

    def __init__(self, requests, server: str, token: str, interval: int):
        self.requests = requests
        self.server = server
        self.token = token
        self.interval = interval
        self._lock = threading.Lock()
        self._last_push: dict[str, float] = {}  # device_id → timestamp
        self._pending: dict[str, dict[str, float]] = {}  # device_id → accumulated fields
        self.messages_received = 0
        self.telemetry_pushed = 0

    def on_message(self, device_id: str, fields: dict[str, float]) -> None:
        if not fields:
            return
        now = time.time()
        with self._lock:
            self.messages_received += 1
            # Accumulate/overwrite fields for this device
            if device_id not in self._pending:
                self._pending[device_id] = {}
            self._pending[device_id].update(fields)

            # Check rate limit
            last = self._last_push.get(device_id, 0)
            if now - last < self.interval:
                return  # too soon — fields accumulated, will push next window

            # Push now
            payload = {f"{device_id}.{k}": v for k, v in self._pending[device_id].items()}
            self._last_push[device_id] = now
            self._pending[device_id] = {}

        # Push outside the lock to avoid blocking the MQTT thread
        if _push_telemetry(self.requests, self.server, self.token, payload):
            with self._lock:
                self.telemetry_pushed += 1
            _ok(f"[{device_id}] Telemetry pushed ({len(payload)} field(s)): {list(payload.keys())[:4]}")
        else:
            _warn(f"[{device_id}] Telemetry push failed")

    def flush_all(self) -> None:
        """Push any remaining accumulated data immediately."""
        with self._lock:
            pending = {did: dict(f) for did, f in self._pending.items() if f}
            self._pending.clear()

        for device_id, fields in pending.items():
            payload = {f"{device_id}.{k}": v for k, v in fields.items()}
            if _push_telemetry(self.requests, self.server, self.token, payload):
                _ok(f"[{device_id}] Flushed {len(payload)} field(s) on shutdown")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(server: str, email: str, password: str, uid: str,
        mqtt_host: str, mqtt_port: int, mqtt_user: str | None, mqtt_pass: str | None,
        topic: str, device_type: str, interval: int,
        auto_pair: bool, token: str | None) -> None:

    requests = _get_requests()
    mqtt = _get_mqtt()

    print(f"\n{BOLD}{CYAN}╔═══════════════════════════════════════╗")
    print(f"║     HUBEX MQTT Bridge                 ║")
    print(f"╚═══════════════════════════════════════╝{RESET}")
    print(f"  Server:      {server}")
    print(f"  Bridge UID:  {uid}")
    print(f"  MQTT Broker: {mqtt_host}:{mqtt_port}")
    print(f"  Topic:       {topic}")
    print(f"  Device type: {device_type}")
    print(f"  Min interval:{interval}s per device\n")

    # HUBEX auth
    if auto_pair or not token:
        _info("Authenticating with HUBEX…")
        try:
            jwt = _login(requests, server, email, password)
            _ok("Logged in")
        except Exception as e:
            _err(f"Login failed: {e}")
            return

    # HUBEX pairing
    if auto_pair:
        _info(f"Pairing bridge device '{uid}'…")
        try:
            token = _do_pair(requests, server, uid, jwt)
        except Exception as e:
            _err(f"Pairing failed: {e}")
            return
    elif not token:
        _err("No device token. Use --auto-pair or --token <token>")
        return

    _ok("Bridge device ready\n")

    state = BridgeState(requests, server, token, interval)

    # ---------------------------------------------------------------------------
    # MQTT callbacks
    # ---------------------------------------------------------------------------

    def on_connect(client, userdata, flags, rc):  # type: ignore
        if rc == 0:
            _ok(f"Connected to MQTT broker {mqtt_host}:{mqtt_port}")
            client.subscribe(topic)
            _info(f"Subscribed to '{topic}'")
        else:
            _err(f"MQTT connection failed (rc={rc})")

    def on_disconnect(client, userdata, rc):  # type: ignore
        if rc != 0:
            _warn(f"MQTT disconnected unexpectedly (rc={rc}) — will reconnect")

    def on_message(client, userdata, msg):  # type: ignore
        try:
            device_id, fields = _parse_payload(msg.topic, msg.payload, device_type)
            if fields:
                print(f"  {DIM}↓ {msg.topic} → [{device_id}] {list(fields.keys())[:3]}{RESET}")
                state.on_message(device_id, fields)
        except Exception as e:
            _warn(f"Message parse error on {msg.topic}: {e}")

    # ---------------------------------------------------------------------------
    # MQTT client setup
    # ---------------------------------------------------------------------------

    client = mqtt.Client()  # type: ignore
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    if mqtt_user:
        client.username_pw_set(mqtt_user, mqtt_pass or "")

    _info(f"Connecting to MQTT broker {mqtt_host}:{mqtt_port}…")
    try:
        client.connect(mqtt_host, mqtt_port, keepalive=60)
    except Exception as e:
        _err(f"MQTT connect failed: {e}")
        return

    client.loop_start()

    # ---------------------------------------------------------------------------
    # Heartbeat loop
    # ---------------------------------------------------------------------------

    _ok(f"Bridge running — Ctrl+C to stop\n")
    last_heartbeat = 0.0

    while _running:
        now = time.time()
        if now - last_heartbeat >= 60:
            if _heartbeat(requests, server, token):
                with state._lock:
                    msgs = state.messages_received
                    pushed = state.telemetry_pushed
                print(f"  {DIM}── Heartbeat OK  |  messages: {msgs}  |  telemetry pushes: {pushed} ──{RESET}")
            else:
                _warn("Heartbeat failed — bridge may appear offline")
            last_heartbeat = now
        time.sleep(0.5)

    # ---------------------------------------------------------------------------
    # Graceful shutdown
    # ---------------------------------------------------------------------------

    _info("Flushing pending telemetry…")
    state.flush_all()
    client.loop_stop()
    client.disconnect()
    print(f"\n{GREEN}MQTT bridge stopped.{RESET}")
    with state._lock:
        print(f"  Total messages received: {state.messages_received}")
        print(f"  Total telemetry pushes:  {state.telemetry_pushed}")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))

    parser = argparse.ArgumentParser(description="HUBEX MQTT Bridge (Shelly/Tasmota)")
    parser.add_argument("--server",      default="http://localhost:8000")
    parser.add_argument("--email",       default="codex+20251219002029@example.com")
    parser.add_argument("--password",    default="Test1234!")
    parser.add_argument("--uid",         default=f"mqtt-bridge-{_suffix}",
                        help="HUBEX device UID for this bridge instance")
    parser.add_argument("--mqtt-host",   default="localhost",
                        help="MQTT broker hostname or IP")
    parser.add_argument("--mqtt-port",   type=int, default=1883,
                        help="MQTT broker port (default: 1883)")
    parser.add_argument("--mqtt-user",   default=None,
                        help="MQTT broker username (optional)")
    parser.add_argument("--mqtt-pass",   default=None,
                        help="MQTT broker password (optional)")
    parser.add_argument("--topic",       default="shellies/#",
                        help="MQTT topic to subscribe to (default: shellies/#)")
    parser.add_argument("--device-type", default="auto",
                        choices=["auto", "shelly", "tasmota"],
                        help="Device format hint for field extraction (default: auto)")
    parser.add_argument("--interval",    type=int, default=10,
                        help="Min seconds between telemetry pushes per device (default: 10)")
    parser.add_argument("--auto-pair",   action="store_true",
                        help="Auto-pair the bridge device with HUBEX")
    parser.add_argument("--token",       default=None,
                        help="HUBEX device token (skip pairing if already paired)")
    args = parser.parse_args()

    run(
        server=args.server.rstrip("/"),
        email=args.email,
        password=args.password,
        uid=args.uid,
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        mqtt_user=args.mqtt_user,
        mqtt_pass=args.mqtt_pass,
        topic=args.topic,
        device_type=args.device_type,
        interval=args.interval,
        auto_pair=args.auto_pair,
        token=args.token,
    )
