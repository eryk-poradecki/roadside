"""Small images built in memory, for the photo pipeline tests."""

from io import BytesIO

from PIL import Image, ImageCms

# EXIF tags (Pillow's ExifTags.Base): Orientation and the GPS IFD pointer.
ORIENTATION = 0x0112
GPS_IFD = 0x8825
# "Rotate 90 CW to display": a phone held upright writes this.
ROTATE_90_CW = 6


def image_bytes(
    width: int = 64,
    height: int = 48,
    fmt: str = "JPEG",
    *,
    orientation: int | None = None,
    gps: bool = False,
    icc: bool = False,
    mode: str = "RGB",
) -> bytes:
    """An image file in `fmt`, optionally with an EXIF orientation, a GPS tag and an ICC
    profile."""
    img = Image.new(mode, (width, height), "red" if mode != "L" else 128)
    # A marker in the top-left corner, so a test can tell which way the pixels were turned.
    img.paste("blue" if mode != "L" else 0, (0, 0, width // 4, height // 4))
    exif = Image.Exif()
    if orientation is not None:
        exif[ORIENTATION] = orientation
    if gps:
        exif.get_ifd(GPS_IFD)[2] = (52.0, 13.0, 0.0)  # GPSLatitude
    out = BytesIO()
    kwargs: dict[str, object] = {"exif": exif} if len(exif) or gps else {}
    if icc:
        kwargs["icc_profile"] = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    img.save(out, fmt, **kwargs)
    return out.getvalue()


def open_image(data: bytes) -> Image.Image:
    img = Image.open(BytesIO(data))
    img.load()
    return img
