import uuid
from datetime import datetime, time
from typing import Annotated, Any, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

PcStatusLiteral = Literal["active", "maintenance", "retired"]


def _valid_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("unknown IANA timezone") from exc
    return value


Timezone = Annotated[
    str, Field(max_length=64, examples=["Asia/Almaty"]), AfterValidator(_valid_timezone)
]


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- customer-facing -------------------------------------------------------------------------


class ClubOut(_Out):
    id: uuid.UUID
    name: str
    city: str
    address: str
    timezone: str
    opens_at: time | None  # both null = open 24/7
    closes_at: time | None


class ZoneOut(_Out):
    id: uuid.UUID
    club_id: uuid.UUID
    name: str
    price_per_hour_kzt: int


class PcOut(BaseModel):
    id: uuid.UUID
    club_id: uuid.UUID
    zone_id: uuid.UUID
    zone_name: str
    label: str
    specs: dict[str, Any]
    price_per_hour_kzt: int
    # Only present when the request specified a time window.
    available: bool | None = None


class BusyInterval(BaseModel):
    starts_at: datetime
    ends_at: datetime


class PcAvailabilityOut(BaseModel):
    pc_id: uuid.UUID
    date: str
    timezone: str
    busy: list[BusyInterval]


# --- admin -----------------------------------------------------------------------------------


class _OpeningHours(BaseModel):
    opens_at: time | None = None
    closes_at: time | None = None

    @model_validator(mode="after")
    def _both_or_none(self) -> Self:
        if (self.opens_at is None) != (self.closes_at is None):
            raise ValueError("opens_at and closes_at must be set together (or both null for 24/7)")
        return self


class ClubCreate(_OpeningHours):
    name: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=300)
    timezone: Timezone = "Asia/Almaty"


class ClubUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = Field(default=None, min_length=1, max_length=300)
    timezone: Timezone | None = None
    opens_at: time | None = None
    closes_at: time | None = None
    is_active: bool | None = None


class AdminClubOut(ClubOut):
    organization_id: uuid.UUID
    is_active: bool


class ZoneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price_per_hour_kzt: int = Field(ge=0, le=1_000_000)


class ZoneUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    price_per_hour_kzt: int | None = Field(default=None, ge=0, le=1_000_000)
    is_active: bool | None = None


class AdminZoneOut(ZoneOut):
    is_active: bool


class PcCreate(BaseModel):
    zone_id: uuid.UUID
    label: str = Field(min_length=1, max_length=50)
    specs: dict[str, Any] = Field(default_factory=dict)


class PcUpdate(BaseModel):
    zone_id: uuid.UUID | None = None
    label: str | None = Field(default=None, min_length=1, max_length=50)
    specs: dict[str, Any] | None = None
    status: PcStatusLiteral | None = None


class AdminPcOut(_Out):
    id: uuid.UUID
    club_id: uuid.UUID
    zone_id: uuid.UUID
    label: str
    specs: dict[str, Any]
    status: str
