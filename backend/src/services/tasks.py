from sqlalchemy.ext.asyncio import AsyncSession

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
