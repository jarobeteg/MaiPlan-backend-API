import re
from typing import Annotated

from core.database import get_db
from core.models import User
from crud.user_crud import create_user, get_user_by_email, get_user_by_username
from fastapi import APIRouter, Depends, HTTPException
from schemas.auth_schema import (
    AuthResponse,
    RefreshTokenRequest,
    UserLogin,
    UserPasswordChange,
    UserPasswordReset,
    UserRegister,
    UserResponse,
    UserUsernameChange,
)
from services.account_service import change_password, change_username
from services.auth_session_service import (
    IssuedSession,
    create_session,
    reset_password_session,
    rotate_session,
)
from sqlalchemy.ext.asyncio import AsyncSession
from utils.auth_utils import (
    AuthContext,
    create_access_token,
    get_auth_context,
    get_current_user,
)
from utils.password_utils import do_passwords_match, is_valid_password, verify_password

router = APIRouter()

EMAIL_REGEX = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"

def validate_email(email: str):
    email = email.strip()
    if not email:
        raise HTTPException(status_code=400, detail={"code": 1, "message": "Email field cannot be empty!"})
    if not re.match(EMAIL_REGEX, email):
        raise HTTPException(status_code=400, detail={"code": 2, "message": "Invalid email format!"})
    return email

async def validate_email_existence(db: AsyncSession, email: str):
    existing_user = await get_user_by_email(db, email)
    if not existing_user:
        raise HTTPException(status_code=401, detail={"code": 3, "message": "Email is not yet registered!"})
    return existing_user

def validate_password(password: str):
    password = password.strip()
    if not password:
        raise HTTPException(status_code=400, detail={"code": 4, "message": "Password field cannot be empty!"})
    return password

def validate_password_strength(password: str):
    if not is_valid_password(password):
        raise HTTPException(status_code=400, detail={"code": 5, "message": "Password is not strong enough!"})

def validate_passwords(password: str, password_again: str):
    if not password_again:
        raise HTTPException(status_code=400, detail={"code": 6, "message": "Password again field cannot be empty!"})
    if not do_passwords_match(password, password_again):
        raise HTTPException(status_code=400, detail={"code": 7, "message": "Passwords do not match!"})

def build_auth_response(user, issued_session: IssuedSession) -> AuthResponse:
    access_token, access_expires_at = create_access_token(
        user_id=user.user_id,
        session_id=issued_session.session.session_id,
        device_id=issued_session.session.device_id,
    )
    return AuthResponse(
        access_token=access_token,
        refresh_token=issued_session.refresh_token,
        session_id=issued_session.session.session_id,
        access_token_expires_at=access_expires_at,
        refresh_token_expires_at=issued_session.session.refresh_expires_at,
        user=UserResponse.model_validate(user),
    )

@router.post("/register", response_model=AuthResponse)
async def register(user: UserRegister, db: Annotated[AsyncSession, Depends(get_db)]):
    user.email = validate_email(user.email)
    user.username = user.username.strip()

    if await get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail={"code": 8, "message": "Email is already taken!"})
    if not user.username:
        raise HTTPException(status_code=400, detail={"code": 9, "message": "Username field cannot be empty!"})
    if await get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail={"code": 10, "message": "Username is already taken!"})

    user.password = validate_password(user.password)
    validate_password_strength(user.password)
    validate_passwords(user.password, user.password_again.strip())
    new_user = await create_user(db, user)
    issued_session = await create_session(db, new_user, user.device_id)
    return build_auth_response(new_user, issued_session)

@router.post("/login", response_model=AuthResponse)
async def login(user: UserLogin, db: Annotated[AsyncSession, Depends(get_db)]):
    user.email = validate_email(user.email)
    existing_user = await validate_email_existence(db, user.email)

    user.password = validate_password(user.password)
    if not verify_password(user.password, existing_user.password_hash):
        raise HTTPException(status_code=401, detail={"code": 8, "message": "Incorrect password!"})
    if existing_user.deleted_at is not None:
        raise HTTPException(status_code=401, detail={"code": 8, "message": "Account is unavailable"})
    issued_session = await create_session(db, existing_user, user.device_id)
    return build_auth_response(existing_user, issued_session)


@router.post("/reset-password", response_model=AuthResponse)
async def reset_password(
    request: UserPasswordReset,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    request.email = validate_email(request.email)
    request.password = validate_password(request.password)
    validate_password_strength(request.password)
    validate_passwords(request.password, request.password_again.strip())
    user, issued_session = await reset_password_session(
        db,
        request.email,
        request.password,
        request.device_id,
    )
    return build_auth_response(user, issued_session)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    user, issued_session = await rotate_session(
        db,
        request.refresh_token,
        request.device_id,
    )
    return build_auth_response(user, issued_session)

# an example of a protected route by jwt
@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_my_username(
    request: UserUsernameChange,
    db: Annotated[AsyncSession, Depends(get_db)],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
) -> UserResponse:
    user = await change_username(
        db, auth_context.user.user_id, auth_context.session.device_id, request.username,
    )
    return UserResponse.model_validate(user)


@router.post("/change-password", response_model=UserResponse)
async def change_my_password(
    request: UserPasswordChange,
    db: Annotated[AsyncSession, Depends(get_db)],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
) -> UserResponse:
    request.password = validate_password(request.password)
    validate_password_strength(request.password)
    validate_passwords(request.password, request.password_again.strip())
    user = await change_password(
        db, auth_context.user.user_id, auth_context.session.device_id, request.password,
    )
    return UserResponse.model_validate(user)
