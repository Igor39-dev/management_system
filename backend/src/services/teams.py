import secrets
import string

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.models.teams import TeamOrm
from backend.src.models.users import UserOrm
from backend.src.schemas.teams import TeamCreate


class TeamNotFoundError(Exception):
    pass


class AlreadyInTeamError(Exception):
    pass


class TeamService:
    _CODE_ALPHABET = string.ascii_uppercase + string.digits
    _CODE_LENGTH = 8

    @classmethod
    async def _generate_unique_code(cls, db: AsyncSession) -> str:
        while True:
            code = "".join(secrets.choice(cls._CODE_ALPHABET) for _ in range(cls._CODE_LENGTH))
            if await cls.get_by_code(db, code) is None:
                return code

    @classmethod
    async def create(cls, db: AsyncSession, creator: UserOrm, data: TeamCreate) -> TeamOrm:
        team = TeamOrm(
            name=data.name,
            code=await cls._generate_unique_code(db),
            owner_id=creator.id,
        )
        db.add(team)
        await db.commit()
        await db.refresh(team)
        return team

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
