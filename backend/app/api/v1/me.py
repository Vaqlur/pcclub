from fastapi import APIRouter

from app.api.deps import ClockDep, CurrentUser, IdentityVerifierDep, SessionDep, SettingsDep
from app.schemas.user import IdentitySubmit, UserOut, UserUpdate
from app.services import identity as identity_service

router = APIRouter(prefix="/me", tags=["profile"])


@router.get("")
async def get_me(user: CurrentUser, settings: SettingsDep) -> UserOut:
    return identity_service.user_out(settings, user)


@router.patch("")
async def update_me(
    data: UserUpdate, user: CurrentUser, session: SessionDep, settings: SettingsDep
) -> UserOut:
    user = await identity_service.update_profile(session, user, data)
    return identity_service.user_out(settings, user)


@router.post("/identity")
async def submit_identity(
    data: IdentitySubmit,
    user: CurrentUser,
    session: SessionDep,
    settings: SettingsDep,
    clock: ClockDep,
    verifier: IdentityVerifierDep,
) -> UserOut:
    """Verify the IIN. Required before booking: the birth date drives the age rule."""
    user = await identity_service.submit_identity(session, settings, clock, verifier, user, data)
    return identity_service.user_out(settings, user)
