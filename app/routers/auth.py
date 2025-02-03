from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import UserAuth, UserResponse, Token
from crud import get_user, create_user
from auth_utils import create_access_token, get_current_user
from password_utils import hash_password, verify_password
from datetime import timedelta

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user: UserAuth, db: AsyncSession = Depends(get_db)):
    existing_user = await get_user(db, user.email, user.username)

    if existing_user:
        raise HTTPException(status_code=401, detail="User already exists")
    
    user.password = hash_password(user.password)

    new_user = await create_user(db, user)
    
    return new_user

@router.post("/login", response_model=Token)
async def login(user: UserAuth, db: AsyncSession = Depends(get_db)):
    existing_user = await get_user(db, user.email, user.username)

    if not existing_user or not verify_password(user.password, existing_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token_data = {"sub": existing_user.user_id}
    access_token = create_access_token(data=token_data)

    return {"access_token": access_token, "token_type": "bearer"}

# an example of a protected route by jwt
@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: UserResponse = Depends(get_current_user)):
    return current_user