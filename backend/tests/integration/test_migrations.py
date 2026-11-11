"""The migrations must produce exactly the schema the ORM models describe."""

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text

from app.models import Base


async def test_models_match_migrated_schema(connection):
    def diff(sync_connection):
        context = MigrationContext.configure(sync_connection, opts={"compare_type": True})
        return compare_metadata(context, Base.metadata)

    assert await connection.run_sync(diff) == []


@pytest.mark.requires_overlap_constraints
async def test_overlap_constraints_exist(connection):
    rows = await connection.execute(
        text(
            "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid = 'bookings'::regclass AND contype = 'x' ORDER BY conname"
        )
    )
    constraints = dict(rows.all())
    assert set(constraints) == {"ex_bookings_pc_no_overlap", "ex_bookings_user_no_overlap"}
    for definition in constraints.values():
        assert "tstzrange(starts_at, ends_at) WITH &&" in definition
        assert "pending_payment" in definition and "confirmed" in definition
