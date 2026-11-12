"""Bundled sample photos (ADR 0002): what demo mode attaches instead of an upload.

Each is freely licensed and credited in `docs/ATTRIBUTION.md`. The ids are stable: the demo's
replay key includes them (#58).
"""

from dataclasses import dataclass
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "assets" / "sample_photos"


@dataclass(frozen=True, slots=True)
class SamplePhoto:
    id: str
    file: str
    # English; the frontend translates by id.
    title: str
    credit: str

    @property
    def path(self) -> Path:
        return SAMPLES_DIR / self.file


SAMPLE_PHOTOS: tuple[SamplePhoto, ...] = (
    SamplePhoto(
        id="flat_tyre",
        file="flat_tyre.jpg",
        title="Flat front tyre",
        credit="Pujanak, public domain, via Wikimedia Commons",
    ),
    SamplePhoto(
        id="screw_in_tread",
        file="screw_in_tread.jpg",
        title="Screw in the tyre tread",
        credit="Godstar23, CC0, via Wikimedia Commons",
    ),
    SamplePhoto(
        id="pothole",
        file="pothole.jpg",
        title="Deep pothole in the road",
        credit="Роман Рябенко, CC0, via Wikimedia Commons",
    ),
    SamplePhoto(
        id="empty_fuel_gauge",
        file="empty_fuel_gauge.jpg",
        title="Fuel gauge on empty",
        credit="BrokenSphere, CC BY-SA 3.0, via Wikimedia Commons",
    ),
    SamplePhoto(
        id="rim_damage",
        file="rim_damage.jpg",
        title="Chipped rim and a deflated tyre",
        credit="Hazel Nicholson, CC BY 2.0, via Flickr",
    ),
)

_BY_ID = {s.id: s for s in SAMPLE_PHOTOS}


def find_sample(sample_id: str) -> SamplePhoto | None:
    return _BY_ID.get(sample_id)
