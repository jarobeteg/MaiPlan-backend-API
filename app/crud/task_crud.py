from core.enums import SyncResult, SyncValue
from core.models import Task
from schemas.task_schema import TaskSync
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from utils.date_time_converters import (
    epoch_days_to_date,
    ms_to_timedelta,
)
from utils.db_utils import DBOperationContext


async def create_task(db: AsyncSession, task: Task) -> tuple[Task | None, DBOperationContext]:
    try:
        db.add(task)
        await db.flush()
        task.server_id = task.task_id
        task.sync_state = 0 
        await db.commit()
        await db.refresh(task)

        return task, DBOperationContext(success=True)

    except SQLAlchemyError as e:
        await db.rollback()

        return None, DBOperationContext(
            success=False,
            exception_type=type(e).__name__,
            exception_message=str(e)
        )

async def get_task(db: AsyncSession, task_id: int) -> tuple[Task | None, DBOperationContext]:
    try:
        stmt = select(Task).where(Task.task_id == task_id)

        result = await db.execute(stmt)
        task = result.scalars().first()

        return task, DBOperationContext(success=True)

    except SQLAlchemyError as e:
        await db.rollback()

        return None, DBOperationContext(
            success=False,
            exception_type=type(e).__name__,
            exception_message=str(e)
        )

async def get_tasks(db: AsyncSession, user_id: int) -> tuple[list[Task], DBOperationContext]:
    try:
        stmt = select(Task).where(Task.user_id == user_id)

        result = await db.execute(stmt)
        tasks = list(result.scalars().all())

        return tasks, DBOperationContext(success=True)

    except SQLAlchemyError as e:
        await db.rollback()

        return [], DBOperationContext(
            success=False,
            exception_type=type(e).__name__,
            exception_message=str(e)
        )

async def get_pending_tasks(db: AsyncSession, user_id: int) -> tuple[list[Task], DBOperationContext]:
    try:
        stmt = select(Task).where(
            Task.user_id == user_id, 
            Task.sync_state != SyncValue.SYNCED
        )

        result = await db.execute(stmt)
        tasks = list(result.scalars().all())

        return tasks, DBOperationContext(success=True)

    except SQLAlchemyError as e:
        await db.rollback()

        return [], DBOperationContext(
            success=False,
            exception_type=type(e).__name__,
            exception_message=str(e)
        )

async def update_task(db: AsyncSession, task_id: int, task_data: TaskSync) -> tuple[Task | None, DBOperationContext]:
    try:
        task, _context = await get_task(db, task_id)

        if task is None:
            return None, DBOperationContext(
                success=False,
                exception_type=SyncResult.NOT_FOUND,
                exception_message=f"Task with id {task_id} not found."
            )

        task.category_id = None if task_data.category_id == 0 else task_data.category_id
        task.reminder_id = None if task_data.reminder_id == 0 else task_data.reminder_id
        task.title = task_data.title
        task.description = task_data.description
        task.status = task_data.status
        task.scheduled_date = None if task_data.scheduled_date == 0 else epoch_days_to_date(task_data.scheduled_date)
        task.estimated_time = None if task_data.estimated_time == 0 else ms_to_timedelta(task_data.estimated_time)
        task.completed_date = None if task_data.completed_date == 0 else epoch_days_to_date(task_data.completed_date)
        task.series_id = task_data.series_id
        task.occurrence_number = task_data.occurrence_number
        task.repeat_unit = task_data.repeat_unit
        task.repeat_interval = task_data.repeat_interval
        task.repeat_weekdays = task_data.repeat_weekdays
        task.repeat_end_date = None if task_data.repeat_end_date == 0 else epoch_days_to_date(task_data.repeat_end_date)
        task.repeat_anchor_date = None if task_data.repeat_anchor_date == 0 else epoch_days_to_date(task_data.repeat_anchor_date)
        task.sync_state = SyncValue.SYNCED
        task.is_deleted = task_data.is_deleted

        await db.commit()
        await db.refresh(task)

        return task, DBOperationContext(success=True)

    except SQLAlchemyError as e:
        await db.rollback()

        return None, DBOperationContext(
            success=False,
            exception_type=type(e).__name__,
            exception_message=str(e)
        )

async def delete_task(db: AsyncSession, task_id: int) -> DBOperationContext:
    try:
        task, _context = await get_task(db, task_id)

        if task is None:
            return DBOperationContext(
                success=False,
                exception_type=SyncResult.NOT_FOUND,
                exception_message=f"Task with id {task_id} not found."
            )

        await db.delete(task)
        await db.commit()

        return DBOperationContext(success=True)

    except SQLAlchemyError as e:
        await db.rollback()

        return DBOperationContext(
            success=False,
            exception_type=type(e).__name__,
            exception_message=str(e)
        )

async def set_task_sync_state(db: AsyncSession, task_id: int, sync_state: int) -> DBOperationContext:
    try:
        stmt = (
            update(Task)
            .where(Task.task_id == task_id)
            .values(sync_state=sync_state)
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