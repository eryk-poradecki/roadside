"""The eval rule checks against hand-written good and bad outputs (#64)."""

from dataclasses import replace
from typing import Any, ClassVar

import pytest

from app.assist.contract import validate_output
from app.assist.prompt import TurnInputs, VehicleFactBlock
from app.domain.ai_turn import Locale
from scripts.evals import rules
from scripts.evals.model import Scenario, Transcript, Turn
from scripts.evals.rules import Status
from tests.fakes import answer_json, ask_json

STEPS_EN = ["First, get everyone behind the barrier", "Call your assistance for a tow"]
STEPS_PL = ["Najpierw stańcie wszyscy za barierą", "Zadzwoń po pomoc drogową do ubezpieczyciela"]


def vehicle(**overrides: Any) -> VehicleFactBlock:
    base = VehicleFactBlock(
        name="Golf",
        make_model="VW Golf",
        year=2018,
        fuel_type="petrol",
        transmission="manual",
        tyre_size=None,
        spare_wheel="full_size",
        wheel_locks=False,
        lock_key_location=None,
        has_assistance=True,
        assistance_insurer="PZU",
    )
    return replace(base, **overrides)


def scenario(
    *,
    locale: Locale = "en",
    problem: str = "flat_tyre",
    note: str | None = None,
    car: VehicleFactBlock | None = None,
    no_vehicle: bool = False,
    road_class: str = "local_street",
    situation: str = "on_road",
) -> Scenario:
    inputs = TurnInputs(
        vehicle=None if no_vehicle else car or vehicle(),
        problem_type=problem,
        note=note,
        local_time="2026-11-11T14:00+01:00",
        dark=False,
        road_class=road_class,
        situation=situation,
    )
    return Scenario(id="s", locale=locale, inputs=inputs)


def answered(seconds: float = 3.0, **answer: Any) -> Transcript:
    """A one-turn transcript; `answer` overrides fields of a valid English answer."""
    answer.setdefault("steps", STEPS_EN)
    raw = answer_json(**answer)
    return Transcript((Turn(seconds, validate_output(raw, allow_ask=False), model="m"),))


def asked_then(answer: Transcript, *asks: str) -> Transcript:
    turns = tuple(Turn(2.0, validate_output(a, allow_ask=True), model="m") for a in asks)
    return Transcript(turns + answer.turns)


def check(name: str, s: Scenario, t: Transcript, budget_s: float = 90.0) -> rules.Check:
    found = [c for c in rules.check_all(s, t, budget_s=budget_s) if c.rule == name]
    assert len(found) == 1, f"no single check named {name}"
    return found[0]


def status(name: str, s: Scenario, t: Transcript, budget_s: float = 90.0) -> Status:
    return check(name, s, t, budget_s).status


class TestSchemaValid:
    def test_a_validated_answer_passes(self) -> None:
        assert status("schema_valid", scenario(), answered()) is Status.PASS

    def test_a_failed_turn_fails_with_its_reason(self) -> None:
        failed = Transcript((Turn(5.0, error="invalid_output"),))
        result = check("schema_valid", scenario(), failed)
        assert result.status is Status.FAIL
        assert "invalid_output" in result.detail


class TestAtMostTwoQuestions:
    def test_two_questions_pass(self) -> None:
        t = asked_then(answered(), ask_json(), ask_json(question="Which wheel?"))
        assert status("at_most_two_questions", scenario(), t) is Status.PASS

    def test_three_questions_fail(self) -> None:
        t = asked_then(answered(), ask_json(), ask_json(), ask_json())
        assert status("at_most_two_questions", scenario(), t) is Status.FAIL


class TestNoPushStart:
    @pytest.mark.parametrize(
        "car",
        [
            vehicle(transmission="automatic"),
            vehicle(fuel_type="electric", transmission=None),
            vehicle(fuel_type="hybrid", transmission="automatic"),
            vehicle(fuel_type="plug_in_hybrid", transmission="manual"),
            vehicle(transmission=None),
        ],
    )
    def test_push_start_fails_for_a_car_that_cannot_be_push_started(
        self, car: VehicleFactBlock
    ) -> None:
        t = answered(steps=["Get behind the barrier", "Try to push-start the car in second gear"])
        s = scenario(problem="flat_battery", car=car)
        assert status("no_push_start", s, t) is Status.FAIL

    def test_a_polish_push_start_is_caught(self) -> None:
        t = answered(steps=["Stań za barierą", "Spróbuj odpalić auto na pych"])
        s = scenario(locale="pl", problem="flat_battery", car=vehicle(transmission="automatic"))
        assert status("no_push_start", s, t) is Status.FAIL

    def test_jump_leads_pass_for_an_automatic(self) -> None:
        t = answered(steps=["Get behind the barrier", "Ask someone for a jump start with leads"])
        s = scenario(problem="flat_battery", car=vehicle(transmission="automatic"))
        assert status("no_push_start", s, t) is Status.PASS

    def test_does_not_apply_to_a_manual_petrol_car(self) -> None:
        t = answered(steps=["Get behind the barrier", "Push start it in second gear"])
        s = scenario(problem="flat_battery")
        assert status("no_push_start", s, t) is Status.NA


class TestEvGetsCharging:
    EV = vehicle(fuel_type="electric", transmission=None)

    def test_charging_passes(self) -> None:
        t = answered(
            steps=["Get behind the barrier", "Call for a flatbed to the nearest charging station"],
            extra_categories=["charging"],
        )
        s = scenario(problem="out_of_fuel", car=self.EV)
        assert status("ev_gets_charging", s, t) is Status.PASS

    def test_a_jerry_can_fails(self) -> None:
        t = answered(steps=["Get behind the barrier", "Walk to get fuel in a jerry can"])
        s = scenario(problem="out_of_fuel", car=self.EV)
        assert status("ev_gets_charging", s, t) is Status.FAIL

    def test_fuel_in_the_nearby_categories_fails(self) -> None:
        t = answered(
            steps=["Get behind the barrier", "Call for a tow to a charging point"],
            extra_categories=["fuel"],
        )
        s = scenario(problem="out_of_fuel", car=self.EV)
        assert status("ev_gets_charging", s, t) is Status.FAIL

    def test_polish_charging_passes(self) -> None:
        t = answered(steps=["Stańcie za barierą", "Wezwij lawetę do najbliższej ładowarki"])
        s = scenario(locale="pl", problem="out_of_fuel", car=self.EV)
        assert status("ev_gets_charging", s, t) is Status.PASS

    def test_does_not_apply_to_a_petrol_car(self) -> None:
        assert status("ev_gets_charging", scenario(problem="out_of_fuel"), answered()) is Status.NA

    def test_discharged_is_not_charging(self) -> None:
        t = answered(steps=["Get behind the barrier", "The battery is discharged, call a flatbed"])
        s = scenario(problem="out_of_fuel", car=self.EV)
        assert status("ev_gets_charging", s, t) is Status.FAIL


class TestNoSpareOnlyForNone:
    def test_saying_no_spare_fails_when_the_spare_is_unknown(self) -> None:
        t = answered(steps=["Get behind the barrier", "You have no spare, so call a tow"])
        s = scenario(car=vehicle(spare_wheel=None))
        assert status("no_spare_only_for_none", s, t) is Status.FAIL

    def test_polish_no_spare_fails_for_a_space_saver(self) -> None:
        t = answered(steps=["Stań za barierą", "Nie masz koła zapasowego, wezwij pomoc"])
        s = scenario(locale="pl", car=vehicle(spare_wheel="space_saver"))
        assert status("no_spare_only_for_none", s, t) is Status.FAIL

    def test_a_conditional_passes(self) -> None:
        t = answered(
            steps=["Get behind the barrier", "If you have no spare, use the repair kit"],
            escalate_if=["Jeśli nie masz koła zapasowego, wezwij lawetę"],
        )
        s = scenario(car=vehicle(spare_wheel=None))
        assert status("no_spare_only_for_none", s, t) is Status.PASS

    def test_no_vehicle_counts_as_unknown(self) -> None:
        t = answered(steps=["Get behind the barrier", "There is no spare wheel, so call a tow"])
        assert status("no_spare_only_for_none", scenario(no_vehicle=True), t) is Status.FAIL

    def test_does_not_apply_when_the_spare_is_none(self) -> None:
        t = answered(steps=["Get behind the barrier", "You have no spare, so call a tow"])
        s = scenario(car=vehicle(spare_wheel="none"))
        assert status("no_spare_only_for_none", s, t) is Status.NA

    def test_a_repair_kit_is_no_spare_wheel(self) -> None:
        t = answered(
            steps=["Get behind the barrier", "There is no spare wheel, use the repair kit"]
        )
        s = scenario(car=vehicle(spare_wheel="repair_kit"))
        assert status("no_spare_only_for_none", s, t) is Status.NA

    def test_an_if_before_a_colon_does_not_excuse_it(self) -> None:
        t = answered(steps=["Get behind the barrier", "If needed: you have no spare, call a tow"])
        s = scenario(car=vehicle(spare_wheel=None))
        assert status("no_spare_only_for_none", s, t) is Status.FAIL


class TestLanguageMatches:
    def test_english_passes_for_english(self) -> None:
        assert status("language_matches", scenario(), answered()) is Status.PASS

    def test_polish_passes_for_polish(self) -> None:
        t = answered(
            cause="Najpewniej przebita opona tylnego koła",
            alternatives=["Uszkodzony wentyl"],
            steps=STEPS_PL,
            escalate_if=["Czujesz zapach paliwa"],
        )
        assert status("language_matches", scenario(locale="pl"), t) is Status.PASS

    def test_an_english_answer_fails_for_polish(self) -> None:
        result = check("language_matches", scenario(locale="pl"), answered())
        assert result.status is Status.FAIL
        assert "puncture" in result.detail

    def test_one_polish_step_fails_an_english_answer(self) -> None:
        t = answered(steps=["Get everyone behind the barrier", "Zadzwoń po pomoc drogową teraz"])
        assert status("language_matches", scenario(), t) is Status.FAIL

    def test_a_question_in_the_wrong_language_fails(self) -> None:
        t = asked_then(answered(), ask_json(question="Czy samochód stoi na poboczu drogi?"))
        assert status("language_matches", scenario(), t) is Status.FAIL

    @pytest.mark.parametrize("text", ["I don't know", "I have a jack", "I am not sure"])
    def test_english_i_is_not_polish(self, text: str) -> None:
        t = asked_then(answered(), ask_json(options=(text, "Something else entirely")))
        assert status("language_matches", scenario(), t) is Status.PASS

    def test_polish_to_is_not_english(self) -> None:
        t = answered(
            cause="Najpewniej przebita opona",
            alternatives=[],
            steps=["Stańcie wszyscy za barierą", "Wezwij pomoc PZU, to szybciej"],
            escalate_if=["Czujesz zapach paliwa"],
        )
        assert status("language_matches", scenario(locale="pl"), t) is Status.PASS


class TestUrgentOnDanger:
    URGENT_STEPS: ClassVar = ["Call 112 now", "Get everyone well away, behind the barrier"]

    @pytest.mark.parametrize(
        "note",
        [
            "Smoke is coming from under the bonnet",
            "Spod maski leci dym",
            "I can smell petrol and there's a puddle under the car",
            "Wyciek paliwa pod autem",
            "Fire in the engine bay",
        ],
    )
    def test_a_danger_note_needs_urgent_with_112(self, note: str) -> None:
        s = scenario(problem="other", note=note)
        assert status("urgent_on_danger", s, answered()) is Status.FAIL
        urgent = answered(urgent=True, steps=self.URGENT_STEPS)
        assert status("urgent_on_danger", s, urgent) is Status.PASS

    def test_does_not_apply_without_danger(self) -> None:
        s = scenario(problem="other", note="Strange rattle from the back")
        assert status("urgent_on_danger", s, answered()) is Status.NA


class TestSafetyLeads:
    def test_motorway_with_a_safety_first_step_passes(self) -> None:
        s = scenario(road_class="motorway_expressway")
        assert status("safety_leads", s, answered()) is Status.PASS

    def test_motorway_leading_with_the_jack_fails(self) -> None:
        t = answered(steps=["Get the jack from the boot", "Get behind the barrier"])
        result = check("safety_leads", scenario(road_class="motorway_expressway"), t)
        assert result.status is Status.FAIL
        assert "jack" in result.detail

    def test_urgent_judges_the_second_step(self) -> None:
        s = scenario(problem="other", note="Smoke from the engine")
        good = answered(urgent=True, steps=["Call 112", "Get behind the barrier, away from it"])
        bad = answered(urgent=True, steps=["Call 112", "Open the bonnet to look"])
        assert status("safety_leads", s, good) is Status.PASS
        assert status("safety_leads", s, bad) is Status.FAIL

    def test_a_question_must_lead_with_safety_too(self) -> None:
        s = scenario(road_class="motorway_expressway")
        t = asked_then(answered(), ask_json(now="Have a look at the tyre"))
        assert status("safety_leads", s, t) is Status.FAIL

    def test_polish_safety_words_count(self) -> None:
        t = answered(steps=["Włącz światła awaryjne i wyjdź za barierę", "Zadzwoń po lawetę"])
        s = scenario(locale="pl", road_class="motorway_expressway")
        assert status("safety_leads", s, t) is Status.PASS

    def test_parked_on_a_motorway_skips_it(self) -> None:
        s = scenario(road_class="motorway_expressway", situation="parked")
        assert status("safety_leads", s, answered()) is Status.NA

    def test_a_local_street_skips_it(self) -> None:
        t = answered(steps=["Get the jack from the boot", "Loosen the nuts"])
        assert status("safety_leads", scenario(), t) is Status.NA


class TestParkedNoRoadsideLead:
    PARKED = "noticed it in the supermarket car park"

    def test_a_roadside_first_step_fails_when_parked(self) -> None:
        s = scenario(situation="parked", note=self.PARKED)
        t = answered(steps=["Turn on your hazard lights", "Loosen the wheel nuts"])
        assert status("parked_no_roadside_lead", s, t) is Status.FAIL

    def test_a_polish_triangle_first_fails(self) -> None:
        s = scenario(locale="pl", situation="parked", note=self.PARKED)
        t = answered(steps=["Ustaw trójkąt ostrzegawczy", "Odkręć śruby koła"])
        assert status("parked_no_roadside_lead", s, t) is Status.FAIL

    def test_the_parking_brake_first_passes(self) -> None:
        s = scenario(situation="parked", note=self.PARKED)
        t = answered(steps=["Put the parking brake on, on firm level ground", "Loosen the nuts"])
        assert status("parked_no_roadside_lead", s, t) is Status.PASS

    def test_a_note_next_to_traffic_skips_it(self) -> None:
        s = scenario(situation="parked", note="Parked on the street, cars passing right by me")
        t = answered(steps=["Turn on your hazard lights", "Loosen the wheel nuts"])
        assert status("parked_no_roadside_lead", s, t) is Status.NA

    def test_on_the_road_skips_it(self) -> None:
        assert status("parked_no_roadside_lead", scenario(), answered()) is Status.NA


class TestRoadHelpOnlyOnMotorway:
    STEPS: ClassVar = ["Get behind the barrier", "Call road help on 19 111"]

    def test_parked_at_a_motorway_service_area_fails(self) -> None:
        s = scenario(road_class="motorway_expressway", situation="parked")
        assert status("road_help_only_on_motorway", s, answered(steps=self.STEPS)) is Status.FAIL

    def test_a_local_street_fails(self) -> None:
        t = answered(steps=["Get behind the barrier", "Zadzwoń do GDDKiA"])
        assert status("road_help_only_on_motorway", scenario(), t) is Status.FAIL

    def test_a_local_street_without_it_passes(self) -> None:
        assert status("road_help_only_on_motorway", scenario(), answered()) is Status.PASS

    def test_on_a_motorway_on_the_road_it_is_allowed(self) -> None:
        s = scenario(road_class="motorway_expressway")
        result = status("road_help_only_on_motorway", s, answered(steps=self.STEPS))
        assert result is Status.NA


class TestNoLpgUnlessLpg:
    LPG_STEPS: ClassVar = ["Get behind the barrier", "Check whether the car has switched to petrol"]

    @pytest.mark.parametrize(
        ("car", "no_vehicle"),
        [
            (vehicle(fuel_type="petrol"), False),
            (vehicle(fuel_type=None), False),
            (None, True),
        ],
    )
    @pytest.mark.parametrize("problem", ["out_of_fuel", "other"])
    def test_lpg_advice_fails_for_a_car_that_is_not_lpg(
        self, car: VehicleFactBlock | None, no_vehicle: bool, problem: str
    ) -> None:
        s = scenario(problem=problem, car=car, no_vehicle=no_vehicle)
        assert status("no_lpg_unless_lpg", s, answered(steps=self.LPG_STEPS)) is Status.FAIL
        assert status("no_lpg_unless_lpg", s, answered()) is Status.PASS

    def test_polish_lpg_mention_fails(self) -> None:
        t = answered(steps=["Stań za barierą", "Sprawdź, czy instalacja LPG przełączyła"])
        assert status("no_lpg_unless_lpg", scenario(locale="pl"), t) is Status.FAIL

    def test_does_not_apply_to_an_lpg_car(self) -> None:
        s = scenario(problem="out_of_fuel", car=vehicle(fuel_type="lpg"))
        assert status("no_lpg_unless_lpg", s, answered(steps=self.LPG_STEPS)) is Status.NA

    def test_an_lpg_car_with_a_flat_tyre_gets_no_lpg_advice(self) -> None:
        s = scenario(problem="flat_tyre", car=vehicle(fuel_type="lpg"))
        assert status("no_lpg_unless_lpg", s, answered(steps=self.LPG_STEPS)) is Status.FAIL


class TestUnderBudget:
    def test_every_turn_under_the_budget_passes(self) -> None:
        t = asked_then(answered(seconds=20.0), ask_json())
        assert status("under_budget", scenario(), t, budget_s=30.0) is Status.PASS

    def test_a_slow_turn_fails(self) -> None:
        result = check("under_budget", scenario(), answered(seconds=31.0), budget_s=30.0)
        assert result.status is Status.FAIL
        assert "31.0" in result.detail

    def test_a_timed_out_turn_is_left_to_schema_valid(self) -> None:
        t = Transcript((Turn(30.0, error="timeout"),))
        assert status("under_budget", scenario(), t, budget_s=30.0) is Status.PASS


def test_every_rule_reports_once_per_scenario() -> None:
    names = [c.rule for c in rules.check_all(scenario(), answered(), budget_s=90.0)]
    assert names == list(rules.RULES)
