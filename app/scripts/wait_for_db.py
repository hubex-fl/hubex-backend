import argparse
import asyncio
import os
import time

import asyncpg


def _normalize_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url[len("postgresql+asyncpg://") :]
    return url


async def wait_for_db(
    url: str,
    *,
    timeout_seconds: float = 60.0,
    interval_seconds: float = 1.0,
) -> bool:
    if not url:
        print("ERROR: HUBEX_DATABASE_URL is not set.")
        return False
    url = _normalize_url(url)
    deadline = time.monotonic() + timeout_seconds
    attempt = 0
    while True:
        attempt += 1
        try:
            conn = await asyncpg.connect(url, timeout=5)
            await conn.close()
            print("OK: database is ready.")
            return True
        except Exception as exc:
            if time.monotonic() >= deadline:
                print(f"ERROR: database not ready after {timeout_seconds}s: {exc}")
                return False
            print(f"waiting for database... (attempt {attempt})")
            await asyncio.sleep(interval_seconds)


async def _run(args: argparse.Namespace) -> int:
    url = args.url or os.getenv("HUBEX_DATABASE_URL", "")
    ok = await wait_for_db(
        url,
        timeout_seconds=args.timeout,
        interval_seconds=args.interval,
    )
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait for database readiness.")
    parser.add_argument("--url", help="Database URL (defaults to HUBEX_DATABASE_URL)", default=None)
    parser.add_argument("--timeout", type=float, default=60.0, help="Timeout in seconds")
    parser.add_argument("--interval", type=float, default=1.0, help="Retry interval in seconds")
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
