"""Shared column helpers for ORM models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

__all__ = ["Base", "created_at_column", "tz_datetime", "uuid_fk_type", "uuid_pk"]

tz_datetime = DateTime(timezone=True)
uuid_fk_type = UUID(as_uuid=True)


def uuid_pk() -> Mapped[uuid.UUID]:
    """Time-ordered UUIDv7 primary key, generated in the application."""
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid7)


def created_at_column() -> Mapped[datetime]:
    """Audit timestamp only. Business logic uses explicit timestamps from the Clock."""
    return mapped_column(tz_datetime, server_default=func.now(), nullable=False)
