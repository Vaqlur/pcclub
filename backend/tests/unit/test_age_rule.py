from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.domain.age_rule import adult_from, can_play_at, is_minor_at, violates_night_restriction

ALMATY = ZoneInfo("Asia/Almaty")
MINOR = date(2010, 3, 10)  # 16 years old in June 2026
ADULT = date(2000, 3, 10)


def local(day: int, hour: int, minute: int = 0, *, month: int = 6, year: int = 2026) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=ALMATY)


def test_almaty_is_utc_plus_5():
    # Kazakhstan moved to a single UTC+5 zone on 2024-03-01; the rule depends on it.
    assert local(1, 22).utcoffset() == timedelta(hours=5)


# --- adult_from ------------------------------------------------------------------------------


def test_adult_from_regular_birthday():
    assert adult_from(date(2008, 11, 11)) == date(2026, 11, 11)


def test_adult_from_leap_day_in_non_leap_year():
    assert adult_from(date(2008, 2, 29)) == date(2026, 3, 1)


def test_adult_from_leap_day_in_leap_year():
    assert adult_from(date(2010, 2, 28), adult_age=18) == date(2028, 2, 28)
    assert adult_from(date(2004, 2, 29), adult_age=20) == date(2024, 2, 29)


# --- minors: boundary table ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("start", "end", "violates"),
    [
        (local(1, 14), local(1, 16), False),  # afternoon
        (local(1, 20), local(1, 22), False),  # ends exactly at 22:00
        (local(1, 21), local(1, 22, 30), True),  # 30 minutes into the night
        (local(1, 21), local(1, 23), True),
        (local(1, 22), local(1, 23), True),  # starts exactly at 22:00
        (local(1, 23), local(2, 1), True),  # across midnight
        (local(2, 0), local(2, 2), True),  # after midnight
        (local(2, 5), local(2, 6), True),  # ends exactly at 06:00 but is inside the night
        (local(2, 5), local(2, 7), True),
        (local(2, 5, 30), local(2, 6, 30), True),
        (local(2, 6), local(2, 8), False),  # starts exactly at 06:00
        (local(2, 6), local(2, 22), False),  # the whole allowed day
        (local(2, 6), local(2, 22, 30), True),
        (local(1, 12), local(2, 12), True),  # 24h booking contains a whole night
    ],
)
def test_minor_boundaries(start, end, violates):
    assert violates_night_restriction(MINOR, start, end, ALMATY) is violates


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (local(1, 21), local(1, 23)),
        (local(1, 22), local(2, 6)),
        (local(2, 0), local(2, 2)),
        (local(1, 12), local(2, 12)),
    ],
)
def test_adults_are_never_restricted(start, end):
    assert violates_night_restriction(ADULT, start, end, ALMATY) is False


# --- the 18th birthday -----------------------------------------------------------------------

BIRTHDAY_BOY = date(2008, 6, 15)  # turns 18 on 2026-06-15


def test_day_before_18th_birthday_is_still_restricted():
    assert violates_night_restriction(BIRTHDAY_BOY, local(14, 21), local(14, 23), ALMATY)


def test_booking_running_into_18th_birthday_is_judged_before_midnight():
    # 23:00 on the 14th is still a minor at night, even though they turn 18 at 00:00.
    assert violates_night_restriction(BIRTHDAY_BOY, local(14, 23), local(15, 1), ALMATY)


def test_from_midnight_of_18th_birthday_is_allowed():
    assert not violates_night_restriction(BIRTHDAY_BOY, local(15, 0), local(15, 3), ALMATY)
    assert not violates_night_restriction(BIRTHDAY_BOY, local(15, 22), local(16, 2), ALMATY)


def test_evening_until_22_then_adult_after_midnight_is_not_enough():
    # 20:00-22:00 is fine for a minor, and 22:00 onwards on the 14th is not.
    assert not violates_night_restriction(BIRTHDAY_BOY, local(14, 20), local(14, 22), ALMATY)
    assert violates_night_restriction(BIRTHDAY_BOY, local(14, 20), local(15, 2), ALMATY)


def test_leap_day_birthday_becomes_adult_on_march_1():
    born = date(2008, 2, 29)
    assert violates_night_restriction(born, local(28, 22, month=2), local(28, 23, month=2), ALMATY)
    assert not violates_night_restriction(born, local(1, 0, month=3), local(1, 2, month=3), ALMATY)


# --- time zones ------------------------------------------------------------------------------


def test_rule_uses_club_local_time_not_utc():
    # 16:30-17:30 UTC is 21:30-22:30 in Almaty -> restricted, although it is afternoon in UTC.
    start = datetime(2026, 6, 1, 16, 30, tzinfo=UTC)
    end = datetime(2026, 6, 1, 17, 30, tzinfo=UTC)
    assert violates_night_restriction(MINOR, start, end, ALMATY)
    # 01:00-03:00 UTC is 06:00-08:00 in Almaty -> allowed, although it is night in UTC.
    start = datetime(2026, 6, 1, 1, 0, tzinfo=UTC)
    end = datetime(2026, 6, 1, 3, 0, tzinfo=UTC)
    assert not violates_night_restriction(MINOR, start, end, ALMATY)


def test_birthday_boundary_is_club_local():
    # 19:30 UTC on the 14th is already 00:30 on the 15th (the 18th birthday) in Almaty.
    start = datetime(2026, 6, 14, 19, 30, tzinfo=UTC)
    assert not violates_night_restriction(BIRTHDAY_BOY, start, start + timedelta(hours=1), ALMATY)
    assert not is_minor_at(BIRTHDAY_BOY, start, ALMATY)
    assert is_minor_at(BIRTHDAY_BOY, start - timedelta(hours=1), ALMATY)


def test_same_instant_in_different_clubs():
    # 17:00 UTC is 22:00 in Almaty (night) but 19:00 in Berlin (evening).
    start = datetime(2026, 1, 10, 17, 0, tzinfo=UTC)
    end = start + timedelta(hours=1)
    assert violates_night_restriction(MINOR, start, end, ALMATY)
    assert not violates_night_restriction(MINOR, start, end, ZoneInfo("Europe/Berlin"))


# --- configuration and misuse ----------------------------------------------------------------


def test_custom_night_window_and_age():
    kwargs = {"night_start": time(23, 0), "night_end": time(7, 0)}
    assert not violates_night_restriction(MINOR, local(1, 21), local(1, 23), ALMATY, **kwargs)
    assert violates_night_restriction(MINOR, local(2, 6), local(2, 8), ALMATY, **kwargs)
    # A 16-year-old is an adult under adult_age=16.
    assert not violates_night_restriction(MINOR, local(1, 22), local(1, 23), ALMATY, adult_age=16)


def test_night_window_within_one_day():
    kwargs = {"night_start": time(1, 0), "night_end": time(5, 0)}
    assert violates_night_restriction(MINOR, local(2, 4), local(2, 6), ALMATY, **kwargs)
    assert not violates_night_restriction(MINOR, local(2, 5), local(2, 7), ALMATY, **kwargs)
    assert not violates_night_restriction(MINOR, local(1, 22), local(2, 1), ALMATY, **kwargs)


def test_naive_datetimes_are_rejected():
    with pytest.raises(ValueError, match="naive"):
        violates_night_restriction(
            MINOR, datetime(2026, 6, 1, 21), datetime(2026, 6, 1, 23), ALMATY
        )


def test_inverted_interval_is_rejected():
    with pytest.raises(ValueError, match="after"):
        violates_night_restriction(MINOR, local(1, 23), local(1, 21), ALMATY)


# --- can_play_at (single instant, for the PC client) ------------------------------------------


@pytest.mark.parametrize(
    ("instant", "allowed"),
    [
        (local(1, 21, 59), True),
        (local(1, 22), False),
        (local(2, 3), False),
        (local(2, 5, 59), False),
        (local(2, 6), True),
    ],
)
def test_can_play_at_for_minor(instant, allowed):
    assert can_play_at(MINOR, instant, ALMATY) is allowed


def test_can_play_at_for_adult():
    assert can_play_at(ADULT, local(2, 3), ALMATY)
    assert can_play_at(BIRTHDAY_BOY, local(15, 0), ALMATY)
    assert not can_play_at(BIRTHDAY_BOY, local(14, 23, 59), ALMATY)
