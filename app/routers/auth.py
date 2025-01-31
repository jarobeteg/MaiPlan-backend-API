from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import UserCreate, UserResponse
from crud import get_user, create_user

router = APIRouter()

@router.post("/login", response_model=UserResponse)
async def login(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing_user = await get_user(db, user.email, user.username)

    if existing_user:
        return existing_user
    
    new_user = await create_user(db, user)
    return new_user