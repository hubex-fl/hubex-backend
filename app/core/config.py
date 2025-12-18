from pydantic_settings import BaseSettings, SettingsConfigDict


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


settings = Settings()
