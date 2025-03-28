from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Reminder
from schemas import ReminderCreate, ReminderResponse

async def new_reminder(db: AsyncSession, reminder: ReminderCreate):
    """ Creates a new reminder and adds it to the database
    
    Args:
        db (AsyncSession): The database session
        reminder (ReminderCreate): Holds all the reminder data that needs to be added to the database
    """
    new_reminder = Reminder(reminder_id=reminder.reminder_id, user_id=reminder.user_id, reminder_time=reminder.reminder_time, frequency=reminder.frequecny, status=reminder.status, message=reminder.message)
    db.add(new_reminder)
    await db.commit()

async def get_reminder(db: AsyncSession, reminder_id: int):
    """ Fetches a reminder by given id
    
    Args:
        db (AsyncSession): The database session
        reminder_id (int): The id of the reminder to fetch

    Returns:
        ReminderResponse: The reminder data connected to the given id
    """
    result = await db.execute(select(Reminder).where(Reminder.reminder_id == reminder_id))
    return result.scalars().first()
