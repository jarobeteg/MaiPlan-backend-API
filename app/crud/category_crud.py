from fastapi import HTTPException
from sqlalchemy.sql import expression
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Category
from schemas import CategoryCreate, CategoryResponse

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
