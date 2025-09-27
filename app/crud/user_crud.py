from sqlalchemy.sql import expression
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from schemas import UserRegister, UserResetPassword, AuthSync
from utils.password_utils import hash_password

async def get_user_by_id(db: AsyncSession, user_id: int):
    stmt = select(User).where(expression.column("user_id") == user_id)
    result = await db.execute(stmt)
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str):
    stmt = select(User).where(expression.column("email") == email)
    result = await db.execute(stmt)
    return result.scalars().first()

async def get_user_by_username(db: AsyncSession, username: str):
    stmt = select(User).where(expression.column("username") == username)
    result = await db.execute(stmt)
    return result.scalars().first()

async def reset_user_password(db: AsyncSession, user: UserResetPassword):
    hashed_password = hash_password(user.password)

    stmt = (update(User)
            .where(expression.column("email") == user.email)
            .values(password_hash=hashed_password)
            .execution_options(synchronize_session="fetch")
    )

    await db.execute(stmt)
    await db.commit()

async def create_user(db: AsyncSession, user: UserRegister):
    hashed_password = hash_password(user.password)
    new_user = User(email=user.email, username=user.username, password_hash=hashed_password, sync_state=4)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    new_user.server_id = new_user.user_id
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def get_pending_user(db: AsyncSession, email: str):
    stmt = select(User).where(
        (expression.column("email") == email) &
        ((expression.column("sync_state") == 2) | (expression.column("sync_state") == 4))
    )
    result = await db.execute(stmt)
    return result.scalars().first()

async def set_sync_state(db: AsyncSession, email: str, sync_state: int):
    stmt = (
        update(User)
        .where(expression.column("email") == email)
        .values(sync_state=sync_state)
        .execution_options(synchronize_session="fetch")
    )

    await db.execute(stmt)
    await db.commit()

# this is not used yet but this will be the main source of function to sync_user
async def sync_user(db: AsyncSession, user: AuthSync):
    pass
