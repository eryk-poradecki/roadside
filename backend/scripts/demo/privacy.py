"""The privacy scan over a recordings directory, run before recordings are committed (#63).

A recording may hold no registration, policy number, phone or coordinates of the driver's.
The demo vehicles carry planted canary values, so finding one anywhere means a driver's real
value would have leaked too. The AI text is also searched for anything shaped like a
coordinate or a phone number, which the model must never invent. Place recordings hold public
map data (a place's position and its listed phone are what the Nearby panel shows), so only
the canaries are searched for there.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from scripts.demo.scenarios import CANARY_PHONE, CANARY_POLICY, CANARY_REGISTRATION

_CANARIES = (CANARY_REGISTRATION, CANARY_POLICY, CANARY_PHONE)
# Four or more decimals: a coordinate to within ~10 m. "1.4 TSI" or "65%" never match.
_COORDINATE = re.compile(r"(?<![\d.])-?\d{1,3}\.\d{4,}(?![\d.])")
# Nine or more digits, maybe grouped: a phone number. 112 is the only number allowed.
_PHONE = re.compile(r"(?<!\d)(?:\+\d{2}[\s-]?)?\d{3}[\s-]?\d{3}[\s-]?\d{3}(?!\d)")


@dataclass(frozen=True, slots=True)
class Finding:
    path: Path
    what: str


def _ai_text(path: Path) -> str | None:
    """The model's own text of an AI recording; None for any other file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    raw = data.get("raw_output") if isinstance(data, dict) else None
    return raw if isinstance(raw, str) else None


def scan(directory: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(directory.rglob("*.json")):
        text = path.read_text(encoding="utf-8")
        findings += [Finding(path, f"planted value {c!r}") for c in _CANARIES if c in text]
        raw = _ai_text(path) if path.parent == directory else None
        if raw is None:
            continue
        findings += [Finding(path, f"coordinate {m!r}") for m in _COORDINATE.findall(raw)]
        findings += [Finding(path, f"phone number {m!r}") for m in _PHONE.findall(raw)]
    return findings
