from datetime import date

from sqlalchemy import select

from app.core import security
from app.domain.iin import build_iin
from app.models import User
from tests.integration.helpers import ADULT_BIRTH, code, iin_for, login, register

PHONE = "+77010000001"
NAMES = {"first_name": "Айдос", "last_name": "Серикулы"}


async def _submit(client, headers, iin, **names):
    return await client.post(
        "/v1/me/identity", headers=headers, json={"iin": iin, **(names or NAMES)}
    )


async def test_identity_verification(client, db, settings):
    headers = await login(client, PHONE)
    iin = iin_for(date(2008, 5, 15))

    response = await _submit(client, headers, iin)
    assert response.status_code == 200
    body = response.json()
    assert body["identity_status"] == "verified"
    assert body["birth_date"] == "2008-05-15"
    assert body["first_name"] == "Айдос"
    assert body["iin_masked"] == "********" + iin[-4:]
    assert iin not in response.text

    # At rest: encrypted, with a keyed hash for uniqueness. Never the plain IIN.
    user = (await db.scalars(select(User).where(User.phone == PHONE))).one()
    assert user.iin_encrypted != iin
    assert iin not in user.iin_encrypted
    assert security.decrypt_iin(settings, user.iin_encrypted) == iin
    assert user.iin_hash == security.hash_iin(settings, iin)
    assert user.iin_hash != iin
    assert user.identity_verified_at is not None


async def test_invalid_iin(client):
    headers = await login(client, PHONE)
    for iin in ["900101300008", "abcdefghijkl", "901301300001"]:
        response = await _submit(client, headers, iin)
        assert response.status_code == 422, iin
        assert code(response) == "INVALID_IIN"
    # Wrong length is caught by request validation.
    response = await _submit(client, headers, "12345")
    assert code(response) == "VALIDATION_ERROR"
    me = (await client.get("/v1/me", headers=headers)).json()
    assert me["identity_status"] == "unverified"


async def test_iin_cannot_be_used_by_two_accounts(client):
    await register(client, PHONE, ADULT_BIRTH, serial=1)
    other = await login(client, "+77010000002")
    response = await _submit(client, other, iin_for(ADULT_BIRTH, serial=1))
    assert response.status_code == 409
    assert code(response) == "IIN_ALREADY_REGISTERED"


async def test_iin_not_found_then_retry(client):
    headers = await login(client, PHONE)
    response = await _submit(client, headers, build_iin(ADULT_BIRTH, "male", 9991))
    assert response.status_code == 422
    assert code(response) == "IDENTITY_NOT_FOUND"
    assert (await client.get("/v1/me", headers=headers)).json()["identity_status"] == "rejected"

    # A rejected user can try again with correct data.
    response = await _submit(client, headers, iin_for(ADULT_BIRTH))
    assert response.status_code == 200
    assert response.json()["identity_status"] == "verified"


async def test_name_mismatch(client):
    headers = await login(client, PHONE)
    response = await _submit(client, headers, build_iin(ADULT_BIRTH, "male", 9992))
    assert response.status_code == 422
    assert code(response) == "IDENTITY_MISMATCH"
    me = (await client.get("/v1/me", headers=headers)).json()
    assert me["identity_status"] == "rejected"
    assert me["birth_date"] is None


async def test_registry_unavailable_leaves_user_unchanged(client):
    headers = await login(client, PHONE)
    response = await _submit(client, headers, build_iin(ADULT_BIRTH, "male", 9993))
    assert response.status_code == 503
    assert code(response) == "IDENTITY_SERVICE_UNAVAILABLE"
    assert (await client.get("/v1/me", headers=headers)).json()["identity_status"] == "unverified"


async def test_cannot_verify_twice(client):
    headers = await register(client, PHONE, ADULT_BIRTH)
    response = await _submit(client, headers, iin_for(date(1999, 9, 9)))
    assert response.status_code == 409
    assert code(response) == "IDENTITY_ALREADY_VERIFIED"
    assert (await client.get("/v1/me", headers=headers)).json()["birth_date"] == "2000-01-15"


async def test_identity_requires_authentication(client):
    response = await client.post("/v1/me/identity", json={"iin": iin_for(ADULT_BIRTH), **NAMES})
    assert response.status_code == 401


async def test_profile_edit_only_before_verification(client):
    headers = await login(client, PHONE)
    response = await client.patch("/v1/me", headers=headers, json={"first_name": "  Dana "})
    assert response.status_code == 200
    assert response.json()["first_name"] == "Dana"

    await _submit(client, headers, iin_for(ADULT_BIRTH))
    response = await client.patch("/v1/me", headers=headers, json={"first_name": "Other"})
    assert response.status_code == 409
    assert code(response) == "IDENTITY_LOCKED"
