import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import AwareDatetime

from app.api.deps import ClockDep, SessionDep
from app.core.errors import AppError
from app.schemas.club import ClubOut, PcAvailabilityOut, PcOut, ZoneOut
from app.services import catalog

router = APIRouter(tags=["catalog"])


@router.get("/clubs")
async def list_clubs(session: SessionDep, city: str | None = None) -> list[ClubOut]:
    return [ClubOut.model_validate(c) for c in await catalog.list_clubs(session, city)]


@router.get("/clubs/{club_id}")
async def get_club(club_id: uuid.UUID, session: SessionDep) -> ClubOut:
    return ClubOut.model_validate(await catalog.get_active_club(session, club_id))


@router.get("/clubs/{club_id}/zones")
async def list_zones(club_id: uuid.UUID, session: SessionDep) -> list[ZoneOut]:
    return [ZoneOut.model_validate(z) for z in await catalog.list_zones(session, club_id)]


@router.get("/clubs/{club_id}/pcs")
async def list_pcs(
    club_id: uuid.UUID,
    session: SessionDep,
    clock: ClockDep,
    zone_id: uuid.UUID | None = None,
    from_: Annotated[AwareDatetime | None, Query(alias="from")] = None,
    to: AwareDatetime | None = None,
) -> list[PcOut]:
    """Bookable PCs of a club. With `from` and `to`, each PC carries an `available` flag."""
    if (from_ is None) != (to is None):
        raise AppError("VALIDATION_ERROR", "`from` and `to` must be given together", 422)
    window = (from_, to) if from_ is not None and to is not None else None
    return await catalog.list_pcs(session, clock.now(), club_id, zone_id, window)


@router.get("/pcs/{pc_id}/availability")
async def pc_availability(
    pc_id: uuid.UUID, session: SessionDep, clock: ClockDep, date: date
) -> PcAvailabilityOut:
    """Busy intervals of a PC for one club-local day."""
    return await catalog.pc_availability(session, clock.now(), pc_id, date)
