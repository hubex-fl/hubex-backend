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

    user_token = args.user_token
    if (args.vars_get or args.vars_set or args.vars_spam) and not user_token:
        log("warning", message="no user token provided; variables calls will be skipped")
    if args.vars_effective and not user_token:
        log("warning", message="no user token provided; effective vars polling skipped")

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
    tick = 0

    while time.time() - start < args.seconds:
        now = time.time()
        if now < next_tick:
            time.sleep(max(0.1, next_tick - now))
        next_tick = next_tick + args.interval
        tick += 1

        if args.vars_effective and user_token and now >= next_vars_poll:
            next_vars_poll = now + args.vars_poll_seconds
            url = f"{args.base}/api/v1/variables/effective?deviceUid={device_uid}"
            if args.include_secrets:
                url += "&includeSecrets=true"
            status, body = http_json("GET", url, headers={"Authorization": f"Bearer {user_token}"})
            payload = parse_json_payload(body)
            if status == 200 and payload:
                vars_cache = {item["key"]: item.get("value") for item in payload.get("items", [])}
                log("vars.effective", status=status, count=len(vars_cache))
            else:
                log("vars.effective", status=status, body=body)

        payload = {
            "event_type": "sim.sample",
            "payload": {
                "temp_c": 20.0 + float(vars_cache.get("device.temp_offset", 0.0) or 0.0),
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

    log("done", device_uid=device_uid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
