"""Which Saturday and Sunday the digest is for, and when to send."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from planner.config import SEND_HOUR_LONDON, SEND_WEEKDAY

LONDON = ZoneInfo("Europe/London")


def london_today(now: datetime | None = None) -> date:
    moment = now or datetime.now(LONDON)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=LONDON)
    return moment.astimezone(LONDON).date()


def coming_weekend(today: date) -> tuple[date, date]:
    """Saturday and Sunday the list is about.

    Monday to Saturday use the Saturday of this week (today, if it is Saturday).
    Sunday looks ahead to the next weekend, because this one is almost over.
    """
    weekday = today.weekday()
    if weekday == 6:
        saturday = today + timedelta(days=6)
    else:
        saturday = today + timedelta(days=(5 - weekday))
    return saturday, saturday + timedelta(days=1)


def is_send_window(now: datetime) -> bool:
    """True only at 10:00 Europe/London on a Friday."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=LONDON)
    local = now.astimezone(LONDON)
    return local.weekday() == SEND_WEEKDAY and local.hour == SEND_HOUR_LONDON
