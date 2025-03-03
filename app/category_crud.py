from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Category
from schemas import CategoryCreate, CategoryResponse

async def new_category(db: AsyncSession, category: CategoryCreate):
    new_category = Category(category_id=category.category_id, user_id=category.user_id, entity_type=category.entity_type, name=category.name, description=category.description)
    db.add(new_category)
    await db.commit()

async def get_categories(db: AsyncSession, user_id: int):
    result = await db.execute(select(Category).where(Category.user_id == user_id))
    return result.scalars().all()
