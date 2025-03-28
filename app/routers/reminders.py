from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import ReminderCreate, ReminderResponse
from reminder_crud import new_reminder, get_reminder

router = APIRouter()

@router.post("/create-reminder")
async def create_reminder(reminder: ReminderCreate, db: AsyncSession = Depends(get_db)):
    """ This API creates a new reminder in the Database

    Args:
        reminder (ReminderCreate): Holds all the data that needs to be insterted into the database
        db (AsyncSession): The database session dependency
    """
    await new_reminder(db, reminder)

@router.get("/get-reminder-by-id", response_model=ReminderResponse)
async def get_reminder_by_id(reminder_id: int, db: AsyncSession = Depends(get_db)):
    """ This API fetches a reminder by the given id

    Args:
        reminder_id (int): An id to get the correct reminder data from the database
        db (AsyncSession): The database session dependency

    Returns:
        ReminderResponse: The correct reminder data fetched by the id
    """
    return await get_reminder(db, reminder_id)
