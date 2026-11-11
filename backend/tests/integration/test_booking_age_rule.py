"""The age rule end to end: users under 18 cannot book 22:00-06:00 club-local time."""

from datetime import date, time
from zoneinfo import ZoneInfo

import pytest

from app.models import Club, Pc, Zone
from tests.integration.helpers import ADULT_BIRTH, MINOR_BIRTH, at, book, code, login, register

PHONE = "+77010000001"


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (at(1, 14), at(1, 16)),  # afternoon
        (at(1, 20), at(1, 22)),  # ends exactly at 22:00
        (at(2, 6), at(2, 8)),  # starts exactly at 06:00
        (at(2, 10), at(2, 22)),  # the longest allowed day booking
    ],
)
async def test_minor_can_book_daytime(client, world, start, end):
    headers = await register(client, PHONE, MINOR_BIRTH)
    response = await book(client, headers, world.pc_ids[0], start, end)
    assert response.status_code == 201, response.text


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (at(1, 21), at(1, 22, 30)),  # 30 minutes past 22:00
        (at(1, 21), at(1, 23)),
        (at(1, 22), at(1, 23)),  # starts at 22:00
        (at(1, 23), at(2, 1)),  # across midnight
        (at(2, 2), at(2, 4)),  # deep night
        (at(2, 5), at(2, 6)),  # ends at 06:00 but lies in the night
        (at(2, 5), at(2, 7)),
        (at(1, 20), at(2, 8)),  # contains the whole night
    ],
)
async def test_minor_cannot_book_at_night(client, world, start, end):
    headers = await register(client, PHONE, MINOR_BIRTH)
    response = await book(client, headers, world.pc_ids[0], start, end)

    assert response.status_code == 403
    assert code(response) == "MINOR_NIGHT_RESTRICTION"
    assert response.json()["error"]["details"] == {
        "adult_age": 18,
        "night_start": "22:00",
        "night_end": "06:00",
        "timezone": "Asia/Almaty",
    }
    history = (await client.get("/v1/bookings", headers=headers)).json()
    assert history["items"] == []  # nothing was held


@pytest.mark.parametrize(
    ("start", "end"),
    [(at(1, 21), at(1, 23)), (at(1, 22), at(2, 6)), (at(2, 2), at(2, 4)), (at(1, 20), at(2, 8))],
)
async def test_adult_can_book_at_night(client, world, start, end):
    headers = await register(client, PHONE, ADULT_BIRTH)
    response = await book(client, headers, world.pc_ids[0], start, end)
    assert response.status_code == 201, response.text


async def test_age_comes_from_the_verified_iin(client, world):
    """Two users, same request: only the birth date encoded in the IIN differs."""
    minor = await register(client, PHONE, date(2008, 6, 2))  # 17 until tomorrow
    adult = await register(client, "+77010000002", date(2008, 6, 1))  # 18 today

    assert code(await book(client, minor, world.pc_ids[0], at(1, 22))) == "MINOR_NIGHT_RESTRICTION"
    assert (await book(client, adult, world.pc_ids[0], at(1, 22))).status_code == 201


async def test_around_the_18th_birthday(client, world):
    # The clock is at 2026-06-01 12:00; this user turns 18 on 2026-06-02 at 00:00 local.
    headers = await register(client, PHONE, date(2008, 6, 2))
    pc = world.pc_ids[0]

    # Tonight they are still 17 ...
    assert code(await book(client, headers, pc, at(1, 22), at(1, 23))) == "MINOR_NIGHT_RESTRICTION"
    # ... even if most of the booking falls on the birthday.
    assert code(await book(client, headers, pc, at(1, 23), at(2, 3))) == "MINOR_NIGHT_RESTRICTION"
    # From midnight of the birthday the night is open.
    assert (await book(client, headers, pc, at(2, 0), at(2, 3))).status_code == 201
    assert (await book(client, headers, pc, at(2, 22), at(3, 2))).status_code == 201


async def test_night_is_judged_in_the_club_timezone(client, world, db):
    """17:00-19:00 Almaty time is 21:00-23:00 in a Tokyo club: night there, evening here."""
    tokyo = ZoneInfo("Asia/Tokyo")
    club = Club(
        organization_id=world.org_id,
        name="Tokyo Arena",
        city="Tokyo",
        address="Shibuya 1",
        timezone="Asia/Tokyo",
    )
    db.add(club)
    await db.flush()
    zone = Zone(club_id=club.id, name="Standard", price_per_hour_kzt=1000)
    db.add(zone)
    await db.flush()
    tokyo_pc = Pc(club_id=club.id, zone_id=zone.id, label="T-01")
    db.add(tokyo_pc)
    await db.commit()

    headers = await register(client, PHONE, MINOR_BIRTH)
    start, end = at(1, 17), at(1, 19)
    assert start.astimezone(tokyo).hour == 21

    response = await book(client, headers, tokyo_pc.id, start, end)
    assert code(response) == "MINOR_NIGHT_RESTRICTION"
    assert response.json()["error"]["details"]["timezone"] == "Asia/Tokyo"
    # The very same instants are fine in the Almaty club.
    assert (await book(client, headers, world.pc_ids[0], start, end)).status_code == 201

    # And the reverse: 03:00-05:00 Almaty is night here but 07:00-09:00 in Tokyo.
    start, end = at(2, 3), at(2, 5)
    assert (
        code(await book(client, headers, world.pc_ids[0], start, end)) == "MINOR_NIGHT_RESTRICTION"
    )
    assert (await book(client, headers, tokyo_pc.id, start, end)).status_code == 201


async def test_night_window_is_configurable(client, world, settings):
    settings.night_start = time(23, 0)
    settings.night_end = time(7, 0)
    headers = await register(client, PHONE, MINOR_BIRTH)
    pc = world.pc_ids[0]

    assert (await book(client, headers, pc, at(1, 21), at(1, 23))).status_code == 201
    response = await book(client, headers, pc, at(2, 6), at(2, 8))
    assert code(response) == "MINOR_NIGHT_RESTRICTION"
    assert response.json()["error"]["details"]["night_start"] == "23:00"


async def test_unverified_user_cannot_bypass_the_rule(client, world):
    """Without a verified IIN there is no birth date, so there is no booking at all."""
    headers = await login(client, PHONE)
    for start in (at(1, 14), at(1, 22)):
        response = await book(client, headers, world.pc_ids[0], start)
        assert response.status_code == 403
        assert code(response) == "IDENTITY_NOT_VERIFIED"
