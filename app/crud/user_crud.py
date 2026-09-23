from core.models import SyncChangeLog, User
from schemas.auth_schema import UserRegister
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from utils.password_utils import hash_password


async def get_user_by_id(db: AsyncSession, user_id: int):
    stmt = select(User).where(User.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str):
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalars().first()

async def get_user_by_username(db: AsyncSession, username: str):
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalars().first()

async def create_user(db: AsyncSession, user: UserRegister):
    hashed_password = hash_password(user.password)
    new_user = User(
        sync_id=user.sync_id,
        email=user.email,
        username=user.username,
        password_hash=hashed_password,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(
        new_user,
        attribute_names=["created_at", "updated_at"],
    )
    db.add(
        SyncChangeLog(
            user_id=new_user.user_id,
            entity_type="user",
            entity_sync_id=new_user.sync_id,
            operation="CREATE",
            entity_version=new_user.version,
            data={
                "email": new_user.email,
                "username": new_user.username,
                "created_at": new_user.created_at.isoformat(),
                "updated_at": new_user.updated_at.isoformat(),
            },
            origin_device_id=user.device_id,
            origin_mutation_id=None,
        )
    )
    await db.commit()
    await db.refresh(new_user)
    return new_user
