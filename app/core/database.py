import os
from collections.abc import AsyncGenerator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

env = os.environ["ENV"]
BASE_DIR = Path(__file__).resolve().parents[2]
env_file = BASE_DIR / f".env.{env}"
load_dotenv(env_file)
DATABASE_URL = os.getenv("DATABASE_URL")
SQL_ECHO = os.getenv("SQL_ECHO", "false").strip().lower() in {"1", "true", "yes", "on"}

# creates async SQLAlchemy engine
engine = create_async_engine(
    DATABASE_URL,
    # Keep SQL values (including synchronized user content) out of logs unless
    # a developer deliberately opts in for a local diagnostic session.
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
