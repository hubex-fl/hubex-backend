"""User-level WebSocket endpoint — notifications + channel events."""
import asyncio
import logging

from fastapi import APIRouter, Query, WebSocket
from sqlalchemy import select

from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.session import AsyncSessionLocal
from app.realtime import user_hub

logger = logging.getLogger("uvicorn.error")

ws_router = APIRouter()

MAX_USER_WS = 100
PING_INTERVAL = 30  # seconds


@ws_router.websocket("/ws")
async def user_ws(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    User-level WebSocket at /api/v1/ws?token=JWT.

    Server pushes:
    - {"type": "connected", "user_id": int}
    - {"type": "ping"}
    - {"type": "notification", "data": {...}}
    - {"type": "event", "channel": str, "data": {...}}

    Channels: device_events, variable_stream, alert_events, automation_events
    """
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except Exception:
        await websocket.close(code=1008)
        return

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()
        if not user:
            await websocket.close(code=1008)
            return

    if user_hub.connection_count >= MAX_USER_WS:
        await websocket.close(code=1013)
        return

    await websocket.accept()
    await user_hub.add(user_id, websocket)
    logger.info("user_ws: connect user_id=%s total=%s", user_id, user_hub.connection_count)

    try:
        await websocket.send_json({"type": "connected", "user_id": user_id})
        while True:
            await asyncio.sleep(PING_INTERVAL)
            await websocket.send_json({"type": "ping"})
    except Exception:
        pass
    finally:
        user_hub.remove(user_id, websocket)
        logger.info("user_ws: disconnect user_id=%s remaining=%s", user_id, user_hub.connection_count)
