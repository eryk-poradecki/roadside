from datetime import UTC, datetime, timedelta

from app.services import clock


def test_now_is_the_real_time_by_default() -> None:
    assert abs(clock.now() - datetime.now(UTC)) < timedelta(seconds=1)


def test_a_shifted_clock_starts_at_the_given_moment_and_keeps_running() -> None:
    at = datetime(2026, 11, 12, 20, 30, tzinfo=UTC)

    with clock.shifted_to(at):
        first = clock.now()
        second = clock.now()
        stamp = clock.utc_now()

    assert abs(first - at) < timedelta(seconds=1)
    assert second >= first
    assert stamp.startswith("2026-11-12T20:3")
    assert abs(clock.now() - datetime.now(UTC)) < timedelta(seconds=1)
