import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from core.models import AuthSession, SyncChangeLog, User
from core.settings import REFRESH_TOKEN_INACTIVITY_DAYS
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from utils.password_utils import hash_password


@dataclass(frozen=True)
class IssuedSession:
    session: AuthSession
    refresh_token: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _refresh_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def _auth_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": "AUTH_REQUIRED", "message": message},
    )


def _is_expired(value: datetime, now: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value <= now


async def _issue_session(
    db: AsyncSession,
    user: User,
    device_id: UUID,
    now: datetime,
) -> IssuedSession:
    refresh_token = _new_refresh_token()
    session = AuthSession(
        user_id=user.user_id,
        device_id=device_id,
        refresh_token_hash=_refresh_token_hash(refresh_token),
        refresh_expires_at=now + timedelta(days=REFRESH_TOKEN_INACTIVITY_DAYS),
        updated_at=now,
    )
    db.add(session)
    await db.flush()
    return IssuedSession(session=session, refresh_token=refresh_token)


async def create_session(
    db: AsyncSession,
    user: User,
    device_id: UUID,
) -> IssuedSession:
    if db.in_transaction():
        await db.commit()
    now = _utc_now()
    async with db.begin():
        existing_sessions = list(
            (
                await db.scalars(
                    select(AuthSession)
                    .where(
                        AuthSession.user_id == user.user_id,
                        AuthSession.device_id == device_id,
                        AuthSession.revoked_at.is_(None),
                    )
                    .with_for_update()
                )
            ).all()
        )
        for existing in existing_sessions:
            existing.revoked_at = now

        issued_session = await _issue_session(db, user, device_id, now)
    return issued_session


async def reset_password_session(
    db: AsyncSession,
    email: str,
    password: str,
    device_id: UUID,
) -> tuple[User, IssuedSession]:
    # Password replacement, session revocation, and issuance must commit together.
    async with db.begin():
        user = await db.scalar(
            select(User)
            .where(User.email == email, User.deleted_at.is_(None))
            .with_for_update()
        )
        if user is None:
            raise HTTPException(
                status_code=401,
                detail={"code": 3, "message": "Email is not yet registered!"},
            )

        now = _utc_now()
        user.password_hash = hash_password(password)
        user.version += 1
        user.updated_at = now
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
        await db.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user.user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now, updated_at=now)
        )
        issued_session = await _issue_session(db, user, device_id, now)
    return user, issued_session


async def rotate_session(
    db: AsyncSession,
    refresh_token: str,
    device_id: UUID,
) -> tuple[User, IssuedSession]:
    if not refresh_token:
        raise _auth_error("Refresh token is required")
    if db.in_transaction():
        await db.commit()

    now = _utc_now()
    token_hash = _refresh_token_hash(refresh_token)
    replacement = _new_refresh_token()
    async with db.begin():
        session = await db.scalar(
            select(AuthSession)
            .where(AuthSession.refresh_token_hash == token_hash)
            .with_for_update()
        )
        if session is None or session.revoked_at is not None:
            raise _auth_error("Refresh session is invalid")
        if not secrets.compare_digest(session.refresh_token_hash, token_hash):
            raise _auth_error("Refresh session is invalid")
        if session.device_id != device_id:
            raise _auth_error("Refresh session belongs to another device")
        if _is_expired(session.refresh_expires_at, now):
            raise _auth_error("Refresh session has expired")

        user = await db.scalar(
            select(User).where(
                User.user_id == session.user_id,
                User.deleted_at.is_(None),
            )
        )
        if user is None:
            raise _auth_error("The session user is unavailable")

        session.refresh_token_hash = _refresh_token_hash(replacement)
        session.refresh_expires_at = now + timedelta(days=REFRESH_TOKEN_INACTIVITY_DAYS)
        session.updated_at = now

    return user, IssuedSession(session=session, refresh_token=replacement)
