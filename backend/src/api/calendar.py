from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from backend.src.api.dependencies import CurrentUser, DBDep
from backend.src.schemas.calendar import CalendarDayGet, CalendarMonthGet
from backend.src.services.calendar import CalendarService
from backend.src.services.meetings import NotInTeamError


router = APIRouter(prefix="/calendar", tags=["Календарь"])


@router.get("/month", response_model=CalendarMonthGet)
async def get_month_calendar(
    current_user: CurrentUser,
    db: DBDep,
    year: int = Query(ge=1, le=9999),
    month: int = Query(ge=1, le=12),
    include_cancelled_meetings: bool = False,
) -> CalendarMonthGet:
    try:
        events = await CalendarService.get_month(
            db,
            current_user,
            year,
            month,
            include_cancelled_meetings=include_cancelled_meetings,
        )
    except NotInTeamError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Вы не состоите в команде")

    return CalendarMonthGet(year=year, month=month, events=events)


@router.get("/day", response_model=CalendarDayGet)
async def get_day_calendar(
    current_user: CurrentUser,
    db: DBDep,
    day: date,
    include_cancelled_meetings: bool = False,
) -> CalendarDayGet:
    try:
        events = await CalendarService.get_day(
            db,
            current_user,
            day,
            include_cancelled_meetings=include_cancelled_meetings,
        )
    except NotInTeamError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Вы не состоите в команде")

    return CalendarDayGet(date=day, events=events)
