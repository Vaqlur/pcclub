from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.domain.pricing import booking_price_kzt
from app.domain.slots import (
    InvalidSlot,
    OutsideOpeningHours,
    SlotRules,
    validate_slot,
    within_opening_hours,
)

ALMATY = ZoneInfo("Asia/Almaty")
NOW = datetime(2026, 6, 1, 12, 0, tzinfo=ALMATY)
RULES = SlotRules()


def at(day: int, hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2026, 6, day, hour, minute, second, tzinfo=ALMATY)


def check(start: datetime, end: datetime, **kwargs) -> None:
    validate_slot(start, end, now=NOW, tz=ALMATY, rules=RULES, **kwargs)


# --- slots -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (at(1, 13), at(1, 14)),  # minimum length
        (at(1, 12, 30), at(1, 14)),  # half-hour alignment
        (at(1, 13), at(2, 1)),  # maximum length (12h)
        (at(15, 12), at(15, 14)),  # exactly 14 days ahead
    ],
)
def test_valid_slots(start, end):
    check(start, end)


@pytest.mark.parametrize(
    ("start", "end", "reason"),
    [
        (at(1, 14), at(1, 13), "after start"),
        (at(1, 14), at(1, 14), "after start"),
        (at(1, 12), at(1, 14), "future"),  # starts exactly now
        (at(1, 10), at(1, 13), "future"),
        (at(15, 12, 30), at(15, 14), "days ahead"),
        (at(1, 13, 15), at(1, 14, 15), "aligned"),
        (at(1, 13), at(1, 14, 10), "aligned"),
        (at(1, 13, 0, 5), at(1, 14), "aligned"),
        (at(1, 13), at(1, 13, 30), "minimum"),
        (at(1, 13), at(2, 1, 30), "maximum"),
    ],
)
def test_invalid_slots(start, end, reason):
    with pytest.raises(InvalidSlot, match=reason):
        check(start, end)


def test_naive_datetimes_are_rejected():
    with pytest.raises(ValueError, match="naive"):
        validate_slot(
            datetime(2026, 6, 1, 13), datetime(2026, 6, 1, 14), now=NOW, tz=ALMATY, rules=RULES
        )


def test_alignment_is_checked_in_club_local_time():
    # Kathmandu is UTC+5:45: a slot on the local hour is :15 past the hour in UTC.
    tz = ZoneInfo("Asia/Kathmandu")
    start = datetime(2026, 6, 2, 13, 0, tzinfo=tz)
    validate_slot(start, start + timedelta(hours=1), now=NOW, tz=tz, rules=RULES)
    with pytest.raises(InvalidSlot, match="aligned"):
        validate_slot(start, start + timedelta(hours=1), now=NOW, tz=ALMATY, rules=RULES)


# --- opening hours ---------------------------------------------------------------------------


def test_24_7_club_accepts_any_time():
    assert within_opening_hours(at(2, 3), at(2, 5), ALMATY, None, None)


@pytest.mark.parametrize(
    ("start", "end", "ok"),
    [
        (at(2, 10), at(2, 12), True),  # from opening
        (at(2, 21), at(2, 23), True),  # until closing
        (at(2, 9, 30), at(2, 11), False),  # before opening
        (at(2, 22), at(3, 0), False),  # past closing
        (at(2, 23), at(3, 11), False),  # spans the closed night
    ],
)
def test_daytime_club(start, end, ok):
    assert within_opening_hours(start, end, ALMATY, time(10), time(23)) is ok


@pytest.mark.parametrize(
    ("start", "end", "ok"),
    [
        (at(2, 12), at(2, 14), True),
        (at(2, 23), at(3, 2), True),  # across midnight inside one period
        (at(3, 2), at(3, 4), True),  # belongs to the period that opened yesterday
        (at(3, 3), at(3, 5), False),  # past closing at 04:00
        (at(3, 4), at(3, 6), False),  # club is closed 04:00-12:00
        (at(3, 3), at(3, 13), False),  # spans the closed morning
    ],
)
def test_overnight_club(start, end, ok):
    assert within_opening_hours(start, end, ALMATY, time(12), time(4)) is ok


def test_validate_slot_raises_outside_opening_hours():
    with pytest.raises(OutsideOpeningHours):
        check(at(2, 8), at(2, 10), opens_at=time(10), closes_at=time(23))
    check(at(2, 10), at(2, 12), opens_at=time(10), closes_at=time(23))


# --- pricing ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rate", "minutes", "expected"),
    [
        (1000, 60, 1000),
        (1000, 90, 1500),
        (1500, 120, 3000),
        (999, 30, 500),  # 499.5 rounds half-up
        (1001, 30, 501),  # 500.5 rounds half-up
        (0, 120, 0),
        (800, 720, 9600),
    ],
)
def test_price(rate, minutes, expected):
    start = at(1, 13)
    price = booking_price_kzt(rate, start, start + timedelta(minutes=minutes))
    assert price == expected
    assert isinstance(price, int)


def test_price_rejects_bad_input():
    with pytest.raises(ValueError):
        booking_price_kzt(-1, at(1, 13), at(1, 14))
    with pytest.raises(ValueError):
        booking_price_kzt(1000, at(1, 14), at(1, 13))
