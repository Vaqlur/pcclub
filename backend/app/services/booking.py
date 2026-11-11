"""Booking lifecycle: hold -> (payment) -> confirmed, plus expiry and cancellation.

    pending_payment --payment within hold--> confirmed --> completed
          |                                     |
          +--hold runs out--> expired           +--cancel before start--> cancelled (refund)

Double booking is prevented by exclusion constraints in the database (migration 0002); this
module only translates a violation into SLOT_TAKEN. Stale holds are expired lazily here.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.clock import Clock
from app.core.config import Settings
from app.core.errors import AppError, not_found
from app.domain.age_rule import violates_night_restriction
from app.domain.pricing import booking_price_kzt
from app.domain.slots import InvalidSlot, OutsideOpeningHours, SlotRules, validate_slot
from app.integrations.payments.base import PaymentProviderError
from app.integrations.registry import PaymentProviders
from app.models import (
    ACTIVE_BOOKING_STATUSES,
    Booking,
    BookingStatus,
    Payment,
    PaymentStatus,
    Pc,
    PcStatus,
    User,
)
from app.models.booking import PC_OVERLAP_CONSTRAINT, USER_OVERLAP_CONSTRAINT
from app.schemas.booking import BookingCreate


def _violated_constraint(exc: IntegrityError) -> str:
    """Name of the violated constraint (asyncpg exposes it on the underlying error)."""
    cause = getattr(exc.orig, "__cause__", None)
    return getattr(cause, "constraint_name", None) or str(exc.orig)


async def expire_stale_holds(
    session: AsyncSession,
    now: datetime,
    *,
    pc_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> None:
    """Flip unpaid bookings whose hold ran out to `expired` so they stop blocking the slot."""
    scope = []
    if pc_id is not None:
        scope.append(Booking.pc_id == pc_id)
    if user_id is not None:
        scope.append(Booking.user_id == user_id)
    stmt = update(Booking).where(
        Booking.status == BookingStatus.PENDING_PAYMENT, Booking.hold_expires_at <= now
    )
    if scope:
        stmt = stmt.where(or_(*scope))
    await session.execute(
        stmt.values(status=BookingStatus.EXPIRED).execution_options(synchronize_session=False)
    )


async def create_booking(
    session: AsyncSession, settings: Settings, clock: Clock, user: User, data: BookingCreate
) -> Booking:
    now = clock.now()

    # Age is only known for verified users, so nobody books without verification.
    if not user.is_identity_verified:
        raise AppError("IDENTITY_NOT_VERIFIED", "Verify your identity (IIN) before booking", 403)
    assert user.birth_date is not None

    pc = await session.scalar(
        select(Pc)
        .options(joinedload(Pc.zone, innerjoin=True), joinedload(Pc.club, innerjoin=True))
        .where(Pc.id == data.pc_id)
    )
    if pc is None:
        raise not_found("PC")
    if pc.status != PcStatus.ACTIVE or not pc.zone.is_active or not pc.club.is_active:
        raise AppError("PC_UNAVAILABLE", "This PC cannot be booked", 409)

    tz = pc.club.tz
    try:
        validate_slot(
            data.starts_at,
            data.ends_at,
            now=now,
            tz=tz,
            rules=SlotRules(
                slot_minutes=settings.slot_minutes,
                min_minutes=settings.min_booking_minutes,
                max_minutes=settings.max_booking_minutes,
                max_advance_days=settings.max_advance_days,
            ),
            opens_at=pc.club.opens_at,
            closes_at=pc.club.closes_at,
        )
    except InvalidSlot as exc:
        raise AppError("INVALID_SLOT", str(exc), 422) from exc
    except OutsideOpeningHours as exc:
        raise AppError("OUTSIDE_OPENING_HOURS", str(exc), 422) from exc

    if violates_night_restriction(
        user.birth_date,
        data.starts_at,
        data.ends_at,
        tz,
        adult_age=settings.adult_age,
        night_start=settings.night_start,
        night_end=settings.night_end,
    ):
        raise AppError(
            "MINOR_NIGHT_RESTRICTION",
            "Users under 18 cannot book between 22:00 and 06:00",
            403,
            {
                "adult_age": settings.adult_age,
                "night_start": settings.night_start.isoformat(timespec="minutes"),
                "night_end": settings.night_end.isoformat(timespec="minutes"),
                "timezone": pc.club.timezone,
            },
        )

    await expire_stale_holds(session, now, pc_id=pc.id, user_id=user.id)

    booking = Booking(
        user_id=user.id,
        pc_id=pc.id,
        club_id=pc.club_id,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        status=BookingStatus.PENDING_PAYMENT,
        hold_expires_at=now + timedelta(minutes=settings.booking_hold_minutes),
        price_kzt=booking_price_kzt(pc.zone.price_per_hour_kzt, data.starts_at, data.ends_at),
    )
    try:
        async with session.begin_nested():
            session.add(booking)
            await session.flush()
    except IntegrityError as exc:
        constraint = _violated_constraint(exc)
        if PC_OVERLAP_CONSTRAINT in constraint:
            raise AppError("SLOT_TAKEN", "This PC is already booked for that time", 409) from exc
        if USER_OVERLAP_CONSTRAINT in constraint:
            raise AppError(
                "USER_BOOKING_OVERLAP", "You already have a booking at that time", 409
            ) from exc
        raise
    await session.commit()
    return booking


async def list_bookings(
    session: AsyncSession,
    clock: Clock,
    user: User,
    status: str | None,
    cursor: uuid.UUID | None,
    limit: int,
) -> tuple[list[Booking], uuid.UUID | None]:
    """Newest first. Ids are UUIDv7 (time-ordered), so the id is the pagination cursor."""
    await expire_stale_holds(session, clock.now(), user_id=user.id)
    await session.commit()

    stmt = select(Booking).where(Booking.user_id == user.id).order_by(Booking.id.desc())
    if status is not None:
        stmt = stmt.where(Booking.status == status)
    if cursor is not None:
        stmt = stmt.where(Booking.id < cursor)
    rows = list(await session.scalars(stmt.limit(limit + 1)))
    if len(rows) > limit:
        return rows[:limit], rows[limit - 1].id
    return rows, None


async def get_booking(
    session: AsyncSession, clock: Clock, user: User, booking_id: uuid.UUID
) -> Booking:
    await expire_stale_holds(session, clock.now(), user_id=user.id)
    await session.commit()
    booking = await session.scalar(
        select(Booking).where(Booking.id == booking_id, Booking.user_id == user.id)
    )
    if booking is None:
        raise not_found("Booking")
    return booking


async def cancel_booking(
    session: AsyncSession,
    clock: Clock,
    providers: PaymentProviders,
    user: User,
    booking_id: uuid.UUID,
) -> Booking:
    """Cancel before the start time. A paid booking is refunded in full."""
    now = clock.now()
    booking = await session.scalar(
        select(Booking)
        .where(Booking.id == booking_id, Booking.user_id == user.id)
        .with_for_update()
    )
    if booking is None:
        raise not_found("Booking")

    if booking.status == BookingStatus.PENDING_PAYMENT and booking.hold_expires_at <= now:
        booking.status = BookingStatus.EXPIRED
        await session.commit()
    if booking.status not in ACTIVE_BOOKING_STATUSES:
        raise AppError(
            "BOOKING_NOT_CANCELLABLE",
            f"A booking in status '{booking.status}' cannot be cancelled",
            409,
            {"status": booking.status},
        )
    if booking.starts_at <= now:
        raise AppError("BOOKING_ALREADY_STARTED", "The booking has already started", 409)

    paid = await session.scalars(
        select(Payment)
        .where(Payment.booking_id == booking.id, Payment.status == PaymentStatus.SUCCEEDED)
        .with_for_update()
    )
    for payment in paid:
        try:
            await providers.by_name_or_raise(payment.provider).refund(
                provider_payment_id=payment.provider_payment_id or "",
                amount_kzt=payment.amount_kzt,
            )
        except PaymentProviderError as exc:
            # Nothing is committed: the booking stays confirmed and the user can retry.
            raise AppError("PAYMENT_PROVIDER_ERROR", "Refund failed, try again later", 502) from exc
        payment.status = PaymentStatus.REFUNDED
        payment.updated_at = now

    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = now
    await session.commit()
    return booking
