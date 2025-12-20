import json
import os
import sys
import uuid
from urllib import request
from urllib.error import HTTPError, URLError


BASE = os.getenv("HUBEX_BASE", "http://127.0.0.1:8000")
EMAIL = "dev@hubex.local"
PASSWORD = "devdevdev"


def _request_json(method, url, payload=None, headers=None):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body
    except HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, body
    except URLError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)


def _parse_body(body):
    try:
        return json.loads(body)
    except Exception:
        return None


def main():
    login_payload = {"email": EMAIL, "password": PASSWORD}
    status, body = _request_json("POST", f"{BASE}/api/v1/auth/login", login_payload)
    if status != 200:
        _request_json("POST", f"{BASE}/api/v1/auth/register", login_payload)
        status, body = _request_json(
            "POST", f"{BASE}/api/v1/auth/login", login_payload
        )
        if status != 200:
            print(f"LOGIN FAILED status={status} body={body}")
            sys.exit(1)

    login_obj = _parse_body(body) or {}
    token = login_obj.get("access_token") or login_obj.get("token")
    if not token:
        print(f"LOGIN RESPONSE MISSING TOKEN body={body}")
        sys.exit(1)

    device_uid = f"SMOKE-REPLAY-{uuid.uuid4().hex[:8]}"
    hello_payload = {"device_uid": device_uid}
    status, body = _request_json(
        "POST", f"{BASE}/api/v1/devices/hello", hello_payload
    )
    print(f"HELLO status={status} body={body}")
    if status != 200:
        sys.exit(1)

    start_payload = {"device_uid": device_uid}
    status, body = _request_json(
        "POST",
        f"{BASE}/api/v1/devices/pairing/start",
        start_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    print(f"PAIRING_START status={status} body={body}")
    start_obj = _parse_body(body) or {}
    code = start_obj.get("pairing_code")
    if status == 409:
        detail = start_obj.get("detail") if isinstance(start_obj, dict) else None
        code_detail = None
        if isinstance(detail, dict):
            code_detail = detail.get("code")
        if code_detail == "PAIRING_ALREADY_ACTIVE":
            if not code:
                print(
                    "PAIRING_START active pairing but no pairing_code in response (cannot proceed)."
                )
                sys.exit(1)
        else:
            print("PAIRING_START failed (unexpected 409).")
            sys.exit(1)
    elif status == 200:
        if not code:
            print("PAIRING_START missing pairing_code.")
            sys.exit(1)
    else:
        print("PAIRING_START failed (expected 200 or 409).")
        sys.exit(1)

    confirm_payload = {"deviceUid": device_uid, "pairingCode": code}
    status1, body1 = _request_json(
        "POST", f"{BASE}/api/v1/devices/pairing/confirm", confirm_payload
    )
    print(f"CONFIRM#1 status={status1} body={body1}")
    if status1 != 200:
        sys.exit(1)

    confirm_obj = _parse_body(body1) or {}
    if not confirm_obj.get("device_token"):
        print("CONFIRM#1 missing device_token.")
        sys.exit(1)

    status2, body2 = _request_json(
        "POST", f"{BASE}/api/v1/devices/pairing/confirm", confirm_payload
    )
    print(f"CONFIRM#2 status={status2} body={body2}")
    if status2 != 409:
        sys.exit(1)

    if "device_token" in (body2 or ""):
        print("CONFIRM#2 leaked device_token.")
        sys.exit(1)

    print("OK: confirm replay blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

