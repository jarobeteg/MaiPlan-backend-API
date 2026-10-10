import re
from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from core.settings import (
    TIDE_DEFAULT_DATA_LIMIT,
    TIDE_MAX_DATA_LIMIT,
    TIDE_MAX_MUTATIONS_PER_REQUEST,
)
from core.task_contract import (
    MAX_ESTIMATED_MILLISECONDS,
    MAX_ORDINAL,
    normalize_task_description,
    normalize_task_title,
    task_date_from_epoch_day,
    task_relationship_uuid,
    validate_task_completion,
    validate_task_repeat_metadata,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

TIDE_PROTOCOL_VERSION = 3
DEFAULT_DATA_LIMIT = TIDE_DEFAULT_DATA_LIMIT
MAX_DATA_LIMIT = TIDE_MAX_DATA_LIMIT
MAX_MUTATIONS_PER_REQUEST = TIDE_MAX_MUTATIONS_PER_REQUEST

MUTABLE_ENTITY_TYPES = frozenset(
    {"category", "reminder", "event", "note", "task", "subtask", "task_action", "task_series", "task_exclusion", "task_series_action"}
)
SUPPORTED_CHANGE_ENTITY_TYPES = frozenset({"user", *MUTABLE_ENTITY_TYPES} - {"task_action", "task_series_action"})


class TideModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TideMutation(TideModel):
    mutation_id: UUID
    entity_type: str = Field(min_length=1, max_length=50)
    entity_sync_id: UUID
    operation: str = Field(min_length=1, max_length=16)
    base_version: int | None = Field(default=None, ge=1)
    data: dict[str, Any] | None = None


class TideSyncRequest(TideModel):
    tide_protocol_version: int
    request_id: UUID
    device_id: UUID
    cursor: str | None = Field(default=None, max_length=255)
    data_limit: int = Field(default=DEFAULT_DATA_LIMIT, gt=0)
    mutations: list[TideMutation] = Field(
        default_factory=list,
        max_length=MAX_MUTATIONS_PER_REQUEST,
    )


class TideActionSnapshot(TideModel):
    entity_type: Literal["task", "subtask", "task_series", "task_exclusion"]
    entity_sync_id: UUID
    operation: Literal["CREATE", "UPDATE", "DELETE"]
    server_version: int = Field(ge=1)
    data: dict[str, Any] | None = None


class TideAcknowledgement(TideModel):
    mutation_id: UUID
    entity_type: str
    entity_sync_id: UUID
    server_version: int = Field(ge=1)
    effects: list[TideActionSnapshot] = Field(default_factory=list)
    continuation: dict | None = None


class TideRejection(TideModel):
    mutation_id: UUID
    entity_type: str
    entity_sync_id: UUID
    error_code: str
    message: str | None = None


class TideConflict(TideModel):
    mutation_id: UUID
    entity_type: str
    entity_sync_id: UUID
    server_version: int = Field(ge=1)
    server_data: dict[str, Any] | None = None


class TideChange(TideModel):
    sequence: str
    entity_type: str
    entity_sync_id: UUID
    operation: Literal["CREATE", "UPDATE", "DELETE"]
    server_version: int = Field(ge=1)
    data: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_operation_data(self):
        if self.operation == "DELETE" and self.data is not None:
            raise ValueError("DELETE changes must not include data")
        if self.operation != "DELETE" and self.data is None:
            raise ValueError("CREATE and UPDATE changes require data")
        return self


class TideSyncResponse(TideModel):
    tide_protocol_version: int = TIDE_PROTOCOL_VERSION
    request_id: UUID
    response_id: UUID
    acknowledged: list[TideAcknowledgement]
    rejected: list[TideRejection]
    conflicts: list[TideConflict]
    changes: list[TideChange]
    next_cursor: str
    more_changes: bool


class CategoryPayload(TideModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    color: str = Field(min_length=1, max_length=32)
    icon: str = Field(min_length=1, max_length=32)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: Any) -> Any:
        if value is None:
            return ""
        return value.strip() if isinstance(value, str) else value


class ZonedPayload(TideModel):
    zone_id: str = Field(min_length=1, max_length=255)

    @field_validator("zone_id")
    @classmethod
    def zone_id_must_be_valid(cls, value: str) -> str:
        if value != "UTC" and not re.fullmatch(
            r"[A-Za-z0-9._+-]+(?:/[A-Za-z0-9._+-]+)+",
            value,
        ):
            raise ValueError("zone_id must use an IANA time-zone identifier")

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("zone_id is not available") from exc

        return value


class ReminderPayload(ZonedPayload):
    reminder_time: int
    frequency: int
    status: int
    message: str | None = None


EPOCH_DAY = date(1970, 1, 1)


def event_date_from_epoch_day(value: int) -> date:
    try:
        return EPOCH_DAY + timedelta(days=value)
    except OverflowError as error:
        raise ValueError("event date is outside the supported range") from error


class EventPayload(ZonedPayload):
    category_sync_id: UUID | None = None
    reminder_sync_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    start_date: int
    end_date: int
    start_time: int | None = None
    end_time: int | None = None
    recurrence_frequency: Literal["DAILY", "WEEKLY", "MONTHLY"] | None = None
    recurrence_interval: int | None = Field(default=None, ge=1, le=365)
    recurrence_weekdays: int | None = Field(default=None, ge=1, le=127)
    recurrence_monthly_mode: Literal[
        "DAY_OF_MONTH", "LAST_DAY", "NTH_WEEKDAY", "LAST_WEEKDAY"
    ] | None = None
    recurrence_until_date: int | None = None
    reminder_offset_minutes: int | None = Field(default=None, ge=0, le=10080)
    reminder_lead_days: int | None = Field(default=None, ge=0, le=7)
    reminder_minute_of_day: int | None = Field(default=None, ge=0, le=1439)
    relative_reminder_message: str | None = None
    priority: int
    location: str | None = Field(default=None, max_length=255)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value

    @model_validator(mode="after")
    def event_times_must_be_consistent(self):
        if (self.start_time is None) != (self.end_time is None):
            raise ValueError("start_time and end_time must be provided together")
        zone = ZoneInfo(self.zone_id)
        start_day = event_date_from_epoch_day(self.start_date)
        end_day = event_date_from_epoch_day(self.end_date)
        if end_day < start_day:
            raise ValueError("end_date precedes start_date")
        if self.start_time is not None and self.end_time is not None:
            start = utc_from_millis(self.start_time).astimezone(zone)
            end = utc_from_millis(self.end_time).astimezone(zone)
            if start.date() != start_day or end.date() != end_day:
                raise ValueError("event timestamps must match start/end dates")
            if start.fold == 1 or end.fold == 1:
                raise ValueError(
                    "the second occurrence of an overlapping event time is unsupported"
                )
            if end.astimezone(UTC) <= start.astimezone(UTC):
                raise ValueError("event end must be after start")
        if self.recurrence_frequency is None:
            if any(value is not None for value in (
                self.recurrence_interval, self.recurrence_weekdays,
                self.recurrence_monthly_mode, self.recurrence_until_date,
            )):
                raise ValueError("recurrence fields require a frequency")
        elif self.recurrence_frequency == "DAILY":
            if self.recurrence_interval is None or (
                self.recurrence_weekdays is not None or
                self.recurrence_monthly_mode is not None
            ):
                raise ValueError("daily recurrence needs only an interval")
        elif self.recurrence_frequency == "WEEKLY":
            if self.recurrence_interval is None or self.recurrence_weekdays is None:
                raise ValueError("weekly recurrence needs interval and weekdays")
            if self.recurrence_interval > 52 or self.recurrence_monthly_mode is not None:
                raise ValueError("invalid weekly recurrence fields")
            if not self.recurrence_weekdays & (1 << start_day.weekday()):
                raise ValueError("anchor date must be a selected weekday")
        else:
            if self.recurrence_interval is None or self.recurrence_interval > 24:
                raise ValueError("monthly interval must be 1–24")
            if self.recurrence_weekdays is not None or self.recurrence_monthly_mode is None:
                raise ValueError("monthly recurrence needs a pattern")
            if (self.recurrence_monthly_mode == "LAST_DAY" and
                start_day.day != monthrange(start_day.year, start_day.month)[1]
            ):
                raise ValueError("anchor must be the month's last day")
            if (self.recurrence_monthly_mode == "LAST_WEEKDAY" and
                start_day.day + 7 <= monthrange(start_day.year, start_day.month)[1]
            ):
                raise ValueError("anchor must be the month's last selected weekday")
        if (
            self.recurrence_frequency is not None
            and self.recurrence_until_date is not None
            and event_date_from_epoch_day(self.recurrence_until_date) < start_day
        ):
            raise ValueError("recurrence until date precedes the anchor")
        if (self.reminder_lead_days is None) != (self.reminder_minute_of_day is None):
            raise ValueError("date-only reminder needs lead days and local clock")
        date_rule = self.reminder_lead_days is not None
        timed = self.start_time is not None
        if timed and date_rule:
            raise ValueError("timed events use minute-offset reminders")
        if not timed and self.reminder_offset_minutes is not None:
            raise ValueError("date-only events use local-time reminders")
        modes = sum((
            self.reminder_sync_id is not None,
            self.reminder_offset_minutes is not None,
            date_rule,
        ))
        if modes > 1:
            raise ValueError("choose only one reminder mode")
        if self.recurrence_frequency is not None and self.reminder_sync_id is not None:
            raise ValueError("a repeating event needs a relative reminder rule")
        if self.relative_reminder_message is not None and not (
            self.reminder_offset_minutes is not None or date_rule
        ):
            raise ValueError("relative reminder message requires a rule")
        return self


class NotePayload(TideModel):
    category_sync_id: UUID | None = None
    reminder_sync_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    content: str | None = None
    is_pinned: bool

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


class TaskPayload(TideModel):
    category_sync_id: UUID | None = None
    reminder_sync_id: UUID | None = None
    title: StrictStr
    description: StrictStr | None = None
    status: StrictInt = Field(ge=0, le=4)
    scheduled_date: StrictInt | None = None
    estimated_time: StrictInt | None = Field(default=None, ge=0, le=MAX_ESTIMATED_MILLISECONDS)
    completed_date: StrictInt | None = None
    series_id: StrictStr | None = None
    occurrence_number: StrictInt | None = Field(default=None, ge=0, le=MAX_ORDINAL)
    slot_date: StrictInt | None = None
    generation_revision: StrictInt | None = Field(default=None, ge=1)
    occurrence_override: StrictBool = False
    relative_reminder: dict | None = None
    repeat_unit: StrictInt | None = None
    repeat_interval: StrictInt | None = Field(default=None, ge=1)
    repeat_weekdays: StrictInt | None = Field(default=None, ge=0)
    repeat_end_date: StrictInt | None = None
    repeat_anchor_date: StrictInt | None = None

    @field_validator("category_sync_id", "reminder_sync_id", mode="before")
    @classmethod
    def validate_relationship_uuid(cls, value):
        return task_relationship_uuid(value)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return normalize_task_title(value)

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return normalize_task_description(value)

    @model_validator(mode="after")
    def validate_task_contract(self):
        from core.task_series_contract import RelativeReminder
        task_date_from_epoch_day(self.slot_date)
        if self.series_id is None:
            if self.slot_date is not None or self.generation_revision is not None or self.occurrence_override:
                raise ValueError('A one-off Task cannot contain occurrence identity metadata')
        elif self.slot_date is None or self.generation_revision is None:
            raise ValueError('A repeating Task requires its original slot and generation revision')
        if self.relative_reminder is not None:
            self.relative_reminder = RelativeReminder.model_validate(self.relative_reminder).model_dump(mode='json')
            if self.reminder_sync_id is not None:
                raise ValueError('Absolute and relative reminders are mutually exclusive')
            if self.scheduled_date is None:
                raise ValueError('A relative reminder requires a planned date')
        scheduled = task_date_from_epoch_day(self.scheduled_date)
        validate_task_completion(self.status, task_date_from_epoch_day(self.completed_date))
        validate_task_repeat_metadata(
            series_id=self.series_id, occurrence_number=self.occurrence_number,
            repeat_unit=self.repeat_unit, repeat_interval=self.repeat_interval,
            repeat_weekdays=self.repeat_weekdays,
            repeat_end_date=task_date_from_epoch_day(self.repeat_end_date),
            repeat_anchor_date=task_date_from_epoch_day(self.repeat_anchor_date),
            scheduled_date=scheduled,
        )
        return self


class SubtaskPayload(TideModel):
    parent_task_sync_id: UUID
    title: StrictStr
    status: StrictInt = Field(ge=0, le=4)
    sort_order: StrictInt = Field(ge=0, le=MAX_ORDINAL)
    estimated_time: StrictInt | None = Field(default=None, ge=0, le=MAX_ESTIMATED_MILLISECONDS)
    completed_date: StrictInt | None = None

    @field_validator("parent_task_sync_id", mode="before")
    @classmethod
    def validate_relationship_uuid(cls, value):
        return task_relationship_uuid(value)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return normalize_task_title(value)

    @model_validator(mode="after")
    def validate_subtask_contract(self):
        validate_task_completion(self.status, task_date_from_epoch_day(self.completed_date))
        return self


class UserPayload(TideModel):
    email: EmailStr
    username: str = Field(min_length=1, max_length=32)


ENTITY_PAYLOAD_MODELS: dict[str, type[TideModel]] = {
    "category": CategoryPayload,
    "reminder": ReminderPayload,
    "event": EventPayload,
    "note": NotePayload,
    "task": TaskPayload,
    "subtask": SubtaskPayload,
    "user": UserPayload,
}

def utc_from_millis(value: int) -> datetime:
    try:
        return datetime.fromtimestamp(value / 1000, UTC)
    except (OverflowError, OSError, ValueError) as exc:
        raise ValueError("timestamp is outside the supported range") from exc
