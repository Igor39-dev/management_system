from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from backend.src.services.evaluations import (
    EvaluationAccessDeniedError,
    EvaluationAlreadyExistsError,
    EvaluationNotFoundError,
    EvaluationService,
)
from backend.src.services.tasks import NotInTeamError
from tests.conftest import auth_as, make_evaluation, make_user


@pytest.mark.asyncio
@patch.object(EvaluationService, "create", new_callable=AsyncMock)
async def test_create_evaluation(mock_create: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_create.return_value = make_evaluation(task_id=1, score=5)
    auth_as(client, team_setup["manager_user"])
    response = await client.post("/tasks/1/evaluation", json={"score": 5})
    assert response.status_code == 201


@pytest.mark.asyncio
@patch.object(EvaluationService, "create", new_callable=AsyncMock)
async def test_create_evaluation_duplicate(mock_create: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_create.side_effect = EvaluationAlreadyExistsError
    auth_as(client, team_setup["manager_user"])
    response = await client.post("/tasks/1/evaluation", json={"score": 3})
    assert response.status_code == 400


@pytest.mark.asyncio
@patch.object(EvaluationService, "create", new_callable=AsyncMock)
async def test_create_evaluation_forbidden_for_member(
    mock_create: AsyncMock,
    client: AsyncClient,
    auth_as,
    team_setup,
) -> None:
    mock_create.side_effect = EvaluationAccessDeniedError
    auth_as(client, team_setup["member_user"])
    response = await client.post("/tasks/1/evaluation", json={"score": 5})
    assert response.status_code == 403


@pytest.mark.asyncio
@patch.object(EvaluationService, "get_for_task", new_callable=AsyncMock)
async def test_get_task_evaluation(mock_get: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_get.return_value = make_evaluation(task_id=1, score=3)
    auth_as(client, team_setup["member_user"])
    response = await client.get("/tasks/1/evaluation")
    assert response.status_code == 200
    assert response.json()["score"] == 3


@pytest.mark.asyncio
@patch.object(EvaluationService, "update", new_callable=AsyncMock)
async def test_update_evaluation(mock_update: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_update.return_value = make_evaluation(task_id=1, score=4)
    auth_as(client, team_setup["manager_user"])
    response = await client.patch("/tasks/1/evaluation", json={"score": 4})
    assert response.status_code == 200


@pytest.mark.asyncio
@patch.object(EvaluationService, "list_for_user", new_callable=AsyncMock)
async def test_list_my_evaluations(mock_list: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_list.return_value = [make_evaluation(score=5)]
    auth_as(client, team_setup["member_user"])
    response = await client.get("/evaluations/me")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
@patch.object(EvaluationService, "get_average_for_user", new_callable=AsyncMock)
async def test_average_score(mock_avg: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_avg.return_value = (3.0, 2)
    auth_as(client, team_setup["member_user"])
    response = await client.get("/evaluations/me/average")
    assert response.status_code == 200
    assert response.json()["average_score"] == 3.0


@pytest.mark.asyncio
@patch.object(EvaluationService, "get_average_for_user", new_callable=AsyncMock)
async def test_average_score_empty(mock_avg: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_avg.return_value = (None, 0)
    auth_as(client, team_setup["member_user"])
    response = await client.get("/evaluations/me/average")
    assert response.json()["count"] == 0


@pytest.mark.asyncio
@patch.object(EvaluationService, "list_for_user", new_callable=AsyncMock)
async def test_evaluations_not_in_team(mock_list: AsyncMock, client: AsyncClient, auth_as) -> None:
    mock_list.side_effect = NotInTeamError
    auth_as(client, make_user(email="noeval@example.com", team_id=None))
    response = await client.get("/evaluations/me")
    assert response.status_code == 400


@pytest.mark.asyncio
@patch.object(EvaluationService, "get_for_task", new_callable=AsyncMock)
async def test_evaluation_not_found(mock_get: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_get.side_effect = EvaluationNotFoundError
    auth_as(client, team_setup["member_user"])
    response = await client.get("/tasks/1/evaluation")
    assert response.status_code == 404
