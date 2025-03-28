from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# creates async SQLAlchemy engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True, # this should be False in production becuase of verbose logging
    future=True,
    poolclass=NullPool # using QueuePool for production might be better, NullPool used for simplicity during development
)

# creates async session factory
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False # prevents automatic expiration of objects after db commit, avoids unnecessary db queries
)
"""
for example:
    session.add(user)
    await session.commit()
    return user # this would trigger a db query if expire_on_commit=True
"""

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """ Provides async database session

    This function is used as a dependency in API routes or other async functions that need access to the database.
    It ensures that the session is properly closed after use.

    Yields:
        AsyncSession: A SQLAlchemy async session instance
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()