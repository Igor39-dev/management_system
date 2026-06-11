from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from backend.src.models.enums import UserRole


class UserBase(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    new_password: str | None = Field(default=None, min_length=8, max_length=128)
    current_password: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_update(self) -> "UserProfileUpdate":
        update_fields = self.model_fields_set - {"current_password"}
        if not update_fields:
            raise ValueError("Не указаны поля для обновления")

        if {"email", "new_password"} & self.model_fields_set:
            if "current_password" not in self.model_fields_set or not self.current_password:
                raise ValueError("Для смены email или пароля необходимо указать текущий пароль")

        if (
            "new_password" in self.model_fields_set
            and "current_password" in self.model_fields_set
            and self.current_password == self.new_password
        ):
            raise ValueError("Новый пароль должен отличаться от текущего")

        return self


class UserProfileDelete(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)


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
