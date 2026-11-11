"""CORS wiring of the app factory. No database: only /health and preflight are touched."""

import httpx
import pytest

from app.core.config import Settings
from app.main import create_app

WEB_PREVIEW = "http://localhost:8081"


async def _get_health(settings: Settings, origin: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=create_app(settings))
    async with httpx.AsyncClient(transport=transport, base_url="http://api") as client:
        return await client.get("/health", headers={"Origin": origin})


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


@pytest.mark.parametrize("origin", [WEB_PREVIEW, "http://127.0.0.1:19006", "http://localhost"])
async def test_dev_allows_localhost_origins(origin: str) -> None:
    response = await _get_health(_settings(environment="dev"), origin)
    assert response.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize(
    "origin",
    ["https://evil.example", "http://localhost.evil.example", "https://localhost:8081"],
)
async def test_dev_rejects_other_origins(origin: str) -> None:
    response = await _get_health(_settings(environment="dev"), origin)
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("environment", ["test", "prod"])
async def test_cors_is_off_outside_dev_by_default(environment: str) -> None:
    secrets = (
        {"jwt_secret": "x" * 48, "iin_hash_pepper": "y" * 48, "iin_encryption_key": "z" * 44}
        if environment == "prod"
        else {}
    )
    response = await _get_health(_settings(environment=environment, **secrets), WEB_PREVIEW)
    assert "access-control-allow-origin" not in response.headers


async def test_explicit_regex_overrides_the_dev_default() -> None:
    settings = _settings(environment="dev", cors_allow_origin_regex=r"^https://admin\.example\.kz$")
    allowed = await _get_health(settings, "https://admin.example.kz")
    assert allowed.headers["access-control-allow-origin"] == "https://admin.example.kz"
    blocked = await _get_health(settings, WEB_PREVIEW)
    assert "access-control-allow-origin" not in blocked.headers


async def test_empty_regex_disables_cors_in_dev() -> None:
    response = await _get_health(
        _settings(environment="dev", cors_allow_origin_regex=""), WEB_PREVIEW
    )
    assert "access-control-allow-origin" not in response.headers


async def test_preflight_allows_the_headers_the_app_sends() -> None:
    transport = httpx.ASGITransport(app=create_app(_settings(environment="dev")))
    async with httpx.AsyncClient(transport=transport, base_url="http://api") as client:
        response = await client.options(
            "/v1/bookings",
            headers={
                "Origin": WEB_PREVIEW,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == WEB_PREVIEW
