"""Real concurrent transactions: only the database constraint can decide these races."""

import asyncio

import pytest

from tests.integration.helpers import at, book, code, register

pytestmark = pytest.mark.requires_overlap_constraints


async def test_two_users_racing_for_one_slot(committed_client, committed_world):
    client, world = committed_client, committed_world
    first = await register(client, "+77010000001", serial=1)
    second = await register(client, "+77010000002", serial=2)

    responses = await asyncio.gather(
        book(client, first, world.pc_ids[0], at(1, 18)),
        book(client, second, world.pc_ids[0], at(1, 18)),
    )

    assert sorted(r.status_code for r in responses) == [201, 409]
    loser = next(r for r in responses if r.status_code == 409)
    assert code(loser) == "SLOT_TAKEN"


async def test_many_users_racing_for_overlapping_slots(committed_client, committed_world):
    client, world = committed_client, committed_world
    users = [await register(client, f"+7701000001{n}", serial=n + 1) for n in range(6)]
    # All six requests overlap 18:30-19:00 on the same PC.
    starts = [at(1, 17), at(1, 17, 30), at(1, 18), at(1, 18), at(1, 18, 30), at(1, 17)]

    responses = await asyncio.gather(
        *(
            book(client, headers, world.pc_ids[0], start)
            for headers, start in zip(users, starts, strict=True)
        )
    )

    assert sorted(r.status_code for r in responses) == [201, 409, 409, 409, 409, 409]


async def test_one_user_double_submitting(committed_client, committed_world):
    """A double tap must not create two holds, even on different PCs."""
    client, world = committed_client, committed_world
    headers = await register(client, "+77010000001")

    responses = await asyncio.gather(
        book(client, headers, world.pc_ids[0], at(1, 18)),
        book(client, headers, world.pc_ids[1], at(1, 18)),
    )

    assert sorted(r.status_code for r in responses) == [201, 409]
    loser = next(r for r in responses if r.status_code == 409)
    assert code(loser) == "USER_BOOKING_OVERLAP"
