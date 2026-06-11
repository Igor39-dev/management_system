from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.models.evaluations import EvaluationOrm
from backend.src.models.tasks import TaskOrm
from backend.src.models.users import UserOrm
from backend.src.schemas.evaluations import EvaluationCreate, EvaluationUpdate
from backend.src.services.tasks import NotInTeamError, TaskService
from backend.src.services.teams import TeamService


class EvaluationNotFoundError(Exception):
    pass


class EvaluationAlreadyExistsError(Exception):
    pass


class EvaluationAccessDeniedError(Exception):
    pass


class EvaluationService:
    @classmethod
    async def _get_by_task_id(cls, db: AsyncSession, task_id: int) -> EvaluationOrm | None:
        result = await db.execute(select(EvaluationOrm).where(EvaluationOrm.task_id == task_id))
        return result.scalar_one_or_none()

    @classmethod
    async def get_for_task(cls, db: AsyncSession, user: UserOrm, task_id: int) -> EvaluationOrm:
        await TaskService.get_task(db, user, task_id)

        evaluation = await cls._get_by_task_id(db, task_id)
        if evaluation is None:
            raise EvaluationNotFoundError
        return evaluation

    @classmethod
    async def create(
        cls,
        db: AsyncSession,
        user: UserOrm,
        task_id: int,
        data: EvaluationCreate,
    ) -> EvaluationOrm:
        task = await TaskService.get_task(db, user, task_id)

        team = await TeamService.get_by_id(db, task.team_id)
        if team is None or not TeamService.can_manage_team(user, team):
            raise EvaluationAccessDeniedError

        if await cls._get_by_task_id(db, task_id) is not None:
            raise EvaluationAlreadyExistsError

        evaluation = EvaluationOrm(
            task_id=task_id,
            evaluator_id=user.id,
            score=data.score,
        )
        db.add(evaluation)
        await db.commit()
        await db.refresh(evaluation)
        return evaluation

    @classmethod
    async def update(
        cls,
        db: AsyncSession,
        user: UserOrm,
        task_id: int,
        data: EvaluationUpdate,
    ) -> EvaluationOrm:
        task = await TaskService.get_task(db, user, task_id)

        team = await TeamService.get_by_id(db, task.team_id)
        if team is None or not TeamService.can_manage_team(user, team):
            raise EvaluationAccessDeniedError

        evaluation = await cls._get_by_task_id(db, task_id)
        if evaluation is None:
            raise EvaluationNotFoundError

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return evaluation

        for field, value in update_data.items():
            setattr(evaluation, field, value)

        await db.commit()
        await db.refresh(evaluation)
        return evaluation

    @classmethod
    async def list_for_user(cls, db: AsyncSession, user: UserOrm) -> list[EvaluationOrm]:
        if user.team_id is None:
            raise NotInTeamError

        stmt = (
            select(EvaluationOrm)
            .join(TaskOrm, EvaluationOrm.task_id == TaskOrm.id)
            .where(TaskOrm.assignee_id == user.id)
            .order_by(EvaluationOrm.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_average_for_user(cls, db: AsyncSession, user: UserOrm) -> tuple[float | None, int]:
        if user.team_id is None:
            raise NotInTeamError

        stmt = (
            select(func.avg(EvaluationOrm.score), func.count(EvaluationOrm.id))
            .select_from(EvaluationOrm)
            .join(TaskOrm, EvaluationOrm.task_id == TaskOrm.id)
            .where(TaskOrm.assignee_id == user.id)
        )
        result = await db.execute(stmt)
        average_score, count = result.one()

        if count == 0:
            return None, 0
        return float(average_score), count
