from collections.abc import AsyncGenerator, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from backend.src.api.dependencies import get_current_user, get_db_session
from backend.src.main import app
from backend.src.models.enums import TaskStatus, UserRole
from backend.src.models.evaluations import EvaluationOrm
from backend.src.models.meetings import MeetingOrm
from backend.src.models.tasks import TaskCommentOrm, TaskOrm
from backend.src.models.teams import TeamOrm
from backend.src.models.users import UserOrm
from backend.src.services.auth import AuthService


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def make_user(
    *,
    user_id: int = 1,
    email: str = "user@example.com",
    password: str = "password123",
    first_name: str = "Test",
    last_name: str = "User",
    role: UserRole = UserRole.USER,
    team_id: int | None = None,
    is_active: bool = True,
    is_verified: bool = False,
) -> UserOrm:
    user = UserOrm(
        id=user_id,
        email=email,
        hashed_password=AuthService.hash_password(password),
        first_name=first_name,
        last_name=last_name,
        role=role,
        team_id=team_id,
        is_active=is_active,
        is_verified=is_verified,
    )
    user.created_at = _now()
    user.updated_at = _now()
    return user


def make_team(
    *,
    team_id: int = 1,
    name: str = "Test Team",
    code: str = "TEAM0001",
    owner_id: int = 1,
) -> TeamOrm:
    team = TeamOrm(id=team_id, name=name, code=code, owner_id=owner_id)
    team.created_at = _now()
    team.updated_at = _now()
    return team


def make_task(
    *,
    task_id: int = 1,
    title: str = "Task",
    team_id: int = 1,
    creator_id: int = 1,
    assignee_id: int | None = None,
    status: TaskStatus = TaskStatus.OPEN,
    deadline: datetime | None = None,
    description: str | None = None,
) -> TaskOrm:
    task = TaskOrm(
        id=task_id,
        title=title,
        description=description,
        status=status,
        deadline=deadline,
        team_id=team_id,
        creator_id=creator_id,
        assignee_id=assignee_id,
    )
    task.created_at = _now()
    task.updated_at = _now()
    return task


def make_comment(
    *,
    comment_id: int = 1,
    task_id: int = 1,
    author_id: int = 1,
    text: str = "Comment",
) -> TaskCommentOrm:
    comment = TaskCommentOrm(id=comment_id, task_id=task_id, author_id=author_id, text=text)
    comment.created_at = _now()
    comment.updated_at = _now()
    return comment


def make_meeting(
    *,
    meeting_id: int = 1,
    title: str = "Meeting",
    team_id: int = 1,
    organizer_id: int = 1,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    is_cancelled: bool = False,
    participants: list[UserOrm] | None = None,
) -> MeetingOrm:
    start = start_at or _now() + timedelta(hours=24)
    end = end_at or start + timedelta(hours=1)
    meeting = MeetingOrm(
        id=meeting_id,
        title=title,
        description=None,
        start_at=start,
        end_at=end,
        is_cancelled=is_cancelled,
        team_id=team_id,
        organizer_id=organizer_id,
    )
    meeting.participants = participants or []
    meeting.created_at = _now()
    meeting.updated_at = _now()
    return meeting


def make_evaluation(
    *,
    evaluation_id: int = 1,
    task_id: int = 1,
    evaluator_id: int = 1,
    score: int = 5,
) -> EvaluationOrm:
    evaluation = EvaluationOrm(
        id=evaluation_id,
        task_id=task_id,
        evaluator_id=evaluator_id,
        score=score,
    )
    evaluation.created_at = _now()
    evaluation.updated_at = _now()
    return evaluation


def user_to_dict(user: UserOrm) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role.value,
        "team_id": user.team_id,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
    }


def team_to_dict(team: TeamOrm) -> dict[str, Any]:
    return {
        "id": team.id,
        "name": team.name,
        "code": team.code,
        "owner_id": team.owner_id,
        "created_at": team.created_at.isoformat(),
        "updated_at": team.updated_at.isoformat(),
    }


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.add = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    return session


@pytest.fixture
async def client(mock_db: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncMock, None]:
        yield mock_db

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client

    app.dependency_overrides.clear()


def authenticate(client: AsyncClient, user: UserOrm) -> None:
    token = AuthService.create_access_token(user.id)
    client.cookies.set(AuthService.cookie_name, token)


def override_current_user(user: UserOrm) -> None:
    async def _get_current_user() -> UserOrm:
        return user

    app.dependency_overrides[get_current_user] = _get_current_user


def clear_current_user_override() -> None:
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def auth_as() -> Callable[[AsyncClient, UserOrm], None]:
    def _auth_as(client: AsyncClient, user: UserOrm) -> None:
        authenticate(client, user)
        override_current_user(user)

    yield _auth_as
    clear_current_user_override()


@pytest.fixture
def admin_user() -> UserOrm:
    return make_user(
        user_id=1,
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
    )


@pytest.fixture
def team_setup() -> dict[str, Any]:
    admin = make_user(
        user_id=1,
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        team_id=1,
    )
    manager = make_user(
        user_id=2,
        email="manager@example.com",
        first_name="Team",
        last_name="Manager",
        role=UserRole.MANAGER,
        team_id=1,
    )
    member = make_user(
        user_id=3,
        email="member@example.com",
        first_name="Team",
        last_name="Member",
        role=UserRole.USER,
        team_id=1,
    )
    team = make_team(team_id=1, owner_id=admin.id, code="TEAM0001")
    return {
        "admin": user_to_dict(admin),
        "manager": user_to_dict(manager),
        "member": user_to_dict(member),
        "team": team_to_dict(team),
        "admin_user": admin,
        "manager_user": manager,
        "member_user": member,
        "team_obj": team,
    }


def future_datetime(hours: int = 1) -> datetime:
    return _now() + timedelta(hours=hours)


def future_meeting_range(hours_from_now: int = 24, duration_hours: int = 1) -> tuple[datetime, datetime]:
    start = future_datetime(hours_from_now)
    end = start + timedelta(hours=duration_hours)
    return start, end
