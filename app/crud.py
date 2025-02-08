from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from schemas import UserRegister
from password_utils import hash_password

async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def create_user(db: AsyncSession, user: UserRegister):
    hashed_password = hash_password(user.password)
    new_user = User(email=user.email, username=user.username, password_hash=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
