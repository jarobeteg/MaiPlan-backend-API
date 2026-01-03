from fastapi import HTTPException
from sqlalchemy.sql import expression
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import Reminder
from schemas.reminder_schema import ReminderCreate, ReminderSync
from datetime import datetime

async def add_reminder(db: AsyncSession, reminder: ReminderCreate):
    reminder_datetime = datetime.fromtimestamp(reminder.reminder_time)

    new_reminder = Reminder(user_id=reminder.user_id, reminder_time=reminder_datetime, frequency=reminder.frequency, status=reminder.status, message=reminder.message)
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

async def make_reminder(db: AsyncSession, reminder: ReminderSync):
    created_at = datetime.fromtimestamp(reminder.created_at / 1000)
    reminder_time = datetime.fromtimestamp(reminder.reminder_time / 1000)
    new_reminder = Reminder(
        user_id=reminder.user_id,
        reminder_time=reminder_time,
        frequency=reminder.frequency,
        status=reminder.status,
        message=reminder.message,
        created_at = created_at
    )
    db.add(new_reminder)
    await db.flush()
    new_reminder.server_id = new_reminder.reminder_id
    await db.commit()
    await db.refresh(new_reminder)
    new_reminder_data = ReminderSync(
        reminder_id=reminder.reminder_id,
        server_id=new_reminder.server_id,
        user_id=new_reminder.user_id,
        reminder_time=int(new_reminder.time.timestamp() * 1000),
        frequency=new_reminder.frequency,
        status=new_reminder.status,
        message=new_reminder.message,
        created_at=int(new_reminder.created_at.timestamp() * 1000),
        updated_at=int(new_reminder.updated_at.timestamp() * 1000),
        last_modified=int(new_reminder.last_modified.timestamp() * 1000),
        sync_state=new_reminder.sync_state,
        is_deleted=new_reminder.is_deleted
    )
    return new_reminder_data

async def remove_reminder(db: AsyncSession, reminder_id: int):
    stmt = select(Reminder).where(expression.column("reminder_id") == reminder_id)
    result = await db.execute(stmt)
    reminder = result.scalars().first()

    if not reminder:
        raise HTTPException(status_code=404, detail={"code": 3, "message": "Reminder not found!"})

    await db.delete(reminder)
    await db.commit()
    return True

async def get_pending_reminders(db: AsyncSession, user_id: int):
    stmt = select(Reminder).where(
        (expression.column("user_id") == user_id) & (expression.column("sync_state") != 0)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def set_reminder_sync_state(db: AsyncSession, reminder_id: int, sync_state: int):
    stmt = (
        update(Reminder)
        .where(expression.column("reminder_id") == reminder_id)
        .values(sync_state=sync_state)
        .execution_options(synchronize_session="fetch")
    )

    await db.execute(stmt)
    await db.commit()

async def set_reminder(
        db: AsyncSession,
        reminder_id: int,
        reminder_time: int,
        frequency: int,
        status: int,
        message: str,
        sync_state: int,
):
    reminder_time_converted = datetime.fromtimestamp(reminder_time / 1000)
    stmt = (
        update(Reminder)
        .where(expression.column("reminder_id") == reminder_id)
        .values(
            reminder_time=reminder_time_converted,
            frequency=frequency,
            status=status,
            message=message,
            sync_state=sync_state,
        )
        .execution_options(synchronize_session="fetch")
    )

    await db.execute(stmt)
    await db.commit()
