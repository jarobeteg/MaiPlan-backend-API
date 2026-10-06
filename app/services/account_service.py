from datetime import datetime, timezone
from uuid import UUID

from core.models import SyncChangeLog, User
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from utils.password_utils import hash_password


async def _lock_user(db: AsyncSession, user_id: int) -> User:
    user = await db.scalar(
        select(User)
        .where(User.user_id == user_id, User.deleted_at.is_(None))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Account is unavailable"},
        )
    return user


async def _save_profile_change(db: AsyncSession, user: User, device_id: UUID) -> User:
    user.version += 1
    user.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(user, attribute_names=["updated_at"])
    db.add(
        SyncChangeLog(
            user_id=user.user_id,
            entity_type="user",
            entity_sync_id=user.sync_id,
            operation="UPDATE",
            entity_version=user.version,
            data={
                "email": user.email,
                "username": user.username,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
            },
            origin_device_id=device_id,
            origin_mutation_id=None,
        )
    )
    await db.commit()
    return user


async def change_username(
    db: AsyncSession, user_id: int, device_id: UUID, username: str,
) -> User:
    username = username.strip()
    if not username:
        raise HTTPException(
            status_code=400,
            detail={"code": 9, "message": "Username field cannot be empty!"},
        )
    user = await _lock_user(db, user_id)
    if user.username == username:
        return user
    existing_user = await db.scalar(
        select(User.user_id).where(User.username == username, User.user_id != user_id)
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=400,
            detail={"code": 10, "message": "Username is already taken!"},
        )
    user.username = username
    return await _save_profile_change(db, user, device_id)


async def change_password(
    db: AsyncSession, user_id: int, device_id: UUID, password: str,
) -> User:
    user = await _lock_user(db, user_id)
    user.password_hash = hash_password(password)
    return await _save_profile_change(db, user, device_id)
