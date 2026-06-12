from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from backend.src.services.auth import AuthService, EmailAlreadyRegisteredError, InvalidCredentialsError
from backend.src.services.users import InvalidCurrentPasswordError, UserService
from tests.conftest import make_user


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient, mock_db: AsyncMock) -> None:
    mock_db.execute = AsyncMock()
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_check_db_failure(client: AsyncClient, mock_db: AsyncMock) -> None:
    mock_db.execute = AsyncMock(side_effect=OSError("db down"))
    response = await client.get("/health")
    assert response.status_code == 500


@pytest.mark.asyncio
@patch.object(AuthService, "register", new_callable=AsyncMock)
async def test_register_success(mock_register: AsyncMock, client: AsyncClient) -> None:
    user = make_user(email="newuser@example.com")
    mock_register.return_value = user

    response = await client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "password123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    assert response.status_code == 201
    assert response.json()["email"] == "newuser@example.com"
    assert client.cookies.get("access_token") is not None


@pytest.mark.asyncio
@patch.object(AuthService, "register", new_callable=AsyncMock)
async def test_register_duplicate_email(mock_register: AsyncMock, client: AsyncClient) -> None:
    mock_register.side_effect = EmailAlreadyRegisteredError
    response = await client.post(
        "/auth/register",
        json={
            "email": "dup@example.com",
            "password": "password123",
            "first_name": "Dup",
            "last_name": "User",
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
@patch.object(AuthService, "login", new_callable=AsyncMock)
async def test_login_success(mock_login: AsyncMock, client: AsyncClient) -> None:
    user = make_user(email="login@example.com")
    mock_login.return_value = user

    response = await client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert client.cookies.get("access_token") is not None


@pytest.mark.asyncio
@patch.object(AuthService, "login", new_callable=AsyncMock)
async def test_login_invalid_credentials(mock_login: AsyncMock, client: AsyncClient) -> None:
    mock_login.side_effect = InvalidCredentialsError
    response = await client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient, auth_as) -> None:
    user = make_user(email="me@example.com", first_name="Me", last_name="Self")
    auth_as(client, user)
    response = await client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


@pytest.mark.asyncio
@patch.object(UserService, "update_profile", new_callable=AsyncMock)
async def test_update_profile(mock_update: AsyncMock, client: AsyncClient, auth_as) -> None:
    user = make_user(email="profile@example.com")
    updated = make_user(email="profile@example.com", first_name="Updated", last_name="Name")
    auth_as(client, user)
    mock_update.return_value = updated

    response = await client.patch("/auth/me", json={"first_name": "Updated", "last_name": "Name"})
    assert response.status_code == 200
    assert response.json()["first_name"] == "Updated"


@pytest.mark.asyncio
@patch.object(UserService, "update_profile", new_callable=AsyncMock)
async def test_update_profile_wrong_password(mock_update: AsyncMock, client: AsyncClient, auth_as) -> None:
    auth_as(client, make_user(email="wrongcurrent@example.com"))
    mock_update.side_effect = InvalidCurrentPasswordError

    response = await client.patch(
        "/auth/me",
        json={"current_password": "wrong", "new_password": "newpassword2"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
@patch.object(UserService, "delete_account", new_callable=AsyncMock)
async def test_delete_account(mock_delete: AsyncMock, client: AsyncClient, auth_as) -> None:
    auth_as(client, make_user(email="delete@example.com"))
    mock_delete.return_value = None

    response = await client.request(
        "DELETE",
        "/auth/me",
        json={"current_password": "deletepass1"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, auth_as) -> None:
    auth_as(client, make_user(email="logout@example.com"))
    response = await client.post("/auth/logout")
    assert response.status_code == 200
    assert response.json()["detail"] == "Выход выполнен"
