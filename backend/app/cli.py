"""Operator commands.

python -m app.cli create-owner --org "My Club LLP" --email owner@example.com
python -m app.cli seed-demo
"""

import argparse
import asyncio
import getpass
import sys
from datetime import time

from sqlalchemy import select

from app.core import security
from app.core.config import get_settings
from app.core.db import get_engine, get_sessionmaker
from app.models import Club, Organization, Pc, StaffRole, StaffUser, Zone


async def create_owner(org_name: str, email: str, password: str) -> None:
    email = email.strip().lower()
    async with get_sessionmaker()() as session:
        if await session.scalar(select(StaffUser.id).where(StaffUser.email == email)):
            sys.exit(f"A staff user with email {email} already exists")
        org = Organization(name=org_name)
        session.add(org)
        await session.flush()
        session.add(
            StaffUser(
                organization_id=org.id,
                email=email,
                password_hash=security.hash_password(password),
                role=StaffRole.OWNER,
            )
        )
        await session.commit()
    print(f"Created organization '{org_name}' with owner {email}")


async def seed_demo() -> None:
    """A demo club with two zones and ten PCs, for local development only."""
    if get_settings().environment == "prod":
        sys.exit("seed-demo is not available in production")
    async with get_sessionmaker()() as session:
        org = Organization(name="Demo Org")
        session.add(org)
        await session.flush()
        club = Club(
            organization_id=org.id,
            name="Demo Arena",
            city="Almaty",
            address="Abay Ave 1",
            opens_at=None,
            closes_at=None,
        )
        daytime = Club(
            organization_id=org.id,
            name="Demo Daytime",
            city="Astana",
            address="Mangilik El 1",
            opens_at=time(10),
            closes_at=time(23),
        )
        session.add_all([club, daytime])
        await session.flush()
        standard = Zone(club_id=club.id, name="Standard", price_per_hour_kzt=800)
        vip = Zone(club_id=club.id, name="VIP", price_per_hour_kzt=1500)
        day = Zone(club_id=daytime.id, name="Standard", price_per_hour_kzt=700)
        session.add_all([standard, vip, day])
        await session.flush()
        session.add_all(
            [Pc(club_id=club.id, zone_id=standard.id, label=f"S-{n:02d}") for n in range(1, 7)]
            + [Pc(club_id=club.id, zone_id=vip.id, label=f"VIP-{n:02d}") for n in range(1, 5)]
            + [Pc(club_id=daytime.id, zone_id=day.id, label=f"D-{n:02d}") for n in range(1, 5)]
        )
        await session.commit()
    print("Seeded demo clubs: Demo Arena (Almaty, 24/7), Demo Daytime (Astana, 10:00-23:00)")


async def _run(args: argparse.Namespace) -> None:
    try:
        if args.command == "create-owner":
            password = getpass.getpass("Password for the owner account: ")
            if len(password) < 10:
                sys.exit("Password must be at least 10 characters")
            await create_owner(args.org, args.email, password)
        elif args.command == "seed-demo":
            await seed_demo()
    finally:
        await get_engine().dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    owner = sub.add_parser("create-owner", help="create an organization and its owner account")
    owner.add_argument("--org", required=True, help="organization (legal entity) name")
    owner.add_argument("--email", required=True)
    sub.add_parser("seed-demo", help="insert demo clubs, zones and PCs (dev only)")
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()
