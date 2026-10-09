"""Selection, age, distance, schedule, and email text. No network."""

import unittest
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from planner.catalogue import CATALOGUE
from planner.config import LIST_SIZE, RADIUS_MILES
from planner.events import (
    overlaps_weekend,
    parse_listing,
    suitable_for_ages,
)
from planner.geo import miles_from_home, within_radius
from planner.mailer import MailConfigError, load_smtp
from planner.model import Activity
from planner.render import render_text
from planner.select import pool_for, select_band
from planner.weather import DayForecast, Forecast
from planner.weekend import coming_weekend, is_send_window
from planner.digest import build_digest


def _activity(**kwargs: object) -> Activity:
    data = dict(
        name="Place",
        summary="A place.",
        url="https://example.com/place",
        lat=55.8862,
        lon=-3.5178,
        price="free",
        audience="family",
        setting="indoor",
        category="museum",
        kind="standing",
        when="Open",
        price_note="Free",
        area="Livingston",
        season=None,
    )
    data.update(kwargs)
    return Activity(**data)  # type: ignore[arg-type]


class DistanceTests(unittest.TestCase):
    def test_catalogue_is_inside_20_miles(self) -> None:
        for place in CATALOGUE:
            miles = miles_from_home(place.lat, place.lon)
            self.assertLessEqual(
                miles,
                RADIUS_MILES,
                f"{place.name} is {miles:.1f} miles from Livingston",
            )

    def test_glasgow_is_outside(self) -> None:
        self.assertFalse(within_radius(55.864, -4.252))


class WeekendTests(unittest.TestCase):
    def test_friday_points_at_the_coming_saturday(self) -> None:
        friday = date(2026, 10, 9)  # Friday after Sat 3 Oct 2026
        self.assertEqual(friday.weekday(), 4)
        saturday, sunday = coming_weekend(friday)
        self.assertEqual(saturday, date(2026, 10, 10))
        self.assertEqual(sunday, date(2026, 10, 11))

    def test_saturday_uses_today(self) -> None:
        saturday, sunday = coming_weekend(date(2026, 10, 3))
        self.assertEqual((saturday, sunday), (date(2026, 10, 3), date(2026, 10, 4)))

    def test_sunday_looks_ahead(self) -> None:
        saturday, sunday = coming_weekend(date(2026, 10, 4))
        self.assertEqual(saturday, date(2026, 10, 10))
        self.assertEqual(sunday, date(2026, 10, 11))


class ScheduleTests(unittest.TestCase):
    def _friday(self, month: int) -> date:
        day = date(2026, month, 1)
        while day.weekday() != 4:
            day += timedelta(days=1)
        return day

    def test_winter_window_is_10_utc(self) -> None:
        friday = self._friday(1)
        utc = ZoneInfo("UTC")
        self.assertTrue(
            is_send_window(datetime(friday.year, friday.month, friday.day, 10, 15, tzinfo=utc))
        )
        self.assertFalse(
            is_send_window(datetime(friday.year, friday.month, friday.day, 9, 15, tzinfo=utc))
        )
        self.assertTrue(
            is_send_window(datetime(friday.year, friday.month, friday.day, 16, 52, tzinfo=utc))
        )

    def test_summer_window_is_09_utc(self) -> None:
        friday = self._friday(7)
        utc = ZoneInfo("UTC")
        self.assertFalse(
            is_send_window(datetime(friday.year, friday.month, friday.day, 8, 59, tzinfo=utc))
        )
        self.assertTrue(
            is_send_window(datetime(friday.year, friday.month, friday.day, 9, 5, tzinfo=utc))
        )
        self.assertTrue(
            is_send_window(datetime(friday.year, friday.month, friday.day, 16, 52, tzinfo=utc))
        )

    def test_ten_utc_sends_in_summer_and_winter(self) -> None:
        utc = ZoneInfo("UTC")
        for month in (1, 7):
            friday = self._friday(month)
            self.assertTrue(
                is_send_window(
                    datetime(friday.year, friday.month, friday.day, 10, 0, tzinfo=utc)
                )
            )


class AgeTests(unittest.TestCase):
    def test_rejects_toddler_and_narrow_ages(self) -> None:
        self.assertFalse(suitable_for_ages("Singing Kettle for little ones"))
        self.assertFalse(suitable_for_ages("sessions for 6-12 year olds"))
        self.assertFalse(suitable_for_ages("under 5s stay and play"))
        self.assertFalse(suitable_for_ages("P5-P7 art class"))
        self.assertFalse(suitable_for_ages("ends at the haunted pub"))
        self.assertFalse(suitable_for_ages("12+ only"))

    def test_all_ages_workshop_is_family_and_a_class_is_kids(self) -> None:
        from planner.events import _infer_audience

        self.assertEqual(
            _infer_audience("workshops and stalls for curious minds of all ages"),
            "family",
        )
        self.assertEqual(_infer_audience("Saturday morning dance classes"), "kids")

    def test_priced_ticket_stays_paid_even_if_under_8s_are_free(self) -> None:
        from planner.events import _price_kind

        priced = "£22 for adults / £15 for under 18s (under 8s go free)"
        self.assertEqual(_price_kind(priced, "Burke and Hare"), "paid")
        self.assertEqual(_price_kind("This is a free event", "Market"), "free")

    def test_keeps_this_age_and_all_ages(self) -> None:
        self.assertTrue(suitable_for_ages("a family day out at the market"))
        self.assertTrue(suitable_for_ages("children aged 3-16 years"))
        self.assertTrue(suitable_for_ages("great informal fun, 10yrs+"))


class ListingTests(unittest.TestCase):
    def test_parses_a_card_and_stops_before_sister_sites(self) -> None:
        page = """
        <div class="card event-card border-0">
          <a href="/event/1-market/"></a>
          <h4><a href="/event/1-market/">Linlithgow Artisan Market</a></h4>
          <div class="border-bottom-light-grey border-top-light-grey font-weight-bold py-1 small"><svg></svg>
          3rd October 2026</div>
          <div class="border-bottom-light-grey small py-1"><svg></svg>
          Linlithgow</div>
          <p class="card-text mt-3">A monthly market on the High Street.</p>
        </div>
        <h2>Family And Kids Events in Fife</h2>
        <div class="card event-card border-0">
          <a href="/event/2-far/"></a>
          <h4><a href="/event/2-far/">Knockhill Racing</a></h4>
          <div class="font-weight-bold py-1 small"><svg></svg>3rd October 2026</div>
          <div class="border-bottom-light-grey small py-1"><svg></svg>Knockhill</div>
          <p class="card-text mt-3">Racing.</p>
        </div>
        """
        cards = parse_listing(page)
        self.assertEqual([card["title"] for card in cards], ["Linlithgow Artisan Market"])
        self.assertTrue(overlaps_weekend(cards[0]["when"], date(2026, 10, 3), date(2026, 10, 4)))


class SelectionTests(unittest.TestCase):
    def _pool(self) -> list[Activity]:
        items = []
        for index in range(4):
            items.append(
                _activity(
                    name=f"Indoor museum {index}",
                    price="free",
                    audience="family",
                    setting="indoor",
                    category="museum" if index < 3 else "science",
                    kind="standing",
                )
            )
        items.append(
            _activity(
                name="Skatepark",
                price="free",
                audience="kids",
                setting="outdoor",
                category="sport",
                kind="standing",
            )
        )
        items.append(
            _activity(
                name="Wet walk",
                price="free",
                audience="family",
                setting="outdoor",
                category="outdoors",
                kind="standing",
            )
        )
        items.append(
            _activity(
                name="Market",
                price="free",
                audience="family",
                setting="outdoor",
                category="market",
                kind="event",
                summary="On Saturday.",
            )
        )
        items.append(
            _activity(
                name="Indoor trail",
                price="free",
                audience="family",
                setting="indoor",
                category="science",
                kind="event",
            )
        )
        return items

    def test_wet_weekend_leans_indoor_and_keeps_both_kinds(self) -> None:
        picks = select_band(self._pool(), "indoor", "2026-10-10")
        self.assertEqual(len(picks), LIST_SIZE)
        names = [pick.activity.name for pick in picks]
        self.assertIn("Indoor trail", names)
        self.assertTrue(any(pick.activity.kind == "standing" for pick in picks))
        self.assertTrue(any(pick.activity.audience == "kids" for pick in picks))
        self.assertTrue(any(pick.activity.audience == "family" for pick in picks))
        indoorish = [
            pick for pick in picks if pick.activity.setting in {"indoor", "either"}
        ]
        self.assertGreaterEqual(len(indoorish), 4)

    def test_dry_weekend_includes_outdoor(self) -> None:
        picks = select_band(self._pool(), "outdoor", "2026-10-10")
        self.assertTrue(any(pick.activity.setting == "outdoor" for pick in picks))

    def test_closed_season_is_left_out(self) -> None:
        winter = _activity(name="Summer park", season=(5, 9), setting="outdoor", category="outdoors")
        saturday, sunday = date(2026, 10, 10), date(2026, 10, 11)
        pooled = pool_for([winter], [], "free", saturday, sunday)
        self.assertEqual(pooled, [])

    def test_digest_text_has_two_lists(self) -> None:
        forecast = Forecast(
            saturday=DayForecast(date(2026, 10, 10), 8, 14, 0.2, 20, 1),
            sunday=DayForecast(date(2026, 10, 11), 7, 13, 4.0, 80, 61),
            bias="indoor",
            summary="Sunday looks wet.",
            available=True,
        )
        digest = build_digest(
            today=date(2026, 10, 9),
            forecast=forecast,
            events=[],
            live=False,
        )
        text = render_text(
            digest.saturday,
            digest.sunday,
            digest.forecast,
            digest.free,
            digest.paid,
            digest.notes,
        )
        self.assertIn("Free", text)
        self.assertIn("Paid", text)
        self.assertEqual(len(digest.free), LIST_SIZE)
        self.assertEqual(len(digest.paid), LIST_SIZE)
        audiences = {pick.activity.audience for pick in digest.free + digest.paid}
        self.assertIn("family", audiences)
        self.assertIn("kids", audiences)
        indoorish = [
            pick
            for pick in digest.free
            if pick.activity.setting in {"indoor", "either"}
        ]
        self.assertGreaterEqual(len(indoorish), 4)


class UrlTests(unittest.TestCase):
    def test_unicode_in_a_path_stays_ascii(self) -> None:
        from planner.http_util import _ascii_url

        url = _ascii_url("https://example.com/event/deacon\u2019s-cabinet/")
        url.encode("ascii")
        self.assertIn("%E2%80%99", url)


class MailTests(unittest.TestCase):
    def test_missing_smtp_is_an_error(self) -> None:
        import os

        for key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM", "RESEND_API_KEY"):
            os.environ.pop(key, None)
        with self.assertRaises(MailConfigError):
            load_smtp("Alan@alanstirling.com")

    def test_resend_key_fills_the_relay_settings(self) -> None:
        import os

        for key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM", "SMTP_PORT"):
            os.environ.pop(key, None)
        os.environ["RESEND_API_KEY"] = "re_test_key"
        try:
            settings = load_smtp("Alan@alanstirling.com")
        finally:
            os.environ.pop("RESEND_API_KEY", None)
        self.assertEqual(settings.host, "smtp.resend.com")
        self.assertEqual(settings.user, "resend")
        self.assertEqual(settings.password, "re_test_key")
        self.assertEqual(settings.sender, "onboarding@resend.dev")
        self.assertEqual(settings.recipient, "Alan@alanstirling.com")


if __name__ == "__main__":
    unittest.main()
