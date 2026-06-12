from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from backend.src.models.enums import UserRole
from backend.src.services.teams import (
    AlreadyInTeamError,
    CannotAssignRoleError,
    CannotRemoveOwnerError,
    MemberNotFoundError,
    TeamAccessDeniedError,
    TeamNotFoundError,
    TeamService,
)
from tests.conftest import auth_as, make_team, make_user


@pytest.mark.asyncio
async def test_create_team_requires_admin(client: AsyncClient, auth_as) -> None:
    auth_as(client, make_user(email="regular@example.com"))
    response = await client.post("/teams", json={"name": "No Access Team"})
    assert response.status_code == 403


@pytest.mark.asyncio
@patch.object(TeamService, "create", new_callable=AsyncMock)
async def test_create_team_success(
    mock_create: AsyncMock,
    client: AsyncClient,
    auth_as,
    admin_user,
) -> None:
    team = make_team(name="Alpha Team", owner_id=admin_user.id)
    mock_create.return_value = team
    auth_as(client, admin_user)

    response = await client.post("/teams", json={"name": "Alpha Team"})
    assert response.status_code == 201
    assert response.json()["name"] == "Alpha Team"


@pytest.mark.asyncio
@patch.object(TeamService, "join_by_code", new_callable=AsyncMock)
@patch.object(TeamService, "create", new_callable=AsyncMock)
async def test_join_team_success(
    mock_create: AsyncMock,
    mock_join: AsyncMock,
    client: AsyncClient,
    auth_as,
    admin_user,
) -> None:
    team = make_team(code="JOIN0001", owner_id=admin_user.id)
    member = make_user(user_id=10, email="joiner@example.com", team_id=team.id)
    mock_create.return_value = team
    mock_join.return_value = member

    auth_as(client, admin_user)
    team_response = await client.post("/teams", json={"name": "Join Team"})
    team_data = team_response.json()

    auth_as(client, make_user(user_id=10, email="joiner@example.com"))
    response = await client.post("/teams/join", json={"code": team_data["code"]})
    assert response.status_code == 200
    assert response.json()["team_id"] == team.id


@pytest.mark.asyncio
@patch.object(TeamService, "join_by_code", new_callable=AsyncMock)
async def test_join_team_invalid_code(mock_join: AsyncMock, client: AsyncClient, auth_as) -> None:
    mock_join.side_effect = TeamNotFoundError
    auth_as(client, make_user(email="badcode@example.com"))
    response = await client.post("/teams/join", json={"code": "BADCODE1"})
    assert response.status_code == 404


@pytest.mark.asyncio
@patch.object(TeamService, "join_by_code", new_callable=AsyncMock)
async def test_join_team_already_in_team(
    mock_join: AsyncMock,
    client: AsyncClient,
    auth_as,
    team_setup,
) -> None:
    mock_join.side_effect = AlreadyInTeamError
    auth_as(client, team_setup["member_user"])
    response = await client.post("/teams/join", json={"code": team_setup["team"]["code"]})
    assert response.status_code == 400


@pytest.mark.asyncio
@patch.object(TeamService, "get_team_detail", new_callable=AsyncMock)
async def test_get_team_detail(
    mock_detail: AsyncMock,
    client: AsyncClient,
    auth_as,
    team_setup,
) -> None:
    members = [team_setup["admin_user"], team_setup["manager_user"], team_setup["member_user"]]
    mock_detail.return_value = (team_setup["team_obj"], members)
    auth_as(client, team_setup["member_user"])

    response = await client.get(f"/teams/{team_setup['team']['id']}")
    assert response.status_code == 200
    assert len(response.json()["members"]) == 3


@pytest.mark.asyncio
@patch.object(TeamService, "get_team_detail", new_callable=AsyncMock)
async def test_get_team_access_denied(mock_detail: AsyncMock, client: AsyncClient, auth_as) -> None:
    mock_detail.side_effect = TeamAccessDeniedError
    auth_as(client, make_user(email="outsider@example.com"))
    response = await client.get("/teams/1")
    assert response.status_code == 403


@pytest.mark.asyncio
@patch.object(TeamService, "assign_role", new_callable=AsyncMock)
async def test_assign_member_role(
    mock_assign: AsyncMock,
    client: AsyncClient,
    auth_as,
    team_setup,
) -> None:
    updated = make_user(
        user_id=team_setup["member"]["id"],
        email=team_setup["member"]["email"],
        role=UserRole.MANAGER,
        team_id=1,
    )
    mock_assign.return_value = updated
    auth_as(client, team_setup["admin_user"])

    response = await client.patch(
        f"/teams/{team_setup['team']['id']}/members/{team_setup['member']['id']}/role",
        json={"role": UserRole.MANAGER.value},
    )
    assert response.status_code == 200
    assert response.json()["role"] == UserRole.MANAGER.value


@pytest.mark.asyncio
@patch.object(TeamService, "remove_member", new_callable=AsyncMock)
async def test_remove_team_member(
    mock_remove: AsyncMock,
    client: AsyncClient,
    auth_as,
    team_setup,
) -> None:
    mock_remove.return_value = None
    auth_as(client, team_setup["admin_user"])
    response = await client.delete(
        f"/teams/{team_setup['team']['id']}/members/{team_setup['member']['id']}",
    )
    assert response.status_code == 200


@pytest.mark.asyncio
@patch.object(TeamService, "remove_member", new_callable=AsyncMock)
async def test_cannot_remove_owner(
    mock_remove: AsyncMock,
    client: AsyncClient,
    auth_as,
    team_setup,
) -> None:
    mock_remove.side_effect = CannotRemoveOwnerError
    auth_as(client, team_setup["manager_user"])
    response = await client.delete(
        f"/teams/{team_setup['team']['id']}/members/{team_setup['admin']['id']}",
    )
    assert response.status_code == 400
