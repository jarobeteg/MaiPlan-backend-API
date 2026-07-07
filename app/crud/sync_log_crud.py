from sqlalchemy.exc import SQLAlchemyError
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
    try:
        sync_log = SyncLog(
            user_id=user_id,
            entity_type=entity_type.value,
            entity_id=entity_id,
            old_data=old_data,
            new_data=new_data,
            action=action.value,
            result=result.value,
            exception_type=exception_type,
            exception_message=exception_message,
        )

        db.add(sync_log)
        await db.commit()

    except SQLAlchemyError as e:
        await db.rollback()
        print("Failed to create sync log:", type(e).__name__, str(e))
        return None