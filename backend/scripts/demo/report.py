"""Markdown for the recording run's review and for the demo check (#63)."""

from pathlib import Path
from typing import Any

from scripts.demo.record import RecordRun
from scripts.demo.reuse import Outcome
from scripts.demo.walk import Walk


def _turn_lines(turn: dict[str, Any]) -> list[str]:
    who = f"{turn['provider']} / {turn['model']} / prompt {turn['prompt_version']}"
    urgent = " · **urgent**" if turn["urgent"] else ""
    if turn["kind"] == "question":
        q = turn["question"]
        return [
            f"- **Question** ({who}){urgent}",
            f"  - Now: {q['now']}",
            f"  - {q['question']}",
            *[f"  - Option: `{o}`" for o in q["options"]],
        ]
    a = turn["advice"]
    lines = [
        f"- **Advice** ({who}){urgent}",
        f"  - Cause ({a['confidence']}): {a['cause']}",
        *[f"  - Could also be: {x}" for x in a["alternatives"]],
    ]
    if a["photo_observation"]:
        lines.append(f"  - Photo: {a['photo_observation']}")
    lines += [f"  - {i}. {step}" for i, step in enumerate(a["steps"], 1)]
    lines += [f"  - Escalate if: {x}" for x in a["escalate_if"]]
    return lines


def _walk_section(w: Walk, steps: list[tuple[str, str, Outcome]]) -> list[str]:
    lines = [f"### {w.name}", ""]
    if w.turns:
        inputs = w.turns[-1]["inputs"]
        lines.append(
            f"Context: road_class `{inputs['road_class']}`, settlement `{inputs['settlement']}`,"
            f" dark `{inputs['dark']}`, local time `{inputs['local_time']}`,"
            f" photos seen {len(inputs['photo_ids_seen'])}, label `{w.location_label}`"
        )
    if w.nearby:
        lines.append("Nearby: " + ", ".join(f"{r} km {s}" for r, s in w.nearby.items()))
    lines += [f"- Recording `{name}`: {label}, {outcome}" for label, name, outcome in steps]
    lines += [f"- **Problem:** {p}" for p in w.problems]
    lines += [f"- **Review:** {d}" for d in w.deviations]
    if w.needs_choice:
        intent, question, options = w.needs_choice
        meaning = next((s.option_meaning for s in w.branch.steps if s.intent == intent), None)
        lines += [
            f"- **Needs a choice** for `{intent}` ({meaning}): {question}",
            *[f"  - `{o}`" for o in options],
        ]
    lines += [""]
    for turn in w.turns:
        lines += _turn_lines(turn)
    for locale, report in w.reports.items():
        lines += ["", f"Damage report draft ({locale}):", "", "```text", report["body"], "```"]
    return [*lines, ""]


def review_markdown(run: RecordRun) -> str:
    recorded = sum(o == "recorded" for steps in run.steps.values() for *_, o in steps)
    lines = [
        "# Recording run",
        "",
        f"{len(run.walks)} walks, {recorded} recordings made, "
        f"{sum(not w.ok for w in run.walks)} not complete.",
        "",
        "## Privacy scan",
        "",
    ]
    lines += [f"- **{f.path.name}**: {f.what}" for f in run.findings] or ["Clean."]
    if run.orphans:
        lines += ["", "## Orphans (no walk reached them)", ""]
        lines += [f"- `{_rel(p)}`" for p in run.orphans]
    lines += ["", "## Walks", ""]
    for w in run.walks:
        lines += _walk_section(w, run.steps.get(w.name, []))
    return "\n".join(lines)


def check_markdown(walks: list[Walk]) -> str:
    failed = [w for w in walks if not w.ok]
    lines = [
        "# Demo check",
        "",
        f"{len(walks) - len(failed)}/{len(walks)} walks replayed with no miss.",
        "",
        "| Walk | Turns | Nearby | Reports | Result |",
        "| --- | --- | --- | --- | --- |",
    ]
    for w in walks:
        turns = " → ".join(t["kind"] for t in w.turns) or "-"
        nearby = ", ".join(f"{r} km {s}" for r, s in w.nearby.items()) or "-"
        reports = ", ".join(w.reports) or "-"
        result = "; ".join(w.problems) or ("ok" if w.ok else "needs a recorded choice")
        lines.append(f"| {w.name} | {turns} | {nearby} | {reports} | {result} |")
    return "\n".join(lines) + "\n"


def _rel(path: Path) -> str:
    return f"{path.parent.name}/{path.name}"
