from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.models.enums import TaskStatus
from backend.src.models.tasks import TaskOrm
from backend.src.models.users import UserOrm
from backend.src.schemas.tasks import TaskCreate
from backend.src.services.teams import MemberNotFoundError, TeamService


class NotInTeamError(Exception):
    pass


class TaskAccessDeniedError(Exception):
    pass


class AssigneeNotInTeamError(Exception):
    pass


class TaskService:
    @classmethod
    async def create(cls, db: AsyncSession, creator: UserOrm, data: TaskCreate) -> TaskOrm:
        if creator.team_id is None:
            raise NotInTeamError

        team = await TeamService.get_by_id(db, creator.team_id)
        if team is None:
            raise NotInTeamError

        if not TeamService.can_manage_team(creator, team):
            raise TaskAccessDeniedError

        if data.assignee_id is not None:
            try:
                await TeamService._get_team_member(db, creator.team_id, data.assignee_id)
            except MemberNotFoundError:
                raise AssigneeNotInTeamError

        task = TaskOrm(
            title=data.title,
            description=data.description,
            deadline=data.deadline,
            team_id=creator.team_id,
            creator_id=creator.id,
            assignee_id=data.assignee_id,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task

    @classmethod
    async def list_tasks(
        cls,
        db: AsyncSession,
        user: UserOrm,
        status: TaskStatus | None = None,
        assignee_id: int | None = None,
        assigned_to_me: bool = False,
    ) -> list[TaskOrm]:
        if user.team_id is None:
            raise NotInTeamError

        stmt = select(TaskOrm).where(TaskOrm.team_id == user.team_id)

        if status is not None:
            stmt = stmt.where(TaskOrm.status == status)
        if assignee_id is not None:
            stmt = stmt.where(TaskOrm.assignee_id == assignee_id)
        if assigned_to_me:
            stmt = stmt.where(TaskOrm.assignee_id == user.id)

        stmt = stmt.order_by(TaskOrm.deadline.asc().nulls_last(), TaskOrm.id.desc())

        result = await db.execute(stmt)
        return list(result.scalars().all())
