from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import Event
from schemas.sync_schema import SyncRequest, SyncResponse
from schemas.event_schema import EventCreate, EventResponse, EventSync
from crud.event_crud import add_event, get_event, get_events, get_pending_events, set_event, set_event_sync_state, \
    make_event, remove_event
from typing import List
from datetime import datetime, time

router = APIRouter()

@router.post("/create-event")
async def create_event(event: EventCreate, db: AsyncSession = Depends(get_db)):
    await add_event(db, event)

@router.get("/get-event-by-id", response_model=EventResponse)
async def get_event_by_id(event_id: int, db: AsyncSession = Depends(get_db)):
    return await get_event(db, event_id)

@router.get("/get-all-event", response_model=List[EventResponse])
async def get_all_event(user_id: int, db: AsyncSession = Depends(get_db)):
    return await get_events(db, user_id)

@router.post("/sync", response_model=SyncResponse[EventSync])
async def sync_event(request: SyncRequest[EventSync], db: AsyncSession = Depends(get_db)):
    acknowledged = []
    rejected = []

    change = request.changes[0] if len(request.changes) > 0 else None

    if not change:
        pending_events: List[Event] = await get_pending_events(db, request.user_id)
        for pending_event in pending_events:
            await set_event_sync_state(db, pending_event.event_id, 0)
            await db.refresh(pending_event)
            acknowledged.append(to_reminder_sync(pending_event))

        return SyncResponse(user_id=request.user_id, acknowledged=acknowledged, rejected=rejected)

    for event in request.changes:
        if event.server_id == 0:
            if event.is_deleted == 0:
                new_event = await make_event(db, event)
                acknowledged.append(new_event)
            else:
                rejected.append(event)
        else:
            if event.is_deleted == 0:
                existing_event = await get_event(db, event.server_id)
                await set_event(db, event.server_id, event.category_id, event.reminder_id, event.title,
                                event.description, event.date, event.start_time, event.end_time, event.priority, event.location, 0)
                await db.refresh(existing_event)
                existing_event_data = EventSync(
                    event_id=event.event_id,
                    server_id=existing_event.server_id,
                    user_id=existing_event.user_id,
                    category_id=existing_event.category_id,
                    reminder_id= 0 if existing_event.reminder_id is None else existing_event.reminder_id,
                    title=existing_event.title,
                    description=existing_event.description,
                    date=int(datetime.combine(existing_event.date, time.min).timestamp() * 1000),
                    start_time=int(datetime.combine(existing_event.date, existing_event.start_time).timestamp() * 1000),
                    end_time=int(datetime.combine(existing_event.date, existing_event.end_time).timestamp() * 1000),
                    priority=existing_event.priority,
                    location=existing_event.location,
                    created_at=int(existing_event.created_at.timestamp() * 1000),
                    updated_at=int(existing_event.updated_at.timestamp() * 1000),
                    last_modified=int(existing_event.last_modified.timestamp() * 1000),
                    sync_state=existing_event.sync_state,
                    is_deleted=existing_event.is_deleted
                )
                acknowledged.append(existing_event_data)
            else:
                await remove_event(db, event.server_id)
                rejected.append(event)

    return SyncResponse(user_id=request.user_id, acknowledged=acknowledged, rejected=rejected)

def to_reminder_sync(event: Event) -> EventSync:
    return EventSync(
        event_id=event.event_id,
        server_id=event.server_id,
        user_id=event.user_id,
        category_id=event.category_id,
        reminder_id=0 if event.reminder_id is None else event.reminder_id,
        title=event.title,
        description=event.description,
        date=int(datetime.combine(event.date, time.min).timestamp() * 1000),
        start_time=int(datetime.combine(event.date, event.start_time).timestamp() * 1000),
        end_time=int(datetime.combine(event.date, event.start_time).timestamp() * 1000),
        priority=event.priority,
        location=event.location,
        created_at=int(event.created_at.timestamp() * 1000),
        updated_at=int(event.updated_at.timestamp() * 1000),
        last_modified=int(event.last_modified.timestamp() * 1000),
        sync_state=event.sync_state,
        is_deleted=event.is_deleted
    )