from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Event
from schemas import EventCreate, EventResponse

async def new_event(db: AsyncSession, event: EventCreate):
    new_event = Event(
            event_id=event.event_id,
            user_id=event.user_id,
            category_id=event.category_id,
            reminder_id=event.reminder_id,
            title=event.title,
            description=event.description,
            date=event.date,
            start_time=event.start_time,
            end_time=event.end_time,
            priority=event.priority,
            location=event.location
            )
    db.add(new_event)
    await db.commit()

async def get_event(db: AsyncSession, event_id: int):
    result = await db.execute(select(Event).where(Event.event_id == event_id))
    return result.scalars().first()
