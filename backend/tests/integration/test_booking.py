import uuid
from datetime import time, timedelta

import pytest
from sqlalchemy import select, update

from app.models import Booking, Club, Pc, PcStatus, Zone
from tests.integration.helpers import (
    NOW,
    at,
    book,
    book_and_pay,
    code,
    login,
    parse_dt,
    pay,
    register,
)

PHONE = "+77010000001"


async def test_create_booking_holds_the_pc(client, world):
    headers = await register(client, PHONE)
    response = await book(client, headers, world.pc_ids[0], at(1, 18), at(1, 20))

    assert response.status_code == 201
    booking = response.json()
    assert booking["status"] == "pending_payment"
    assert booking["pc_id"] == str(world.pc_ids[0])
    assert booking["club_id"] == str(world.club_id)
    assert parse_dt(booking["starts_at"]) == at(1, 18)
    assert parse_dt(booking["ends_at"]) == at(1, 20)
    assert parse_dt(booking["hold_expires_at"]) == NOW + timedelta(minutes=10)
    assert booking["price_kzt"] == 2000
    assert booking["cancelled_at"] is None


async def test_price_uses_the_zone_rate_and_duration(client, world):
    headers = await register(client, PHONE)
    response = await book(client, headers, world.vip_pc_id, at(1, 18), at(1, 19, 30))
    assert response.json()["price_kzt"] == 2250  # 1.5 h x 1500


async def test_booking_requires_authentication(client, world):
    response = await book(client, {}, world.pc_ids[0], at(1, 18))
    assert response.status_code == 401


async def test_booking_requires_verified_identity(client, world):
    headers = await login(client, PHONE)
    response = await book(client, headers, world.pc_ids[0], at(1, 18))
    assert response.status_code == 403
    assert code(response) == "IDENTITY_NOT_VERIFIED"


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (at(1, 10), at(1, 12)),  # in the past
        (at(1, 12), at(1, 14)),  # starts exactly now
        (at(1, 18, 15), at(1, 20, 15)),  # not aligned to 30 minutes
        (at(1, 18), at(1, 18, 30)),  # shorter than 1 hour
        (at(1, 18), at(2, 7)),  # longer than 12 hours
        (at(16, 18), at(16, 20)),  # more than 14 days ahead
        (at(1, 20), at(1, 18)),  # ends before it starts
    ],
)
async def test_invalid_slots(client, world, start, end):
    headers = await register(client, PHONE)
    response = await book(client, headers, world.pc_ids[0], start, end)
    assert response.status_code == 422
    assert code(response) == "INVALID_SLOT"


async def test_naive_datetime_is_rejected(client, world):
    headers = await register(client, PHONE)
    response = await client.post(
        "/v1/bookings",
        headers=headers,
        json={
            "pc_id": str(world.pc_ids[0]),
            "starts_at": "2026-06-01T18:00:00",
            "ends_at": "2026-06-01T20:00:00",
        },
    )
    assert response.status_code == 422
    assert code(response) == "VALIDATION_ERROR"


async def test_slot_given_in_another_offset_is_the_same_instant(client, world):
    headers = await register(client, PHONE)
    response = await client.post(
        "/v1/bookings",
        headers=headers,
        json={
            "pc_id": str(world.pc_ids[0]),
            "starts_at": "2026-06-01T13:00:00Z",  # 18:00 in Almaty
            "ends_at": "2026-06-01T15:00:00Z",
        },
    )
    assert response.status_code == 201
    assert parse_dt(response.json()["starts_at"]) == at(1, 18)


async def test_unknown_pc(client, world):
    headers = await register(client, PHONE)
    response = await book(client, headers, uuid.uuid4(), at(1, 18))
    assert response.status_code == 404


@pytest.mark.parametrize("reason", ["maintenance", "retired", "zone_inactive", "club_inactive"])
async def test_unbookable_pc(client, world, db, reason):
    headers = await register(client, PHONE)
    pc_id = world.pc_ids[0]
    if reason in ("maintenance", "retired"):
        await db.execute(update(Pc).where(Pc.id == pc_id).values(status=PcStatus(reason)))
    elif reason == "zone_inactive":
        await db.execute(
            update(Zone).where(Zone.id == world.standard_zone_id).values(is_active=False)
        )
    else:
        await db.execute(update(Club).where(Club.id == world.club_id).values(is_active=False))
    await db.commit()

    response = await book(client, headers, pc_id, at(1, 18))
    assert response.status_code == 409
    assert code(response) == "PC_UNAVAILABLE"


async def test_opening_hours(client, world, db):
    await db.execute(
        update(Club).where(Club.id == world.club_id).values(opens_at=time(10), closes_at=time(23))
    )
    await db.commit()
    headers = await register(client, PHONE)
    pc = world.pc_ids[0]

    assert (await book(client, headers, pc, at(1, 21), at(1, 23))).status_code == 201
    response = await book(client, headers, pc, at(2, 8), at(2, 10))
    assert response.status_code == 422
    assert code(response) == "OUTSIDE_OPENING_HOURS"
    assert code(await book(client, headers, pc, at(2, 22), at(3, 0))) == "OUTSIDE_OPENING_HOURS"


# --- history -----------------------------------------------------------------------------------


async def test_history_is_newest_first_and_paginated(client, world):
    headers = await register(client, PHONE)
    ids = []
    for hour in (14, 16, 18, 20):
        response = await book(client, headers, world.pc_ids[0], at(2, hour))
        assert response.status_code == 201, response.text
        ids.append(response.json()["id"])

    page = (await client.get("/v1/bookings", headers=headers, params={"limit": 3})).json()
    assert [b["id"] for b in page["items"]] == ids[:0:-1]
    assert page["next_cursor"] == ids[1]

    page = (
        await client.get(
            "/v1/bookings", headers=headers, params={"limit": 3, "cursor": page["next_cursor"]}
        )
    ).json()
    assert [b["id"] for b in page["items"]] == [ids[0]]
    assert page["next_cursor"] is None


async def test_history_status_filter(client, world):
    headers = await register(client, PHONE)
    confirmed = await book_and_pay(client, headers, world.pc_ids[0], at(2, 14))
    pending = (await book(client, headers, world.pc_ids[0], at(2, 18))).json()

    async def ids(status):
        response = await client.get("/v1/bookings", headers=headers, params={"status": status})
        assert response.status_code == 200, response.text
        return [b["id"] for b in response.json()["items"]]

    assert await ids("confirmed") == [confirmed["id"]]
    assert await ids("pending_payment") == [pending["id"]]
    assert await ids("cancelled") == []
    response = await client.get("/v1/bookings", headers=headers, params={"status": "bogus"})
    assert response.status_code == 422


async def test_bookings_are_private(client, world):
    owner = await register(client, PHONE)
    stranger = await register(client, "+77010000002", serial=2)
    booking = (await book(client, owner, world.pc_ids[0], at(1, 18))).json()

    assert (await client.get(f"/v1/bookings/{booking['id']}", headers=owner)).status_code == 200
    assert (await client.get(f"/v1/bookings/{booking['id']}", headers=stranger)).status_code == 404
    assert (await client.get("/v1/bookings", headers=stranger)).json()["items"] == []
    response = await client.post(f"/v1/bookings/{booking['id']}/cancel", headers=stranger)
    assert response.status_code == 404
    response = await pay(client, stranger, booking["id"])
    assert response.status_code == 404


# --- hold expiry -------------------------------------------------------------------------------


async def test_unpaid_hold_expires(client, world, clock):
    headers = await register(client, PHONE)
    booking = (await book(client, headers, world.pc_ids[0], at(1, 18))).json()

    clock.advance(minutes=9, seconds=59)
    response = await client.get(f"/v1/bookings/{booking['id']}", headers=headers)
    assert response.json()["status"] == "pending_payment"

    clock.advance(seconds=1)
    response = await client.get(f"/v1/bookings/{booking['id']}", headers=headers)
    assert response.json()["status"] == "expired"
    history = (await client.get("/v1/bookings", headers=headers)).json()
    assert history["items"][0]["status"] == "expired"


async def test_paid_booking_does_not_expire(client, world, clock):
    headers = await register(client, PHONE)
    booking = await book_and_pay(client, headers, world.pc_ids[0], at(1, 18))
    clock.advance(minutes=25)  # well past the 10-minute hold, within the access token TTL
    response = await client.get(f"/v1/bookings/{booking['id']}", headers=headers)
    assert response.json()["status"] == "confirmed"


# --- cancellation ------------------------------------------------------------------------------


async def test_cancel_unpaid_booking(client, world, clock, mock_provider):
    headers = await register(client, PHONE)
    booking = (await book(client, headers, world.pc_ids[0], at(1, 18))).json()
    clock.advance(minutes=1)

    response = await client.post(f"/v1/bookings/{booking['id']}/cancel", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert parse_dt(response.json()["cancelled_at"]) == NOW + timedelta(minutes=1)
    assert mock_provider.refunds == []


async def test_cancel_paid_booking_refunds(client, world, mock_provider):
    headers = await register(client, PHONE)
    booking = await book_and_pay(client, headers, world.pc_ids[0], at(1, 18))

    response = await client.post(f"/v1/bookings/{booking['id']}/cancel", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert [amount for _, amount in mock_provider.refunds] == [2000]


async def test_failed_refund_keeps_the_booking(client, world, mock_provider):
    headers = await register(client, PHONE)
    booking = await book_and_pay(client, headers, world.pc_ids[0], at(1, 18))
    mock_provider.fail_next_refund = True

    response = await client.post(f"/v1/bookings/{booking['id']}/cancel", headers=headers)
    assert response.status_code == 502
    assert code(response) == "PAYMENT_PROVIDER_ERROR"
    current = (await client.get(f"/v1/bookings/{booking['id']}", headers=headers)).json()
    assert current["status"] == "confirmed"

    # The retry succeeds and refunds exactly once.
    response = await client.post(f"/v1/bookings/{booking['id']}/cancel", headers=headers)
    assert response.json()["status"] == "cancelled"
    assert len(mock_provider.refunds) == 1


async def test_cannot_cancel_twice_or_after_expiry(client, world, clock):
    headers = await register(client, PHONE)
    first = (await book(client, headers, world.pc_ids[0], at(1, 18))).json()
    assert (await client.post(f"/v1/bookings/{first['id']}/cancel", headers=headers)).is_success
    response = await client.post(f"/v1/bookings/{first['id']}/cancel", headers=headers)
    assert response.status_code == 409
    assert code(response) == "BOOKING_NOT_CANCELLABLE"

    second = (await book(client, headers, world.pc_ids[0], at(1, 18))).json()
    clock.advance(minutes=11)
    response = await client.post(f"/v1/bookings/{second['id']}/cancel", headers=headers)
    assert code(response) == "BOOKING_NOT_CANCELLABLE"
    assert response.json()["error"]["details"] == {"status": "expired"}


async def test_cannot_cancel_after_start(client, world, clock, mock_provider):
    headers = await register(client, PHONE)
    booking = await book_and_pay(client, headers, world.pc_ids[0], at(1, 18))
    clock.set(at(1, 18))
    headers = await login(client, PHONE)  # the old access token expired hours ago

    response = await client.post(f"/v1/bookings/{booking['id']}/cancel", headers=headers)
    assert response.status_code == 409
    assert code(response) == "BOOKING_ALREADY_STARTED"
    assert mock_provider.refunds == []


# --- double booking: enforced by the database (migration 0002) ---------------------------------

overlap = pytest.mark.requires_overlap_constraints


@overlap
@pytest.mark.parametrize(
    ("start", "end"),
    [
        (at(1, 18), at(1, 20)),  # identical
        (at(1, 17), at(1, 19)),  # overlaps the beginning
        (at(1, 19), at(1, 21)),  # overlaps the end
        (at(1, 18, 30), at(1, 19, 30)),  # inside
        (at(1, 17), at(1, 21)),  # around
    ],
)
async def test_overlapping_booking_on_the_same_pc_is_rejected(client, world, start, end):
    first = await register(client, PHONE)
    second = await register(client, "+77010000002", serial=2)
    assert (await book(client, first, world.pc_ids[0], at(1, 18), at(1, 20))).status_code == 201

    response = await book(client, second, world.pc_ids[0], start, end)
    assert response.status_code == 409
    assert code(response) == "SLOT_TAKEN"


@overlap
async def test_back_to_back_and_other_pcs_are_fine(client, world):
    first = await register(client, PHONE)
    second = await register(client, "+77010000002", serial=2)
    pc = world.pc_ids[0]
    assert (await book(client, first, pc, at(1, 18), at(1, 20))).status_code == 201

    assert (await book(client, second, pc, at(1, 16), at(1, 18))).status_code == 201
    assert (await book(client, first, pc, at(1, 20), at(1, 22))).status_code == 201
    third = await register(client, "+77010000003", serial=3)
    assert (await book(client, third, world.pc_ids[1], at(1, 18), at(1, 20))).status_code == 201


@overlap
async def test_user_cannot_hold_two_overlapping_bookings(client, world):
    headers = await register(client, PHONE)
    assert (await book(client, headers, world.pc_ids[0], at(1, 18), at(1, 20))).status_code == 201

    response = await book(client, headers, world.pc_ids[1], at(1, 19), at(1, 21))
    assert response.status_code == 409
    assert code(response) == "USER_BOOKING_OVERLAP"


@overlap
async def test_confirmed_booking_blocks_the_slot(client, world, clock):
    first = await register(client, PHONE)
    second = await register(client, "+77010000002", serial=2)
    await book_and_pay(client, first, world.pc_ids[0], at(1, 18))
    clock.advance(minutes=25)  # long after any hold would have expired

    assert code(await book(client, second, world.pc_ids[0], at(1, 18))) == "SLOT_TAKEN"


@overlap
async def test_expired_hold_frees_the_slot(client, world, clock, db):
    first = await register(client, PHONE)
    second = await register(client, "+77010000002", serial=2)
    stale = (await book(client, first, world.pc_ids[0], at(1, 18))).json()

    clock.advance(minutes=9)
    assert code(await book(client, second, world.pc_ids[0], at(1, 18))) == "SLOT_TAKEN"
    clock.advance(minutes=1)
    assert (await book(client, second, world.pc_ids[0], at(1, 18))).status_code == 201

    status = await db.scalar(select(Booking.status).where(Booking.id == uuid.UUID(stale["id"])))
    assert status == "expired"


@overlap
async def test_cancelled_booking_frees_the_slot(client, world):
    first = await register(client, PHONE)
    second = await register(client, "+77010000002", serial=2)
    booking = await book_and_pay(client, first, world.pc_ids[0], at(1, 18))
    assert code(await book(client, second, world.pc_ids[0], at(1, 18))) == "SLOT_TAKEN"

    await client.post(f"/v1/bookings/{booking['id']}/cancel", headers=first)
    assert (await book(client, second, world.pc_ids[0], at(1, 18))).status_code == 201
