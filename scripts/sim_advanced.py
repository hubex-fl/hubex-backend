#!/usr/bin/env python3
"""
sim_advanced.py — HUBEX Advanced Simulator

Extends basic simulation with:
  - Task polling + execution (poll → execute → complete)
  - Alert triggering (deliberately exceed thresholds)
  - Geofence movement (GPS track simulation)
  - Burst telemetry mode (stress test)
  - API Key auth (hbx_ prefix)
  - Webhook receiver (local HTTP server)

Usage:
  python scripts/sim_advanced.py --server http://localhost:8000 --scenario tasks
  python scripts/sim_advanced.py --server http://localhost:8000 --scenario alerts
  python scripts/sim_advanced.py --server http://localhost:8000 --scenario burst
  python scripts/sim_advanced.py --server http://localhost:8000 --scenario geofence
  python scripts/sim_advanced.py --server http://localhost:8000 --scenario webhook-receiver

Requirements: requests (pip install requests)
"""

from __future__ import annotations
import argparse, json, math, random, string, sys, time, threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

from sim_helpers import robust_pair

RESET = "\033[0m"; BOLD = "\033[1m"
GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"; CYAN = "\033[96m"; DIM = "\033[2m"


def _log(prefix: str, color: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  {DIM}{ts}{RESET} {color}{prefix}{RESET} {msg}")


# ── Scenario: Task Execution ────────────────────────────────────────────────

def run_tasks(server: str, token: str, uid: str, interval: int = 10):
    """Simulate a device that polls for tasks, executes them, and reports completion."""
    _log("TASK", GREEN, f"Task executor started for {uid}")

    while True:
        try:
            # Poll for pending tasks
            r = requests.post(f"{server}/api/v1/tasks/poll", json={"device_uid": uid},
                              headers={"X-Device-Token": token}, timeout=5)
            if r.status_code == 200:
                task = r.json()
                if task and task.get("id"):
                    task_id = task["id"]
                    _log("TASK", CYAN, f"Received task #{task_id}: {task.get('type', '?')}")

                    # Simulate execution (1-3 seconds)
                    exec_time = random.uniform(1, 3)
                    time.sleep(exec_time)

                    # Complete task
                    cr = requests.post(f"{server}/api/v1/tasks/{task_id}/complete",
                                       json={"result": {"status": "ok", "duration_ms": int(exec_time * 1000)}},
                                       headers={"X-Device-Token": token}, timeout=5)
                    if cr.status_code == 200:
                        _log("TASK", GREEN, f"Task #{task_id} completed in {exec_time:.1f}s")
                    else:
                        _log("TASK", RED, f"Task #{task_id} completion failed: {cr.status_code}")
                else:
                    _log("TASK", DIM, "No pending tasks")
            else:
                _log("TASK", YELLOW, f"Poll: {r.status_code}")
        except Exception as e:
            _log("TASK", RED, f"Error: {e}")

        time.sleep(interval)


# ── Scenario: Alert Triggering ──────────────────────────────────────────────

def run_alerts(server: str, token: str, jwt: str, uid: str, interval: int = 15):
    """Deliberately exceed thresholds to trigger alerts."""
    _log("ALERT", YELLOW, f"Alert trigger mode for {uid}")

    cycle = 0
    while True:
        cycle += 1
        # Normal values most of the time, spike every 3rd cycle
        if cycle % 3 == 0:
            temp = random.uniform(85, 110)  # Way above typical threshold
            humidity = random.uniform(95, 100)
            _log("ALERT", RED, f"SPIKE: T={temp:.1f}°C H={humidity:.1f}% — should trigger alerts!")
        else:
            temp = random.uniform(20, 25)
            humidity = random.uniform(40, 60)
            _log("ALERT", DIM, f"Normal: T={temp:.1f}°C H={humidity:.1f}%")

        # Send telemetry
        try:
            requests.post(f"{server}/api/v1/telemetry",
                          json={"event_type": "sensor_reading", "payload": {
                              "temperature": round(temp, 1),
                              "humidity": round(humidity, 1),
                              "alert_test": True,
                          }},
                          headers={"X-Device-Token": token}, timeout=5)
        except Exception as e:
            _log("ALERT", RED, f"Telemetry error: {e}")

        time.sleep(interval)


# ── Scenario: Burst Telemetry ───────────────────────────────────────────────

def run_burst(server: str, token: str, uid: str, count: int = 100, delay: float = 0.1):
    """Send rapid telemetry to stress-test the ingestion pipeline."""
    _log("BURST", CYAN, f"Sending {count} telemetry messages (delay={delay}s)")

    success = 0
    errors = 0
    start = time.time()

    for i in range(count):
        try:
            r = requests.post(f"{server}/api/v1/telemetry",
                              json={"event_type": "burst_test", "payload": {
                                  "seq": i, "value": random.uniform(0, 100),
                                  "timestamp": datetime.now(timezone.utc).isoformat(),
                              }},
                              headers={"X-Device-Token": token}, timeout=5)
            if r.status_code == 200:
                success += 1
            else:
                errors += 1
        except:
            errors += 1

        if delay > 0:
            time.sleep(delay)

    elapsed = time.time() - start
    rate = count / elapsed if elapsed > 0 else 0
    _log("BURST", GREEN, f"Done: {success}/{count} success, {errors} errors, {rate:.1f} msg/s in {elapsed:.1f}s")


# ── Scenario: Geofence Movement ────────────────────────────────────────────

def run_geofence(server: str, token: str, jwt: str, uid: str, interval: int = 5):
    """Simulate GPS movement that enters/exits a geofence zone."""
    _log("GEO", CYAN, f"Geofence movement simulation for {uid}")

    # Center of Munich
    center_lat, center_lng = 48.137, 11.576
    radius_km = 2.0

    angle = 0
    while True:
        # Move in a circle around center, occasionally crossing the boundary
        r = radius_km * (0.8 + 0.5 * math.sin(angle * 0.3))  # varies 0.3-1.3x radius
        lat = center_lat + (r / 111.0) * math.cos(angle)
        lng = center_lng + (r / (111.0 * math.cos(math.radians(center_lat)))) * math.sin(angle)

        inside = r <= radius_km
        _log("GEO", GREEN if inside else YELLOW,
             f"{'INSIDE' if inside else 'OUTSIDE'} zone — lat={lat:.5f} lng={lng:.5f} (r={r:.2f}km)")

        try:
            requests.post(f"{server}/api/v1/telemetry",
                          json={"event_type": "gps_update", "payload": {
                              "gps_lat": round(lat, 6), "gps_lng": round(lng, 6),
                              "speed_kmh": random.uniform(5, 40),
                              "inside_zone": inside,
                          }},
                          headers={"X-Device-Token": token}, timeout=5)
        except Exception as e:
            _log("GEO", RED, f"Error: {e}")

        angle += 0.2
        time.sleep(interval)


# ── Scenario: Webhook Receiver ──────────────────────────────────────────────

class WebhookHandler(BaseHTTPRequestHandler):
    received: list = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else ""
        sig = self.headers.get("X-Hubex-Signature", "none")
        ts = datetime.now().strftime("%H:%M:%S")
        try:
            data = json.loads(body)
        except:
            data = body

        WebhookHandler.received.append(data)
        _log("WEBHOOK", GREEN, f"Received #{len(WebhookHandler.received)}: {json.dumps(data)[:120]}")
        _log("WEBHOOK", DIM, f"Signature: {sig[:40]}...")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode())

    def log_message(self, format, *args):
        pass  # Suppress default logging


def run_webhook_receiver(port: int = 9876):
    """Start a local HTTP server to receive HUBEX webhook deliveries."""
    _log("WEBHOOK", CYAN, f"Starting webhook receiver on http://localhost:{port}")
    _log("WEBHOOK", DIM, "Register this URL as a webhook in HUBEX Settings → Webhooks")
    server = HTTPServer(("0.0.0.0", port), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _log("WEBHOOK", YELLOW, f"Stopped. Received {len(WebhookHandler.received)} deliveries total.")


# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sfx = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    parser = argparse.ArgumentParser(description="HUBEX Advanced Simulator")
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--email", default="codex+20251219002029@example.com")
    parser.add_argument("--password", default="Test1234!")
    parser.add_argument("--uid", default=f"sim-adv-{sfx}")
    parser.add_argument("--scenario", required=True,
                        choices=["tasks", "alerts", "burst", "geofence", "webhook-receiver"],
                        help="Which simulation scenario to run")
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--burst-count", type=int, default=100)
    parser.add_argument("--webhook-port", type=int, default=9876)
    args = parser.parse_args()

    server = args.server.rstrip("/")

    if args.scenario == "webhook-receiver":
        run_webhook_receiver(args.webhook_port)
        sys.exit(0)

    # Pair device
    _log("INIT", CYAN, f"Pairing device {args.uid}...")
    token, jwt = robust_pair(server, args.email, args.password, args.uid, category="hardware")

    if args.scenario == "tasks":
        run_tasks(server, token, args.uid, args.interval)
    elif args.scenario == "alerts":
        run_alerts(server, token, jwt, args.uid, args.interval)
    elif args.scenario == "burst":
        run_burst(server, token, args.uid, args.burst_count, delay=0.05)
    elif args.scenario == "geofence":
        run_geofence(server, token, jwt, args.uid, args.interval)
