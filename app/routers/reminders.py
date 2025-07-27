from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import ReminderCreate, ReminderResponse
from reminder_crud import new_reminder, get_reminder, get_reminders
from typing import List

router = APIRouter()

@router.post("/create-reminder")
async def create_reminder(reminder: ReminderCreate, db: AsyncSession = Depends(get_db)):
    """ This API creates a new reminder in the Database

    Args:
        reminder (ReminderCreate): Holds all the data that needs to be insterted into the database
        db (AsyncSession): The database session dependency

    Returns:
        Int: The created reminder id number
    """
    return await new_reminder(db, reminder)

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

@router.get("/get-all-reminder", response_model=List[ReminderResponse])
async def get_all_reminder(user_id: int, db: AsyncSession = Depends(get_db)):
    """ This API fetches all the reminders into a list

    Args:
        user_id (int): An id to indentify all the events connected to this user
        db (AsyncSession): The database session dependency

    Returns:
        List[ReminderResponse]: A list of reminders
    """
    return await get_reminders(db, user_id)
