"""Payments: start a payment for a held booking and apply provider webhooks.

A booking is confirmed ONLY by a verified webhook event, never by the client. Row locks are
always taken booking first, then payment, to keep webhook / cancel / pay deadlock-free.
"""

import logging
import uuid
from collections.abc import Mapping
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import AppError, not_found
from app.integrations.payments.base import (
    InvalidWebhook,
    PaymentMethod,
    PaymentProvider,
    PaymentProviderError,
    ProviderPaymentStatus,
    WebhookEvent,
)
from app.integrations.registry import PaymentProviders
from app.models import Booking, BookingStatus, Payment, PaymentStatus, User

logger = logging.getLogger("pcclub.payments")


async def create_payment(
    session: AsyncSession,
    clock: Clock,
    providers: PaymentProviders,
    user: User,
    booking_id: uuid.UUID,
    method: PaymentMethod,
    idempotency_key: str,
) -> Payment:
    now = clock.now()
    booking = await session.scalar(
        select(Booking)
        .where(Booking.id == booking_id, Booking.user_id == user.id)
        .with_for_update()
    )
    if booking is None:
        raise not_found("Booking")

    # A retried request (same key) returns the original payment, whatever happened since.
    existing = await session.scalar(
        select(Payment).where(
            Payment.booking_id == booking.id, Payment.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        if existing.method != method:
            raise AppError(
                "IDEMPOTENCY_KEY_REUSED", "This Idempotency-Key was used with other data", 409
            )
        return existing

    if booking.status == BookingStatus.PENDING_PAYMENT and booking.hold_expires_at <= now:
        booking.status = BookingStatus.EXPIRED
        await session.commit()
        raise AppError("HOLD_EXPIRED", "The booking hold has expired, book again", 409)
    if booking.status != BookingStatus.PENDING_PAYMENT:
        raise AppError(
            "BOOKING_NOT_PAYABLE",
            f"A booking in status '{booking.status}' cannot be paid",
            409,
            {"status": booking.status},
        )

    provider = providers.for_method(method)
    payment = Payment(
        id=uuid.uuid7(),
        booking_id=booking.id,
        method=method,
        provider=provider.name,
        amount_kzt=booking.price_kzt,
        status=PaymentStatus.PENDING,
        idempotency_key=idempotency_key,
    )
    try:
        created = await provider.create_payment(
            payment_id=payment.id,
            amount_kzt=payment.amount_kzt,
            description=f"PC booking {booking.id}",
        )
    except PaymentProviderError as exc:
        raise AppError("PAYMENT_PROVIDER_ERROR", "Payment provider is unavailable", 502) from exc

    payment.provider_payment_id = created.provider_payment_id
    payment.redirect_url = created.redirect_url
    payment.raw = {"create": created.raw}
    session.add(payment)
    await session.commit()
    return payment


async def get_payment(session: AsyncSession, user: User, payment_id: uuid.UUID) -> Payment:
    payment = await session.scalar(
        select(Payment)
        .join(Booking, Booking.id == Payment.booking_id)
        .where(Payment.id == payment_id, Booking.user_id == user.id)
    )
    if payment is None:
        raise not_found("Payment")
    return payment


async def handle_webhook(
    session: AsyncSession,
    clock: Clock,
    providers: PaymentProviders,
    provider_name: str,
    headers: Mapping[str, str],
    body: bytes,
) -> Payment:
    provider = providers.by_name(provider_name)
    if provider is None:
        raise not_found("Payment provider")
    try:
        event = provider.parse_webhook(headers=headers, body=body)
    except InvalidWebhook as exc:
        raise AppError("INVALID_WEBHOOK", "Webhook could not be verified", 401) from exc
    return await apply_event(session, clock.now(), provider, event)


async def apply_event(
    session: AsyncSession, now: datetime, provider: PaymentProvider, event: WebhookEvent
) -> Payment:
    """Apply a verified provider event. Idempotent: only a pending payment changes state."""
    booking_id = await session.scalar(
        select(Payment.booking_id).where(
            Payment.provider == provider.name,
            Payment.provider_payment_id == event.provider_payment_id,
        )
    )
    if booking_id is None:
        raise not_found("Payment")

    # Lock order: booking, then payment.
    booking = (
        await session.scalars(select(Booking).where(Booking.id == booking_id).with_for_update())
    ).one()
    payment = (
        await session.scalars(
            select(Payment)
            .where(
                Payment.provider == provider.name,
                Payment.provider_payment_id == event.provider_payment_id,
            )
            .with_for_update()
        )
    ).one()

    if event.status == ProviderPaymentStatus.PENDING or payment.status != PaymentStatus.PENDING:
        return payment  # nothing to do / duplicate delivery

    payment.updated_at = now
    payment.raw = {**payment.raw, "webhook": event.raw}

    if event.status == ProviderPaymentStatus.FAILED:
        payment.status = PaymentStatus.FAILED
        await session.commit()
        return payment

    payment.status = PaymentStatus.SUCCEEDED
    hold_is_live = booking.status == BookingStatus.PENDING_PAYMENT and booking.hold_expires_at > now
    if hold_is_live:
        booking.status = BookingStatus.CONFIRMED
    else:
        # Paid too late, or the booking was already paid/cancelled: give the money back.
        if booking.status == BookingStatus.PENDING_PAYMENT:
            booking.status = BookingStatus.EXPIRED
        try:
            await provider.refund(
                provider_payment_id=event.provider_payment_id, amount_kzt=payment.amount_kzt
            )
            payment.status = PaymentStatus.REFUNDED
        except PaymentProviderError:
            # Keep `succeeded` and flag it; a worker / operator must retry the refund.
            payment.raw = {**payment.raw, "refund_required": True}
            logger.error("refund failed for payment %s (booking %s)", payment.id, booking.id)
    await session.commit()
    return payment
