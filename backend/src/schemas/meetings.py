from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MeetingBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    start_at: datetime
    end_at: datetime

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.end_at <= self.start_at:
            msg = "Окончание встречи должно быть позже начала"
            raise ValueError(msg)
        return self


class MeetingCreate(MeetingBase):
    participant_ids: list[int] = Field(default_factory=list)


class MeetingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    participant_ids: list[int] | None = None
    is_cancelled: bool | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.start_at is not None and self.end_at is not None:
            if self.end_at <= self.start_at:
                msg = "end_at must be later than start_at"
                raise ValueError(msg)
        return self


class MeetingGet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    start_at: datetime
    end_at: datetime
    is_cancelled: bool
    team_id: int
    organizer_id: int
    created_at: datetime
    updated_at: datetime


class MeetingGetDetail(MeetingGet):
    participant_ids: list[int] = Field(default_factory=list)
