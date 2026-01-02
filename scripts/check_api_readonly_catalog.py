import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

CATALOG_PATH = Path("docs/API_READONLY.md")

# Routes intentionally excluded from catalog
EXCLUDE = {
    "GET /api/v1/openapi.json",
    "GET /api/v1/docs",
    "GET /api/v1/redoc",
    "GET /api/v1/health",
    "GET /api/v1/version",
}


def _catalog_entries(text: str) -> set[str]:
    entries = set()
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        line = line[2:]
        if " /api/v1/" not in line:
            continue
        first = line.split(" - ", 1)[0]
        entries.add(first)
    return entries


def _route_entries() -> set[str]:
    entries = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path.startswith("/api/v1"):
            continue
        methods = getattr(route, "methods", set())
        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            entries.add(f"{method} {path}")
    return entries


def main() -> int:
    if not CATALOG_PATH.exists():
        print("api readonly catalog missing: docs/API_READONLY.md", file=sys.stderr)
        return 1
    catalog = _catalog_entries(CATALOG_PATH.read_text(encoding="utf-8"))
    routes = _route_entries()

    missing = sorted(r for r in routes if r not in catalog and r not in EXCLUDE)
    if missing:
        print("api readonly catalog missing entries:", file=sys.stderr)
        for item in missing:
            print(item, file=sys.stderr)
        return 1

    print(f"api readonly catalog ok: {len(routes)} routes checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
