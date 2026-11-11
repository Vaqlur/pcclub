"""Booking slot validation. Pure functions, no I/O."""

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta, tzinfo


class InvalidSlot(ValueError):
    """The requested interval is not a bookable slot (misaligned, too short, in the past...)."""


class OutsideOpeningHours(ValueError):
    """The requested interval is not fully inside one opening period of the club."""


@dataclass(frozen=True)
class SlotRules:
    slot_minutes: int = 30
    min_minutes: int = 60
    max_minutes: int = 12 * 60
    max_advance_days: int = 14


def _is_aligned(local: datetime, slot_minutes: int) -> bool:
    minutes_of_day = local.hour * 60 + local.minute
    return local.second == 0 and local.microsecond == 0 and minutes_of_day % slot_minutes == 0


def within_opening_hours(
    starts_at: datetime,
    ends_at: datetime,
    tz: tzinfo,
    opens_at: time | None,
    closes_at: time | None,
) -> bool:
    """True if [starts_at, ends_at] fits in one opening period. None/None means 24/7.

    closes_at <= opens_at means the club closes after midnight (e.g. 12:00-04:00).
    """
    if opens_at is None or closes_at is None:
        return True
    start, end = starts_at.astimezone(UTC), ends_at.astimezone(UTC)
    overnight = closes_at <= opens_at
    local_day = starts_at.astimezone(tz).date()
    # The slot may belong to the period that opened today or (for overnight clubs) yesterday.
    for day in (local_day - timedelta(days=1), local_day):
        period_start = datetime.combine(day, opens_at, tzinfo=tz).astimezone(UTC)
        close_day = day + timedelta(days=1) if overnight else day
        period_end = datetime.combine(close_day, closes_at, tzinfo=tz).astimezone(UTC)
        if period_start <= start and end <= period_end:
            return True
    return False


def validate_slot(
    starts_at: datetime,
    ends_at: datetime,
    *,
    now: datetime,
    tz: tzinfo,
    rules: SlotRules,
    opens_at: time | None = None,
    closes_at: time | None = None,
) -> None:
    """Raise InvalidSlot / OutsideOpeningHours if the interval cannot be booked."""
    for value in (starts_at, ends_at, now):
        if value.tzinfo is None:
            raise ValueError("naive datetimes are not allowed")

    if ends_at <= starts_at:
        raise InvalidSlot("end must be after start")
    if starts_at <= now:
        raise InvalidSlot("slot must start in the future")
    if starts_at > now + timedelta(days=rules.max_advance_days):
        raise InvalidSlot(f"slot may start at most {rules.max_advance_days} days ahead")

    local_start, local_end = starts_at.astimezone(tz), ends_at.astimezone(tz)
    if not (
        _is_aligned(local_start, rules.slot_minutes) and _is_aligned(local_end, rules.slot_minutes)
    ):
        raise InvalidSlot(f"start and end must be aligned to {rules.slot_minutes} minutes")

    minutes = (ends_at - starts_at) / timedelta(minutes=1)
    if minutes < rules.min_minutes:
        raise InvalidSlot(f"minimum booking is {rules.min_minutes} minutes")
    if minutes > rules.max_minutes:
        raise InvalidSlot(f"maximum booking is {rules.max_minutes} minutes")

    if not within_opening_hours(starts_at, ends_at, tz, opens_at, closes_at):
        raise OutsideOpeningHours("slot is outside the club's opening hours")
