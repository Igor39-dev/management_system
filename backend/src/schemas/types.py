from datetime import datetime
from typing import Annotated

from pydantic import PlainSerializer

_DATETIME_FORMAT = "%Y-%m-%d | %H:%M"


def format_api_datetime(value: datetime) -> str:
    return value.replace(second=0, microsecond=0).strftime(_DATETIME_FORMAT)


ApiDateTime = Annotated[
    datetime,
    PlainSerializer(format_api_datetime, return_type=str, when_used="json"),
]
