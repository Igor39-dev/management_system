from fastapi import APIRouter, HTTPException, status

from backend.src.api.dependencies import CurrentUser, DBDep
from backend.src.models.enums import TaskStatus
from backend.src.models.tasks import TaskCommentOrm, TaskOrm
from backend.src.models.evaluations import EvaluationOrm
from backend.src.schemas.evaluations import EvaluationCreate, EvaluationGet, EvaluationUpdate
from backend.src.schemas.tasks import TaskCommentCreate, TaskCommentGet, TaskCreate, TaskGet, TaskUpdate
from backend.src.services.evaluations import EvaluationAccessDeniedError, EvaluationAlreadyExistsError, EvaluationNotFoundError, EvaluationService
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


@router.patch("/{task_id}", response_model=TaskGet)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    current_user: CurrentUser,
    db: DBDep,
) -> TaskOrm:
    try:
        return await TaskService.update(db, current_user, task_id, data)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    except TaskAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для изменения задачи")
    except AssigneeNotInTeamError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Исполнитель не найден в команде задачи")


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: int,
    current_user: CurrentUser,
    db: DBDep,
) -> dict[str, str]:
    try:
        await TaskService.delete(db, current_user, task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    except TaskAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для удаления задачи")

    return {"detail": "Задача удалена"}


@router.get("/{task_id}/comments", response_model=list[TaskCommentGet])
async def list_task_comments(
    task_id: int,
    current_user: CurrentUser,
    db: DBDep,
) -> list[TaskCommentOrm]:
    try:
        return await TaskService.list_comments(db, current_user, task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    except TaskAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этой задаче")


@router.post("/{task_id}/comments", response_model=TaskCommentGet, status_code=status.HTTP_201_CREATED)
async def add_task_comment(
    task_id: int,
    data: TaskCommentCreate,
    current_user: CurrentUser,
    db: DBDep,
) -> TaskCommentOrm:
    try:
        return await TaskService.add_comment(db, current_user, task_id, data)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    except TaskAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этой задаче")


@router.get("/{task_id}/evaluation", response_model=EvaluationGet)
async def get_task_evaluation(
    task_id: int,
    current_user: CurrentUser,
    db: DBDep,
) -> EvaluationOrm:
    try:
        return await EvaluationService.get_for_task(db, current_user, task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    except TaskAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этой задаче")
    except EvaluationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Оценка для задачи не найдена")


@router.post("/{task_id}/evaluation", response_model=EvaluationGet, status_code=status.HTTP_201_CREATED)
async def create_task_evaluation(
    task_id: int,
    data: EvaluationCreate,
    current_user: CurrentUser,
    db: DBDep,
) -> EvaluationOrm:
    try:
        return await EvaluationService.create(db, current_user, task_id, data)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    except TaskAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этой задаче")
    except EvaluationAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для оценки задачи")
    except EvaluationAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Задача уже оценена")


@router.patch("/{task_id}/evaluation", response_model=EvaluationGet)
async def update_task_evaluation(
    task_id: int,
    data: EvaluationUpdate,
    current_user: CurrentUser,
    db: DBDep,
) -> EvaluationOrm:
    try:
        return await EvaluationService.update(db, current_user, task_id, data)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    except TaskAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этой задаче")
    except EvaluationAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для изменения оценки")
    except EvaluationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Оценка для задачи не найдена")


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
