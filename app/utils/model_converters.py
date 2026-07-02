from core.models import Note
from schemas.note_schema import NoteSync
from utils.date_time_converters import datetime_to_ms, ms_to_datetime

def to_note_sync(note: Note) -> NoteSync:
    return NoteSync(
        note_id=note.note_id,
        server_id=note.server_id or note.note_id,
        user_id=note.user_id,
        category_id=note.category_id or 0,
        reminder_id=note.reminder_id or 0,
        title=note.title,
        content=note.content or "",
        created_at=datetime_to_ms(note.created_at),
        updated_at=datetime_to_ms(note.updated_at),
        last_modified=datetime_to_ms(note.last_modified),
        sync_state=note.sync_state,
        is_deleted=note.is_deleted,
        is_pinned=note.is_pinned
    )

def to_note(note_sync: NoteSync) -> Note:
    return Note(
        server_id=note_sync.server_id,
        user_id=note_sync.user_id,
        category_id=None if note_sync.category_id == 0 else note_sync.category_id,
        reminder_id=None if note_sync.reminder_id == 0 else note_sync.reminder_id,
        title=note_sync.title,
        content=note_sync.content,
        created_at=ms_to_datetime(note_sync.created_at),
        updated_at=ms_to_datetime(note_sync.updated_at),
        last_modified=ms_to_datetime(note_sync.last_modified),
        sync_state=note_sync.sync_state,
        is_deleted=note_sync.is_deleted,
        is_pinned=note_sync.is_pinned
    )
