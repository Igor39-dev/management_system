from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from backend.src.models.enums import TaskStatus
from backend.src.services.tasks import (
    AssigneeNotInTeamError,
    NotInTeamError,
    TaskAccessDeniedError,
    TaskNotFoundError,
    TaskService,
)
from tests.conftest import auth_as, future_datetime, make_task, make_user


@pytest.mark.asyncio
@patch.object(TaskService, "create", new_callable=AsyncMock)
async def test_create_task_requires_team(mock_create: AsyncMock, client: AsyncClient, auth_as) -> None:
    mock_create.side_effect = NotInTeamError
    auth_as(client, make_user(email="noteam@example.com", team_id=None))
    response = await client.post("/tasks", json={"title": "Lonely task"})
    assert response.status_code == 400


@pytest.mark.asyncio
@patch.object(TaskService, "create", new_callable=AsyncMock)
async def test_create_task_requires_manager(mock_create: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_create.side_effect = TaskAccessDeniedError
    auth_as(client, team_setup["member_user"])
    response = await client.post("/tasks", json={"title": "Member task"})
    assert response.status_code == 403


@pytest.mark.asyncio
@patch.object(TaskService, "create", new_callable=AsyncMock)
async def test_create_task_success(mock_create: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    task = make_task(
        task_id=1,
        title="Important task",
        assignee_id=team_setup["member"]["id"],
        team_id=1,
        creator_id=team_setup["manager"]["id"],
    )
    mock_create.return_value = task
    auth_as(client, team_setup["manager_user"])

    response = await client.post(
        "/tasks",
        json={
            "title": "Important task",
            "assignee_id": team_setup["member"]["id"],
            "deadline": future_datetime(48).isoformat(),
        },
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Important task"


@pytest.mark.asyncio
@patch.object(TaskService, "list_tasks", new_callable=AsyncMock)
async def test_list_tasks(mock_list: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_list.return_value = [
        make_task(task_id=1, title="Task 1"),
        make_task(task_id=2, title="Task 2"),
    ]
    auth_as(client, team_setup["member_user"])
    response = await client.get("/tasks")
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
@patch.object(TaskService, "list_tasks", new_callable=AsyncMock)
async def test_list_tasks_assigned_to_me(mock_list: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_list.return_value = [make_task(task_id=1, title="Mine", assignee_id=3)]
    auth_as(client, team_setup["member_user"])
    response = await client.get("/tasks", params={"assigned_to_me": True})
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
@patch.object(TaskService, "get_task", new_callable=AsyncMock)
async def test_get_task(mock_get: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_get.return_value = make_task(task_id=1, title="View me")
    auth_as(client, team_setup["member_user"])
    response = await client.get("/tasks/1")
    assert response.status_code == 200


@pytest.mark.asyncio
@patch.object(TaskService, "update", new_callable=AsyncMock)
async def test_update_task_by_manager(mock_update: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_update.return_value = make_task(
        task_id=1,
        title="New title",
        status=TaskStatus.IN_PROGRESS,
    )
    auth_as(client, team_setup["manager_user"])
    response = await client.patch(
        "/tasks/1",
        json={"title": "New title", "status": TaskStatus.IN_PROGRESS.value},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
@patch.object(TaskService, "update", new_callable=AsyncMock)
async def test_update_task_status_by_assignee(mock_update: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_update.return_value = make_task(task_id=1, status=TaskStatus.DONE)
    auth_as(client, team_setup["member_user"])
    response = await client.patch("/tasks/1", json={"status": TaskStatus.DONE.value})
    assert response.status_code == 200


@pytest.mark.asyncio
@patch.object(TaskService, "update", new_callable=AsyncMock)
async def test_assignee_cannot_change_title(mock_update: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_update.side_effect = TaskAccessDeniedError
    auth_as(client, team_setup["member_user"])
    response = await client.patch("/tasks/1", json={"title": "Hacked"})
    assert response.status_code == 403


@pytest.mark.asyncio
@patch.object(TaskService, "delete", new_callable=AsyncMock)
@patch.object(TaskService, "get_task", new_callable=AsyncMock)
async def test_delete_task(
    mock_get: AsyncMock,
    mock_delete: AsyncMock,
    client: AsyncClient,
    auth_as,
    team_setup,
) -> None:
    mock_delete.return_value = None
    mock_get.side_effect = TaskNotFoundError
    auth_as(client, team_setup["manager_user"])

    delete_response = await client.delete("/tasks/1")
    assert delete_response.status_code == 200

    get_response = await client.get("/tasks/1")
    assert get_response.status_code == 404


@pytest.mark.asyncio
@patch.object(TaskService, "add_comment", new_callable=AsyncMock)
@patch.object(TaskService, "list_comments", new_callable=AsyncMock)
async def test_task_comments(
    mock_list: AsyncMock,
    mock_add: AsyncMock,
    client: AsyncClient,
    auth_as,
    team_setup,
) -> None:
    from tests.conftest import make_comment

    comment = make_comment(text="Working on it")
    mock_add.return_value = comment
    mock_list.return_value = [comment]
    auth_as(client, team_setup["member_user"])

    add_response = await client.post("/tasks/1/comments", json={"text": "Working on it"})
    assert add_response.status_code == 201

    list_response = await client.get("/tasks/1/comments")
    assert len(list_response.json()) == 1


@pytest.mark.asyncio
@patch.object(TaskService, "create", new_callable=AsyncMock)
async def test_create_task_invalid_assignee(mock_create: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_create.side_effect = AssigneeNotInTeamError
    auth_as(client, team_setup["manager_user"])
    response = await client.post("/tasks", json={"title": "Bad assignee", "assignee_id": 99999})
    assert response.status_code == 400
