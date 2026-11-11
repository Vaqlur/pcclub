"""Builds integration adapters from settings.

To add a real adapter: implement the Protocol in app/integrations/<kind>/<name>.py and
register its factory here. Services depend only on the Protocols.
"""

from dataclasses import dataclass
from functools import lru_cache

from app.core.config import Settings, get_settings
from app.integrations.identity.base import IdentityVerifier
from app.integrations.identity.mock import MockIdentityVerifier
from app.integrations.payments.base import PaymentMethod, PaymentProvider
from app.integrations.payments.mock import MockPaymentProvider
from app.integrations.sms.base import SmsSender
from app.integrations.sms.mock import MockSmsSender


class UnknownProvider(ValueError):
    pass


@dataclass(frozen=True)
class PaymentProviders:
    """Payment providers by customer-facing method and by provider name (for webhooks)."""

    by_method: dict[PaymentMethod, PaymentProvider]

    def for_method(self, method: PaymentMethod) -> PaymentProvider:
        return self.by_method[method]

    def by_name(self, name: str) -> PaymentProvider | None:
        return next((p for p in self.by_method.values() if p.name == name), None)

    def by_name_or_raise(self, name: str) -> PaymentProvider:
        provider = self.by_name(name)
        if provider is None:
            raise UnknownProvider(f"payment provider {name!r} is not configured")
        return provider


def build_identity_verifier(settings: Settings) -> IdentityVerifier:
    if settings.identity_provider == "mock":
        return MockIdentityVerifier()
    raise UnknownProvider(f"identity provider {settings.identity_provider!r} is not implemented")


def build_sms_sender(settings: Settings) -> SmsSender:
    if settings.sms_provider == "mock":
        return MockSmsSender()
    raise UnknownProvider(f"sms provider {settings.sms_provider!r} is not implemented")


def build_payment_providers(settings: Settings) -> PaymentProviders:
    instances: dict[str, PaymentProvider] = {}

    def build(name: str) -> PaymentProvider:
        if name not in instances:
            if name == "mock":
                instances[name] = MockPaymentProvider(settings.mock_payment_webhook_secret)
            else:
                raise UnknownProvider(f"payment provider {name!r} is not implemented")
        return instances[name]

    return PaymentProviders(
        by_method={
            PaymentMethod.CARD: build(settings.payment_provider_card),
            PaymentMethod.KASPI: build(settings.payment_provider_kaspi),
        }
    )


# --- FastAPI dependencies (process-wide singletons; overridden in tests) ----------------------


@lru_cache
def get_identity_verifier() -> IdentityVerifier:
    return build_identity_verifier(get_settings())


@lru_cache
def get_sms_sender() -> SmsSender:
    return build_sms_sender(get_settings())


@lru_cache
def get_payment_providers() -> PaymentProviders:
    return build_payment_providers(get_settings())
