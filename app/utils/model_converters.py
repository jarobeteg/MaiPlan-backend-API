from core.models import Note, Subtask, Task
from schemas.note_schema import NoteSync
from schemas.subtask_schema import SubtaskSync
from schemas.task_schema import TaskSync
from utils.date_time_converters import (
    date_to_epoch_days,
    datetime_to_ms,
    epoch_days_to_date,
    ms_to_datetime,
    ms_to_timedelta,
    timedelta_to_ms,
)


def to_note_sync(note: Note) -> NoteSync:
    return NoteSync(
        note_id=note.note_id,
        server_id=note.server_id or 0,
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

def to_task_sync(task: Task) -> TaskSync:
    return TaskSync(
        task_id=task.task_id,
        server_id=task.server_id or 0,
        user_id=task.user_id,        
        category_id=task.category_id or 0,
        reminder_id=task.reminder_id or 0,
        title=task.title,
        description=task.description or "",
        status=task.status,
        scheduled_date=date_to_epoch_days(task.scheduled_date) if task.scheduled_date else 0,
        estimated_time=timedelta_to_ms(task.estimated_time) if task.estimated_time else 0,
        completed_date=date_to_epoch_days(task.completed_date) if task.completed_date else 0,
        series_id=task.series_id or "",
        occurrence_number=task.occurrence_number or 0,
        repeat_unit=task.repeat_unit or 0,
        repeat_interval=task.repeat_interval or 0,
        repeat_weekdays=task.repeat_weekdays or 0,
        repeat_end_date=date_to_epoch_days(task.repeat_end_date) if task.repeat_end_date else 0,
        repeat_anchor_date=date_to_epoch_days(task.repeat_anchor_date) if task.repeat_anchor_date else 0,
        created_at=datetime_to_ms(task.created_at),
        updated_at=datetime_to_ms(task.updated_at),
        last_modified=datetime_to_ms(task.last_modified),
        sync_state=task.sync_state,
        is_deleted=task.is_deleted
    )

def to_task(task_sync: TaskSync) -> Task:
    return Task(
        server_id=task_sync.server_id,
        user_id=task_sync.user_id,
        category_id=None if task_sync.category_id == 0 else task_sync.category_id,
        reminder_id=None if task_sync.reminder_id == 0 else task_sync.reminder_id,
        title=task_sync.title,
        description=task_sync.description,
        status=task_sync.status,
        scheduled_date=None if task_sync.scheduled_date == 0 else epoch_days_to_date(task_sync.scheduled_date),
        estimated_time=None if task_sync.estimated_time == 0 else ms_to_timedelta(task_sync.estimated_time),
        completed_date=None if task_sync.completed_date == 0 else epoch_days_to_date(task_sync.completed_date),
        series_id=task_sync.series_id or "",
        occurrence_number=task_sync.occurrence_number or 0,
        repeat_unit=task_sync.repeat_unit or 0,
        repeat_interval=task_sync.repeat_interval or 0,
        repeat_weekdays=task_sync.repeat_weekdays or 0,
        repeat_end_date=None if task_sync.repeat_end_date == 0 else epoch_days_to_date(task_sync.repeat_end_date),
        repeat_anchor_date=None if task_sync.repeat_anchor_date == 0 else epoch_days_to_date(task_sync.repeat_anchor_date),
        created_at=ms_to_datetime(task_sync.created_at),
        updated_at=ms_to_datetime(task_sync.updated_at),
        last_modified=ms_to_datetime(task_sync.last_modified),
        sync_state=task_sync.sync_state,
        is_deleted=task_sync.is_deleted
    )

def to_subtask_sync(subtask: Subtask) -> SubtaskSync:
    return SubtaskSync(
        subtask_id=subtask.subtask_id,
        server_id=subtask.server_id or 0,
        task_id=subtask.task_id,
        title=subtask.title,
        status=subtask.status,
        sort_order=subtask.sort_order,
        estimated_time=timedelta_to_ms(subtask.estimated_time) if subtask.estimated_time else 0,
        completed_date=date_to_epoch_days(subtask.completed_date) if subtask.completed_date else 0,
        created_at=datetime_to_ms(subtask.created_at),
        updated_at=datetime_to_ms(subtask.updated_at),
        last_modified=datetime_to_ms(subtask.last_modified),
        sync_state=subtask.sync_state,
        is_deleted=subtask.is_deleted
    )

def to_subtask(subtask_sync: SubtaskSync) -> Subtask:
    return Subtask(
        server_id=subtask_sync.server_id,
        task_id=subtask_sync.task_id,
        title=subtask_sync.title,
        status=subtask_sync.status,
        sort_order=subtask_sync.sort_order,
        estimated_time=None if subtask_sync.estimated_time == 0 else ms_to_timedelta(subtask_sync.estimated_time),
        completed_date=None if subtask_sync.completed_date == 0 else epoch_days_to_date(subtask_sync.completed_date),
        created_at=ms_to_datetime(subtask_sync.created_at),
        updated_at=ms_to_datetime(subtask_sync.updated_at),
        last_modified=ms_to_datetime(subtask_sync.last_modified),
        sync_state=subtask_sync.sync_state,
        is_deleted=subtask_sync.is_deleted
    )