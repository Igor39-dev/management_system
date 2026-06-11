from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from backend.src.api.dependencies import CurrentUser, DBDep
from backend.src.models.meetings import MeetingOrm
from backend.src.schemas.meetings import MeetingCreate, MeetingGet, MeetingGetDetail, MeetingUpdate
from backend.src.services.meetings import InvalidMeetingTimeError, MeetingAccessDeniedError, MeetingNotFoundError, MeetingService, MeetingTimeConflictError, NotInTeamError, ParticipantNotInTeamError


router = APIRouter(prefix="/meetings", tags=["Встречи"])


def _to_meeting_detail(meeting: MeetingOrm) -> MeetingGetDetail:
    return MeetingGetDetail(
        **MeetingGet.model_validate(meeting).model_dump(),
        participant_ids=[participant.id for participant in meeting.participants],
    )


@router.get("", response_model=list[MeetingGet])
async def list_meetings(
    current_user: CurrentUser,
    db: DBDep,
    from_at: datetime | None = None,
    to_at: datetime | None = None,
    include_cancelled: bool = False,
) -> list[MeetingOrm]:
    try:
        return await MeetingService.list_meetings(
            db,
            current_user,
            from_at=from_at,
            to_at=to_at,
            include_cancelled=include_cancelled,
        )
    except NotInTeamError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Вы не состоите в команде")


@router.post("", response_model=MeetingGetDetail, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    data: MeetingCreate,
    current_user: CurrentUser,
    db: DBDep,
) -> MeetingGetDetail:
    try:
        meeting = await MeetingService.create(db, current_user, data)
    except NotInTeamError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Вы не состоите в команде")
    except ParticipantNotInTeamError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Один или несколько участников не найдены в команде")
    except InvalidMeetingTimeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Окончание встречи должно быть позже начала")
    except MeetingTimeConflictError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Участники уже заняты в это время")

    return _to_meeting_detail(meeting)


@router.get("/{meeting_id}", response_model=MeetingGetDetail)
async def get_meeting(
    meeting_id: int,
    current_user: CurrentUser,
    db: DBDep,
) -> MeetingGetDetail:
    try:
        meeting = await MeetingService.get_meeting(db, current_user, meeting_id)
    except MeetingNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Встреча не найдена")
    except MeetingAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этой встрече")

    return _to_meeting_detail(meeting)


@router.patch("/{meeting_id}", response_model=MeetingGetDetail)
async def update_meeting(
    meeting_id: int,
    data: MeetingUpdate,
    current_user: CurrentUser,
    db: DBDep,
) -> MeetingGetDetail:
    try:
        meeting = await MeetingService.update(db, current_user, meeting_id, data)
    except MeetingNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Встреча не найдена")
    except MeetingAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для изменения встречи")
    except ParticipantNotInTeamError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Один или несколько участников не найдены в команде")
    except InvalidMeetingTimeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Окончание встречи должно быть позже начала")
    except MeetingTimeConflictError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Участники уже заняты в это время")

    return _to_meeting_detail(meeting)


@router.post("/{meeting_id}/cancel", response_model=MeetingGetDetail)
async def cancel_meeting(
    meeting_id: int,
    current_user: CurrentUser,
    db: DBDep,
) -> MeetingGetDetail:
    try:
        meeting = await MeetingService.cancel(db, current_user, meeting_id)
    except MeetingNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Встреча не найдена")
    except MeetingAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для отмены встречи")

    return _to_meeting_detail(meeting)
