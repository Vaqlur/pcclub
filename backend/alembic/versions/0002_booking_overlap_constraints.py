"""booking overlap constraints

Makes double booking impossible at the database level: no two active bookings
(pending_payment / confirmed) may overlap on the same PC, and a user may not hold two
overlapping active bookings. tstzrange is half-open, so back-to-back slots are allowed.

Requires the btree_gist extension (ships with PostgreSQL contrib; trusted since PG 13, so the
database owner can create it).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACTIVE = "status IN ('pending_payment', 'confirmed')"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        "ALTER TABLE bookings ADD CONSTRAINT ex_bookings_pc_no_overlap "
        "EXCLUDE USING gist (pc_id WITH =, tstzrange(starts_at, ends_at) WITH &&) "
        f"WHERE ({_ACTIVE})"
    )
    op.execute(
        "ALTER TABLE bookings ADD CONSTRAINT ex_bookings_user_no_overlap "
        "EXCLUDE USING gist (user_id WITH =, tstzrange(starts_at, ends_at) WITH &&) "
        f"WHERE ({_ACTIVE})"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE bookings DROP CONSTRAINT ex_bookings_user_no_overlap")
    op.execute("ALTER TABLE bookings DROP CONSTRAINT ex_bookings_pc_no_overlap")
    # The extension is left installed: other objects may depend on it.
