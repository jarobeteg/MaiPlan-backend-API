from datetime import datetime

def datetime_to_ms(value: datetime | None) -> int | None:
    if value is None:
        return None

    return int(value.timestamp() * 1000)


def ms_to_datetime(value: int | None) -> datetime | None:
    if value is None:
        return None

    return datetime.fromtimestamp(value / 1000, tz=None)