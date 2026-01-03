import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app


def main() -> int:
    client = TestClient(app)
    uid = "smoke-auth-caps"

    hello = client.post("/api/v1/devices/hello", json={"device_uid": uid})
    if hello.status_code != 200:
        print(f"FAIL whitelist /devices/hello expected 200 got {hello.status_code}", file=sys.stderr)
        return 1

    noauth = client.get("/api/v1/devices")
    if noauth.status_code != 401:
        print(f"FAIL protected /devices expected 401 got {noauth.status_code}", file=sys.stderr)
        return 1

    print("OK: auth caps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
