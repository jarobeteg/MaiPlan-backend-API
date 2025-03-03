from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from schemas import UserRegister, UserResetPassword
from password_utils import hash_password

async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

async def reset_user_password(db: AsyncSession, user: UserResetPassword):
    hashed_password = hash_password(user.password)
    
    stmt = (
            update(User)
            .where(User.email == user.email)
            .values(password_hash=hashed_password)
            .execution_options(synchronize_session="fetch")
    )

    await db.execute(stmt)
    await db.commit()

async def create_user(db: AsyncSession, user: UserRegister):
    hashed_password = hash_password(user.password)
    new_user = User(email=user.email, username=user.username, password_hash=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
