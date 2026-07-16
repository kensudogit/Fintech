from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings
from app.db_url import to_asyncpg_url


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(
    to_asyncpg_url(settings.database_url),
    echo=settings.debug and settings.app_env == "development",
    pool_pre_ping=True,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create tables and ensure sample data exists."""
    from app.db import models  # noqa: F401
    from app.seed import seed_sample_data

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        await seed_sample_data(session, force=False)
