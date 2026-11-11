import uuid

from fastapi import APIRouter, Request

from app.api.deps import ClockDep, CurrentUser, PaymentProvidersDep, SessionDep
from app.core.errors import AppError
from app.integrations.payments.base import ProviderPaymentStatus
from app.integrations.payments.mock import MockPaymentProvider
from app.schemas.payment import PaymentOut
from app.services import payment as payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/{payment_id}")
async def get_payment(payment_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> PaymentOut:
    return PaymentOut.model_validate(await payment_service.get_payment(session, user, payment_id))


@router.post("/webhooks/{provider}")
async def provider_webhook(
    provider: str,
    request: Request,
    session: SessionDep,
    clock: ClockDep,
    providers: PaymentProvidersDep,
) -> dict[str, str]:
    """Called by the payment provider. Authenticated by the provider's signature."""
    await payment_service.handle_webhook(
        session, clock, providers, provider, request.headers, await request.body()
    )
    return {"status": "ok"}


# --- development helpers: only mounted while a mock payment provider is configured ------------

mock_router = APIRouter(prefix="/payments/mock", tags=["payments (mock)"])


async def _simulate(
    payment_id: uuid.UUID,
    outcome: ProviderPaymentStatus,
    user: CurrentUser,
    session: SessionDep,
    clock: ClockDep,
    providers: PaymentProvidersDep,
) -> PaymentOut:
    payment = await payment_service.get_payment(session, user, payment_id)
    provider = providers.by_name(payment.provider)
    if not isinstance(provider, MockPaymentProvider) or payment.provider_payment_id is None:
        raise AppError(
            "NOT_A_MOCK_PAYMENT", "This payment is not handled by the mock provider", 409
        )
    headers, body = provider.build_webhook(
        provider_payment_id=payment.provider_payment_id, status=outcome
    )
    # Goes through the same signed-webhook path as a real provider callback.
    payment = await payment_service.handle_webhook(
        session, clock, providers, provider.name, headers, body
    )
    return PaymentOut.model_validate(payment)


@mock_router.post("/{payment_id}/complete")
async def mock_complete(
    payment_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    clock: ClockDep,
    providers: PaymentProvidersDep,
) -> PaymentOut:
    """Simulate the provider reporting a successful payment."""
    return await _simulate(
        payment_id, ProviderPaymentStatus.SUCCEEDED, user, session, clock, providers
    )


@mock_router.post("/{payment_id}/fail")
async def mock_fail(
    payment_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    clock: ClockDep,
    providers: PaymentProvidersDep,
) -> PaymentOut:
    """Simulate the provider reporting a failed payment."""
    return await _simulate(
        payment_id, ProviderPaymentStatus.FAILED, user, session, clock, providers
    )
