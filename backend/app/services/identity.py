"""Identity: IIN submission and verification. The verified birth date drives the age rule."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.clock import Clock
from app.core.config import Settings
from app.core.errors import AppError
from app.domain.iin import InvalidIIN, parse_iin
from app.integrations.identity.base import (
    IdentityCheckStatus,
    IdentityVerifier,
    IdentityVerifierUnavailable,
)
from app.models import IdentityStatus, User
from app.schemas.user import IdentitySubmit, UserOut, UserUpdate


def user_out(settings: Settings, user: User) -> UserOut:
    iin_masked = None
    if user.iin_encrypted:
        iin_masked = security.mask_iin(security.decrypt_iin(settings, user.iin_encrypted))
    return UserOut(
        id=user.id,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        birth_date=user.birth_date,
        identity_status=user.identity_status,
        iin_masked=iin_masked,
    )


async def update_profile(session: AsyncSession, user: User, data: UserUpdate) -> User:
    if user.identity_status == IdentityStatus.VERIFIED:
        # After verification the name is the one confirmed against the registry.
        raise AppError("IDENTITY_LOCKED", "A verified profile cannot be edited", 409)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await session.commit()
    return user


async def submit_identity(
    session: AsyncSession,
    settings: Settings,
    clock: Clock,
    verifier: IdentityVerifier,
    user: User,
    data: IdentitySubmit,
) -> User:
    if user.identity_status == IdentityStatus.VERIFIED:
        raise AppError("IDENTITY_ALREADY_VERIFIED", "Identity is already verified", 409)

    try:
        info = parse_iin(data.iin)
    except InvalidIIN as exc:
        raise AppError("INVALID_IIN", "IIN is not valid", 422) from exc

    iin_hash = security.hash_iin(settings, data.iin)
    taken = AppError("IIN_ALREADY_REGISTERED", "This IIN belongs to another account", 409)
    owner_id = await session.scalar(select(User.id).where(User.iin_hash == iin_hash))
    if owner_id is not None and owner_id != user.id:
        raise taken

    try:
        result = await verifier.verify(
            iin=data.iin, first_name=data.first_name, last_name=data.last_name
        )
    except IdentityVerifierUnavailable as exc:
        raise AppError(
            "IDENTITY_SERVICE_UNAVAILABLE", "Verification is temporarily unavailable", 503
        ) from exc

    if result.status == IdentityCheckStatus.NOT_FOUND:
        await _mark_rejected(session, user)
        raise AppError("IDENTITY_NOT_FOUND", "IIN was not found in the registry", 422)
    if result.status == IdentityCheckStatus.NAME_MISMATCH or result.birth_date != info.birth_date:
        # A registry birth date that disagrees with the IIN is treated as a mismatch too.
        await _mark_rejected(session, user)
        raise AppError("IDENTITY_MISMATCH", "IIN does not match the provided data", 422)

    user.first_name = result.first_name or data.first_name
    user.last_name = result.last_name or data.last_name
    user.iin_encrypted = security.encrypt_iin(settings, data.iin)
    user.iin_hash = iin_hash
    user.birth_date = result.birth_date
    user.identity_status = IdentityStatus.VERIFIED
    user.identity_verified_at = clock.now()
    try:
        await session.commit()
    except IntegrityError as exc:  # the same IIN was registered concurrently
        await session.rollback()
        raise taken from exc
    return user


async def _mark_rejected(session: AsyncSession, user: User) -> None:
    user.identity_status = IdentityStatus.REJECTED
    await session.commit()
