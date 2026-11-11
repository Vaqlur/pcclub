"""Clubs, zones and PCs: customer browsing and organization-scoped admin management."""

import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import ColumnElement, and_, exists, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.errors import AppError, not_found
from app.models import Booking, BookingStatus, Club, Pc, PcStatus, StaffUser, Zone
from app.schemas.club import (
    BusyInterval,
    ClubCreate,
    ClubUpdate,
    PcAvailabilityOut,
    PcCreate,
    PcOut,
    PcUpdate,
    ZoneCreate,
    ZoneUpdate,
)


def occupies_slot(now: datetime) -> ColumnElement[bool]:
    """Bookings that currently block their PC: confirmed, or pending with a live hold."""
    return or_(
        Booking.status == BookingStatus.CONFIRMED,
        and_(Booking.status == BookingStatus.PENDING_PAYMENT, Booking.hold_expires_at > now),
    )


# --- customer-facing -------------------------------------------------------------------------


async def list_clubs(session: AsyncSession, city: str | None) -> list[Club]:
    stmt = select(Club).where(Club.is_active).order_by(Club.city, Club.name)
    if city:
        stmt = stmt.where(Club.city.ilike(city))
    return list(await session.scalars(stmt))


async def get_active_club(session: AsyncSession, club_id: uuid.UUID) -> Club:
    club = await session.get(Club, club_id)
    if club is None or not club.is_active:
        raise not_found("Club")
    return club


async def list_zones(session: AsyncSession, club_id: uuid.UUID) -> list[Zone]:
    await get_active_club(session, club_id)
    stmt = select(Zone).where(Zone.club_id == club_id, Zone.is_active).order_by(Zone.name)
    return list(await session.scalars(stmt))


async def list_pcs(
    session: AsyncSession,
    now: datetime,
    club_id: uuid.UUID,
    zone_id: uuid.UUID | None,
    window: tuple[datetime, datetime] | None,
) -> list[PcOut]:
    await get_active_club(session, club_id)
    stmt = (
        select(Pc)
        .join(Pc.zone)
        .options(joinedload(Pc.zone, innerjoin=True))
        .where(Pc.club_id == club_id, Pc.status == PcStatus.ACTIVE, Zone.is_active)
        .order_by(Zone.name, Pc.label)
    )
    if zone_id is not None:
        stmt = stmt.where(Pc.zone_id == zone_id)

    if window is None:
        rows = [(pc, None) for pc in await session.scalars(stmt)]
    else:
        start, end = window
        if end <= start:
            raise AppError("INVALID_SLOT", "`to` must be after `from`", 422)
        busy = exists().where(
            Booking.pc_id == Pc.id,
            Booking.starts_at < end,
            Booking.ends_at > start,
            occupies_slot(now),
        )
        rows = [(pc, not is_busy) for pc, is_busy in await session.execute(stmt.add_columns(busy))]

    return [
        PcOut(
            id=pc.id,
            club_id=pc.club_id,
            zone_id=pc.zone_id,
            zone_name=pc.zone.name,
            label=pc.label,
            specs=pc.specs,
            price_per_hour_kzt=pc.zone.price_per_hour_kzt,
            available=available,
        )
        for pc, available in rows
    ]


async def pc_availability(
    session: AsyncSession, now: datetime, pc_id: uuid.UUID, day: date
) -> PcAvailabilityOut:
    pc = await session.scalar(
        select(Pc).options(joinedload(Pc.club, innerjoin=True)).where(Pc.id == pc_id)
    )
    if pc is None or pc.status == PcStatus.RETIRED or not pc.club.is_active:
        raise not_found("PC")
    tz = pc.club.tz
    day_start = datetime.combine(day, time.min, tzinfo=tz)
    day_end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz)
    bookings = await session.execute(
        select(Booking.starts_at, Booking.ends_at)
        .where(
            Booking.pc_id == pc_id,
            Booking.starts_at < day_end,
            Booking.ends_at > day_start,
            occupies_slot(now),
        )
        .order_by(Booking.starts_at)
    )
    return PcAvailabilityOut(
        pc_id=pc_id,
        date=day.isoformat(),
        timezone=pc.club.timezone,
        busy=[BusyInterval(starts_at=s, ends_at=e) for s, e in bookings],
    )


# --- admin (always scoped to the staff member's organization) ---------------------------------


async def admin_list_clubs(session: AsyncSession, staff: StaffUser) -> list[Club]:
    stmt = select(Club).where(Club.organization_id == staff.organization_id).order_by(Club.name)
    return list(await session.scalars(stmt))


async def admin_get_club(session: AsyncSession, staff: StaffUser, club_id: uuid.UUID) -> Club:
    club = await session.get(Club, club_id)
    # Another organization's club is reported as missing, not as forbidden.
    if club is None or club.organization_id != staff.organization_id:
        raise not_found("Club")
    return club


async def admin_create_club(session: AsyncSession, staff: StaffUser, data: ClubCreate) -> Club:
    club = Club(organization_id=staff.organization_id, **data.model_dump())
    session.add(club)
    await session.commit()
    return club


async def admin_update_club(
    session: AsyncSession, staff: StaffUser, club_id: uuid.UUID, data: ClubUpdate
) -> Club:
    club = await admin_get_club(session, staff, club_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None or field in ("opens_at", "closes_at"):  # only hours are nullable
            setattr(club, field, value)
    if (club.opens_at is None) != (club.closes_at is None):
        raise AppError(
            "VALIDATION_ERROR", "opens_at and closes_at must be set together or both null", 422
        )
    await session.commit()
    return club


async def admin_list_zones(
    session: AsyncSession, staff: StaffUser, club_id: uuid.UUID
) -> list[Zone]:
    await admin_get_club(session, staff, club_id)
    return list(
        await session.scalars(select(Zone).where(Zone.club_id == club_id).order_by(Zone.name))
    )


async def admin_create_zone(
    session: AsyncSession, staff: StaffUser, club_id: uuid.UUID, data: ZoneCreate
) -> Zone:
    await admin_get_club(session, staff, club_id)
    zone = Zone(club_id=club_id, **data.model_dump())
    session.add(zone)
    await _commit_unique(session, "ZONE_NAME_TAKEN", "A zone with this name already exists")
    return zone


async def _admin_get_zone(session: AsyncSession, staff: StaffUser, zone_id: uuid.UUID) -> Zone:
    zone = await session.scalar(
        select(Zone)
        .join(Club, Club.id == Zone.club_id)
        .where(Zone.id == zone_id, Club.organization_id == staff.organization_id)
    )
    if zone is None:
        raise not_found("Zone")
    return zone


async def admin_update_zone(
    session: AsyncSession, staff: StaffUser, zone_id: uuid.UUID, data: ZoneUpdate
) -> Zone:
    zone = await _admin_get_zone(session, staff, zone_id)
    for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(zone, field, value)
    await _commit_unique(session, "ZONE_NAME_TAKEN", "A zone with this name already exists")
    return zone


async def admin_list_pcs(session: AsyncSession, staff: StaffUser, club_id: uuid.UUID) -> list[Pc]:
    await admin_get_club(session, staff, club_id)
    return list(await session.scalars(select(Pc).where(Pc.club_id == club_id).order_by(Pc.label)))


async def admin_create_pc(
    session: AsyncSession, staff: StaffUser, club_id: uuid.UUID, data: PcCreate
) -> Pc:
    await admin_get_club(session, staff, club_id)
    await _require_zone_in_club(session, data.zone_id, club_id)
    pc = Pc(club_id=club_id, **data.model_dump())
    session.add(pc)
    await _commit_unique(session, "PC_LABEL_TAKEN", "A PC with this label already exists")
    return pc


async def admin_update_pc(
    session: AsyncSession, staff: StaffUser, pc_id: uuid.UUID, data: PcUpdate
) -> Pc:
    pc = await session.scalar(
        select(Pc)
        .join(Club, Club.id == Pc.club_id)
        .where(Pc.id == pc_id, Club.organization_id == staff.organization_id)
    )
    if pc is None:
        raise not_found("PC")
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if changes.get("zone_id") is not None:
        await _require_zone_in_club(session, changes["zone_id"], pc.club_id)
    for field, value in changes.items():
        setattr(pc, field, value)
    await _commit_unique(session, "PC_LABEL_TAKEN", "A PC with this label already exists")
    return pc


async def admin_list_bookings(
    session: AsyncSession, staff: StaffUser, club_id: uuid.UUID, day: date
) -> list[Booking]:
    club = await admin_get_club(session, staff, club_id)
    day_start = datetime.combine(day, time.min, tzinfo=club.tz)
    day_end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=club.tz)
    stmt = (
        select(Booking)
        .where(Booking.club_id == club_id, Booking.starts_at < day_end, Booking.ends_at > day_start)
        .order_by(Booking.starts_at, Booking.id)
    )
    return list(await session.scalars(stmt))


async def _require_zone_in_club(
    session: AsyncSession, zone_id: uuid.UUID, club_id: uuid.UUID
) -> None:
    zone = await session.get(Zone, zone_id)
    if zone is None or zone.club_id != club_id:
        raise AppError("ZONE_NOT_IN_CLUB", "Zone does not belong to this club", 422)


async def _commit_unique(session: AsyncSession, code: str, message: str) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(code, message, 409) from exc
