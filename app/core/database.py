from collections.abc import AsyncGenerator

from core.settings import DATABASE_URL, SQL_ECHO
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# creates async SQLAlchemy engine
engine = create_async_engine(
    DATABASE_URL,
    echo=SQL_ECHO,
    future=True,
    poolclass=NullPool # using QueuePool for production might be better, NullPool used for simplicity during development
)

# creates async session factory
async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False # prevents automatic expiration of objects after db commit, avoids unnecessary db queries
)
"""
for example:
    session.add(user)
    await session.commit()
    return user # this would trigger a db query if expire_on_commit=True
"""

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
