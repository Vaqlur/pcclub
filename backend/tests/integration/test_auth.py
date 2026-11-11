import uuid

from sqlalchemy import select, update

from app.core import security
from app.models import User
from tests.integration.helpers import OTP_CODE, code, login

PHONE = "+77071234567"


async def _request(client, phone=PHONE):
    return await client.post("/v1/auth/otp/request", json={"phone": phone})


async def _verify(client, otp=OTP_CODE, phone=PHONE):
    return await client.post("/v1/auth/otp/verify", json={"phone": phone, "code": otp})


async def test_first_login_creates_unverified_user(client, sms):
    assert (await _request(client)).status_code == 204
    assert sms.sent[-1].phone == PHONE
    assert OTP_CODE in sms.sent[-1].text

    response = await _verify(client)
    assert response.status_code == 200
    tokens = response.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] == 30 * 60

    me = await client.get("/v1/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json() == {
        "id": me.json()["id"],
        "phone": PHONE,
        "first_name": None,
        "last_name": None,
        "birth_date": None,
        "identity_status": "unverified",
        "iin_masked": None,
    }


async def test_phone_formats_map_to_one_account(client, clock, db):
    await login(client, "8 (707) 123-45-67")
    clock.advance(seconds=61)
    await login(client, "+7 707 123 45 67")
    clock.advance(seconds=61)
    await login(client, "77071234567")
    phones = list(await db.scalars(select(User.phone)))
    assert phones == [PHONE]


async def test_invalid_phone_is_rejected(client):
    for phone in ["12345", "+1 202 555 0100", "+7707123456", "phone"]:
        response = await _request(client, phone)
        assert response.status_code == 422, phone
        assert code(response) == "VALIDATION_ERROR"


async def test_wrong_code_is_rejected(client):
    await _request(client)
    response = await _verify(client, "111111")
    assert response.status_code == 400
    assert code(response) == "OTP_INVALID"
    # The right code still works after a single mistake.
    assert (await _verify(client)).status_code == 200


async def test_code_is_locked_after_too_many_attempts(client):
    await _request(client)
    for _ in range(5):
        assert code(await _verify(client, "111111")) == "OTP_INVALID"
    assert code(await _verify(client)) == "OTP_INVALID"


async def test_code_expires(client, clock):
    await _request(client)
    clock.advance(seconds=301)
    assert code(await _verify(client)) == "OTP_INVALID"


async def test_code_is_single_use(client):
    await _request(client)
    assert (await _verify(client)).status_code == 200
    assert code(await _verify(client)) == "OTP_INVALID"


async def test_verify_without_request_fails(client):
    assert code(await _verify(client)) == "OTP_INVALID"


async def test_resend_cooldown(client, clock):
    assert (await _request(client)).status_code == 204
    response = await _request(client)
    assert response.status_code == 429
    assert code(response) == "OTP_RATE_LIMITED"
    assert 0 < response.json()["error"]["details"]["retry_after_seconds"] <= 61
    # Another phone is not affected.
    assert (await _request(client, "+77070000002")).status_code == 204
    clock.advance(seconds=60)
    assert (await _request(client)).status_code == 204


async def test_only_latest_code_is_valid(client, clock, settings, sms):
    settings.otp_fixed_code = None  # random codes
    await _request(client)
    first = sms.sent[-1].text.split()[-1]
    clock.advance(seconds=61)
    await _request(client)
    second = sms.sent[-1].text.split()[-1]
    if first != second:
        assert code(await _verify(client, first)) == "OTP_INVALID"
    assert (await _verify(client, second)).status_code == 200


async def test_refresh_rotates_tokens(client):
    await _request(client)
    tokens = (await _verify(client)).json()

    response = await client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200
    rotated = response.json()
    assert rotated["refresh_token"] != tokens["refresh_token"]
    me = await client.get("/v1/me", headers={"Authorization": f"Bearer {rotated['access_token']}"})
    assert me.status_code == 200


async def test_replayed_refresh_token_revokes_the_whole_chain(client):
    await _request(client)
    tokens = (await _verify(client)).json()
    rotated = (
        await client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    ).json()

    replay = await client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
    assert code(replay) == "INVALID_REFRESH_TOKEN"
    # The token issued by the legitimate rotation is revoked as well.
    after = await client.post("/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]})
    assert after.status_code == 401


async def test_refresh_token_expires(client, clock):
    await _request(client)
    tokens = (await _verify(client)).json()
    clock.advance(days=31)
    response = await client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 401


async def test_unknown_refresh_token(client):
    response = await client.post("/v1/auth/refresh", json={"refresh_token": "x" * 40})
    assert response.status_code == 401


async def test_logout_revokes_refresh_token(client):
    await _request(client)
    tokens = (await _verify(client)).json()
    body = {"refresh_token": tokens["refresh_token"]}
    assert (await client.post("/v1/auth/logout", json=body)).status_code == 204
    assert (await client.post("/v1/auth/refresh", json=body)).status_code == 401
    # Logging out twice is harmless.
    assert (await client.post("/v1/auth/logout", json=body)).status_code == 204


async def test_access_token_expires(client, clock):
    headers = await login(client, PHONE)
    assert (await client.get("/v1/me", headers=headers)).status_code == 200
    clock.advance(minutes=30)
    response = await client.get("/v1/me", headers=headers)
    assert response.status_code == 401
    assert code(response) == "UNAUTHORIZED"


async def test_missing_or_garbage_token(client):
    assert (await client.get("/v1/me")).status_code == 401
    for value in ["Bearer not-a-jwt", "Bearer ", "Basic abc"]:
        response = await client.get("/v1/me", headers={"Authorization": value})
        assert response.status_code == 401, value
        assert code(response) == "UNAUTHORIZED"


async def test_token_signed_with_another_secret_is_rejected(client, settings, clock):
    headers = await login(client, PHONE)
    me = (await client.get("/v1/me", headers=headers)).json()
    forged_settings = settings.model_copy(update={"jwt_secret": "another-secret-" + "x" * 32})
    forged = security.create_access_token(
        forged_settings, subject_id=uuid.UUID(me["id"]), subject_type="customer", now=clock.now()
    )
    response = await client.get("/v1/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


async def test_blocked_user(client, clock, db):
    headers = await login(client, PHONE)
    await db.execute(update(User).where(User.phone == PHONE).values(is_blocked=True))
    await db.commit()

    response = await client.get("/v1/me", headers=headers)
    assert response.status_code == 403
    assert code(response) == "USER_BLOCKED"

    clock.advance(seconds=61)
    await _request(client)
    response = await _verify(client)
    assert response.status_code == 403
    assert code(response) == "USER_BLOCKED"
