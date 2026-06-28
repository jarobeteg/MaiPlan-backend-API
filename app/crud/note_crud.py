from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from core.enums import SyncResult
from core.models import Note
from schemas.note_schema import NoteSync
from utils.db_utils import DBOperationContext

async def create_note(db: AsyncSession, note: Note) -> tuple[Note | None, DBOperationContext]:
    try:
        db.add(note)
        await db.commit()
        await db.refresh(note)

        return note, DBOperationContext(success=True)

    except SQLAlchemyError as e:
        await db.rollback()

        return None, DBOperationContext(
            success=False,
            exception_type=type(e).__name__,
            exception_message=str(e)
        )

async def get_note(db: AsyncSession, note_id: int) -> tuple[Note | None, DBOperationContext]:
    try:
        stmt = select(Note).where(Note.note_id == note_id)

        result = await db.execute(stmt)
        note = result.scalars().first()

        return note, DBOperationContext(success=True)

    except SQLAlchemyError as e:
        await db.rollback()

        return None, DBOperationContext(
            success=False,
            exception_type=type(e).__name__,
            exception_message=str(e)
        )

async def get_notes(db: AsyncSession, user_id: int) -> tuple[list[Note], DBOperationContext]:
    try:
        stmt = select(Note).where(Note.user_id == user_id)

        result = await db.execute(stmt)
        notes = list(result.scalars().all())

        return notes, DBOperationContext(success=True)

    except SQLAlchemyError as e:
        await db.rollback()

        return [], DBOperationContext(
            success=False,
            exception_type=type(e).__name__,
            exception_message=str(e)
        )

async def get_pending_notes(db: AsyncSession, user_id: int) -> tuple[list[Note], DBOperationContext]:
    try:
        stmt = select(Note).where(
            Note.user_id == user_id,
            Note.sync_state != 0,
        )

        result = await db.execute(stmt)
        notes = list(result.scalars().all())

        return notes, DBOperationContext(success=True)

    except SQLAlchemyError as e:
        await db.rollback()

        return [], DBOperationContext(
            success=False,
            exception_type=type(e).__name__,
            exception_message=str(e)
        )

async def update_note(db: AsyncSession, note_id: int, note_data: NoteSync) -> tuple[Note | None, DBOperationContext]:
    try:
        note, context = await get_note(db, note_id)

        if note is None:
            return None, DBOperationContext(
                success=False,
                exception_type=SyncResult.NOT_FOUND,
                exception_message="Note DB record not found"
            )

        note.title = note_data.title
        note.content = note_data.content
        note.category_id = note_data.category_id
        note.reminder_id = note_data.reminder_id
        note.is_deleted = note_data.is_deleted
        note.sync_state = 0

        await db.commit()
        await db.refresh(note)

        return note, DBOperationContext(success=True)

    except SQLAlchemyError as e:
        await db.rollback()

        return None, DBOperationContext(
            success=False,
            exception_type=type(e).__name__,
            exception_message=str(e)
        )

async def delete_note(db: AsyncSession, note_id: int) -> DBOperationContext:
    try:
        note, context = await get_note(db, note_id)

        if note is None:
            return DBOperationContext(
                success=False,
                exception_type=SyncResult.NOT_FOUND,
                exception_message="Note DB record not found"
            )

        await db.delete(note)
        await db.commit()

        return DBOperationContext(success=True)

    except SQLAlchemyError as e:
        await db.rollback()

        return DBOperationContext(
            success=False,
            exception_type=type(e).__name__,
            exception_message=str(e)
        )

async def set_note_sync_state(db: AsyncSession, note_id: int, sync_state: int) -> DBOperationContext:
    try:
        stmt = (
            update(Note)
            .where(Note.note_id == note_id)
            .values(sync_state=sync_state)
            .execution_options(synchronize_session="fetch")
        )

        await db.execute(stmt)
        await db.commit()

        return DBOperationContext(success=True)

    except SQLAlchemyError as e:
        await db.rollback()

        return DBOperationContext(
            success=False,
            exception_type=type(e).__name__,
            exception_message=str(e)
        )
