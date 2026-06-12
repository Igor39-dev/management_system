from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from backend.src.services.meetings import (
    InvalidMeetingTimeError,
    MeetingAccessDeniedError,
    MeetingNotFoundError,
    MeetingService,
    MeetingTimeConflictError,
    NotInTeamError,
    ParticipantNotInTeamError,
)
from tests.conftest import auth_as, future_meeting_range, make_meeting, make_user


@pytest.mark.asyncio
@patch.object(MeetingService, "create", new_callable=AsyncMock)
async def test_create_meeting_success(mock_create: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    start_at, end_at = future_meeting_range(24, 1)
    meeting = make_meeting(
        title="Sprint planning",
        organizer_id=team_setup["manager"]["id"],
        start_at=start_at,
        end_at=end_at,
        participants=[team_setup["member_user"]],
    )
    mock_create.return_value = meeting
    auth_as(client, team_setup["manager_user"])

    response = await client.post(
        "/meetings",
        json={
            "title": "Sprint planning",
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "participant_ids": [team_setup["member"]["id"]],
        },
    )
    assert response.status_code == 201
    assert team_setup["member"]["id"] in response.json()["participant_ids"]


@pytest.mark.asyncio
@patch.object(MeetingService, "create", new_callable=AsyncMock)
async def test_create_meeting_not_in_team(mock_create: AsyncMock, client: AsyncClient, auth_as) -> None:
    mock_create.side_effect = NotInTeamError
    auth_as(client, make_user(email="nomeeting@example.com", team_id=None))
    start_at, end_at = future_meeting_range()
    response = await client.post(
        "/meetings",
        json={
            "title": "Solo",
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "participant_ids": [],
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_meeting_invalid_time(client: AsyncClient, auth_as, team_setup) -> None:
    auth_as(client, team_setup["manager_user"])
    start_at, _ = future_meeting_range(24, 1)
    response = await client.post(
        "/meetings",
        json={
            "title": "Bad time",
            "start_at": start_at.isoformat(),
            "end_at": start_at.isoformat(),
            "participant_ids": [],
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@patch.object(MeetingService, "create", new_callable=AsyncMock)
async def test_create_meeting_time_conflict(mock_create: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_create.side_effect = [make_meeting(), MeetingTimeConflictError()]
    auth_as(client, team_setup["manager_user"])
    start_at, end_at = future_meeting_range(48, 2)
    overlap_start = start_at + timedelta(hours=1)

    first = await client.post(
        "/meetings",
        json={
            "title": "First",
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "participant_ids": [team_setup["member"]["id"]],
        },
    )
    assert first.status_code == 201

    second = await client.post(
        "/meetings",
        json={
            "title": "Conflict",
            "start_at": overlap_start.isoformat(),
            "end_at": end_at.isoformat(),
            "participant_ids": [team_setup["member"]["id"]],
        },
    )
    assert second.status_code == 400


@pytest.mark.asyncio
@patch.object(MeetingService, "list_meetings", new_callable=AsyncMock)
async def test_list_meetings(mock_list: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_list.return_value = [make_meeting(title="Listed meeting")]
    auth_as(client, team_setup["member_user"])
    response = await client.get("/meetings")
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
@patch.object(MeetingService, "get_meeting", new_callable=AsyncMock)
async def test_get_meeting(mock_get: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_get.return_value = make_meeting(meeting_id=1, title="Details")
    auth_as(client, team_setup["manager_user"])
    response = await client.get("/meetings/1")
    assert response.status_code == 200


@pytest.mark.asyncio
@patch.object(MeetingService, "update", new_callable=AsyncMock)
async def test_update_meeting(mock_update: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_update.return_value = make_meeting(meeting_id=1, title="After update")
    auth_as(client, team_setup["manager_user"])
    response = await client.patch("/meetings/1", json={"title": "After update"})
    assert response.status_code == 200


@pytest.mark.asyncio
@patch.object(MeetingService, "cancel", new_callable=AsyncMock)
async def test_cancel_meeting(mock_cancel: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_cancel.return_value = make_meeting(meeting_id=1, is_cancelled=True)
    auth_as(client, team_setup["manager_user"])
    response = await client.post("/meetings/1/cancel")
    assert response.status_code == 200
    assert response.json()["is_cancelled"] is True


@pytest.mark.asyncio
@patch.object(MeetingService, "get_meeting", new_callable=AsyncMock)
async def test_meeting_access_denied(mock_get: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    mock_get.side_effect = MeetingAccessDeniedError
    auth_as(client, team_setup["member_user"])
    response = await client.get("/meetings/99")
    assert response.status_code == 403
