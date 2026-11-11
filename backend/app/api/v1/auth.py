from fastapi import APIRouter, status

from app.api.deps import ClockDep, SessionDep, SettingsDep, SmsSenderDep
from app.schemas.auth import OtpRequest, OtpVerify, RefreshRequest, TokenPair
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/otp/request", status_code=status.HTTP_204_NO_CONTENT)
async def request_otp(
    data: OtpRequest, session: SessionDep, settings: SettingsDep, clock: ClockDep, sms: SmsSenderDep
) -> None:
    """Send a one-time login code by SMS."""
    await auth_service.request_otp(session, settings, clock, sms, data.phone)


@router.post("/otp/verify")
async def verify_otp(
    data: OtpVerify, session: SessionDep, settings: SettingsDep, clock: ClockDep
) -> TokenPair:
    """Exchange the SMS code for tokens. The account is created on first login."""
    return await auth_service.verify_otp(session, settings, clock, data.phone, data.code)


@router.post("/refresh")
async def refresh(
    data: RefreshRequest, session: SessionDep, settings: SettingsDep, clock: ClockDep
) -> TokenPair:
    """Rotate a refresh token (customers and staff)."""
    return await auth_service.refresh_tokens(session, settings, clock, data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshRequest, session: SessionDep, clock: ClockDep) -> None:
    await auth_service.logout(session, clock, data.refresh_token)
