import sys
from fastapi.routing import APIRoute

from app.main import app
from app.core.capabilities import CAPABILITY_MAP, PUBLIC_WHITELIST


IGNORED_PREFIXES = (
    "/docs",
    "/redoc",
    "/openapi.json",
)


def main() -> int:
    missing = []
    total = 0
    mapped = 0

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        path = route.path
        if path.startswith(IGNORED_PREFIXES):
            continue
        if not path.startswith("/api/v1"):
            continue
        methods = {m for m in route.methods or [] if m not in {"HEAD", "OPTIONS"}}
        for method in methods:
            total += 1
            key = (method, path)
            if key in PUBLIC_WHITELIST:
                mapped += 1
                continue
            if key in CAPABILITY_MAP:
                mapped += 1
                continue
            missing.append(f"{method} {path}")

    if missing:
        print("CAPABILITY COVERAGE FAIL: missing mappings:")
        for item in missing:
            print(f"- {item}")
        print(f"mapped={mapped} total={total}")
        return 1

    print(f"capability coverage ok: mapped={mapped} total={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
