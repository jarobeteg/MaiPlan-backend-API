from typing import Annotated

from core.database import get_db
from fastapi import APIRouter, Depends
from schemas.subtask_schema import SubtaskSync
from schemas.sync_schema import SyncRequest, SyncResponse
from services.subtask_service import subtask_sync_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/sync", response_model=SyncResponse[SubtaskSync])
async def subtask_sync(
    request: SyncRequest[SubtaskSync], 
    db: Annotated[AsyncSession, Depends(get_db)]
) -> SyncResponse[SubtaskSync]:
    return await subtask_sync_service(
        request=request,
        db=db
    )