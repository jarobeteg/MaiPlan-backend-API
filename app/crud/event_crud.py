from fastapi import HTTPException
from sqlalchemy.sql import expression
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import Event
from schemas.event_schema import EventCreate, EventSync
from datetime import datetime, time, date, timedelta

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

async def make_event(db: AsyncSession, event: EventSync):
    created_at = datetime.fromtimestamp(event.created_at / 1000)
    date_value = datetime.fromtimestamp(event.date / 1000).date()
    start_time = datetime.fromtimestamp(event.start_time / 1000).time()
    end_time = datetime.fromtimestamp(event.end_time / 1000).time()
    new_event = Event(
        user_id=event.user_id,
        category_id=event.category_id,
        reminder_id=None if event.reminder_id == 0 else event.reminder_id,
        title=event.title,
        description=event.description,
        date=date_value,
        start_time=start_time,
        end_time=end_time,
        priority=event.priority,
        location=event.location,
        created_at=created_at
    )
    db.add(new_event)
    await db.flush()
    new_event.server_id = new_event.event_id
    await db.commit()
    await db.refresh(new_event)
    new_event_data = EventSync(
        event_id=event.event_id,
        server_id=new_event.server_id,
        user_id=new_event.user_id,
        category_id=new_event.category_id,
        reminder_id=0 if new_event.reminder_id is None else new_event.reminder_id,
        title=new_event.title,
        description=new_event.description,
        date=int(datetime.combine(new_event.date, time.min).timestamp() * 1000),
        start_time=int(datetime.combine(new_event.date, new_event.start_time).timestamp() * 1000),
        end_time=int(datetime.combine(new_event.date, new_event.end_time).timestamp() * 1000),
        priority=new_event.priority,
        location=new_event.location,
        created_at=int(new_event.created_at.timestamp() * 1000),
        updated_at=int(new_event.updated_at.timestamp() * 1000),
        last_modified=int(new_event.last_modified.timestamp() * 1000),
        sync_state=new_event.sync_state,
        is_deleted=new_event.is_deleted
    )
    return new_event_data

async def remove_event(db: AsyncSession, event_id: int):
    stmt = select(Event).where(expression.column("event_id") == event_id)
    result = await db.execute(stmt)
    event = result.scalars().first()

    if not event:
        raise HTTPException(status_code=404, detail={"code": 3, "message": "Event not found!"})

    await db.delete(event)
    await db.commit()
    return True

async def get_pending_events(db: AsyncSession, user_id: int):
    stmt = select(Event).where(
        (expression.column("user_id") == user_id) & (expression.column("sync_state") != 0)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def set_event_sync_state(db: AsyncSession, event_id: int, sync_state: int):
    stmt = (
        update(Event)
        .where(expression.column("event_id") == event_id)
        .values(sync_state=sync_state)
        .execution_options(synchronize_session="fetch")
    )

    await db.execute(stmt)
    await db.commit()

async def set_event(
        db: AsyncSession,
        event_id: int,
        category_id: int,
        reminder_id: int,
        title: str,
        description: str,
        date_event: int,
        start_time: int,
        end_time: int,
        priority: int,
        location: str,
        sync_state: int
):
    date_converted = datetime.fromtimestamp(date_event / 1000).date()
    start_time_converted = datetime.fromtimestamp(start_time / 1000).time()
    end_time_converted = datetime.fromtimestamp(end_time / 1000).time()
    stmt = (
        update(Event)
        .where(expression.column("event_id") == event_id)
        .values(
            category_id=category_id,
            reminder_id=reminder_id,
            title=title,
            description=description,
            date=date_converted,
            start_time=start_time_converted,
            end_time=end_time_converted,
            priority=priority,
            location=location,
            sync_state=sync_state
        )
        .execution_options(synchronize_session="fetch")
    )

    await db.execute(stmt)
    await db.commit()
