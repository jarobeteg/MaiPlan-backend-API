from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import CategoryCreate, CategoryResponse
from category_crud import get_categories, new_category
from typing import List

router = APIRouter()

@router.post("/create-category")
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_db)):
    await new_category(db, category)

@router.get("/get-all-category", response_model=List[CategoryResponse])
async def get_all_category(user_id: int, db: AsyncSession = Depends(get_db)):
    return await get_categories(db, user_id)
