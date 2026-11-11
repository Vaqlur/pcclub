import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, uuid_fk_type, uuid_pk


class StaffRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"


class Organization(Base):
    """Tenant: a club owner (company) that operates one or more clubs."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = created_at_column()


class StaffUser(Base):
    """Admin-panel account, always scoped to one organization."""

    __tablename__ = "staff_users"
    __table_args__ = (CheckConstraint("role IN ('owner', 'admin')", name="role_valid"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        uuid_fk_type, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=StaffRole.ADMIN)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = created_at_column()
