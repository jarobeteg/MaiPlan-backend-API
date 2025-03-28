from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import CategoryCreate, CategoryResponse
from category_crud import get_categories, new_category, remake_category, remove_category
from typing import List

router = APIRouter()

def validate_category_data(name: str, description: str):
    """ Validates category data

    Args:
        name (str): The name of the category
        description (str): The description of the category

    Raises:
        HTTPException: If name or description field is empty
    """
    if not name.strip():
        raise HTTPException(status_code=400, detail={"code": 1, "message": "Name field cannot be empty!"})
    if not description.strip():
        raise HTTPException(status_code=400, detail={"code": 2, "message": "Description field cannot be empty!"})

@router.post("/create-category")
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_db)):
    """ This API creates a new category in the Database

    Args:
        category (CategoryCreate): Holds all the data that needs to be inserted into the database
        db (AsyncSession): The database session dependency
    """
    validate_category_data(category.name, category.description)
    await new_category(db, category)

@router.get("/get-all-category", response_model=List[CategoryResponse])
async def get_all_category(user_id: int, db: AsyncSession = Depends(get_db)):
    """ This API fetches all the categories into a list

    Args:
        user_id (int): An id to indentify all the categories connected to this user
        db (AsyncSession): The database session dependency

    Returns:
        List[CategoryResponse]: A list of categories
    """
    return await get_categories(db, user_id)

@router.post("/update-category")
async def update_category(category: CategoryResponse, db: AsyncSession = Depends(get_db)):
    """ This API updates a category in the database

    Args:
        category (CategoryResponse): The category that is going to be updated
        db (AsyncSession): The database session dependency
    """
    validate_category_data(category.name, category.description)
    await remake_category(db, category)

@router.delete("/{category_id}")
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    """ This API will delete a category from the database
    
    Args:
        category_id (int): The category with this id needs to be deleted
        db (AsyncSession): The database session dependency
    
    Raises:
        HTTPException: If the database query does not find a category with the given id
    """
    deleted = await remove_category(db, category_id)

    if not deleted:
        raise HTTPException(status_code=404, detail={"code": 3, "message": "Category not found!"})
