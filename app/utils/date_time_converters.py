from datetime import date, datetime, timedelta, timezone
from typing import overload

EPOCH_DATE = date(1970, 1, 1)

@overload
def datetime_to_ms(value: datetime) -> int:
    ...

@overload
def datetime_to_ms(value: None) -> None:
    ...

def datetime_to_ms(value: datetime | None) -> int | None:
    if value is None:
        return None

    return int(value.timestamp() * 1000)


@overload
def ms_to_datetime(value: int) -> datetime:
    ...

@overload
def ms_to_datetime(value: None) -> None:
    ...

def ms_to_datetime(value: int | None) -> datetime | None:
    if value is None:
        return None

    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).astimezone()


@overload
def ms_to_timedelta(value: int) -> timedelta:
    ...

@overload
def ms_to_timedelta(value: None) -> None:
    ...

def ms_to_timedelta(value: int | None) -> timedelta | None:
    if value is None:
        return None

    return timedelta(milliseconds=value)


@overload
def timedelta_to_ms(value: timedelta) -> int:
    ...

@overload
def timedelta_to_ms(value: None) -> None:
    ...

def timedelta_to_ms(value: timedelta | None) -> int | None:
    if value is None:
        return None

    return value // timedelta(milliseconds=1)


@overload
def epoch_days_to_date(value: int) -> date:
    ...

@overload
def epoch_days_to_date(value: None) -> None:
    ...

def epoch_days_to_date(value: int | None) -> date | None:
    if value is None:
        return None

    return EPOCH_DATE + timedelta(days=value)


@overload
def date_to_epoch_days(value: date) -> int:
    ...

@overload
def date_to_epoch_days(value: None) -> None:
    ...

def date_to_epoch_days(value: date | None) -> int | None:
    if value is None:
        return None

    return (value - EPOCH_DATE).days
