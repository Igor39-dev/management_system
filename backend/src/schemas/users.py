from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.src.models.enums import UserRole


class UserBase(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    password: str | None = None


class UserGet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    first_name: str | None
    last_name: str | None
    role: UserRole
    team_id: int | None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
