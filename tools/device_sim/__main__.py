import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict


def log(event: str, **data: Any) -> None:
    stamp = datetime.now(timezone.utc).isoformat()
    payload = {"ts": stamp, "event": event, **data}
    print(json.dumps(payload, ensure_ascii=True))


def http_json(method: str, url: str, body: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = resp.read().decode("utf-8")
            return resp.status, payload
    except urllib.error.HTTPError as e:
        payload = e.read().decode("utf-8")
        return e.code, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Hubex device simulator")
    parser.add_argument("--base", default="http://127.0.0.1:8000", help="Base URL")
    parser.add_argument("--device-uid", default="", help="Device UID to use")
    parser.add_argument("--device-token", default="", help="Device token for telemetry/tasks")
    parser.add_argument("--interval", type=float, default=5.0, help="Telemetry interval seconds")
    parser.add_argument("--seconds", type=int, default=30, help="Run duration seconds")
    parser.add_argument("--tasks", action="store_true", help="Poll tasks when device token provided")
    parser.add_argument("--context-key", default="default", help="Context key for tasks")
    args = parser.parse_args()

    device_uid = args.device_uid
    if not device_uid:
        device_uid = f"sim-{int(time.time())}"

    hello_body = {
        "device_uid": device_uid,
        "firmware_version": "sim-1.0",
        "capabilities": {"sim": True, "telemetry": True},
    }
    status, body = http_json("POST", f"{args.base}/api/v1/devices/hello", hello_body)
    log("hello", status=status, body=body, device_uid=device_uid)

    token = args.device_token
    if not token:
        log("warning", message="no device token provided; telemetry may be rejected")

    start = time.time()
    next_tick = start

    while time.time() - start < args.seconds:
        now = time.time()
        if now < next_tick:
            time.sleep(max(0.1, next_tick - now))
        next_tick = next_tick + args.interval

        payload = {
            "event_type": "sim.sample",
            "payload": {
                "temp_c": 20.0,
                "voltage": 3.7,
                "rssi": -60,
                "uid": device_uid,
            },
        }
        headers = {"X-Device-Token": token} if token else {}
        status, body = http_json("POST", f"{args.base}/api/v1/telemetry", payload, headers=headers)
        log("telemetry", status=status, body=body)

        if args.tasks and token:
            poll_url = f"{args.base}/api/v1/tasks/poll?limit=1&context_key={args.context_key}&lease_seconds=30"
            status, body = http_json("POST", poll_url, headers={"X-Device-Token": token})
            log("tasks.poll", status=status, body=body)

    log("done", device_uid=device_uid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
