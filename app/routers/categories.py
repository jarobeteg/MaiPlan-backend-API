from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas.category_schema import CategoryCreate, CategoryResponse, CategorySync
from schemas.sync_schema import SyncRequest, SyncResponse
from crud.category_crud import get_categories, add_category, remake_category, remove_category, make_category, get_category, get_pending_categories, set_category_sync_state
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

    change = request.changes[0] if len(request.changes) > 0 else None

    if not change:
        pending_categories: List[Category] = await get_pending_categories(db, request.user_id)
        for pending_category in pending_categories:
            await set_category_sync_state(db, pending_category.category_id, 0)
            await db.refresh(pending_category)
            acknowledged.append(pending_category)

        return SyncResponse(user_id=request.user_id, acknowledged=acknowledged, rejected=rejected)

    for category in request.changes:
        if category.server_id is None:
            if category.is_deleted == 0:
                new_category = await make_category(db, category)
                acknowledged.append(new_category)
            else:
                rejected.append(category)
        else:
            if category.is_deleted == 0:
                existing_category = await get_category(db, category.server_id)
                await set_category_sync_state(db, category.server_id, 0)
                await db.refresh(existing_category)
                existing_category_data = CategorySync.model_validate(existing_category)
                existing_category_data.category_id = category.category_id
                acknowledged.append(existing_category_data)
            else:
                await remove_category(db, category.server_id)
                rejected.append(category)

    return SyncResponse(user_id=request.user_id, acknowledged=acknowledged, rejected=rejected)

def to_category_sync(category: Category) -> CategorySync:
    return CategorySync(
    category_id=category.category_id,
    server_id=category.server_id,
    user_id=category.user_id,
    name=category.name,
    description=category.description,
    color=category.color,
    icon=category.icon,
    created_at=category.created_at,
    updated_at=category.updated_at,
    last_modified=int(category.last_modified.timestamp() * 1000),
    sync_state=category.sync_state,
    is_deleted=category.is_deleted
    )