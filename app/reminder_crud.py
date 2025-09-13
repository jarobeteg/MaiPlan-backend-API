from sqlalchemy.sql import expression
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Reminder
from schemas import ReminderCreate

async def add_reminder(db: AsyncSession, reminder: ReminderCreate):
    new_reminder = Reminder(user_id=reminder.user_id, reminder_time=reminder.reminder_time, frequency=reminder.frequency, status=reminder.status, message=reminder.message)
    db.add(new_reminder)
    await db.flush()    # this populates new_reminder.reminder_id
    await db.commit()
    return new_reminder.reminder_id

async def get_reminder(db: AsyncSession, reminder_id: int):
    stmt = select(Reminder).where(expression.column("reminder_id") == reminder_id)
    result = await db.execute(stmt)
    return result.scalars().first()

async def get_reminders(db: AsyncSession, user_id: int):
    stmt = select(Reminder).where(expression.column("user_id") == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()
