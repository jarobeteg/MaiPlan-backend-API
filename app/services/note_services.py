from sqlalchemy.ext.asyncio import AsyncSession
from core.enums import EntityType, SyncResult, SyncAction
from core.models import Note
from crud.note_crud import get_pending_notes, set_note_sync_state, create_note, get_note, delete_note, update_note
from crud.sync_log_crud import create_sync_log
from schemas.note_schema import NoteSync
from schemas.sync_schema import SyncRequest, SyncResponse
from utils.model_converters import to_note_sync, to_note

def note_snapshot(note: Note) -> dict:
    return to_note_sync(note).model_dump()

async def note_sync_service(db: AsyncSession, request: SyncRequest[NoteSync]) -> SyncResponse[NoteSync]:
    acknowledged: list[NoteSync] = []
    rejected: list[NoteSync] = []

    change = request.changes[0] if request.changes else None

    if not change:
        await log_note_sync(
            db=db,
            user_id=request.user_id,
            action=SyncAction.SYNC_UPLOAD,
            result=SyncResult.NO_CHANGES,
        )

        acknowledged = await process_pending_download_notes(db=db, user_id=request.user_id)

        return SyncResponse(user_id=request.user_id, acknowledged=acknowledged, rejected=rejected)

    for note_sync in request.notes:
        try:
            # note was created locally and needs to be created on the server
            if note_sync.server_id == 0 and note_sync.is_deleted == 0:
                new_note = to_note(note_sync)

                created_note, context = await create_note(db=db, note=new_note)

                if not context.success or created_note is None:
                    rejected.append(note_sync)

                    await log_note_sync(
                        db=db,
                        user_id=request.user_id,
                        entity_id=None,
                        old_data=None,
                        new_data=note_sync.model_dump(),
                        action=SyncAction.SYNC_UPLOAD,
                        result=SyncResult.FAILED,
                        exception_type=context.exception_type,
                        exception_message=context.exception_message,
                    )

                    continue

                acknowledged_note = to_note_sync(created_note)
                acknowledged.append(acknowledged_note)

                await log_note_sync(
                    db=db,
                    user_id=request.user_id,
                    entity_id=created_note.note_id,
                    old_data=None,
                    new_data=note_snapshot(created_note),
                    action=SyncAction.SYNC_UPLOAD,
                    result=SyncResult.SUCCESS,
                )

            # note was created locally but deleted before reaching server
            elif note_sync.server_id == 0 and note_sync.is_deleted == 1:
                rejected.append(note_sync)

                await log_note_sync(
                    db=db,
                    user_id=request.user_id,
                    entity_id=None,
                    old_data=note_sync.model_dump(),
                    new_data=None,
                    action=SyncAction.SYNC_UPLOAD,
                    result=SyncResult.NO_CHANGES,
                    exception_type="LocalOnlyDeletedNote",
                    exception_message="Note was created locally and deleted before it was synced to the server."
                )

            # note exists on the sever and was updated locally
            elif note_sync.server_id != 0 and note_sync.is_deleted == 0:
                existing_note, context = await get_note(
                    db=db,
                    note_id=note_sync.server_id,
                )

                if context.success or existing_note is None:
                    rejected.append(note_sync)

                    await log_note_sync(
                        db=db,
                        user_id=request.user_id,
                        entity_id=note_sync.server_id,
                        old_data=None,
                        new_data=note_sync.model_dump(),
                        action=SyncAction.SYNC_UPLOAD,
                        result=SyncResult.FAILED,
                        exception_type=context.exception_type,
                        exception_message=context.exception_message or "Note DB record not found.",
                    )

                    continue

                old_data = note_snapshot(existing_note)

                updated_note, context = await update_note(
                    db=db,
                    note_id=note_sync.server_id,
                    note_data=note_sync,
                )

                if not context.success or updated_note is None:
                    rejected.append(note_sync)

                    await log_note_sync(
                        db=db,
                        user_id=request.user_id,
                        entity_id=note_sync.server_id,
                        old_data=old_data,
                        new_data=note_sync.model_dump(),
                        action=SyncAction.SYNC_UPLOAD,
                        result=SyncResult.FAILED,
                        exception_type=context.exception_type,
                        exception_message=context.exception_message,
                    )

                    continue

                new_data = note_snapshot(updated_note)

                acknowledged_note = to_note_sync(updated_note)
                acknowledged.append(acknowledged_note)

                await log_note_sync(
                    db=db,
                    user_id=request.user_id,
                    entity_id=updated_note.note_id,
                    old_data=old_data,
                    new_data=new_data,
                    action=SyncAction.SYNC_UPLOAD,
                    result=SyncResult.SUCCESS,
                )

            # note exists on the sever and was deleted locally
            elif note_sync.server_id != 0 and note_sync.is_deleted == 1:
                existing_note, context = await get_note(
                    db=db,
                    note_id=note_sync.server_id,
                )

                if not context.success or existing_note is None:
                    rejected.append(note_sync)

                    await log_note_sync(
                        db=db,
                        user_id=request.user_id,
                        entity_id=note_sync.server_id,
                        old_data=None,
                        new_data=note_sync.model_dump(),
                        action=SyncAction.SYNC_UPLOAD,
                        result=SyncResult.FAILED,
                        exception_type=context.exception_type,
                        exception_message=context.exception_message or "Note DB record not found.",
                    )

                    continue

                old_data = note_snapshot(existing_note)

                delete_context = await delete_note(
                    db=db,
                    note_id=note_sync.server_id,
                )

                if not delete_context.success:
                    rejected.append(note_sync)

                    await log_note_sync(
                        db=db,
                        user_id=request.user_id,
                        entity_id=note_sync.server_id,
                        old_data=old_data,
                        new_data=None,
                        action=SyncAction.SYNC_UPLOAD,
                        result=SyncResult.FAILED,
                        exception_type=delete_context.exception_type,
                        exception_message=delete_context.exception_message,
                    )

                    continue

                # acknowledge the delete if it succeeded
                acknowledged.append(note_sync)

                await log_note_sync(
                    db=db,
                    user_id=request.user_id,
                    entity_id=note_sync.server_id,
                    old_data=old_data,
                    new_data=None,
                    action=SyncAction.SYNC_UPLOAD,
                    result=SyncResult.SUCCESS,
                )

        except Exception as e:
            rejected.append(note_sync)

            await log_note_sync(
                db=db,
                user_id=request.user_id,
                entity_id=note_sync.server_id if note_sync.server_id != 0 else None,
                old_data=note_sync.model_dump(),
                new_data=None,
                action=SyncAction.SYNC_UPLOAD,
                result=SyncResult.FAILED,
                exception_type=type(e).__name__,
                exception_message=str(e),
            )

    pending_download_notes = await process_pending_download_notes(
        db=db,
        user_id=request.user_id,
    )

    acknowledged.extend(pending_download_notes)

    return SyncResponse(user_id=request.user_id, acknowledged=acknowledged, rejected=rejected)

async def process_pending_download_notes(
    db: AsyncSession,
    user_id: int
) -> list[NoteSync]:

    acknowledged: list[NoteSync] = []

    pending_notes, context = await get_pending_notes(db, user_id)

    if not context.success:
        await log_note_sync(
            db=db,
            user_id=user_id,
            action=SyncAction.SYNC_DOWNLOAD,
            result=SyncResult.NO_CHANGES,
        )
        return acknowledged

    for pending_note in pending_notes:
        old_data = note_snapshot(pending_note)

        sync_state_result = await set_note_sync_state(
            db=db,
            note_id=pending_note.note_id,
            sync_state=0,
        )

        if not sync_state_result.success:
            continue

        await db.refresh(pending_note)

        new_data = note_snapshot(pending_note)

        note_sync = to_note_sync(pending_note)
        acknowledged.append(note_sync)

        await log_note_sync(
            db=db,
            user_id=user_id,
            entity_id=pending_note.note_id,
            old_data=old_data,
            new_data=new_data,
            action=SyncAction.SYNC_DOWNLOAD,
            result=SyncResult.SUCCESS,
        )

    return acknowledged

async def log_note_sync(
    db: AsyncSession,
    user_id: int,
    action: SyncAction,
    result: SyncResult,
    entity_id: int | None = None,
    old_data: dict | None = None,
    new_data: dict | None = None,
    exception_type: str | None = None,
    exception_message: str | None = None,
):
    await create_sync_log(
        db=db,
        user_id=user_id,
        entity_type=EntityType.NOTE,
        entity_id=entity_id,
        old_data=old_data,
        new_data=new_data,
        action=action,
        result=result,
        exception_type=exception_type,
        exception_message=exception_message,
    )