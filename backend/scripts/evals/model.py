"""What an eval runs (a scenario) and what it gets back (a transcript)."""

from dataclasses import dataclass, field

from app.assist.contract import Answer, Ask, TurnOutput
from app.assist.prompt import TurnInputs
from app.domain.ai_turn import Locale, Reply


@dataclass(frozen=True, slots=True)
class Scenario:
    """One driver situation, as the model is told it.

    `replies` answer the model's clarifying questions in order. The options it offers aren't
    known in advance, so they are free text; once they run out, the driver skips to the steps.
    """

    id: str
    locale: Locale
    inputs: TurnInputs
    replies: tuple[Reply, ...] = ()


@dataclass(frozen=True, slots=True)
class Turn:
    """One model turn: the validated output, or why it failed. `seconds` covers the repair."""

    seconds: float
    output: TurnOutput | None = None
    error: str | None = None
    provider: str | None = None
    model: str | None = None


@dataclass(frozen=True, slots=True)
class Transcript:
    turns: tuple[Turn, ...] = field(default=())

    @property
    def asks(self) -> list[Ask]:
        return [t.output.ask for t in self.turns if t.output and t.output.ask]

    @property
    def final(self) -> TurnOutput | None:
        """The answer that closed the conversation; None when a turn failed."""
        last = self.turns[-1].output if self.turns else None
        return last if last is not None and last.kind == "answer" else None

    @property
    def answer(self) -> Answer | None:
        return self.final.answer if self.final else None

    @property
    def error(self) -> str | None:
        return next((t.error for t in self.turns if t.error), None)

    @property
    def model(self) -> str | None:
        return next((t.model for t in self.turns if t.model), None)

    @property
    def provider(self) -> str | None:
        return next((t.provider for t in self.turns if t.provider), None)
