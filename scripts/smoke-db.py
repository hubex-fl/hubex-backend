import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import engine


async def main() -> int:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("OK: db")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: db {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
