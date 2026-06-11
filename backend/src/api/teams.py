from fastapi import APIRouter, HTTPException, status

from backend.src.api.dependencies import CurrentAdmin, CurrentUser, DBDep
from backend.src.models.teams import TeamOrm
from backend.src.models.users import UserOrm
from backend.src.schemas.teams import TeamCreate, TeamGet, TeamGetDetail, TeamJoin, TeamMemberRoleUpdate
from backend.src.schemas.users import UserGet
from backend.src.services.teams import (
    AlreadyInTeamError,
    CannotAssignRoleError,
    CannotRemoveOwnerError,
    MemberNotFoundError,
    TeamAccessDeniedError,
    TeamNotFoundError,
    TeamService,
)


router = APIRouter(prefix="/teams", tags=["Команды"])


@router.post("", response_model=TeamGet, status_code=status.HTTP_201_CREATED)
async def create_team(
    data: TeamCreate,
    current_admin: CurrentAdmin,
    db: DBDep,
) -> TeamOrm:
    return await TeamService.create(db, current_admin, data)


@router.get("/{team_id}", response_model=TeamGetDetail)
async def get_team(
    team_id: int,
    current_user: CurrentUser,
    db: DBDep,
) -> TeamGetDetail:
    try:
        team, members = await TeamService.get_team_detail(db, current_user, team_id)
    except TeamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Команда не найдена",
        )
    except TeamAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой команде",
        )

    return TeamGetDetail(
        **TeamGet.model_validate(team).model_dump(),
        members=members,
    )


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def remove_team_member(
    team_id: int,
    user_id: int,
    current_user: CurrentUser,
    db: DBDep,
) -> dict[str, str]:
    try:
        await TeamService.remove_member(db, current_user, team_id, user_id)
    except TeamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Команда не найдена",
        )
    except TeamAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для управления командой",
        )
    except MemberNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участник не найден в этой команде",
        )
    except CannotRemoveOwnerError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить владельца команды",
        )

    return {"detail": "Участник удалён из команды"}


@router.patch("/{team_id}/members/{user_id}/role", response_model=UserGet)
async def assign_member_role(
    team_id: int,
    user_id: int,
    data: TeamMemberRoleUpdate,
    current_user: CurrentUser,
    db: DBDep,
) -> UserOrm:
    try:
        return await TeamService.assign_role(db, current_user, team_id, user_id, data.role)
    except TeamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Команда не найдена",
        )
    except TeamAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для управления командой",
        )
    except MemberNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участник не найден в этой команде",
        )
    except CannotAssignRoleError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недостаточно прав для назначения этой роли",
        )


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
