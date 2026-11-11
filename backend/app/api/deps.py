"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.clock import Clock, get_clock
from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.core.errors import AppError
from app.integrations.identity.base import IdentityVerifier
from app.integrations.registry import (
    PaymentProviders,
    get_identity_verifier,
    get_payment_providers,
    get_sms_sender,
)
from app.integrations.sms.base import SmsSender
from app.models import StaffUser, User

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
ClockDep = Annotated[Clock, Depends(get_clock)]
IdentityVerifierDep = Annotated[IdentityVerifier, Depends(get_identity_verifier)]
SmsSenderDep = Annotated[SmsSender, Depends(get_sms_sender)]
PaymentProvidersDep = Annotated[PaymentProviders, Depends(get_payment_providers)]

_bearer = HTTPBearer(auto_error=False, description="Access token from /v1/auth or /v1/admin/auth")


def _claims(
    credentials: HTTPAuthorizationCredentials | None,
    settings: Settings,
    clock: Clock,
    expected: security.SubjectType,
) -> security.TokenClaims:
    unauthorized = AppError("UNAUTHORIZED", "Missing or invalid access token", 401)
    if credentials is None:
        raise unauthorized
    try:
        claims = security.decode_access_token(settings, credentials.credentials, now=clock.now())
    except security.InvalidToken as exc:
        raise unauthorized from exc
    if claims.subject_type != expected:
        raise unauthorized
    return claims


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: SessionDep,
    settings: SettingsDep,
    clock: ClockDep,
) -> User:
    claims = _claims(credentials, settings, clock, "customer")
    user = await session.get(User, claims.subject_id)
    if user is None:
        raise AppError("UNAUTHORIZED", "Missing or invalid access token", 401)
    if user.is_blocked:
        raise AppError("USER_BLOCKED", "This account is blocked", 403)
    return user


async def get_current_staff(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: SessionDep,
    settings: SettingsDep,
    clock: ClockDep,
) -> StaffUser:
    claims = _claims(credentials, settings, clock, "staff")
    staff = await session.get(StaffUser, claims.subject_id)
    if staff is None or not staff.is_active:
        raise AppError("UNAUTHORIZED", "Missing or invalid access token", 401)
    return staff


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentStaff = Annotated[StaffUser, Depends(get_current_staff)]
