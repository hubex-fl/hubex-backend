# app/main.py
import asyncio
import logging
import signal
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import router as v1_router
from app.api.v1.telemetry import ws_router as telemetry_ws_router
from app.core.cache import CacheMiddleware
from app.core.config import settings
from app.core.logging_config import configure_logging, is_test_env
from app.core.middleware import SecurityMiddleware
from app.core.modules import sync_module_registry
from app.core.rate_limit import RateLimitMiddleware
from app.core.redis_client import close_redis, init_redis
from app.core.token_revoke import cleanup_expired_revocations
from app.core.webhook_dispatcher import webhook_dispatcher_loop
from app.core.alert_worker import alert_worker_loop
from app.core.health_worker import health_worker_loop
from app.core.ota_worker import ota_worker_loop
from app.core.history_retention import history_retention_loop
from app.db.session import AsyncSessionLocal, engine

logger = logging.getLogger("uvicorn.error")

# Apply structured logging unless we're running tests
if not is_test_env():
    configure_logging(log_level=settings.log_level, log_format=settings.log_format)


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
    # ---- Startup ----
    await init_redis()

    async with AsyncSessionLocal() as db:
        await sync_module_registry(db)

    cleanup_task = asyncio.create_task(_token_cleanup_loop())
    dispatcher_task = asyncio.create_task(webhook_dispatcher_loop())
    alert_task = asyncio.create_task(alert_worker_loop())
    health_task = asyncio.create_task(health_worker_loop())
    ota_task = asyncio.create_task(ota_worker_loop())
    retention_task = asyncio.create_task(history_retention_loop())

    background_tasks = (cleanup_task, dispatcher_task, alert_task, health_task, ota_task, retention_task)

    # ---- SIGTERM handler for graceful shutdown ----
    loop = asyncio.get_event_loop()

    def _on_sigterm(*_: Any) -> None:
        logger.info("lifespan: received SIGTERM, initiating graceful shutdown")
        for task in background_tasks:
            task.cancel()

    try:
        loop.add_signal_handler(signal.SIGTERM, _on_sigterm)
    except (NotImplementedError, RuntimeError):
        # Windows does not support add_signal_handler
        pass

    yield

    # ---- Shutdown ----
    for task in background_tasks:
        task.cancel()
    for task in background_tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass

    await close_redis()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    lifespan=lifespan,
    title="HUBEX API",
    version="0.1.0",
    description="HUBEX device-management platform API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Middleware stack — order matters: last add_middleware = outermost (first to
# see the request, last to touch the response).
#
# Execution order for a request:
#   SecurityMiddleware → RateLimitMiddleware → CacheMiddleware → CORS → routes
# Response flows in reverse.

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

app.add_middleware(CacheMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityMiddleware)

app.include_router(v1_router, prefix="/api/v1")
app.include_router(telemetry_ws_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Health / Readiness endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def health() -> dict:
    """Liveness probe — no DB or Redis check."""
    return {"status": "ok", "version": "0.1.0"}


@app.get("/ready", tags=["health"])
async def ready() -> dict:
    """Readiness probe — checks DB and Redis connectivity."""
    checks: dict[str, str] = {}
    overall = "ok"

    # DB check
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        logger.warning("ready: DB check failed: %s", exc)
        checks["db"] = "error"
        overall = "degraded"

    # Redis check
    from app.core.redis_client import get_redis
    redis = get_redis()
    if redis is None:
        checks["redis"] = "disabled"
    else:
        try:
            await redis.ping()
            checks["redis"] = "ok"
        except Exception as exc:
            logger.warning("ready: Redis check failed: %s", exc)
            checks["redis"] = "error"
            overall = "degraded"

    status_code = 200 if overall == "ok" else 503
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "checks": checks, "version": "0.1.0"},
    )
