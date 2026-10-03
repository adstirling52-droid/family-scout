"""Weekend forecast for Livingston from Open-Meteo. No API key."""

import json
from dataclasses import dataclass
from datetime import date

from planner.config import HOME
from planner.http_util import FetchError, get_text

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"

# WMO codes that mean rain, showers, snow or thunder.
_WET_CODES = set(range(51, 68)) | set(range(71, 78)) | set(range(80, 83)) | {95, 96, 99}


@dataclass(frozen=True)
class DayForecast:
    day: date
    temp_min: float | None
    temp_max: float | None
    precip_mm: float | None
    precip_probability: int | None
    weather_code: int | None

    @property
    def wet(self) -> bool:
        if self.precip_probability is not None and self.precip_probability >= 50:
            return True
        if self.precip_mm is not None and self.precip_mm >= 1.0:
            return True
        if self.weather_code is not None and self.weather_code in _WET_CODES:
            return True
        return False

    def phrase(self) -> str:
        label = _sky(self.weather_code, self.wet)
        temps = ""
        if self.temp_max is not None:
            temps = f"{round(self.temp_max)}°C"
            if self.temp_min is not None:
                temps = f"{round(self.temp_min)}–{round(self.temp_max)}°C"
        chance = ""
        if self.precip_probability is not None:
            chance = f", {self.precip_probability}% chance of rain"
        bits = [part for part in (temps, label) if part]
        return f"{', '.join(bits)}{chance}" if bits else label


@dataclass(frozen=True)
class Forecast:
    saturday: DayForecast | None
    sunday: DayForecast | None
    bias: str  # indoor | outdoor | either
    summary: str
    available: bool
    one_dry_day: bool = False


def _sky(code: int | None, wet: bool) -> str:
    if code is None:
        return "wet" if wet else "forecast unavailable"
    if code in {0}:
        return "clear"
    if code in {1, 2, 3}:
        return "cloudy"
    if code in {45, 48}:
        return "fog"
    if code in set(range(71, 78)) | {85, 86}:
        return "snow"
    if code in {95, 96, 99}:
        return "thunder"
    if wet or code in _WET_CODES:
        return "rain"
    return "mixed"


def _bias(saturday: DayForecast | None, sunday: DayForecast | None) -> str:
    days = [day for day in (saturday, sunday) if day is not None]
    if not days:
        return "either"
    wet_days = [day for day in days if day.wet]
    if len(wet_days) == len(days):
        return "indoor"
    if wet_days:
        return "indoor"
    return "outdoor"


def _summary(saturday: DayForecast | None, sunday: DayForecast | None, bias: str) -> str:
    parts: list[str] = []
    if saturday:
        parts.append(f"Saturday: {saturday.phrase()}")
    if sunday:
        parts.append(f"Sunday: {sunday.phrase()}")
    detail = ". ".join(parts)
    if bias == "indoor" and saturday and sunday and saturday.wet and not sunday.wet:
        lean = "The list leans indoor because Saturday looks wet. Sunday is the better day to be outside."
    elif bias == "indoor" and saturday and sunday and sunday.wet and not saturday.wet:
        lean = "The list leans indoor because Sunday looks wet. Saturday is the better day to be outside."
    elif bias == "indoor":
        lean = "The list leans indoor because the weekend looks wet."
    elif bias == "outdoor":
        lean = "The weekend looks dry enough to favour outdoor plans."
    else:
        lean = "No weekend forecast was available, so indoor and outdoor ideas are mixed."
    return f"{detail}. {lean}" if detail else lean


def unknown_forecast() -> Forecast:
    summary = "No weekend forecast was available, so indoor and outdoor ideas are mixed."
    return Forecast(None, None, "either", summary, False)


def _day_from_row(day: date, payload: dict, index: int) -> DayForecast:
    daily = payload["daily"]

    def at(key: str) -> float | int | None:
        values = daily.get(key) or []
        if index >= len(values) or values[index] is None:
            return None
        return values[index]

    prob = at("precipitation_probability_max")
    return DayForecast(
        day=day,
        temp_min=_as_float(at("temperature_2m_min")),
        temp_max=_as_float(at("temperature_2m_max")),
        precip_mm=_as_float(at("precipitation_sum")),
        precip_probability=int(prob) if prob is not None else None,
        weather_code=int(at("weather_code")) if at("weather_code") is not None else None,
    )


def _as_float(value: float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def fetch_forecast(saturday: date, sunday: date) -> Forecast:
    lat, lon = HOME
    url = (
        f"{OPEN_METEO}?latitude={lat}&longitude={lon}"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
        "precipitation_sum,precipitation_probability_max"
        "&timezone=Europe%2FLondon&forecast_days=16"
    )
    payload = None
    last_error: Exception | None = None
    for _ in range(2):
        try:
            payload = json.loads(get_text(url, timeout=25))
            break
        except (FetchError, json.JSONDecodeError, KeyError) as exc:
            last_error = exc
    if payload is None:
        raise FetchError(f"weather forecast failed: {last_error}") from last_error

    dates = payload.get("daily", {}).get("time") or []
    by_date = {dates[i]: i for i in range(len(dates))}
    saturday_row = None
    sunday_row = None
    if saturday.isoformat() in by_date:
        saturday_row = _day_from_row(saturday, payload, by_date[saturday.isoformat()])
    if sunday.isoformat() in by_date:
        sunday_row = _day_from_row(sunday, payload, by_date[sunday.isoformat()])
    if saturday_row is None and sunday_row is None:
        raise FetchError("weather forecast did not include this weekend")
    bias = _bias(saturday_row, sunday_row)
    dry_days = [day for day in (saturday_row, sunday_row) if day is not None and not day.wet]
    wet_days = [day for day in (saturday_row, sunday_row) if day is not None and day.wet]
    return Forecast(
        saturday_row,
        sunday_row,
        bias,
        _summary(saturday_row, sunday_row, bias),
        True,
        one_dry_day=bool(dry_days) and bool(wet_days),
    )
