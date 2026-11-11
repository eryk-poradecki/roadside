from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.nearby import (
    MAX_PLACES,
    RADIUS_KM_MAX,
    RADIUS_KM_MIN,
    NearbyCategory,
    NearbySnapshot,
    OsmType,
    Place,
)


class NearbyRequest(BaseModel):
    """5 km first; 25 km when the driver asks to search wider."""

    model_config = ConfigDict(extra="forbid")

    radius_km: Annotated[int, Field(strict=True, ge=RADIUS_KM_MIN, le=RADIUS_KM_MAX)]


class PlaceRead(BaseModel):
    """A real place from OpenStreetMap, never from the model."""

    osm_type: OsmType
    osm_id: int
    category: NearbyCategory
    name: str | None
    lat: float
    lon: float
    distance_m: int
    phone: str | None
    # The raw OSM `opening_hours`; the UI shows only `24/7` and the same hours every day.
    opening_hours: str | None

    @classmethod
    def from_domain(cls, p: Place) -> "PlaceRead":
        return cls(
            osm_type=p.osm_type,
            osm_id=p.osm_id,
            category=p.category,
            name=p.name,
            lat=p.lat,
            lon=p.lon,
            distance_m=p.distance_m,
            phone=p.phone,
            opening_hours=p.opening_hours,
        )


class NearbyRead(BaseModel):
    """The last successful lookup. `none` is a success: nothing within the radius."""

    status: Literal["found", "none"]
    places: Annotated[list[PlaceRead], Field(max_length=MAX_PLACES)]
    radius_km: int
    fetched_at: str

    @classmethod
    def from_domain(cls, s: NearbySnapshot) -> "NearbyRead":
        return cls(
            status=s.status,
            places=[PlaceRead.from_domain(p) for p in s.places],
            radius_km=s.radius_km,
            fetched_at=s.fetched_at,
        )
