import uuid
from datetime import time

from sqlalchemy import update

from app.models import Club, Pc, PcStatus, Zone
from tests.integration.helpers import at, book, book_and_pay, code, parse_dt, register


async def test_list_and_get_clubs(client, world, db):
    db.add_all(
        [
            Club(
                organization_id=world.org_id,
                name="Day Club",
                city="Astana",
                address="Mangilik El 1",
                opens_at=time(10),
                closes_at=time(23),
            ),
            Club(
                organization_id=world.org_id,
                name="Closed Club",
                city="Almaty",
                address="Dostyk 5",
                is_active=False,
            ),
        ]
    )
    await db.commit()

    clubs = (await client.get("/v1/clubs")).json()
    assert [(c["city"], c["name"]) for c in clubs] == [("Almaty", "Arena"), ("Astana", "Day Club")]
    assert clubs[0]["opens_at"] is None and clubs[0]["timezone"] == "Asia/Almaty"
    assert clubs[1]["opens_at"] == "10:00:00" and clubs[1]["closes_at"] == "23:00:00"

    astana = (await client.get("/v1/clubs", params={"city": "ASTANA"})).json()
    assert [c["name"] for c in astana] == ["Day Club"]

    response = await client.get(f"/v1/clubs/{world.club_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Arena"
    assert "organization_id" not in response.json()


async def test_unknown_or_inactive_club_is_404(client, world, db):
    assert (await client.get(f"/v1/clubs/{uuid.uuid4()}")).status_code == 404
    await db.execute(update(Club).where(Club.id == world.club_id).values(is_active=False))
    await db.commit()
    for path in ("", "/zones", "/pcs"):
        response = await client.get(f"/v1/clubs/{world.club_id}{path}")
        assert response.status_code == 404, path
        assert code(response) == "NOT_FOUND"


async def test_zones(client, world, db):
    db.add(Zone(club_id=world.club_id, name="Old zone", price_per_hour_kzt=1, is_active=False))
    await db.commit()
    zones = (await client.get(f"/v1/clubs/{world.club_id}/zones")).json()
    assert [(z["name"], z["price_per_hour_kzt"]) for z in zones] == [
        ("Standard", 1000),
        ("VIP", 1500),
    ]


async def test_pcs_by_zone_and_status(client, world, db):
    await db.execute(update(Pc).where(Pc.id == world.pc_ids[2]).values(status=PcStatus.MAINTENANCE))
    await db.commit()

    pcs = (await client.get(f"/v1/clubs/{world.club_id}/pcs")).json()
    assert [p["label"] for p in pcs] == ["S-01", "S-02", "VIP-01"]
    assert all(p["available"] is None for p in pcs)
    vip = pcs[-1]
    assert vip["zone_name"] == "VIP"
    assert vip["price_per_hour_kzt"] == 1500
    assert vip["specs"] == {"gpu": "RTX 5080"}

    only_vip = (
        await client.get(f"/v1/clubs/{world.club_id}/pcs", params={"zone_id": world.vip_zone_id})
    ).json()
    assert [p["label"] for p in only_vip] == ["VIP-01"]


async def test_availability_flag_for_a_window(client, world):
    headers = await register(client, "+77010000001")
    await book_and_pay(client, headers, world.pc_ids[0], at(1, 18))  # 18:00-20:00, confirmed
    other = await register(client, "+77010000002", serial=2)
    assert (await book(client, other, world.pc_ids[1], at(1, 19))).status_code == 201  # held

    async def availability(start, end):
        response = await client.get(
            f"/v1/clubs/{world.club_id}/pcs",
            params={"from": start.isoformat(), "to": end.isoformat()},
        )
        assert response.status_code == 200, response.text
        return {p["label"]: p["available"] for p in response.json()}

    assert await availability(at(1, 19), at(1, 20)) == {
        "S-01": False,
        "S-02": False,
        "S-03": True,
        "VIP-01": True,
    }
    # Half-open intervals: a slot starting when a booking ends is free.
    assert (await availability(at(1, 20), at(1, 21)))["S-01"] is True
    assert (await availability(at(1, 16), at(1, 18)))["S-01"] is True
    assert (await availability(at(1, 17), at(1, 18, 30)))["S-01"] is False


async def test_unpaid_hold_stops_blocking_after_expiry(client, world, clock):
    headers = await register(client, "+77010000001")
    assert (await book(client, headers, world.pc_ids[0], at(1, 18))).status_code == 201
    params = {"from": at(1, 18).isoformat(), "to": at(1, 20).isoformat()}

    pcs = (await client.get(f"/v1/clubs/{world.club_id}/pcs", params=params)).json()
    assert pcs[0]["available"] is False
    clock.advance(minutes=10)
    pcs = (await client.get(f"/v1/clubs/{world.club_id}/pcs", params=params)).json()
    assert pcs[0]["available"] is True


async def test_window_validation(client, world):
    url = f"/v1/clubs/{world.club_id}/pcs"
    response = await client.get(url, params={"from": at(1, 18).isoformat()})
    assert response.status_code == 422
    response = await client.get(
        url, params={"from": at(1, 20).isoformat(), "to": at(1, 18).isoformat()}
    )
    assert response.status_code == 422
    assert code(response) == "INVALID_SLOT"
    response = await client.get(
        url, params={"from": "2026-06-01T18:00:00", "to": "2026-06-01T20:00:00"}
    )
    assert response.status_code == 422  # naive datetimes are rejected
    assert code(response) == "VALIDATION_ERROR"


async def test_pc_busy_intervals_for_a_local_day(client, world):
    headers = await register(client, "+77010000001")
    pc = world.pc_ids[0]
    await book_and_pay(client, headers, pc, at(1, 18))  # Jun 1 18:00-20:00
    await book_and_pay(client, headers, pc, at(1, 23))  # Jun 1 23:00 - Jun 2 01:00
    await book_and_pay(client, headers, pc, at(2, 10))  # Jun 2 10:00-12:00

    async def busy(day):
        response = await client.get(f"/v1/pcs/{pc}/availability", params={"date": day})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["timezone"] == "Asia/Almaty"
        return [(parse_dt(i["starts_at"]), parse_dt(i["ends_at"])) for i in body["busy"]]

    assert await busy("2026-06-01") == [(at(1, 18), at(1, 20)), (at(1, 23), at(2, 1))]
    # The booking that crosses midnight shows up on both days.
    assert await busy("2026-06-02") == [(at(1, 23), at(2, 1)), (at(2, 10), at(2, 12))]
    assert await busy("2026-06-03") == []

    assert (
        await client.get(f"/v1/pcs/{uuid.uuid4()}/availability", params={"date": "2026-06-01"})
    ).status_code == 404
