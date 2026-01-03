from fastapi import HTTPException
from sqlalchemy.sql import expression
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import Category
from datetime import datetime
from schemas.category_schema import CategoryCreate, CategoryResponse, CategorySync

async def add_category(db: AsyncSession, category: CategoryCreate):
    new_category = Category(user_id=category.user_id, name=category.name, description=category.description, color=category.color, icon=category.icon)
    db.add(new_category)
    await db.commit()

async def get_categories(db: AsyncSession, user_id: int):
    stmt = select(Category).where(expression.column("user_id") == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()

async def remake_category(db: AsyncSession, category_data: CategoryResponse):
    stmt = select(Category).where(expression.column("category_id") == category_data.category_id)
    result = await db.execute(stmt)
    category = result.scalars().first()
    
    if not category:
        raise HTTPException(status_code=404, detail={"code": 3, "message": "Category not found!"})

    category.name = category_data.name
    category.description = category_data.description
    category.color = category_data.color
    category.icon = category_data.icon

    await db.commit()
    await db.refresh(category)

async def remove_category(db: AsyncSession, category_id: int):
    stmt = select(Category).where(expression.column("category_id") == category_id)
    result = await db.execute(stmt)
    category = result.scalars().first()

    if not category:
        raise HTTPException(status_code=404, detail={"code": 3, "message": "Category not found!"})

    await db.delete(category)
    await db.commit()
    return True

async def make_category(db: AsyncSession, category: CategorySync):
    created_at = datetime.fromtimestamp(category.created_at / 1000)
    new_category = Category(
        user_id=category.user_id,
        name=category.name,
        description=category.description,
        color=category.color,
        icon=category.icon,
        created_at=created_at
    )
    db.add(new_category)
    await db.flush()
    new_category.server_id = new_category.category_id
    await db.commit()
    await db.refresh(new_category)
    new_category_data = CategorySync(
        category_id=category.category_id,
        server_id=new_category.server_id,
        user_id=new_category.user_id,
        name=new_category.name,
        description=new_category.description,
        color=new_category.color,
        icon=new_category.icon,
        created_at=int(new_category.created_at.timestamp() * 1000),
        updated_at=int(new_category.updated_at.timestamp() * 1000),
        last_modified=int(new_category.last_modified.timestamp() * 1000),
        sync_state=new_category.sync_state,
        is_deleted=new_category.is_deleted,
    )
    return new_category_data

async def get_category(db: AsyncSession, category_id: int):
    stmt = select(Category).where(expression.column("category_id") == category_id)
    result = await db.execute(stmt)
    return result.scalars().first()

async def get_pending_categories(db: AsyncSession, user_id: int):
    stmt = select(Category).where(
        (expression.column("user_id") == user_id) & (expression.column("sync_state") != 0)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def set_category_sync_state(db: AsyncSession, category_id: int, sync_state: int):
    stmt = (
        update(Category)
        .where(expression.column("category_id") == category_id)
        .values(sync_state=sync_state)
        .execution_options(synchronize_session="fetch")
    )

    await db.execute(stmt)
    await db.commit()

async def set_category(
        db: AsyncSession,
        category_id: int,
        name: str,
        description: str,
        color: str,
        icon: str,
        sync_state: int
):
    stmt = (
        update(Category)
        .where(expression.column("category_id") == category_id)
        .values(
            name=name,
            description=description,
            color=color,
            icon=icon,
            sync_state=sync_state
        )
        .execution_options(synchronize_session="fetch")
    )

    await db.execute(stmt)
    await db.commit()