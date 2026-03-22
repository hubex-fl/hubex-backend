from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.revoked_token import RevokedToken

# Tokens older than this are safe to purge because JWTs would have expired
# long before this. Default: 48h (well beyond any reasonable JWT lifetime).
_CLEANUP_AGE = timedelta(hours=48)


async def is_token_revoked(db: AsyncSession, jti: str) -> bool:
    res = await db.execute(select(RevokedToken.id).where(RevokedToken.jti == jti))
    return res.scalar_one_or_none() is not None


async def revoke_token(db: AsyncSession, jti: str, reason: str | None = None) -> bool:
    res = await db.execute(select(RevokedToken).where(RevokedToken.jti == jti))
    existing = res.scalar_one_or_none()
    if existing:
        return False
    db.add(RevokedToken(jti=jti, reason=reason))
    await db.commit()
    return True


async def cleanup_expired_revocations(db: AsyncSession) -> int:
    """Remove revoked-token entries older than _CLEANUP_AGE.

    Returns number of rows deleted.
    """
    cutoff = datetime.now(timezone.utc) - _CLEANUP_AGE
    result = await db.execute(
        delete(RevokedToken).where(RevokedToken.revoked_at < cutoff)
    )
    await db.commit()
    return int(result.rowcount or 0)
