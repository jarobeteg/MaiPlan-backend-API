from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import Reminder
from schemas.reminder_schema import ReminderCreate, ReminderResponse, ReminderSync
from schemas.sync_schema import SyncRequest, SyncResponse
from crud.reminder_crud import add_reminder, get_reminder, get_reminders, get_pending_reminders, \
    set_reminder_sync_state, make_reminder, remove_reminder, set_reminder
from typing import List

from schemas.sync_schema import SyncRequest

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

@router.post("/sync", response_model=SyncResponse[ReminderSync])
async def reminder_sync(request: SyncRequest[ReminderSync], db: AsyncSession = Depends(get_db)):
    acknowledged = []
    rejected = []

    change = request.changes[0] if len(request.changes) > 0 else None

    if not change:
        pending_reminders: List[Reminder] = await get_pending_reminders(db, request.user_id)
        for pending_reminder in pending_reminders:
            await set_reminder_sync_state(db, pending_reminder.reminder_id, 0)
            await db.refresh(pending_reminder)
            acknowledged.append(to_reminder_sync(pending_reminder))

        return SyncResponse(user_id=request.user_id, acknowledged=acknowledged, rejected=rejected)

    for reminder in request.changes:
        if reminder.server_id == 0:
            if reminder.is_deleted == 0:
                new_reminder = await make_reminder(db, reminder)
                acknowledged.append(new_reminder)
            else:
                rejected.append(reminder)
        else:
            if reminder.is_deleted == 0:
                existing_reminder = await get_reminder(db, reminder.server_id)
                await set_reminder(db, reminder.server_id, reminder.reminder_time, reminder.frequency, reminder.status, reminder.message, 0)
                await db.refresh(existing_reminder)
                existing_reminder_data = ReminderSync(
                    reminder_id=reminder.id,
                    server_id=existing_reminder.server_id,
                    user_id=existing_reminder.user_id,
                    reminder_time=int(existing_reminder.time.timestamp() * 1000),
                    frequency=existing_reminder.frequency,
                    status=existing_reminder.status,
                    message=existing_reminder.message,
                    created_at=int(existing_reminder.created_at.timestamp() * 1000),
                    updated_at=int(existing_reminder.updated_at.timestamp() * 1000),
                    last_modified=int(existing_reminder.last_modified.timestamp() * 1000),
                    sync_state=existing_reminder.sync_state,
                    is_deleted=existing_reminder.is_deleted
                )
                acknowledged.append(existing_reminder_data)
            else:
                await remove_reminder(db, reminder.server_id)
                rejected.append(reminder)

    return SyncResponse(user_id=request.user_id, acknowledged=acknowledged, rejected=rejected)

def to_reminder_sync(reminder: Reminder) -> ReminderSync:
    return ReminderSync(
        reminder_id=reminder.id,
        server_id=reminder.server_id,
        user_id=reminder.user_id,
        reminder_time=int(reminder.time.timestamp() * 1000),
        frequency=reminder.frequency,
        status=reminder.status,
        message=reminder.message,
        created_at=int(reminder.created_at.timestamp() * 1000),
        updated_at=int(reminder.updated_at.timestamp() * 1000),
        last_modified=int(reminder.last_modified.timestamp() * 1000),
        sync_state=reminder.sync_state,
        is_deleted=reminder.is_deleted
    )