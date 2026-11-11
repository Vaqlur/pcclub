"""Mock eGov verifier for development and tests.

Any checksum-valid IIN is "found" with the birth date encoded in it. The registration
serial (digits 8-11) triggers failure scenarios:

    9991 -> not found in the registry
    9992 -> name does not match
    9993 -> registry unavailable
"""

from app.domain.iin import InvalidIIN, parse_iin
from app.integrations.identity.base import (
    IdentityCheckStatus,
    IdentityResult,
    IdentityVerifierUnavailable,
)

SERIAL_NOT_FOUND = 9991
SERIAL_NAME_MISMATCH = 9992
SERIAL_UNAVAILABLE = 9993


class MockIdentityVerifier:
    name = "mock"

    async def verify(self, *, iin: str, first_name: str, last_name: str) -> IdentityResult:
        try:
            info = parse_iin(iin)
        except InvalidIIN:
            return IdentityResult(status=IdentityCheckStatus.NOT_FOUND)

        serial = int(iin[7:11])
        if serial == SERIAL_UNAVAILABLE:
            raise IdentityVerifierUnavailable("mock registry is unavailable")
        if serial == SERIAL_NOT_FOUND:
            return IdentityResult(status=IdentityCheckStatus.NOT_FOUND)
        if serial == SERIAL_NAME_MISMATCH:
            return IdentityResult(status=IdentityCheckStatus.NAME_MISMATCH)

        return IdentityResult(
            status=IdentityCheckStatus.VERIFIED,
            birth_date=info.birth_date,
            first_name=first_name,
            last_name=last_name,
        )
