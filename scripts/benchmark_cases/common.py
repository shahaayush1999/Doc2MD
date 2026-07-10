from __future__ import annotations

import json
import math
import random
import reportlab
import textwrap
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, Sequence

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from reportlab.lib.colors import Color, HexColor, black, white
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


REPO_ROOT = Path(__file__).resolve().parents[2]
PORTRAIT = LETTER
LANDSCAPE = landscape(LETTER)

INK = HexColor("#17202A")
MUTED = HexColor("#59636E")
RULE = HexColor("#C9CED3")
LIGHT_RULE = HexColor("#E5E7E9")
PAPER = HexColor("#FCFCFA")
BLUE = HexColor("#1D4E89")
RED = HexColor("#9E2A2B")
AMBER = HexColor("#A15C00")
GREEN = HexColor("#2D6A4F")

FONT_DIR = Path(reportlab.__file__).resolve().parent / "fonts"
REGULAR = "DocSans"
BOLD = "DocSans-Bold"
ITALIC = "DocSans-Italic"
pdfmetrics.registerFont(TTFont(REGULAR, str(FONT_DIR / "Vera.ttf")))
pdfmetrics.registerFont(TTFont(BOLD, str(FONT_DIR / "VeraBd.ttf")))
pdfmetrics.registerFont(TTFont(ITALIC, str(FONT_DIR / "VeraIt.ttf")))


def slugify(value: str) -> str:
    return "-".join(part for part in "".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def wrap_lines(text: str, width: float, font: str, size: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if pdfmetrics.stringWidth(candidate, font, size) <= width:
            current = candidate
        elif current:
            lines.append(current)
            current = word
        else:
            # Preserve long identifiers while allowing them to wrap deterministically.
            chunk = ""
            for char in word:
                if pdfmetrics.stringWidth(chunk + char, font, size) <= width:
                    chunk += char
                else:
                    lines.append(chunk)
                    chunk = char
            current = chunk
    if current:
        lines.append(current)
    return lines or [""]


def draw_paragraph(
    canvas: Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    *,
    font: str = "DocSans",
    size: float = 9.2,
    leading: float = 12.2,
    color: Color = INK,
    max_lines: int | None = None,
) -> float:
    lines = wrap_lines(text, width, font, size)
    if max_lines is not None:
        if len(lines) > max_lines:
            raise ValueError(f"Paragraph would truncate {len(lines) - max_lines} line(s): {text[:80]!r}")
    canvas.setFont(font, size)
    canvas.setFillColor(color)
    for line in lines:
        canvas.drawString(x, y, line)
        y -= leading
    return y


def draw_label(canvas: Canvas, text: str, x: float, y: float, *, color: Color = MUTED) -> None:
    canvas.setFillColor(color)
    canvas.setFont("DocSans-Bold", 6.8)
    canvas.drawString(x, y, text.upper())


def draw_badge(canvas: Canvas, text: str, x: float, y: float, color: Color) -> float:
    width = pdfmetrics.stringWidth(text.upper(), "DocSans-Bold", 7) + 14
    canvas.setFillColor(Color(color.red, color.green, color.blue, alpha=0.10))
    canvas.roundRect(x, y - 3, width, 15, 4, fill=1, stroke=0)
    canvas.setFillColor(color)
    canvas.setFont("DocSans-Bold", 7)
    canvas.drawString(x + 7, y + 1, text.upper())
    return width


def draw_checkbox(canvas: Canvas, x: float, y: float, state: str, label: str = "") -> None:
    canvas.setStrokeColor(INK if state != "disabled" else RULE)
    canvas.setLineWidth(0.8)
    canvas.rect(x, y, 9, 9, fill=0, stroke=1)
    if state == "checked":
        canvas.setStrokeColor(BLUE)
        canvas.setLineWidth(1.4)
        canvas.line(x + 1.5, y + 4.5, x + 4, y + 1.5)
        canvas.line(x + 4, y + 1.5, x + 8.5, y + 8)
    elif state == "crossed":
        canvas.setStrokeColor(RED)
        canvas.line(x + 1, y + 1, x + 8, y + 8)
        canvas.line(x + 1, y + 8, x + 8, y + 1)
    elif state == "disabled":
        canvas.setFillColor(HexColor("#E8EAEC"))
        canvas.rect(x + 1, y + 1, 7, 7, fill=1, stroke=0)
    if label:
        canvas.setFillColor(INK if state != "disabled" else MUTED)
        canvas.setFont("DocSans", 8)
        canvas.drawString(x + 14, y + 1, label)


def draw_arrow(
    canvas: Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    color: Color = INK,
    dashed: bool = False,
    width: float = 1.4,
) -> None:
    canvas.saveState()
    canvas.setStrokeColor(color)
    canvas.setFillColor(color)
    canvas.setLineWidth(width)
    if dashed:
        canvas.setDash(5, 3)
    canvas.line(x1, y1, x2, y2)
    angle = math.atan2(y2 - y1, x2 - x1)
    length = 7
    left = angle + math.pi * 0.84
    right = angle - math.pi * 0.84
    path = canvas.beginPath()
    path.moveTo(x2, y2)
    path.lineTo(x2 + length * math.cos(left), y2 + length * math.sin(left))
    path.lineTo(x2 + length * math.cos(right), y2 + length * math.sin(right))
    path.close()
    canvas.drawPath(path, fill=1, stroke=0)
    canvas.restoreState()


def draw_table(
    canvas: Canvas,
    x: float,
    top: float,
    widths: Sequence[float],
    rows: Sequence[Sequence[str]],
    *,
    font_size: float = 7.2,
    row_padding: float = 4.2,
    header_rows: int = 1,
    group_header_rows: int = 0,
    zebra: bool = False,
    vertical_rules: bool = False,
) -> float:
    """Draw a compact, alignment-led table and return its lower y coordinate."""
    page_width = float(canvas._pagesize[0])
    if x < 0 or x + sum(widths) > page_width + 0.1:
        raise ValueError(f"Table exceeds page width: x={x}, width={sum(widths)}, page={page_width}")
    y = top
    line_height = font_size + 2.4
    for row_index, row in enumerate(rows):
        cell_lines = [wrap_lines(str(value), widths[i] - 2 * row_padding, "DocSans", font_size) for i, value in enumerate(row)]
        height = max(len(lines) for lines in cell_lines) * line_height + 2 * row_padding
        is_header = row_index < header_rows
        is_group = row_index < group_header_rows
        if is_group:
            canvas.setFillColor(HexColor("#E9EDF1"))
            canvas.rect(x, y - height, sum(widths), height, fill=1, stroke=0)
        elif is_header:
            canvas.setFillColor(HexColor("#F3F4F4"))
            canvas.rect(x, y - height, sum(widths), height, fill=1, stroke=0)
        elif zebra and row_index % 2:
            canvas.setFillColor(HexColor("#FAFAF8"))
            canvas.rect(x, y - height, sum(widths), height, fill=1, stroke=0)
        cursor = x
        for col_index, lines in enumerate(cell_lines):
            canvas.setFont("DocSans-Bold" if is_header else "DocSans", font_size)
            canvas.setFillColor(INK)
            text_y = y - row_padding - font_size
            for line in lines:
                canvas.drawString(cursor + row_padding, text_y, line)
                text_y -= line_height
            if vertical_rules and col_index > 0:
                canvas.setStrokeColor(LIGHT_RULE)
                canvas.setLineWidth(0.35)
                canvas.line(cursor, y, cursor, y - height)
            cursor += widths[col_index]
        canvas.setStrokeColor(INK if is_header else LIGHT_RULE)
        canvas.setLineWidth(0.75 if is_header else 0.35)
        canvas.line(x, y - height, x + sum(widths), y - height)
        y -= height
    if y < 36:
        raise ValueError(f"Table enters the footer margin: bottom={y:.1f}")
    return y


def markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    def safe(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    return "\n".join(
        [
            "| " + " | ".join(safe(value) for value in headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(safe(value) for value in row) + " |" for row in rows),
        ]
    )


def leaf(
    leaf_id: str,
    expectation: str,
    *,
    harm: int = 1,
    allow_partial: bool = False,
) -> dict[str, Any]:
    return {
        "id": leaf_id,
        "expectation": expectation,
        "harm": harm,
        "allowPartial": allow_partial,
    }


def table_leaves(
    prefix: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    key_column: int = 0,
    consequential: set[tuple[str, str]] | None = None,
    skip_columns: set[int] | None = None,
) -> list[dict[str, Any]]:
    consequential = consequential or set()
    skip_columns = skip_columns or set()
    key_order = [str(row[key_column]) for row in rows]
    leaves: list[dict[str, Any]] = [
        leaf(
            f"{prefix}.schema",
            "The region preserves the source field schema in order: " + ", ".join(str(header) for header in headers) + ".",
            allow_partial=True,
        ),
        leaf(
            f"{prefix}.row-order",
            "The source row order is recoverable as: " + " -> ".join(key_order) + ".",
            allow_partial=True,
        ),
    ]
    for row in rows:
        key = str(row[key_column])
        key_slug = slugify(key)
        for column_index, value in enumerate(row):
            if column_index == key_column or column_index in skip_columns:
                continue
            header = str(headers[column_index])
            leaves.append(
                leaf(
                    f"{prefix}.{key_slug}.{slugify(header)}",
                    f"For {key}, {header} is {value}.",
                    harm=2 if (key, header) in consequential else 1,
                )
            )
    return leaves


def make_scan(
    title: str,
    lines: Sequence[str],
    *,
    width: int = 1300,
    height: int = 760,
    seed: int = 1,
    marks: Sequence[tuple[int, int, str]] = (),
) -> Image.Image:
    """Create a deterministic, readable scanned-form region with paper texture."""
    rng = random.Random(seed)
    image = Image.new("L", (width, height), 245)
    pixels = image.load()
    for _ in range(width * height // 35):
        px = rng.randrange(width)
        py = rng.randrange(height)
        pixels[px, py] = rng.randrange(225, 250)
    image = image.filter(ImageFilter.GaussianBlur(0.25))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=18)
    bold = ImageFont.load_default(size=21)
    draw.text((45, 32), title, font=bold, fill=25)
    draw.line((45, 68, width - 45, 68), fill=80, width=2)
    y = 95
    for line in lines:
        if draw.textlength(line, font=font) > width - 110:
            raise ValueError(f"Scanned-form line exceeds image width: {line!r}")
        if y + 30 > height - 24:
            raise ValueError(f"Scanned-form lines exceed image height near: {line!r}")
        draw.text((55, y), line, font=font, fill=35)
        y += 33
    for x, y, mark in marks:
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError(f"Scanned-form mark is outside the image: {(x, y, mark)!r}")
        if mark == "check":
            draw.line((x, y + 8, x + 8, y + 18), fill=25, width=4)
            draw.line((x + 8, y + 18, x + 28, y - 5), fill=25, width=4)
        elif mark == "strike":
            draw.line((x, y, x + 220, y - 4), fill=35, width=3)
        else:
            draw.text((x, y), mark, font=font, fill=25)
    image = ImageEnhance.Contrast(image).enhance(1.08)
    return image.convert("RGB")


def image_reader(image: Image.Image) -> ImageReader:
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return ImageReader(buffer)


@dataclass
class CaseBuilder:
    output_root: Path
    case_id: str
    title: str
    family: str
    tags: list[str]
    page_count: int
    purpose: str
    source_modality: str
    document_ref: str = ""
    metadata_date: str = "D:20260701090000+00'00'"
    canvas: Canvas = field(init=False)
    case_dir: Path = field(init=False)
    pdf_path: Path = field(init=False)
    page_number: int = field(default=0, init=False)
    page_size: tuple[float, float] = field(default=PORTRAIT, init=False)
    gold_parts: list[str] = field(default_factory=list, init=False)
    regions: list[dict[str, Any]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.output_root = self.output_root.resolve()
        try:
            self.output_root.relative_to(REPO_ROOT)
        except ValueError as exc:
            raise ValueError(f"Output root must stay inside the repository: {self.output_root}") from exc
        self.case_dir = self.output_root / "cases" / self.case_id
        self.case_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_path = self.case_dir / "source.pdf"
        self.canvas = Canvas(str(self.pdf_path), pagesize=PORTRAIT, invariant=1, pageCompression=1)
        self.canvas.setTitle(self.title)
        self.canvas.setAuthor("Document Control")
        self.canvas.setCreator("Office document export")
        self.canvas.setProducer("Enterprise Document Services")
        self.canvas.setDateFormatter(lambda *_: self.metadata_date)

    @property
    def width(self) -> float:
        return self.page_size[0]

    @property
    def height(self) -> float:
        return self.page_size[1]

    def new_page(
        self,
        title: str,
        *,
        subtitle: str = "",
        page_size: tuple[float, float] = PORTRAIT,
        section_code: str = "",
    ) -> Canvas:
        if self.page_number:
            self.canvas.showPage()
        self.page_number += 1
        self.page_size = page_size
        self.canvas.setPageSize(page_size)
        self.canvas.setFillColor(PAPER)
        self.canvas.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        self.canvas.setFillColor(MUTED)
        self.canvas.setFont("DocSans-Bold", 7.2)
        self.canvas.drawString(42, self.height - 31, self.family.upper())
        if section_code:
            self.canvas.drawRightString(self.width - 42, self.height - 31, section_code)
        self.canvas.setFillColor(INK)
        self.canvas.setFont("DocSans-Bold", 18)
        self.canvas.drawString(42, self.height - 62, title)
        if subtitle:
            self.canvas.setFont("DocSans", 8)
            self.canvas.setFillColor(MUTED)
            self.canvas.drawString(42, self.height - 78, subtitle)
        self.canvas.setStrokeColor(RULE)
        self.canvas.setLineWidth(0.6)
        self.canvas.line(42, self.height - 88, self.width - 42, self.height - 88)
        self.canvas.setFont("DocSans", 6.8)
        self.canvas.setFillColor(MUTED)
        footer_ref = self.document_ref or f"{self.family.title()} · controlled copy"
        self.canvas.drawString(42, 24, footer_ref)
        self.canvas.drawRightString(self.width - 42, 24, f"{self.page_number} / {self.page_count}")
        return self.canvas

    def add_gold(self, heading: str, body: str) -> None:
        self.gold_parts.append(f"## {heading}\n\n{body.strip()}\n")

    def add_region(
        self,
        region_id: str,
        label: str,
        kind: str,
        leaves: Sequence[dict[str, Any]],
        *,
        page: int | None = None,
        budget: int = 1,
        closed_world: bool = False,
    ) -> None:
        self.regions.append(
            {
                "id": region_id,
                "page": page or self.page_number,
                "label": label,
                "kind": kind,
                "budget": budget,
                "closedWorld": closed_world,
                "leaves": list(leaves),
            }
        )

    def finish(self) -> dict[str, Any]:
        if self.page_number != self.page_count:
            raise ValueError(f"{self.case_id}: expected {self.page_count} pages, generated {self.page_number}")
        self.canvas.save()
        gold = f"# {self.title}\n\n" + "\n".join(self.gold_parts)
        (self.case_dir / "gold.md").write_text(gold, encoding="utf-8")
        (self.case_dir / "facts.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 2,
                    "id": self.case_id,
                    "title": self.title,
                    "family": self.family,
                    "tags": self.tags,
                    "regions": self.regions,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (self.case_dir / "spec.md").write_text(
            f"# {self.title}\n\n"
            f"Source modality: {self.source_modality}\n\n"
            f"Family: `{self.family}`\n\n"
            f"Purpose: {self.purpose}\n\n"
            "Tags: "
            + ", ".join(f"`{tag}`" for tag in self.tags)
            + "\n",
            encoding="utf-8",
        )
        prefix = self.output_root.relative_to(REPO_ROOT).as_posix()
        base = f"{prefix}/cases/{self.case_id}"
        return {
            "id": self.case_id,
            "title": self.title,
            "family": self.family,
            "tags": self.tags,
            "pages": self.page_count,
            "pdf": f"{base}/source.pdf",
            "gold": f"{base}/gold.md",
            "spec": f"{base}/spec.md",
            "facts": f"{base}/facts.json",
        }
