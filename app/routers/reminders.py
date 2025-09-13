from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import ReminderCreate, ReminderResponse
from app.reminder_crud import add_reminder, get_reminder, get_reminders
from typing import List

router = APIRouter()

@router.post("/create-reminder")
async def create_reminder(reminder: ReminderCreate, db: AsyncSession = Depends(get_db)):
    return await add_reminder(db, reminder)

@router.get("/get-reminder-by-id", response_model=ReminderResponse)
async def get_reminder_by_id(reminder_id: int, db: AsyncSession = Depends(get_db)):
    return await get_reminder(db, reminder_id)

@router.get("/get-all-reminder", response_model=List[ReminderResponse])
async def get_all_reminder(user_id: int, db: AsyncSession = Depends(get_db)):
    return await get_reminders(db, user_id)
