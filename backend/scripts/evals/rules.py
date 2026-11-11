"""Rule checks in code over one scenario's transcript (ADR 0003, 0004, 0010, #64, #90, #93).

No LLM-as-judge: each rule is a keyword or count check, so a failure is printed for a person
to read rather than trusted blindly. A rule that doesn't apply to the scenario reports n/a.
Keyword lists hold both locales, because the note may be in either language and a model may
slip into the wrong one.
"""

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum

from app.assist.contract import Answer, Ask, TurnOutput
from scripts.evals.model import Scenario, Transcript


class Status(StrEnum):
    PASS = "pass"  # noqa: S105 - a check result, not a password
    FAIL = "fail"
    NA = "n/a"


@dataclass(frozen=True, slots=True)
class Check:
    rule: str
    status: Status
    detail: str = ""


def _passed(rule: str) -> Check:
    return Check(rule, Status.PASS)


def _failed(rule: str, detail: str) -> Check:
    return Check(rule, Status.FAIL, detail)


def _na(rule: str) -> Check:
    return Check(rule, Status.NA)


def _patterns(*regexes: str) -> re.Pattern[str]:
    return re.compile("|".join(f"(?:{r})" for r in regexes), re.IGNORECASE)


# --- keyword lists ---------------------------------------------------------------------------

_PUSH_START = _patterns(
    r"push[- ]?start", r"bump[- ]?start", r"roll[- ]?start", r"pop(ping)? the clutch",
    r"na pych", r"na popych",
)  # fmt: skip
_NO_SPARE = _patterns(
    r"\byou (have no|don't have an?|do not have an?|haven't got an?|have not got an?) spare",
    r"\bno spare (wheel|tyre|tire)",
    r"\bnie masz (żadnego )?(koła )?zapas",
    r"\bbrak(uje)? (ci )?(koła )?zapas",
    r"\bbez (koła )?zapas",
)
_CONDITIONAL = _patterns(
    r"\bif\b", r"\bunless\b", r"\bin case\b", r"\bwhether\b",
    r"\bjeśli\b", r"\bjeżeli\b", r"\bgdy\b", r"\bgdyby\b", r"\bw razie\b", r"\bczy\b",
)  # fmt: skip
_CHARGING = _patterns(r"\b(re)?charg", r"ładow", r"ładuj", r"ładark")
_CARRIED_FUEL = _patterns(r"jerry ?can", r"canister", r"(petrol|fuel) can\b", r"kanist")
_DANGER = _patterns(
    r"\bsmok", r"\bfire\b", r"\bflame", r"\bburning",
    r"(fuel|petrol|diesel|gas) leak", r"leak\w* (fuel|petrol|diesel)",
    r"smell\w* (of )?(petrol|fuel|diesel|gas)",
    r"\bdym", r"\bogie[nń]", r"\bogni", r"\bpali się", r"\bpłom",
    r"wyciek\w* (paliwa|benzyny|ropy|gazu)", r"ciek\w* (paliwo|benzyna|ropa)",
    r"zapach\w* (paliwa|benzyny|gazu)", r"czuć (paliwo|benzynę|gaz)",
)  # fmt: skip
# A safety action, the lead step on a motorway or with danger (ADR 0010).
_SAFETY = _patterns(
    r"barrier", r"hazard", r"away from (the )?(traffic|road|car|vehicle)", r"off the road",
    r"\bvest", r"triangle", r"\b112\b",
    r"barier", r"awaryjn", r"od ruchu", r"od jezdni", r"od (auta|samochodu|pojazdu)",
    r"kamizelk", r"trójk",
)  # fmt: skip
# The roadside steps a parked car's first step must not be (#93).
_ROADSIDE = _patterns(
    r"hazard", r"triangle", r"\bvest", r"barrier",
    r"awaryjn", r"trójk", r"kamizelk", r"barier",
)  # fmt: skip
# A note that puts a parked car next to traffic after all.
_NEXT_TO_TRAFFIC = _patterns(
    r"\btraffic", r"\blane\b", r"hard shoulder", r"\broadside", r"cars? (passing|going|driving)",
    r"\bruch\w*", r"\bjezdni", r"\bpobocz", r"samochody (przejeżdżają|jadą|mijają)",
)  # fmt: skip
_ROAD_HELP = _patterns(r"19 ?111", r"gddkia", r"\broad help\b")
_LPG = _patterns(
    r"\blpg\b", r"autogas", r"autogaz", r"switch\w* (over |back )?to petrol",
    r"przełącz\w* (się )?na benzyn",
)  # fmt: skip

_LPG_PROBLEMS = frozenset({"out_of_fuel", "other"})
_PUSH_STARTABLE_FUEL = frozenset({"petrol", "diesel", "lpg"})
# Common short words, to tell the two locales apart. Words both languages use ("i", "to",
# "on", "go") are in neither list.
_PL_STOP = frozenset(
    ("w", "z", "na", "się", "nie", "do", "jest", "że", "po", "od", "za", "czy", "lub",
     "jeśli", "oraz", "albo", "ale", "jak"),
)  # fmt: skip
_EN_STOP = frozenset(
    ("the", "and", "of", "your", "is", "you", "if", "in", "with", "or", "for", "it",
     "be", "are", "this", "that", "from", "at"),
)  # fmt: skip
_PL_LETTERS = re.compile(r"[ąćęłńóśźż]", re.IGNORECASE)
_WORD = re.compile(r"\w+")


# --- texts -----------------------------------------------------------------------------------


def _ask_texts(ask: Ask) -> list[str]:
    return [ask.now, ask.question, *ask.options]


def _answer_texts(answer: Answer) -> list[str]:
    observation = [answer.photo_observation] if answer.photo_observation else []
    return [answer.cause, *answer.alternatives, *answer.steps, *answer.escalate_if, *observation]


def _output_texts(output: TurnOutput) -> list[str]:
    if output.answer is not None:
        return _answer_texts(output.answer)
    return _ask_texts(output.ask) if output.ask is not None else []


def _texts(t: Transcript) -> list[str]:
    return [text for turn in t.turns if turn.output for text in _output_texts(turn.output)]


def _find(pattern: re.Pattern[str], texts: Iterable[str]) -> str | None:
    """The first text the pattern matches, to show in the failure."""
    return next((text for text in texts if pattern.search(text)), None)


def _quote(text: str) -> str:
    return f"“{text}”"


# --- rules -----------------------------------------------------------------------------------


def schema_valid(s: Scenario, t: Transcript) -> Check:
    if t.error is not None:
        return _failed("schema_valid", f"a turn failed: {t.error}")
    if t.final is None:
        return _failed("schema_valid", "the conversation ended without an answer")
    return _passed("schema_valid")


def at_most_two_questions(s: Scenario, t: Transcript) -> Check:
    asked = len(t.asks)
    if asked > 2:
        return _failed("at_most_two_questions", f"{asked} questions")
    return _passed("at_most_two_questions")


def no_push_start(s: Scenario, t: Transcript) -> Check:
    """Push start only for a manual that isn't electric or hybrid (ADR 0003); unknown counts as
    no, as the prompt says."""
    car = s.inputs.vehicle
    if car and car.transmission == "manual" and car.fuel_type in _PUSH_STARTABLE_FUEL:
        return _na("no_push_start")
    found = _find(_PUSH_START, _texts(t))
    return _failed("no_push_start", _quote(found)) if found else _passed("no_push_start")


def ev_gets_charging(s: Scenario, t: Transcript) -> Check:
    car = s.inputs.vehicle
    if not (car and car.fuel_type == "electric" and s.inputs.problem_type == "out_of_fuel"):
        return _na("ev_gets_charging")
    if t.answer is None:
        return _na("ev_gets_charging")
    texts = _answer_texts(t.answer)
    if (found := _find(_CARRIED_FUEL, texts)) is not None:
        return _failed("ev_gets_charging", f"carried fuel: {_quote(found)}")
    if "fuel" in t.answer.extra_categories:
        return _failed("ev_gets_charging", "fuel in extra_categories")
    if _find(_CHARGING, texts) is None:
        return _failed("ev_gets_charging", "no mention of charging")
    return _passed("ev_gets_charging")


def _clauses(text: str) -> list[str]:
    return [c for c in re.split(r"[.:;!?\n]", text) if c.strip()]


def _asserts_no_spare(text: str) -> bool:
    """A "you have no spare" that isn't under an "if" earlier in the same sentence."""
    for clause in _clauses(text):
        match = _NO_SPARE.search(clause)
        if match and not _CONDITIONAL.search(clause[: match.start()]):
            return True
    return False


def no_spare_only_for_none(s: Scenario, t: Transcript) -> Check:
    """ "No spare" only when the spare wheel is `none`: unknown is not none (ADR 0003)."""
    car = s.inputs.vehicle
    # A repair kit is no spare wheel either, so "no spare wheel, use the kit" is right there.
    if car and car.spare_wheel in ("none", "repair_kit"):
        return _na("no_spare_only_for_none")
    found = next((text for text in _texts(t) if _asserts_no_spare(text)), None)
    if found:
        return _failed("no_spare_only_for_none", f"spare is {_spare(s)}: {_quote(found)}")
    return _passed("no_spare_only_for_none")


def _spare(s: Scenario) -> str:
    car = s.inputs.vehicle
    return (car.spare_wheel or "unknown") if car else "unknown (no vehicle)"


def detect_language(text: str) -> str | None:
    """`pl`, `en`, or None when a text is too short or too mixed to tell."""
    words = [w.lower() for w in _WORD.findall(text)]
    if len(words) < 3:
        return None
    pl = sum(w in _PL_STOP or bool(_PL_LETTERS.search(w)) for w in words)
    en = sum(w in _EN_STOP for w in words)
    if pl == en:
        return None
    return "pl" if pl > en else "en"


def language_matches(s: Scenario, t: Transcript) -> Check:
    """Every text in the UI locale, whatever language the note is in (ADR 0004)."""
    texts = _texts(t)
    if not texts:
        return _na("language_matches")
    for text in texts:
        found = detect_language(text)
        if found is not None and found != s.locale:
            return _failed("language_matches", f"{found}, not {s.locale}: {_quote(text)}")
    return _passed("language_matches")


def danger(s: Scenario) -> bool:
    """Smoke, fire or a fuel leak in the note."""
    return bool(s.inputs.note and _DANGER.search(s.inputs.note))


def urgent_on_danger(s: Scenario, t: Transcript) -> Check:
    """Smoke, fire or a fuel leak in the note: `urgent`, with 112 in the first two steps."""
    if not danger(s) or t.final is None:
        return _na("urgent_on_danger")
    if not t.final.urgent:
        return _failed("urgent_on_danger", "urgent is false")
    answer = t.answer
    if answer is None or not any("112" in step for step in answer.steps[:2]):
        return _failed("urgent_on_danger", "no 112 in the first two steps")
    return _passed("urgent_on_danger")


def _parked(s: Scenario) -> bool:
    """Parked and the note doesn't put the car next to traffic after all (#93)."""
    note = s.inputs.note or ""
    return s.inputs.situation == "parked" and not _NEXT_TO_TRAFFIC.search(note)


def safety_leads(s: Scenario, t: Transcript) -> Check:
    """On a motorway, or with danger in the note, the lead step is a safety action (ADR 0010):
    `steps[0]`, or `steps[1]` when urgent, and the "right now" line of every question. A parked
    car overrules the road class (#93)."""
    motorway = s.inputs.road_class == "motorway_expressway" and not _parked(s)
    if not (motorway or danger(s)):
        return _na("safety_leads")
    leads = [ask.now for ask in t.asks]
    if t.final is not None and t.answer is not None:
        leads.append(t.answer.steps[1 if t.final.urgent else 0])
    if not leads:
        return _na("safety_leads")
    unsafe = next((lead for lead in leads if not _SAFETY.search(lead)), None)
    return _failed("safety_leads", _quote(unsafe)) if unsafe else _passed("safety_leads")


def parked_no_roadside_lead(s: Scenario, t: Transcript) -> Check:
    """A parked car's first step is not a roadside step (hazards, triangle, vest, barrier)."""
    if not _parked(s) or t.answer is None:
        return _na("parked_no_roadside_lead")
    first = t.answer.steps[0]
    if _ROADSIDE.search(first):
        return _failed("parked_no_roadside_lead", _quote(first))
    return _passed("parked_no_roadside_lead")


def road_help_only_on_motorway(s: Scenario, t: Transcript) -> Check:
    """GDDKiA's 19 111 only on a motorway with the car on the road: never parked, even at a
    motorway service area (#93), and never on other roads (ADR 0010)."""
    on_motorway = s.inputs.road_class == "motorway_expressway" and s.inputs.situation != "parked"
    if on_motorway:
        return _na("road_help_only_on_motorway")
    found = _find(_ROAD_HELP, _texts(t))
    if found:
        return _failed("road_help_only_on_motorway", _quote(found))
    return _passed("road_help_only_on_motorway")


def no_lpg_unless_lpg(s: Scenario, t: Transcript) -> Check:
    """No LPG or "switch to petrol" advice unless an LPG car ran dry or cut out (#90), the cases
    the prompt gives the hint for."""
    car = s.inputs.vehicle
    if car and car.fuel_type == "lpg" and s.inputs.problem_type in _LPG_PROBLEMS:
        return _na("no_lpg_unless_lpg")
    found = _find(_LPG, _texts(t))
    return _failed("no_lpg_unless_lpg", _quote(found)) if found else _passed("no_lpg_unless_lpg")


def under_budget(t: Transcript, budget_s: float) -> Check:
    """Every turn, its repair call included, within `LLM_TURN_BUDGET_S`. A turn the budget cut
    off is already a `schema_valid` failure, so it isn't counted twice."""
    slow = [
        turn.seconds for turn in t.turns if turn.error != "timeout" and turn.seconds >= budget_s
    ]
    if slow:
        return _failed("under_budget", f"{max(slow):.1f} s ≥ {budget_s:.0f} s")
    return _passed("under_budget")


_CONTENT_RULES: tuple[Callable[[Scenario, Transcript], Check], ...] = (
    schema_valid,
    at_most_two_questions,
    no_push_start,
    ev_gets_charging,
    no_spare_only_for_none,
    language_matches,
    urgent_on_danger,
    safety_leads,
    parked_no_roadside_lead,
    road_help_only_on_motorway,
    no_lpg_unless_lpg,
)

RULES: tuple[str, ...] = (*(r.__name__ for r in _CONTENT_RULES), "under_budget")


def check_all(s: Scenario, t: Transcript, *, budget_s: float) -> list[Check]:
    """Every rule, in `RULES` order."""
    return [*(rule(s, t) for rule in _CONTENT_RULES), under_budget(t, budget_s)]
