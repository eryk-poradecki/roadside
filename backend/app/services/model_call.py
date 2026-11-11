"""One model call with validation and at most one repair call (ADR 0004, 0009).

Shared by the AI turn and the damage report: both send one schema-constrained request, validate
the raw text with Pydantic, and on failure make one repair call with the error appended.
"""

import logging
from collections.abc import Callable
from dataclasses import replace

from pydantic import ValidationError

from app.errors import AppError
from app.integrations.llm.base import (
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMResult,
    ProviderTimeoutError,
)
from app.integrations.llm.replay import NoRecordingError

logger = logging.getLogger(__name__)


class InvalidOutputError(Exception):
    """The output was invalid twice: once, and again after the repair call."""


def problem_for(exc: BaseException) -> AppError:
    """The problem a failed model call answers with."""
    if isinstance(exc, TimeoutError | ProviderTimeoutError):
        return AppError(504, "timeout", "The assistant did not answer in time")
    if isinstance(exc, NoRecordingError):
        # Demo mode: a labelled fallback, never another scenario's answer (ADR 0004).
        return AppError(503, "no_recording", "No recorded answer for this case in demo mode")
    if isinstance(exc, InvalidOutputError):
        return AppError(502, "invalid_output", "The assistant's answer was not valid")
    return AppError(502, "provider_error", "The assistant could not be reached")


def _repair_message(error: Exception) -> str:
    detail = (
        "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or 'output'}: {e['msg']}"
            for e in error.errors(include_url=False)
        )
        if isinstance(error, ValidationError)
        else str(error)
    )
    return (
        f"Your previous output was invalid: {detail}. "
        "Reply again with one corrected JSON object that follows the schema, and nothing else."
    )


async def complete_validated[T](
    provider: LLMProvider, request: LLMRequest, validate: Callable[[str], T]
) -> tuple[T, LLMResult]:
    """Raises `ProviderError` from the provider, or `InvalidOutputError` after a failed repair.

    `validate` raises ValueError (pydantic's included) for an invalid output.
    """
    result = await provider.complete(request)
    try:
        return validate(result.text), result
    except ValueError as exc:
        logger.info("model output invalid, making the one repair call")
        repair = replace(
            request,
            messages=(
                *request.messages,
                LLMMessage("assistant", result.text),
                LLMMessage("user", _repair_message(exc)),
            ),
        )
    result = await provider.complete(repair)
    try:
        return validate(result.text), result
    except ValueError as exc:
        raise InvalidOutputError from exc
