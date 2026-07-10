#!/usr/bin/env python3
"""Deterministically replace selected PDF pages with scan-like page images.

The public API is :func:`rasterize_pdf_pages`.  Page numbers are one-based and
each selected page has its own explicit :class:`ScanProfile`.  Non-selected
pages are copied from the source PDF without rendering.

Example::

    rasterize_pdf_pages(
        "native.pdf",
        "mixed.pdf",
        {
            2: ScanProfile(seed=2202, color_mode="grayscale"),
            5: ScanProfile(seed=2205, color_mode="color", skew_degrees=-0.18),
        },
    )

The implementation intentionally has no network or model-provider dependency.
It requires Poppler's ``pdftoppm`` executable plus the repository's Python
dependencies (Pillow, pypdf, and ReportLab).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, fields
from io import BytesIO
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
from typing import Any, Mapping

from PIL import Image, ImageChops, ImageEnhance, ImageFilter
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas


MIN_EFFECTIVE_DPI = 120.0
_METADATA_KEYS = (
    "/Title",
    "/Author",
    "/Subject",
    "/Keywords",
    "/Creator",
    "/Producer",
    "/CreationDate",
    "/ModDate",
)
_LIBRARY_MARKERS = (
    "ghostscript",
    "pillow",
    "poppler",
    "pypdf",
    "reportlab",
)
_DEFAULT_CREATOR = "Document imaging workflow"
_DEFAULT_PRODUCER = "Enterprise Document Services"


@dataclass(frozen=True, slots=True)
class ScanProfile:
    """A bounded, human-readable scan-degradation profile for one page."""

    seed: int
    color_mode: str = "grayscale"
    dpi: int = 144
    skew_degrees: float = 0.22
    noise_level: float = 1.8
    blur_radius: float = 0.22
    jpeg_quality: int = 88
    contrast: float = 1.03
    brightness: float = 1.0

    def __post_init__(self) -> None:
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("seed must be an integer")
        if self.color_mode not in {"grayscale", "color"}:
            raise ValueError("color_mode must be 'grayscale' or 'color'")
        if isinstance(self.dpi, bool) or not isinstance(self.dpi, int) or not 120 <= self.dpi <= 300:
            raise ValueError("dpi must be an integer from 120 through 300")
        if not 0.05 <= abs(self.skew_degrees) <= 0.75:
            raise ValueError("skew_degrees must be slightly non-zero (absolute value 0.05 through 0.75)")
        if not 0.25 <= self.noise_level <= 5.0:
            raise ValueError("noise_level must be from 0.25 through 5.0")
        if not 0.05 <= self.blur_radius <= 0.65:
            raise ValueError("blur_radius must be from 0.05 through 0.65")
        if isinstance(self.jpeg_quality, bool) or not isinstance(self.jpeg_quality, int):
            raise TypeError("jpeg_quality must be an integer")
        if not 65 <= self.jpeg_quality <= 95:
            raise ValueError("jpeg_quality must be from 65 through 95")
        if not 0.88 <= self.contrast <= 1.16:
            raise ValueError("contrast must be from 0.88 through 1.16")
        if not 0.94 <= self.brightness <= 1.06:
            raise ValueError("brightness must be from 0.94 through 1.06")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ScanProfile":
        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(f"unknown scan-profile field(s): {', '.join(unknown)}")
        return cls(**dict(value))


def _library_safe(value: str) -> bool:
    normalized = value.casefold()
    return not any(marker in normalized for marker in _LIBRARY_MARKERS)


def _controlled_metadata(
    reader: PdfReader,
    overrides: Mapping[str, str] | None,
) -> dict[str, str]:
    """Copy only stable public metadata, replacing library-identifying values."""

    source = reader.metadata or {}
    metadata: dict[str, str] = {}
    for key in _METADATA_KEYS:
        raw = source.get(key)
        if raw is None:
            continue
        value = str(raw)
        if value and _library_safe(value):
            metadata[key] = value

    metadata.setdefault("/Creator", _DEFAULT_CREATOR)
    metadata.setdefault("/Producer", _DEFAULT_PRODUCER)

    for raw_key, raw_value in (overrides or {}).items():
        key = raw_key if raw_key.startswith("/") else f"/{raw_key}"
        if key not in _METADATA_KEYS:
            raise ValueError(f"unsupported PDF metadata key: {raw_key}")
        if not isinstance(raw_value, str) or not raw_value:
            raise ValueError(f"PDF metadata value for {key} must be a non-empty string")
        if not _library_safe(raw_value):
            raise ValueError(f"PDF metadata value for {key} exposes an implementation library")
        metadata[key] = raw_value

    # PdfWriter starts with its own library-identifying producer.  Keeping
    # these keys explicit guarantees that value can never reach the artifact.
    metadata.setdefault("/Creator", _DEFAULT_CREATOR)
    metadata.setdefault("/Producer", _DEFAULT_PRODUCER)
    return {key: metadata[key] for key in _METADATA_KEYS if key in metadata}


def _render_page(
    snapshot_path: Path,
    page_number: int,
    profile: ScanProfile,
    work_dir: Path,
) -> Image.Image:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise RuntimeError("pdftoppm is required; install Poppler before rasterizing benchmark pages")
    prefix = work_dir / f"page-{page_number:04d}"
    result = subprocess.run(
        [
            pdftoppm,
            "-f",
            str(page_number),
            "-l",
            str(page_number),
            "-singlefile",
            "-r",
            str(profile.dpi),
            "-png",
            str(snapshot_path),
            str(prefix),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    png_path = prefix.with_suffix(".png")
    if result.returncode != 0 or not png_path.is_file():
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise RuntimeError(f"Poppler failed to render page {page_number}: {detail}")
    with Image.open(png_path) as rendered:
        rendered.load()
        if rendered.mode == "RGBA":
            flattened = Image.new("RGB", rendered.size, (249, 249, 247))
            flattened.paste(rendered, mask=rendered.getchannel("A"))
            return flattened
        return rendered.convert("RGB")


def _add_seeded_noise(image: Image.Image, profile: ScanProfile) -> Image.Image:
    rng = random.Random(profile.seed)
    raw = Image.frombytes("L", image.size, rng.randbytes(image.width * image.height))
    amplitude = profile.noise_level
    lut = [max(0, min(255, round(128 + ((value - 127.5) / 127.5) * amplitude))) for value in range(256)]
    noise = raw.point(lut)
    if image.mode == "RGB":
        noise = Image.merge("RGB", (noise, noise, noise))
    return ImageChops.add(image, noise, scale=1.0, offset=-128)


def _degrade(rendered: Image.Image, profile: ScanProfile) -> bytes:
    if profile.color_mode == "grayscale":
        image = rendered.convert("L")
        fill: int | tuple[int, int, int] = 247
    else:
        image = ImageEnhance.Color(rendered.convert("RGB")).enhance(0.92)
        fill = (249, 248, 245)

    image = image.rotate(
        profile.skew_degrees,
        resample=Image.Resampling.BICUBIC,
        expand=False,
        fillcolor=fill,
    )
    image = _add_seeded_noise(image, profile)
    image = ImageEnhance.Contrast(image).enhance(profile.contrast)
    image = ImageEnhance.Brightness(image).enhance(profile.brightness)
    image = image.filter(ImageFilter.GaussianBlur(profile.blur_radius))

    jpeg = BytesIO()
    image.save(
        jpeg,
        format="JPEG",
        quality=profile.jpeg_quality,
        optimize=False,
        progressive=False,
        subsampling=0,
    )
    return jpeg.getvalue()


def _display_size(page: Any) -> tuple[float, float]:
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    rotation = int(page.rotation or 0) % 360
    return (height, width) if rotation in {90, 270} else (width, height)


def _assert_effective_dpi(image: Image.Image, page: Any, page_number: int) -> None:
    display_width, display_height = _display_size(page)
    effective = min(image.width * 72.0 / display_width, image.height * 72.0 / display_height)
    if effective + 1e-6 < MIN_EFFECTIVE_DPI:
        raise ValueError(
            f"page {page_number} rendered at only {effective:.2f} effective DPI; "
            f"at least {MIN_EFFECTIVE_DPI:.0f} is required"
        )


def _normalize_box(box: Any, media_box: Any) -> RectangleObject:
    left = float(box.left) - float(media_box.left)
    bottom = float(box.bottom) - float(media_box.bottom)
    right = float(box.right) - float(media_box.left)
    top = float(box.top) - float(media_box.bottom)
    return RectangleObject([left, bottom, right, top])


def _raster_page(jpeg_bytes: bytes, source_page: Any) -> Any:
    width = float(source_page.mediabox.width)
    height = float(source_page.mediabox.height)
    rotation = int(source_page.rotation or 0) % 360

    # Poppler renders the displayed orientation.  Counter-rotate the pixels in
    # page coordinates, then retain /Rotate, so rotated source pages stay the
    # same physical size and display orientation.
    with Image.open(BytesIO(jpeg_bytes)) as decoded:
        decoded.load()
        raw_orientation = decoded.rotate(rotation, expand=True) if rotation else decoded.copy()
    normalized_jpeg = BytesIO()
    raw_orientation.save(
        normalized_jpeg,
        format="JPEG",
        quality=95,
        optimize=False,
        progressive=False,
        subsampling=0,
    )
    normalized_jpeg.seek(0)

    page_pdf = BytesIO()
    canvas = Canvas(page_pdf, pagesize=(width, height), invariant=1, pageCompression=1)
    canvas.drawImage(ImageReader(normalized_jpeg), 0, 0, width=width, height=height, mask=None)
    canvas.showPage()
    canvas.save()
    page_pdf.seek(0)
    page = PdfReader(page_pdf).pages[0]

    original_media = source_page.mediabox
    for name in ("cropbox", "trimbox", "bleedbox", "artbox"):
        setattr(page, name, _normalize_box(getattr(source_page, name), original_media))
    if rotation:
        page.rotate(rotation)
    return page


def _atomic_write(writer: PdfWriter, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            writer.write(stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, destination)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise


def rasterize_pdf_pages(
    source_pdf: str | os.PathLike[str],
    output_pdf: str | os.PathLike[str],
    page_profiles: Mapping[int, ScanProfile],
    *,
    metadata: Mapping[str, str] | None = None,
) -> None:
    """Replace selected pages with deterministic scan-like, image-only pages.

    ``page_profiles`` maps one-based page numbers to explicit profiles.  The
    output is atomically replaced only after every page has been processed.
    Source and destination may be the same path.
    """

    source = Path(source_pdf).expanduser().resolve()
    destination = Path(output_pdf).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"source PDF does not exist: {source}")
    if not page_profiles:
        raise ValueError("at least one page profile is required")
    for page_number, profile in page_profiles.items():
        if isinstance(page_number, bool) or not isinstance(page_number, int) or page_number < 1:
            raise ValueError(f"page number must be a positive one-based integer: {page_number!r}")
        if not isinstance(profile, ScanProfile):
            raise TypeError(f"page {page_number} profile must be a ScanProfile")

    source_bytes = source.read_bytes()
    reader = PdfReader(BytesIO(source_bytes))
    page_count = len(reader.pages)
    invalid = sorted(page for page in page_profiles if page > page_count)
    if invalid:
        raise ValueError(f"selected page(s) exceed the {page_count}-page source: {invalid}")
    controlled_metadata = _controlled_metadata(reader, metadata)

    destination.parent.mkdir(parents=True, exist_ok=True)
    raster_pages: dict[int, Any] = {}
    with tempfile.TemporaryDirectory(
        dir=destination.parent,
        prefix=f".{destination.name}.render-",
    ) as temporary_name:
        work_dir = Path(temporary_name)
        snapshot = work_dir / "source.pdf"
        snapshot.write_bytes(source_bytes)
        for page_number in sorted(page_profiles):
            profile = page_profiles[page_number]
            rendered = _render_page(snapshot, page_number, profile, work_dir)
            _assert_effective_dpi(rendered, reader.pages[page_number - 1], page_number)
            jpeg_bytes = _degrade(rendered, profile)
            raster_pages[page_number] = _raster_page(jpeg_bytes, reader.pages[page_number - 1])

        writer = PdfWriter()
        writer.metadata = None
        for page_number, source_page in enumerate(reader.pages, start=1):
            writer.add_page(raster_pages.get(page_number, source_page))
        writer.add_metadata(controlled_metadata)
        _atomic_write(writer, destination)


def _load_profiles(path: Path) -> dict[int, ScanProfile]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not value:
        raise ValueError("profile JSON must be a non-empty object keyed by one-based page number")
    profiles: dict[int, ScanProfile] = {}
    for raw_page, raw_profile in value.items():
        try:
            page = int(raw_page)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid page key in profile JSON: {raw_page!r}") from exc
        if str(page) != str(raw_page):
            raise ValueError(f"page key must be a canonical positive integer: {raw_page!r}")
        if not isinstance(raw_profile, dict):
            raise ValueError(f"profile for page {page} must be an object")
        profiles[page] = ScanProfile.from_mapping(raw_profile)
    return profiles


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="existing source PDF")
    parser.add_argument("output", type=Path, help="atomically written output PDF")
    parser.add_argument(
        "--profiles",
        type=Path,
        required=True,
        help="JSON object mapping one-based page numbers to ScanProfile fields",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        help="optional JSON object of controlled PDF metadata overrides",
    )
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8")) if args.metadata else None
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("metadata JSON must be an object")
    rasterize_pdf_pages(
        args.source,
        args.output,
        _load_profiles(args.profiles),
        metadata=metadata,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
