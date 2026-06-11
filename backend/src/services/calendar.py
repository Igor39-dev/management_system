from calendar import monthrange
from datetime import date, datetime, time

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.models.enums import CalendarEventType
from backend.src.models.meetings import MeetingOrm
from backend.src.models.tasks import TaskOrm
from backend.src.models.users import UserOrm
from backend.src.schemas.calendar import CalendarEvent
from backend.src.services.meetings import MeetingService, NotInTeamError


class CalendarService:
    @staticmethod
    def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
        start = datetime(year, month, 1)
        last_day = monthrange(year, month)[1]
        end = datetime.combine(date(year, month, last_day), time.max)
        return start, end

    @staticmethod
    def _day_bounds(day: date) -> tuple[datetime, datetime]:
        start = datetime.combine(day, time.min)
        end = datetime.combine(day, time.max)
        return start, end

    @classmethod
    def _task_to_event(cls, task: TaskOrm) -> CalendarEvent:
        return CalendarEvent(
            id=task.id,
            type=CalendarEventType.TASK,
            title=task.title,
            starts_at=task.deadline,  # type: ignore[arg-type]
            status=task.status,
        )

    @classmethod
    def _meeting_to_event(cls, meeting: MeetingOrm) -> CalendarEvent:
        return CalendarEvent(
            id=meeting.id,
            type=CalendarEventType.MEETING,
            title=meeting.title,
            starts_at=meeting.start_at,
            ends_at=meeting.end_at,
            is_cancelled=meeting.is_cancelled,
        )

    @classmethod
    async def _list_tasks(
        cls,
        db: AsyncSession,
        user: UserOrm,
        from_at: datetime,
        to_at: datetime,
    ) -> list[TaskOrm]:
        stmt = (
            select(TaskOrm)
            .where(
                TaskOrm.team_id == user.team_id,
                TaskOrm.deadline.is_not(None),
                TaskOrm.deadline >= from_at,
                TaskOrm.deadline <= to_at,
                or_(
                    TaskOrm.assignee_id == user.id,
                    TaskOrm.creator_id == user.id,
                ),
            )
            .order_by(TaskOrm.deadline.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def _collect_events(
        cls,
        db: AsyncSession,
        user: UserOrm,
        from_at: datetime,
        to_at: datetime,
        *,
        include_cancelled_meetings: bool,
    ) -> list[CalendarEvent]:
        if user.team_id is None:
            raise NotInTeamError

        tasks = await cls._list_tasks(db, user, from_at, to_at)
        meetings = await MeetingService.list_meetings(
            db,
            user,
            from_at=from_at,
            to_at=to_at,
            include_cancelled=include_cancelled_meetings,
        )

        events = [cls._task_to_event(task) for task in tasks]
        events.extend(cls._meeting_to_event(meeting) for meeting in meetings)
        events.sort(key=lambda event: event.starts_at)
        return events

    @classmethod
    async def get_month(
        cls,
        db: AsyncSession,
        user: UserOrm,
        year: int,
        month: int,
        *,
        include_cancelled_meetings: bool = False,
    ) -> list[CalendarEvent]:
        from_at, to_at = cls._month_bounds(year, month)
        return await cls._collect_events(
            db,
            user,
            from_at,
            to_at,
            include_cancelled_meetings=include_cancelled_meetings,
        )

    @classmethod
    async def get_day(
        cls,
        db: AsyncSession,
        user: UserOrm,
        day: date,
        *,
        include_cancelled_meetings: bool = False,
    ) -> list[CalendarEvent]:
        from_at, to_at = cls._day_bounds(day)
        return await cls._collect_events(
            db,
            user,
            from_at,
            to_at,
            include_cancelled_meetings=include_cancelled_meetings,
        )
