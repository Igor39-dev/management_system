from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.database import session as session_factory
from backend.src.models.enums import UserRole
from backend.src.models.users import UserOrm
from backend.src.services.auth import AuthService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as db_session:
        yield db_session


DBDep = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(
    db: DBDep,
    access_token: Annotated[str | None, Cookie(alias=AuthService.cookie_name, include_in_schema=False)] = None,
) -> UserOrm:
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
        )

    user_id = AuthService.decode_access_token(access_token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
        )

    user = await AuthService.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    return user


CurrentUser = Annotated[UserOrm, Depends(get_current_user)]


async def get_current_admin(current_user: CurrentUser) -> UserOrm:
    if current_user.role != UserRole.ADMIN and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )
    return current_user


CurrentAdmin = Annotated[UserOrm, Depends(get_current_admin)]
