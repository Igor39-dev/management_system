from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.src.models.enums import TaskStatus, UserRole
from backend.src.services.teams import (
    AlreadyInTeamError,
    MemberNotFoundError,
    TeamAccessDeniedError,
    TeamNotFoundError,
    TeamService,
)
from backend.src.services.tasks import NotInTeamError, TaskAccessDeniedError, TaskService
from backend.src.services.meetings import InvalidMeetingTimeError, MeetingService, NotInTeamError as MeetingNotInTeamError
from backend.src.services.evaluations import EvaluationAccessDeniedError, EvaluationService
from backend.src.services.calendar import CalendarService
from backend.src.schemas.tasks import TaskCreate
from backend.src.schemas.teams import TeamCreate
from backend.src.schemas.meetings import MeetingCreate
from backend.src.schemas.evaluations import EvaluationCreate
from tests.conftest import future_datetime, make_task, make_team, make_user


@pytest.mark.asyncio
async def test_team_service_can_access_team() -> None:
    admin = make_user(role=UserRole.ADMIN)
    team = make_team(owner_id=99)
    assert TeamService.can_access_team(admin, team)
    assert TeamService.can_manage_team(admin, team)


@pytest.mark.asyncio
async def test_team_service_create(mock_db: AsyncMock) -> None:
    admin = make_user(user_id=1, role=UserRole.ADMIN)
    mock_db.get = AsyncMock(return_value=None)
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)

    async def refresh_side_effect(obj):
        obj.id = 1
        obj.code = "ABCD1234"

    mock_db.refresh = AsyncMock(side_effect=refresh_side_effect)

    team = await TeamService.create(mock_db, admin, TeamCreate(name="New Team"))
    assert team.name == "New Team"
    mock_db.add.assert_called()


@pytest.mark.asyncio
async def test_team_service_join_already_in_team(mock_db: AsyncMock) -> None:
    user = make_user(team_id=1)
    with pytest.raises(AlreadyInTeamError):
        await TeamService.join_by_code(mock_db, user, "CODE1234")


@pytest.mark.asyncio
async def test_task_service_create_not_in_team(mock_db: AsyncMock) -> None:
    user = make_user(team_id=None)
    with pytest.raises(NotInTeamError):
        await TaskService.create(mock_db, user, TaskCreate(title="X"))


@pytest.mark.asyncio
async def test_task_service_create_access_denied(mock_db: AsyncMock) -> None:
    user = make_user(team_id=1, role=UserRole.USER)
    team = make_team(team_id=1, owner_id=99)
    mock_db.get = AsyncMock(return_value=team)

    with pytest.raises(TaskAccessDeniedError):
        await TaskService.create(mock_db, user, TaskCreate(title="X"))


@pytest.mark.asyncio
async def test_meeting_service_invalid_time() -> None:
    with pytest.raises(InvalidMeetingTimeError):
        MeetingService._validate_time_range(future_datetime(1), future_datetime(1))


@pytest.mark.asyncio
async def test_meeting_service_create_not_in_team(mock_db: AsyncMock) -> None:
    user = make_user(team_id=None)
    start = future_datetime(24)
    end = start + timedelta(hours=1)
    data = MeetingCreate(title="M", start_at=start, end_at=end)
    with pytest.raises(MeetingNotInTeamError):
        await MeetingService.create(mock_db, user, data)


@pytest.mark.asyncio
@patch("backend.src.services.evaluations.TaskService.get_task", new_callable=AsyncMock)
async def test_evaluation_service_access_denied(mock_get_task: AsyncMock, mock_db: AsyncMock) -> None:
    member = make_user(user_id=3, team_id=1, role=UserRole.USER)
    task = make_task(task_id=1, team_id=1)
    mock_get_task.return_value = task
    mock_db.get = AsyncMock(return_value=make_team(team_id=1, owner_id=99))

    with pytest.raises(EvaluationAccessDeniedError):
        await EvaluationService.create(mock_db, member, 1, EvaluationCreate(score=5))


@pytest.mark.asyncio
async def test_calendar_service_month_bounds() -> None:
    start, end = CalendarService._month_bounds(2026, 6)
    assert start.month == 6
    assert end.month == 6


@pytest.mark.asyncio
async def test_team_service_get_team_not_found(mock_db: AsyncMock) -> None:
    mock_db.get = AsyncMock(return_value=None)
    user = make_user(role=UserRole.ADMIN)
    with pytest.raises(TeamNotFoundError):
        await TeamService.get_team_detail(mock_db, user, 999)


@pytest.mark.asyncio
async def test_team_service_access_denied(mock_db: AsyncMock) -> None:
    team = make_team(team_id=1, owner_id=99)
    outsider = make_user(team_id=None)
    mock_db.get = AsyncMock(return_value=team)
    with pytest.raises(TeamAccessDeniedError):
        await TeamService.get_team_detail(mock_db, outsider, 1)
