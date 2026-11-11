"""The eval scenarios: about ten driver situations, each aimed at one or more rules (#64).

Notes are what a driver would type, sometimes in the other language than the UI. The local
time and the location context are fixed here, as the backend would have computed them.
"""

from dataclasses import replace
from typing import Any

from app.assist.prompt import TurnInputs, VehicleFactBlock
from app.domain.ai_turn import Locale, Reply
from scripts.evals.model import Scenario

DAY = "2026-11-11T13:30+01:00"
NIGHT = "2026-11-11T21:40+01:00"

_GOLF = VehicleFactBlock(
    name="Golf",
    make_model="Volkswagen Golf VII",
    year=2017,
    fuel_type="petrol",
    transmission="manual",
    tyre_size="205/55 R16",
    spare_wheel="full_size",
    wheel_locks=True,
    lock_key_location="glovebox",
    has_assistance=True,
    assistance_insurer="PZU",
)


def car(**facts: Any) -> VehicleFactBlock:
    return replace(_GOLF, **facts)


def scenario(
    id: str,
    locale: Locale,
    problem: str,
    *,
    vehicle: VehicleFactBlock | None,
    note: str | None = None,
    road_class: str = "unknown",
    settlement: str = "unknown",
    situation: str = "on_road",
    night: bool = False,
    replies: tuple[Reply, ...] = (),
) -> Scenario:
    inputs = TurnInputs(
        vehicle=vehicle,
        problem_type=problem,
        note=note,
        local_time=NIGHT if night else DAY,
        dark=night,
        road_class=road_class,
        settlement=settlement,
        situation=situation,
    )
    return Scenario(id=id, locale=locale, inputs=inputs, replies=replies)


SCENARIOS: tuple[Scenario, ...] = (
    # Safety leads on a motorway at night; a full-size spare must not read as "no spare".
    scenario(
        "tyre_motorway_night_en",
        "en",
        "flat_tyre",
        vehicle=car(),
        note="Rear right tyre went flat, I'm on the hard shoulder",
        road_class="motorway_expressway",
        settlement="countryside",
        night=True,
    ),
    # Spare is `none`: "you have no spare" is right here.
    scenario(
        "tyre_no_spare_pl",
        "pl",
        "flat_tyre",
        vehicle=car(spare_wheel="none"),
        note="Złapałem gumę na osiedlowej uliczce",
        road_class="local_street",
        settlement="city",
    ),
    # A Polish note with the English UI: the answer stays English. Spare unknown.
    scenario(
        "tyre_pl_note_en_ui",
        "en",
        "flat_tyre",
        vehicle=car(spare_wheel=None, wheel_locks=None, lock_key_location=None),
        note="Przednia lewa opona całkiem płaska, stoję na poboczu",
        road_class="main_road",
        settlement="village",
    ),
    # No push start for an automatic; tell the tow company, flatbed preferred.
    scenario(
        "battery_automatic_en",
        "en",
        "flat_battery",
        vehicle=car(name="Octavia", make_model="Skoda Octavia", transmission="automatic"),
        note="Clicks but won't crank, lights are dim",
        road_class="local_street",
        settlement="town",
        night=True,
    ),
    # No push start for a hybrid.
    scenario(
        "battery_hybrid_pl",
        "pl",
        "flat_battery",
        vehicle=car(
            name="Corolla",
            make_model="Toyota Corolla",
            fuel_type="hybrid",
            transmission="automatic",
        ),
        note="Rano auto nie reaguje, deska ledwo świeci",
        road_class="local_street",
        settlement="city",
    ),
    # An EV that ran out: charging, never a jerry can.
    scenario(
        "ev_out_of_charge_en",
        "en",
        "out_of_fuel",
        vehicle=car(
            name="Model 3",
            make_model="Tesla Model 3",
            fuel_type="electric",
            transmission=None,
            spare_wheel="repair_kit",
        ),
        note="Range hit zero, the car stopped",
        road_class="main_road",
        settlement="countryside",
        night=True,
    ),
    # A petrol car that ran dry: no LPG hint (#90).
    scenario(
        "fuel_petrol_pl",
        "pl",
        "out_of_fuel",
        vehicle=car(),
        note="Skończyła się benzyna, auto zgasło",
        road_class="main_road",
        settlement="village",
    ),
    # Unknown fuel type: no LPG hint either (#90).
    scenario(
        "fuel_unknown_type_en",
        "en",
        "out_of_fuel",
        vehicle=car(fuel_type=None, transmission=None),
        note="Ran out of fuel, the gauge was broken",
        road_class="local_street",
        settlement="town",
    ),
    # An LPG car that ran dry: the switch-to-petrol hint is allowed.
    scenario(
        "fuel_lpg_pl",
        "pl",
        "out_of_fuel",
        vehicle=car(name="Astra", make_model="Opel Astra", fuel_type="lpg"),
        note="Auto szarpnęło i zgasło",
        road_class="main_road",
        settlement="countryside",
    ),
    # No vehicle and a vague note: the model may ask; scripted replies, then skip. No LPG, no
    # push start (transmission unknown).
    scenario(
        "other_no_vehicle_en",
        "en",
        "other",
        vehicle=None,
        note="Engine light came on and it lost power",
        road_class="main_road",
        settlement="town",
        replies=(
            Reply(text="It's orange and steady, not flashing"),
            Reply(text="I've pulled into a lay-by"),
        ),
    ),
    # Pothole damage at night on a main road: the tyre is damaged, so the spare and safety rules
    # apply as for a flat; the damage report is a separate call the evals don't cover.
    scenario(
        "pothole_main_road_night_pl",
        "pl",
        "pothole_damage",
        vehicle=car(spare_wheel="space_saver"),
        note="Wpadłem w głęboką dziurę, opona ma bąbel, a felga jest wygięta",
        road_class="main_road",
        settlement="village",
        night=True,
    ),
    # Smoke: urgent, 112 first, then a safety action.
    scenario(
        "smoke_pl",
        "pl",
        "other",
        vehicle=car(fuel_type="diesel"),
        note="Spod maski leci dym i czuć spaleniznę",
        road_class="main_road",
        settlement="countryside",
    ),
    # A fuel leak on a motorway at night: urgent.
    scenario(
        "fuel_leak_motorway_en",
        "en",
        "other",
        vehicle=car(fuel_type="diesel"),
        note="I can smell diesel and there's a puddle spreading under the car",
        road_class="motorway_expressway",
        settlement="countryside",
        night=True,
    ),
    # Parked (#93): no roadside lead, no road help.
    scenario(
        "tyre_parked_en",
        "en",
        "flat_tyre",
        vehicle=car(),
        note="Noticed it in the supermarket car park",
        road_class="local_street",
        settlement="city",
        situation="parked",
    ),
    # Parked at a motorway service area (#93): the road class says motorway, parked overrules
    # it, so no 19 111 and no roadside lead.
    scenario(
        "battery_parked_service_area_pl",
        "pl",
        "flat_battery",
        vehicle=car(),
        note="Stoję na parkingu na MOP-ie, po postoju auto nie odpala",
        road_class="motorway_expressway",
        settlement="countryside",
        situation="parked",
    ),
)
