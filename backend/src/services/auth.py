from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
import jwt
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.config import settings
from backend.src.models.users import UserOrm
from backend.src.schemas.users import UserCreate


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class AuthService:
    password_hash = PasswordHash.recommended()
    cookie_name = "access_token"

    @classmethod
    def hash_password(cls, password: str) -> str:
        return cls.password_hash.hash(password)

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        return cls.password_hash.verify(plain_password, hashed_password)

    @classmethod
    def create_access_token(cls, user_id: int) -> str:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {"sub": str(user_id), "exp": expire}
        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    @classmethod
    def decode_access_token(cls, token: str) -> int | None:
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return int(payload["sub"])
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    @classmethod
    async def get_user_by_email(cls, db: AsyncSession, email: str) -> UserOrm | None:
        result = await db.execute(select(UserOrm).where(UserOrm.email == email))
        return result.scalar_one_or_none()

    @classmethod
    async def register(cls, db: AsyncSession, data: UserCreate) -> UserOrm:
        existing_user = await cls.get_user_by_email(db, data.email)
        if existing_user is not None and existing_user.is_active:
            raise EmailAlreadyRegisteredError

        user = UserOrm(
            email=data.email,
            hashed_password=cls.hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
        )
        db.add(user)
        await db.commit()
        return user

    @classmethod
    async def login(cls, db: AsyncSession, email: str, password: str) -> UserOrm:
        user = await cls.get_user_by_email(db, email)
        if user is None or not cls.verify_password(password, user.hashed_password):
            raise InvalidCredentialsError
        if not user.is_active:
            raise InvalidCredentialsError
        return user

    @classmethod
    async def get_user_by_id(cls, db: AsyncSession, user_id: int) -> UserOrm | None:
        return await db.get(UserOrm, user_id)
