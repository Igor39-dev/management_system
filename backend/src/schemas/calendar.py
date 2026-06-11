from datetime import date

from pydantic import BaseModel, Field

from backend.src.models.enums import CalendarEventType, TaskStatus
from backend.src.schemas.types import ApiDateTime


class CalendarEvent(BaseModel):
    id: int
    type: CalendarEventType
    title: str
    starts_at: ApiDateTime
    ends_at: ApiDateTime | None = None
    status: TaskStatus | None = None
    is_cancelled: bool | None = None


class CalendarMonthGet(BaseModel):
    year: int = Field(ge=1, le=9999)
    month: int = Field(ge=1, le=12)
    events: list[CalendarEvent]


class CalendarDayGet(BaseModel):
    date: date
    events: list[CalendarEvent]
