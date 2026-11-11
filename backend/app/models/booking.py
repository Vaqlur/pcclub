import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, literal_column, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at_column, tz_datetime, uuid_fk_type, uuid_pk
from app.models.club import Pc


class BookingStatus(StrEnum):
    PENDING_PAYMENT = "pending_payment"  # PC is held until hold_expires_at
    CONFIRMED = "confirmed"  # paid
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"  # hold ran out without payment
    NO_SHOW = "no_show"


# Statuses that occupy the PC. Must match the WHERE clause of the exclusion constraints.
ACTIVE_BOOKING_STATUSES = (BookingStatus.PENDING_PAYMENT, BookingStatus.CONFIRMED)

PC_OVERLAP_CONSTRAINT = "ex_bookings_pc_no_overlap"
USER_OVERLAP_CONSTRAINT = "ex_bookings_user_no_overlap"

_ACTIVE_WHERE = "status IN ('pending_payment', 'confirmed')"
_PERIOD = "tstzrange(starts_at, ends_at)"  # half-open [start, end): back-to-back slots are fine


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ends_after_start"),
        CheckConstraint("price_kzt >= 0", name="price_non_negative"),
        CheckConstraint(
            "status IN ('pending_payment', 'confirmed', 'completed', 'cancelled', 'expired',"
            " 'no_show')",
            name="status_valid",
        ),
        CheckConstraint(
            "status <> 'pending_payment' OR hold_expires_at IS NOT NULL", name="pending_has_hold"
        ),
        # Double booking is impossible at the database level, whatever the application does.
        ExcludeConstraint(
            ("pc_id", "="),
            (literal_column(_PERIOD), "&&"),
            where=text(_ACTIVE_WHERE),
            using="gist",
            name=PC_OVERLAP_CONSTRAINT,
        ),
        ExcludeConstraint(
            ("user_id", "="),
            (literal_column(_PERIOD), "&&"),
            where=text(_ACTIVE_WHERE),
            using="gist",
            name=USER_OVERLAP_CONSTRAINT,
        ),
        Index("ix_bookings_club_id_starts_at", "club_id", "starts_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        uuid_fk_type, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    pc_id: Mapped[uuid.UUID] = mapped_column(
        uuid_fk_type, ForeignKey("pcs.id", ondelete="RESTRICT"), nullable=False
    )
    club_id: Mapped[uuid.UUID] = mapped_column(
        uuid_fk_type, ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(tz_datetime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(tz_datetime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    hold_expires_at: Mapped[datetime | None] = mapped_column(tz_datetime)
    price_kzt: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = created_at_column()
    cancelled_at: Mapped[datetime | None] = mapped_column(tz_datetime)

    pc: Mapped[Pc] = relationship(lazy="raise")
