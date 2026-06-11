from pydantic import BaseModel, ConfigDict, Field

from backend.src.schemas.types import ApiDateTime


class EvaluationCreate(BaseModel):
    score: int = Field(ge=1, le=5)


class EvaluationUpdate(BaseModel):
    score: int | None = Field(default=None, ge=1, le=5)


class EvaluationGet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    evaluator_id: int
    score: int
    created_at: ApiDateTime
    updated_at: ApiDateTime
