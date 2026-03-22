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
