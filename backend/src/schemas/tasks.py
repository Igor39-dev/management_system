from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.src.models.enums import TaskStatus
from backend.src.schemas.types import ApiDateTime


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

    @model_validator(mode="after")
    def validate_update(self) -> "TaskUpdate":
        if not self.model_fields_set:
            raise ValueError("Не указаны поля для обновления")
        return self


class TaskGet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    deadline: ApiDateTime | None
    team_id: int
    creator_id: int
    assignee_id: int | None
    created_at: ApiDateTime
    updated_at: ApiDateTime


class TaskCommentCreate(BaseModel):
    text: str = Field(min_length=1)


class TaskCommentGet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    author_id: int
    text: str
    created_at: ApiDateTime
    updated_at: ApiDateTime
