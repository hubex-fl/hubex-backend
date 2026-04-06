"""Redis Streams-based telemetry ingestion worker.

When HUBEX_TELEMETRY_QUEUE_ENABLED=true, the POST /telemetry endpoint
enqueues messages to a Redis Stream instead of writing directly to the DB.
This worker consumes from the stream and performs the bridge + history write
in batches.

When disabled (default), the telemetry endpoint writes directly as before.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.core.redis_client import get_redis

logger = logging.getLogger("uvicorn.error")

STREAM_KEY = "hubex:telemetry:ingest"
CONSUMER_GROUP = "hubex-workers"
CONSUMER_NAME = "worker-1"
BATCH_SIZE = 50
POLL_INTERVAL = 0.5  # seconds


async def enqueue_telemetry(
    device_id: int,
    device_uid: str,
    event_type: str,
    payload: dict,
    user_id: int | None = None,
) -> bool:
    """Enqueue a telemetry message to Redis Stream.

    Returns True if enqueued, False if Redis unavailable (caller should fall back).
    """
    redis = get_redis()
    if redis is None:
        return False

    try:
        msg = {
            "device_id": str(device_id),
            "device_uid": device_uid,
            "event_type": event_type,
            "payload": json.dumps(payload),
            "user_id": str(user_id) if user_id else "",
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
        }
        await redis.xadd(STREAM_KEY, msg, maxlen=100_000)
        return True
    except Exception as exc:
        logger.warning("telemetry_worker: enqueue failed: %s", exc)
        return False


async def _ensure_consumer_group() -> bool:
    """Create the consumer group if it doesn't exist."""
    redis = get_redis()
    if redis is None:
        return False
    try:
        await redis.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
    except Exception:
        pass  # Group already exists
    return True


async def _process_batch(messages: list) -> int:
    """Process a batch of telemetry messages from the stream."""
    from app.db.session import async_session_factory
    from app.api.v1.telemetry import _bridge_telemetry_to_variables

    processed = 0
    async with async_session_factory() as db:
        for msg_id, fields in messages:
            try:
                device_id = int(fields.get(b"device_id", fields.get("device_id", 0)))
                device_uid = (fields.get(b"device_uid") or fields.get("device_uid", b"")).decode() if isinstance(fields.get(b"device_uid", fields.get("device_uid", "")), bytes) else str(fields.get("device_uid", ""))
                event_type = (fields.get(b"event_type") or fields.get("event_type", b"")).decode() if isinstance(fields.get(b"event_type", fields.get("event_type", "")), bytes) else str(fields.get("event_type", ""))
                payload_raw = fields.get(b"payload") or fields.get("payload", b"{}")
                if isinstance(payload_raw, bytes):
                    payload_raw = payload_raw.decode()
                payload = json.loads(payload_raw)

                # Bridge telemetry to variables (the expensive part)
                await _bridge_telemetry_to_variables(
                    db=db,
                    device_id=device_id,
                    device_uid=device_uid,
                    payload=payload,
                )
                processed += 1

            except Exception as exc:
                logger.warning("telemetry_worker: failed to process message %s: %s", msg_id, exc)

        await db.commit()

    # ACK all processed messages
    redis = get_redis()
    if redis and messages:
        msg_ids = [msg_id for msg_id, _ in messages]
        await redis.xack(STREAM_KEY, CONSUMER_GROUP, *msg_ids)

    return processed


async def telemetry_worker_loop() -> None:
    """Background loop that consumes from the telemetry Redis Stream.

    Only runs when HUBEX_TELEMETRY_QUEUE_ENABLED=true.
    """
    if not settings.telemetry_queue_enabled:
        logger.info("telemetry_worker: disabled (HUBEX_TELEMETRY_QUEUE_ENABLED=false)")
        return

    logger.info("telemetry_worker: starting (batch_size=%d)", BATCH_SIZE)

    if not await _ensure_consumer_group():
        logger.warning("telemetry_worker: Redis unavailable, exiting")
        return

    while True:
        try:
            redis = get_redis()
            if redis is None:
                await asyncio.sleep(5)
                continue

            # Read batch from stream
            results = await redis.xreadgroup(
                CONSUMER_GROUP,
                CONSUMER_NAME,
                {STREAM_KEY: ">"},
                count=BATCH_SIZE,
                block=int(POLL_INTERVAL * 1000),
            )

            if not results:
                continue

            for stream_name, messages in results:
                if messages:
                    count = await _process_batch(messages)
                    if count:
                        logger.debug("telemetry_worker: processed %d messages", count)

        except asyncio.CancelledError:
            logger.info("telemetry_worker: shutting down")
            break
        except Exception as exc:
            logger.error("telemetry_worker: unexpected error: %s", exc)
            await asyncio.sleep(2)
