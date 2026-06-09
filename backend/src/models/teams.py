from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.src.database import Base
from backend.src.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from backend.src.models.meetings import MeetingOrm
    from backend.src.models.tasks import TaskOrm
    from backend.src.models.users import UserOrm


class TeamOrm(TimestampMixin, Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    owner: Mapped["UserOrm"] = relationship(back_populates="owned_teams", foreign_keys=[owner_id])
    members: Mapped[list["UserOrm"]] = relationship(back_populates="team", foreign_keys="UserOrm.team_id")
    tasks: Mapped[list["TaskOrm"]] = relationship(back_populates="team")
    meetings: Mapped[list["MeetingOrm"]] = relationship(back_populates="team")
