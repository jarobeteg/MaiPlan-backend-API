from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..schemas import EventCreate, EventResponse
from ..crud.event_crud import add_event, get_event, get_events
from typing import List

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
