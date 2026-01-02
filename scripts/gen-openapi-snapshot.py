import json
import sys
from pathlib import Path

from app.main import app

SNAPSHOT_PATH = Path("docs/openapi.snapshot.json")


def _generate() -> dict:
    return app.openapi()


def main() -> int:
    check = "--check" in sys.argv
    data = _generate()

    if check:
        if not SNAPSHOT_PATH.exists():
            print("openapi snapshot missing: docs/openapi.snapshot.json", file=sys.stderr)
            return 1
        existing = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        if existing != data:
            print("openapi snapshot drift detected", file=sys.stderr)
            return 1
        print("openapi snapshot ok")
        return 0

    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    print("wrote openapi snapshot to docs/openapi.snapshot.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
