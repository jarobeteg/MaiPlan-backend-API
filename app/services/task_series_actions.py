from itertools import islice
from typing import Any, Literal
from uuid import UUID, uuid5

from core.models import Event, Note, Reminder, Subtask, Task, TaskExclusion, TaskSeries
from core.task_contract import task_date_from_epoch_day, task_date_to_epoch_day
from core.task_series_contract import (
    PAGE_SIZE,
    SeriesDefinition,
    StrictModel,
    exclusion_id,
    occurrence_id,
    step_id,
)
from pydantic import Field, StrictInt, ValidationError
from schemas.tide_schema import (
    TaskPayload,
    TideAcknowledgement,
    TideActionSnapshot,
    TideConflict,
    TideMutation,
)
from sqlalchemy import exists, select


class SeriesAction(StrictModel):
    format_version: Literal[1]
    action: Literal['CREATE_SERIES', 'EDIT_FUTURE', 'MATERIALIZE', 'RECONCILE', 'DELETE_ALL']
    definition: dict | None = None
    expected_revision: StrictInt | None = Field(default=None, ge=1)
    from_date: StrictInt | None = None
    through_date: StrictInt | None = None
    cutoff: StrictInt | None = None
    requested_on: StrictInt | None = None
    operation_id: UUID | None = None


def active_operation(series) -> dict[str, Any] | None:
    operation = series.pending_operation
    return operation if operation and not operation.get('done') else None


def occurrence_payload(series, slot, revision, number) -> TaskPayload:
    return TaskPayload(title=revision.title, description=revision.description, status=0,
        scheduled_date=task_date_to_epoch_day(slot), estimated_time=revision.estimated_time,
        category_sync_id=revision.category_sync_id, series_id=str(series.sync_id),
        occurrence_number=number, slot_date=task_date_to_epoch_day(slot),
        generation_revision=revision.revision, repeat_unit=revision.repeat_unit,
        repeat_interval=revision.repeat_interval, repeat_weekdays=revision.repeat_weekdays,
        repeat_anchor_date=revision.repeat_anchor_date, repeat_end_date=revision.repeat_end_date,
        relative_reminder=revision.reminder.model_dump(mode='json') if revision.reminder else None)


async def release_absolute_reminder(db, user, device, mutation, reminder_id, now):
    from services import tide_service as tide
    if reminder_id is None:
        return
    reminder = await db.scalar(select(Reminder).where(Reminder.reminder_id == reminder_id,
        Reminder.user_id == user).with_for_update())
    if reminder is None or reminder.deleted_at is not None:
        return
    for model in (Task, Event, Note):
        if await db.scalar(select(exists().where(model.reminder_id == reminder_id, model.deleted_at.is_(None)))):
            return
    reminder.deleted_at = now
    reminder.updated_at = now
    reminder.version += 1
    await db.flush()
    tide._append_change(db, user, device, mutation.mutation_id, 'reminder', reminder.sync_id,
        tide.DELETE, reminder.version, None)


async def record_exclusion(db, user, device, mutation, series_id, slot) -> TideActionSnapshot:
    from services import tide_service as tide
    identity = exclusion_id(series_id, slot)
    row = await tide._load_entity(db, user, 'task_exclusion', identity, for_update=True)
    if row is None:
        now = tide._utc_now()
        row = TaskExclusion(user_id=user, sync_id=identity, series_id=str(series_id), slot_date=slot,
            version=1, created_at=now, updated_at=now, deleted_at=None)
        db.add(row)
        await db.flush()
        tide._append_change(db, user, device, mutation.mutation_id, 'task_exclusion', identity,
            tide.CREATE, 1, await tide._serialize_entity(db, 'task_exclusion', row))
    return TideActionSnapshot(entity_type='task_exclusion', entity_sync_id=identity,
        operation=tide.CREATE, server_version=row.version,
        data=await tide._serialize_entity(db, 'task_exclusion', row))


async def evaluate_series_action(db, user, device, mutation) -> TideAcknowledgement | TideConflict:
    from services import tide_service as tide
    try:
        action = SeriesAction.model_validate(mutation.data)
        desired = SeriesDefinition.model_validate(action.definition) if action.definition is not None else None
        start, through = task_date_from_epoch_day(action.from_date), task_date_from_epoch_day(action.through_date)
        cutoff = task_date_from_epoch_day(action.cutoff)
        requested_on = task_date_from_epoch_day(action.requested_on)
        if action.action == 'CREATE_SERIES' and (desired is None or len(desired.revisions) != 1 or mutation.operation != tide.CREATE):
            raise ValueError('CREATE_SERIES requires one initial revision')
        if action.action == 'EDIT_FUTURE' and (desired is None or cutoff is None or requested_on is None or cutoff <= requested_on or action.operation_id is None):
            raise ValueError('Future edits require a cutoff after the local request day, definition, and operation identity')
        if action.action == 'MATERIALIZE' and (start is None or through is None or start > through or action.expected_revision is None):
            raise ValueError('Materialization requires an inclusive window and expected definition revision')
        if action.action in {'RECONCILE', 'DELETE_ALL'} and action.operation_id is None:
            raise ValueError('Bulk actions require an operation identity')
        if action.action != 'CREATE_SERIES' and mutation.operation != tide.UPDATE:
            raise ValueError('Series lifecycle actions use UPDATE')
    except (ValidationError, ValueError, TypeError) as error:
        raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Invalid series action') from error
    series = await tide._load_entity(db, user, 'task_series', mutation.entity_sync_id, for_update=True)
    effects: list[TideActionSnapshot] = []
    now = tide._utc_now()

    async def emit(kind, row, operation, changed=True):
        data = None if operation == tide.DELETE else await tide._serialize_entity(db, kind, row)
        if changed:
            tide._append_change(db, user, device, mutation.mutation_id, kind, row.sync_id, operation, row.version, data)
        effects.append(TideActionSnapshot(entity_type=kind, entity_sync_id=row.sync_id,
            operation=operation, server_version=row.version, data=data))

    async def conflict(current_series: TaskSeries) -> TideConflict:
        return TideConflict(mutation_id=mutation.mutation_id, entity_type=mutation.entity_type,
            entity_sync_id=mutation.entity_sync_id, server_version=current_series.version,
            server_data={'series': {
                'entity_type': 'task_series',
                'entity_sync_id': str(current_series.sync_id),
                'operation': tide.DELETE if current_series.deleted_at else tide.UPDATE,
                'server_version': current_series.version,
                'data': None if current_series.deleted_at else await tide._serialize_entity(db, 'task_series', current_series),
            }})

    if action.action == 'CREATE_SERIES':
        if series is not None:
            return await conflict(series)
        if mutation.base_version is not None:
            raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'CREATE has no base version')
        assert desired is not None  # CREATE_SERIES validation requires a definition.
        for revision in desired.revisions:
            await tide._resolve_relationship(db, user, tide.Category, 'category_id', revision.category_sync_id, 'category')
        series = TaskSeries(user_id=user, sync_id=mutation.entity_sync_id, definition=desired.model_dump(mode='json'),
            pending_operation=None, version=1, created_at=now, updated_at=now, deleted_at=None)
        db.add(series)
        await db.flush()
        await emit('task_series', series, tide.CREATE)
    else:
        if series is None:
            raise tide.MutationRejected(tide.MUTATION_DEPENDENCY_PENDING, 'Series definition must be accepted first')
        definition = SeriesDefinition.model_validate(series.definition)
        if action.action == 'MATERIALIZE':
            assert start is not None and through is not None  # Validated inclusive window.
            if series.deleted_at or active_operation(series) or action.expected_revision != definition.revisions[-1].revision:
                return await conflict(series)
            slots = list(islice(definition.slots(start, through), PAGE_SIZE+1))
            if len(slots) > PAGE_SIZE:
                raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Materialization window exceeds 32 slots; page it')
            for slot, revision, number in slots:
                excluded = await tide._load_entity(db, user, 'task_exclusion', exclusion_id(series.sync_id, slot), for_update=True)
                if excluded is not None:
                    await emit('task_exclusion', excluded, tide.CREATE, False)
                    continue
                identity = occurrence_id(series.sync_id, slot)
                task = await tide._load_entity(db, user, 'task', identity, for_update=True)
                if task is None:
                    task = Task(user_id=user, sync_id=identity, version=1, created_at=now, updated_at=now, deleted_at=None)
                    await tide._apply_payload(db, user, 'task', task, occurrence_payload(series, slot, revision, number))
                    db.add(task)
                    await db.flush()
                    await emit('task', task, tide.CREATE)
                    for order, template in enumerate(revision.steps):
                        step = Subtask(user_id=user, task_id=task.task_id, sync_id=step_id(identity, template.key),
                            title=template.title, estimated_time=tide._milliseconds_to_timedelta(template.estimated_time),
                            status=0, completed_date=None, sort_order=order, version=1,
                            created_at=now, updated_at=now, deleted_at=None)
                        db.add(step)
                        await db.flush()
                        await emit('subtask', step, tide.CREATE)
                else:
                    if task.series_id != str(series.sync_id) or task.slot_date != slot:
                        raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Occurrence UUID is already occupied')
                    await emit('task', task, tide.DELETE if task.deleted_at else tide.UPDATE, False)
                    steps = (await db.scalars(select(Subtask).where(Subtask.user_id == user, Subtask.task_id == task.task_id))).all()
                    for step in steps:
                        await emit('subtask', step, tide.DELETE if step.deleted_at else tide.UPDATE, False)
        elif action.action == 'EDIT_FUTURE':
            assert desired is not None  # EDIT_FUTURE validation requires a definition.
            if series.deleted_at or active_operation(series) or mutation.base_version != series.version:
                return await conflict(series)
            if desired.revisions[:-1] != definition.revisions or desired.revisions[-1].effective_from != action.cutoff:
                raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Future edits append a revision without rewriting history')
            revision = desired.revisions[-1]
            await tide._resolve_relationship(db, user, tide.Category, 'category_id', revision.category_sync_id, 'category')
            series.definition = desired.model_dump(mode='json')
            series.pending_operation = {
                'id': str(action.operation_id), 'kind': 'EDIT',
                'cutoff': action.cutoff, 'action_date': action.requested_on, 'after': 0,
            }
        elif action.action == 'DELETE_ALL':
            if active_operation(series) or mutation.base_version != series.version or series.deleted_at:
                return await conflict(series)
            series.deleted_at = now
            series.pending_operation = {'id': str(action.operation_id), 'kind': 'DELETE', 'after': 0}
        elif action.action == 'RECONCILE':
            if not series.pending_operation or series.pending_operation['id'] != str(action.operation_id) or series.pending_operation.get('done'):
                await emit('task_series', series, tide.DELETE if series.deleted_at else tide.UPDATE, False)
                return TideAcknowledgement(mutation_id=mutation.mutation_id, entity_type=mutation.entity_type,
                    entity_sync_id=mutation.entity_sync_id, server_version=series.version, effects=effects)

        if action.action != 'MATERIALIZE':
            definition = SeriesDefinition.model_validate(series.definition)
            pending_operation = series.pending_operation
            assert pending_operation is not None  # Bulk branches establish or resume an operation.
            operation: dict[str, Any] = pending_operation.copy()
            conditions = [Task.user_id == user, Task.series_id == str(series.sync_id), Task.task_id > operation['after']]
            if operation['kind'] == 'EDIT':
                conditions.append(Task.scheduled_date >= task_date_from_epoch_day(operation['cutoff']))
            tasks = list((await db.scalars(select(Task).where(*conditions).order_by(Task.task_id).limit(PAGE_SIZE+1).with_for_update())).all())
            for task in tasks[:PAGE_SIZE]:
                operation['after'] = task.task_id
                if task.deleted_at:
                    continue
                old_reminder_id = task.reminder_id
                revision = definition.revision_for(task.scheduled_date or task.slot_date)
                matching = list(definition.slots(task.slot_date, task.slot_date))
                delete = operation['kind'] == 'DELETE' or (not matching and task.slot_date >= task_date_from_epoch_day(operation['cutoff']))
                steps = list((await db.scalars(select(Subtask).where(Subtask.user_id == user, Subtask.task_id == task.task_id).with_for_update())).all())
                if delete:
                    effects.append(await record_exclusion(db, user, device, mutation, series.sync_id, task.slot_date))
                    for step in steps:
                        if step.deleted_at is None:
                            step.deleted_at = now
                            step.updated_at = now
                            step.version += 1
                            await emit('subtask', step, tide.DELETE)
                    task.deleted_at = now
                else:
                    assert revision is not None  # An editable occurrence belongs to a definition revision.
                    number = matching[0][2] if matching else task.occurrence_number
                    payload = occurrence_payload(series, task.slot_date, revision, number)
                    payload.status = task.status
                    payload.completed_date = task_date_to_epoch_day(task.completed_date)
                    payload.scheduled_date = task_date_to_epoch_day(task.scheduled_date)
                    await tide._apply_payload(db, user, 'task', task, payload)
                    desired_steps = {step_id(task.sync_id, item.key): (order, item) for order, item in enumerate(revision.steps)}
                    for step in steps:
                        if step.deleted_at is not None:
                            continue
                        item = desired_steps.pop(step.sync_id, None)
                        if item is None:
                            step.deleted_at = now
                        else:
                            step.sort_order, template = item
                            step.title = template.title
                            step.estimated_time = tide._milliseconds_to_timedelta(template.estimated_time)
                        step.version += 1
                        step.updated_at = now
                        await emit('subtask', step, tide.DELETE if step.deleted_at else tide.UPDATE)
                    for identity, (order, template) in desired_steps.items():
                        if any(step.sync_id == identity for step in steps):
                            continue
                        terminal = task.status in {1, 3, 4}
                        step = Subtask(user_id=user, task_id=task.task_id, sync_id=identity, title=template.title,
                            estimated_time=tide._milliseconds_to_timedelta(template.estimated_time),
                            status=task.status if terminal else 0, completed_date=task.completed_date if task.status == 1 else None,
                            sort_order=order, version=1, created_at=now, updated_at=now, deleted_at=None)
                        db.add(step)
                        await db.flush()
                        await emit('subtask', step, tide.CREATE)
                        steps.append(step)
                    remaining = [step for step in steps if step.deleted_at is None]
                    if task.status not in {1, 3, 4} and remaining and all(step.status in {1, 3, 4} for step in remaining):
                        task.status = 1
                        task.completed_date = task_date_from_epoch_day(operation['action_date'])
                task.version += 1
                task.updated_at = now
                await db.flush()
                await emit('task', task, tide.DELETE if task.deleted_at else tide.UPDATE)
                await release_absolute_reminder(db, user, device, mutation, old_reminder_id, now)
            series.pending_operation = operation if len(tasks) > PAGE_SIZE else {**operation, 'done': True}
            series.version += 1
            series.updated_at = now
            await db.flush()
            await emit('task_series', series, tide.DELETE if series.deleted_at else tide.UPDATE)
    return TideAcknowledgement(mutation_id=mutation.mutation_id, entity_type=mutation.entity_type,
        entity_sync_id=mutation.entity_sync_id, server_version=series.version, effects=effects,
        continuation=active_operation(series))


async def resume_one_series_page(db, user, device) -> bool:
    from services import tide_service as tide
    series = await db.scalar(select(TaskSeries).where(TaskSeries.user_id == user,
        TaskSeries.pending_operation['id'].as_string().is_not(None),
        TaskSeries.pending_operation['done'].as_boolean().is_not(True))
        .order_by(TaskSeries.task_series_id).limit(1).with_for_update())
    if series is None:
        return False
    operation = active_operation(series)
    if operation is None:
        return False
    identity = uuid5(series.sync_id, f"operation:{operation['id']}:{operation['after']}")
    mutation = TideMutation(mutation_id=identity, entity_type='task_series_action', entity_sync_id=series.sync_id,
        operation='UPDATE', base_version=series.version,
        data={'format_version': 1, 'action': 'RECONCILE', 'operation_id': operation['id']})
    outcome = await evaluate_series_action(db, user, device, mutation)
    db.add(tide._ledger_from_outcome(user, device, mutation, outcome))
    await db.flush()
    return active_operation(series) is not None
