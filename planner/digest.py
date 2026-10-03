"""Build one weekend's free and paid lists."""

import logging
from dataclasses import dataclass
from datetime import date, datetime

from planner.catalogue import CATALOGUE
from planner.events import fetch_events
from planner.http_util import FetchError
from planner.model import Activity, Pick
from planner.select import pool_for, select_band
from planner.weather import Forecast, fetch_forecast, unknown_forecast
from planner.weekend import coming_weekend, london_today

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Digest:
    saturday: date
    sunday: date
    forecast: Forecast
    free: list[Pick]
    paid: list[Pick]
    notes: list[str]


def build_digest(
    today: date | None = None,
    now: datetime | None = None,
    forecast: Forecast | None = None,
    events: list[Activity] | None = None,
    live: bool = True,
) -> Digest:
    day = today or london_today(now)
    saturday, sunday = coming_weekend(day)
    notes: list[str] = []

    if forecast is None:
        if live:
            try:
                forecast = fetch_forecast(saturday, sunday)
            except FetchError as exc:
                log.warning("%s", exc)
                forecast = unknown_forecast()
                notes.append("The weather feed did not respond, so indoor and outdoor ideas are mixed.")
        else:
            forecast = unknown_forecast()

    event_warnings: list[str] = []
    if events is None:
        if live:
            try:
                events, event_warnings = fetch_events(saturday, sunday)
            except FetchError as exc:
                log.warning("%s", exc)
                events = []
                notes.append(
                    "Weekend listings could not be read. These are places that are open anyway."
                )
        else:
            events = []
    notes.extend(event_warnings)

    seed = saturday.isoformat()
    spare_outdoor = forecast.one_dry_day
    free = select_band(
        pool_for(list(CATALOGUE), events, "free", saturday, sunday),
        forecast.bias,
        seed,
        spare_outdoor=spare_outdoor,
    )
    paid = select_band(
        pool_for(list(CATALOGUE), events, "paid", saturday, sunday),
        forecast.bias,
        seed,
        spare_outdoor=spare_outdoor,
    )
    if not any(pick.activity.kind == "event" for pick in [*free, *paid]):
        if not any(note.startswith("Weekend listings") for note in notes):
            notes.append(
                "No separate one-off events made the list, so these are places you can go anyway."
            )
    return Digest(saturday, sunday, forecast, free, paid, notes)
