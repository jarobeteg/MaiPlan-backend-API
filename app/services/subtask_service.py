from schemas.subtask_schema import SubtaskSync
from schemas.sync_schema import SyncRequest, SyncResponse
from sqlalchemy.ext.asyncio import AsyncSession


async def subtask_sync_service(db: AsyncSession, request: SyncRequest[SubtaskSync]) -> SyncResponse[SubtaskSync]:
    acknowledged: list[SubtaskSync] = []
    rejected: list[SubtaskSync] = []

    change = request.changes[0] if request.changes else None

    if not change:
        pass

    return SyncResponse(user_id=request.user_id, acknowledged=acknowledged, rejected=rejected)