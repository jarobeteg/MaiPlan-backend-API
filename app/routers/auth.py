from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas.auth_schema import UserRegister, UserLogin, UserResponse, UserResetPassword, Token, AuthResponse, AuthSync
from schemas.sync_schema import SyncRequest, SyncResponse
from models import User
from crud.user_crud import get_user_by_email, get_user_by_username, create_user, reset_user_password, get_pending_user, set_auth_sync_state
from utils.auth_utils import create_access_token, get_current_user
from utils.password_utils import verify_password, is_valid_password, do_passwords_match
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
    acknowledged = []
    rejected = []

    change = request.changes[0] if len(request.changes) > 0 else None

    if not change:
        pending_user: User = await get_pending_user(db, request.email)
        if pending_user:
            await set_auth_sync_state(db, request.email, sync_state=0)
            await db.refresh(pending_user)
            acknowledged.append(to_auth_sync(pending_user))

        return SyncResponse(email=request.email, acknowledged=acknowledged, rejected=rejected)

    existing_user: User = await get_user_by_email(db, request.email)

    if not existing_user:
        change.is_deleted = 1
        rejected.append(change)
        return SyncResponse(email=request.email, acknowledged=acknowledged, rejected=rejected)

    existing_last_modified_ms = int(existing_user.last_modified.timestamp() * 1000)

    if change.last_modified <= existing_last_modified_ms:
        match change.sync_state:
            case 1:
                change.sync_state = 2
            case 2:
                change.sync_state = 1

    match change.sync_state:
         case 1:
             pass
         case 2:
             await set_auth_sync_state(db, request.email, sync_state=0)
             await db.refresh(existing_user)
             acknowledged.append(to_auth_sync(existing_user))
         case 3:
             pass
         case 4:
             await set_auth_sync_state(db, request.email, sync_state=0)
             await db.refresh(existing_user)
             acknowledged.append(to_auth_sync(existing_user))

    return SyncResponse(email=request.email, acknowledged=acknowledged, rejected=rejected)

def to_auth_sync(user: User) -> AuthSync:
    return AuthSync(
        user_id=user.user_id,
        server_id=user.server_id,
        email=user.email,
        username=user.username,
        balance=float(user.balance),
        created_at=int(user.created_at.timestamp() * 1000),
        updated_at=int(user.updated_at.timestamp() * 1000),
        password_hash=user.password_hash,
        last_modified=int(user.last_modified.timestamp() * 1000),
        sync_state=user.sync_state,
        is_deleted=user.is_deleted
    )
