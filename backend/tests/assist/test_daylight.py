from datetime import UTC, datetime

import pytest

from app.assist.daylight import is_dark, solar_elevation_deg

WARSAW = (52.23, 21.01)


@pytest.mark.parametrize(
    ("when", "dark"),
    [
        (datetime(2026, 6, 21, 10, 0, tzinfo=UTC), False),  # midsummer noon
        (datetime(2026, 11, 10, 10, 30, tzinfo=UTC), False),  # November late morning
        # Sunset in Warsaw on 10 Nov 2026 is about 14:55 UTC (15:55 local).
        (datetime(2026, 11, 10, 14, 30, tzinfo=UTC), False),
        (datetime(2026, 11, 10, 15, 30, tzinfo=UTC), True),
        (datetime(2026, 11, 10, 23, 0, tzinfo=UTC), True),
        # Midsummer sunset in Warsaw is about 19:00 UTC (21:00 local).
        (datetime(2026, 6, 21, 19, 30, tzinfo=UTC), True),
        (datetime(2026, 6, 21, 18, 30, tzinfo=UTC), False),
    ],
)
def test_dark_follows_the_sun_in_warsaw(when: datetime, dark: bool) -> None:
    assert is_dark(when, *WARSAW) is dark


def test_noon_elevation_is_plausible() -> None:
    # Warsaw at the June solstice: about 90 - 52.2 + 23.4 = 61 degrees at solar noon.
    elevation = solar_elevation_deg(datetime(2026, 6, 21, 10, 35, tzinfo=UTC), *WARSAW)
    assert 59 < elevation < 63
