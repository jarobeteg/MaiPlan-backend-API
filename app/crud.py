from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from schemas import UserCreate

async def get_user(db: AsyncSession, email: str, username: str):
    result = await db.execute(select(User).where(User.email == email, User.username == username))
    return result.scalars().first()

async def create_user(db: AsyncSession, user: UserCreate):
    new_user = User(email=user.email, username=user.username)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
