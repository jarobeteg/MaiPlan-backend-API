from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import UserRegister, UserLogin, UserResponse, Token
from crud import get_user_by_email, get_user_by_username, create_user
from auth_utils import create_access_token, get_current_user
from password_utils import hash_password, verify_password
from datetime import timedelta
import re

router = APIRouter()

EMAIL_REGEX = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"

@router.post("/register", response_model=UserResponse)
async def register(user: UserRegister, db: AsyncSession = Depends(get_db)):
    taken_email = await get_user_by_email(db, user.email)
    taken_username = await get_user_by_username(db, user.username)

    if taken_email:
        raise HTTPException(
                status_code=400, 
                detail={"code": 1, "message": "Email is already taken!"}
                )

    if taken_username:
        raise HTTPException(
                status_code=400, 
                detail={"code": 2, "message": "Username is already taken!"}
                )

    new_user = await create_user(db, user)

    return new_user

@router.post("/login", response_model=Token)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    if not user.email.strip():
        raise HTTPException(
                status_code=400,
                detail={"code": 1, "message": "Email field cannot be empty!"}
                )

    if not re.match(EMAIL_REGEX, user.email):
        raise HTTPException(
                status_code=400,
                detail={"code": 2, "message": "Invalid email format!"}
                )

    if not user.password.strip():
        raise HTTPException(
                status_code=400,
                detail={"code": 3, "message": "Password field cannot be empty!"}
                )

    existing_email = await get_user_by_email(db, user.email.strip())
    if not existing_email:
        raise HTTPException(
                status_code=401,
                detail={"code": 4, "message": "Email is not yet registered!"}
                )

    if not verify_password(user.password.strip(), existing_email.password_hash):
        raise HTTPException(
                status_code=401,
                detail={"code": 5, "message": "Incorrect password!"}
                )
    
    token_data = {"sub": existing_user.user_id}
    access_token = create_access_token(data=token_data)

    return {"access_token": access_token, "token_type": "bearer"}

# an example of a protected route by jwt
@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: UserResponse = Depends(get_current_user)):
    return current_user
