"""Mock payment provider for development and tests.

Behaves like a real redirect + webhook provider: create_payment() returns a fake redirect
URL, and the outcome arrives through a signed webhook. build_webhook() produces such a
callback (used by the /payments/mock/... endpoints and by tests).
"""

import hashlib
import hmac
import json
import uuid
from collections.abc import Mapping

from app.integrations.payments.base import (
    CreatedPayment,
    InvalidWebhook,
    PaymentProviderError,
    ProviderPaymentStatus,
    WebhookEvent,
)

SIGNATURE_HEADER = "x-mock-signature"


class MockPaymentProvider:
    name = "mock"

    def __init__(self, webhook_secret: str) -> None:
        self._secret = webhook_secret.encode()
        self.refunds: list[tuple[str, int]] = []
        self.fail_next_create = False
        self.fail_next_refund = False

    async def create_payment(
        self, *, payment_id: uuid.UUID, amount_kzt: int, description: str
    ) -> CreatedPayment:
        if self.fail_next_create:
            self.fail_next_create = False
            raise PaymentProviderError("mock provider declined the request")
        provider_payment_id = f"mock_{payment_id.hex}"
        return CreatedPayment(
            provider_payment_id=provider_payment_id,
            redirect_url=f"https://pay.mock.invalid/checkout/{provider_payment_id}",
            raw={"amount_kzt": amount_kzt, "description": description},
        )

    async def refund(self, *, provider_payment_id: str, amount_kzt: int) -> None:
        if self.fail_next_refund:
            self.fail_next_refund = False
            raise PaymentProviderError("mock provider could not refund")
        self.refunds.append((provider_payment_id, amount_kzt))
        del self.refunds[:-100]

    def _sign(self, body: bytes) -> str:
        return hmac.new(self._secret, body, hashlib.sha256).hexdigest()

    def build_webhook(
        self, *, provider_payment_id: str, status: ProviderPaymentStatus
    ) -> tuple[dict[str, str], bytes]:
        body = json.dumps({"payment_id": provider_payment_id, "status": status.value}).encode()
        return {SIGNATURE_HEADER: self._sign(body)}, body

    def parse_webhook(self, *, headers: Mapping[str, str], body: bytes) -> WebhookEvent:
        signature = {k.lower(): v for k, v in headers.items()}.get(SIGNATURE_HEADER, "")
        if not hmac.compare_digest(signature, self._sign(body)):
            raise InvalidWebhook("bad signature")
        try:
            payload = json.loads(body)
            return WebhookEvent(
                provider_payment_id=str(payload["payment_id"]),
                status=ProviderPaymentStatus(payload["status"]),
                raw=payload,
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise InvalidWebhook("malformed payload") from exc
