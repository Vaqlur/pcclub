import uuid
from typing import Annotated

from fastapi import APIRouter, Header, Query, status

from app.api.deps import ClockDep, CurrentUser, PaymentProvidersDep, SessionDep, SettingsDep
from app.schemas.booking import BookingCreate, BookingOut, BookingPage, BookingStatusLiteral
from app.schemas.payment import PaymentCreate, PaymentOut
from app.services import booking as booking_service
from app.services import payment as payment_service

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_booking(
    data: BookingCreate,
    user: CurrentUser,
    session: SessionDep,
    settings: SettingsDep,
    clock: ClockDep,
) -> BookingOut:
    """Hold a PC for a time slot. The hold must be paid before `hold_expires_at`."""
    booking = await booking_service.create_booking(session, settings, clock, user, data)
    return BookingOut.model_validate(booking)


@router.get("")
async def list_bookings(
    user: CurrentUser,
    session: SessionDep,
    clock: ClockDep,
    status_: Annotated[BookingStatusLiteral | None, Query(alias="status")] = None,
    cursor: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> BookingPage:
    """Booking history, newest first."""
    items, next_cursor = await booking_service.list_bookings(
        session, clock, user, status_, cursor, limit
    )
    return BookingPage(items=[BookingOut.model_validate(b) for b in items], next_cursor=next_cursor)


@router.get("/{booking_id}")
async def get_booking(
    booking_id: uuid.UUID, user: CurrentUser, session: SessionDep, clock: ClockDep
) -> BookingOut:
    return BookingOut.model_validate(
        await booking_service.get_booking(session, clock, user, booking_id)
    )


@router.post("/{booking_id}/cancel")
async def cancel_booking(
    booking_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    clock: ClockDep,
    providers: PaymentProvidersDep,
) -> BookingOut:
    """Cancel before the start time; a paid booking is refunded."""
    booking = await booking_service.cancel_booking(session, clock, providers, user, booking_id)
    return BookingOut.model_validate(booking)


@router.post("/{booking_id}/payments", status_code=status.HTTP_201_CREATED)
async def create_payment(
    booking_id: uuid.UUID,
    data: PaymentCreate,
    user: CurrentUser,
    session: SessionDep,
    clock: ClockDep,
    providers: PaymentProvidersDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=100)],
) -> PaymentOut:
    """Start a card or Kaspi payment. Send the customer to `redirect_url`."""
    payment = await payment_service.create_payment(
        session, clock, providers, user, booking_id, data.method, idempotency_key
    )
    return PaymentOut.model_validate(payment)
