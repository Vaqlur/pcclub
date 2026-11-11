"""Injectable time source. Services never call datetime.now() directly."""

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Current instant as a timezone-aware UTC datetime."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """Controllable clock for tests."""

    def __init__(self, now: datetime) -> None:
        self.set(now)

    def now(self) -> datetime:
        return self._now

    def set(self, now: datetime) -> None:
        if now.tzinfo is None:
            raise ValueError("FixedClock requires an aware datetime")
        self._now = now.astimezone(UTC)

    def advance(self, **delta: float) -> None:
        self._now += timedelta(**delta)


_system_clock = SystemClock()


def get_clock() -> Clock:
    return _system_clock
