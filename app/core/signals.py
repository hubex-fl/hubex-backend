from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.signals import SignalV1


@dataclass(slots=True)
class SignalPersistResult:
    created: bool
    cursor: int
    signal: SignalV1


async def persist_signal(
    db: AsyncSession,
    *,
    stream: str,
    signal_type: str,
    payload: dict,
    idempotency_key: str,
    provider_instance_id: int | None = None,
) -> SignalPersistResult:
    existing = await db.scalar(select(SignalV1).where(SignalV1.idempotency_key == idempotency_key))
    if existing is not None:
        return SignalPersistResult(created=False, cursor=existing.id, signal=existing)

    signal = SignalV1(
        stream=stream,
        signal_type=signal_type,
        payload=payload,
        idempotency_key=idempotency_key,
        provider_instance_id=provider_instance_id,
    )
    db.add(signal)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        deduped = await db.scalar(select(SignalV1).where(SignalV1.idempotency_key == idempotency_key))
        if deduped is None:
            raise
        return SignalPersistResult(created=False, cursor=deduped.id, signal=deduped)

    await db.refresh(signal)
    return SignalPersistResult(created=True, cursor=signal.id, signal=signal)
