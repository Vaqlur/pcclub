import json
import uuid

import pytest
from sqlalchemy import func, select

from app.integrations.payments.base import ProviderPaymentStatus
from app.main import create_app
from app.models import Payment
from tests.integration.helpers import at, book, book_and_pay, code, pay, register

PHONE = "+77010000001"


@pytest.fixture
async def headers(client):
    return await register(client, PHONE)


@pytest.fixture
async def booking(client, world, headers):
    response = await book(client, headers, world.pc_ids[0], at(1, 18))
    assert response.status_code == 201
    return response.json()


async def _booking_status(client, headers, booking_id):
    return (await client.get(f"/v1/bookings/{booking_id}", headers=headers)).json()["status"]


async def _webhook(client, mock_provider, payment, status):
    """Deliver a signed provider callback to the public webhook endpoint."""
    provider_payment_id = f"mock_{uuid.UUID(payment['id']).hex}"
    webhook_headers, body = mock_provider.build_webhook(
        provider_payment_id=provider_payment_id, status=status
    )
    return await client.post("/v1/payments/webhooks/mock", headers=webhook_headers, content=body)


@pytest.mark.parametrize("method", ["card", "kaspi"])
async def test_successful_payment_confirms_the_booking(client, headers, booking, method):
    response = await pay(client, headers, booking["id"], method)
    assert response.status_code == 201
    payment = response.json()
    assert payment["status"] == "pending"
    assert payment["method"] == method
    assert payment["amount_kzt"] == booking["price_kzt"] == 2000
    assert payment["redirect_url"].startswith("https://pay.mock.invalid/checkout/")
    # Creating the payment does not confirm anything yet.
    assert await _booking_status(client, headers, booking["id"]) == "pending_payment"

    response = await client.post(f"/v1/payments/mock/{payment['id']}/complete", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert await _booking_status(client, headers, booking["id"]) == "confirmed"
    current = await client.get(f"/v1/payments/{payment['id']}", headers=headers)
    assert current.json()["status"] == "succeeded"


async def test_signed_webhook_confirms_the_booking(client, headers, booking, mock_provider):
    payment = (await pay(client, headers, booking["id"])).json()

    response = await _webhook(client, mock_provider, payment, ProviderPaymentStatus.SUCCEEDED)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert await _booking_status(client, headers, booking["id"]) == "confirmed"


async def test_webhook_with_bad_signature_is_ignored(client, headers, booking, mock_provider):
    payment = (await pay(client, headers, booking["id"])).json()
    _, body = mock_provider.build_webhook(
        provider_payment_id=f"mock_{uuid.UUID(payment['id']).hex}",
        status=ProviderPaymentStatus.SUCCEEDED,
    )

    for bad_headers in ({}, {"x-mock-signature": "0" * 64}):
        response = await client.post(
            "/v1/payments/webhooks/mock", headers=bad_headers, content=body
        )
        assert response.status_code == 401
        assert code(response) == "INVALID_WEBHOOK"
    assert await _booking_status(client, headers, booking["id"]) == "pending_payment"


async def test_tampered_webhook_body_is_rejected(client, headers, booking, mock_provider):
    payment = (await pay(client, headers, booking["id"])).json()
    webhook_headers, body = mock_provider.build_webhook(
        provider_payment_id=f"mock_{uuid.UUID(payment['id']).hex}",
        status=ProviderPaymentStatus.FAILED,
    )
    tampered = json.dumps({**json.loads(body), "status": "succeeded"}).encode()

    response = await client.post(
        "/v1/payments/webhooks/mock", headers=webhook_headers, content=tampered
    )
    assert response.status_code == 401
    assert await _booking_status(client, headers, booking["id"]) == "pending_payment"


async def test_webhook_for_unknown_provider_or_payment(client, mock_provider):
    webhook_headers, body = mock_provider.build_webhook(
        provider_payment_id="mock_does_not_exist", status=ProviderPaymentStatus.SUCCEEDED
    )
    response = await client.post(
        "/v1/payments/webhooks/mock", headers=webhook_headers, content=body
    )
    assert response.status_code == 404
    response = await client.post(
        "/v1/payments/webhooks/nope", headers=webhook_headers, content=body
    )
    assert response.status_code == 404


async def test_duplicate_webhook_is_idempotent(client, headers, booking, mock_provider):
    payment = (await pay(client, headers, booking["id"])).json()
    for _ in range(3):
        response = await _webhook(client, mock_provider, payment, ProviderPaymentStatus.SUCCEEDED)
        assert response.status_code == 200
    assert await _booking_status(client, headers, booking["id"]) == "confirmed"
    assert mock_provider.refunds == []
    # A late "failed" for an already succeeded payment changes nothing either.
    await _webhook(client, mock_provider, payment, ProviderPaymentStatus.FAILED)
    current = await client.get(f"/v1/payments/{payment['id']}", headers=headers)
    assert current.json()["status"] == "succeeded"
    assert await _booking_status(client, headers, booking["id"]) == "confirmed"


async def test_failed_payment_can_be_retried(client, headers, booking):
    first = (await pay(client, headers, booking["id"], "card")).json()
    response = await client.post(f"/v1/payments/mock/{first['id']}/fail", headers=headers)
    assert response.json()["status"] == "failed"
    assert await _booking_status(client, headers, booking["id"]) == "pending_payment"

    second = (await pay(client, headers, booking["id"], "kaspi")).json()
    assert second["id"] != first["id"]
    await client.post(f"/v1/payments/mock/{second['id']}/complete", headers=headers)
    assert await _booking_status(client, headers, booking["id"]) == "confirmed"


async def test_idempotency_key_replay_returns_the_same_payment(client, headers, booking, db):
    key = "order-0001-attempt-1"
    first = await pay(client, headers, booking["id"], "card", key)
    second = await pay(client, headers, booking["id"], "card", key)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert await db.scalar(select(func.count()).select_from(Payment)) == 1

    # Replaying after the payment completed still returns it instead of failing.
    await client.post(f"/v1/payments/mock/{first.json()['id']}/complete", headers=headers)
    third = await pay(client, headers, booking["id"], "card", key)
    assert third.status_code == 201
    assert third.json()["id"] == first.json()["id"]
    assert third.json()["status"] == "succeeded"

    conflict = await pay(client, headers, booking["id"], "kaspi", key)
    assert conflict.status_code == 409
    assert code(conflict) == "IDEMPOTENCY_KEY_REUSED"


async def test_idempotency_key_is_required(client, headers, booking):
    response = await client.post(
        f"/v1/bookings/{booking['id']}/payments", headers=headers, json={"method": "card"}
    )
    assert response.status_code == 422
    assert code(response) == "VALIDATION_ERROR"


async def test_unknown_payment_method(client, headers, booking):
    response = await pay(client, headers, booking["id"], "bitcoin")
    assert response.status_code == 422


async def test_cannot_pay_after_the_hold_expired(client, headers, booking, clock):
    clock.advance(minutes=10)
    response = await pay(client, headers, booking["id"])
    assert response.status_code == 409
    assert code(response) == "HOLD_EXPIRED"
    assert await _booking_status(client, headers, booking["id"]) == "expired"


async def test_payment_arriving_after_the_hold_is_refunded(
    client, headers, booking, clock, mock_provider
):
    payment = (await pay(client, headers, booking["id"])).json()
    clock.advance(minutes=10)  # the customer paid, but too late

    response = await _webhook(client, mock_provider, payment, ProviderPaymentStatus.SUCCEEDED)
    assert response.status_code == 200
    assert await _booking_status(client, headers, booking["id"]) == "expired"
    current = await client.get(f"/v1/payments/{payment['id']}", headers=headers)
    assert current.json()["status"] == "refunded"
    assert [amount for _, amount in mock_provider.refunds] == [2000]


async def test_late_payment_with_failing_refund_is_flagged(
    client, headers, booking, clock, mock_provider, db
):
    payment = (await pay(client, headers, booking["id"])).json()
    clock.advance(minutes=10)
    mock_provider.fail_next_refund = True

    response = await _webhook(client, mock_provider, payment, ProviderPaymentStatus.SUCCEEDED)
    assert response.status_code == 200  # the provider must not retry forever
    row = (await db.scalars(select(Payment).where(Payment.id == uuid.UUID(payment["id"])))).one()
    assert row.status == "succeeded"
    assert row.raw["refund_required"] is True
    assert await _booking_status(client, headers, booking["id"]) == "expired"


async def test_second_successful_payment_is_refunded(client, headers, booking, mock_provider):
    first = (await pay(client, headers, booking["id"], "card")).json()
    second = (await pay(client, headers, booking["id"], "kaspi")).json()

    await _webhook(client, mock_provider, first, ProviderPaymentStatus.SUCCEEDED)
    await _webhook(client, mock_provider, second, ProviderPaymentStatus.SUCCEEDED)

    assert await _booking_status(client, headers, booking["id"]) == "confirmed"
    statuses = {
        p["id"]: (await client.get(f"/v1/payments/{p['id']}", headers=headers)).json()["status"]
        for p in (first, second)
    }
    assert statuses == {first["id"]: "succeeded", second["id"]: "refunded"}
    assert len(mock_provider.refunds) == 1


async def test_payment_for_a_cancelled_booking_is_refunded(client, headers, booking, mock_provider):
    payment = (await pay(client, headers, booking["id"])).json()
    await client.post(f"/v1/bookings/{booking['id']}/cancel", headers=headers)

    await _webhook(client, mock_provider, payment, ProviderPaymentStatus.SUCCEEDED)
    assert await _booking_status(client, headers, booking["id"]) == "cancelled"
    current = await client.get(f"/v1/payments/{payment['id']}", headers=headers)
    assert current.json()["status"] == "refunded"


async def test_cannot_pay_a_confirmed_or_cancelled_booking(client, world, headers):
    confirmed = await book_and_pay(client, headers, world.pc_ids[0], at(1, 18))
    response = await pay(client, headers, confirmed["id"])
    assert response.status_code == 409
    assert code(response) == "BOOKING_NOT_PAYABLE"
    assert response.json()["error"]["details"] == {"status": "confirmed"}

    cancelled = (await book(client, headers, world.pc_ids[1], at(2, 18))).json()
    await client.post(f"/v1/bookings/{cancelled['id']}/cancel", headers=headers)
    assert code(await pay(client, headers, cancelled["id"])) == "BOOKING_NOT_PAYABLE"


async def test_provider_error_creates_no_payment(client, headers, booking, mock_provider, db):
    mock_provider.fail_next_create = True
    response = await pay(client, headers, booking["id"])
    assert response.status_code == 502
    assert code(response) == "PAYMENT_PROVIDER_ERROR"
    assert await db.scalar(select(func.count()).select_from(Payment)) == 0
    # The hold is untouched, so the customer can simply try again.
    assert (await pay(client, headers, booking["id"])).status_code == 201


async def test_payments_are_private(client, headers, booking):
    payment = (await pay(client, headers, booking["id"])).json()
    stranger = await register(client, "+77010000002", serial=2)

    assert (await client.get(f"/v1/payments/{payment['id']}", headers=stranger)).status_code == 404
    response = await client.post(f"/v1/payments/mock/{payment['id']}/complete", headers=stranger)
    assert response.status_code == 404
    assert (await client.get(f"/v1/payments/{payment['id']}")).status_code == 401
    assert await _booking_status(client, headers, booking["id"]) == "pending_payment"


async def test_mock_endpoints_are_absent_without_a_mock_provider(settings):
    def paths(app):
        return set(app.openapi()["paths"])

    assert "/v1/payments/mock/{payment_id}/complete" in paths(create_app(settings))
    real = settings.model_copy(
        update={"payment_provider_card": "acquirer", "payment_provider_kaspi": "kaspi"}
    )
    assert "/v1/payments/mock/{payment_id}/complete" not in paths(create_app(real))
    assert "/v1/payments/webhooks/{provider}" in paths(create_app(real))
