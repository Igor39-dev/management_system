from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from backend.src.models.enums import CalendarEventType, TaskStatus
from backend.src.schemas.calendar import CalendarEvent
from backend.src.services.calendar import CalendarService
from backend.src.services.meetings import NotInTeamError
from tests.conftest import auth_as, future_datetime, future_meeting_range, make_user


@pytest.mark.asyncio
@patch.object(CalendarService, "get_month", new_callable=AsyncMock)
async def test_month_calendar(mock_month: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    deadline = future_datetime(24)
    start_at, end_at = future_meeting_range(24, 1)
    mock_month.return_value = [
        CalendarEvent(
            id=1,
            type=CalendarEventType.TASK,
            title="Calendar task",
            starts_at=deadline,
            status=TaskStatus.OPEN,
        ),
        CalendarEvent(
            id=1,
            type=CalendarEventType.MEETING,
            title="Calendar meeting",
            starts_at=start_at,
            ends_at=end_at,
        ),
    ]
    auth_as(client, team_setup["member_user"])

    response = await client.get(
        "/calendar/month",
        params={"year": deadline.year, "month": deadline.month},
    )
    assert response.status_code == 200
    assert len(response.json()["events"]) == 2


@pytest.mark.asyncio
@patch.object(CalendarService, "get_day", new_callable=AsyncMock)
async def test_day_calendar(mock_day: AsyncMock, client: AsyncClient, auth_as, team_setup) -> None:
    deadline = future_datetime(24)
    mock_day.return_value = [
        CalendarEvent(
            id=1,
            type=CalendarEventType.TASK,
            title="Day task",
            starts_at=deadline,
            status=TaskStatus.OPEN,
        ),
    ]
    auth_as(client, team_setup["member_user"])

    response = await client.get("/calendar/day", params={"day": deadline.date().isoformat()})
    assert response.status_code == 200
    assert response.json()["events"][0]["title"] == "Day task"


@pytest.mark.asyncio
@patch.object(CalendarService, "get_month", new_callable=AsyncMock)
async def test_calendar_not_in_team(mock_month: AsyncMock, client: AsyncClient, auth_as) -> None:
    mock_month.side_effect = NotInTeamError
    auth_as(client, make_user(email="nocal@example.com", team_id=None))
    response = await client.get("/calendar/month", params={"year": 2026, "month": 6})
    assert response.status_code == 400


@pytest.mark.asyncio
@patch.object(CalendarService, "get_month", new_callable=AsyncMock)
async def test_calendar_excludes_cancelled_meetings_by_default(
    mock_month: AsyncMock,
    client: AsyncClient,
    auth_as,
    team_setup,
) -> None:
    start_at, end_at = future_meeting_range(48, 1)

    async def side_effect(*args, **kwargs):
        if kwargs.get("include_cancelled_meetings"):
            return [
                CalendarEvent(
                    id=1,
                    type=CalendarEventType.MEETING,
                    title="Cancelled event",
                    starts_at=start_at,
                    ends_at=end_at,
                    is_cancelled=True,
                ),
            ]
        return []

    mock_month.side_effect = side_effect
    auth_as(client, team_setup["member_user"])

    response = await client.get(
        "/calendar/month",
        params={"year": start_at.year, "month": start_at.month},
    )
    assert "Cancelled event" not in [event["title"] for event in response.json()["events"]]

    response_with_cancelled = await client.get(
        "/calendar/month",
        params={
            "year": start_at.year,
            "month": start_at.month,
            "include_cancelled_meetings": True,
        },
    )
    assert "Cancelled event" in [event["title"] for event in response_with_cancelled.json()["events"]]
