from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import UserRegister, UserLogin, UserResponse, Token
from crud import get_user_by_email, get_user_by_username, create_user
from auth_utils import create_access_token, get_current_user
from password_utils import hash_password, verify_password
from datetime import timedelta

router = APIRouter()

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
    existing_email = await get_user_by_email(db, user.email)
    password_match = verify_password(user.password, existing_email.password_hash)

    if not existing_email and not password_match:
        raise HTTPException(
                status_code=401,
                detail={"code": 1, "message": "Invalid credentials!"}
                )

    if not existing_email:
        raise HTTPException(
                status_code=401,
                detail={"code": 2, "message": "Email is not yet registered!"}
                )

    if not password_match:
        raise HTTPException(
                status_code=401,
                detail={"code": 3, "message": "Incorrect password!"}
                )
    
    token_data = {"sub": existing_user.user_id}
    access_token = create_access_token(data=token_data)

    return {"access_token": access_token, "token_type": "bearer"}

# an example of a protected route by jwt
@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: UserResponse = Depends(get_current_user)):
    return current_user
