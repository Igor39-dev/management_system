from fastapi import APIRouter, HTTPException, status

from backend.src.api.dependencies import CurrentUser, DBDep
from backend.src.models.evaluations import EvaluationOrm
from backend.src.schemas.evaluations import EvaluationAverage, EvaluationGet
from backend.src.services.evaluations import EvaluationService
from backend.src.services.tasks import NotInTeamError


router = APIRouter(prefix="/evaluations", tags=["Оценки"])


@router.get("/me", response_model=list[EvaluationGet])
async def list_my_evaluations(
    current_user: CurrentUser,
    db: DBDep,
) -> list[EvaluationOrm]:
    try:
        return await EvaluationService.list_for_user(db, current_user)
    except NotInTeamError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Вы не состоите в команде")


@router.get("/me/average", response_model=EvaluationAverage)
async def get_my_average_score(
    current_user: CurrentUser,
    db: DBDep,
) -> EvaluationAverage:
    try:
        average_score, count = await EvaluationService.get_average_for_user(db, current_user)
    except NotInTeamError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Вы не состоите в команде")

    return EvaluationAverage(average_score=average_score, count=count)
