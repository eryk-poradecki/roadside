"""Photos (ADR 0002): what is stored, and the fixed pipeline every photo goes through."""

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

# The server pipeline's limit on the long edge (the client already sends at most 1600 px).
MAX_EDGE_PX = 2048
# Pixels decoded at most: a small file can still be a huge image (a decompression bomb).
MAX_PIXELS = 50_000_000

# Pillow format → what we store and serve. Everything else is refused.
_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
_JPEG_QUALITY = 85
# The long edge of a photo as sent to the model, for the request only (ADR 0002).
MODEL_EDGE_PX = 1024


@dataclass(frozen=True, slots=True)
class Photo:
    id: int
    incident_id: int
    stored_name: str
    content_type: str
    size_bytes: int
    width: int
    height: int
    sample_id: str | None
    created_at: str


@dataclass(frozen=True, slots=True)
class PreparedPhoto:
    """A photo after the pipeline: the bytes to write, with no metadata left in them."""

    data: bytes
    content_type: str
    width: int
    height: int


class UnsupportedImageError(Exception):
    """Not a JPEG, PNG or WebP that decodes (415)."""


class ImageTooLargeError(Exception):
    """Decodes to more pixels than the server will process (413)."""


def prepare_photo(data: bytes) -> PreparedPhoto:
    """decode → apply EXIF orientation → limit the long edge → re-encode without metadata.

    The order is fixed (ADR 0002): orientation must be applied before EXIF is dropped, or a
    portrait phone photo comes out sideways. Dropping EXIF also drops its GPS tag. The format
    is kept, verified by decoding rather than taken from the client's `Content-Type`.
    """
    try:
        opened = Image.open(BytesIO(data))
        content_type = _FORMATS.get(opened.format or "")
        if content_type is None:
            raise UnsupportedImageError(opened.format)
        width, height = opened.size
        if width * height > MAX_PIXELS:
            raise ImageTooLargeError(opened.size)
        opened.load()
        img = ImageOps.exif_transpose(opened)
    except Image.DecompressionBombError as exc:
        raise ImageTooLargeError(str(exc)) from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, EOFError) as exc:
        raise UnsupportedImageError(str(exc)) from exc

    img.thumbnail((MAX_EDGE_PX, MAX_EDGE_PX), Image.Resampling.LANCZOS)
    if content_type == "image/jpeg" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    # Pillow writes EXIF only when asked, but PNG carries `info` over (the ICC profile).
    clean = img.copy()
    clean.info = {}
    out = BytesIO()
    match content_type:
        case "image/jpeg":
            clean.save(out, "JPEG", quality=_JPEG_QUALITY, optimize=True)
        case "image/png":
            clean.save(out, "PNG", optimize=True)
        case _:
            clean.save(out, "WEBP", quality=_JPEG_QUALITY)
    return PreparedPhoto(out.getvalue(), content_type, clean.width, clean.height)


def downscale_for_model(data: bytes) -> bytes:
    """A stored photo as the model gets it: a JPEG with the long edge at most 1024 px.

    The stored file stays as it is. Stored photos already went through `prepare_photo`, so
    they are upright and carry no metadata. Raises `UnsupportedImageError` when the file does
    not decode.
    """
    try:
        opened = Image.open(BytesIO(data))
        opened.load()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, EOFError) as exc:
        raise UnsupportedImageError(str(exc)) from exc
    img: Image.Image = opened
    if img.mode not in ("RGB", "L"):
        # Flatten transparency onto white: a plain RGB convert turns it black.
        rgba = img.convert("RGBA")
        img = Image.new("RGB", rgba.size, "white")
        img.paste(rgba, mask=rgba.getchannel("A"))
    img.thumbnail((MODEL_EDGE_PX, MODEL_EDGE_PX), Image.Resampling.LANCZOS)
    out = BytesIO()
    img.save(out, "JPEG", quality=_JPEG_QUALITY)
    return out.getvalue()
