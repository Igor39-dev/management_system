from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.src.models.enums import UserRole


class TeamBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)


class TeamJoin(BaseModel):
    code: str = Field(min_length=4, max_length=32)


class TeamGet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    owner_id: int
    created_at: datetime
    updated_at: datetime


class TeamMemberGet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    first_name: str | None
    last_name: str | None
    role: UserRole


class TeamGetDetail(TeamGet):
    members: list[TeamMemberGet]


class TeamMemberRoleUpdate(BaseModel):
    role: UserRole
