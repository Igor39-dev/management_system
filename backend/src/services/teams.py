from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.models.teams import TeamOrm
from backend.src.models.users import UserOrm


class TeamNotFoundError(Exception):
    pass


class AlreadyInTeamError(Exception):
    pass


class TeamService:
    @classmethod
    async def get_by_code(cls, db: AsyncSession, code: str) -> TeamOrm | None:
        result = await db.execute(select(TeamOrm).where(TeamOrm.code == code))
        return result.scalar_one_or_none()

    @classmethod
    async def join_by_code(
        cls,
        db: AsyncSession,
        user: UserOrm,
        code: str,
    ) -> UserOrm:
        if user.team_id is not None:
            raise AlreadyInTeamError

        team = await cls.get_by_code(db, code)
        if team is None:
            raise TeamNotFoundError

        user.team_id = team.id
        await db.commit()
        return user
