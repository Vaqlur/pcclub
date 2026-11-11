"""Integration test harness: real PostgreSQL, real migrations, mocked integrations.

Database selection:
  1. TEST_DATABASE_URL (environment or backend/.env). Its database name must contain "test"
     because the public schema is wiped at the start of the run.
  2. Otherwise an embedded throwaway server, if `pip install -e ".[embedded-pg]"` was done.
     That server has no btree_gist, so migration 0002 (overlap constraints) is not applied
     and tests marked `requires_overlap_constraints` are skipped.
  3. Otherwise all integration tests are skipped.

Each test runs inside one outer transaction that is rolled back; application commits become
savepoints. Tests needing real concurrent transactions use the `committed_*` fixtures.
"""

import asyncio
import os
import uuid
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import pytest
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from alembic import command
from app.core import security
from app.core.clock import FixedClock, get_clock
from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.integrations.identity.mock import MockIdentityVerifier
from app.integrations.payments.mock import MockPaymentProvider
from app.integrations.registry import (
    PaymentProviders,
    build_payment_providers,
    get_identity_verifier,
    get_payment_providers,
    get_sms_sender,
)
from app.integrations.sms.mock import MockSmsSender
from app.main import create_app
from app.models import Base, Club, Organization, Pc, StaffRole, StaffUser, Zone
from tests.integration.helpers import NOW

BACKEND_DIR = Path(__file__).resolve().parents[2]
SessionFactory = Callable[[], AsyncSession]


@dataclass(frozen=True)
class Database:
    url: str
    has_overlap_constraints: bool


def alembic_config(url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["url"] = url
    config.attributes["configure_logging"] = False
    return config


async def _reset_schema(url: str) -> bool:
    """Wipe the public schema. Returns whether btree_gist can be installed."""
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            available = await conn.scalar(
                text("SELECT count(*) FROM pg_available_extensions WHERE name = 'btree_gist'")
            )
    finally:
        await engine.dispose()
    return bool(available)


@pytest.fixture(scope="session")
def database(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Database]:
    url = os.environ.get("TEST_DATABASE_URL") or Settings().test_database_url
    server = None
    if url:
        if "test" not in (make_url(url).database or ""):
            pytest.exit(
                "TEST_DATABASE_URL must point to a database whose name contains 'test': "
                "the test run wipes its public schema.",
                returncode=2,
            )
    else:
        try:
            import pixeltable_pgserver
        except ImportError:
            pytest.skip(
                "no test database: set TEST_DATABASE_URL in backend/.env "
                'or install the embedded server with pip install -e ".[embedded-pg]"'
            )
        server = pixeltable_pgserver.get_server(
            tmp_path_factory.mktemp("embedded-pg") / "data", cleanup_mode="delete"
        )
        url = server.get_uri().replace("postgresql://", "postgresql+asyncpg://", 1)

    try:
        has_btree_gist = asyncio.run(_reset_schema(url))
        # Without btree_gist (embedded server) stop before the exclusion-constraint migration.
        command.upgrade(alembic_config(url), "head" if has_btree_gist else "0001")
        yield Database(url=url, has_overlap_constraints=has_btree_gist)
    finally:
        if server is not None:
            server.cleanup()


@pytest.fixture(autouse=True)
def _skip_without_overlap_constraints(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("requires_overlap_constraints"):
        database: Database = request.getfixturevalue("database")
        if not database.has_overlap_constraints:
            pytest.skip(
                "needs the btree_gist exclusion constraints (migration 0002): run against a "
                "real PostgreSQL via TEST_DATABASE_URL; the embedded server does not ship them"
            )


# --- per-test doubles --------------------------------------------------------------------------


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, environment="test", otp_fixed_code="000000")


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(NOW)


@pytest.fixture
def sms() -> MockSmsSender:
    return MockSmsSender()


@pytest.fixture
def providers(settings: Settings) -> PaymentProviders:
    return build_payment_providers(settings)


@pytest.fixture
def mock_provider(providers: PaymentProviders) -> MockPaymentProvider:
    provider = providers.by_name("mock")
    assert isinstance(provider, MockPaymentProvider)
    return provider


def _build_app(
    settings: Settings,
    session_factory: SessionFactory,
    clock: FixedClock,
    sms: MockSmsSender,
    providers: PaymentProviders,
) -> FastAPI:
    app = create_app(settings)
    verifier = MockIdentityVerifier()

    async def _session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides.update(
        {
            get_settings: lambda: settings,
            get_session: _session,
            get_clock: lambda: clock,
            get_sms_sender: lambda: sms,
            get_payment_providers: lambda: providers,
            get_identity_verifier: lambda: verifier,
        }
    )
    return app


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


# --- transactional (default) fixtures ----------------------------------------------------------


@pytest.fixture
async def connection(database: Database) -> AsyncIterator[AsyncConnection]:
    engine = create_async_engine(database.url, poolclass=NullPool)
    async with engine.connect() as conn:
        transaction = await conn.begin()
        try:
            yield conn
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.fixture
def session_factory(connection: AsyncConnection) -> SessionFactory:
    return async_sessionmaker(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )


@pytest.fixture
async def db(session_factory: SessionFactory) -> AsyncIterator[AsyncSession]:
    """Session for seeding and inspecting data directly. Use `populate_existing` or
    `refresh` when re-reading rows the API has changed."""
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(
    settings: Settings,
    session_factory: SessionFactory,
    clock: FixedClock,
    sms: MockSmsSender,
    providers: PaymentProviders,
) -> AsyncIterator[httpx.AsyncClient]:
    async with _client(_build_app(settings, session_factory, clock, sms, providers)) as client:
        yield client


# --- committed fixtures (real concurrent transactions) -----------------------------------------


@pytest.fixture
async def committed_session_factory(database: Database) -> AsyncIterator[SessionFactory]:
    engine = create_async_engine(database.url, pool_size=10)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
        async with engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE TABLE {tables} CASCADE"))
        await engine.dispose()


@pytest.fixture
async def committed_client(
    settings: Settings,
    committed_session_factory: SessionFactory,
    clock: FixedClock,
    sms: MockSmsSender,
    providers: PaymentProviders,
) -> AsyncIterator[httpx.AsyncClient]:
    app = _build_app(settings, committed_session_factory, clock, sms, providers)
    async with _client(app) as client:
        yield client


# --- seed data ---------------------------------------------------------------------------------


@dataclass
class World:
    """One organization with a 24/7 Almaty club: 3 Standard PCs (1000 ₸/h), 1 VIP (1500 ₸/h)."""

    org_id: uuid.UUID
    club_id: uuid.UUID
    standard_zone_id: uuid.UUID
    vip_zone_id: uuid.UUID
    pc_ids: list[uuid.UUID] = field(default_factory=list)
    vip_pc_id: uuid.UUID | None = None
    staff_email: str = "owner@example.com"
    staff_password: str = "correct-horse-battery"


async def seed_world(session: AsyncSession, *, email: str = "owner@example.com") -> World:
    org = Organization(name=f"Org of {email}")
    session.add(org)
    await session.flush()
    club = Club(organization_id=org.id, name="Arena", city="Almaty", address="Abay Ave 1")
    session.add(club)
    await session.flush()
    standard = Zone(club_id=club.id, name="Standard", price_per_hour_kzt=1000)
    vip = Zone(club_id=club.id, name="VIP", price_per_hour_kzt=1500)
    session.add_all([standard, vip])
    await session.flush()
    pcs = [Pc(club_id=club.id, zone_id=standard.id, label=f"S-{n:02d}") for n in (1, 2, 3)]
    vip_pc = Pc(club_id=club.id, zone_id=vip.id, label="VIP-01", specs={"gpu": "RTX 5080"})
    session.add_all([*pcs, vip_pc])
    world = World(
        org_id=org.id,
        club_id=club.id,
        standard_zone_id=standard.id,
        vip_zone_id=vip.id,
        staff_email=email,
    )
    session.add(
        StaffUser(
            organization_id=org.id,
            email=email,
            password_hash=security.hash_password(world.staff_password),
            role=StaffRole.OWNER,
        )
    )
    await session.commit()
    world.pc_ids = [pc.id for pc in pcs]
    world.vip_pc_id = vip_pc.id
    return world


@pytest.fixture
async def world(db: AsyncSession) -> World:
    return await seed_world(db)


@pytest.fixture
async def committed_world(committed_session_factory: SessionFactory) -> World:
    async with committed_session_factory() as session:
        return await seed_world(session)
