"""Weekend events from the What's On Edinburgh family-and-kids listings.

The page covers Edinburgh and the West Lothian towns that list there.
Pages for Fife, Glasgow and other sister sites are ignored. Each event is
kept only if it suits an 11-year-old and a 13-year-old and sits inside the
20-mile radius.
"""

import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from planner.geo import miles_from_home, within_radius
from planner.http_util import FetchError, get_text
from planner.model import Activity

log = logging.getLogger(__name__)

BASE = "https://www.whatsoninedinburgh.co.uk"
SISTER_MARKERS = (
    "Family And Kids Events in Fife",
    "Family And Kids Events in Glasgow",
    "Family And Kids Events in Stirling",
    "Family And Kids Events in Lanarkshire",
)

# Town and neighbourhood pins. Longest name wins, then the radius check.
GAZETTEER: dict[str, tuple[float, float]] = {
    "livingston": (55.8862, -3.5178),
    "linlithgow": (55.9770, -3.6000),
    "bathgate": (55.9020, -3.6430),
    "west calder": (55.8520, -3.5690),
    "east calder": (55.8970, -3.4630),
    "mid calder": (55.8920, -3.4780),
    "broxburn": (55.9340, -3.4710),
    "uphall": (55.9290, -3.5020),
    "winchburgh": (55.9580, -3.4640),
    "whitburn": (55.8670, -3.6870),
    "armadale": (55.8980, -3.7050),
    "fauldhouse": (55.8270, -3.7080),
    "blackburn": (55.8780, -3.6240),
    "west linton": (55.7530, -3.3550),
    "south queensferry": (55.9900, -3.3980),
    "craigies": (55.9780, -3.3520),
    "dynamic earth": (55.9504, -3.1745),
    "howden park": (55.8834, -3.5157),
    "holyrood": (55.9504, -3.1745),
    "queensferry": (55.9900, -3.3980),
    "kirkliston": (55.9560, -3.4030),
    "ratho": (55.9220, -3.3790),
    "balerno": (55.8840, -3.3390),
    "currie": (55.8960, -3.3080),
    "juniper green": (55.9030, -3.2850),
    "colinton": (55.9080, -3.2560),
    "craiglockhart": (55.9180, -3.2440),
    "kings buildings": (55.9230, -3.1750),
    "edinburgh south": (55.9230, -3.1780),
    "morningside": (55.9270, -3.2090),
    "marchmont": (55.9380, -3.1940),
    "newington": (55.9380, -3.1740),
    "grassmarket": (55.9470, -3.1960),
    "edinburgh old town": (55.9490, -3.1910),
    "royal mile": (55.9500, -3.1870),
    "stockbridge": (55.9580, -3.2100),
    "leith": (55.9800, -3.1730),
    "ocean terminal": (55.9820, -3.1760),
    "portobello": (55.9530, -3.1140),
    "corstorphine": (55.9410, -3.2820),
    "gorgie": (55.9380, -3.2400),
    "haymarket": (55.9460, -3.2180),
    "fountainbridge": (55.9430, -3.2090),
    "tollcross": (55.9410, -3.2030),
    "barnton": (55.9620, -3.3080),
    "davidson's mains": (55.9670, -3.2750),
    "davidsons mains": (55.9670, -3.2750),
    "dalmeny": (55.9850, -3.3700),
    "house of the binns": (55.9890, -3.5260),
    "abercorn": (55.9890, -3.5260),
    "dalkeith": (55.8960, -3.0680),
    "bonnyrigg": (55.8740, -3.1030),
    "penicuik": (55.8310, -3.2230),
    "loanhead": (55.8790, -3.1480),
    "lasswade": (55.8800, -3.1170),
    "musselburgh": (55.9420, -3.0540),
    "wallyford": (55.9420, -3.0140),
    "craigmillar": (55.9250, -3.1350),
    "falkirk": (56.0010, -3.7840),
    "grangemouth": (56.0110, -3.7170),
    "polmont": (55.9890, -3.7070),
    "bo'ness": (56.0170, -3.6080),
    "boness": (56.0170, -3.6080),
    "blackness": (56.0060, -3.5160),
    "north queensferry": (56.0090, -3.3940),
    "inverkeithing": (56.0300, -3.3980),
    "dunfermline": (56.0720, -3.4390),
    "knockhill": (56.1310, -3.5030),
    "edinburgh": (55.9530, -3.1880),
    # Outside the radius on purpose, so a match is dropped rather than
    # treated as Edinburgh.
    "kirkcaldy": (56.1170, -3.1600),
    "glenrothes": (56.1960, -3.1730),
    "stirling": (56.1170, -3.9370),
    "glasgow": (55.8640, -4.2520),
    "hamilton": (55.7770, -4.0390),
    "motherwell": (55.7900, -3.9920),
    "north berwick": (56.0580, -2.7170),
    "haddington": (55.9560, -2.7830),
    "east linton": (55.9870, -2.6560),
    "tranent": (55.9450, -2.9540),
    "prestonpans": (55.9590, -2.9850),
}

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

_TOO_YOUNG = re.compile(
    r"\b("
    r"0\s*[-–to]+\s*5|under\s*[0-7]\b|under\s*[0-7]\s*s|"
    r"[1-7]\s*(?:years?|yrs?)?\s*and under|"
    r"toddlers?|bab(?:y|ies)|early years|bookbug|nursery|"
    r"preschool|pre-school|singing kettle|little ones|soft play|"
    r"babes in arms"
    r")\b",
    re.I,
)
_ADULT_ONLY = re.compile(
    r"\b(18\s*\+|over\s*18|adults only|nightclub|pubs?)\b",
    re.I,
)
_AGE_RANGE = re.compile(
    r"(?:ages?|aged|years?(?:\s*old)?)\s*(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})",
    re.I,
)
_AGE_RANGE_TAIL = re.compile(
    r"\b(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})\s*(?:years?|yrs?)\b",
    re.I,
)
_PRIMARY = re.compile(r"\bP(\d)\s*(?:-|–|to)\s*P(\d)\b", re.I)
_SECONDARY = re.compile(r"\bS(\d)\s*(?:-|–|to)\s*S(\d)\b", re.I)
_PLUS = re.compile(r"\b(\d{1,2})\s*(?:years?|yrs?)?\s*\+", re.I)
_DATE = re.compile(
    r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})",
    re.I,
)


def listing_url(day: date) -> str:
    return (
        f"{BASE}/events/family-and-kids/"
        f"{day.year:04d}/{day.month:02d}/{day.day:02d}/"
    )


def suitable_for_ages(text: str) -> bool:
    """True when an 11-year-old and a 13-year-old can both do it."""
    if _TOO_YOUNG.search(text) or _ADULT_ONLY.search(text):
        return False
    for pattern in (_AGE_RANGE, _AGE_RANGE_TAIL):
        for match in pattern.finditer(text):
            low, high = int(match.group(1)), int(match.group(2))
            if high > 25:
                continue
            if not (low <= 11 and high >= 13):
                return False
    primary = _PRIMARY.search(text)
    if primary:
        low = int(primary.group(1)) + 4
        high = int(primary.group(2)) + 4
        if not (low <= 11 and high >= 13):
            return False
    secondary = _SECONDARY.search(text)
    if secondary:
        low = int(secondary.group(1)) + 11
        high = int(secondary.group(2)) + 11
        if not (low <= 11 and high >= 13):
            return False
    for match in _PLUS.finditer(text):
        minimum = int(match.group(1))
        if minimum > 11:
            return False
    return True


def parse_dates(text: str) -> tuple[date, date] | None:
    found: list[date] = []
    for day_s, month_s, year_s in _DATE.findall(text):
        month = _MONTHS.get(month_s.lower())
        if month is None:
            continue
        try:
            found.append(date(int(year_s), month, int(day_s)))
        except ValueError:
            continue
    if not found:
        return None
    return min(found), max(found)


def overlaps_weekend(text: str, saturday: date, sunday: date) -> bool:
    span = parse_dates(text)
    if span is None:
        return False
    start, end = span
    return start <= sunday and end >= saturday


def locate(text: str) -> tuple[float, float] | None:
    lowered = text.lower()
    matches = [name for name in GAZETTEER if name in lowered]
    if not matches:
        return None
    name = max(matches, key=len)
    return GAZETTEER[name]


def _clean(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_listing(page: str) -> list[dict[str, str]]:
    cut = len(page)
    for marker in SISTER_MARKERS:
        index = page.find(marker)
        if index != -1:
            cut = min(cut, index)
    body = page[:cut]
    cards: list[dict[str, str]] = []
    parts = body.split('class="card event-card')
    for chunk in parts[1:]:
        href = re.search(r'href="(/event/[^"]+)"', chunk)
        title = re.search(r"<h4[^>]*>\s*<a[^>]*>(.*?)</a>", chunk, re.S)
        when = re.search(
            r'font-weight-bold py-1 small">.*?</svg>\s*([^<]+)',
            chunk,
            re.S,
        )
        area = re.search(
            r'border-bottom-light-grey small py-1">.*?</svg>\s*([^<]+)',
            chunk,
            re.S,
        )
        blurb = re.search(r'<p class="card-text[^"]*">(.*?)</p>', chunk, re.S)
        if not href or not title:
            continue
        cards.append(
            {
                "path": href.group(1),
                "title": _clean(title.group(1)),
                "when": _clean(when.group(1)) if when else "",
                "area": _clean(area.group(1)) if area else "",
                "blurb": _clean(blurb.group(1)) if blurb else "",
            }
        )
    return cards


def _infer_category(text: str) -> str:
    lowered = text.lower()
    rules = (
        ("market", ("market", "farmers' market", "farmers market")),
        ("farm", ("pumpkin", "farm", "orchard")),
        ("animals", ("zoo", "wildlife", "fungi", "animal")),
        ("museum", ("museum", "exhibition", "gallery")),
        ("adventure", ("escape room", "escape", "high ropes", "go ape")),
        ("sport", ("climb", "swim", "dance", "ceilidh", "sport")),
        ("history", ("castle", "palace", "tour", "heritage", "close", "bunker")),
        ("outdoors", ("walk", "trail", "garden", "park", "outdoor")),
        ("show", ("cinema", "show", "theatre", "concert", "choir")),
    )
    for category, words in rules:
        if any(word in lowered for word in words):
            return category
    return "day-out"


def _infer_setting(text: str) -> str:
    lowered = text.lower()
    indoor_words = (
        "museum",
        "exhibition",
        "gallery",
        "cinema",
        "escape room",
        "close",
        "indoor",
        "theatre",
        "science",
        "bunker",
    )
    outdoor_words = (
        "market",
        "walk",
        "trail",
        "garden",
        "park",
        "farm",
        "pumpkin",
        "outdoor",
        "woodland",
        "foray",
    )
    indoor = any(word in lowered for word in indoor_words)
    outdoor = any(word in lowered for word in outdoor_words)
    if indoor and outdoor:
        return "either"
    if indoor:
        return "indoor"
    if outdoor:
        return "outdoor"
    return "either"


def _infer_audience(text: str) -> str:
    lowered = text.lower()
    if any(phrase in lowered for phrase in ("all ages", "whole family", "for all the family")):
        return "family"
    if re.search(r"\b(class|classes|club|choir|juniors?)\b", lowered):
        return "kids"
    if "your child" in lowered or "for children" in lowered:
        return "kids"
    return "family"


def _price_kind(price_text: str, title: str) -> str | None:
    lowered = price_text.lower().strip()
    if not lowered:
        return None
    # "under 8s go free" must not turn a priced ticket into a free event.
    if re.search(r"£\s*\d", lowered) or re.search(r"\b\d+(?:\.\d{2})?\s+for\b", lowered):
        return "paid"
    if re.search(r"\b(this is a free event|free entry|free to attend|admission free)\b", lowered):
        return "free"
    if lowered in {"free", "free event"} or lowered.startswith("free "):
        return "free"
    if "market" in title.lower() and "see event website" in lowered:
        return "free"
    return "paid"


def _is_term_course(text: str) -> bool:
    return re.search(r"\b(for the term|per term|term time|this term)\b", text, re.I) is not None


def _first_sentence(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    match = re.match(r"^(.{20,}?[.!?])(?:\s|$)", stripped)
    sentence = match.group(1) if match else stripped
    if len(sentence) > 220:
        return sentence[:217].rstrip() + "..."
    return sentence


def activity_from_card(
    card: dict[str, str],
    price_text: str,
    saturday: date,
    sunday: date,
    address: str = "",
) -> Activity | None:
    combined = " ".join((card["title"], card["blurb"], card["area"], address, price_text))
    if not suitable_for_ages(combined) or _is_term_course(combined):
        return None
    if card["when"] and not overlaps_weekend(card["when"], saturday, sunday):
        return None
    point = (
        locate(card["area"])
        or locate(address)
        or locate(card["title"])
        or locate(card["blurb"])
    )
    if point is None or not within_radius(*point):
        return None
    kind = _price_kind(price_text, card["title"])
    if kind is None:
        return None
    where = card["area"] or address or "see listing"
    summary = _first_sentence(card["blurb"]) or f"Listed in {where} this weekend."
    return Activity(
        name=card["title"],
        summary=summary,
        url=BASE + card["path"],
        lat=point[0],
        lon=point[1],
        price=kind,
        audience=_infer_audience(combined),
        setting=_infer_setting(combined),
        category=_infer_category(combined),
        kind="event",
        when=card["when"] or "This weekend",
        price_note=price_text[:140],
        area=where,
    )


def _price_from_detail(page: str) -> str:
    # The first cell is an icon. The price is the next cell.
    match = re.search(r"<!-- event price -->.*?</td>\s*<td>(.*?)</td>", page, re.S)
    if not match:
        return ""
    return _clean(match.group(1))


def _address_from_detail(page: str) -> str:
    match = re.search(r'itemprop="address"[^>]*content="([^"]*)"', page, re.S)
    if not match:
        return ""
    return _clean(match.group(1))


def fetch_events(saturday: date, sunday: date) -> tuple[list[Activity], list[str]]:
    """Return suitable events and any warnings. Raises FetchError if both days fail."""
    warnings: list[str] = []
    cards: list[dict[str, str]] = []
    failures = 0
    for day in (saturday, sunday):
        url = listing_url(day)
        try:
            cards.extend(parse_listing(get_text(url)))
        except FetchError as exc:
            failures += 1
            warnings.append(f"Could not read the {day.strftime('%A')} listings ({exc}).")
            log.warning("%s", exc)
    if failures == 2:
        raise FetchError("weekend event listings could not be read")

    deduped: dict[str, dict[str, str]] = {}
    for card in cards:
        deduped.setdefault(card["path"], card)
    candidates = []
    for card in deduped.values():
        combined = " ".join((card["title"], card["blurb"], card["area"]))
        if not suitable_for_ages(combined):
            continue
        if card["when"] and not overlaps_weekend(card["when"], saturday, sunday):
            continue
        # Drop only when the listing already names a place outside the radius.
        # A missing place is resolved from the event page.
        point = locate(card["area"]) or locate(card["title"]) or locate(card["blurb"])
        if point is not None and not within_radius(*point):
            continue
        candidates.append(card)

    # Cap detail fetches. Prefer listings that are not a long repeating class.
    candidates = candidates[:24]
    details: dict[str, tuple[str, str]] = {}

    def load(card: dict[str, str]) -> tuple[str, str, str]:
        page = get_text(BASE + card["path"])
        return card["path"], _price_from_detail(page), _address_from_detail(page)

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(load, card) for card in candidates]
        for future in as_completed(futures):
            try:
                path, price, address = future.result()
            except (FetchError, UnicodeError, OSError) as exc:
                log.warning("Event detail skipped: %s", exc)
                continue
            details[path] = (price, address)

    events: list[Activity] = []
    seen: set[str] = set()
    for card in candidates:
        price, address = details.get(card["path"], ("", ""))
        activity = activity_from_card(card, price, saturday, sunday, address)
        if activity is None or activity.url in seen:
            continue
        seen.add(activity.url)
        events.append(activity)
    events.sort(key=lambda item: (item.price, miles_from_home(item.lat, item.lon), item.name))
    return events, warnings
