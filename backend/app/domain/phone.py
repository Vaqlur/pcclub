"""Kazakhstan phone number normalization to E.164 (+7XXXXXXXXXX). Pure functions, no I/O."""

import re

_SEPARATORS = re.compile(r"[\s\-()]")
_E164_KZ = re.compile(r"^\+7\d{10}$")


class InvalidPhone(ValueError):
    pass


def normalize_phone(raw: str) -> str:
    """Accepts +7 707 123-45-67, 87071234567, 77071234567 and returns +77071234567."""
    value = _SEPARATORS.sub("", raw)
    if len(value) == 11 and value.isascii() and value.isdigit() and value[0] in "78":
        value = "+7" + value[1:]
    if not _E164_KZ.fullmatch(value):
        raise InvalidPhone("phone must be a +7 number with 10 digits after the country code")
    return value
