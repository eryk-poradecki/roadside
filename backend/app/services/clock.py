from datetime import UTC, datetime


def utc_now() -> str:
    """ISO 8601 UTC with milliseconds and `Z`, so text order is time order (ADR 0006)."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
