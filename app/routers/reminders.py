from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import ReminderCreate, ReminderResponse
from reminder_crud import new_reminder, get_reminder

router = APIRouter()

@router.post("/create-reminder")
async def create_reminder(reminder: ReminderCreate, db: AsyncSession = Depends(get_db)):
    await new_reminder(db, reminder)

@router.get("/get-reminder-by-id", response_model=ReminderResponse)
async def get_reminder_by_id(reminder_id: int, db: AsyncSession = Depends(get_db)):
    return await get_reminder(db, reminder_id)
