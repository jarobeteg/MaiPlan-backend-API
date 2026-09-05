from schemas.sync_schema import SyncRequest, SyncResponse
from schemas.task_schema import TaskSync
from sqlalchemy.ext.asyncio import AsyncSession


async def task_sync_service(db: AsyncSession, request: SyncRequest[TaskSync]) -> SyncResponse[TaskSync]:
    acknowledged: list[TaskSync] = []
    rejected: list[TaskSync] = []

    change = request.changes[0] if request.changes else None

    if not change:
        pass

    return SyncResponse(user_id=request.user_id, acknowledged=acknowledged, rejected=rejected)