#!/usr/bin/env python3
"""
sim_all.py — Launch all HUBEX device simulators at once.

Starts ESP32, API Device, and Agent simulators in parallel threads.
All connect to the same HUBEX backend and auto-pair.

Usage:
  python scripts/sim_all.py
  python scripts/sim_all.py --server http://localhost:8002

Press Ctrl+C to stop all simulators.
"""

from __future__ import annotations
import argparse, signal, sys, threading, time

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

RESET = "\033[0m"; BOLD = "\033[1m"; CYAN = "\033[96m"; GREEN = "\033[92m"; YELLOW = "\033[93m"

_running = True
def _stop(*_):
    global _running
    _running = False
    print(f"\n{YELLOW}Stopping all simulators…{RESET}")
signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)


def run_esp32(server, email, password):
    from sim_esp32 import run
    run(server=server, email=email, password=password,
        uid="sim-esp32-live", interval=15, auto_pair=True, token=None)

def run_api_device(server, email, password):
    from api_device import run
    run(server=server, email=email, password=password,
        uid="sim-weather-api",
        source_url="https://api.open-meteo.com/v1/forecast?latitude=48.1&longitude=11.6&current=temperature_2m,wind_speed_10m,relative_humidity_2m",
        interval=30, fields=None, auto_pair=True, token=None)

def run_agent(server, email, password):
    from sim_agent import run
    run(server=server, email=email, password=password,
        uid="sim-agent-live", interval=10, auto_pair=True, token=None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Launch all HUBEX simulators")
    parser.add_argument("--server", default="http://localhost:8002")
    parser.add_argument("--email", default="codex+20251219002029@example.com")
    parser.add_argument("--password", default="Test1234!")
    args = parser.parse_args()

    print(f"\n{BOLD}{CYAN}╔═══════════════════════════════════════╗")
    print(f"║   HUBEX Simulator Fleet               ║")
    print(f"╚═══════════════════════════════════════╝{RESET}")
    print(f"  Server: {args.server}")
    print(f"  Starting 3 simulators…\n")

    # Add scripts dir to path
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    threads = [
        threading.Thread(target=run_esp32, args=(args.server, args.email, args.password), daemon=True, name="ESP32"),
        threading.Thread(target=run_api_device, args=(args.server, args.email, args.password), daemon=True, name="API-Device"),
        threading.Thread(target=run_agent, args=(args.server, args.email, args.password), daemon=True, name="Agent"),
    ]

    for t in threads:
        print(f"  {GREEN}▶ Starting {t.name}…{RESET}")
        t.start()
        time.sleep(2)  # stagger starts to avoid pairing conflicts

    print(f"\n{GREEN}All simulators running — Ctrl+C to stop{RESET}\n")

    while _running:
        alive = [t for t in threads if t.is_alive()]
        if not alive:
            break
        time.sleep(1)

    print(f"\n{GREEN}All simulators stopped.{RESET}")
