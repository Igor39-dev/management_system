from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.models.enums import TaskStatus
from backend.src.models.tasks import TaskCommentOrm, TaskOrm
from backend.src.models.users import UserOrm
from backend.src.schemas.tasks import TaskCommentCreate, TaskCreate, TaskUpdate
from backend.src.services.teams import MemberNotFoundError, TeamService


class NotInTeamError(Exception):
    pass


class TaskAccessDeniedError(Exception):
    pass


class AssigneeNotInTeamError(Exception):
    pass


class TaskNotFoundError(Exception):
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

    @classmethod
    async def get_task(cls, db: AsyncSession, user: UserOrm, task_id: int) -> TaskOrm:
        task = await db.get(TaskOrm, task_id)
        if task is None:
            raise TaskNotFoundError

        team = await TeamService.get_by_id(db, task.team_id)
        if team is None:
            raise TaskNotFoundError

        if not TeamService.can_access_team(user, team):
            raise TaskAccessDeniedError

        return task

    @classmethod
    async def update(
        cls,
        db: AsyncSession,
        user: UserOrm,
        task_id: int,
        data: TaskUpdate,
    ) -> TaskOrm:
        task = await cls.get_task(db, user, task_id)

        team = await TeamService.get_by_id(db, task.team_id)
        if team is None:
            raise TaskNotFoundError

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return task

        can_manage = TeamService.can_manage_team(user, team)
        is_assignee = task.assignee_id == user.id

        if can_manage:
            assignee_id = update_data.get("assignee_id")
            if assignee_id is not None:
                try:
                    await TeamService._get_team_member(db, task.team_id, assignee_id)
                except MemberNotFoundError:
                    raise AssigneeNotInTeamError

            for field, value in update_data.items():
                setattr(task, field, value)
        elif is_assignee:
            if set(update_data.keys()) - {"status"}:
                raise TaskAccessDeniedError
            task.status = update_data["status"]
        else:
            raise TaskAccessDeniedError

        await db.commit()
        await db.refresh(task)
        return task

    @classmethod
    async def delete(cls, db: AsyncSession, user: UserOrm, task_id: int) -> None:
        task = await cls.get_task(db, user, task_id)

        team = await TeamService.get_by_id(db, task.team_id)
        if team is None:
            raise TaskNotFoundError

        if not TeamService.can_manage_team(user, team):
            raise TaskAccessDeniedError

        await db.delete(task)
        await db.commit()

    @classmethod
    async def list_comments(
        cls,
        db: AsyncSession,
        user: UserOrm,
        task_id: int,
    ) -> list[TaskCommentOrm]:
        await cls.get_task(db, user, task_id)

        stmt = (
            select(TaskCommentOrm)
            .where(TaskCommentOrm.task_id == task_id)
            .order_by(TaskCommentOrm.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def add_comment(
        cls,
        db: AsyncSession,
        user: UserOrm,
        task_id: int,
        data: TaskCommentCreate,
    ) -> TaskCommentOrm:
        await cls.get_task(db, user, task_id)

        comment = TaskCommentOrm(
            task_id=task_id,
            author_id=user.id,
            text=data.text,
        )
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return comment
