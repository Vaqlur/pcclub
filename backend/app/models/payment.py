import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, tz_datetime, uuid_fk_type, uuid_pk


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(Base):
    """One payment attempt for a booking. A booking may have several attempts."""

    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("booking_id", "idempotency_key"),
        UniqueConstraint("provider", "provider_payment_id"),
        CheckConstraint("method IN ('card', 'kaspi')", name="method_valid"),
        CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'refunded')", name="status_valid"
        ),
        CheckConstraint("amount_kzt >= 0", name="amount_non_negative"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    booking_id: Mapped[uuid.UUID] = mapped_column(
        uuid_fk_type, ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_payment_id: Mapped[str | None] = mapped_column(String(200))
    amount_kzt: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=PaymentStatus.PENDING)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    redirect_url: Mapped[str | None] = mapped_column(String(1000))
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime | None] = mapped_column(tz_datetime)
