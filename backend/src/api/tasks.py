from fastapi import APIRouter, HTTPException, status

from backend.src.api.dependencies import CurrentUser, DBDep
from backend.src.models.tasks import TaskOrm
from backend.src.schemas.tasks import TaskCreate, TaskGet
from backend.src.services.tasks import AssigneeNotInTeamError, NotInTeamError, TaskAccessDeniedError, TaskService


router = APIRouter(prefix="/tasks", tags=["Задачи"])


@router.post("", response_model=TaskGet, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    current_user: CurrentUser,
    db: DBDep,
) -> TaskOrm:
    try:
        return await TaskService.create(db, current_user, data)
    except NotInTeamError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы не состоите в команде",
        )
    except TaskAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для создания задач",
        )
    except AssigneeNotInTeamError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Исполнитель не найден в вашей команде",
        )
