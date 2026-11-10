"""Location context for the AI turn: one reverse lookup, mapped by the pure rules (ADR 0004)."""

from dataclasses import dataclass, replace

import aiosqlite

from app.db.connection import transaction
from app.domain.ai_turn import Locale
from app.domain.incident import Incident, Location
from app.domain.location_context import LocationContext, derive_location
from app.integrations.nominatim import ReverseGeocoder
from app.repositories.incidents import IncidentRepository
from app.services.clock import utc_now


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


async def refresh_location_context(
    conn: aiosqlite.Connection,
    incidents: IncidentRepository,
    resolver: LocationResolver,
    incident: Incident,
    locale: Locale,
) -> Incident:
    """Look the context up for the incident's location and cache it with the label.

    Runs outside any transaction, so no write lock is held during the lookup. A failed lookup
    caches nothing. Returns the incident as stored, or unchanged when nothing was written.
    """
    if incident.location is None:
        return incident
    resolved = await resolver.resolve(incident.location, locale)
    if resolved is None:
        return incident
    async with transaction(conn):
        current = await incidents.get(incident.id)
        # A PATCH may have moved or deleted the incident during the lookup.
        if current is None or current.location != incident.location:
            return incident
        updated = replace(current, location_context=resolved.context, location_label=resolved.label)
        await incidents.update(updated, utc_now())
    return updated
