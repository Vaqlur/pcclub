"""Login: SMS one-time codes for customers, email + password for staff, refresh tokens."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.clock import Clock
from app.core.config import Settings
from app.core.errors import AppError
from app.integrations.sms.base import SmsDeliveryError, SmsSender
from app.models import OtpCode, RefreshToken, StaffUser, User
from app.schemas.auth import TokenPair


def _otp_invalid() -> AppError:
    # One code for "wrong", "expired" and "too many attempts": do not leak which.
    return AppError("OTP_INVALID", "Code is invalid or expired", 400)


async def request_otp(
    session: AsyncSession, settings: Settings, clock: Clock, sms: SmsSender, phone: str
) -> None:
    now = clock.now()
    last = await session.scalar(
        select(OtpCode).where(OtpCode.phone == phone).order_by(OtpCode.created_at.desc()).limit(1)
    )
    if last is not None:
        elapsed = (now - last.created_at).total_seconds()
        if elapsed < settings.otp_resend_cooldown_seconds:
            retry_after = int(settings.otp_resend_cooldown_seconds - elapsed) + 1
            raise AppError(
                "OTP_RATE_LIMITED",
                "A code was sent recently, try again later",
                429,
                {"retry_after_seconds": retry_after},
            )

    code = settings.otp_fixed_code or security.generate_otp_code()
    session.add(
        OtpCode(
            phone=phone,
            code_hash=security.hash_otp(settings, phone, code),
            created_at=now,
            expires_at=now + timedelta(seconds=settings.otp_ttl_seconds),
        )
    )
    await session.flush()
    try:
        await sms.send(phone=phone, text=f"PC Club: код для входа {code}")
    except SmsDeliveryError as exc:
        raise AppError("SMS_DELIVERY_FAILED", "Could not send the code", 502) from exc
    await session.commit()


async def verify_otp(
    session: AsyncSession, settings: Settings, clock: Clock, phone: str, code: str
) -> TokenPair:
    now = clock.now()
    # Only the most recent code for the phone can be used.
    otp = await session.scalar(
        select(OtpCode)
        .where(OtpCode.phone == phone)
        .order_by(OtpCode.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    if (
        otp is None
        or otp.consumed_at is not None
        or otp.expires_at <= now
        or otp.attempts >= settings.otp_max_attempts
    ):
        raise _otp_invalid()

    if not security.constant_time_equals(otp.code_hash, security.hash_otp(settings, phone, code)):
        otp.attempts += 1
        await session.commit()
        raise _otp_invalid()

    otp.consumed_at = now
    user = await _get_or_create_user(session, phone)
    if user.is_blocked:
        await session.commit()  # the code is spent either way
        raise AppError("USER_BLOCKED", "This account is blocked", 403)

    tokens = _issue_tokens(session, settings, now, "customer", user.id)
    await session.commit()
    return tokens


async def _get_or_create_user(session: AsyncSession, phone: str) -> User:
    user = await session.scalar(select(User).where(User.phone == phone))
    if user is not None:
        return user
    try:
        async with session.begin_nested():
            user = User(phone=phone)
            session.add(user)
            await session.flush()
        return user
    except IntegrityError:  # concurrent first login with the same phone
        return (await session.scalars(select(User).where(User.phone == phone))).one()


def _issue_tokens(
    session: AsyncSession,
    settings: Settings,
    now: datetime,
    subject_type: security.SubjectType,
    subject_id: uuid.UUID,
) -> TokenPair:
    refresh_token = security.new_refresh_token()
    session.add(
        RefreshToken(
            subject_type=subject_type,
            subject_id=subject_id,
            token_hash=security.hash_token(refresh_token),
            created_at=now,
            expires_at=now + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    return TokenPair(
        access_token=security.create_access_token(
            settings, subject_id=subject_id, subject_type=subject_type, now=now
        ),
        refresh_token=refresh_token,
        expires_in=settings.access_token_ttl_minutes * 60,
    )


async def refresh_tokens(
    session: AsyncSession, settings: Settings, clock: Clock, refresh_token: str
) -> TokenPair:
    now = clock.now()
    invalid = AppError("INVALID_REFRESH_TOKEN", "Refresh token is invalid or expired", 401)

    stored = await session.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == security.hash_token(refresh_token))
        .with_for_update()
    )
    if stored is None or stored.expires_at <= now:
        raise invalid
    if stored.revoked_at is not None:
        # A rotated token was replayed: assume theft and end every session of this subject.
        await _revoke_all(session, now, stored.subject_type, stored.subject_id)
        await session.commit()
        raise invalid

    if not await _subject_may_login(session, stored.subject_type, stored.subject_id):
        raise invalid

    stored.revoked_at = now
    tokens = _issue_tokens(session, settings, now, stored.subject_type, stored.subject_id)  # type: ignore[arg-type]
    await session.commit()
    return tokens


async def logout(session: AsyncSession, clock: Clock, refresh_token: str) -> None:
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == security.hash_token(refresh_token),
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=clock.now())
    )
    await session.commit()


async def _revoke_all(
    session: AsyncSession, now: datetime, subject_type: str, subject_id: uuid.UUID
) -> None:
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.subject_type == subject_type,
            RefreshToken.subject_id == subject_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )


async def _subject_may_login(
    session: AsyncSession, subject_type: str, subject_id: uuid.UUID
) -> bool:
    if subject_type == "customer":
        user = await session.get(User, subject_id)
        return user is not None and not user.is_blocked
    staff = await session.get(StaffUser, subject_id)
    return staff is not None and staff.is_active


async def staff_login(
    session: AsyncSession, settings: Settings, clock: Clock, email: str, password: str
) -> TokenPair:
    staff = await session.scalar(select(StaffUser).where(StaffUser.email == email.strip().lower()))
    if (
        staff is None
        or not staff.is_active
        or not security.verify_password(staff.password_hash, password)
    ):
        raise AppError("INVALID_CREDENTIALS", "Wrong email or password", 401)
    tokens = _issue_tokens(session, settings, clock.now(), "staff", staff.id)
    await session.commit()
    return tokens
