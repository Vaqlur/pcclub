"""Shared helpers for API tests."""

import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from app.domain.iin import build_iin

ALMATY = ZoneInfo("Asia/Almaty")
# The test clock starts here: Monday 2026-06-01 12:00 in Almaty (07:00 UTC).
NOW = datetime(2026, 6, 1, 12, 0, tzinfo=ALMATY)
OTP_CODE = "000000"

ADULT_BIRTH = date(2000, 1, 15)
MINOR_BIRTH = date(2010, 3, 10)  # 16 years old at NOW


def at(day: int, hour: int, minute: int = 0, tz: ZoneInfo = ALMATY) -> datetime:
    """A club-local time in June 2026."""
    return datetime(2026, 6, day, hour, minute, tzinfo=tz)


def code(response: httpx.Response) -> str:
    return response.json()["error"]["code"]


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def iin_for(birth_date: date, serial: int = 1) -> str:
    """A checksum-valid IIN; bumps the serial if this one has no valid check digit."""
    for candidate in range(serial, serial + 20):
        try:
            return build_iin(birth_date, "male", candidate)
        except ValueError:
            continue
    raise AssertionError("no valid IIN found")


async def login(client: httpx.AsyncClient, phone: str) -> dict[str, str]:
    response = await client.post("/v1/auth/otp/request", json={"phone": phone})
    assert response.status_code == 204, response.text
    response = await client.post("/v1/auth/otp/verify", json={"phone": phone, "code": OTP_CODE})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def register(
    client: httpx.AsyncClient,
    phone: str,
    birth_date: date = ADULT_BIRTH,
    serial: int = 1,
) -> dict[str, str]:
    """Log in and verify identity with an IIN encoding `birth_date`."""
    headers = await login(client, phone)
    response = await client.post(
        "/v1/me/identity",
        headers=headers,
        json={"iin": iin_for(birth_date, serial), "first_name": "Test", "last_name": "User"},
    )
    assert response.status_code == 200, response.text
    return headers


async def book(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    pc_id: uuid.UUID,
    start: datetime,
    end: datetime | None = None,
) -> httpx.Response:
    end = end or start + timedelta(hours=2)
    return await client.post(
        "/v1/bookings",
        headers=headers,
        json={"pc_id": str(pc_id), "starts_at": start.isoformat(), "ends_at": end.isoformat()},
    )


async def pay(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    booking_id: str,
    method: str = "card",
    key: str | None = None,
) -> httpx.Response:
    return await client.post(
        f"/v1/bookings/{booking_id}/payments",
        headers={**headers, "Idempotency-Key": key or uuid.uuid4().hex},
        json={"method": method},
    )


async def book_and_pay(
    client: httpx.AsyncClient, headers: dict[str, str], pc_id: uuid.UUID, start: datetime
) -> dict:
    """Create a booking and confirm it through the mock provider. Returns the booking JSON."""
    response = await book(client, headers, pc_id, start)
    assert response.status_code == 201, response.text
    booking = response.json()
    response = await pay(client, headers, booking["id"])
    assert response.status_code == 201, response.text
    response = await client.post(
        f"/v1/payments/mock/{response.json()['id']}/complete", headers=headers
    )
    assert response.status_code == 200, response.text
    response = await client.get(f"/v1/bookings/{booking['id']}", headers=headers)
    assert response.json()["status"] == "confirmed"
    return response.json()
