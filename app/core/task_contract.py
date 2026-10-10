from calendar import monthrange
from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import date, timedelta
from enum import IntEnum
from typing import overload
from uuid import UUID

EPOCH_DATE = date(1970, 1, 1)
MIN_EPOCH_DAY = (date.min - EPOCH_DATE).days
MAX_EPOCH_DAY = (date.max - EPOCH_DATE).days
MAX_ESTIMATED_MILLISECONDS = 365 * 24 * 60 * 60 * 1000
MAX_TITLE_LENGTH = 255
MAX_DESCRIPTION_LENGTH = 10_000
MAX_ORDINAL = 2_147_483_647
TEXT_WHITESPACE = "".join(
    chr(value)
    for value in (
        *range(9, 14),
        *range(28, 33),
        0x85,
        0xA0,
        0x1680,
        *range(0x2000, 0x200B),
        0x2028,
        0x2029,
        0x202F,
        0x205F,
        0x3000,
    )
)


class TaskStatus(IntEnum):
    TODO = 0
    DONE = 1
    IN_PROGRESS = 2
    SKIPPED = 3
    CANCELLED = 4

    @property
    def is_terminal(self) -> bool:
        return self in {self.DONE, self.SKIPPED, self.CANCELLED}


class TaskRepeatUnit(IntEnum):
    DAILY = 1
    WEEKLY = 2
    MONTHLY = 3


def strict_integer(value: object, name: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer")
    return value


def _validate_repeat_interval(unit: TaskRepeatUnit, value: object) -> int:
    interval = strict_integer(value, "repeat_interval")
    bounds = {
        TaskRepeatUnit.DAILY: 365,
        TaskRepeatUnit.WEEKLY: 52,
        TaskRepeatUnit.MONTHLY: 24,
    }
    if not 1 <= interval <= bounds[unit]:
        raise ValueError("repeat_interval is outside its unit's supported range")
    return interval


def task_status(value: int | TaskStatus) -> TaskStatus:
    if isinstance(value, TaskStatus):
        return value
    return TaskStatus(strict_integer(value, "status"))


def task_relationship_uuid(value: str | UUID | None) -> UUID | None:
    if value is None or isinstance(value, UUID):
        return value
    if not isinstance(value, str):
        raise TypeError("Task relationship identity must be UUID text")
    parsed = UUID(value)
    if str(parsed) != value.lower():
        raise ValueError("Task relationship identity must be a hyphenated UUID")
    return parsed


def _text(value: str, name: str, limit: int) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be text")
    if "\x00" in value or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise ValueError(f"{name} contains an invalid Unicode character")
    result = value.strip(TEXT_WHITESPACE)
    if len(result) > limit:
        raise ValueError(f"{name} exceeds {limit} characters")
    return result


def normalize_task_title(value: str) -> str:
    result = _text(value, "title", MAX_TITLE_LENGTH)
    if not result:
        raise ValueError("title must not be blank")
    return result


def normalize_task_description(value: str | None) -> str | None:
    return (
        None
        if value is None
        else _text(value, "description", MAX_DESCRIPTION_LENGTH) or None
    )


@overload
def task_date_from_epoch_day(value: int) -> date: ...


@overload
def task_date_from_epoch_day(value: None) -> None: ...


def task_date_from_epoch_day(value: int | None) -> date | None:
    if value is None:
        return None
    strict_integer(value, "date")
    if not MIN_EPOCH_DAY <= value <= MAX_EPOCH_DAY:
        raise ValueError("Task date is outside years 1 through 9999")
    return EPOCH_DATE + timedelta(days=value)


@overload
def task_date_to_epoch_day(value: date) -> int: ...


@overload
def task_date_to_epoch_day(value: None) -> None: ...


def task_date_to_epoch_day(value: date | None) -> int | None:
    if value is None:
        return None
    if type(value) is not date:
        raise TypeError("Task date must be a date without a time")
    return (value - EPOCH_DATE).days


@overload
def validate_task_estimate(value: int) -> int: ...


@overload
def validate_task_estimate(value: None) -> None: ...


def validate_task_estimate(value: int | None) -> int | None:
    if value is not None:
        strict_integer(value, "estimated_time")
        if not 0 <= value <= MAX_ESTIMATED_MILLISECONDS:
            raise ValueError("estimated_time must be between zero and 365 fixed days")
    return value


def task_duration_from_milliseconds(value: int | None) -> timedelta | None:
    return (
        None if value is None else timedelta(milliseconds=validate_task_estimate(value))
    )


def task_duration_to_milliseconds(value: timedelta | None) -> int | None:
    if value is None:
        return None
    if type(value) is not timedelta:
        raise TypeError("Task duration must be a fixed timedelta")
    microseconds = (value.days * 86400 + value.seconds) * 1_000_000 + value.microseconds
    if microseconds % 1000:
        raise ValueError("Task duration must contain whole milliseconds")
    return validate_task_estimate(microseconds // 1000)


def validate_task_completion(
    status: int | TaskStatus, completed_date: date | None
) -> None:
    state = task_status(status)
    task_date_to_epoch_day(completed_date)
    if (state == TaskStatus.DONE) != (completed_date is not None):
        raise ValueError("Only Done has a completed_date, and Done requires one")


@dataclass(frozen=True)
class TaskRepeatRule:
    unit: TaskRepeatUnit
    interval: int
    anchor_date: date
    weekdays: int | None = None
    end_date: date | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.unit, TaskRepeatUnit):
            raise TypeError("Unknown Task repeat unit")
        _validate_repeat_interval(self.unit, self.interval)
        if self.anchor_date is None:
            raise ValueError("A repeat rule requires an anchor date")
        task_date_to_epoch_day(self.anchor_date)
        task_date_to_epoch_day(self.end_date)
        if self.end_date is not None and self.end_date < self.anchor_date:
            raise ValueError("repeat_end_date precedes repeat_anchor_date")
        if self.unit == TaskRepeatUnit.WEEKLY:
            weekdays = strict_integer(self.weekdays, "repeat_weekdays")
            if not 1 <= weekdays <= 127:
                raise ValueError("Weekly repetition requires a weekday mask in 1..127")
            if not weekdays & (1 << self.anchor_date.weekday()):
                raise ValueError("The weekly mask must include the anchor weekday")
        elif self.weekdays is not None:
            raise ValueError("Only weekly repetition has a weekday mask")


def validate_task_repeat_metadata(
    *,
    series_id: str | None,
    occurrence_number: int | None,
    repeat_unit: int | None,
    repeat_interval: int | None,
    repeat_weekdays: int | None,
    repeat_end_date: date | None,
    repeat_anchor_date: date | None,
    scheduled_date: date | None,
) -> TaskRepeatRule | None:
    fields = (
        series_id,
        occurrence_number,
        repeat_interval,
        repeat_weekdays,
        repeat_end_date,
        repeat_anchor_date,
    )
    if repeat_unit is None:
        if any(value is not None for value in fields):
            raise ValueError("A one-off Task must not contain repeat metadata")
        return None
    if not isinstance(series_id, str):
        raise TypeError("series_id must be a canonical lowercase UUID")
    if str(UUID(series_id)) != series_id:
        raise ValueError("series_id must be a canonical lowercase UUID")
    occurrence_number = strict_integer(occurrence_number, "occurrence_number")
    if not 0 <= occurrence_number <= MAX_ORDINAL:
        raise ValueError("occurrence_number is outside the supported range")
    if scheduled_date is None:
        raise ValueError("A repeating occurrence requires a planned date")
    task_date_to_epoch_day(scheduled_date)
    unit = TaskRepeatUnit(strict_integer(repeat_unit, "repeat_unit"))
    interval = _validate_repeat_interval(unit, repeat_interval)
    if repeat_anchor_date is None:
        raise ValueError("A repeat rule requires an anchor date")
    return TaskRepeatRule(
        unit,
        interval,
        repeat_anchor_date,
        repeat_weekdays,
        repeat_end_date,
    )


def task_rule_dates(
    rule: TaskRepeatRule, from_date: date, through_date: date
) -> Iterator[date]:
    task_date_to_epoch_day(from_date)
    task_date_to_epoch_day(through_date)
    if from_date > through_date:
        raise ValueError("Calendar window is reversed")
    start = max(from_date, rule.anchor_date)
    end = min(through_date, rule.end_date or date.max)
    if start > end:
        return
    if rule.unit == TaskRepeatUnit.DAILY:
        offset = (start - rule.anchor_date).days
        step = (offset + rule.interval - 1) // rule.interval
        while True:
            ordinal = rule.anchor_date.toordinal() + step * rule.interval
            if ordinal > end.toordinal():
                return
            yield date.fromordinal(ordinal)
            step += 1
    elif rule.unit == TaskRepeatUnit.WEEKLY:
        weekdays = strict_integer(rule.weekdays, "repeat_weekdays")
        anchor_monday = rule.anchor_date.toordinal() - rule.anchor_date.weekday()
        start_monday = start.toordinal() - start.weekday()
        weeks = (start_monday - anchor_monday) // 7
        step = (weeks + rule.interval - 1) // rule.interval
        while True:
            monday = anchor_monday + step * rule.interval * 7
            if monday > end.toordinal():
                return
            for weekday in range(7):
                ordinal = monday + weekday
                if (
                    weekdays & (1 << weekday)
                    and start.toordinal() <= ordinal <= end.toordinal()
                ):
                    yield date.fromordinal(ordinal)
            step += 1
    else:
        anchor_month = (rule.anchor_date.year - 1) * 12 + rule.anchor_date.month - 1
        start_month = (start.year - 1) * 12 + start.month - 1
        step = (start_month - anchor_month) // rule.interval
        while True:
            month_index = anchor_month + step * rule.interval
            year, month = month_index // 12 + 1, month_index % 12 + 1
            if year > end.year or (year == end.year and month > end.month):
                return
            candidate = date(
                year, month, min(rule.anchor_date.day, monthrange(year, month)[1])
            )
            if start <= candidate <= end:
                yield candidate
            step += 1


@dataclass(frozen=True)
class TaskCompletion:
    status: TaskStatus = TaskStatus.TODO
    completed_date: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", task_status(self.status))
        validate_task_completion(self.status, self.completed_date)


@dataclass(frozen=True)
class SubtaskCompletion:
    sync_id: UUID
    completion: TaskCompletion = TaskCompletion()


@dataclass(frozen=True)
class TaskChecklist:
    completion: TaskCompletion
    subtasks: tuple[SubtaskCompletion, ...] = ()

    def __post_init__(self) -> None:
        identities = [step.sync_id for step in self.subtasks]
        if len(identities) != len(set(identities)):
            raise ValueError("Duplicate Subtask identity")


def _set_completion(
    previous: TaskCompletion, status: int | TaskStatus, today: date
) -> TaskCompletion:
    status = task_status(status)
    if today is None:
        raise ValueError("A Task status action requires its local calendar date")
    task_date_to_epoch_day(today)
    if status == previous.status:
        return previous
    return TaskCompletion(status, today if status == TaskStatus.DONE else None)


def apply_task_status(
    state: TaskChecklist, status: int | TaskStatus, today: date
) -> TaskChecklist:
    status = task_status(status)
    if status == TaskStatus.IN_PROGRESS and state.completion.status.is_terminal:
        raise ValueError("Reopen the Task before starting it")
    parent = _set_completion(state.completion, status, today)
    steps = state.subtasks
    if status != TaskStatus.IN_PROGRESS:
        steps = tuple(
            replace(step, completion=_set_completion(step.completion, status, today))
            for step in steps
        )
    return TaskChecklist(parent, steps)


def apply_subtask_status(
    state: TaskChecklist, sync_id: UUID, status: int | TaskStatus, today: date
) -> TaskChecklist:
    status = task_status(status)
    step = next((step for step in state.subtasks if step.sync_id == sync_id), None)
    if step is None:
        raise ValueError("Subtask does not belong to this checklist")
    if step.completion.status == status:
        return state
    if state.completion.status.is_terminal:
        raise ValueError("Reopen the Task before changing its checklist")
    steps = tuple(
        replace(item, completion=_set_completion(item.completion, status, today))
        if item.sync_id == sync_id
        else item
        for item in state.subtasks
    )
    if steps and all(item.completion.status.is_terminal for item in steps):
        parent = _set_completion(state.completion, TaskStatus.DONE, today)
    elif state.completion.status == TaskStatus.IN_PROGRESS or any(
        item.completion.status != TaskStatus.TODO for item in steps
    ):
        parent = TaskCompletion(TaskStatus.IN_PROGRESS)
    else:
        parent = TaskCompletion()
    return TaskChecklist(parent, steps)


@dataclass(frozen=True)
class TaskEstimate:
    milliseconds: int | None
    is_partial: bool
    is_manual: bool


def effective_task_estimate(
    manual: int | None, steps: tuple[int | None, ...]
) -> TaskEstimate:
    validate_task_estimate(manual)
    for value in steps:
        validate_task_estimate(value)
    if manual is not None:
        return TaskEstimate(manual, False, True)
    known = [value for value in steps if value is not None]
    return TaskEstimate(
        sum(known) if known else None, bool(steps) and len(known) != len(steps), False
    )


def task_sql_checks(*, subtask: bool = False) -> dict[str, str]:
    whitespace_sql = " || ".join(f"chr({ord(char)})" for char in TEXT_WHITESPACE)
    checks = {
        "status": "status IN (0, 1, 2, 3, 4)",
        "completion": "(status = 1) = (completed_date IS NOT NULL)",
        "completed_date_range": (
            "completed_date IS NULL OR completed_date BETWEEN DATE '0001-01-01' "
            "AND DATE '9999-12-31'"
        ),
        "title_contract": (
            f"char_length(title) BETWEEN 1 AND {MAX_TITLE_LENGTH} "
            f"AND length(btrim(title, {whitespace_sql})) > 0 "
            f"AND title = btrim(title, {whitespace_sql})"
        ),
        "estimated_time_contract": (
            "estimated_time IS NULL OR (estimated_time >= INTERVAL '0 seconds' "
            "AND estimated_time <= INTERVAL '365 days' "
            "AND EXTRACT(YEAR FROM estimated_time) = 0 "
            "AND EXTRACT(MONTH FROM estimated_time) = 0 "
            "AND MOD(EXTRACT(EPOCH FROM estimated_time) * 1000, 1) = 0)"
        ),
    }
    if subtask:
        checks["sort_order_contract"] = f"sort_order BETWEEN 0 AND {MAX_ORDINAL}"
        return checks
    checks["scheduled_date_range"] = (
        "scheduled_date IS NULL OR scheduled_date BETWEEN DATE '0001-01-01' "
        "AND DATE '9999-12-31'"
    )
    checks["description_contract"] = (
        "description IS NULL OR (char_length(description) BETWEEN 1 "
        f"AND {MAX_DESCRIPTION_LENGTH} "
        f"AND length(btrim(description, {whitespace_sql})) > 0 "
        f"AND description = btrim(description, {whitespace_sql}))"
    )
    checks["recurrence_contract"] = (
        "COALESCE((\n"
        "        (repeat_unit IS NULL AND series_id IS NULL "
        "AND occurrence_number IS NULL AND\n"
        "         repeat_interval IS NULL AND repeat_weekdays IS NULL AND\n"
        "         repeat_end_date IS NULL AND repeat_anchor_date IS NULL)\n"
        "        OR\n"
        "        (repeat_unit IN (1, 2, 3) AND series_id IS NOT NULL AND\n"
        "         series_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}"
        "-[0-9a-f]{4}-[0-9a-f]{12}$' AND\n"
        "         occurrence_number IS NOT NULL "
        "AND occurrence_number BETWEEN 0 AND 2147483647 AND\n"
        "         scheduled_date IS NOT NULL AND repeat_anchor_date IS NOT NULL AND\n"
        "         repeat_anchor_date BETWEEN DATE '0001-01-01' "
        "AND DATE '9999-12-31' AND\n"
        "         (repeat_end_date IS NULL "
        "OR repeat_end_date BETWEEN repeat_anchor_date AND DATE '9999-12-31') AND\n"
        "         ((repeat_unit = 1 AND repeat_interval BETWEEN 1 AND 365 "
        "AND repeat_weekdays IS NULL) OR\n"
        "          (repeat_unit = 2 AND repeat_interval BETWEEN 1 AND 52 "
        "AND repeat_weekdays BETWEEN 1 AND 127 AND\n"
        "           (repeat_weekdays & (1 << (EXTRACT(ISODOW "
        "FROM repeat_anchor_date)::INTEGER - 1))) <> 0) OR\n"
        "          (repeat_unit = 3 AND repeat_interval BETWEEN 1 AND 24 "
        "AND repeat_weekdays IS NULL)))\n"
        "    ), FALSE)"
    )
    return checks
