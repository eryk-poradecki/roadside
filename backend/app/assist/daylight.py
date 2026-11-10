"""Is it dark where the driver is? A pure solar-elevation estimate (NOAA approximation).

The coordinates are used here only; the model gets the resulting `dark` hint, never them.
"""

import math
from datetime import UTC, datetime

# Geographic centre of Poland, for incidents without a location.
POLAND_CENTRE = (52.0, 19.0)
# The sun's upper edge at the horizon, with refraction: below this it has set.
_SUNSET_ELEVATION_DEG = -0.833


def solar_elevation_deg(when: datetime, lat: float, lon: float) -> float:
    t = when.astimezone(UTC)
    day = t.timetuple().tm_yday
    hours = t.hour + t.minute / 60 + t.second / 3600
    g = 2 * math.pi / 365 * (day - 1 + (hours - 12) / 24)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(g)
        - 0.032077 * math.sin(g)
        - 0.014615 * math.cos(2 * g)
        - 0.040849 * math.sin(2 * g)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(g)
        + 0.070257 * math.sin(g)
        - 0.006758 * math.cos(2 * g)
        + 0.000907 * math.sin(2 * g)
        - 0.002697 * math.cos(3 * g)
        + 0.00148 * math.sin(3 * g)
    )
    true_solar_minutes = hours * 60 + eqtime + 4 * lon
    hour_angle = math.radians(true_solar_minutes / 4 - 180)
    phi = math.radians(lat)
    cos_zenith = math.sin(phi) * math.sin(decl) + math.cos(phi) * math.cos(decl) * math.cos(
        hour_angle
    )
    zenith = math.degrees(math.acos(max(-1.0, min(1.0, cos_zenith))))
    return 90 - zenith


def is_dark(when: datetime, lat: float, lon: float) -> bool:
    return solar_elevation_deg(when, lat, lon) < _SUNSET_ELEVATION_DEG
