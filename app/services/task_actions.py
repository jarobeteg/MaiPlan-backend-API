from typing import Literal
from uuid import UUID

from core.models import Subtask, Task
from core.task_contract import (
    SubtaskCompletion,
    TaskChecklist,
    TaskCompletion,
    apply_subtask_status,
    apply_task_status,
    task_date_from_epoch_day,
)
from pydantic import Field, StrictBool, StrictInt, ValidationError, model_validator
from schemas.tide_schema import (
    SubtaskPayload,
    TaskPayload,
    TideAcknowledgement,
    TideConflict,
    TideModel,
)
from sqlalchemy import select


class TaskRecord(TideModel):
    sync_id: UUID
    base_version: StrictInt | None = Field(default=None, ge=1)
    deleted: StrictBool
    data: TaskPayload


class StepRecord(TideModel):
    sync_id: UUID
    base_version: StrictInt | None = Field(default=None, ge=1)
    deleted: StrictBool
    data: SubtaskPayload


class TaskAction(TideModel):
    format_version: StrictInt
    action: Literal['CREATE_TASK', 'EDIT_TASK', 'SET_TASK_STATUS', 'SET_SUBTASK_STATUS',
                    'ADD_SUBTASK', 'EDIT_SUBTASK', 'REORDER_SUBTASKS', 'EDIT_CHECKLIST', 'DELETE_SUBTASK', 'DELETE_TASK']
    arguments: dict = Field(default_factory=dict)
    task: TaskRecord
    subtask_changes: list[StepRecord] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_links(self):
        if self.format_version != 1:
            raise ValueError('Unsupported Task action format')
        ids = [step.sync_id for step in self.subtask_changes]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate Subtask identity')
        if any(step.data.parent_task_sync_id != self.task.sync_id for step in self.subtask_changes):
            raise ValueError('Every step must belong to the action Task')
        allowed = {'SET_TASK_STATUS': {'status', 'action_date'},
                   'SET_SUBTASK_STATUS': {'status', 'action_date', 'subtask_sync_id'},
                   'DELETE_SUBTASK': {'action_date'},
                   'EDIT_CHECKLIST': {'action_date', 'edited_step_ids'}}.get(self.action, set())
        if set(self.arguments) != allowed:
            raise ValueError('Unexpected or missing action arguments')
        if 'status' in allowed:
            value = self.arguments['status']
            if type(value) is not int or value not in range(5):
                raise ValueError('Invalid action status')
        if 'action_date' in allowed:
            value = self.arguments['action_date']
            if type(value) is not int:
                raise ValueError('Action date must be an epoch day')
            task_date_from_epoch_day(value)
        if 'subtask_sync_id' in allowed:
            UUID(self.arguments['subtask_sync_id'])
        if 'edited_step_ids' in allowed:
            edited = self.arguments['edited_step_ids']
            if type(edited) is not list or any(type(value) is not str or str(UUID(value)) != value for value in edited) or len(set(edited)) != len(edited):
                raise ValueError('Edited step IDs must be unique canonical UUIDs')
        return self


async def evaluate_task_action(db, user_id, device_id, mutation):
    from services import tide_service as tide
    try:
        action = TaskAction.model_validate(mutation.data)
    except (ValidationError, ValueError, TypeError) as error:
        raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Invalid Task action') from error
    if action.task.sync_id != mutation.entity_sync_id or action.task.base_version != mutation.base_version:
        raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Task action identity/version mismatch')
    expected_operation = {'CREATE_TASK': tide.CREATE, 'DELETE_TASK': tide.DELETE}.get(action.action, tide.UPDATE)
    if mutation.operation != expected_operation or action.task.deleted != (action.action == 'DELETE_TASK'):
        raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Task action lifecycle mismatch')
    task = await tide._load_entity(db, user_id, 'task', mutation.entity_sync_id, for_update=True)
    if action.task.data.series_id is not None and action.action == 'CREATE_TASK':
        raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Series occurrences must use MATERIALIZE')
    if task is None and action.task.data.series_id is not None:
        raise tide.MutationRejected('TASK_SERIES_CHANGED', 'Occurrence is unavailable; retain local work for review')
    if task is not None and task.series_id is not None:
        series = await tide._load_entity(db, user_id, 'task_series', UUID(task.series_id), for_update=True)
        if series is None or series.deleted_at is not None or (series.pending_operation and not series.pending_operation.get('done')):
            raise tide.MutationRejected('TASK_SERIES_CHANGED', 'Retain local work for review; series is unavailable or being edited')
        if action.task.data.series_id != task.series_id or action.task.data.slot_date != tide._date_to_epoch_days(task.slot_date):
            raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Occurrence membership and original slot are immutable')
        if action.task.data.generation_revision != task.generation_revision:
            raise tide.MutationRejected('TASK_SERIES_CHANGED', 'Occurrence template changed; retain local work for review')
    steps = [] if task is None else list((await db.scalars(
        select(Subtask).where(Subtask.user_id == user_id, Subtask.task_id == task.task_id)
        .order_by(Subtask.sync_id).with_for_update()
    )).all())
    by_id = {step.sync_id: step for step in steps}
    now = tide._utc_now()

    async def snapshot(kind, entity):
        return {
            'entity_type': kind,
            'entity_sync_id': str(entity.sync_id),
            'operation': tide.DELETE if entity.deleted_at else tide.UPDATE,
            'server_version': entity.version,
            'data': None if entity.deleted_at else await tide._serialize_entity(db, kind, entity),
        }

    async def conflict():
        assert task is not None
        return TideConflict(mutation_id=mutation.mutation_id, entity_type='task_action',
            entity_sync_id=task.sync_id, server_version=task.version,
            server_data={'task': await snapshot('task', task),
                         'subtasks': [await snapshot('subtask', step) for step in steps]})

    changed = []
    async def emit(kind, entity, operation=tide.UPDATE):
        data = None if operation == tide.DELETE else await tide._serialize_entity(db, kind, entity)
        tide._append_change(db, user_id, device_id, mutation.mutation_id, kind,
                            entity.sync_id, operation, entity.version, data)
        changed.append({
            'entity_type': kind,
            'entity_sync_id': str(entity.sync_id),
            'operation': operation,
            'server_version': entity.version,
            'data': data,
        })

    async def write(kind, entity, deleted=False):
        entity.version += 1
        entity.updated_at = now
        if deleted:
            entity.deleted_at = now
        await db.flush()
        await emit(kind, entity, tide.DELETE if deleted else tide.UPDATE)

    if task is None:
        if action.action not in {'CREATE_TASK', 'DELETE_TASK'} or mutation.base_version is not None:
            raise tide.MutationRejected(tide.ENTITY_NOT_FOUND, 'The Task does not exist')
        payload = action.task.data
        if action.action == 'DELETE_TASK':
            payload = payload.model_copy(update={'category_sync_id': None, 'reminder_sync_id': None})
        elif payload.status != 0 or any(step.deleted or step.base_version is not None or step.data.status != 0 for step in action.subtask_changes):
            raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'New Tasks and steps must start To-do')
        task = Task(user_id=user_id, sync_id=mutation.entity_sync_id, version=1,
                    created_at=now, updated_at=now, deleted_at=now if action.action == 'DELETE_TASK' else None)
        await tide._apply_payload(db, user_id, 'task', task, payload)
        db.add(task)
        await db.flush()
        await emit('task', task, tide.DELETE if task.deleted_at else tide.CREATE)
        if not task.deleted_at:
            for item in action.subtask_changes:
                if await tide._load_entity(db, user_id, 'subtask', item.sync_id) is not None:
                    raise tide.MutationRejected(tide.ENTITY_ALREADY_EXISTS, 'Step UUID already exists')
                step = Subtask(user_id=user_id, task_id=task.task_id, sync_id=item.sync_id, version=1,
                               created_at=now, updated_at=now, deleted_at=None)
                await tide._apply_payload(db, user_id, 'subtask', step, item.data)
                db.add(step)
                await db.flush()
                await emit('subtask', step, tide.CREATE)
    else:
        if action.action == 'CREATE_TASK' or task.deleted_at is not None:
            return await conflict()
        if action.action != 'EDIT_SUBTASK' and mutation.base_version != task.version:
            return await conflict()
        active = [step for step in steps if step.deleted_at is None]
        if action.action in {'ADD_SUBTASK', 'EDIT_SUBTASK', 'REORDER_SUBTASKS', 'EDIT_CHECKLIST', 'DELETE_SUBTASK'} and task.status in (1, 3, 4):
            return await conflict()
        if action.action == 'EDIT_TASK':
            if action.subtask_changes:
                raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Content edit must not replace steps')
            data = await tide._serialize_entity(db, 'task', task)
            content = action.task.data.model_dump()
            content.update(status=data['status'], completed_date=data['completed_date'])
            if task.series_id is not None:
                for field in ('series_id', 'slot_date', 'occurrence_number', 'generation_revision', 'repeat_unit', 'repeat_interval', 'repeat_weekdays', 'repeat_anchor_date', 'repeat_end_date'):
                    content[field] = data[field]
                content['occurrence_override'] = True
            await tide._apply_payload(db, user_id, 'task', task, TaskPayload.model_validate(content))
            await write('task', task)
        elif action.action in {'SET_TASK_STATUS', 'SET_SUBTASK_STATUS'}:
            state = TaskChecklist(TaskCompletion(task.status, task.completed_date), tuple(
                SubtaskCompletion(step.sync_id, TaskCompletion(step.status, step.completed_date)) for step in active))
            today = task_date_from_epoch_day(action.arguments['action_date'])
            if today is None:
                raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Task status actions require an action date')
            try:
                desired = (apply_task_status(state, action.arguments['status'], today) if action.action == 'SET_TASK_STATUS'
                           else apply_subtask_status(state, UUID(action.arguments['subtask_sync_id']), action.arguments['status'], today))
            except ValueError:
                return await conflict()
            values = {step.sync_id: step.completion for step in desired.subtasks}
            for step in active:
                value = values[step.sync_id]
                if (step.status, step.completed_date) != (value.status, value.completed_date):
                    step.status, step.completed_date = int(value.status), value.completed_date
                    await write('subtask', step)
            if desired != state:
                task.status, task.completed_date = int(desired.completion.status), desired.completion.completed_date
                await write('task', task)
        elif action.action == 'DELETE_TASK':
            if task.series_id is not None:
                from services.task_series_actions import record_exclusion
                changed.append(await record_exclusion(db, user_id, device_id, mutation, UUID(task.series_id), task.slot_date))
            for step in active:
                await write('subtask', step, deleted=True)
            await write('task', task, deleted=True)
        elif action.action == 'EDIT_CHECKLIST':
            records = {item.sync_id: item for item in action.subtask_changes}
            if not {step.sync_id for step in active}.issubset(records):
                return await conflict()
            retained = [item for item in action.subtask_changes if not item.deleted]
            edited = {UUID(value) for value in action.arguments['edited_step_ids']}
            if not edited.issubset({item.sync_id for item in retained if item.sync_id in by_id}):
                raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Edited IDs must identify retained existing steps')
            if sorted(item.data.sort_order for item in retained) != list(range(len(retained))):
                raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Invalid checklist order')
            for item in action.subtask_changes:
                step = by_id.get(item.sync_id)
                if step is not None:
                    if step.deleted_at is not None or item.base_version != step.version:
                        return await conflict()
                else:
                    if item.base_version is not None or item.deleted or item.data.status != 0:
                        raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'New steps must start To-do')
                    if await tide._load_entity(db, user_id, 'subtask', item.sync_id) is not None:
                        raise tide.MutationRejected(tide.ENTITY_ALREADY_EXISTS, 'Step UUID already exists')
            removed = False
            for item in action.subtask_changes:
                step = by_id.get(item.sync_id)
                if step is None:
                    step = Subtask(user_id=user_id, task_id=task.task_id, sync_id=item.sync_id, version=1,
                                   created_at=now, updated_at=now, deleted_at=None)
                    await tide._apply_payload(db, user_id, 'subtask', step, item.data)
                    db.add(step)
                    await db.flush()
                    steps.append(step)
                    await emit('subtask', step, tide.CREATE)
                elif item.deleted:
                    removed = True
                    await write('subtask', step, deleted=True)
                else:
                    before = (step.title, step.estimated_time, step.sort_order)
                    if item.sync_id in edited:
                        step.title = item.data.title
                        step.estimated_time = tide._milliseconds_to_timedelta(item.data.estimated_time)
                    step.sort_order = item.data.sort_order
                    if before != (step.title, step.estimated_time, step.sort_order):
                        await write('subtask', step)
            remaining = [step for step in steps if step.deleted_at is None]
            if removed and remaining and all(step.status in (1, 3, 4) for step in remaining):
                task.status = 1
                task.completed_date = task_date_from_epoch_day(action.arguments['action_date'])
            await write('task', task)
        else:
            if action.action in {'EDIT_SUBTASK', 'DELETE_SUBTASK'} and len(action.subtask_changes) != 1:
                raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Action needs one target step')
            targets = []
            for item in action.subtask_changes:
                step = by_id.get(item.sync_id)
                if step is not None and (step.deleted_at is not None or item.base_version != step.version):
                    return await conflict()
                if step is None and (action.action != 'ADD_SUBTASK' or item.base_version is not None or item.deleted or item.data.status != 0):
                    raise tide.MutationRejected(tide.ENTITY_NOT_FOUND, 'Step does not exist')
                targets.append((item, step))
            if action.action == 'ADD_SUBTASK' and sum(step is None for _, step in targets) != 1:
                raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Add must create one step')
            if action.action == 'REORDER_SUBTASKS':
                if {item.sync_id for item, _ in targets} != {step.sync_id for step in active}:
                    return await conflict()
                if sorted(item.data.sort_order for item, _ in targets) != list(range(len(active))):
                    raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Invalid checklist order')
            for item, step in targets:
                if step is None:
                    if await tide._load_entity(db, user_id, 'subtask', item.sync_id) is not None:
                        raise tide.MutationRejected(tide.ENTITY_ALREADY_EXISTS, 'Step UUID already exists')
                    step = Subtask(user_id=user_id, task_id=task.task_id, sync_id=item.sync_id, version=1,
                                   created_at=now, updated_at=now, deleted_at=None)
                    await tide._apply_payload(db, user_id, 'subtask', step, item.data)
                    db.add(step)
                    await db.flush()
                    await emit('subtask', step, tide.CREATE)
                elif action.action == 'DELETE_SUBTASK':
                    if not item.deleted:
                        raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Delete must tombstone its step')
                    await write('subtask', step, deleted=True)
                else:
                    if item.deleted:
                        raise tide.MutationRejected(tide.MALFORMED_MUTATION, 'Unexpected step tombstone')
                    if action.action == 'EDIT_SUBTASK':
                        step.title = item.data.title
                        step.estimated_time = tide._milliseconds_to_timedelta(item.data.estimated_time)
                    else:
                        step.sort_order = item.data.sort_order
                    await write('subtask', step)
            if action.action != 'EDIT_SUBTASK':
                remaining = [step for step in steps if step.deleted_at is None]
                if action.action == 'DELETE_SUBTASK' and remaining and all(step.status in (1, 3, 4) for step in remaining):
                    task.status = 1
                    task.completed_date = task_date_from_epoch_day(action.arguments['action_date'])
                await write('task', task)
    return TideAcknowledgement(mutation_id=mutation.mutation_id, entity_type='task_action',
        entity_sync_id=task.sync_id, server_version=task.version, effects=changed)
