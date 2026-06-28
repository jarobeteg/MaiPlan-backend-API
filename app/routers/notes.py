from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from schemas.note_schema import NoteSync
from schemas.sync_schema import SyncRequest, SyncResponse
from services.note_services import note_sync_service

router = APIRouter()

@router.post("/sync", response_model=SyncResponse[NoteSync])
async def note_sync(request: SyncRequest[NoteSync], db: AsyncSession = Depends(get_db)) -> SyncResponse[NoteSync]:
    return await note_sync_service(
        request=request,
        db=db
    )