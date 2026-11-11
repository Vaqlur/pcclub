from tests.integration.helpers import ADULT_BIRTH, at, book_and_pay, register


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_full_customer_flow(client, world):
    """Login -> verify IIN -> browse -> book -> pay -> confirmed -> history."""
    headers = await register(client, "+77010000001", ADULT_BIRTH)

    clubs = (await client.get("/v1/clubs", params={"city": "almaty"})).json()
    assert [c["name"] for c in clubs] == ["Arena"]
    pcs = (await client.get(f"/v1/clubs/{world.club_id}/pcs")).json()
    assert len(pcs) == 4

    booking = await book_and_pay(client, headers, world.pc_ids[0], at(1, 18))
    assert booking["price_kzt"] == 2000

    history = (await client.get("/v1/bookings", headers=headers)).json()
    assert [b["id"] for b in history["items"]] == [booking["id"]]
    assert history["next_cursor"] is None
