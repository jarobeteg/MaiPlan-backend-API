from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Category
from schemas import CategoryCreate, CategoryResponse

async def new_category(db: AsyncSession, category: CategoryCreate):
    """ Creates a new category and adds it to the database

    Args:
        db (AsyncSession): The database session
        category (CategoryCreate): Holds all the category data that needs to be added to the database
    """
    new_category = Category(user_id=category.user_id, name=category.name, description=category.description, color=category.color, icon=category.icon)
    db.add(new_category)
    await db.commit()

async def get_categories(db: AsyncSession, user_id: int):
    """ Fetches all categories for a given user
    
    Args:
        db (AsyncSession): The database session
        user_id (int): The id of the user whose categories should be fetched

    Returns:
        List[CategoryResponse]: A list of categories connected with the given user 
    """
    result = await db.execute(select(Category).where(Category.user_id == user_id))
    return result.scalars().all()

async def remake_category(db: AsyncSession, category_data: CategoryResponse):
    """ Updates an existing category in the database 
    
    Args:
        db (AsyncSession): The database session
        category_data (CategoryResponse): The updated category data

    Raises:
        HTTPException: If the category is not found
    """
    result = await db.execute(select(Category).where(Category.category_id == category_data.category_id))
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
    """ Deletes a category from the database
    
    Args:
        db (AsyncSession): The database session
        category_id (int): The id of the category that needs to be deleted

    Returns:
        bool: True if the category was deleted

    Raises:
        HTTPException: If the category is not found
    """
    result = await db.execute(select(Category).where(Category.category_id == category_id))
    category = result.scalars().first()

    if not category:
        raise HTTPException(status_code=404, detail={"code": 3, "message": "Category not found!"})

    await db.delete(category)
    await db.commit()
    return True
