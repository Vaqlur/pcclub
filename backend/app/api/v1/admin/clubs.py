"""Admin catalog management. Everything is scoped to the staff member's organization."""

import uuid
from datetime import date

from fastapi import APIRouter, status

from app.api.deps import CurrentStaff, SessionDep
from app.schemas.booking import BookingOut
from app.schemas.club import (
    AdminClubOut,
    AdminPcOut,
    AdminZoneOut,
    ClubCreate,
    ClubUpdate,
    PcCreate,
    PcUpdate,
    ZoneCreate,
    ZoneUpdate,
)
from app.services import catalog

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/clubs")
async def list_clubs(staff: CurrentStaff, session: SessionDep) -> list[AdminClubOut]:
    return [AdminClubOut.model_validate(c) for c in await catalog.admin_list_clubs(session, staff)]


@router.post("/clubs", status_code=status.HTTP_201_CREATED)
async def create_club(data: ClubCreate, staff: CurrentStaff, session: SessionDep) -> AdminClubOut:
    return AdminClubOut.model_validate(await catalog.admin_create_club(session, staff, data))


@router.get("/clubs/{club_id}")
async def get_club(club_id: uuid.UUID, staff: CurrentStaff, session: SessionDep) -> AdminClubOut:
    return AdminClubOut.model_validate(await catalog.admin_get_club(session, staff, club_id))


@router.patch("/clubs/{club_id}")
async def update_club(
    club_id: uuid.UUID, data: ClubUpdate, staff: CurrentStaff, session: SessionDep
) -> AdminClubOut:
    club = await catalog.admin_update_club(session, staff, club_id, data)
    return AdminClubOut.model_validate(club)


@router.get("/clubs/{club_id}/zones")
async def list_zones(
    club_id: uuid.UUID, staff: CurrentStaff, session: SessionDep
) -> list[AdminZoneOut]:
    zones = await catalog.admin_list_zones(session, staff, club_id)
    return [AdminZoneOut.model_validate(z) for z in zones]


@router.post("/clubs/{club_id}/zones", status_code=status.HTTP_201_CREATED)
async def create_zone(
    club_id: uuid.UUID, data: ZoneCreate, staff: CurrentStaff, session: SessionDep
) -> AdminZoneOut:
    return AdminZoneOut.model_validate(
        await catalog.admin_create_zone(session, staff, club_id, data)
    )


@router.patch("/zones/{zone_id}")
async def update_zone(
    zone_id: uuid.UUID, data: ZoneUpdate, staff: CurrentStaff, session: SessionDep
) -> AdminZoneOut:
    return AdminZoneOut.model_validate(
        await catalog.admin_update_zone(session, staff, zone_id, data)
    )


@router.get("/clubs/{club_id}/pcs")
async def list_pcs(
    club_id: uuid.UUID, staff: CurrentStaff, session: SessionDep
) -> list[AdminPcOut]:
    return [
        AdminPcOut.model_validate(p) for p in await catalog.admin_list_pcs(session, staff, club_id)
    ]


@router.post("/clubs/{club_id}/pcs", status_code=status.HTTP_201_CREATED)
async def create_pc(
    club_id: uuid.UUID, data: PcCreate, staff: CurrentStaff, session: SessionDep
) -> AdminPcOut:
    return AdminPcOut.model_validate(await catalog.admin_create_pc(session, staff, club_id, data))


@router.patch("/pcs/{pc_id}")
async def update_pc(
    pc_id: uuid.UUID, data: PcUpdate, staff: CurrentStaff, session: SessionDep
) -> AdminPcOut:
    return AdminPcOut.model_validate(await catalog.admin_update_pc(session, staff, pc_id, data))


@router.get("/clubs/{club_id}/bookings")
async def list_club_bookings(
    club_id: uuid.UUID, date: date, staff: CurrentStaff, session: SessionDep
) -> list[BookingOut]:
    """All bookings of a club that touch the given club-local day."""
    bookings = await catalog.admin_list_bookings(session, staff, club_id, date)
    return [BookingOut.model_validate(b) for b in bookings]
