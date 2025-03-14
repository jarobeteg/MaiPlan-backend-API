from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import EventCreate, EventResponse
from event_crud import new_event, get_event

router = APIRouter()

@router.post("/create-event")
async def create_event(event: EventCreate, db: AsyncSession = Depends(get_db)):
    await new_event(db, event)

@router.get("/get-event-by-id", response_model=EventResponse)
async def get_event_by_id(event_id: int, db: AsyncSession = Depends(get_db)):
    return await get_event(db, event_id)
