import argparse
import json
import os
import random
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict


VERBOSE = False
NOISY_EVENTS = {"telemetry", "tasks.poll", "vars.spam"}


def log(event: str, **data: Any) -> None:
    if not VERBOSE and event in NOISY_EVENTS:
        return
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


def parse_value(raw: str | None) -> Any:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def parse_json_payload(raw: str) -> dict[str, Any] | None:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def should_fail(rate: float) -> bool:
    return rate > 0 and random.random() < rate


def main() -> int:
    parser = argparse.ArgumentParser(description="Hubex device simulator")
    parser.add_argument("--base", default="http://127.0.0.1:8000", help="Base URL")
    parser.add_argument("--device-uid", default="", help="Device UID to use")
    parser.add_argument("--device-token", default="", help="Device token for telemetry/tasks")
    parser.add_argument("--user-token", default="", help="User JWT for variables API")
    parser.add_argument("--interval", type=float, default=5.0, help="Telemetry interval seconds")
    parser.add_argument("--seconds", type=int, default=30, help="Run duration seconds")
    parser.add_argument("--tasks", action="store_true", help="Poll tasks when device token provided")
    parser.add_argument("--context-key", default="default", help="Context key for tasks")
    parser.add_argument("--vars-key", default="", help="Variable key to read/write")
    parser.add_argument("--vars-scope", default="device", help="Variable scope: device|global")
    parser.add_argument("--vars-get", action="store_true", help="Read variable value once")
    parser.add_argument("--vars-set", action="store_true", help="Write variable value once")
    parser.add_argument("--vars-value", default="", help="Variable value (JSON string if possible)")
    parser.add_argument("--vars-expected-version", type=int, default=None, help="Expected version")
    parser.add_argument("--vars-spam", action="store_true", help="Update variable each telemetry tick")
    parser.add_argument("--vars-effective", action="store_true", help="Poll effective variables")
    parser.add_argument("--vars-poll-seconds", type=float, default=15.0, help="Effective vars poll interval")
    parser.add_argument("--include-secrets", action="store_true", help="Include secrets when polling vars")
    parser.add_argument("--vars-ack", action="store_true", help="Send applied vars ack using device token")
    parser.add_argument("--verbose", action="store_true", help="Verbose logs")
    args = parser.parse_args()
    global VERBOSE
    VERBOSE = args.verbose

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

    user_token = args.user_token
    if (args.vars_get or args.vars_set or args.vars_spam) and not user_token:
        log("warning", message="no user token provided; variables calls will be skipped")
    if args.vars_effective and not (user_token or token):
        log("warning", message="no token provided; snapshot polling skipped")

    var_value = parse_value(args.vars_value) if args.vars_value else None
    if args.vars_get and user_token and args.vars_key:
        url = f"{args.base}/api/v1/variables/value?key={args.vars_key}&scope={args.vars_scope}"
        if args.vars_scope == "device":
            url += f"&deviceUid={device_uid}"
        status, body = http_json("GET", url, headers={"Authorization": f"Bearer {user_token}"})
        log("vars.get", status=status, body=body, key=args.vars_key)

    if args.vars_set and user_token and args.vars_key:
        payload = {
            "key": args.vars_key,
            "scope": args.vars_scope,
            "value": var_value,
        }
        if args.vars_scope == "device":
            payload["deviceUid"] = device_uid
        if args.vars_expected_version is not None:
            payload["expectedVersion"] = args.vars_expected_version
        status, body = http_json(
            "PUT",
            f"{args.base}/api/v1/variables/value",
            payload,
            headers={"Authorization": f"Bearer {user_token}"},
        )
        log("vars.set", status=status, body=body, key=args.vars_key)

    start = time.time()
    next_tick = start
    next_vars_poll = start
    vars_cache: dict[str, Any] = {}
    last_snapshot_id: str | None = None
    last_effective_rev: int | None = None
    tick = 0
    exit_code = 0
    fail_timeout_rate = env_float("HUBEX_FAIL_RATE_TIMEOUT", 0.0)
    fail_type_rate = env_float("HUBEX_FAIL_RATE_TYPE", 0.0)

    while time.time() - start < args.seconds:
        now = time.time()
        if now < next_tick:
            time.sleep(max(0.1, next_tick - now))
        interval = args.interval
        interval_ms = vars_cache.get("device.telemetry_interval_ms")
        if isinstance(interval_ms, (int, float)) and interval_ms > 0:
            interval = max(0.5, float(interval_ms) / 1000.0)
        next_tick = time.time() + interval
        tick += 1

        if args.vars_effective and (user_token or token) and now >= next_vars_poll:
            next_vars_poll = now + args.vars_poll_seconds
            url = f"{args.base}/api/v1/variables/snapshot?deviceUid={device_uid}"
            headers = {"X-Device-Token": token} if token else {"Authorization": f"Bearer {user_token}"}
            status, body = http_json("GET", url, headers=headers)
            payload = parse_json_payload(body)
            if status == 200 and payload:
                snapshot_id = payload.get("snapshot_id")
                effective_rev = payload.get("effective_rev")
                items = payload.get("vars", [])
                vars_cache = {
                    item["key"]: item.get("value")
                    for item in items
                    if item.get("value") is not None
                }
                last_snapshot_id = snapshot_id
                log("vars.snapshot", status=status, snapshot_id=snapshot_id, effective_rev=effective_rev, count=len(items))
                if args.vars_ack and token and effective_rev is not None:
                    if effective_rev != last_effective_rev:
                        results = []
                        for item in items:
                            key = item.get("key")
                            if not key:
                                continue
                            status_code = "OK"
                            detail = None
                            if should_fail(fail_timeout_rate):
                                status_code = "HW_TIMEOUT"
                                detail = "timeout"
                            elif should_fail(fail_type_rate):
                                status_code = "TYPE_MISMATCH"
                                detail = "type mismatch"
                            results.append({"key": key, "status": status_code, "detail": detail})
                        ack_body = {
                            "deviceUid": device_uid,
                            "effectiveRev": effective_rev,
                            "results": results,
                        }
                        ack_status, ack_resp = http_json(
                            "POST",
                            f"{args.base}/api/v1/variables/ack",
                            ack_body,
                            headers={"X-Device-Token": token},
                        )
                        ack_payload = parse_json_payload(ack_resp)
                        log("vars.ack", status=ack_status, body=ack_resp)
                        if ack_status != 200 or not ack_payload:
                            log("vars.ack.error", status=ack_status)
                            exit_code = 2
                            break
                        failed_count = int(ack_payload.get("failed") or 0)
                        if failed_count > 0:
                            log("vars.ack.fail", failed=failed_count)
                            exit_code = 2
                            break
                        last_effective_rev = effective_rev
                elif args.vars_ack and not token:

                    log("warning", message="vars ack requested but no device token provided")
            else:
                log("vars.snapshot", status=status, body=body)

        label = vars_cache.get("device.label")
        payload = {
            "event_type": "sim.sample",
            "payload": {
                "temp_c": 20.0 + float(vars_cache.get("device.temp_offset", 0.0) or 0.0),
                "voltage": 3.7,
                "rssi": -60,
                "uid": device_uid,
                "label": label,
                "vars_snapshot_id": last_snapshot_id,
                "vars_effective_rev": last_effective_rev,
            },
        }
        headers = {"X-Device-Token": token} if token else {}
        status, body = http_json("POST", f"{args.base}/api/v1/telemetry", payload, headers=headers)
        log("telemetry", status=status, body=body)

        if args.tasks and token:
            poll_url = f"{args.base}/api/v1/tasks/poll?limit=1&context_key={args.context_key}&lease_seconds=30"
            status, body = http_json("POST", poll_url, headers={"X-Device-Token": token})
            log("tasks.poll", status=status, body=body)

        if args.vars_spam and user_token and args.vars_key:
            spam_payload = {
                "key": args.vars_key,
                "scope": args.vars_scope,
                "value": tick,
            }
            if args.vars_scope == "device":
                spam_payload["deviceUid"] = device_uid
            status, body = http_json(
                "PUT",
                f"{args.base}/api/v1/variables/value",
                spam_payload,
                headers={"Authorization": f"Bearer {user_token}"},
            )
            log("vars.spam", status=status, body=body, key=args.vars_key)

        if exit_code:
            break

    log("done", device_uid=device_uid, status=exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

