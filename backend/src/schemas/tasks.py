from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.src.models.enums import TaskStatus


def _to_naive_utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    deadline: datetime | None = None

    @field_validator("deadline", mode="after")
    @classmethod
    def normalize_deadline(cls, value: datetime | None) -> datetime | None:
        return _to_naive_utc(value)


class TaskCreate(TaskBase):
    assignee_id: int | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus | None = None
    deadline: datetime | None = None
    assignee_id: int | None = None

    @field_validator("deadline", mode="after")
    @classmethod
    def normalize_deadline(cls, value: datetime | None) -> datetime | None:
        return _to_naive_utc(value)


class TaskGet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    deadline: datetime | None
    team_id: int
    creator_id: int
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime


class TaskCommentCreate(BaseModel):
    text: str = Field(min_length=1)


class TaskCommentGet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    author_id: int
    text: str
    created_at: datetime
    updated_at: datetime
