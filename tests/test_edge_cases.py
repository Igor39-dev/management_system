from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from backend.src.models.enums import TaskStatus, UserRole
from backend.src.services.auth import AuthService
from backend.src.services.meetings import MeetingNotFoundError, MeetingService, ParticipantNotInTeamError
from backend.src.services.tasks import TaskNotFoundError, TaskService
from backend.src.services.teams import CannotAssignRoleError, TeamNotFoundError, TeamService
from tests.conftest import auth_as, make_task, make_user


@pytest.mark.asyncio
async def test_invalid_token(client: AsyncClient) -> None:
    client.cookies.set(AuthService.cookie_name, "invalid.token.value")
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
@patch.object(TeamService, "get_team_detail", new_callable=AsyncMock)
async def test_team_not_found(mock_detail: AsyncMock, client: AsyncClient, auth_as, admin_user) -> None:
    mock_detail.side_effect = TeamNotFoundError
    auth_as(client, admin_user)
    response = await client.get("/teams/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
@patch.object(TaskService, "get_task", new_callable=AsyncMock)
async def test_task_not_found(mock_get: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_get.side_effect = TaskNotFoundError
    auth_as(client, team_setup["member_user"])
    response = await client.get("/tasks/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
@patch.object(TaskService, "list_tasks", new_callable=AsyncMock)
async def test_list_tasks_with_status_filter(
    mock_list: AsyncMock,
    client: AsyncClient,
    auth_as,
    team_setup,
) -> None:
    mock_list.return_value = [make_task(task_id=2, title="Done task", status=TaskStatus.DONE)]
    auth_as(client, team_setup["manager_user"])
    response = await client.get("/tasks", params={"status": TaskStatus.DONE.value})
    assert response.status_code == 200
    assert response.json()[0]["status"] == TaskStatus.DONE.value


@pytest.mark.asyncio
@patch.object(TeamService, "assign_role", new_callable=AsyncMock)
async def test_cannot_assign_admin_role_without_admin(
    mock_assign: AsyncMock,
    client: AsyncClient,
    auth_as,
    team_setup,
) -> None:
    mock_assign.side_effect = CannotAssignRoleError
    auth_as(client, team_setup["manager_user"])
    response = await client.patch(
        f"/teams/{team_setup['team']['id']}/members/{team_setup['member']['id']}/role",
        json={"role": UserRole.ADMIN.value},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
@patch.object(MeetingService, "get_meeting", new_callable=AsyncMock)
async def test_meeting_not_found(mock_get: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_get.side_effect = MeetingNotFoundError
    auth_as(client, team_setup["manager_user"])
    response = await client.get("/meetings/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
@patch.object(MeetingService, "create", new_callable=AsyncMock)
async def test_meeting_invalid_participant(
    mock_create: AsyncMock,
    client: AsyncClient,
    auth_as,
    team_setup,
) -> None:
    from tests.conftest import future_meeting_range

    mock_create.side_effect = ParticipantNotInTeamError
    auth_as(client, team_setup["manager_user"])
    start_at, end_at = future_meeting_range(200, 1)
    response = await client.post(
        "/meetings",
        json={
            "title": "Bad participant",
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "participant_ids": [99999],
        },
    )
    assert response.status_code == 400
