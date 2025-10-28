from sqlalchemy.sql import expression
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Event
from schemas.event_schema import EventCreate, EventResponse
from datetime import datetime, date, time

async def add_event(db: AsyncSession, event: EventCreate):
    event_date = datetime.fromtimestamp(event.date / 1000).date()
    start_time = datetime.fromtimestamp(event.start_time / 1000).time()
    end_time = datetime.fromtimestamp(event.end_time / 1000).time()

    new_event = Event(
            user_id=event.user_id,
            category_id=event.category_id,
            reminder_id=event.reminder_id,
            title=event.title,
            description=event.description,
            date=event_date,
            start_time=start_time,
            end_time=end_time,
            priority=event.priority,
            location=event.location
            )
    db.add(new_event)
    await db.commit()

async def get_event(db: AsyncSession, event_id: int):
    stmt = select(Event).where(expression.column("event_id") == event_id)
    result = await db.execute(stmt)
    return result.scalars().first()

async def get_events(db: AsyncSession, user_id: int):
    stmt = select(Event).where(expression.column("user_id") == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()
