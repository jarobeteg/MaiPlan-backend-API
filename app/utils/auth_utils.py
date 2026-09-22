import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from core.database import get_db
from core.models import AuthSession, User
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

env = os.environ["ENV"]
BASE_DIR = Path(__file__).resolve().parents[2]
env_file = BASE_DIR / f".env.{env}"
load_dotenv(env_file)
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRY_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRY_MINUTES", "15"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

@dataclass(frozen=True)
class AuthContext:
    user: User
    session: AuthSession


def _credential_error(message: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": "AUTH_REQUIRED", "message": message},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _is_expired(value: datetime, now: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value <= now


def create_access_token(
    user_id: int,
    session_id: UUID,
    device_id: UUID,
) -> tuple[str, datetime]:
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not configured")
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=ACCESS_TOKEN_EXPIRY_MINUTES)
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "did": str(device_id),
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM), expires_at


async def get_auth_context(
    token: str = Security(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not configured")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
        session_id = UUID(payload["sid"])
        device_id = UUID(payload["did"])
    except ExpiredSignatureError as exception:
        raise _credential_error("Access token has expired") from exception
    except (JWTError, KeyError, TypeError, ValueError) as exception:
        raise _credential_error("Access token is invalid") from exception

    session = await db.scalar(
        select(AuthSession).where(
            AuthSession.session_id == session_id,
            AuthSession.user_id == user_id,
            AuthSession.device_id == device_id,
            AuthSession.revoked_at.is_(None),
        )
    )
    if session is None or _is_expired(session.refresh_expires_at, datetime.now(timezone.utc)):
        raise _credential_error("Authentication session is invalid")

    user = await db.scalar(
        select(User).where(
            User.user_id == user_id,
            User.deleted_at.is_(None),
        )
    )
    if user is None:
        raise _credential_error()
    return AuthContext(user=user, session=session)


async def get_current_user(
    context: AuthContext = Depends(get_auth_context),
) -> User:
    return context.user
