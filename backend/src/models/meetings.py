from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.src.database import Base
from backend.src.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from backend.src.models.teams import TeamOrm
    from backend.src.models.users import UserOrm


meeting_participants_table = Table(
    "meeting_participants",
    Base.metadata,
    Column("meeting_id", ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class MeetingOrm(TimestampMixin, Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start_at: Mapped[datetime] = mapped_column(nullable=False)
    end_at: Mapped[datetime] = mapped_column(nullable=False)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    organizer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    team: Mapped["TeamOrm"] = relationship(back_populates="meetings")
    organizer: Mapped["UserOrm"] = relationship(back_populates="organized_meetings", foreign_keys=[organizer_id])
    participants: Mapped[list["UserOrm"]] = relationship(secondary=meeting_participants_table, back_populates="meetings")
