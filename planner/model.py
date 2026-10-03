"""Shared activity shape for standing places and weekend events."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Activity:
    name: str
    summary: str
    url: str
    lat: float
    lon: float
    price: str  # free | paid
    audience: str  # family | kids
    setting: str  # indoor | outdoor | either
    category: str
    kind: str  # standing | event
    when: str
    price_note: str
    area: str
    season: tuple[int, int] | None = None

    def open_on(self, saturday: date, sunday: date) -> bool:
        if self.season is None:
            return True
        start, end = self.season
        return any(start <= day.month <= end for day in (saturday, sunday))


@dataclass(frozen=True)
class Pick:
    activity: Activity
    miles: float
