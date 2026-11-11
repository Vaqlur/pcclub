"""Identity verification (eGov IIN lookup) interface."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Protocol


class IdentityCheckStatus(StrEnum):
    VERIFIED = "verified"
    NOT_FOUND = "not_found"
    NAME_MISMATCH = "name_mismatch"


@dataclass(frozen=True)
class IdentityResult:
    status: IdentityCheckStatus
    # Set when status == VERIFIED. This is the authoritative birth date for the age rule.
    birth_date: date | None = None
    first_name: str | None = None
    last_name: str | None = None


class IdentityVerifierUnavailable(Exception):
    """The upstream registry could not be reached; the caller may retry later."""


class IdentityVerifier(Protocol):
    name: str

    async def verify(self, *, iin: str, first_name: str, last_name: str) -> IdentityResult:
        """Check that the IIN exists and belongs to this person.

        Raises IdentityVerifierUnavailable on transport/upstream failure.
        Implementations must never log the IIN.
        """
        ...
