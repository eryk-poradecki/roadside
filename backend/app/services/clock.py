"""The app's notion of now.

A recording run (#63) shifts it to the time of day a demo scenario happens at, so `dark` and
the local time the model is told agree with the scenario, whatever the hour of the run. The
shift is a context variable: it never leaks into another request.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta

_offset: ContextVar[timedelta] = ContextVar("clock_offset", default=timedelta(0))


def now() -> datetime:
    return datetime.now(UTC) + _offset.get()


def utc_now() -> str:
    """ISO 8601 UTC with milliseconds and `Z`, so text order is time order (ADR 0006)."""
    return now().isoformat(timespec="milliseconds").replace("+00:00", "Z")


def real_utc_now() -> str:
    """`utc_now` ignoring any shift: when a recording was really made."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@contextmanager
def shifted_to(at: datetime) -> Iterator[None]:
    """Run the clock from `at` instead of the real time; it keeps ticking from there."""
    token = _offset.set(at - datetime.now(UTC))
    try:
        yield
    finally:
        _offset.reset(token)
