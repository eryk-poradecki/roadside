"""Location context for the AI turn: one reverse lookup, mapped by the pure rules (ADR 0004)."""

from dataclasses import dataclass

from app.domain.ai_turn import Locale
from app.domain.incident import Location
from app.domain.location_context import LocationContext, derive_location
from app.integrations.nominatim import ReverseGeocoder


@dataclass(frozen=True, slots=True)
class ResolvedLocation:
    context: LocationContext
    label: str | None


class LocationResolver:
    """`geocoder` is None in demo mode, where no call is made."""

    def __init__(
        self,
        geocoder: ReverseGeocoder | None,
        *,
        max_gps_accuracy_m: float,
        max_road_distance_m: float,
    ) -> None:
        self._geocoder = geocoder
        self._max_gps_accuracy_m = max_gps_accuracy_m
        self._max_road_distance_m = max_road_distance_m

    async def resolve(self, location: Location, locale: Locale) -> ResolvedLocation | None:
        """None when there is no lookup or it failed: the caller uses unknown and caches nothing."""
        if self._geocoder is None:
            return None
        result = await self._geocoder.reverse(location.lat, location.lon, locale)
        if result is None:
            return None
        context, label = derive_location(
            result,
            location,
            max_gps_accuracy_m=self._max_gps_accuracy_m,
            max_road_distance_m=self._max_road_distance_m,
        )
        return ResolvedLocation(context, label)
