from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.src.database import Base
from backend.src.models.enums import TaskStatus, enum_values
from backend.src.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from backend.src.models.evaluations import EvaluationOrm
    from backend.src.models.teams import TeamOrm
    from backend.src.models.users import UserOrm


class TaskOrm(TimestampMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", values_callable=enum_values),
        default=TaskStatus.OPEN,
        server_default="open",
    )
    deadline: Mapped[datetime | None] = mapped_column()
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    team: Mapped["TeamOrm"] = relationship(back_populates="tasks")
    creator: Mapped["UserOrm"] = relationship(back_populates="created_tasks", foreign_keys=[creator_id])
    assignee: Mapped["UserOrm | None"] = relationship(back_populates="assigned_tasks", foreign_keys=[assignee_id])
    comments: Mapped[list["TaskCommentOrm"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    evaluation: Mapped["EvaluationOrm | None"] = relationship(back_populates="task", uselist=False, cascade="all, delete-orphan")


class TaskCommentOrm(TimestampMixin, Base):
    __tablename__ = "task_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    task: Mapped["TaskOrm"] = relationship(back_populates="comments")
    author: Mapped["UserOrm"] = relationship(back_populates="task_comments")
