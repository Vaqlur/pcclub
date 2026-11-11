"""Booking price calculation. Money is always whole tenge (int). Pure functions, no I/O."""

from datetime import datetime, timedelta


def booking_price_kzt(price_per_hour_kzt: int, starts_at: datetime, ends_at: datetime) -> int:
    """Hourly rate x duration, rounded half-up to a whole tenge."""
    if price_per_hour_kzt < 0:
        raise ValueError("price must not be negative")
    if ends_at <= starts_at:
        raise ValueError("ends_at must be after starts_at")
    minutes = (ends_at - starts_at) // timedelta(minutes=1)
    return (price_per_hour_kzt * minutes + 30) // 60
