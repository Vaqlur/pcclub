from fastapi import APIRouter

from app.api.deps import ClockDep, SessionDep, SettingsDep
from app.schemas.auth import StaffLogin, TokenPair
from app.services import auth as auth_service

router = APIRouter(prefix="/admin/auth", tags=["admin"])


@router.post("/login")
async def staff_login(
    data: StaffLogin, session: SessionDep, settings: SettingsDep, clock: ClockDep
) -> TokenPair:
    """Staff login for the admin panel. Refresh with POST /v1/auth/refresh."""
    return await auth_service.staff_login(session, settings, clock, data.email, data.password)
