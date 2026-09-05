from typing import Annotated

from core.database import get_db
from fastapi import APIRouter, Depends
from schemas.sync_schema import SyncRequest, SyncResponse
from schemas.task_schema import TaskSync
from services.task_service import task_sync_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/sync", response_model=SyncResponse[TaskSync])
async def task_sync(
    request: SyncRequest[TaskSync], 
    db: Annotated[AsyncSession, Depends(get_db)]
) -> SyncResponse[TaskSync]:
    return await task_sync_service(
        request=request,
        db=db
    )