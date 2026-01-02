import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

SNAPSHOT_PATH = Path("docs/openapi.snapshot.json")


def _generate() -> dict:
    return app.openapi()


def _normalize(obj):
    if isinstance(obj, dict):
        return {k: _normalize(obj[k]) for k in sorted(obj)}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    return obj


def main() -> int:
    check = "--check" in sys.argv
    data = _normalize(_generate())

    if check:
        if not SNAPSHOT_PATH.exists():
            print("openapi snapshot missing: docs/openapi.snapshot.json", file=sys.stderr)
            return 1
        existing = _normalize(json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8")))
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
