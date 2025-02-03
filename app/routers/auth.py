from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import UserCreate, UserResponse, Token
from crud import get_user, create_user
from routers.auth_utils import create_access_token, verify_password, get_current_user
from datetime import timedelta

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing_user = await get_user(db, user.email, user.username)

    if not existing_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    if not verify_password(user.password, existing_user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    token_data = {"sub": existing_user.email, "username": existing_user.username}
    access_token = create_access_token(data=token_data, expires_delta=timedelta(days=30))

    return {"access_token": access_token, "token_type": "bearer"}

# an example of a protected route by jwt
@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: UserResponse = Depends(get_current_user)):
    return current_user