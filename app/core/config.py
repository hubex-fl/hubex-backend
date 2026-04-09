import logging
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("uvicorn.error")

_INSECURE_SECRETS = frozenset({"change-me-now", "dev-secret-change-me", ""})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HUBEX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "dev"
    host: str = "127.0.0.1"
    port: int = 8000

    database_url: str = ""
    redis_url: str = ""

    jwt_secret: str = "change-me-now"
    jwt_issuer: str = "hubex"
    jwt_exp_minutes: int = 60 * 24

    caps_enforce: bool = True

    # Phase 7 — Rate-Limiting
    rate_limit_enabled: bool = True

    # Phase 7 — Response Caching
    cache_enabled: bool = True

    # Phase 7 — Structured Logging
    log_level: str = "INFO"
    log_format: str = "text"  # "text" | "json"

    # Phase 7 — JWT Refresh Tokens
    refresh_token_exp_days: int = 30

    # CORS — kommasepariert, leer = localhost defaults
    cors_origins: str = ""

    # Edition & Soft Limits (CE vs Pro — warnings only, no hard blocks)
    edition: str = "community"  # "community" | "pro" | "enterprise"
    max_users: int = 5
    max_devices: int = 50
    max_api_keys: int = 3
    max_dashboards: int = 10
    max_automations: int = 20
    max_custom_endpoints: int = 5
    upgrade_url: str = "https://hubex.io/pricing"

    # M27 — Scaling
    history_retention_days: int = 30
    audit_retention_days: int = 90
    telemetry_queue_enabled: bool = False  # opt-in Redis Streams
    automation_concurrency: int = 10  # max concurrent rule evaluations
    automation_batch_size: int = 200  # max events per engine cycle
    db_pool_size: int = 5  # SQLAlchemy pool_size
    db_max_overflow: int = 20  # SQLAlchemy max_overflow


settings = Settings()

# Hard-fail in non-dev environments if JWT secret is insecure.
# In dev, emit a loud warning so it's visible but doesn't block local work.
if settings.jwt_secret in _INSECURE_SECRETS:
    if settings.env != "dev":
        logger.critical(
            "FATAL: HUBEX_JWT_SECRET is insecure (%r). "
            "Set a strong secret (≥32 chars) before running in %s mode.",
            settings.jwt_secret,
            settings.env,
        )
        sys.exit(1)
    else:
        logger.warning(
            "HUBEX_JWT_SECRET is using the default dev value. "
            "This is acceptable for local development only."
        )
