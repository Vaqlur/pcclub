"""Kazakhstan IIN (ИИН / ЖСН) parsing and validation. Pure functions, no I/O.

Structure of the 12 digits:
    1-6   birth date YYMMDD
    7     century and sex: 1/2 = 18xx, 3/4 = 19xx, 5/6 = 20xx; odd = male, even = female
    8-11  registration serial
    12    check digit

Check digit: sum(digit[i] * weight[i]) mod 11 over the first 11 digits with weights 1..11.
If that gives 10, repeat with weights 3,4,...,11,1,2. If it is 10 again the number is not a
valid IIN.

Local parsing is only a first filter. The authoritative birth date comes from the
IdentityVerifier (eGov) and must match the one encoded here.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

Sex = Literal["male", "female"]

_WEIGHTS_1 = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
_WEIGHTS_2 = (3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2)
_CENTURY = {1: 1800, 2: 1800, 3: 1900, 4: 1900, 5: 2000, 6: 2000}


class InvalidIIN(ValueError):
    """The string is not a structurally valid IIN."""


@dataclass(frozen=True)
class IINInfo:
    birth_date: date
    sex: Sex


def check_digit(first_eleven: str) -> int | None:
    """Check digit for the first 11 digits, or None if no valid check digit exists."""
    digits = [int(c) for c in first_eleven]
    for weights in (_WEIGHTS_1, _WEIGHTS_2):
        remainder = sum(d * w for d, w in zip(digits, weights, strict=True)) % 11
        if remainder != 10:
            return remainder
    return None


def parse_iin(iin: str) -> IINInfo:
    if len(iin) != 12 or not (iin.isascii() and iin.isdigit()):
        raise InvalidIIN("IIN must be exactly 12 digits")

    century = _CENTURY.get(int(iin[6]))
    if century is None:
        raise InvalidIIN("unsupported century/sex digit")

    try:
        birth_date = date(century + int(iin[0:2]), int(iin[2:4]), int(iin[4:6]))
    except ValueError as exc:
        raise InvalidIIN("IIN does not encode a valid birth date") from exc

    if check_digit(iin[:11]) != int(iin[11]):
        raise InvalidIIN("IIN check digit mismatch")

    return IINInfo(birth_date=birth_date, sex="male" if int(iin[6]) % 2 else "female")


def is_valid_iin(iin: str) -> bool:
    try:
        parse_iin(iin)
    except InvalidIIN:
        return False
    return True


def build_iin(birth_date: date, sex: Sex = "male", serial: int = 1) -> str:
    """Build a checksum-valid IIN for seed data and tests (never for real people)."""
    if not 0 <= serial <= 9999:
        raise ValueError("serial must be 0..9999")
    base = birth_date.year // 100 * 100
    century_digit = {1800: 1, 1900: 3, 2000: 5}.get(base)
    if century_digit is None:
        raise ValueError("birth year must be within 1800..2099")
    if sex == "female":
        century_digit += 1
    first_eleven = f"{birth_date:%y%m%d}{century_digit}{serial:04d}"
    digit = check_digit(first_eleven)
    if digit is None:
        raise ValueError("no valid check digit for this date/serial; try another serial")
    return f"{first_eleven}{digit}"
