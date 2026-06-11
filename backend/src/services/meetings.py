from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.src.models.meetings import MeetingOrm, meeting_participants_table
from backend.src.models.users import UserOrm
from backend.src.schemas.meetings import MeetingCreate, MeetingUpdate
from backend.src.services.teams import MemberNotFoundError, TeamService


class NotInTeamError(Exception):
    pass


class MeetingNotFoundError(Exception):
    pass


class MeetingAccessDeniedError(Exception):
    pass


class ParticipantNotInTeamError(Exception):
    pass


class InvalidMeetingTimeError(Exception):
    pass


class MeetingTimeConflictError(Exception):
    pass


class MeetingService:
    @classmethod
    def _validate_time_range(cls, start_at: datetime, end_at: datetime) -> None:
        if end_at <= start_at:
            raise InvalidMeetingTimeError

    @classmethod
    async def _resolve_participants(
        cls,
        db: AsyncSession,
        team_id: int,
        participant_ids: list[int],
    ) -> list[UserOrm]:
        unique_ids = list(dict.fromkeys(participant_ids))
        participants: list[UserOrm] = []
        for participant_id in unique_ids:
            try:
                participants.append(await TeamService._get_team_member(db, team_id, participant_id))
            except MemberNotFoundError:
                raise ParticipantNotInTeamError
        return participants

    @classmethod
    def _users_for_conflict_check(cls, organizer_id: int, participant_ids: list[int]) -> set[int]:
        return {organizer_id, *participant_ids}

    @classmethod
    async def _check_time_conflicts(
        cls,
        db: AsyncSession,
        user_ids: set[int],
        start_at: datetime,
        end_at: datetime,
        exclude_meeting_id: int | None = None,
    ) -> None:
        if not user_ids:
            return

        participant_meeting_ids = select(meeting_participants_table.c.meeting_id).where(
            meeting_participants_table.c.user_id.in_(user_ids),
        )

        stmt = select(MeetingOrm.id).where(
            MeetingOrm.is_cancelled.is_(False),
            MeetingOrm.start_at < end_at,
            MeetingOrm.end_at > start_at,
            or_(
                MeetingOrm.organizer_id.in_(user_ids),
                MeetingOrm.id.in_(participant_meeting_ids),
            ),
        )
        if exclude_meeting_id is not None:
            stmt = stmt.where(MeetingOrm.id != exclude_meeting_id)

        result = await db.execute(stmt.limit(1))
        if result.scalar_one_or_none() is not None:
            raise MeetingTimeConflictError

    @classmethod
    async def _get_meeting(
        cls,
        db: AsyncSession,
        meeting_id: int,
        *,
        with_participants: bool = False,
    ) -> MeetingOrm | None:
        stmt = select(MeetingOrm).where(MeetingOrm.id == meeting_id)
        if with_participants:
            stmt = stmt.options(selectinload(MeetingOrm.participants))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def create(cls, db: AsyncSession, user: UserOrm, data: MeetingCreate) -> MeetingOrm:
        if user.team_id is None:
            raise NotInTeamError

        team = await TeamService.get_by_id(db, user.team_id)
        if team is None:
            raise NotInTeamError

        cls._validate_time_range(data.start_at, data.end_at)

        participants = await cls._resolve_participants(db, user.team_id, data.participant_ids)
        participant_ids = [participant.id for participant in participants]
        user_ids = cls._users_for_conflict_check(user.id, participant_ids)

        await cls._check_time_conflicts(db, user_ids, data.start_at, data.end_at)

        meeting = MeetingOrm(
            title=data.title,
            description=data.description,
            start_at=data.start_at,
            end_at=data.end_at,
            team_id=user.team_id,
            organizer_id=user.id,
            participants=participants,
        )
        db.add(meeting)
        await db.commit()

        meeting = await cls._get_meeting(db, meeting.id, with_participants=True)
        if meeting is None:
            raise MeetingNotFoundError
        return meeting

    @classmethod
    async def list_meetings(
        cls,
        db: AsyncSession,
        user: UserOrm,
        *,
        from_at: datetime | None = None,
        to_at: datetime | None = None,
        include_cancelled: bool = False,
    ) -> list[MeetingOrm]:
        if user.team_id is None:
            raise NotInTeamError

        participant_meeting_ids = select(meeting_participants_table.c.meeting_id).where(
            meeting_participants_table.c.user_id == user.id,
        )

        stmt = (
            select(MeetingOrm)
            .where(
                MeetingOrm.team_id == user.team_id,
                or_(
                    MeetingOrm.organizer_id == user.id,
                    MeetingOrm.id.in_(participant_meeting_ids),
                ),
            )
            .order_by(MeetingOrm.start_at.asc())
        )

        if not include_cancelled:
            stmt = stmt.where(MeetingOrm.is_cancelled.is_(False))
        if from_at is not None:
            stmt = stmt.where(MeetingOrm.end_at >= from_at)
        if to_at is not None:
            stmt = stmt.where(MeetingOrm.start_at <= to_at)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_meeting(cls, db: AsyncSession, user: UserOrm, meeting_id: int) -> MeetingOrm:
        meeting = await cls._get_meeting(db, meeting_id, with_participants=True)
        if meeting is None:
            raise MeetingNotFoundError

        team = await TeamService.get_by_id(db, meeting.team_id)
        if team is None:
            raise MeetingNotFoundError

        if not TeamService.can_access_team(user, team):
            raise MeetingAccessDeniedError

        is_organizer = meeting.organizer_id == user.id
        is_participant = any(participant.id == user.id for participant in meeting.participants)
        if not is_organizer and not is_participant and not TeamService.can_manage_team(user, team):
            raise MeetingAccessDeniedError

        return meeting

    @classmethod
    async def update(
        cls,
        db: AsyncSession,
        user: UserOrm,
        meeting_id: int,
        data: MeetingUpdate,
    ) -> MeetingOrm:
        meeting = await cls.get_meeting(db, user, meeting_id)

        team = await TeamService.get_by_id(db, meeting.team_id)
        if team is None:
            raise MeetingNotFoundError

        is_organizer = meeting.organizer_id == user.id
        if not is_organizer and not TeamService.can_manage_team(user, team):
            raise MeetingAccessDeniedError

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return meeting

        new_start_at = update_data.get("start_at", meeting.start_at)
        new_end_at = update_data.get("end_at", meeting.end_at)
        cls._validate_time_range(new_start_at, new_end_at)

        if update_data.get("participant_ids") is not None:
            participants = await cls._resolve_participants(db, meeting.team_id, update_data["participant_ids"])
            meeting.participants = participants
            participant_ids = [participant.id for participant in participants]
        else:
            participant_ids = [participant.id for participant in meeting.participants]

        time_changed = "start_at" in update_data or "end_at" in update_data
        participants_changed = "participant_ids" in update_data
        if time_changed or participants_changed:
            user_ids = cls._users_for_conflict_check(meeting.organizer_id, participant_ids)
            await cls._check_time_conflicts(
                db,
                user_ids,
                new_start_at,
                new_end_at,
                exclude_meeting_id=meeting.id,
            )

        for field in ("title", "description", "start_at", "end_at", "is_cancelled"):
            if field in update_data:
                setattr(meeting, field, update_data[field])

        await db.commit()

        updated_meeting = await cls._get_meeting(db, meeting.id, with_participants=True)
        if updated_meeting is None:
            raise MeetingNotFoundError
        return updated_meeting

    @classmethod
    async def cancel(cls, db: AsyncSession, user: UserOrm, meeting_id: int) -> MeetingOrm:
        return await cls.update(db, user, meeting_id, MeetingUpdate(is_cancelled=True))
