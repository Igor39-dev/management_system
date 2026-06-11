from fastapi import APIRouter, HTTPException, status

from backend.src.api.dependencies import CurrentUser, DBDep
from backend.src.models.users import UserOrm
from backend.src.schemas.teams import TeamJoin
from backend.src.schemas.users import UserGet
from backend.src.services.teams import AlreadyInTeamError, TeamNotFoundError, TeamService


router = APIRouter(prefix="/teams", tags=["Команды"])


@router.post("/join", response_model=UserGet)
async def join_team(
    data: TeamJoin,
    current_user: CurrentUser,
    db: DBDep,
) -> UserOrm:
    try:
        return await TeamService.join_by_code(db, current_user, data.code)
    except TeamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Команда с таким кодом не найдена",
        )
    except AlreadyInTeamError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы уже состоите в команде",
        )
