"""Webhook dispatcher — background worker that delivers events to registered webhooks."""
import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.db.models.events import EventV1
from app.db.models.webhooks import WebhookDelivery, WebhookSubscription
from app.db.session import AsyncSessionLocal

logger = logging.getLogger("uvicorn.error")

# 3 retries with delays before each retry attempt
RETRY_DELAYS = [1, 5, 25]
POLL_INTERVAL = 5  # seconds between dispatch cycles


def _compute_signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _build_payload(event: EventV1) -> tuple[bytes, str]:
    """Build the n8n-ready JSON payload and HMAC signature."""
    ts = event.ts
    if ts is not None and ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    payload = {
        "event": event.type,
        "timestamp": (ts or datetime.now(timezone.utc)).isoformat(),
        "stream": event.stream,
        "event_id": event.id,
        "data": event.payload,
    }
    return payload


async def _dispatch_with_retry(
    webhook: WebhookSubscription,
    event: EventV1,
    client: httpx.AsyncClient,
) -> None:
    payload_dict = _build_payload(event)
    # Compute signature over the core payload (without hubex_signature field)
    body_for_sig = json.dumps(payload_dict, default=str, sort_keys=True).encode()
    signature = _compute_signature(webhook.secret, body_for_sig)
    payload_dict["hubex_signature"] = signature
    body = json.dumps(payload_dict, default=str).encode()

    headers = {
        "Content-Type": "application/json",
        "X-Hubex-Signature": signature,
    }

    for attempt in range(len(RETRY_DELAYS) + 1):
        if attempt > 0:
            await asyncio.sleep(RETRY_DELAYS[attempt - 1])

        start = time.monotonic()
        status_code: int | None = None
        success = False
        try:
            resp = await client.post(webhook.url, content=body, headers=headers, timeout=10.0)
            status_code = resp.status_code
            success = 200 <= status_code < 300
        except Exception as exc:
            logger.warning(
                "webhook dispatch error webhook=%d event=%d attempt=%d: %s",
                webhook.id,
                event.id,
                attempt + 1,
                exc,
            )

        elapsed_ms = (time.monotonic() - start) * 1000

        async with AsyncSessionLocal() as db:
            db.add(
                WebhookDelivery(
                    webhook_id=webhook.id,
                    event_id=event.id,
                    status_code=status_code,
                    response_time_ms=elapsed_ms,
                    attempt=attempt + 1,
                    success=success,
                )
            )
            await db.commit()

        if success:
            return

    logger.warning(
        "webhook delivery failed after %d attempts webhook=%d event=%d",
        len(RETRY_DELAYS) + 1,
        webhook.id,
        event.id,
    )


async def _run_dispatch_cycle(cursor: int) -> int:
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(EventV1)
            .where(EventV1.id > cursor)
            .order_by(EventV1.id.asc())
            .limit(100)
        )
        events = list(res.scalars().all())
        if not events:
            return cursor

        res = await db.execute(
            select(WebhookSubscription).where(WebhookSubscription.active.is_(True))
        )
        webhooks = list(res.scalars().all())

    if not webhooks:
        return events[-1].id

    async with httpx.AsyncClient() as client:
        for event in events:
            cursor = event.id
            for webhook in webhooks:
                filter_list = webhook.event_filter or []
                if not filter_list or event.type in filter_list:
                    await _dispatch_with_retry(webhook, event, client)

    return cursor


async def webhook_dispatcher_loop() -> None:
    """Background loop: polls events_v1 and dispatches to registered webhooks."""
    cursor = 0
    while True:
        try:
            cursor = await _run_dispatch_cycle(cursor)
        except Exception:
            logger.exception("webhook_dispatcher: unhandled error in dispatch cycle")
        await asyncio.sleep(POLL_INTERVAL)
