import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.src.services.auth import AuthService, EmailAlreadyRegisteredError, InvalidCredentialsError
from backend.src.schemas.users import UserCreate
from tests.conftest import make_user


@pytest.mark.asyncio
async def test_hash_and_verify_password() -> None:
    hashed = AuthService.hash_password("secret123")
    assert AuthService.verify_password("secret123", hashed)
    assert not AuthService.verify_password("wrong", hashed)


@pytest.mark.asyncio
async def test_create_and_decode_access_token() -> None:
    token = AuthService.create_access_token(user_id=42)
    assert AuthService.decode_access_token(token) == 42


@pytest.mark.asyncio
async def test_get_user_by_email(mock_db: AsyncMock) -> None:
    user = make_user(email="lookup@example.com")
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=result)

    found = await AuthService.get_user_by_email(mock_db, "lookup@example.com")
    assert found is user


@pytest.mark.asyncio
async def test_register_and_login_service(mock_db: AsyncMock) -> None:
    empty_result = MagicMock()
    empty_result.scalar_one_or_none.return_value = None

    user = make_user(email="service@example.com")
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    mock_db.execute = AsyncMock(side_effect=[empty_result, user_result])

    async def refresh_side_effect(obj) -> None:
        if getattr(obj, "id", None) is None:
            obj.id = user.id

    mock_db.refresh = AsyncMock(side_effect=refresh_side_effect)

    created = await AuthService.register(
        mock_db,
        UserCreate(email="service@example.com", password="password123", first_name="S", last_name="U"),
    )
    assert created.email == "service@example.com"

    logged_in = await AuthService.login(mock_db, "service@example.com", "password123")
    assert logged_in.email == user.email


@pytest.mark.asyncio
async def test_register_duplicate_active_user(mock_db: AsyncMock) -> None:
    existing = make_user(email="dup@example.com")
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing
    mock_db.execute = AsyncMock(return_value=result)

    with pytest.raises(EmailAlreadyRegisteredError):
        await AuthService.register(
            mock_db,
            UserCreate(email="dup@example.com", password="password123"),
        )


@pytest.mark.asyncio
async def test_login_inactive_user(mock_db: AsyncMock) -> None:
    user = make_user(email="inactive@example.com", is_active=False)
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=result)

    with pytest.raises(InvalidCredentialsError):
        await AuthService.login(mock_db, "inactive@example.com", "password123")


@pytest.mark.asyncio
async def test_get_user_by_id(mock_db: AsyncMock) -> None:
    user = make_user(user_id=5)
    mock_db.get = AsyncMock(return_value=user)
    assert await AuthService.get_user_by_id(mock_db, 5) is user
