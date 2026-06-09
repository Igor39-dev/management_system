from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.src.database import Base
from backend.src.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from backend.src.models.tasks import TaskOrm
    from backend.src.models.users import UserOrm


class EvaluationOrm(TimestampMixin, Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        UniqueConstraint("task_id", name="uq_evaluations_task_id"),
        CheckConstraint("score >= 1 AND score <= 5", name="ck_evaluations_score_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    evaluator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    score: Mapped[int] = mapped_column(nullable=False)

    task: Mapped["TaskOrm"] = relationship(back_populates="evaluation")
    evaluator: Mapped["UserOrm"] = relationship(back_populates="evaluations_given")
