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
from app.api.v1.ws_user import ws_router as user_ws_router
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
from app.core.automation_engine import automation_engine_loop
from app.core.partition_manager import partition_maintenance_loop
from app.core.telemetry_worker import telemetry_worker_loop
from app.db.session import AsyncSessionLocal, engine

logger = logging.getLogger("uvicorn.error")

# Apply structured logging unless we're running tests
if not is_test_env():
    configure_logging(log_level=settings.log_level, log_format=settings.log_format)


async def _demo_heartbeat_loop() -> None:
    """Keep demo devices online by refreshing last_seen_at every 60s."""
    from sqlalchemy import text
    while True:
        await asyncio.sleep(60)
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(text(
                    "UPDATE devices SET last_seen_at = NOW() WHERE device_uid LIKE 'demo-%'"
                ))
                await db.commit()
        except Exception:
            logger.debug("demo_heartbeat: error updating demo devices")


async def _computed_variables_loop() -> None:
    """Recompute computed variables every 30 seconds."""
    from app.core.computed_variables import compute_all
    while True:
        await asyncio.sleep(30)
        try:
            async with AsyncSessionLocal() as db:
                count = await compute_all(db)
                if count:
                    logger.debug("computed_variables: updated %d values", count)
        except Exception:
            logger.debug("computed_variables: error in compute cycle")


async def _api_poll_worker_loop() -> None:
    """Poll configured API endpoints for service-type devices and write values as telemetry."""
    import httpx
    from sqlalchemy import select
    from app.db.models.device import Device
    from datetime import datetime, timezone

    while True:
        await asyncio.sleep(30)  # Check every 30s
        try:
            async with AsyncSessionLocal() as db:
                # Find service devices with endpoint_url configured
                res = await db.execute(
                    select(Device).where(
                        Device.category == "service",
                        Device.config.isnot(None),
                        Device.is_claimed == True,
                    )
                )
                devices = res.scalars().all()

                for device in devices:
                    cfg = device.config or {}
                    url = cfg.get("endpoint_url")
                    if not url:
                        continue

                    interval = cfg.get("poll_interval_seconds", 60)
                    # Check if enough time passed since last_seen
                    if device.last_seen_at:
                        age = (datetime.now(timezone.utc) - device.last_seen_at.replace(tzinfo=timezone.utc)).total_seconds()
                        if age < interval * 0.8:  # 80% of interval = not yet due
                            continue

                    try:
                        method = cfg.get("method", "GET").upper()
                        headers = cfg.get("headers") or {}
                        auth_type = cfg.get("auth_type", "none")
                        if auth_type == "bearer" and cfg.get("auth_credentials"):
                            headers["Authorization"] = f"Bearer {cfg['auth_credentials']}"
                        elif auth_type == "api_key" and cfg.get("auth_credentials"):
                            headers["X-API-Key"] = cfg["auth_credentials"]

                        async with httpx.AsyncClient(timeout=15) as client:
                            resp = await client.request(method, url, headers=headers)
                            if resp.status_code == 200:
                                data = resp.json()
                                # Extract numeric fields
                                payload = {}
                                def _extract(obj, prefix=""):
                                    if isinstance(obj, dict):
                                        for k, v in obj.items():
                                            full = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
                                            if isinstance(v, (int, float)) and not isinstance(v, bool):
                                                payload[k] = float(v)
                                            elif isinstance(v, dict):
                                                _extract(v, full)
                                _extract(data)

                                if payload:
                                    # Write as telemetry via internal bridge
                                    from app.api.v1.telemetry import _bridge_telemetry_to_variables
                                    device.last_seen_at = datetime.now(timezone.utc)
                                    await _bridge_telemetry_to_variables(device.id, device.device_uid, "api_poll", payload)
                                    logger.debug("api_poll: %s → %d fields", device.device_uid, len(payload))
                    except Exception as e:
                        logger.debug("api_poll: %s failed: %s", device.device_uid, e)

                await db.commit()
        except Exception:
            logger.debug("api_poll_worker: error in poll cycle")


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
    # Auto-create all tables on fresh database
    from app.db.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Safety net: add columns that create_all cannot add to existing tables.
        # This covers cases where Alembic migrations have not been applied yet.
        # Uses IF NOT EXISTS to avoid errors on PostgreSQL.
        _COLUMN_PATCHES = [
            ("dashboards", "embed_config", "JSON"),
            ("dashboards", "kiosk_config", "JSON"),
        ]
        for table, col, col_type in _COLUMN_PATCHES:
            try:
                await conn.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type}"
                ))
            except Exception:
                pass

    logger.info("startup: database tables ensured")

    await init_redis()

    async with AsyncSessionLocal() as db:
        await sync_module_registry(db)

    # Seed built-in semantic types if table is empty
    try:
        async with AsyncSessionLocal() as db:
            count_result = await db.execute(text("SELECT COUNT(*) FROM semantic_types"))
            count = count_result.scalar() or 0
            if count == 0:
                logger.info("startup: seeding built-in semantic types")
                from app.scripts.seed_semantic_types import main as seed_types
                await seed_types()
                logger.info("startup: semantic types seeded")
            else:
                logger.info("startup: semantic types already present (%d)", count)
    except Exception:
        logger.warning("startup: failed to seed semantic types (table may not exist yet)")

    cleanup_task = asyncio.create_task(_token_cleanup_loop())
    dispatcher_task = asyncio.create_task(webhook_dispatcher_loop())
    alert_task = asyncio.create_task(alert_worker_loop())
    health_task = asyncio.create_task(health_worker_loop())
    ota_task = asyncio.create_task(ota_worker_loop())
    retention_task = asyncio.create_task(history_retention_loop())
    automation_task = asyncio.create_task(automation_engine_loop())
    demo_heartbeat_task = asyncio.create_task(_demo_heartbeat_loop())
    api_poll_task = asyncio.create_task(_api_poll_worker_loop())
    computed_task = asyncio.create_task(_computed_variables_loop())
    partition_task = asyncio.create_task(partition_maintenance_loop())
    telemetry_task = asyncio.create_task(telemetry_worker_loop())

    background_tasks = (cleanup_task, dispatcher_task, alert_task, health_task, ota_task, retention_task, automation_task, demo_heartbeat_task, api_poll_task, computed_task)

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

# CORS — konfigurierbar via HUBEX_CORS_ORIGINS env var (kommasepariert)
_cors_env = settings.cors_origins if hasattr(settings, 'cors_origins') and settings.cors_origins else ""
_cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Device-Token", "X-Request-ID", "X-Access-Token-Expire-Seconds"],
)

app.add_middleware(CacheMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityMiddleware)

app.include_router(v1_router, prefix="/api/v1")
app.include_router(telemetry_ws_router, prefix="/api/v1")
app.include_router(user_ws_router, prefix="/api/v1")


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
