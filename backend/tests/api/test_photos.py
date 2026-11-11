"""Photos: one file per request, a fixed server pipeline, files on disk (ADR 0002, 0005)."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.db.migrate import migrate
from app.main import create_app
from app.repositories.photos import SqlitePhotoRepository
from app.settings import Settings
from tests.conftest import ORIGIN
from tests.images import GPS_IFD, ORIENTATION, ROTATE_90_CW, image_bytes, open_image

INC = "/api/v1/incidents"
MB = 1024 * 1024


@pytest.fixture
def live_settings(tmp_path: Path) -> Settings:
    """Demo mode off: file uploads are accepted. The model is never called here."""
    return Settings(
        database_path=tmp_path / "live.db",
        upload_dir=tmp_path / "uploads",
        frontend_origins=[ORIGIN],
        demo_mode=False,
        llm_base_url="http://llm.test/v1/",
        llm_api_key="test-key",
        llm_model="test-model",
    )


@pytest.fixture
def live_app(live_settings: Settings) -> FastAPI:
    migrate(live_settings.database_path)
    live_settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return create_app(live_settings)


@pytest.fixture
async def live(live_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=live_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def make_incident(client: httpx.AsyncClient) -> int:
    r = await client.post(INC, json={"problem_type": "pothole_damage"})
    assert r.status_code == 201, r.text
    return int(r.json()["id"])


async def upload(
    client: httpx.AsyncClient,
    incident_id: int,
    data: bytes | None = None,
    content_type: str = "image/jpeg",
    name: str = "photo.jpg",
) -> httpx.Response:
    body = image_bytes() if data is None else data
    return await client.post(
        f"{INC}/{incident_id}/photos", files={"file": (name, body, content_type)}
    )


async def attach_sample(
    client: httpx.AsyncClient, incident_id: int, sample_id: object
) -> httpx.Response:
    return await client.post(f"{INC}/{incident_id}/photos", json={"sample_id": sample_id})


async def stored_photos(client: httpx.AsyncClient, incident_id: int) -> list[Any]:
    r = await client.get(f"{INC}/{incident_id}")
    assert r.status_code == 200, r.text
    photos: list[Any] = r.json()["photos"]
    return photos


async def fetch(client: httpx.AsyncClient, url: str) -> bytes:
    r = await client.get(url)
    assert r.status_code == 200, r.text
    return r.content


def files_in(settings: Settings) -> list[Path]:
    return sorted(p for p in settings.upload_dir.iterdir() if p.is_file())


# --- adding and reading ---------------------------------------------------------------------


async def test_upload_stores_the_photo_and_the_incident_lists_it(
    live: httpx.AsyncClient, live_settings: Settings
) -> None:
    incident_id = await make_incident(live)

    r = await upload(live, incident_id, image_bytes(64, 48))

    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body) == {"id", "url", "content_type", "width", "height", "created_at"}
    assert body["url"] == f"/api/v1/photos/{body['id']}"
    assert r.headers["location"] == body["url"]
    assert body["content_type"] == "image/jpeg"
    assert (body["width"], body["height"]) == (64, 48)
    assert body["created_at"].endswith("Z")
    assert await stored_photos(live, incident_id) == [body]

    served = await live.get(body["url"])
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/jpeg"
    assert open_image(served.content).size == (64, 48)
    # Under a server-generated name, never the client's.
    [file] = files_in(live_settings)
    assert "photo" not in file.name
    assert file.read_bytes() == served.content


async def test_a_new_incident_has_no_photos(live: httpx.AsyncClient) -> None:
    incident_id = await make_incident(live)
    assert await stored_photos(live, incident_id) == []


async def test_photos_are_listed_in_upload_order(live: httpx.AsyncClient) -> None:
    incident_id = await make_incident(live)
    ids = [
        (await upload(live, incident_id, image_bytes(10 + i, 10))).json()["id"] for i in range(3)
    ]
    assert [p["id"] for p in await stored_photos(live, incident_id)] == ids


async def test_png_and_webp_keep_their_format(live: httpx.AsyncClient) -> None:
    incident_id = await make_incident(live)
    png = await upload(live, incident_id, image_bytes(fmt="PNG"), "image/png", "a.png")
    webp = await upload(live, incident_id, image_bytes(fmt="WEBP"), "image/webp", "a.webp")
    assert png.status_code == 201, png.text
    assert png.json()["content_type"] == "image/png"
    assert webp.status_code == 201, webp.text
    assert webp.json()["content_type"] == "image/webp"
    assert open_image(await fetch(live, webp.json()["url"])).format == "WEBP"


async def test_the_type_comes_from_decoding_not_the_header(live: httpx.AsyncClient) -> None:
    incident_id = await make_incident(live)
    r = await upload(live, incident_id, image_bytes(fmt="PNG"), "image/jpeg", "a.jpg")
    assert r.status_code == 201, r.text
    assert r.json()["content_type"] == "image/png"


async def test_unknown_incident_is_404(live: httpx.AsyncClient) -> None:
    r = await upload(live, 999)
    assert r.status_code == 404
    assert r.json()["reason"] == "not_found"


async def test_unknown_photo_is_404(live: httpx.AsyncClient) -> None:
    for r in (await live.get("/api/v1/photos/999"), await live.delete("/api/v1/photos/999")):
        assert r.status_code == 404
        assert r.json()["reason"] == "not_found"


# --- the gate -------------------------------------------------------------------------------


async def test_the_sixth_photo_is_409_photo_limit(
    live: httpx.AsyncClient, live_settings: Settings
) -> None:
    incident_id = await make_incident(live)
    for _ in range(5):
        assert (await upload(live, incident_id)).status_code == 201

    r = await upload(live, incident_id)

    assert r.status_code == 409
    assert r.json()["reason"] == "photo_limit"
    assert len(await stored_photos(live, incident_id)) == 5
    assert len(files_in(live_settings)) == 5


async def test_a_file_over_10_mb_is_413_photo_too_large(
    live: httpx.AsyncClient, live_settings: Settings
) -> None:
    incident_id = await make_incident(live)
    # Under the 12 MB body cap, over the 10 MB photo cap.
    r = await upload(live, incident_id, b"\xff" * (10 * MB + 1))
    assert r.status_code == 413
    assert r.json()["reason"] == "photo_too_large"
    assert await stored_photos(live, incident_id) == []
    assert files_in(live_settings) == []


async def test_a_small_file_that_decodes_to_too_many_pixels_is_413(
    live: httpx.AsyncClient,
) -> None:
    # 64 megapixels of one colour: a few hundred KB as PNG (a decompression bomb, mildly).
    data = image_bytes(8000, 8000, fmt="PNG", mode="L")
    assert len(data) < MB
    incident_id = await make_incident(live)
    r = await upload(live, incident_id, data, "image/png")
    assert r.status_code == 413
    assert r.json()["reason"] == "photo_too_large"


@pytest.mark.parametrize(
    ("data", "content_type"),
    [
        (b"just some text, not a picture", "text/plain"),
        # Claims to be a JPEG, but the bytes stop after the header.
        (image_bytes(fmt="JPEG")[:200], "image/jpeg"),
        # A real image, in a format the API doesn't take.
        (image_bytes(fmt="GIF", mode="L"), "image/gif"),
    ],
    ids=["not-an-image", "truncated-jpeg", "gif"],
)
async def test_a_non_image_or_undecodable_file_is_415(
    live: httpx.AsyncClient, live_settings: Settings, data: bytes, content_type: str
) -> None:
    incident_id = await make_incident(live)
    r = await upload(live, incident_id, data, content_type)
    assert r.status_code == 415
    assert r.json()["reason"] == "unsupported_media_type"
    assert await stored_photos(live, incident_id) == []
    assert files_in(live_settings) == []


async def test_a_body_that_is_neither_multipart_nor_json_is_415(live: httpx.AsyncClient) -> None:
    incident_id = await make_incident(live)
    r = await live.post(
        f"{INC}/{incident_id}/photos", content=image_bytes(), headers={"Content-Type": "image/jpeg"}
    )
    assert r.status_code == 415
    assert r.json()["reason"] == "unsupported_media_type"


async def test_a_multipart_body_without_a_file_is_422(live: httpx.AsyncClient) -> None:
    incident_id = await make_incident(live)
    r = await live.post(f"{INC}/{incident_id}/photos", data={"other": "x"}, files={"x": b""})
    assert r.status_code == 422
    assert r.json()["errors"] == [{"field": "file", "message": "A file is required"}]


# --- the pipeline ---------------------------------------------------------------------------


async def test_exif_orientation_is_applied_and_metadata_stripped(live: httpx.AsyncClient) -> None:
    incident_id = await make_incident(live)
    # Stored landscape with "rotate 90 CW", as a phone held upright writes it, and a GPS tag.
    data = image_bytes(80, 40, orientation=ROTATE_90_CW, gps=True)
    assert open_image(data).getexif().get_ifd(GPS_IFD)

    r = await upload(live, incident_id, data)

    assert r.status_code == 201, r.text
    assert (r.json()["width"], r.json()["height"]) == (40, 80)
    img = open_image(await fetch(live, r.json()["url"]))
    assert img.size == (40, 80)
    # The blue marker was top-left before the turn, so it is top-right after it.
    red, _, blue = img.convert("RGB").getpixel((35, 4))  # type: ignore[misc]
    assert blue > 200 > red
    exif = img.getexif()
    assert ORIENTATION not in exif
    assert not exif.get_ifd(GPS_IFD)
    assert len(exif) == 0
    assert "exif" not in img.info


@pytest.mark.parametrize("fmt", ["JPEG", "PNG", "WEBP"])
async def test_no_metadata_survives_in_any_format(live: httpx.AsyncClient, fmt: str) -> None:
    incident_id = await make_incident(live)
    data = image_bytes(fmt=fmt, orientation=1, gps=True, icc=True)
    sent = open_image(data)
    assert "icc_profile" in sent.info
    assert sent.getexif().get_ifd(GPS_IFD)

    r = await upload(live, incident_id, data, f"image/{fmt.lower()}")

    assert r.status_code == 201, r.text
    img = open_image(await fetch(live, r.json()["url"]))
    assert len(img.getexif()) == 0
    assert "icc_profile" not in img.info
    assert "exif" not in img.info


async def test_the_long_edge_is_limited_to_2048_px(live: httpx.AsyncClient) -> None:
    incident_id = await make_incident(live)
    for size, expected in (((3000, 1000), (2048, 683)), ((900, 2400), (768, 2048))):
        r = await upload(live, incident_id, image_bytes(*size))
        assert r.status_code == 201, r.text
        assert (r.json()["width"], r.json()["height"]) == expected
        assert open_image(await fetch(live, r.json()["url"])).size == expected


async def test_a_small_photo_is_not_enlarged(live: httpx.AsyncClient) -> None:
    incident_id = await make_incident(live)
    r = await upload(live, incident_id, image_bytes(2048, 30))
    assert (r.json()["width"], r.json()["height"]) == (2048, 30)


# --- deleting -------------------------------------------------------------------------------


async def test_deleting_a_photo_removes_the_row_and_the_file(
    live: httpx.AsyncClient, live_settings: Settings
) -> None:
    incident_id = await make_incident(live)
    keep = (await upload(live, incident_id)).json()
    gone = (await upload(live, incident_id)).json()
    assert len(files_in(live_settings)) == 2

    r = await live.delete(gone["url"])

    assert r.status_code == 204
    assert (await live.get(gone["url"])).status_code == 404
    assert await stored_photos(live, incident_id) == [keep]
    assert len(files_in(live_settings)) == 1
    assert (await live.delete(gone["url"])).status_code == 404
    # A freed slot can be used again.
    for _ in range(4):
        assert (await upload(live, incident_id)).status_code == 201


async def test_deleting_the_incident_removes_its_photos_and_files(
    live: httpx.AsyncClient, live_settings: Settings
) -> None:
    incident_id = await make_incident(live)
    other_id = await make_incident(live)
    urls = [(await upload(live, incident_id)).json()["url"] for _ in range(3)]
    other = (await upload(live, other_id)).json()

    assert (await live.delete(f"{INC}/{incident_id}")).status_code == 204

    for url in urls:
        assert (await live.get(url)).status_code == 404
    assert len(files_in(live_settings)) == 1
    assert await stored_photos(live, other_id) == [other]


async def test_a_photo_whose_file_is_gone_is_404_and_still_deletable(
    live: httpx.AsyncClient, live_settings: Settings
) -> None:
    incident_id = await make_incident(live)
    url = (await upload(live, incident_id)).json()["url"]
    for f in files_in(live_settings):
        f.unlink()
    assert (await live.get(url)).status_code == 404
    assert (await live.delete(url)).status_code == 204


async def test_a_failed_commit_removes_the_written_file(
    live: httpx.AsyncClient, live_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    incident_id = await make_incident(live)

    async def broken_insert(*args: object, **kwargs: object) -> int:
        raise RuntimeError("disk full")

    monkeypatch.setattr(SqlitePhotoRepository, "insert", broken_insert)
    with pytest.raises(RuntimeError, match="disk full"):
        await upload(live, incident_id)

    assert files_in(live_settings) == []
    monkeypatch.undo()
    assert await stored_photos(live, incident_id) == []


# --- demo mode: sample photos instead of uploads --------------------------------------------


async def test_demo_mode_refuses_file_uploads_with_403(
    client: httpx.AsyncClient, settings: Settings
) -> None:
    incident_id = await make_incident(client)
    r = await upload(client, incident_id)
    assert r.status_code == 403
    assert r.json()["reason"] == "demo_uploads_disabled"
    assert await stored_photos(client, incident_id) == []


async def test_config_lists_the_sample_photos(client: httpx.AsyncClient) -> None:
    samples = (await client.get("/api/v1/config")).json()["sample_photos"]
    assert len(samples) >= 2
    for s in samples:
        assert set(s) == {"id", "url", "title", "credit"}
        assert s["url"] == f"/api/v1/sample-photos/{s['id']}"
        assert s["title"]
        assert s["credit"]
        r = await client.get(s["url"])
        assert r.status_code == 200, s
        assert r.headers["content-type"] == "image/jpeg"
        assert max(open_image(r.content).size) <= 2048


async def test_an_unknown_sample_photo_file_is_404(client: httpx.AsyncClient) -> None:
    for sample_id in ("nope", "..%2Fsettings.py"):
        r = await client.get(f"/api/v1/sample-photos/{sample_id}")
        assert r.status_code == 404
        assert r.json()["reason"] == "not_found"


async def test_a_known_sample_is_copied_in_as_an_ordinary_photo(
    client: httpx.AsyncClient, settings: Settings
) -> None:
    sample = (await client.get("/api/v1/config")).json()["sample_photos"][0]
    incident_id = await make_incident(client)

    r = await attach_sample(client, incident_id, sample["id"])

    assert r.status_code == 201, r.text
    photo = r.json()
    assert photo["url"] == f"/api/v1/photos/{photo['id']}"
    assert r.headers["location"] == photo["url"]
    assert await stored_photos(client, incident_id) == [photo]
    assert len(files_in(settings)) == 1
    served = open_image(await fetch(client, photo["url"]))
    assert served.size == (photo["width"], photo["height"])

    # Deleted like any other photo.
    assert (await client.delete(photo["url"])).status_code == 204
    assert files_in(settings) == []
    # The bundled sample itself is untouched.
    assert (await client.get(sample["url"])).status_code == 200


async def test_an_unknown_sample_id_is_422_unknown_sample(client: httpx.AsyncClient) -> None:
    incident_id = await make_incident(client)
    r = await attach_sample(client, incident_id, "nope")
    assert r.status_code == 422
    body = r.json()
    assert body["reason"] == "unknown_sample"
    assert body["errors"] == [{"field": "sample_id", "message": "Unknown sample photo"}]


@pytest.mark.parametrize("body", [{}, {"sample_id": 3}, {"sample_id": "x", "extra": 1}, "[]"])
async def test_an_invalid_sample_body_is_422(client: httpx.AsyncClient, body: object) -> None:
    incident_id = await make_incident(client)
    url = f"{INC}/{incident_id}/photos"
    r = await (
        client.post(url, content=body, headers={"Content-Type": "application/json"})
        if isinstance(body, str)
        else client.post(url, json=body)
    )
    assert r.status_code == 422
    assert r.json()["reason"] == "validation_error"


async def test_sample_photos_count_towards_the_limit(client: httpx.AsyncClient) -> None:
    sample_id = (await client.get("/api/v1/config")).json()["sample_photos"][0]["id"]
    incident_id = await make_incident(client)
    for _ in range(5):
        assert (await attach_sample(client, incident_id, sample_id)).status_code == 201
    r = await attach_sample(client, incident_id, sample_id)
    assert r.status_code == 409
    assert r.json()["reason"] == "photo_limit"


async def test_sample_on_unknown_incident_is_404(client: httpx.AsyncClient) -> None:
    sample_id = (await client.get("/api/v1/config")).json()["sample_photos"][0]["id"]
    r = await attach_sample(client, 999, sample_id)
    assert r.status_code == 404
