"""Mock SMS sender: logs the message and keeps it in memory for tests."""

import logging
from dataclasses import dataclass

logger = logging.getLogger("pcclub.sms.mock")


@dataclass(frozen=True)
class SentSms:
    phone: str
    text: str


class MockSmsSender:
    name = "mock"

    def __init__(self) -> None:
        self.sent: list[SentSms] = []

    async def send(self, *, phone: str, text: str) -> None:
        self.sent.append(SentSms(phone=phone, text=text))
        del self.sent[:-100]  # bounded memory in long-running dev servers
        logger.info("MOCK SMS to %s: %s", phone, text)
