from datetime import date
from uuid import NAMESPACE_URL, UUID, uuid5
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from core.task_contract import (
    MAX_ESTIMATED_MILLISECONDS,
    TaskRepeatRule,
    TaskRepeatUnit,
    normalize_task_description,
    normalize_task_title,
    strict_integer,
    task_date_from_epoch_day,
    task_date_to_epoch_day,
    task_rule_dates,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

PAGE_SIZE = 32

def occurrence_id(series_id: UUID, slot: date) -> UUID:
    return uuid5(NAMESPACE_URL, f"maiplan/task/{series_id}/{slot.isoformat()}")

def step_id(task_id: UUID, key: UUID) -> UUID:
    return uuid5(task_id, str(key))

def exclusion_id(series_id: UUID, slot: date) -> UUID:
    return uuid5(series_id, f"excluded:{slot.isoformat()}")

def occurrence_number(rule: TaskRepeatRule, slot: date) -> int:
    if rule.unit == TaskRepeatUnit.DAILY:
        return (slot - rule.anchor_date).days // rule.interval
    if rule.unit == TaskRepeatUnit.MONTHLY:
        return ((slot.year-rule.anchor_date.year)*12 + slot.month-rule.anchor_date.month)//rule.interval
    weeks = ((slot.toordinal()-slot.weekday()) -
             (rule.anchor_date.toordinal()-rule.anchor_date.weekday()))//7//rule.interval
    mask = strict_integer(rule.weekdays, 'repeat_weekdays')
    first = sum(bool(mask & (1 << day)) for day in range(rule.anchor_date.weekday(), 7))
    preceding = sum(bool(mask & (1 << day)) for day in range(slot.weekday()))
    return preceding - sum(bool(mask & (1 << day)) for day in range(rule.anchor_date.weekday())) if weeks == 0 else first + (weeks-1)*mask.bit_count() + preceding

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class TemplateStep(StrictModel):
    key: UUID
    title: StrictStr
    estimated_time: StrictInt | None = Field(default=None, ge=0, le=MAX_ESTIMATED_MILLISECONDS)
    _title = field_validator('title')(normalize_task_title)

class RelativeReminder(StrictModel):
    lead_days: StrictInt = Field(ge=0, le=7)
    minute_of_day: StrictInt = Field(ge=0, le=1439)
    zone_id: StrictStr
    message: StrictStr | None = Field(default=None, max_length=512)

    @field_validator('zone_id')
    @classmethod
    def zone(cls, value):
        if value != 'UTC' and '/' not in value:
            raise ValueError('Use an IANA time zone')
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError('Use a valid IANA time zone') from error
        return value

class SeriesRevision(StrictModel):
    revision: StrictInt = Field(ge=1)
    effective_from: StrictInt
    title: StrictStr
    description: StrictStr | None = None
    estimated_time: StrictInt | None = Field(default=None, ge=0, le=MAX_ESTIMATED_MILLISECONDS)
    category_sync_id: UUID | None = None
    repeat_unit: StrictInt
    repeat_interval: StrictInt
    repeat_weekdays: StrictInt | None = None
    repeat_anchor_date: StrictInt
    repeat_end_date: StrictInt | None = None
    steps: list[TemplateStep] = Field(default_factory=list, max_length=100)
    reminder: RelativeReminder | None = None
    _title = field_validator('title')(normalize_task_title)
    _description = field_validator('description')(normalize_task_description)

    def rule(self):
        return TaskRepeatRule(TaskRepeatUnit(self.repeat_unit), self.repeat_interval,
            task_date_from_epoch_day(self.repeat_anchor_date), self.repeat_weekdays,
            task_date_from_epoch_day(self.repeat_end_date))

    @model_validator(mode='after')
    def validate_revision(self):
        task_date_from_epoch_day(self.effective_from)
        self.rule()
        if len({step.key for step in self.steps}) != len(self.steps):
            raise ValueError('Template step keys must be unique')
        return self

class SeriesDefinition(StrictModel):
    revisions: list[SeriesRevision] = Field(min_length=1, max_length=1000)

    @model_validator(mode='after')
    def ordered(self):
        retired = set()
        previous = set()
        for i, revision in enumerate(self.revisions):
            if revision.revision != i+1:
                raise ValueError('Series revisions must be consecutive')
            keys = {step.key for step in revision.steps}
            if keys & retired:
                raise ValueError('Removed template keys cannot be recycled')
            retired.update(previous-keys)
            previous = keys
        if self.revisions[0].effective_from != self.revisions[0].repeat_anchor_date:
            raise ValueError('Initial effective date must be the anchor')
        return self

    def slots(self, start: date, through: date):
        for i, revision in enumerate(self.revisions):
            lower = max(start, task_date_from_epoch_day(revision.effective_from))
            upper = through
            if i+1 < len(self.revisions):
                next_day = task_date_from_epoch_day(min(r.effective_from for r in self.revisions[i+1:]))
                if next_day <= lower:
                    continue
                from datetime import timedelta
                upper = min(upper, next_day-timedelta(days=1))
            if lower > upper:
                continue
            for slot in task_rule_dates(revision.rule(), lower, upper):
                yield slot, revision, occurrence_number(revision.rule(), slot)

    def revision_for(self, slot: date):
        epoch = task_date_to_epoch_day(slot)
        return next((r for r in reversed(self.revisions) if r.effective_from <= epoch), None)
