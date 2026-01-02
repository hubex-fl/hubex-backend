import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.events import EventV1
from app.db.models.effects import EffectV1


async def enqueue_effect_from_event(
    db: AsyncSession,
    event: EventV1,
    kind: str,
    payload: dict,
) -> EffectV1:
    effect = EffectV1(
        effect_id=uuid.uuid4().hex,
        source_event_id=event.id,
        kind=kind,
        status="queued",
        payload_json=payload,
        error_json=None,
    )
    db.add(effect)
    await db.commit()
    await db.refresh(effect)
    return effect
