from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings


def _normalize_async_url(url: str) -> str:
    """Railway / Heroku-style providers hand out `postgresql://...` which makes
    SQLAlchemy default to the sync psycopg2 driver. We use async SQLAlchemy +
    asyncpg, so rewrite the scheme. Also handle the older `postgres://` form."""
    if url.startswith("postgresql+"):
        return url  # already explicit (e.g. postgresql+asyncpg://...)
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]
    return url


SQLALCHEMY_DATABASE_URL = _normalize_async_url(settings.database_url)


engine = create_async_engine(SQLALCHEMY_DATABASE_URL)


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
