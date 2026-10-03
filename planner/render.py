"""Plain-text and HTML versions of the Friday email."""

from datetime import date

from planner.config import HOME_NAME, RADIUS_MILES
from planner.model import Pick
from planner.weather import Forecast

AUDIENCE = {"family": "Whole family", "kids": "Kids"}
KIND = {"event": "On this weekend", "standing": "Open anytime"}
SETTING = {"indoor": "Indoor", "outdoor": "Outdoor", "either": "Indoor and outdoor"}


def _format_day(day: date) -> str:
    return f"{day.day} {day.strftime('%B')}"


def subject(saturday: date, sunday: date) -> str:
    return (
        f"Weekend of {_format_day(saturday)}–{_format_day(sunday)}: "
        "free and paid ideas from Livingston"
    )


def _item_block(index: int, pick: Pick) -> str:
    activity = pick.activity
    from planner.geo import format_miles

    tags = " · ".join(
        (
            KIND[activity.kind],
            AUDIENCE[activity.audience],
            SETTING[activity.setting],
            format_miles(pick.miles),
        )
    )
    lines = [
        f"{index}. {activity.name}",
        f"   {tags}",
        f"   {activity.area}. {activity.when}.",
        f"   {activity.summary}",
        f"   {activity.price_note}",
        f"   {activity.url}",
    ]
    return "\n".join(lines)


def _section(title: str, picks: list[Pick]) -> str:
    if not picks:
        body = "Nothing matched this list this weekend."
    else:
        body = "\n\n".join(_item_block(i, pick) for i, pick in enumerate(picks, start=1))
    return f"{title}\n\n{body}"


def render_text(
    saturday: date,
    sunday: date,
    forecast: Forecast,
    free: list[Pick],
    paid: list[Pick],
    notes: list[str],
) -> str:
    intro = (
        f"Weekend of {_format_day(saturday)} and {_format_day(sunday)}.\n"
        f"From {HOME_NAME}, within {RADIUS_MILES:.0f} miles as the crow flies, "
        "for an 11-year-old, a 13-year-old, and both of you. By car.\n"
        "Each idea is tagged Whole family (you all do it) or Kids "
        "(they do it, you take them)."
    )
    note_block = ""
    if notes:
        note_block = "\n\n" + "\n".join(notes)
    parts = [
        intro,
        "Weather\n\n" + forecast.summary,
        _section("Free", free),
        _section("Paid", paid),
        "Check opening times, tides and tickets before you go. "
        "Straight-line miles, so the drive can be a little longer."
        + note_block,
    ]
    return "\n\n".join(parts) + "\n"


def _html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _html_item(index: int, pick: Pick) -> str:
    from planner.geo import format_miles

    activity = pick.activity
    tags = " · ".join(
        (
            KIND[activity.kind],
            AUDIENCE[activity.audience],
            SETTING[activity.setting],
            format_miles(pick.miles),
        )
    )
    return (
        "<li style=\"margin:0 0 18px 0\">"
        f"<strong>{index}. {_html_escape(activity.name)}</strong><br>"
        f"<span style=\"color:#444\">{_html_escape(tags)}</span><br>"
        f"{_html_escape(activity.area)}. {_html_escape(activity.when)}.<br>"
        f"{_html_escape(activity.summary)}<br>"
        f"<span style=\"color:#444\">{_html_escape(activity.price_note)}</span><br>"
        f"<a href=\"{_html_escape(activity.url)}\">{_html_escape(activity.url)}</a>"
        "</li>"
    )


def render_html(
    saturday: date,
    sunday: date,
    forecast: Forecast,
    free: list[Pick],
    paid: list[Pick],
    notes: list[str],
) -> str:
    def items(picks: list[Pick]) -> str:
        if not picks:
            return "<p>Nothing matched this list this weekend.</p>"
        body = "".join(_html_item(i, pick) for i, pick in enumerate(picks, start=1))
        return f"<ol style=\"padding-left:18px\">{body}</ol>"

    notes_html = ""
    if notes:
        notes_html = "<p>" + "<br>".join(_html_escape(note) for note in notes) + "</p>"
    return f"""<!DOCTYPE html>
<html>
<body style="font-family:Georgia,serif;color:#1a1a1a;line-height:1.45;max-width:640px">
<p>Weekend of {_html_escape(_format_day(saturday))} and {_html_escape(_format_day(sunday))}.</p>
<p>From {HOME_NAME}, within {RADIUS_MILES:.0f} miles as the crow flies, for an 11-year-old, a 13-year-old, and both of you. By car. Each idea is tagged Whole family (you all do it) or Kids (they do it, you take them).</p>
<h2 style="font-size:18px">Weather</h2>
<p>{_html_escape(forecast.summary)}</p>
<h2 style="font-size:18px">Free</h2>
{items(free)}
<h2 style="font-size:18px">Paid</h2>
{items(paid)}
<p>Check opening times, tides and tickets before you go. Straight-line miles, so the drive can be a little longer.</p>
{notes_html}
</body>
</html>
"""
