"""The LLM transport seam (ADR 0004).

A provider only moves a request to a model and the raw text back. Prompts, the vehicle fact
block, validation, the repair call and the turn budget live in the assistant service, so
every provider goes through the same pipeline.
"""

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass(frozen=True, slots=True)
class LLMImage:
    media_type: str
    data_b64: str


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: Literal["system", "user", "assistant"]
    text: str
    images: tuple[LLMImage, ...] = ()


@dataclass(frozen=True, slots=True)
class LLMRequest:
    messages: tuple[LLMMessage, ...]
    # The JSON schema the output must follow, sent as a structured-output constraint.
    schema: dict[str, Any]
    schema_name: str
    # Built by the service for the replay provider; live providers ignore it.
    replay_key: str | None = None


@dataclass(frozen=True, slots=True)
class LLMResult:
    text: str
    provider: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)


class ProviderError(Exception):
    """The model could not be reached or refused the request (502 `provider_error`)."""


class ProviderTimeoutError(ProviderError):
    """The model did not answer within the read timeout (504 `timeout`)."""


class LLMProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def vision(self) -> bool: ...

    @property
    def max_images(self) -> int: ...

    async def complete(self, request: LLMRequest) -> LLMResult: ...

    async def aclose(self) -> None: ...
