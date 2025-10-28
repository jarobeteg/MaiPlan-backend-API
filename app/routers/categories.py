from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas.category_schema import CategoryCreate, CategoryResponse, CategorySync
from schemas.sync_schema import SyncRequest, SyncResponse
from crud.category_crud import get_categories, add_category, remake_category, remove_category
from models import Category
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
    await add_category(db, category)

@router.get("/get-all-category", response_model=List[CategoryResponse])
async def get_all_category(user_id: int, db: AsyncSession = Depends(get_db)):
    return await get_categories(db, user_id)

@router.post("/update-category")
async def update_category(category: CategoryResponse, db: AsyncSession = Depends(get_db)):
    validate_category_data(category.name, category.description)
    await remake_category(db, category)

@router.delete("/{category_id}")
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await remove_category(db, category_id)

    if not deleted:
        raise HTTPException(status_code=404, detail={"code": 3, "message": "Category not found!"})

@router.post("/sync", response_model=SyncResponse[CategorySync])
async def category_sync(request: SyncRequest[CategorySync], db: AsyncSession = Depends(get_db)):
    acknowledged = []
    rejected = []

    pass

def to_category_sync(category: Category) -> CategorySync:
    return CategorySync(
    category_id=category.category_id,
    server_id=category.server_id,
    user_id=category.user_id,
    name=category.name,
    description=category.description,
    color=category.color,
    icon=category.icon,
    last_modified=int(category.last_modified.timestamp() * 1000),
    sync_state=category.sync_state,
    is_deleted=category.is_deleted
    )