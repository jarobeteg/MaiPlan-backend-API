from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import CategoryCreate, CategoryResponse
from category_crud import get_categories, new_category, remake_category, remove_category
from typing import List

router = APIRouter()

def validate_category_data(name: str, description: str):
    if not name.strip():
        raise HTTPException(status_code=400, detail={"code": 1, "message": "Name field cannot be empty!"})
    if not description.strip():
        raise HTTPException(status_code=400, detail={"code": 2, "message": "Description field cannot be empty!"})

@router.post("/create-category")
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_db)):
    validate_category_data(category.name, category.description)
    await new_category(db, category)

@router.get("/get-all-category", response_model=List[CategoryResponse])
async def get_all_category(user_id: int, db: AsyncSession = Depends(get_db)):
    return await get_categories(db, user_id)

@router.post("/update-category")
async def update_category(category: CategoryResponse, db: AsyncSession = Depends(get_db)):
    validate_category_data(category.name, category.description)
    await remake_category(db, category)

@router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await remove_category(db, category_id)

    if not deleted:
        raise HTTPException(status_code=404, detail={"code": 3, "message": "Category not found!"})

    return
