import argparse
import base64
import json
import asyncio

from app.db.session import AsyncSessionLocal
from app.core.token_revoke import revoke_token


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _extract_jti(token: str) -> str | None:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload = json.loads(_b64url_decode(parts[1]))
        return payload.get("jti")
    except Exception:
        return None


async def _run(jti: str, reason: str | None) -> int:
    async with AsyncSessionLocal() as db:
        inserted = await revoke_token(db, jti, reason)
        if inserted:
            print(f"revoked jti={jti}")
        else:
            print(f"already revoked jti={jti}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Revoke JWT by jti (denylist).")
    parser.add_argument("--token", help="JWT to revoke", default=None)
    parser.add_argument("--jti", help="JTI to revoke", default=None)
    parser.add_argument("--reason", help="Optional revoke reason", default=None)
    args = parser.parse_args()

    jti = args.jti
    if not jti and args.token:
        jti = _extract_jti(args.token)
    if not jti:
        raise SystemExit("missing jti (provide --jti or --token with jti)")

    return asyncio.run(_run(str(jti), args.reason))


if __name__ == "__main__":
    raise SystemExit(main())
