from fastapi import APIRouter, HTTPException, Response, status

from backend.src.api.dependencies import CurrentUser, DBDep
from backend.src.config import settings
from backend.src.models.users import UserOrm
from backend.src.schemas.users import UserCreate, UserGet, UserLogin, UserProfileDelete, UserProfileUpdate
from backend.src.services.auth import AuthService, EmailAlreadyRegisteredError, InvalidCredentialsError
from backend.src.services.users import InvalidCurrentPasswordError, UserService


router = APIRouter(prefix="/auth", tags=["Авторизация и аутентификация"])


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AuthService.cookie_name,
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )


@router.post("/register", response_model=UserGet, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: DBDep, response: Response) -> UserOrm:
    try:
        user = await AuthService.register(db, data)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже зарегистрирован",
        )

    token = AuthService.create_access_token(user.id)
    _set_auth_cookie(response, token)
    return user


@router.post("/login", response_model=UserGet)
async def login(data: UserLogin, db: DBDep, response: Response) -> UserOrm:
    try:
        user = await AuthService.login(db, data.email, data.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    token = AuthService.create_access_token(user.id)
    _set_auth_cookie(response, token)
    return user


@router.get("/me", response_model=UserGet)
async def get_me(current_user: CurrentUser) -> UserOrm:
    return current_user


@router.patch("/me", response_model=UserGet)
async def update_profile(
    data: UserProfileUpdate,
    current_user: CurrentUser,
    db: DBDep,
) -> UserOrm:
    try:
        return await UserService.update_profile(db, current_user, data)
    except InvalidCurrentPasswordError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный пароль",
        )
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже зарегистрирован",
        )


@router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_account(
    data: UserProfileDelete,
    current_user: CurrentUser,
    db: DBDep,
    response: Response,
) -> dict[str, str]:
    try:
        await UserService.delete_account(db, current_user, data.current_password)
    except InvalidCurrentPasswordError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный пароль",
        )

    response.delete_cookie(key=AuthService.cookie_name)
    return {"detail": "Аккаунт удалён"}


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(key=AuthService.cookie_name)
    return {"detail": "Выход выполнен"}
