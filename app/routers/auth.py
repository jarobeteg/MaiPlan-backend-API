from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import UserRegister, UserLogin, UserResponse, UserResetPassword, Token, AuthResponse, AuthSync, SyncRequest, SyncResponse
from crud.user_crud import get_user_by_email, get_user_by_username, create_user, reset_user_password, sync_user
from utils.auth_utils import create_access_token, get_current_user
from utils.password_utils import verify_password, is_valid_password, do_passwords_match
from models import User
from datetime import datetime
from sqlalchemy.sql import expression
from sqlalchemy import select
import re

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

def get_access_token(user_id: int):
    token_data = {"sub": user_id}
    return create_access_token(data=token_data)

@router.post("/register", response_model=AuthResponse)
async def register(user: UserRegister, db: AsyncSession = Depends(get_db)):
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

    return AuthResponse(access_token=get_access_token(new_user.user_id), user=new_user)

@router.post("/login", response_model=AuthResponse)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    user.email = validate_email(user.email)
    existing_user = await validate_email_existence(db, user.email)

    user.password = validate_password(user.password)
    if not verify_password(user.password, existing_user.password_hash):
        raise HTTPException(status_code=401, detail={"code": 8, "message": "Incorrect password!"})

    return AuthResponse(access_token=get_access_token(existing_user.user_id), user=existing_user)

@router.post("/reset-password", response_model=AuthResponse)
async def reset_password(user: UserResetPassword, db: AsyncSession = Depends(get_db)):
    user.email = validate_email(user.email)
    existing_user = await validate_email_existence(db, user.email)

    user.password = validate_password(user.password)
    validate_password_strength(user.password)
    validate_passwords(user.password, user.password_again.strip())
    await reset_user_password(db, user)

    return AuthResponse(access_token=get_access_token(existing_user.user_id), user=existing_user)

@router.post("/token-refresh", response_model=Token)
async def token_refresh(current_user: UserResponse = Depends(get_current_user)):
    return Token(access_token=get_access_token(current_user.user_id), token_type="bearer")

# an example of a protected route by jwt
@router.get("/me", response_model=AuthResponse)
async def get_my_profile(current_user: UserResponse = Depends(get_current_user)):
    return AuthResponse(access_token=get_access_token(current_user.user_id), user=current_user)

@router.post("/sync", response_model=SyncResponse[AuthSync])
async def auth_sync(request: SyncRequest[AuthSync], db: AsyncSession = Depends(get_db)):
    server_changes = []
    acknowledged = []

    for change in request.changes:
        stmt = select(User).where(expression.column("user_id") == change.server_id)
        result = await db.execute(stmt)
        existing = result.scalars().first()

        if existing:
            # Update existing record
            existing.email = change.email
            existing.username = change.username
            existing.balance = change.balance
            existing.password_hash = change.password_hash
            existing.last_modified = change.last_modified
            existing.sync_state = change.sync_state
            existing.is_deleted = change.is_deleted
            existing.server_id = change.server_id
            acknowledged.append(change)
        else:
            new_user = User(
                user_id=change.user_id,
                email=change.email,
                username=change.username,
                balance=change.balance,
                password_hash=change.password_hash,
                last_modified=change.last_modified,
                sync_state=change.sync_state,
                is_deleted=change.is_deleted,
                server_id=change.server_id
            )
            db.add(new_user)
            acknowledged.append(change)

    await db.commit()

    #there should be a separate table to store lastSync or something similar, this will be fixed and also refactored
    stmt = select(User).where(User.last_modified > 0)
    result = await db.execute(stmt)
    updated_users = result.scalars().all()

    for user in updated_users:
        server_changes.append(
            AuthSync(
                user_id=user.user_id,
                server_id=user.server_id,
                email=user.email,
                username=user.username,
                balance=float(user.balance),
                created_at=user.created_at.timestamp(),
                updated_at=user.updated_at.timestamp(),
                password_hash=user.password_hash,
                last_modified=user.last_modified,
                sync_state=user.sync_state,
                is_deleted=user.is_deleted
            )
        )

    return SyncResponse(server_changes=server_changes, acknowledged=acknowledged)