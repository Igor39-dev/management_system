from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.src.database import Base
from backend.src.models.enums import UserRole, enum_values
from backend.src.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from backend.src.models.evaluations import EvaluationOrm
    from backend.src.models.meetings import MeetingOrm
    from backend.src.models.tasks import TaskCommentOrm, TaskOrm
    from backend.src.models.teams import TeamOrm


class UserOrm(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(1024), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=enum_values),
        default=UserRole.USER,
        server_default="user",
    )
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", use_alter=True, name="fk_users_team_id"))

    team: Mapped["TeamOrm | None"] = relationship(back_populates="members", foreign_keys=[team_id])
    owned_teams: Mapped[list["TeamOrm"]] = relationship(back_populates="owner", foreign_keys="TeamOrm.owner_id")
    created_tasks: Mapped[list["TaskOrm"]] = relationship(back_populates="creator", foreign_keys="TaskOrm.creator_id")
    assigned_tasks: Mapped[list["TaskOrm"]] = relationship(back_populates="assignee", foreign_keys="TaskOrm.assignee_id")
    task_comments: Mapped[list["TaskCommentOrm"]] = relationship(back_populates="author")
    evaluations_given: Mapped[list["EvaluationOrm"]] = relationship(back_populates="evaluator")
    organized_meetings: Mapped[list["MeetingOrm"]] = relationship(back_populates="organizer", foreign_keys="MeetingOrm.organizer_id")
    meetings: Mapped[list["MeetingOrm"]] = relationship(secondary="meeting_participants", back_populates="participants")
