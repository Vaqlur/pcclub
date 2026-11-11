"""initial schema

Tables, checks and indexes. The booking overlap (exclusion) constraints live in 0002
because they need the btree_gist extension.

Revision ID: 0001
Revises:
Create Date: 2026-11-11 21:44:32.550895
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
    )
    op.create_table(
        "otp_codes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("phone", sa.String(length=16), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_otp_codes")),
    )
    op.create_index(
        "ix_otp_codes_phone_created_at", "otp_codes", ["phone", "created_at"], unique=False
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("subject_type", sa.String(length=20), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "subject_type IN ('customer', 'staff')",
            name=op.f("ck_refresh_tokens_subject_type_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(
        "ix_refresh_tokens_subject", "refresh_tokens", ["subject_type", "subject_id"], unique=False
    )
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("phone", sa.String(length=16), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("iin_encrypted", sa.Text(), nullable=True),
        sa.Column("iin_hash", sa.String(length=64), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("identity_status", sa.String(length=20), nullable=False),
        sa.Column("identity_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_blocked", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "identity_status <> 'verified' OR (birth_date IS NOT NULL AND iin_hash IS NOT NULL)",
            name=op.f("ck_users_verified_has_identity"),
        ),
        sa.CheckConstraint(
            "identity_status IN ('unverified', 'verified', 'rejected')",
            name=op.f("ck_users_identity_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("iin_hash", name=op.f("uq_users_iin_hash")),
        sa.UniqueConstraint("phone", name=op.f("uq_users_phone")),
    )
    op.create_table(
        "clubs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("address", sa.String(length=300), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("opens_at", sa.Time(), nullable=True),
        sa.Column("closes_at", sa.Time(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(opens_at IS NULL) = (closes_at IS NULL)",
            name=op.f("ck_clubs_opening_hours_both_or_none"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_clubs_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clubs")),
    )
    op.create_index(op.f("ix_clubs_city"), "clubs", ["city"], unique=False)
    op.create_index(op.f("ix_clubs_organization_id"), "clubs", ["organization_id"], unique=False)
    op.create_table(
        "staff_users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('owner', 'admin')", name=op.f("ck_staff_users_role_valid")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_staff_users_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_staff_users")),
        sa.UniqueConstraint("email", name=op.f("uq_staff_users_email")),
    )
    op.create_index(
        op.f("ix_staff_users_organization_id"), "staff_users", ["organization_id"], unique=False
    )
    op.create_table(
        "zones",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("club_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("price_per_hour_kzt", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("price_per_hour_kzt >= 0", name=op.f("ck_zones_price_non_negative")),
        sa.ForeignKeyConstraint(
            ["club_id"], ["clubs.id"], name=op.f("fk_zones_club_id_clubs"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_zones")),
        sa.UniqueConstraint("club_id", "name", name=op.f("uq_zones_club_id_name")),
    )
    op.create_index(op.f("ix_zones_club_id"), "zones", ["club_id"], unique=False)
    op.create_table(
        "pcs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("club_id", sa.UUID(), nullable=False),
        sa.Column("zone_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(length=50), nullable=False),
        sa.Column("specs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'maintenance', 'retired')", name=op.f("ck_pcs_status_valid")
        ),
        sa.ForeignKeyConstraint(
            ["club_id"], ["clubs.id"], name=op.f("fk_pcs_club_id_clubs"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["zone_id"], ["zones.id"], name=op.f("fk_pcs_zone_id_zones"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pcs")),
        sa.UniqueConstraint("club_id", "label", name=op.f("uq_pcs_club_id_label")),
    )
    op.create_index(op.f("ix_pcs_club_id"), "pcs", ["club_id"], unique=False)
    op.create_index(op.f("ix_pcs_zone_id"), "pcs", ["zone_id"], unique=False)
    op.create_table(
        "bookings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("pc_id", sa.UUID(), nullable=False),
        sa.Column("club_id", sa.UUID(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("hold_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("price_kzt", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status <> 'pending_payment' OR hold_expires_at IS NOT NULL",
            name=op.f("ck_bookings_pending_has_hold"),
        ),
        sa.CheckConstraint(
            "status IN ('pending_payment', 'confirmed', 'completed', 'cancelled', 'expired', 'no_show')",
            name=op.f("ck_bookings_status_valid"),
        ),
        sa.CheckConstraint("ends_at > starts_at", name=op.f("ck_bookings_ends_after_start")),
        sa.CheckConstraint("price_kzt >= 0", name=op.f("ck_bookings_price_non_negative")),
        sa.ForeignKeyConstraint(
            ["club_id"], ["clubs.id"], name=op.f("fk_bookings_club_id_clubs"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["pc_id"], ["pcs.id"], name=op.f("fk_bookings_pc_id_pcs"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_bookings_user_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bookings")),
    )
    op.create_index(
        "ix_bookings_club_id_starts_at", "bookings", ["club_id", "starts_at"], unique=False
    )
    op.create_index(op.f("ix_bookings_user_id"), "bookings", ["user_id"], unique=False)
    op.create_table(
        "payments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("booking_id", sa.UUID(), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_payment_id", sa.String(length=200), nullable=True),
        sa.Column("amount_kzt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("redirect_url", sa.String(length=1000), nullable=True),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("method IN ('card', 'kaspi')", name=op.f("ck_payments_method_valid")),
        sa.CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'refunded')",
            name=op.f("ck_payments_status_valid"),
        ),
        sa.CheckConstraint("amount_kzt >= 0", name=op.f("ck_payments_amount_non_negative")),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
            name=op.f("fk_payments_booking_id_bookings"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payments")),
        sa.UniqueConstraint(
            "booking_id", "idempotency_key", name=op.f("uq_payments_booking_id_idempotency_key")
        ),
        sa.UniqueConstraint(
            "provider", "provider_payment_id", name=op.f("uq_payments_provider_provider_payment_id")
        ),
    )
    op.create_index(op.f("ix_payments_booking_id"), "payments", ["booking_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_payments_booking_id"), table_name="payments")
    op.drop_table("payments")
    op.drop_index(op.f("ix_bookings_user_id"), table_name="bookings")
    op.drop_index("ix_bookings_club_id_starts_at", table_name="bookings")
    op.drop_table("bookings")
    op.drop_index(op.f("ix_pcs_zone_id"), table_name="pcs")
    op.drop_index(op.f("ix_pcs_club_id"), table_name="pcs")
    op.drop_table("pcs")
    op.drop_index(op.f("ix_zones_club_id"), table_name="zones")
    op.drop_table("zones")
    op.drop_index(op.f("ix_staff_users_organization_id"), table_name="staff_users")
    op.drop_table("staff_users")
    op.drop_index(op.f("ix_clubs_organization_id"), table_name="clubs")
    op.drop_index(op.f("ix_clubs_city"), table_name="clubs")
    op.drop_table("clubs")
    op.drop_table("users")
    op.drop_index("ix_refresh_tokens_subject", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("ix_otp_codes_phone_created_at", table_name="otp_codes")
    op.drop_table("otp_codes")
    op.drop_table("organizations")
