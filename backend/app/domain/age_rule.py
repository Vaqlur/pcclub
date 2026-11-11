"""Night restriction for minors. Pure functions, no I/O.

Rule: a user under `adult_age` (18) may not book or play during the night window
[night_start, night_end) = [22:00, 06:00) in the club's local time.

Boundary semantics (all club-local):
  * the window is half-open: ending exactly at 22:00 is allowed, starting exactly at 06:00
    is allowed, 21:00-23:00 and 05:00-07:00 are not;
  * a user becomes an adult at 00:00 on their 18th birthday (29 Feb -> 1 Mar in non-leap
    years). `adult_from` is the single place that encodes this legal interpretation;
  * a booking is rejected if ANY instant of it is both before adulthood and inside a night
    window, so a booking that runs into the 18th birthday is judged only on the part before it.
"""

from datetime import UTC, date, datetime, time, timedelta, tzinfo

DEFAULT_ADULT_AGE = 18
DEFAULT_NIGHT_START = time(22, 0)
DEFAULT_NIGHT_END = time(6, 0)


def adult_from(birth_date: date, adult_age: int = DEFAULT_ADULT_AGE) -> date:
    """First calendar day on which the person counts as an adult."""
    try:
        return birth_date.replace(year=birth_date.year + adult_age)
    except ValueError:  # 29 February in a non-leap target year
        return date(birth_date.year + adult_age, 3, 1)


def _require_aware(*values: datetime) -> None:
    for value in values:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("naive datetimes are not allowed; pass timezone-aware values")


def _local(day: date, at: time, tz: tzinfo) -> datetime:
    """Club-local wall time as a UTC instant."""
    return datetime.combine(day, at, tzinfo=tz).astimezone(UTC)


def is_minor_at(
    birth_date: date, instant: datetime, tz: tzinfo, *, adult_age: int = DEFAULT_ADULT_AGE
) -> bool:
    _require_aware(instant)
    return instant.astimezone(tz).date() < adult_from(birth_date, adult_age)


def violates_night_restriction(
    birth_date: date,
    starts_at: datetime,
    ends_at: datetime,
    tz: tzinfo,
    *,
    adult_age: int = DEFAULT_ADULT_AGE,
    night_start: time = DEFAULT_NIGHT_START,
    night_end: time = DEFAULT_NIGHT_END,
) -> bool:
    """True if the interval [starts_at, ends_at) breaks the night rule for this person."""
    _require_aware(starts_at, ends_at)
    if ends_at <= starts_at:
        raise ValueError("ends_at must be after starts_at")

    start = starts_at.astimezone(UTC)
    # Only the part of the interval before adulthood can violate the rule.
    end = min(ends_at.astimezone(UTC), _local(adult_from(birth_date, adult_age), time.min, tz))
    if end <= start:
        return False

    crosses_midnight = night_end <= night_start
    day = start.astimezone(tz).date() - timedelta(days=1)
    last_day = end.astimezone(tz).date()
    while day <= last_day:
        window_start = _local(day, night_start, tz)
        window_end = _local(day + timedelta(days=1) if crosses_midnight else day, night_end, tz)
        if start < window_end and window_start < end:
            return True
        day += timedelta(days=1)
    return False


def can_play_at(
    birth_date: date,
    instant: datetime,
    tz: tzinfo,
    *,
    adult_age: int = DEFAULT_ADULT_AGE,
    night_start: time = DEFAULT_NIGHT_START,
    night_end: time = DEFAULT_NIGHT_END,
) -> bool:
    """Whether this person may be in a session at this instant (used by the PC client later)."""
    return not violates_night_restriction(
        birth_date,
        instant,
        instant + timedelta(microseconds=1),
        tz,
        adult_age=adult_age,
        night_start=night_start,
        night_end=night_end,
    )
