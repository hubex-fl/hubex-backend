import json
import urllib.error
import urllib.request

# Intentionally send invalid-shaped payloads to trigger 422 validation.
# We only care about the server-side VALIDATION log output.
BASE = "http://127.0.0.1:8001"
URL = f"{BASE}/api/v1/devices/pairing/confirm"

tests = [
    ("empty", {}),
    ("camel", {"deviceUid": "DUMMY", "pairingCode": "DUMMY"}),
    ("snake", {"device_uid": "DUMMY", "pairing_code": "DUMMY"}),
    ("wrapped_data", {"data": {"deviceUid": "DUMMY", "pairingCode": "DUMMY"}}),
    ("wrong_keys", {"device_id": "DUMMY", "code": "DUMMY"}),
]

for name, payload in tests:
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8")
        try:
            body = json.loads(raw)
        except Exception:
            body = raw
        if isinstance(body, dict) and "validation_id" in body:
            print(f"{name}: validation_id={body['validation_id']}")
        print(f"{name}: status={status} body={body}")
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8")
        try:
            body = json.loads(raw)
        except Exception:
            body = raw
        if isinstance(body, dict) and "validation_id" in body:
            print(f"{name}: validation_id={body['validation_id']}")
        print(f"{name}: status={status} body={body}")
    except Exception as exc:
        print(f"{name}: ERROR {exc}")
