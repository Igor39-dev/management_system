import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.models.users import UserOrm
from backend.src.schemas.users import UserProfileUpdate
from backend.src.services.auth import AuthService, EmailAlreadyRegisteredError


class InvalidCurrentPasswordError(Exception):
    pass


class UserService:
    @classmethod
    def _verify_current_password(cls, user: UserOrm, password: str) -> None:
        if not AuthService.verify_password(password, user.hashed_password):
            raise InvalidCurrentPasswordError

    @classmethod
    async def update_profile(
        cls,
        db: AsyncSession,
        user: UserOrm,
        data: UserProfileUpdate,
    ) -> UserOrm:
        update_data = data.model_dump(exclude_unset=True)
        current_password = update_data.pop("current_password", None)
        new_password = update_data.pop("new_password", None)
        email = update_data.pop("email", None)

        for field, value in update_data.items():
            setattr(user, field, value)

        if email is not None or new_password is not None:
            cls._verify_current_password(user, current_password)

        if email is not None and email != user.email:
            existing_user = await AuthService.get_user_by_email(db, email)
            if existing_user is not None:
                raise EmailAlreadyRegisteredError

            user.email = email
            user.is_verified = False

        if new_password is not None:
            user.hashed_password = AuthService.hash_password(new_password)

        await db.commit()
        await db.refresh(user)
        return user

    @classmethod
    async def delete_account(
        cls,
        db: AsyncSession,
        user: UserOrm,
        current_password: str,
    ) -> None:
        cls._verify_current_password(user, current_password)

        user.is_active = False
        user.team_id = None
        user.email = f"deleted_{user.id}_{uuid.uuid4().hex[:12]}@deleted.local"

        await db.commit()
