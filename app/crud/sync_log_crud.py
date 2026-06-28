from sqlalchemy.ext.asyncio import AsyncSession
from core.enums import EntityType, SyncAction, SyncResult
from core.models import SyncLog

async def create_sync_log(
        db: AsyncSession,
        user_id: int,
        entity_type: EntityType,
        entity_id: int | None,
        old_data: dict | None,
        new_data: dict | None,
        action: SyncAction,
        result: SyncResult,
        exception_type: str | None,
        exception_message: str | None,
) -> None:
    log = SyncLog(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        old_data=old_data,
        new_data=new_data,
        action=action,
        result=result,
        exception_type=exception_type,
        exception_message=exception_message,
    )

    db.add(log)
    await db.commit()