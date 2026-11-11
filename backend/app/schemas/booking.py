import uuid
from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict

BookingStatusLiteral = Literal[
    "pending_payment", "confirmed", "completed", "cancelled", "expired", "no_show"
]


class BookingCreate(BaseModel):
    pc_id: uuid.UUID
    # Must carry a UTC offset, e.g. 2026-06-01T18:00:00+05:00.
    starts_at: AwareDatetime
    ends_at: AwareDatetime


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    pc_id: uuid.UUID
    club_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    status: BookingStatusLiteral
    hold_expires_at: datetime | None
    price_kzt: int
    created_at: datetime
    cancelled_at: datetime | None


class BookingPage(BaseModel):
    items: list[BookingOut]
    next_cursor: uuid.UUID | None
