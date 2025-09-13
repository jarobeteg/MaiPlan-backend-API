from sqlalchemy.sql import expression
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from schemas import UserRegister, UserResetPassword

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
    stmt = (
            update(User)
            .where(expression.column("email") == user.email)
            .values(password_hash=user.password_hash)
            .execution_options(synchronize_session="fetch")
    )

    await db.execute(stmt)
    await db.commit()

async def create_user(db: AsyncSession, user: UserRegister):
    new_user = User(email=user.email, username=user.username, password_hash=user.password_hash)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
