from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Reminder
from schemas import ReminderCreate, ReminderResponse

async def new_reminder(db: AsyncSession, reminder: ReminderCreate):
    new_reminder = Reminder(reminder_id=reminder.reminder_id, user_id=reminder.user_id, reminder_time=reminder.reminder_time, frequency=reminder.frequecny, status=reminder.status, message=reminder.message)
    db.add(new_reminder)
    await db.commit()

async def get_reminder(db: AsyncSession, reminder_id: int):
    result = await db.execute(select(Reminder).where(Reminder.reminder_id == reminder_id))
    return result.scalars().first()
