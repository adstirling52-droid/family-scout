# Weekend planner

Friday email for a family based in Livingston: an 11-year-old, a 13-year-old, and both parents, by car.

Related: [Friday email setup](../ops/friday-email.md), [ADR 0002](../adr/0002-friday-email-via-github-actions.md), [ADR 0003](../adr/0003-resend-free-plan.md).

## Behaviour

| Step | What | Where |
| --- | --- | --- |
| Weekend | Monday–Saturday: the Saturday and Sunday of this week. Sunday: the next weekend. | `planner/weekend.py` |
| Weather | Daily forecast for Livingston. A day is wet if the chance of rain is 50% or more, rainfall is at least 1 mm, or the weather code is rain, snow, or thunder. One wet day is enough to lean indoor, and the email names the drier day. If the other day is dry, one outdoor event is kept for it. | `planner/weather.py` |
| Events | What's On Edinburgh family-and-kids page for Saturday and for Sunday. Drop toddler and under-7 sessions, classes whose ages miss 11 or 13, pubs and 18+ nights, and anything outside 20 miles. Sister-site blocks (Fife, Glasgow, and the rest) are not read. | `planner/events.py` |
| Standing places | Curated venues, some only in certain months (Jupiter Artland, Conifox's outdoor park, House of the Binns). | `planner/catalogue.py` |
| Pick | 6 free and 6 paid. Prefer a mix of "on this weekend" and "open anytime", and of Whole family and Kids. Prefer indoor when the weekend is wet, outdoor when it is dry. Same Saturday always picks the same list. | `planner/select.py` |
| Send | Plain text and HTML, Friday 10:00 Europe/London, via Resend's free SMTP relay. | `planner/render.py`, `planner/mailer.py` |

Tags:

| Tag | Means |
| --- | --- |
| Whole family | You all do it together |
| Kids | They do the activity; you take them and can join or wait |
| On this weekend | A listed event for that Saturday or Sunday |
| Open anytime | A standing place |

Distance is a straight line from The Centre, Almondvale (`55.8862, -3.5178`). The drive can be longer. 20 miles is the cut-off.

## Extension points

- Add a venue in `planner/catalogue.py`. Set `audience` to `family` or `kids`, `price` to `free` or `paid`, and `setting` to `indoor`, `outdoor`, or `either`.
- Add a town the event parser should recognise in `GAZETTEER` in `planner/events.py`.
- Change list length with `LIST_SIZE` in `planner/config.py`.

## Intentionally not handled

- Public transport, walking-only trips, or a budget cap.
- Toddler soft play and sessions aimed under about 10, or adults-only nights.
- Booking tickets. The email links out; it does not reserve anything.
- Places beyond 20 miles in a straight line (Glasgow, Stirling, North Berwick, and similar).

## Failure and fallback

| Failure | What the email does |
| --- | --- |
| Open-Meteo is down | Still sends. Says the forecast was missing and does not lean indoor or outdoor. |
| What's On Edinburgh is down or the HTML changed | Still sends the standing places, and says the listings could not be read. |
| An event has no price on its page | That event is left out, so a paid event is not labelled free. |
| `RESEND_API_KEY` is missing | The run fails and prints the digest. Nothing is sent. |
