from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.revoked_token import RevokedToken


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
