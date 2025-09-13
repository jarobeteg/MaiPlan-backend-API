from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import UserRegister, UserLogin, UserResponse, UserResetPassword, Token
from app.user_crud import get_user_by_email, get_user_by_username, create_user, reset_user_password
from app.auth_utils import create_access_token, get_current_user
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

def get_access_token(user_id: int):
    token_data = {"sub": user_id}
    return create_access_token(data=token_data)

@router.post("/register", response_model=Token)
async def register(user: UserRegister, db: AsyncSession = Depends(get_db)):
    user.email = validate_email(user.email)
    user.username = user.username.strip()

    if await get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail={"code": 8, "message": "Email is already taken!"})
    if not user.username:
        raise HTTPException(status_code=400, detail={"code": 9, "message": "Username field cannot be empty!"})
    if await get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail={"code": 10, "message": "Username is already taken!"})

    new_user = await create_user(db, user)

    return Token(access_token=get_access_token(new_user.user_id), token_type="bearer")

@router.post("/login", response_model=Token)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    user.email = validate_email(user.email)
    existing_user = await validate_email_existence(db, user.email)

    if user.password_hash != existing_user.password_hash:
        raise HTTPException(status_code=401, detail={"code": 8, "message": "Incorrect password!"})

    return Token(access_token=get_access_token(existing_user.user_id), token_type="bearer")

@router.post("/reset-password", response_model=Token)
async def reset_password(user: UserResetPassword, db: AsyncSession = Depends(get_db)):
    user.email = validate_email(user.email)
    existing_user = await validate_email_existence(db, user.email)

    await reset_user_password(db, user)

    return Token(access_token=get_access_token(existing_user.user_id), token_type="bearer")

@router.post("/token-refresh", response_model=Token)
async def token_refresh(current_user: UserResponse = Depends(get_current_user)):
    return Token(access_token=get_access_token(current_user.user_id), token_type="bearer")

# an example of a protected route by jwt
@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: UserResponse = Depends(get_current_user)):
    return current_user
