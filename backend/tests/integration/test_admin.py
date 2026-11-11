import uuid

import pytest

from tests.integration.conftest import seed_world
from tests.integration.helpers import at, book_and_pay, code, login, register


async def staff_login(client, world) -> dict[str, str]:
    response = await client.post(
        "/v1/admin/auth/login",
        json={"email": world.staff_email, "password": world.staff_password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
async def staff(client, world):
    return await staff_login(client, world)


async def test_staff_login(client, world):
    response = await client.post(
        "/v1/admin/auth/login",
        json={"email": "  OWNER@example.com ", "password": world.staff_password},
    )
    assert response.status_code == 200  # email is case-insensitive

    for email, password in [(world.staff_email, "wrong"), ("nobody@example.com", "whatever")]:
        response = await client.post(
            "/v1/admin/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 401
        assert code(response) == "INVALID_CREDENTIALS"


async def test_staff_refresh_token(client, world):
    tokens = (
        await client.post(
            "/v1/admin/auth/login",
            json={"email": world.staff_email, "password": world.staff_password},
        )
    ).json()
    rotated = await client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert rotated.status_code == 200
    headers = {"Authorization": f"Bearer {rotated.json()['access_token']}"}
    assert (await client.get("/v1/admin/clubs", headers=headers)).status_code == 200


async def test_customer_and_staff_tokens_are_not_interchangeable(client, world, staff):
    customer = await login(client, "+77010000001")
    assert (await client.get("/v1/admin/clubs", headers=customer)).status_code == 401
    assert (await client.get("/v1/me", headers=staff)).status_code == 401
    assert (await client.get("/v1/admin/clubs")).status_code == 401


async def test_create_club_zone_and_pc(client, staff):
    response = await client.post(
        "/v1/admin/clubs",
        headers=staff,
        json={
            "name": "Cyber Hub",
            "city": "Shymkent",
            "address": "Tauke Khan 10",
            "opens_at": "10:00",
            "closes_at": "02:00",
        },
    )
    assert response.status_code == 201, response.text
    club = response.json()
    assert club["timezone"] == "Asia/Almaty"
    assert club["is_active"] is True

    response = await client.post(
        f"/v1/admin/clubs/{club['id']}/zones",
        headers=staff,
        json={"name": "Bootcamp", "price_per_hour_kzt": 1200},
    )
    assert response.status_code == 201, response.text
    zone = response.json()

    response = await client.post(
        f"/v1/admin/clubs/{club['id']}/pcs",
        headers=staff,
        json={"zone_id": zone["id"], "label": "B-01", "specs": {"monitor": "240Hz"}},
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "active"

    # Immediately visible to customers.
    public = (await client.get(f"/v1/clubs/{club['id']}/pcs")).json()
    assert [(p["label"], p["zone_name"], p["price_per_hour_kzt"]) for p in public] == [
        ("B-01", "Bootcamp", 1200)
    ]
    assert [c["name"] for c in (await client.get("/v1/admin/clubs", headers=staff)).json()] == [
        "Arena",
        "Cyber Hub",
    ]


async def test_club_validation(client, staff):
    base = {"name": "X", "city": "Almaty", "address": "Y"}
    for extra in (
        {"timezone": "Mars/Olympus"},
        {"opens_at": "10:00"},  # closes_at missing
        {"name": ""},
    ):
        response = await client.post("/v1/admin/clubs", headers=staff, json={**base, **extra})
        assert response.status_code == 422, extra
    response = await client.post(
        "/v1/admin/clubs", headers=staff, json={**base, "timezone": "Asia/Tashkent"}
    )
    assert response.status_code == 201


async def test_duplicates_and_foreign_zones(client, world, staff, db):
    url = f"/v1/admin/clubs/{world.club_id}"
    response = await client.post(
        f"{url}/zones", headers=staff, json={"name": "VIP", "price_per_hour_kzt": 1}
    )
    assert response.status_code == 409
    assert code(response) == "ZONE_NAME_TAKEN"

    response = await client.post(
        f"{url}/pcs", headers=staff, json={"zone_id": str(world.standard_zone_id), "label": "S-01"}
    )
    assert response.status_code == 409
    assert code(response) == "PC_LABEL_TAKEN"

    other_club = (
        await client.post(
            "/v1/admin/clubs", headers=staff, json={"name": "B", "city": "Almaty", "address": "Z"}
        )
    ).json()
    response = await client.post(
        f"/v1/admin/clubs/{other_club['id']}/pcs",
        headers=staff,
        json={"zone_id": str(world.standard_zone_id), "label": "P-01"},
    )
    assert response.status_code == 422
    assert code(response) == "ZONE_NOT_IN_CLUB"


async def test_updates(client, world, staff):
    response = await client.patch(
        f"/v1/admin/zones/{world.standard_zone_id}", headers=staff, json={"price_per_hour_kzt": 900}
    )
    assert response.status_code == 200
    assert response.json()["price_per_hour_kzt"] == 900

    response = await client.patch(
        f"/v1/admin/pcs/{world.pc_ids[0]}", headers=staff, json={"status": "maintenance"}
    )
    assert response.json()["status"] == "maintenance"
    public = (await client.get(f"/v1/clubs/{world.club_id}/pcs")).json()
    assert "S-01" not in [p["label"] for p in public]
    assert next(p for p in public if p["label"] == "S-02")["price_per_hour_kzt"] == 900
    # Staff still see the PC.
    admin_pcs = (await client.get(f"/v1/admin/clubs/{world.club_id}/pcs", headers=staff)).json()
    assert len(admin_pcs) == 4

    response = await client.patch(
        f"/v1/admin/clubs/{world.club_id}",
        headers=staff,
        json={"opens_at": "09:00", "closes_at": "23:30"},
    )
    assert response.json()["opens_at"] == "09:00:00"
    response = await client.patch(
        f"/v1/admin/clubs/{world.club_id}", headers=staff, json={"opens_at": None}
    )
    assert response.status_code == 422  # hours must be cleared together
    response = await client.patch(
        f"/v1/admin/clubs/{world.club_id}",
        headers=staff,
        json={"opens_at": None, "closes_at": None, "name": None},
    )
    assert response.status_code == 200
    assert response.json()["opens_at"] is None
    assert response.json()["name"] == "Arena"  # null on a required field is ignored

    response = await client.patch(
        f"/v1/admin/clubs/{world.club_id}", headers=staff, json={"is_active": False}
    )
    assert response.json()["is_active"] is False
    assert (await client.get(f"/v1/clubs/{world.club_id}")).status_code == 404
    assert (await client.get(f"/v1/admin/clubs/{world.club_id}", headers=staff)).status_code == 200


async def test_organizations_are_isolated(client, world, staff, db):
    other = await seed_world(db, email="rival@example.com")
    rival = await staff_login(client, other)

    assert [c["id"] for c in (await client.get("/v1/admin/clubs", headers=rival)).json()] == [
        str(other.club_id)
    ]
    club_url = f"/v1/admin/clubs/{world.club_id}"
    attempts = [
        await client.get(club_url, headers=rival),
        await client.patch(club_url, headers=rival, json={"name": "Hacked"}),
        await client.get(f"{club_url}/zones", headers=rival),
        await client.post(
            f"{club_url}/zones", headers=rival, json={"name": "Z", "price_per_hour_kzt": 1}
        ),
        await client.get(f"{club_url}/pcs", headers=rival),
        await client.post(
            f"{club_url}/pcs",
            headers=rival,
            json={"zone_id": str(world.standard_zone_id), "label": "X"},
        ),
        await client.patch(
            f"/v1/admin/zones/{world.standard_zone_id}",
            headers=rival,
            json={"price_per_hour_kzt": 1},
        ),
        await client.patch(
            f"/v1/admin/pcs/{world.pc_ids[0]}", headers=rival, json={"status": "retired"}
        ),
        await client.get(f"{club_url}/bookings", headers=rival, params={"date": "2026-06-01"}),
    ]
    assert [r.status_code for r in attempts] == [404] * len(attempts)

    # Nothing changed for the real owner.
    assert (await client.get(club_url, headers=staff)).json()["name"] == "Arena"
    zones = (await client.get(f"{club_url}/zones", headers=staff)).json()
    assert {z["name"]: z["price_per_hour_kzt"] for z in zones} == {"Standard": 1000, "VIP": 1500}

    # A rival cannot attach their PC to someone else's zone either.
    response = await client.post(
        f"/v1/admin/clubs/{other.club_id}/pcs",
        headers=rival,
        json={"zone_id": str(world.standard_zone_id), "label": "X"},
    )
    assert response.status_code == 422


async def test_club_bookings_for_a_day(client, world, staff):
    customer = await register(client, "+77010000001")
    first = await book_and_pay(client, customer, world.pc_ids[0], at(1, 18))
    second = await book_and_pay(client, customer, world.pc_ids[1], at(1, 23))  # into June 2
    third = await book_and_pay(client, customer, world.pc_ids[0], at(3, 10))

    async def ids(day):
        response = await client.get(
            f"/v1/admin/clubs/{world.club_id}/bookings", headers=staff, params={"date": day}
        )
        assert response.status_code == 200, response.text
        return [b["id"] for b in response.json()]

    assert await ids("2026-06-01") == [first["id"], second["id"]]
    assert await ids("2026-06-02") == [second["id"]]
    assert await ids("2026-06-03") == [third["id"]]
    assert await ids("2026-06-04") == []


async def test_unknown_ids_are_404(client, staff):
    assert (await client.get(f"/v1/admin/clubs/{uuid.uuid4()}", headers=staff)).status_code == 404
    response = await client.patch(
        f"/v1/admin/pcs/{uuid.uuid4()}", headers=staff, json={"label": "x"}
    )
    assert response.status_code == 404
