"""The fixed demo vehicles of `docs/demo-scenarios.md` (#122), seeded in demo mode so a visitor
can pick a scenario's car and replay its recording.

A vehicle reaches the replay key through its fuel type, transmission, spare wheel and whether
it has assistance (ADR 0004); the rest makes them read as real cars. They carry no
registration or policy number: the recording run plants its canaries there instead
(`scripts/demo/scenarios.py`).
"""

import aiosqlite

from app.db.connection import transaction
from app.domain.vehicle import FuelType, SpareWheel, Transmission
from app.repositories.vehicles import VehicleRepository
from app.schemas.vehicle import VehicleCreate
from app.services.clock import utc_now

# `has_assistance` needs a non-blank phone. With no digit in it the app never offers to call
# it, so it can't be mistaken for a real number; the word reads the same in Polish.
DEMO_ASSISTANCE_PHONE = "demo"

# By the document's profile id, in its table's order. API bodies, so they pass the same
# validation as a visitor's own vehicle.
DEMO_VEHICLES: dict[str, VehicleCreate] = {
    "golf_2017": VehicleCreate(
        name="Golf",
        make_model="Volkswagen Golf VII 1.4 TSI",
        year=2017,
        fuel_type=FuelType.PETROL,
        transmission=Transmission.MANUAL,
        spare_wheel=SpareWheel.FULL_SIZE,
        wheel_locks=True,
        lock_key_location="glovebox",
    ),
    "mini_ev_2021": VehicleCreate(
        name="MINI",
        make_model="MINI Cooper SE Electric",
        year=2021,
        fuel_type=FuelType.ELECTRIC,
        transmission=Transmission.AUTOMATIC,
        spare_wheel=SpareWheel.NONE,
        assistance_phone=DEMO_ASSISTANCE_PHONE,
    ),
    "octavia_2015": VehicleCreate(
        name="Octavia",
        make_model="Škoda Octavia III 1.6 TDI",
        year=2015,
        fuel_type=FuelType.DIESEL,
        transmission=Transmission.MANUAL,
        spare_wheel=SpareWheel.SPACE_SAVER,
    ),
}
# The car of the video scenario (#4), so the recorded walkthrough needs no vehicle pick.
DEFAULT_DEMO_VEHICLE = "octavia_2015"


async def seed_demo_vehicles(conn: aiosqlite.Connection, repo: VehicleRepository) -> int:
    """Add missing marked profiles, preserving every existing vehicle and default."""
    now = utc_now()
    added = 0
    async with transaction(conn):
        profiles = {v.demo_profile for v in await repo.list_all()}
        has_default = await repo.has_default()
        for profile_id, body in DEMO_VEHICLES.items():
            if profile_id in profiles:
                continue
            is_default = profile_id == DEFAULT_DEMO_VEHICLE and not has_default
            await repo.insert(body.to_facts(), is_default, now, demo_profile=profile_id)
            added += 1
    return added
