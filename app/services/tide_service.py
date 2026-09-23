from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from typing import Any, Literal, cast
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from core.models import (
    Category,
    Event,
    Note,
    ProcessedMutation,
    Reminder,
    Subtask,
    SyncChangeLog,
    SyncLog,
    Task,
    User,
)
from core.settings import TIDE_MAX_REQUEST_BYTES
from fastapi import HTTPException
from pydantic import ValidationError
from schemas.tide_schema import (
    ENTITY_PAYLOAD_MODELS,
    MAX_DATA_LIMIT,
    MUTABLE_ENTITY_TYPES,
    SUPPORTED_CHANGE_ENTITY_TYPES,
    TIDE_PROTOCOL_VERSION,
    CategoryPayload,
    EventPayload,
    NotePayload,
    ReminderPayload,
    SubtaskPayload,
    TaskPayload,
    TideAcknowledgement,
    TideChange,
    TideConflict,
    TideMutation,
    TideRejection,
    TideSyncRequest,
    TideSyncResponse,
    UserPayload,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

ACKNOWLEDGED = "ACKNOWLEDGED"
REJECTED = "REJECTED"
CONFLICT = "CONFLICT"

CREATE = "CREATE"
UPDATE = "UPDATE"
DELETE = "DELETE"
OPERATIONS = {CREATE, UPDATE, DELETE}
MAX_REQUEST_BYTES = TIDE_MAX_REQUEST_BYTES

MALFORMED_MUTATION = "MALFORMED_MUTATION"
UNKNOWN_ENTITY_TYPE = "UNKNOWN_ENTITY_TYPE"
ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
ENTITY_ALREADY_EXISTS = "ENTITY_ALREADY_EXISTS"
RELATIONSHIP_NOT_FOUND = "RELATIONSHIP_NOT_FOUND"
RELATIONSHIP_OWNERSHIP_MISMATCH = "RELATIONSHIP_OWNERSHIP_MISMATCH"
VERSION_CONFLICT = "VERSION_CONFLICT"
MUTATION_DEPENDENCY_PENDING = "MUTATION_DEPENDENCY_PENDING"


@dataclass(frozen=True)
class EntityConfig:
    model: type
    id_attribute: str


ENTITY_CONFIGS: dict[str, EntityConfig] = {
    "user": EntityConfig(User, "user_id"),
    "category": EntityConfig(Category, "category_id"),
    "reminder": EntityConfig(Reminder, "reminder_id"),
    "event": EntityConfig(Event, "event_id"),
    "note": EntityConfig(Note, "note_id"),
    "task": EntityConfig(Task, "task_id"),
    "subtask": EntityConfig(Subtask, "subtask_id"),
}


class MutationRejected(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


TideOutcome = TideAcknowledgement | TideRejection | TideConflict


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_instant(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _milliseconds_to_datetime(value: int) -> datetime:
    try:
        return datetime.fromtimestamp(value / 1000, timezone.utc)
    except (OverflowError, OSError, ValueError) as exception:
        raise MutationRejected(MALFORMED_MUTATION, "Timestamp is outside the supported range") from exception


def _datetime_to_milliseconds(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)


def _zone_info(zone_id: str) -> tzinfo:
    if zone_id == "UTC":
        return timezone.utc
    try:
        return ZoneInfo(zone_id)
    except ZoneInfoNotFoundError as exception:
        raise MutationRejected(
            MALFORMED_MUTATION,
            "zone_id is not available in the IANA time-zone database",
        ) from exception


def _milliseconds_to_date(value: int, zone_id: str) -> date:
    return _milliseconds_to_datetime(value).astimezone(_zone_info(zone_id)).date()


def _date_to_milliseconds(value: date, zone_id: str) -> int:
    return int(datetime.combine(value, time.min, _zone_info(zone_id)).timestamp() * 1000)


def _milliseconds_to_time(value: int | None, zone_id: str) -> time | None:
    if value is None:
        return None
    return _milliseconds_to_datetime(value).astimezone(_zone_info(zone_id)).time().replace(tzinfo=None)


def _time_to_milliseconds(day: date, value: time | None, zone_id: str) -> int | None:
    if value is None:
        return None
    return int(datetime.combine(day, value, _zone_info(zone_id)).timestamp() * 1000)


def _epoch_days_to_date(value: int | None) -> date | None:
    if value is None:
        return None
    try:
        return date(1970, 1, 1) + timedelta(days=value)
    except OverflowError as exception:
        raise MutationRejected(MALFORMED_MUTATION, "Date is outside the supported range") from exception


def _date_to_epoch_days(value: date | None) -> int | None:
    if value is None:
        return None
    return (value - date(1970, 1, 1)).days


def _milliseconds_to_timedelta(value: int | None) -> timedelta | None:
    if value is None:
        return None
    return timedelta(milliseconds=value)


def _timedelta_to_milliseconds(value: timedelta | None) -> int | None:
    if value is None:
        return None
    return int(value.total_seconds() * 1000)


def _parse_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        parsed = int(cursor)
    except (TypeError, ValueError) as exception:
        raise _http_error(400, "CURSOR_INVALID", "The sync cursor is invalid") from exception
    if parsed < 0:
        raise _http_error(400, "CURSOR_INVALID", "The sync cursor is invalid")
    return parsed


def _validate_request(request: TideSyncRequest) -> None:
    if request.tide_protocol_version != TIDE_PROTOCOL_VERSION:
        raise _http_error(
            400,
            "UNSUPPORTED_PROTOCOL_VERSION",
            f"TIDE protocol version {request.tide_protocol_version} is not supported",
        )
    mutation_ids = [mutation.mutation_id for mutation in request.mutations]
    if len(mutation_ids) != len(set(mutation_ids)):
        raise _http_error(400, MALFORMED_MUTATION, "Mutation IDs must be unique within a request")
    encoded_size = len(
        json.dumps(request.model_dump(mode="json"), separators=(",", ":")).encode("utf-8")
    )
    if encoded_size > MAX_REQUEST_BYTES:
        raise _http_error(413, "PAYLOAD_TOO_LARGE", "The TIDE request payload is too large")


def _mutation_request_hash(mutation: TideMutation) -> str:
    canonical_request = json.dumps(
        mutation.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical_request).hexdigest()


async def _validate_cursor(db: AsyncSession, user_id: int, cursor: int) -> None:
    if cursor == 0:
        return
    maximum = await db.scalar(select(func.max(SyncChangeLog.sequence)))
    if cursor > (maximum or 0):
        raise _http_error(400, "CURSOR_INVALID", "The sync cursor is ahead of the change feed")
    cursor_owner = await db.scalar(
        select(SyncChangeLog.user_id).where(SyncChangeLog.sequence == cursor)
    )
    if cursor_owner != user_id:
        raise _http_error(
            400,
            "CURSOR_INVALID",
            "The sync cursor does not belong to the authenticated user",
        )


async def _get_processed_mutation(
    db: AsyncSession,
    user_id: int,
    mutation_id: UUID,
) -> ProcessedMutation | None:
    return await db.scalar(
        select(ProcessedMutation).where(
            ProcessedMutation.user_id == user_id,
            ProcessedMutation.mutation_id == mutation_id,
        )
    )


def _outcome_from_ledger(
    ledger: ProcessedMutation,
    device_id: UUID,
    mutation: TideMutation,
) -> TideOutcome:
    if (
        ledger.device_id != device_id
        or ledger.entity_type != mutation.entity_type
        or ledger.entity_sync_id != mutation.entity_sync_id
        or ledger.operation != mutation.operation
        or ledger.request_hash != _mutation_request_hash(mutation)
    ):
        return TideRejection(
            mutation_id=mutation.mutation_id,
            entity_type=mutation.entity_type,
            entity_sync_id=mutation.entity_sync_id,
            error_code=MALFORMED_MUTATION,
            message="The mutation ID was already used for a different mutation",
        )

    identity = {
        "mutation_id": ledger.mutation_id,
        "entity_type": ledger.entity_type,
        "entity_sync_id": ledger.entity_sync_id,
    }
    if ledger.outcome == ACKNOWLEDGED:
        result_version = ledger.result_version
        if result_version is None:
            raise RuntimeError("An acknowledged mutation is missing its result version")
        return TideAcknowledgement(
            **identity,
            server_version=result_version,
        )
    if ledger.outcome == CONFLICT:
        result_version = ledger.result_version
        if result_version is None:
            raise RuntimeError("A conflicting mutation is missing its result version")
        return TideConflict(
            **identity,
            server_version=result_version,
            server_data=ledger.server_data,
        )
    return TideRejection(
        **identity,
        error_code=ledger.error_code or MALFORMED_MUTATION,
        message=ledger.message,
    )


def _ledger_from_outcome(
    user_id: int,
    device_id: UUID,
    mutation: TideMutation,
    outcome: TideOutcome,
) -> ProcessedMutation:
    if isinstance(outcome, TideAcknowledgement):
        result = ACKNOWLEDGED
        result_version = outcome.server_version
        error_code = None
        message = None
        server_data = None
    elif isinstance(outcome, TideConflict):
        result = CONFLICT
        result_version = outcome.server_version
        error_code = VERSION_CONFLICT
        message = "The mutation base version is stale"
        server_data = outcome.server_data
    else:
        result = REJECTED
        result_version = None
        error_code = outcome.error_code
        message = outcome.message
        server_data = None

    return ProcessedMutation(
        user_id=user_id,
        mutation_id=mutation.mutation_id,
        device_id=device_id,
        entity_type=mutation.entity_type,
        entity_sync_id=mutation.entity_sync_id,
        operation=mutation.operation,
        request_hash=_mutation_request_hash(mutation),
        outcome=result,
        result_version=result_version,
        error_code=error_code,
        message=message,
        server_data=server_data,
    )


async def _load_entity(
    db: AsyncSession,
    user_id: int,
    entity_type: str,
    sync_id: UUID,
    *,
    for_update: bool = False,
):
    config = ENTITY_CONFIGS[entity_type]
    model = config.model
    if entity_type == "user":
        statement = select(model).where(model.user_id == user_id, model.sync_id == sync_id)
    else:
        statement = select(model).where(model.user_id == user_id, model.sync_id == sync_id)
    if for_update:
        statement = statement.with_for_update()
    return await db.scalar(statement)


async def _sync_id_for_internal_id(
    db: AsyncSession,
    model: type,
    id_attribute: str,
    internal_id: int | None,
) -> UUID | None:
    if internal_id is None:
        return None
    return await db.scalar(
        select(model.sync_id).where(getattr(model, id_attribute) == internal_id)
    )


async def _resolve_relationship(
    db: AsyncSession,
    user_id: int,
    model: type,
    id_attribute: str,
    sync_id: UUID | None,
    relationship_name: str,
) -> int | None:
    if sync_id is None:
        return None
    related = await db.scalar(
        select(model).where(model.sync_id == sync_id, model.user_id == user_id)
    )
    if related is None:
        belongs_to_another_user = await db.scalar(
            select(model.user_id).where(model.sync_id == sync_id).limit(1)
        )
        if belongs_to_another_user is not None:
            raise MutationRejected(
                RELATIONSHIP_OWNERSHIP_MISMATCH,
                f"Referenced {relationship_name} belongs to another user",
            )
        raise MutationRejected(
            MUTATION_DEPENDENCY_PENDING,
            f"Referenced {relationship_name} has not been synchronized yet",
        )
    if related.deleted_at is not None:
        raise MutationRejected(
            RELATIONSHIP_NOT_FOUND,
            f"Referenced {relationship_name} is deleted",
        )
    return getattr(related, id_attribute)


def _parse_payload(mutation: TideMutation):
    if mutation.operation == DELETE:
        if mutation.data is not None:
            raise MutationRejected(MALFORMED_MUTATION, "DELETE mutations must not include data")
        return None
    if mutation.data is None:
        raise MutationRejected(MALFORMED_MUTATION, "CREATE and UPDATE mutations require data")
    payload_model = ENTITY_PAYLOAD_MODELS[mutation.entity_type]
    try:
        return payload_model.model_validate(mutation.data)
    except ValidationError as exception:
        raise MutationRejected(
            MALFORMED_MUTATION,
            "Mutation data does not match the entity schema",
        ) from exception


async def _apply_payload(
    db: AsyncSession,
    user_id: int,
    entity_type: str,
    entity,
    payload,
) -> None:
    if entity_type == "category":
        assert isinstance(payload, CategoryPayload)
        entity.name = payload.name
        entity.description = payload.description
        entity.color = payload.color
        entity.icon = payload.icon
        return

    if entity_type == "reminder":
        assert isinstance(payload, ReminderPayload)
        _zone_info(payload.zone_id)
        entity.reminder_time = _milliseconds_to_datetime(payload.reminder_time)
        entity.zone_id = payload.zone_id
        entity.frequency = payload.frequency
        entity.status = payload.status
        entity.message = payload.message
        return

    if entity_type in {"event", "note", "task"}:
        entity.category_id = await _resolve_relationship(
            db,
            user_id,
            Category,
            "category_id",
            payload.category_sync_id,
            "category",
        )
        entity.reminder_id = await _resolve_relationship(
            db,
            user_id,
            Reminder,
            "reminder_id",
            payload.reminder_sync_id,
            "reminder",
        )

    if entity_type == "event":
        assert isinstance(payload, EventPayload)
        entity.title = payload.title
        entity.description = payload.description
        entity.date = _milliseconds_to_date(payload.date, payload.zone_id)
        entity.start_time = _milliseconds_to_time(payload.start_time, payload.zone_id)
        entity.end_time = _milliseconds_to_time(payload.end_time, payload.zone_id)
        entity.zone_id = payload.zone_id
        entity.priority = payload.priority
        entity.location = payload.location
        return

    if entity_type == "note":
        assert isinstance(payload, NotePayload)
        entity.title = payload.title
        entity.content = payload.content
        entity.is_pinned = payload.is_pinned
        return

    if entity_type == "task":
        assert isinstance(payload, TaskPayload)
        entity.title = payload.title
        entity.description = payload.description
        entity.status = payload.status
        entity.scheduled_date = _epoch_days_to_date(payload.scheduled_date)
        entity.estimated_time = _milliseconds_to_timedelta(payload.estimated_time)
        entity.completed_date = _epoch_days_to_date(payload.completed_date)
        entity.series_id = payload.series_id
        entity.occurrence_number = payload.occurrence_number
        entity.repeat_unit = payload.repeat_unit
        entity.repeat_interval = payload.repeat_interval
        entity.repeat_weekdays = payload.repeat_weekdays
        entity.repeat_end_date = _epoch_days_to_date(payload.repeat_end_date)
        entity.repeat_anchor_date = _epoch_days_to_date(payload.repeat_anchor_date)
        return

    if entity_type == "subtask":
        assert isinstance(payload, SubtaskPayload)
        entity.task_id = await _resolve_relationship(
            db,
            user_id,
            Task,
            "task_id",
            payload.parent_task_sync_id,
            "parent task",
        )
        entity.title = payload.title
        entity.status = payload.status
        entity.sort_order = payload.sort_order
        entity.estimated_time = _milliseconds_to_timedelta(payload.estimated_time)
        entity.completed_date = _epoch_days_to_date(payload.completed_date)
        return

    if entity_type == "user":
        assert isinstance(payload, UserPayload)
        entity.email = str(payload.email)
        entity.username = payload.username.strip()


async def _serialize_entity(db: AsyncSession, entity_type: str, entity) -> dict[str, Any]:
    common = {
        "created_at": _iso_instant(entity.created_at),
        "updated_at": _iso_instant(entity.updated_at),
    }
    if entity_type == "user":
        return {"email": entity.email, "username": entity.username, **common}
    if entity_type == "category":
        return {
            "name": entity.name,
            "description": entity.description,
            "color": entity.color,
            "icon": entity.icon,
            **common,
        }
    if entity_type == "reminder":
        return {
            "reminder_time": _datetime_to_milliseconds(entity.reminder_time),
            "zone_id": entity.zone_id,
            "frequency": entity.frequency,
            "status": entity.status,
            "message": entity.message,
            **common,
        }

    relationship_data: dict[str, Any] = {}
    if entity_type in {"event", "note", "task"}:
        category_sync_id = await _sync_id_for_internal_id(
            db, Category, "category_id", entity.category_id
        )
        reminder_sync_id = await _sync_id_for_internal_id(
            db, Reminder, "reminder_id", entity.reminder_id
        )
        relationship_data = {
            "category_sync_id": str(category_sync_id) if category_sync_id else None,
            "reminder_sync_id": str(reminder_sync_id) if reminder_sync_id else None,
        }

    if entity_type == "event":
        return {
            **relationship_data,
            "title": entity.title,
            "description": entity.description,
            "date": _date_to_milliseconds(entity.date, entity.zone_id),
            "start_time": _time_to_milliseconds(
                entity.date, entity.start_time, entity.zone_id
            ),
            "end_time": _time_to_milliseconds(entity.date, entity.end_time, entity.zone_id),
            "zone_id": entity.zone_id,
            "priority": entity.priority,
            "location": entity.location,
            **common,
        }
    if entity_type == "note":
        return {
            **relationship_data,
            "title": entity.title,
            "content": entity.content,
            "is_pinned": bool(entity.is_pinned),
            **common,
        }
    if entity_type == "task":
        return {
            **relationship_data,
            "title": entity.title,
            "description": entity.description,
            "status": entity.status,
            "scheduled_date": _date_to_epoch_days(entity.scheduled_date),
            "estimated_time": _timedelta_to_milliseconds(entity.estimated_time),
            "completed_date": _date_to_epoch_days(entity.completed_date),
            "series_id": entity.series_id,
            "occurrence_number": entity.occurrence_number,
            "repeat_unit": entity.repeat_unit,
            "repeat_interval": entity.repeat_interval,
            "repeat_weekdays": entity.repeat_weekdays,
            "repeat_end_date": _date_to_epoch_days(entity.repeat_end_date),
            "repeat_anchor_date": _date_to_epoch_days(entity.repeat_anchor_date),
            **common,
        }
    if entity_type == "subtask":
        parent_sync_id = await _sync_id_for_internal_id(db, Task, "task_id", entity.task_id)
        return {
            "parent_task_sync_id": str(parent_sync_id),
            "title": entity.title,
            "status": entity.status,
            "sort_order": entity.sort_order,
            "estimated_time": _timedelta_to_milliseconds(entity.estimated_time),
            "completed_date": _date_to_epoch_days(entity.completed_date),
            **common,
        }
    raise AssertionError(f"Unsupported entity type: {entity_type}")


async def _create_entity(
    db: AsyncSession,
    user_id: int,
    mutation: TideMutation,
    payload,
):
    if mutation.entity_type == "user":
        raise MutationRejected(MALFORMED_MUTATION, "Users are created through registration")
    existing = await _load_entity(
        db,
        user_id,
        mutation.entity_type,
        mutation.entity_sync_id,
        for_update=True,
    )
    if existing is not None:
        raise MutationRejected(ENTITY_ALREADY_EXISTS, "An entity with this sync ID already exists")
    if mutation.base_version is not None:
        raise MutationRejected(MALFORMED_MUTATION, "CREATE mutations must not have a base version")

    config = ENTITY_CONFIGS[mutation.entity_type]
    entity = config.model(
        user_id=user_id,
        sync_id=mutation.entity_sync_id,
        version=1,
        deleted_at=None,
    )
    await _apply_payload(db, user_id, mutation.entity_type, entity, payload)
    db.add(entity)
    await db.flush()
    await db.refresh(entity, attribute_names=["created_at", "updated_at"])
    return entity


async def _conflict_outcome(
    db: AsyncSession,
    mutation: TideMutation,
    entity,
) -> TideConflict:
    return TideConflict(
        mutation_id=mutation.mutation_id,
        entity_type=mutation.entity_type,
        entity_sync_id=mutation.entity_sync_id,
        server_version=entity.version,
        server_data=await _serialize_entity(db, mutation.entity_type, entity),
    )


def _append_change(
    db: AsyncSession,
    user_id: int,
    device_id: UUID,
    mutation_id: UUID,
    entity_type: str,
    entity_sync_id: UUID,
    operation: str,
    version: int,
    data: dict[str, Any] | None,
) -> None:
    if entity_type not in SUPPORTED_CHANGE_ENTITY_TYPES:
        raise AssertionError(f"Unsupported Android TIDE change type: {entity_type}")
    db.add(
        SyncChangeLog(
            user_id=user_id,
            entity_type=entity_type,
            entity_sync_id=entity_sync_id,
            operation=operation,
            entity_version=version,
            data=data,
            origin_device_id=device_id,
            origin_mutation_id=mutation_id,
        )
    )


async def _detach_deleted_relationships(
    db: AsyncSession,
    user_id: int,
    device_id: UUID,
    mutation: TideMutation,
    deleted_entity,
    now: datetime,
) -> None:
    if mutation.entity_type == "category":
        relationships = (
            (Event, "event", "category_id"),
            (Note, "note", "category_id"),
            (Task, "task", "category_id"),
        )
    elif mutation.entity_type == "reminder":
        relationships = (
            (Event, "event", "reminder_id"),
            (Note, "note", "reminder_id"),
            (Task, "task", "reminder_id"),
        )
    else:
        relationships = ()

    deleted_internal_id = getattr(
        deleted_entity,
        ENTITY_CONFIGS[mutation.entity_type].id_attribute,
    )
    for model, entity_type, relationship_attribute in relationships:
        dependants = list(
            (
                await db.scalars(
                    select(model)
                    .where(
                        model.user_id == user_id,
                        getattr(model, relationship_attribute) == deleted_internal_id,
                        model.deleted_at.is_(None),
                    )
                    .with_for_update()
                )
            ).all()
        )
        for dependant in dependants:
            setattr(dependant, relationship_attribute, None)
            dependant.version += 1
            dependant.updated_at = now
            await db.flush()
            data = await _serialize_entity(db, entity_type, dependant)
            _append_change(
                db,
                user_id,
                device_id,
                mutation.mutation_id,
                entity_type,
                dependant.sync_id,
                UPDATE,
                dependant.version,
                data,
            )

    if mutation.entity_type != "task":
        return
    subtasks = list(
        (
            await db.scalars(
                select(Subtask)
                .where(
                    Subtask.user_id == user_id,
                    Subtask.task_id == deleted_entity.task_id,
                    Subtask.deleted_at.is_(None),
                )
                .with_for_update()
            )
        ).all()
    )
    for subtask in subtasks:
        subtask.version += 1
        subtask.updated_at = now
        subtask.deleted_at = now
        _append_change(
            db,
            user_id,
            device_id,
            mutation.mutation_id,
            "subtask",
            subtask.sync_id,
            DELETE,
            subtask.version,
            None,
        )


async def _evaluate_mutation(
    db: AsyncSession,
    user_id: int,
    device_id: UUID,
    mutation: TideMutation,
) -> TideOutcome:
    if mutation.entity_type not in MUTABLE_ENTITY_TYPES:
        raise MutationRejected(UNKNOWN_ENTITY_TYPE, "The mutation entity type is not supported")
    if mutation.operation not in OPERATIONS:
        raise MutationRejected(MALFORMED_MUTATION, "The mutation operation is not supported")

    payload = _parse_payload(mutation)
    now = _utc_now()

    if mutation.operation == CREATE:
        entity = await _create_entity(db, user_id, mutation, payload)
    else:
        if mutation.base_version is None:
            raise MutationRejected(
                MALFORMED_MUTATION,
                "UPDATE and DELETE mutations require a base version",
            )
        entity = await _load_entity(
            db,
            user_id,
            mutation.entity_type,
            mutation.entity_sync_id,
            for_update=True,
        )
        if entity is None:
            raise MutationRejected(ENTITY_NOT_FOUND, "The synchronized entity was not found")
        if mutation.base_version != entity.version:
            return await _conflict_outcome(db, mutation, entity)
        if entity.deleted_at is not None:
            raise MutationRejected(ENTITY_NOT_FOUND, "The synchronized entity is deleted")

        entity.version += 1
        entity.updated_at = now
        if mutation.operation == UPDATE:
            await _apply_payload(db, user_id, mutation.entity_type, entity, payload)
        else:
            entity.deleted_at = now
        await db.flush()

    change_data = None
    if mutation.operation != DELETE:
        change_data = await _serialize_entity(db, mutation.entity_type, entity)
    _append_change(
        db,
        user_id,
        device_id,
        mutation.mutation_id,
        mutation.entity_type,
        mutation.entity_sync_id,
        mutation.operation,
        entity.version,
        change_data,
    )
    if mutation.operation == DELETE:
        await db.flush()
        await _detach_deleted_relationships(
            db,
            user_id,
            device_id,
            mutation,
            entity,
            now,
        )
    return TideAcknowledgement(
        mutation_id=mutation.mutation_id,
        entity_type=mutation.entity_type,
        entity_sync_id=mutation.entity_sync_id,
        server_version=entity.version,
    )


async def _persist_rejection_after_integrity_error(
    db: AsyncSession,
    user_id: int,
    device_id: UUID,
    mutation: TideMutation,
) -> TideOutcome:
    async with db.begin():
        ledger = await _get_processed_mutation(db, user_id, mutation.mutation_id)
        if ledger is not None:
            return _outcome_from_ledger(ledger, device_id, mutation)
        outcome = TideRejection(
            mutation_id=mutation.mutation_id,
            entity_type=mutation.entity_type,
            entity_sync_id=mutation.entity_sync_id,
            error_code=MALFORMED_MUTATION,
            message="The mutation violates a server data constraint",
        )
        db.add(_ledger_from_outcome(user_id, device_id, mutation, outcome))
        return outcome


async def _process_mutation(
    db: AsyncSession,
    user_id: int,
    device_id: UUID,
    mutation: TideMutation,
) -> TideOutcome:
    try:
        async with db.begin():
            ledger = await _get_processed_mutation(db, user_id, mutation.mutation_id)
            if ledger is not None:
                return _outcome_from_ledger(ledger, device_id, mutation)
            try:
                async with db.begin_nested():
                    outcome = await _evaluate_mutation(db, user_id, device_id, mutation)
            except MutationRejected as rejection:
                outcome = TideRejection(
                    mutation_id=mutation.mutation_id,
                    entity_type=mutation.entity_type,
                    entity_sync_id=mutation.entity_sync_id,
                    error_code=rejection.code,
                    message=rejection.message,
                )
            if not (
                isinstance(outcome, TideRejection)
                and outcome.error_code == MUTATION_DEPENDENCY_PENDING
            ):
                db.add(_ledger_from_outcome(user_id, device_id, mutation, outcome))
            return outcome
    except IntegrityError:
        await db.rollback()
        return await _persist_rejection_after_integrity_error(
            db, user_id, device_id, mutation
        )


async def _load_changes(
    db: AsyncSession,
    user_id: int,
    cursor: int,
    requested_limit: int,
) -> tuple[list[TideChange], str, bool]:
    limit = min(requested_limit, MAX_DATA_LIMIT)
    rows = list(
        (
            await db.scalars(
                select(SyncChangeLog)
                .where(
                    SyncChangeLog.user_id == user_id,
                    SyncChangeLog.sequence > cursor,
                )
                .order_by(SyncChangeLog.sequence)
                .limit(limit + 1)
            )
        ).all()
    )
    more_changes = len(rows) > limit
    returned = rows[:limit]
    unsupported_types = {
        row.entity_type
        for row in returned
        if row.entity_type not in SUPPORTED_CHANGE_ENTITY_TYPES
    }
    if unsupported_types:
        raise RuntimeError(
            "The change feed contains entity types unsupported by the Android client: "
            + ", ".join(sorted(unsupported_types))
        )
    changes = [
        TideChange(
            sequence=str(row.sequence),
            entity_type=row.entity_type,
            entity_sync_id=row.entity_sync_id,
            operation=cast(Literal["CREATE", "UPDATE", "DELETE"], row.operation),
            server_version=row.entity_version,
            data=row.data,
        )
        for row in returned
    ]
    next_cursor = str(returned[-1].sequence) if returned else str(cursor)
    return changes, next_cursor, more_changes


def _partition_outcomes(
    outcomes: list[TideOutcome],
) -> tuple[list[TideAcknowledgement], list[TideRejection], list[TideConflict]]:
    acknowledged = [item for item in outcomes if isinstance(item, TideAcknowledgement)]
    rejected = [item for item in outcomes if isinstance(item, TideRejection)]
    conflicts = [item for item in outcomes if isinstance(item, TideConflict)]
    return acknowledged, rejected, conflicts


async def exchange_tide(
    db: AsyncSession,
    current_user: User,
    request: TideSyncRequest,
) -> TideSyncResponse:
    _validate_request(request)
    cursor = _parse_cursor(request.cursor)
    response_id = uuid4()

    if db.in_transaction():
        await db.commit()

    async with db.begin():
        await _validate_cursor(db, current_user.user_id, cursor)

    outcomes = [
        await _process_mutation(db, current_user.user_id, request.device_id, mutation)
        for mutation in request.mutations
    ]
    acknowledged, rejected, conflicts = _partition_outcomes(outcomes)

    async with db.begin():
        changes, next_cursor, more_changes = await _load_changes(
            db,
            current_user.user_id,
            cursor,
            request.data_limit,
        )
        db.add(
            SyncLog(
                user_id=current_user.user_id,
                result="SUCCESS",
                request_id=request.request_id,
                response_id=response_id,
                device_id=request.device_id,
                input_cursor=request.cursor,
                output_cursor=next_cursor,
                received_count=len(request.mutations),
                acknowledged_count=len(acknowledged),
                rejected_count=len(rejected),
                conflict_count=len(conflicts),
                returned_change_count=len(changes),
                completed_at=_utc_now(),
            )
        )

    return TideSyncResponse(
        request_id=request.request_id,
        response_id=response_id,
        acknowledged=acknowledged,
        rejected=rejected,
        conflicts=conflicts,
        changes=changes,
        next_cursor=next_cursor,
        more_changes=more_changes,
    )
