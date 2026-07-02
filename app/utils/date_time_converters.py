from datetime import datetime
from typing import overload

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

    return datetime.fromtimestamp(value / 1000, tz=None)
