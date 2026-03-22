import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings

DATABASE_URL = os.getenv("DATABASE_URL") or settings.database_url or (
    "postgresql+asyncpg://hubex:hubex@localhost:5432/hubex"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
