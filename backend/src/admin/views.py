from typing import Any

from sqlalchemy.sql.expression import Select
from sqladmin import ModelView
from sqladmin.filters import BooleanFilter, StaticValuesFilter, get_column_obj
from starlette.requests import Request
from wtforms import PasswordField
from wtforms.validators import Optional

from backend.src.database import session as session_factory
from backend.src.models.enums import TaskStatus, UserRole
from backend.src.models.evaluations import EvaluationOrm
from backend.src.models.meetings import MeetingOrm
from backend.src.models.tasks import TaskCommentOrm, TaskOrm
from backend.src.models.teams import TeamOrm
from backend.src.models.users import UserOrm
from backend.src.services.auth import AuthService
from backend.src.services.teams import TeamService

_ROLE_LABELS = {
    UserRole.USER: "Пользователь",
    UserRole.MANAGER: "Менеджер",
    UserRole.ADMIN: "Админ",
}

_STATUS_LABELS = {
    TaskStatus.OPEN: "Открыта",
    TaskStatus.IN_PROGRESS: "В работе",
    TaskStatus.DONE: "Выполнена",
}


def _format_related_email(model: Any, attr: str) -> str:
    related = getattr(model, attr, None)
    return related.email if related is not None else "—"


def _format_related_name(model: Any, attr: str) -> str:
    related = getattr(model, attr, None)
    return related.name if related is not None else "—"


def _format_related_title(model: Any, attr: str) -> str:
    related = getattr(model, attr, None)
    return related.title if related is not None else "—"


def _format_participants(model: MeetingOrm) -> str:
    if not model.participants:
        return "—"
    return ", ".join(participant.email for participant in model.participants)


def _truncate_text(text: str, max_length: int = 80) -> str:
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}…"


class IntegerStaticValuesFilter(StaticValuesFilter):
    async def get_filtered_query(self, query: Select, value: Any, model: Any) -> Select:
        if value == "":
            return query

        column_obj = get_column_obj(self.column, model)
        return query.filter(column_obj == int(value))


class UserAdmin(ModelView, model=UserOrm):
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-user"

    column_list = [
        UserOrm.id,
        UserOrm.email,
        UserOrm.first_name,
        UserOrm.last_name,
        UserOrm.role,
        UserOrm.is_active,
        UserOrm.team,
        UserOrm.created_at,
    ]
    column_searchable_list = [UserOrm.email, UserOrm.first_name, UserOrm.last_name]
    column_sortable_list = [UserOrm.id, UserOrm.email, UserOrm.role, UserOrm.created_at]
    column_default_sort = (UserOrm.id, True)
    column_filters = [
        StaticValuesFilter(
            UserOrm.role,
            values=[(role.value, label) for role, label in _ROLE_LABELS.items()],
            title="Роль",
        ),
        BooleanFilter(UserOrm.is_active, title="Активен"),
        BooleanFilter(UserOrm.is_superuser, title="Суперпользователь"),
    ]
    column_formatters = {
        UserOrm.role: lambda model, _: _ROLE_LABELS.get(model.role, model.role),
        UserOrm.team: lambda model, _: _format_related_name(model, "team"),
    }

    form_excluded_columns = [
        UserOrm.hashed_password,
        UserOrm.owned_teams,
        UserOrm.created_tasks,
        UserOrm.assigned_tasks,
        UserOrm.task_comments,
        UserOrm.evaluations_given,
        UserOrm.organized_meetings,
        UserOrm.meetings,
        UserOrm.created_at,
        UserOrm.updated_at,
    ]
    form_ajax_refs = {
        "team": {
            "fields": ("name", "code"),
            "order_by": ("name",),
        },
    }

    column_labels = {
        UserOrm.email: "Email",
        UserOrm.first_name: "Имя",
        UserOrm.last_name: "Фамилия",
        UserOrm.role: "Роль",
        UserOrm.is_active: "Активен",
        UserOrm.is_superuser: "Суперпользователь",
        UserOrm.is_verified: "Подтверждён",
        UserOrm.team: "Команда",
        UserOrm.created_at: "Создан",
        UserOrm.updated_at: "Обновлён",
    }

    async def scaffold_form(self, rules: list[str] | None = None) -> type:
        form_class = await super().scaffold_form(rules)
        form_class.password = PasswordField("Пароль", validators=[Optional()])
        return form_class

    async def on_model_change(
        self,
        data: dict[str, Any],
        model: UserOrm,
        is_created: bool,
        request: Request,
    ) -> None:
        password = data.pop("password", None)
        if password:
            model.hashed_password = AuthService.hash_password(str(password))
        elif is_created and not model.hashed_password:
            raise ValueError("Укажите пароль при создании пользователя")


class TeamAdmin(ModelView, model=TeamOrm):
    name = "Команда"
    name_plural = "Команды"
    icon = "fa-solid fa-people-group"

    column_list = [
        TeamOrm.id,
        TeamOrm.name,
        TeamOrm.code,
        TeamOrm.owner,
        TeamOrm.created_at,
    ]
    column_searchable_list = [TeamOrm.name, TeamOrm.code]
    column_sortable_list = [TeamOrm.id, TeamOrm.name, TeamOrm.code, TeamOrm.created_at]
    column_default_sort = (TeamOrm.id, True)

    form_excluded_columns = [
        TeamOrm.members,
        TeamOrm.tasks,
        TeamOrm.meetings,
        TeamOrm.created_at,
        TeamOrm.updated_at,
    ]
    form_ajax_refs = {
        "owner": {
            "fields": ("email", "first_name", "last_name"),
            "order_by": ("email",),
        },
    }

    column_labels = {
        TeamOrm.name: "Название",
        TeamOrm.code: "Код",
        TeamOrm.owner: "Владелец",
        TeamOrm.created_at: "Создана",
        TeamOrm.updated_at: "Обновлена",
    }
    column_formatters = {
        TeamOrm.owner: lambda model, _: _format_related_email(model, "owner"),
    }

    async def on_model_change(
        self,
        data: dict[str, Any],
        model: TeamOrm,
        is_created: bool,
        request: Request,
    ) -> None:
        if is_created and not model.code:
            async with session_factory() as db:
                model.code = await TeamService._generate_unique_code(db)


class TaskAdmin(ModelView, model=TaskOrm):
    name = "Задача"
    name_plural = "Задачи"
    icon = "fa-solid fa-list-check"

    column_list = [
        TaskOrm.id,
        TaskOrm.title,
        TaskOrm.status,
        TaskOrm.deadline,
        TaskOrm.team,
        TaskOrm.assignee,
        TaskOrm.created_at,
    ]
    column_searchable_list = [TaskOrm.title]
    column_sortable_list = [
        TaskOrm.id,
        TaskOrm.title,
        TaskOrm.status,
        TaskOrm.deadline,
        TaskOrm.created_at,
    ]
    column_default_sort = (TaskOrm.id, True)
    column_filters = [
        StaticValuesFilter(
            TaskOrm.status,
            values=[(status.value, label) for status, label in _STATUS_LABELS.items()],
            title="Статус",
        ),
    ]

    form_excluded_columns = [
        TaskOrm.comments,
        TaskOrm.evaluation,
        TaskOrm.created_at,
        TaskOrm.updated_at,
    ]
    form_ajax_refs = {
        "team": {
            "fields": ("name", "code"),
            "order_by": ("name",),
        },
        "creator": {
            "fields": ("email",),
            "order_by": ("email",),
        },
        "assignee": {
            "fields": ("email",),
            "order_by": ("email",),
        },
    }

    column_labels = {
        TaskOrm.title: "Название",
        TaskOrm.description: "Описание",
        TaskOrm.status: "Статус",
        TaskOrm.deadline: "Дедлайн",
        TaskOrm.team: "Команда",
        TaskOrm.creator: "Создатель",
        TaskOrm.assignee: "Исполнитель",
        TaskOrm.created_at: "Создана",
        TaskOrm.updated_at: "Обновлена",
    }

    column_formatters = {
        TaskOrm.status: lambda model, _: _STATUS_LABELS.get(model.status, model.status),
        TaskOrm.team: lambda model, _: _format_related_name(model, "team"),
        TaskOrm.assignee: lambda model, _: _format_related_email(model, "assignee"),
    }


class MeetingAdmin(ModelView, model=MeetingOrm):
    name = "Встреча"
    name_plural = "Встречи"
    icon = "fa-solid fa-calendar"

    column_list = [
        MeetingOrm.id,
        MeetingOrm.title,
        MeetingOrm.start_at,
        MeetingOrm.end_at,
        MeetingOrm.is_cancelled,
        MeetingOrm.team,
        MeetingOrm.organizer,
        MeetingOrm.participants,
        MeetingOrm.created_at,
    ]
    column_searchable_list = [MeetingOrm.title]
    column_sortable_list = [
        MeetingOrm.id,
        MeetingOrm.title,
        MeetingOrm.start_at,
        MeetingOrm.end_at,
        MeetingOrm.created_at,
    ]
    column_default_sort = (MeetingOrm.start_at, True)
    column_filters = [BooleanFilter(MeetingOrm.is_cancelled, title="Отменена")]

    form_excluded_columns = [
        MeetingOrm.created_at,
        MeetingOrm.updated_at,
    ]
    form_ajax_refs = {
        "team": {
            "fields": ("name", "code"),
            "order_by": ("name",),
        },
        "organizer": {
            "fields": ("email",),
            "order_by": ("email",),
        },
        "participants": {
            "fields": ("email", "first_name", "last_name"),
            "order_by": ("email",),
        },
    }

    column_labels = {
        MeetingOrm.title: "Название",
        MeetingOrm.description: "Описание",
        MeetingOrm.start_at: "Начало",
        MeetingOrm.end_at: "Окончание",
        MeetingOrm.is_cancelled: "Отменена",
        MeetingOrm.team: "Команда",
        MeetingOrm.organizer: "Организатор",
        MeetingOrm.participants: "Участники",
        MeetingOrm.created_at: "Создана",
        MeetingOrm.updated_at: "Обновлена",
    }
    column_formatters = {
        MeetingOrm.team: lambda model, _: _format_related_name(model, "team"),
        MeetingOrm.organizer: lambda model, _: _format_related_email(model, "organizer"),
        MeetingOrm.participants: lambda model, _: _format_participants(model),
    }


class EvaluationAdmin(ModelView, model=EvaluationOrm):
    name = "Оценка"
    name_plural = "Оценки"
    icon = "fa-solid fa-star"

    column_list = [
        EvaluationOrm.id,
        EvaluationOrm.task,
        EvaluationOrm.evaluator,
        EvaluationOrm.score,
        EvaluationOrm.created_at,
    ]
    column_sortable_list = [
        EvaluationOrm.id,
        EvaluationOrm.score,
        EvaluationOrm.created_at,
    ]
    column_default_sort = (EvaluationOrm.id, True)
    column_filters = [
        IntegerStaticValuesFilter(
            EvaluationOrm.score,
            values=[(str(score), str(score)) for score in range(1, 6)],
            title="Оценка",
        ),
    ]

    form_excluded_columns = [
        EvaluationOrm.created_at,
        EvaluationOrm.updated_at,
    ]
    form_ajax_refs = {
        "task": {
            "fields": ("title",),
            "order_by": ("title",),
        },
        "evaluator": {
            "fields": ("email",),
            "order_by": ("email",),
        },
    }

    column_labels = {
        EvaluationOrm.task: "Задача",
        EvaluationOrm.evaluator: "Оценил",
        EvaluationOrm.score: "Балл",
        EvaluationOrm.created_at: "Создана",
        EvaluationOrm.updated_at: "Обновлена",
    }
    column_formatters = {
        EvaluationOrm.task: lambda model, _: _format_related_title(model, "task"),
        EvaluationOrm.evaluator: lambda model, _: _format_related_email(model, "evaluator"),
    }


class TaskCommentAdmin(ModelView, model=TaskCommentOrm):
    name = "Комментарий"
    name_plural = "Комментарии к задачам"
    icon = "fa-solid fa-comment"

    column_list = [
        TaskCommentOrm.id,
        TaskCommentOrm.task,
        TaskCommentOrm.author,
        TaskCommentOrm.text,
        TaskCommentOrm.created_at,
    ]
    column_searchable_list = [TaskCommentOrm.text]
    column_sortable_list = [
        TaskCommentOrm.id,
        TaskCommentOrm.created_at,
    ]
    column_default_sort = (TaskCommentOrm.id, True)

    form_excluded_columns = [
        TaskCommentOrm.created_at,
        TaskCommentOrm.updated_at,
    ]
    form_ajax_refs = {
        "task": {
            "fields": ("title",),
            "order_by": ("title",),
        },
        "author": {
            "fields": ("email",),
            "order_by": ("email",),
        },
    }

    column_labels = {
        TaskCommentOrm.task: "Задача",
        TaskCommentOrm.author: "Автор",
        TaskCommentOrm.text: "Текст",
        TaskCommentOrm.created_at: "Создан",
        TaskCommentOrm.updated_at: "Обновлён",
    }
    column_formatters = {
        TaskCommentOrm.task: lambda model, _: _format_related_title(model, "task"),
        TaskCommentOrm.author: lambda model, _: _format_related_email(model, "author"),
        TaskCommentOrm.text: lambda model, _: _truncate_text(model.text),
    }
