"""The fixed demo scenario catalogue (ADR 0013).

Public-road points belong to the scenarios. Recording scripts add their own time of day.
"""

from collections.abc import Mapping
from pathlib import Path

from app.assist.prompt import TurnInputs, VehicleFactBlock
from app.assist.replay_key import replay_key, scenario_key
from app.domain.ai_turn import Locale
from app.domain.incident import ProblemType, Situation
from app.integrations.llm.base import LLMProvider
from app.integrations.llm.recording import load_recordings
from app.integrations.place_recording import PlaceRecording
from app.schemas.incident import LocationRead
from app.schemas.meta import DemoScenario, DemoScenarioLocale
from app.services.demo_vehicles import DEMO_VEHICLES

DEMO_SCENARIOS: tuple[DemoScenario, ...] = (
    DemoScenario(
        id="tyre_parked_morning",
        problem_type=ProblemType("flat_tyre"),
        vehicle_profile="golf_2017",
        situation=Situation("parked"),
        sample_photo_ids=["flat_tyre"],
        location=LocationRead(lat=52.4085, lon=16.91, accuracy_m=10),
        locales={
            "en": DemoScenarioLocale(
                title="Flat tyre before work",
                summary="A flat tyre on a parked Golf, before the morning commute.",
                note=(
                    "Was about to leave for work, but the front-left tyre is completely flat. "
                    "The car is parked outside my building."
                ),
            ),
            "pl": DemoScenarioLocale(
                title="Przebita opona przed pracą",
                summary="Golf stoi pod blokiem z przebitą oponą przed porannym wyjazdem.",
                note=(
                    "Rano chciałem jechać do pracy, ale lewe przednie koło jest całkiem flakiem."
                    " Auto stoi pod blokiem."
                ),
            ),
        },
    ),
    DemoScenario(
        id="battery_parked_night",
        problem_type=ProblemType("flat_battery"),
        vehicle_profile="golf_2017",
        situation=Situation("parked"),
        sample_photo_ids=[],
        location=LocationRead(lat=52.4085, lon=16.91, accuracy_m=10),
        locales={
            "en": DemoScenarioLocale(
                title="Car won't start after shopping",
                summary="A Golf clicks but won't start in a quiet car park at night.",
                note=(
                    "Left my lights on while shopping. Now it just clicks and won't start. The "
                    "supermarket car park is nearly empty."
                ),
            ),
            "pl": DemoScenarioLocale(
                title="Auto nie odpala po zakupach",
                summary="Golf tylko klika na pustym parkingu późnym wieczorem.",
                note=(
                    "Zostawiłem włączone światła na zakupach. Teraz tylko klika i nie odpala. "
                    "Parking pod marketem jest prawie pusty."
                ),
            ),
        },
    ),
    DemoScenario(
        id="fuel_almost_at_station",
        problem_type=ProblemType("out_of_fuel"),
        vehicle_profile="golf_2017",
        situation=Situation("on_road"),
        sample_photo_ids=["empty_fuel_gauge"],
        location=LocationRead(lat=52.4567, lon=16.6934, accuracy_m=10),
        locales={
            "en": DemoScenarioLocale(
                title="Out of fuel near a station",
                summary="A Golf runs out of petrol just before a fuel station.",
                note=(
                    "Ran out of petrol just before the station. Engine stopped, managed to pull "
                    "over."
                ),
            ),
            "pl": DemoScenarioLocale(
                title="Brak paliwa tuż przed stacją",
                summary="W Golfie kończy się benzyna tuż przed stacją paliw.",
                note=(
                    "Skończyła mi się benzyna tuż przed stacją. Silnik zgasł, udało mi się "
                    "zjechać na bok."
                ),
            ),
        },
    ),
    DemoScenario(
        id="pothole_damaged_wheel",
        problem_type=ProblemType("pothole_damage"),
        vehicle_profile="octavia_2015",
        situation=Situation("on_road"),
        sample_photo_ids=["rim_damage"],
        location=LocationRead(lat=52.4203, lon=20.7722, accuracy_m=10),
        locales={
            "en": DemoScenarioLocale(
                title="Wheel damaged by a pothole",
                summary="An Octavia hits a pothole, with a damaged rim and unusual steering.",
                note=(
                    "Hit a huge pothole. Pulled over but the rim looks damaged and the steering "
                    "felt weird."
                ),
            ),
            "pl": DemoScenarioLocale(
                title="Uszkodzone koło po dziurze",
                summary=(
                    "Octavia wpada w dziurę: felga jest uszkodzona, a kierownica dziwnie pracuje."
                ),
                note=(
                    "Wpadłem w dużą dziurę. Zjechałem na pobocze, felga jest uszkodzona i "
                    "dziwnie chodzi kierownica."
                ),
            ),
        },
    ),
    DemoScenario(
        id="tyre_motorway_night",
        problem_type=ProblemType("flat_tyre"),
        vehicle_profile="golf_2017",
        situation=Situation("on_road"),
        sample_photo_ids=["flat_tyre"],
        location=LocationRead(lat=52.3286, lon=15.8498, accuracy_m=10),
        locales={
            "en": DemoScenarioLocale(
                title="Flat tyre on the motorway",
                summary="An Octavia stops on the hard shoulder with a flat tyre at night.",
                note=(
                    "Front-left tyre went flat on the motorway. I'm on the hard shoulder, it's "
                    "dark and cars are passing really fast."
                ),
            ),
            "pl": DemoScenarioLocale(
                title="Przebita opona na autostradzie",
                summary="Octavia stoi nocą na pasie awaryjnym z przebitą oponą.",
                note=(
                    "Złapałem gumę w lewym przednim kole na autostradzie. Stoję na pasie "
                    "awaryjnym, jest ciemno, a auta jadą bardzo szybko."
                ),
            ),
        },
    ),
    DemoScenario(
        id="ev_wont_power_on",
        problem_type=ProblemType("flat_battery"),
        vehicle_profile="mini_ev_2021",
        situation=Situation("parked"),
        sample_photo_ids=[],
        location=LocationRead(lat=52.4064, lon=16.9252, accuracy_m=10),
        locales={
            "en": DemoScenarioLocale(
                title="Electric MINI won't turn on",
                summary=(
                    "A parked electric MINI has a dark dashboard despite a charged drive battery."
                ),
                note=(
                    "My electric MINI won't turn on. Battery was at 65% yesterday, but now the "
                    "dashboard is completely dark."
                ),
            ),
            "pl": DemoScenarioLocale(
                title="Elektryczny MINI się nie włącza",
                summary="MINI stoi z ciemną deską rozdzielczą mimo naładowanej baterii napędowej.",
                note=(
                    "Mój elektryczny MINI nie chce się włączyć. Wczoraj bateria miała 65%, a "
                    "teraz deska rozdzielcza jest całkiem ciemna."
                ),
            ),
        },
    ),
    DemoScenario(
        id="unknown_knocking_warning",
        problem_type=ProblemType("other"),
        vehicle_profile=None,
        situation=Situation("on_road"),
        sample_photo_ids=[],
        location=LocationRead(lat=52.36, lon=20.62, accuracy_m=1000),
        locales={
            "en": DemoScenarioLocale(
                title="Knocking and a warning light",
                summary="An unfamiliar noise and a warning light, with few details known.",
                note=(
                    "smth knocking at the front and some warning light on, pulled over dont know"
                    " what it is"
                ),
            ),
            "pl": DemoScenarioLocale(
                title="Stukanie i kontrolka",
                summary="Coś stuka z przodu i świeci kontrolka, ale niewiele więcej wiadomo.",
                note=(
                    "cos stuka z przodu i jakas kontrolka sie swieci, zjechalem na bok nie wiem "
                    "co to"
                ),
            ),
        },
    ),
    DemoScenario(
        id="smoke_engine_bay",
        problem_type=ProblemType("other"),
        vehicle_profile="octavia_2015",
        situation=Situation("on_road"),
        sample_photo_ids=[],
        location=LocationRead(lat=52.1006, lon=21.5015, accuracy_m=10),
        locales={
            "en": DemoScenarioLocale(
                title="Smoke under the bonnet",
                summary="Thick smoke and a burning smell after pulling over.",
                note=(
                    "Pulled over, there's thick grey smoke coming from under the bonnet and a "
                    "strong burning smell."
                ),
            ),
            "pl": DemoScenarioLocale(
                title="Dym spod maski",
                summary=(
                    "Po zjechaniu na pobocze spod maski wydobywa się gęsty dym i zapach spalenizny."
                ),
                note=(
                    "Zjechałem na pobocze, spod maski leci gęsty szary dym i strasznie śmierdzi "
                    "spalenizną."
                ),
            ),
        },
    ),
)


def recorded_scenarios(
    directory: Path,
    places: Mapping[str, PlaceRecording],
    provider: LLMProvider,
) -> list[DemoScenario]:
    """Advertise only first turns that match the provider's actual replay inputs."""
    recordings = load_recordings(directory)
    available = []
    for scenario in DEMO_SCENARIOS:
        vehicle = (
            VehicleFactBlock.from_facts(DEMO_VEHICLES[scenario.vehicle_profile].to_facts())
            if scenario.vehicle_profile
            else None
        )
        place = places.get(scenario_key(scenario.problem_type, scenario.situation, vehicle))
        # Without recorded darkness the assistant would depend on the visitor's clock.
        if place is None or place.dark is None:
            continue
        locales: dict[Locale, DemoScenarioLocale] = {}
        for locale, copy in scenario.locales.items():
            inputs = TurnInputs(
                vehicle=vehicle,
                problem_type=scenario.problem_type,
                note=copy.note,
                local_time="",
                dark=place.dark,
                road_class=place.location.context.road_class.value if place.location else "unknown",
                situation=scenario.situation,
            )
            key = replay_key(
                inputs,
                locale=locale,
                sample_photo_ids=scenario.sample_photo_ids,
                vision=bool(scenario.sample_photo_ids)
                and provider.vision
                and provider.max_images > 0,
                replies=[],
            )
            if key in recordings:
                locales[locale] = copy
        if locales:
            available.append(scenario.model_copy(update={"locales": locales}))
    return available
