"""Pick 6 free and 6 paid ideas for one weekend."""

import zlib
from datetime import date

from planner.config import LIST_SIZE
from planner.geo import miles_from_home, within_radius
from planner.model import Activity, Pick

Bias = str


def score(activity: Activity, bias: Bias, seed: str) -> float:
    setting_score = {
        "indoor": {"indoor": 6.0, "either": 3.0, "outdoor": 0.0},
        "outdoor": {"outdoor": 5.0, "either": 2.5, "indoor": 0.5},
        "either": {"indoor": 1.0, "either": 1.0, "outdoor": 1.0},
    }[bias][activity.setting]
    # Same weekend always produces the same order. Next weekend moves.
    jitter = (zlib.crc32(f"{seed}|{activity.name}".encode()) % 1000) / 1000
    event_boost = 3.0 if activity.kind == "event" else 0.0
    return setting_score + event_boost + jitter


def _same_event_place(item: Activity, picked: list[Activity]) -> bool:
    if item.kind != "event":
        return False
    key = item.area.split(",")[0].strip().lower()
    if len(key) < 8:
        return False
    for other in picked:
        if other.kind != "event":
            continue
        if other.area.split(",")[0].strip().lower() == key:
            return True
    return False


def _matches_bias(activity: Activity, bias: Bias) -> bool:
    if bias == "indoor":
        return activity.setting in {"indoor", "either"}
    if bias == "outdoor":
        return activity.setting in {"outdoor", "either"}
    return True


def select_band(
    items: list[Activity],
    bias: Bias,
    seed: str,
    size: int = LIST_SIZE,
    spare_outdoor: bool = False,
) -> list[Pick]:
    ranked = sorted(items, key=lambda item: (-score(item, bias, seed), item.name))
    picked: list[Activity] = []

    def count(pred) -> int:
        return sum(1 for item in picked if pred(item))

    def best(pred, limit_category: bool = True) -> Activity | None:
        for item in ranked:
            if item in picked or not pred(item):
                continue
            if limit_category and count(lambda chosen: chosen.category == item.category) >= 2:
                continue
            if _same_event_place(item, picked):
                continue
            return item
        return None

    def take(pred, need: int, limit_category: bool = True) -> None:
        while count(pred) < need and len(picked) < size:
            item = best(pred, limit_category=limit_category)
            if item is None and limit_category:
                item = best(pred, limit_category=False)
            if item is None:
                return
            picked.append(item)

    # What's on, and places that are always there.
    # If only one weekend day is wet, keep an outdoor event for the dry day.
    event_bias_target = 1 if spare_outdoor else 2
    take(lambda item: item.kind == "event" and _matches_bias(item, bias), event_bias_target)
    if spare_outdoor:
        take(lambda item: item.kind == "event" and item.setting == "outdoor", 1)
    take(lambda item: item.kind == "event", 2)
    take(lambda item: item.kind == "standing" and _matches_bias(item, bias), 2)
    # Both tags, preferring the weather.
    take(lambda item: item.audience == "kids" and _matches_bias(item, bias), 2)
    take(lambda item: item.audience == "kids", 1)
    take(lambda item: item.audience == "family" and _matches_bias(item, bias), 2)

    take(lambda item: _matches_bias(item, bias), size)
    take(lambda item: True, size)

    picked.sort(key=lambda item: (0 if item.kind == "event" else 1, -score(item, bias, seed), item.name))
    return [Pick(activity=item, miles=miles_from_home(item.lat, item.lon)) for item in picked[:size]]


def pool_for(
    standing: list[Activity],
    events: list[Activity],
    price: str,
    saturday: date,
    sunday: date,
) -> list[Activity]:
    chosen: list[Activity] = []
    seen: set[str] = set()
    for item in [*events, *standing]:
        if item.price != price or not item.open_on(saturday, sunday):
            continue
        if not within_radius(item.lat, item.lon):
            continue
        if item.name in seen:
            continue
        seen.add(item.name)
        chosen.append(item)
    return chosen
