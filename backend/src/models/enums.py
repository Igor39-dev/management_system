from enum import StrEnum
from typing import TypeVar

E = TypeVar("E", bound=StrEnum)


def enum_values(enum_cls: type[E]) -> list[str]:
    return [member.value for member in enum_cls]


class UserRole(StrEnum):
    USER = "user"
    MANAGER = "manager"
    ADMIN = "admin"


class TaskStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
