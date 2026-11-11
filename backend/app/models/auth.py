import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, tz_datetime, uuid_fk_type, uuid_pk


class OtpCode(Base):
    """One-time SMS login code. Only a keyed hash of the code is stored."""

    __tablename__ = "otp_codes"
    __table_args__ = (Index("ix_otp_codes_phone_created_at", "phone", "created_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    phone: Mapped[str] = mapped_column(String(16), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(tz_datetime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(tz_datetime, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(tz_datetime)


class RefreshToken(Base):
    """Refresh token (hashed), rotated on every use. Subject is a customer or a staff user."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        CheckConstraint("subject_type IN ('customer', 'staff')", name="subject_type_valid"),
        Index("ix_refresh_tokens_subject", "subject_type", "subject_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(uuid_fk_type, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(tz_datetime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(tz_datetime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(tz_datetime)
