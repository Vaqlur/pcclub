from datetime import date

import pytest

from app.domain.iin import InvalidIIN, build_iin, check_digit, is_valid_iin, parse_iin

# Hand-computed: digits 9,0,0,1,0,1,3,0,0,0,0 x weights 1..11 = 9+4+6+21 = 40; 40 mod 11 = 7.
IIN_1990_MALE = "900101300007"
# First pass: 16+20+5+30+35+80 = 186, 186 mod 11 = 10 -> second pass (weights 3..11,1,2):
# 32+30+7+40+45+8 = 162, 162 mod 11 = 8.
IIN_SECOND_PASS = "080515500808"
# Same but serial 0081: both passes give 10 -> no valid check digit exists.
FIRST_ELEVEN_NO_CHECK_DIGIT = "08051550081"


def test_parses_birth_date_and_sex():
    info = parse_iin(IIN_1990_MALE)
    assert info.birth_date == date(1990, 1, 1)
    assert info.sex == "male"


def test_second_pass_check_digit():
    assert check_digit(IIN_SECOND_PASS[:11]) == 8
    info = parse_iin(IIN_SECOND_PASS)
    assert info.birth_date == date(2008, 5, 15)
    assert info.sex == "male"


@pytest.mark.parametrize("last_digit", range(10))
def test_no_valid_check_digit_exists(last_digit):
    assert check_digit(FIRST_ELEVEN_NO_CHECK_DIGIT) is None
    with pytest.raises(InvalidIIN):
        parse_iin(f"{FIRST_ELEVEN_NO_CHECK_DIGIT}{last_digit}")


@pytest.mark.parametrize(
    ("century_digit", "year", "sex"),
    [(1, 1899, "male"), (2, 1899, "female"), (3, 1999, "male"), (4, 1999, "female"),
     (5, 2099, "male"), (6, 2099, "female")],
)  # fmt: skip
def test_century_and_sex_digit(century_digit, year, sex):
    first_eleven = f"991231{century_digit}0001"
    iin = f"{first_eleven}{check_digit(first_eleven)}"
    info = parse_iin(iin)
    assert info.birth_date == date(year, 12, 31)
    assert info.sex == sex


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "90010130000",  # 11 digits
        "9001013000070",  # 13 digits
        "90010130000a",
        "9001013０0007",  # full-width digit
        " 90010130000",
        "900101300008",  # wrong check digit
        "901301300001",  # month 13
        "900230300001",  # 30 February
        "900101000001",  # century digit 0
        "900101700001",  # century digit 7
    ],
)
def test_rejects_invalid(bad):
    assert not is_valid_iin(bad)
    with pytest.raises(InvalidIIN):
        parse_iin(bad)


def test_wrong_check_digit_is_always_detected():
    for digit in range(10):
        candidate = f"{IIN_1990_MALE[:11]}{digit}"
        assert is_valid_iin(candidate) is (digit == 7)


def test_checksum_does_not_catch_every_typo():
    # Documented limitation of the two-pass scheme: 900101... -> 901101... moves the first
    # pass to 10 and the second pass happens to give 7 again. This is why the local check is
    # only a filter and the IdentityVerifier is authoritative.
    assert is_valid_iin("901101300007")


def test_leap_day_birth_date():
    iin = build_iin(date(2008, 2, 29), "female", serial=7)
    assert parse_iin(iin).birth_date == date(2008, 2, 29)
    assert parse_iin(iin).sex == "female"


@pytest.mark.parametrize("sex", ["male", "female"])
def test_build_iin_round_trip(sex):
    for serial in range(50):
        birth = date(2009, 3, 14)
        try:
            iin = build_iin(birth, sex, serial)
        except ValueError:
            continue  # this serial has no valid check digit
        info = parse_iin(iin)
        assert (info.birth_date, info.sex) == (birth, sex)


def test_build_iin_reports_impossible_serial():
    with pytest.raises(ValueError, match="check digit"):
        build_iin(date(2008, 5, 15), "male", serial=81)
