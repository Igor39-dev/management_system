from fastapi import APIRouter, HTTPException, status

from backend.src.api.dependencies import CurrentUser, DBDep
from backend.src.models.enums import TaskStatus
from backend.src.models.tasks import TaskOrm
from backend.src.schemas.tasks import TaskCreate, TaskGet
from backend.src.services.tasks import AssigneeNotInTeamError, NotInTeamError, TaskAccessDeniedError, TaskNotFoundError, TaskService


router = APIRouter(prefix="/tasks", tags=["Задачи"])


@router.get("", response_model=list[TaskGet])
async def list_tasks(
    current_user: CurrentUser,
    db: DBDep,
    status: TaskStatus | None = None,
    assignee_id: int | None = None,
    assigned_to_me: bool = False,
) -> list[TaskOrm]:
    try:
        return await TaskService.list_tasks(
            db,
            current_user,
            status=status,
            assignee_id=assignee_id,
            assigned_to_me=assigned_to_me,
        )
    except NotInTeamError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Вы не состоите в команде")


@router.get("/{task_id}", response_model=TaskGet)
async def get_task(
    task_id: int,
    current_user: CurrentUser,
    db: DBDep,
) -> TaskOrm:
    try:
        return await TaskService.get_task(db, current_user, task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    except TaskAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этой задаче")


@router.post("", response_model=TaskGet, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    current_user: CurrentUser,
    db: DBDep,
) -> TaskOrm:
    try:
        return await TaskService.create(db, current_user, data)
    except NotInTeamError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Вы не состоите в команде")
    except TaskAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для создания задач")
    except AssigneeNotInTeamError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Исполнитель не найден в вашей команде")
