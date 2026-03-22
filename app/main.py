# app/main.py
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.api.v1.telemetry import ws_router as telemetry_ws_router
from app.core.config import settings
from app.core.modules import sync_module_registry
from app.core.token_revoke import cleanup_expired_revocations
from app.core.webhook_dispatcher import webhook_dispatcher_loop
from app.db.session import AsyncSessionLocal

logger = logging.getLogger("uvicorn.error")


async def _token_cleanup_loop() -> None:
    """Periodic cleanup of expired revoked-token entries (every 6h)."""
    while True:
        await asyncio.sleep(6 * 3600)
        try:
            async with AsyncSessionLocal() as db:
                deleted = await cleanup_expired_revocations(db)
                if deleted:
                    logger.info("token_cleanup: purged %d expired revocations", deleted)
        except Exception:
            logger.exception("token_cleanup: error during cleanup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with AsyncSessionLocal() as db:
        await sync_module_registry(db)

    cleanup_task = asyncio.create_task(_token_cleanup_loop())
    dispatcher_task = asyncio.create_task(webhook_dispatcher_loop())

    yield

    # Shutdown
    cleanup_task.cancel()
    dispatcher_task.cancel()
    for task in (cleanup_task, dispatcher_task):
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")
app.include_router(telemetry_ws_router, prefix="/api/v1")
