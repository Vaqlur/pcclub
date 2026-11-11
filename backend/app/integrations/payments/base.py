"""Payment provider interface (card acquirer, Kaspi).

Flow: create_payment() returns a redirect URL / deeplink for the customer. The provider
later calls our webhook; parse_webhook() authenticates and normalizes that call. Booking
state only ever changes from a verified webhook event, never from the client.
"""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class PaymentMethod(StrEnum):
    CARD = "card"
    KASPI = "kaspi"


class ProviderPaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class CreatedPayment:
    provider_payment_id: str
    redirect_url: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WebhookEvent:
    provider_payment_id: str
    status: ProviderPaymentStatus
    raw: dict[str, Any] = field(default_factory=dict)


class PaymentProviderError(Exception):
    """The provider rejected the request or could not be reached."""


class InvalidWebhook(Exception):
    """Webhook signature or payload is not valid; the request must be ignored."""


class PaymentProvider(Protocol):
    name: str

    async def create_payment(
        self, *, payment_id: uuid.UUID, amount_kzt: int, description: str
    ) -> CreatedPayment:
        """Start a payment. `payment_id` is our id and doubles as the provider idempotency key."""
        ...

    async def refund(self, *, provider_payment_id: str, amount_kzt: int) -> None:
        """Refund a succeeded payment in full. Raises PaymentProviderError on failure."""
        ...

    def parse_webhook(self, *, headers: Mapping[str, str], body: bytes) -> WebhookEvent:
        """Authenticate and decode a provider callback. Raises InvalidWebhook."""
        ...
