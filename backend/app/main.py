"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, bookings, clubs, me, payments
from app.api.v1.admin import auth as admin_auth
from app.api.v1.admin import clubs as admin_clubs
from app.core.config import Settings, get_settings
from app.core.db import get_engine
from app.core.errors import register_error_handlers

_DEV_CORS_ORIGIN_REGEX = r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"


def _cors_origin_regex(settings: Settings) -> str | None:
    if settings.cors_allow_origin_regex is not None:
        return settings.cors_allow_origin_regex or None
    return _DEV_CORS_ORIGIN_REGEX if settings.environment == "dev" else None


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    if get_engine.cache_info().currsize:
        await get_engine().dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="PC Club API", version="0.1.0", lifespan=_lifespan)
    register_error_handlers(app)

    # Tokens travel in the Authorization header, never in cookies, so no credentials.
    if origin_regex := _cors_origin_regex(settings):
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=origin_regex,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    v1 = APIRouter(prefix="/v1")
    for module in (auth, me, clubs, bookings, admin_auth, admin_clubs):
        v1.include_router(module.router)
    # Mock helpers are registered before /payments/{payment_id} style routes and never in prod.
    if settings.uses_mock_payments and settings.environment != "prod":
        v1.include_router(payments.mock_router)
    v1.include_router(payments.router)
    app.include_router(v1)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
