"""SMS delivery interface (used for login codes)."""

from typing import Protocol


class SmsDeliveryError(Exception):
    pass


class SmsSender(Protocol):
    name: str

    async def send(self, *, phone: str, text: str) -> None:
        """Send a text message to an E.164 phone number. Raises SmsDeliveryError on failure."""
        ...
