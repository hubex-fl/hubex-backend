#!/usr/bin/env python3
"""
sim_agent.py — HUBEX Software Agent Simulator

Simulates a software agent monitoring the local system:
  - Auto-pairs as an Agent-type device
  - Reports CPU, RAM, disk usage as telemetry
  - Updates variables with system metrics

Usage:
  python scripts/sim_agent.py --server http://localhost:8002

Requirements: requests, psutil (pip install requests psutil)
"""

from __future__ import annotations
import argparse, random, signal, string, sys, time
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
    try: import requests; return requests
    except ImportError: print(f"{RED}pip install requests{RESET}"); sys.exit(1)

def _login(requests, server, email, password):
    r = requests.post(f"{server}/api/v1/auth/login", json={"email": email, "password": password}, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]

def _do_pair(requests, server, uid, jwt):
    auth = {"Authorization": f"Bearer {jwt}"}
    r = requests.post(f"{server}/api/v1/devices/pairing/hello",
                      json={"device_uid": uid, "firmware_version": "sim-agent-1.0",
                            "capabilities": {"monitoring": ["cpu", "memory", "disk"]}}, timeout=15)
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
                   json={"name": "System Agent (Sim)", "device_type": "agent", "category": "agent"},
                   timeout=10)
    return token

def _heartbeat(requests, server, token):
    try:
        r = requests.post(f"{server}/api/v1/edge/heartbeat",
                          headers={"X-Device-Token": token},
                          json={"firmware_version": "sim-agent-1.0"}, timeout=10)
        return r.status_code == 200
    except: return False

def _push_telemetry(requests, server, token, payload):
    try:
        r = requests.post(f"{server}/api/v1/telemetry",
                          headers={"X-Device-Token": token},
                          json={"event_type": "system_metrics", "payload": payload}, timeout=10)
        return r.status_code in (200, 201)
    except: return False

def _get_system_metrics():
    """Get real or simulated system metrics."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu_percent": round(cpu, 1),
            "memory_percent": round(mem.percent, 1),
            "memory_used_mb": round(mem.used / (1024 * 1024), 0),
            "memory_total_mb": round(mem.total / (1024 * 1024), 0),
            "disk_percent": round(disk.percent, 1),
            "disk_used_gb": round(disk.used / (1024**3), 1),
            "disk_total_gb": round(disk.total / (1024**3), 1),
        }
    except ImportError:
        # Simulate if psutil not available
        return {
            "cpu_percent": round(random.uniform(5, 80), 1),
            "memory_percent": round(random.uniform(30, 75), 1),
            "memory_used_mb": round(random.uniform(2000, 6000), 0),
            "memory_total_mb": 8192,
            "disk_percent": round(random.uniform(40, 70), 1),
            "disk_used_gb": round(random.uniform(50, 150), 1),
            "disk_total_gb": 256,
        }


def run(server, email, password, uid, interval, auto_pair, token):
    requests = _get_requests()

    print(f"\n{BOLD}{CYAN}╔═══════════════════════════════════════╗")
    print(f"║   HUBEX System Agent Simulator        ║")
    print(f"╚═══════════════════════════════════════╝{RESET}")
    print(f"  Server:     {server}")
    print(f"  Device UID: {uid}")
    print(f"  Interval:   {interval}s\n")

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

    if jwt:
        try:
            from sim_helpers import ensure_variable_definitions, AGENT_VARIABLES
            n = ensure_variable_definitions(requests, server, jwt, AGENT_VARIABLES)
            if n: _ok(f"Created {n} variable definitions")
        except Exception:
            pass

    _ok(f"Agent Simulator running — Ctrl+C to stop\n")

    cycle = 0
    while _running:
        cycle += 1
        metrics = _get_system_metrics()

        print(f"{DIM}── Cycle {cycle} ──────────────────────────────{RESET}")
        _info(f"CPU={metrics['cpu_percent']}%  RAM={metrics['memory_percent']}%  Disk={metrics['disk_percent']}%")

        if _heartbeat(requests, server, token): _ok("Heartbeat")
        if _push_telemetry(requests, server, token, metrics): _ok(f"Telemetry ({len(metrics)} fields)")

        if not _running: break
        print(f"  {DIM}Next in {interval}s…{RESET}")
        for _ in range(interval * 2):
            if not _running: break
            time.sleep(0.5)

    print(f"\n{GREEN}Agent Simulator stopped.{RESET}")


if __name__ == "__main__":
    sfx = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    parser = argparse.ArgumentParser(description="HUBEX System Agent Simulator")
    parser.add_argument("--server", default="http://localhost:8002")
    parser.add_argument("--email", default="codex+20251219002029@example.com")
    parser.add_argument("--password", default="Test1234!")
    parser.add_argument("--uid", default=f"sim-agent-{sfx}")
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--auto-pair", action="store_true", default=True)
    parser.add_argument("--token", default=None)
    args = parser.parse_args()
    run(server=args.server.rstrip("/"), email=args.email, password=args.password,
        uid=args.uid, interval=args.interval, auto_pair=args.auto_pair, token=args.token)
