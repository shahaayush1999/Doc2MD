from __future__ import annotations

import json
import random
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = ROOT / "benchmark"
CASE_ROOT = BENCHMARK_ROOT / "cases"
ASSET_ROOT = ROOT / "assets"

PAGE_W, PAGE_H = 1700, 2200
DECK_W, DECK_H = 2200, 1238


def pdf_text_reference(path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    text = result.stdout.replace("\f", "\n\n--- Page Break ---\n\n").strip()
    return re.sub(r"\n{4,}", "\n\n\n", text)


def font(size: int, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = []
    if bold:
        names += [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        ]
    if italic:
        names += [
            "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
            "/Library/Fonts/Arial Italic.ttf",
        ]
    names += [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


F = {
    "title": font(48, True),
    "h1": font(36, True),
    "h2": font(28, True),
    "body": font(25),
    "small": font(21),
    "small_bold": font(21, True),
    "tiny": font(18),
    "tiny_bold": font(18, True),
    "mono": font(22),
    "italic": font(24, italic=True),
    "stamp": font(32, True),
}


def make_field_photo(kind: int, w: int, h: int) -> Image.Image:
    rng = random.Random(7000 + kind)
    img = Image.new("RGB", (w, h), "#d8dee7")
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(h):
        shade = int(210 - y * 0.26 + rng.randint(-3, 3))
        d.line((0, y, w, y), fill=(shade, shade + 3, min(255, shade + 10), 255))
    for _ in range(2800):
        x = rng.randrange(w)
        y = rng.randrange(h)
        delta = rng.randrange(-22, 23)
        base = max(0, min(255, img.getpixel((x, y))[0] + delta))
        img.putpixel((x, y), (base, max(0, min(255, base + rng.randrange(-5, 6))), max(0, min(255, base + rng.randrange(-5, 8)))))

    d = ImageDraw.Draw(img, "RGBA")
    if kind == 0:
        d.polygon([(0, h * 0.58), (w, h * 0.46), (w, h), (0, h)], fill=(112, 118, 128, 120))
        d.rectangle((54, 30, 235, 126), fill=(125, 138, 153, 230), outline=(65, 74, 86, 255), width=2)
        d.rectangle((252, 48, 430, 128), fill=(121, 56, 17, 230), outline=(69, 26, 3, 255), width=2)
        for px in [220, 278, 338]:
            d.rectangle((px, 24, px + 44, 48), fill=(217, 119, 6, 240), outline=(146, 64, 14, 255))
        d.line((238, 132, 258, 132), fill=(180, 20, 20, 255), width=4)
        d.text((210, 112), '36"', fill=(180, 20, 20, 255), font=F["tiny_bold"])
    elif kind == 1:
        d.rectangle((0, 72, w, h), fill=(88, 96, 105, 150))
        d.rectangle((78, 50, 275, 132), fill=(55, 65, 81, 240), outline=(17, 24, 39, 255), width=2)
        d.ellipse((370, 55, 414, 100), fill=(210, 38, 38, 240))
        d.rectangle((386, 96, 397, 134), fill=(210, 38, 38, 240))
        d.line((275, 108, 370, 78), fill=(245, 158, 11, 255), width=4)
        d.text((322, 50), "16'-0\"", fill=(180, 20, 20, 255), font=F["tiny_bold"])
    elif kind == 2:
        d.rectangle((0, 0, w, h), fill=(218, 226, 236, 160))
        d.rectangle((95, 38, 475, 124), fill=(224, 231, 240, 230), outline=(100, 116, 139, 255), width=2)
        for px in range(115, 455, 38):
            d.line((px, 38, px + 38, 124), fill=(160, 174, 192, 90), width=1)
        d.line((145, 132, 420, 132), fill=(37, 99, 235, 255), width=4)
        d.text((255, 112), "3'-2\"", fill=(37, 99, 235, 255), font=F["tiny_bold"])
    elif kind == 3:
        d.rectangle((0, 0, w, h), fill=(229, 234, 241, 120))
        for sx in range(92, 430, 54):
            d.rectangle((sx, 28, sx + 30, 130), fill=(183, 194, 208, 230), outline=(95, 111, 129, 255))
            d.rectangle((sx + 5, 18, sx + 26, 28), fill=(140, 153, 171, 180))
        d.line((150, 132, 360, 132), fill=(153, 27, 27, 255), width=4)
        d.text((238, 112), '39"', fill=(153, 27, 27, 255), font=F["tiny_bold"])
    elif kind == 4:
        d.rectangle((0, 68, w, h), fill=(148, 163, 184, 100))
        d.rectangle((130, 40, 445, 125), fill=(196, 207, 220, 230), outline=(51, 65, 85, 255), width=3)
        d.line((130, 40, 445, 125), fill=(100, 116, 139, 180), width=2)
        d.line((130, 125, 445, 40), fill=(100, 116, 139, 180), width=2)
        d.text((235, 78), '58" x 80"', fill=(153, 27, 27, 255), font=F["tiny_bold"])
    else:
        d.rectangle((0, 0, w, h), fill=(242, 231, 183, 170))
        d.rectangle((150, 32, 470, 116), fill=(254, 249, 195, 245), outline=(161, 98, 7, 255), width=3)
        draw_text(d, (175, 51), "Accessible Entrance During Crane Pick\nJuly 8-10", F["tiny_bold"], fill="#92400e", width=35, leading=22)
        for px in [155, 455]:
            d.rectangle((px, 28, px + 22, 38), fill=(180, 83, 9, 180))
    return img.filter(ImageFilter.GaussianBlur(radius=0.35))


def observation_photo(kind: int, w: int, h: int) -> Image.Image:
    sheet_path = ASSET_ROOT / "photo-observation-contact-sheet.png"
    if not sheet_path.exists():
        return make_field_photo(kind, w, h)
    sheet = Image.open(sheet_path).convert("RGB")
    cell_w = sheet.width // 2
    cell_h = sheet.height // 3
    col = kind % 2
    row = kind // 2
    crop = sheet.crop((col * cell_w + 8, row * cell_h + 8, (col + 1) * cell_w - 8, (row + 1) * cell_h - 8))
    return ImageOps.fit(crop, (w, h), method=Image.Resampling.LANCZOS)


def cad_floorplan_crop(w: int, h: int) -> Image.Image:
    sheet_path = ASSET_ROOT / "library-floorplan-cad-crop.png"
    if not sheet_path.exists():
        return Image.new("RGB", (w, h), "#f8fbff")
    sheet = Image.open(sheet_path).convert("RGB")
    return ImageOps.fit(sheet, (w, h), method=Image.Resampling.LANCZOS)


@dataclass
class Case:
    id: str
    title: str
    family: str
    tags: list[str]
    purpose: str
    modality: str
    expected: list[str]
    scoring: list[str]
    gold: str
    checks: list[dict]
    pages: list[Image.Image]
    facts: list[dict] | None = None
    hidden_text: list[str] | None = None
    covered_text: list[str] | None = None
    extractable_text_pages: list[list[tuple[int, int, str]]] | None = None
    source_pdf: Path | None = None
    rasterize_source_pdf: bool = False
    rasterize_dpi: int = 144
    page_count_override: int | None = None

    @property
    def slug(self) -> str:
        return self.id


def base_page(title: str) -> Image.Image:
    img = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    d = ImageDraw.Draw(img)
    d.text((92, 72), title, fill="#111827", font=F["title"])
    return img


def draw_text(d: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fnt=F["body"], fill="#111827", width=88, leading=34) -> int:
    x, y = xy
    for para in text.split("\n"):
        lines = wrap(para, width=width) if para else [""]
        for line in lines:
            d.text((x, y), line, fill=fill, font=fnt)
            y += leading
        if para == "":
            y += leading // 2
    return y


def draw_section(d: ImageDraw.ImageDraw, x: int, y: int, title: str, w: int = 1400, color: str = "#111827") -> int:
    d.text((x, y), title.upper(), fill=color, font=F["small_bold"])
    d.line((x, y + 34, x + w, y + 34), fill="#9ca3af", width=1)
    return y + 52


def draw_two_columns(
    d: ImageDraw.ImageDraw,
    x: int,
    y: int,
    left: str,
    right: str,
    col_w_chars: int = 49,
    gap: int = 80,
    leading: int = 27,
    fnt=F["tiny"],
) -> int:
    y1 = draw_text(d, (x, y), left, fnt, width=col_w_chars, leading=leading)
    y2 = draw_text(d, (x + 690 + gap, y), right, fnt, width=col_w_chars, leading=leading)
    return max(y1, y2)


def draw_note(d: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str, text: str, color: str = "#9a3412") -> None:
    x1, y1, x2, y2 = box
    d.line((x1, y1, x2, y1), fill=color, width=3)
    d.text((x1, y1 + 18), title, fill=color, font=F["small_bold"])
    draw_text(d, (x1, y1 + 52), text, F["tiny"], fill="#1f2937", width=max(22, int((x2 - x1) / 15)), leading=24)


def draw_kv_band(d: ImageDraw.ImageDraw, x: int, y: int, pairs: list[tuple[str, str]], widths: list[int] | None = None) -> int:
    widths = widths or [260] * len(pairs)
    cx = x
    d.line((x, y, x + sum(widths), y), fill="#111827", width=2)
    for (label, value), w in zip(pairs, widths):
        d.text((cx, y + 18), label.upper(), fill="#6b7280", font=F["tiny_bold"])
        d.text((cx, y + 48), value, fill="#111827", font=F["small"])
        cx += w
    d.line((x, y + 86, x + sum(widths), y + 86), fill="#d1d5db", width=1)
    return y + 105


def draw_redline_text(d: ImageDraw.ImageDraw, x: int, y: int, chunks: list[tuple[str, str]], width: int = 1040) -> int:
    cx, cy = x, y
    line_h = 30
    max_x = x + width
    for kind, text in chunks:
        for word in text.split(" "):
            token = word + " "
            bbox = d.textbbox((0, 0), token, font=F["small"])
            tw = bbox[2] - bbox[0]
            if cx + tw > max_x:
                cx = x
                cy += line_h
            fill = "#111827"
            if kind == "delete":
                fill = "#991b1b"
            elif kind == "insert":
                fill = "#166534"
            d.text((cx, cy), token, fill=fill, font=F["small"])
            if kind == "delete":
                d.line((cx, cy + 16, cx + tw - 5, cy + 16), fill="#991b1b", width=2)
            if kind == "insert":
                d.line((cx, cy + 27, cx + tw - 5, cy + 27), fill="#166534", width=2)
            cx += tw
    return cy + line_h + 12


def draw_card(d: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str, lines: list[str], fill="#f8fafc", outline="#334155") -> None:
    x1, y1, _, _ = box
    x2, y2 = box[2], box[3]
    d.line((x1, y1, x2, y1), fill=outline, width=3)
    d.line((x1, y1, x1, y2), fill=outline, width=5)
    d.text((x1 + 24, y1 + 22), title, fill="#111827", font=F["h2"])
    y = y1 + 72
    for line in lines:
        d.text((x1 + 24, y), line, fill="#111827", font=F["small"])
        y += 34


def draw_table(d: ImageDraw.ImageDraw, x: int, y: int, widths: list[int], rows: list[list[str]], row_h: int = 66) -> int:
    table_w = sum(widths)
    header_h = row_h
    d.line((x, y, x + table_w, y), fill="#111827", width=3)
    for r, row in enumerate(rows):
        cx = x
        fnt = F["small_bold"] if r == 0 else F["tiny"]
        fill = "#111827" if r == 0 else "#1f2937"
        for c, w in enumerate(widths):
            text = row[c] if c < len(row) else ""
            d.multiline_text((cx + 8, y + 12), text, fill=fill, font=fnt, spacing=3)
            cx += w
        line_fill = "#111827" if r == 0 else "#d1d5db"
        line_width = 2 if r == 0 else 1
        d.line((x, y + row_h, x + table_w, y + row_h), fill=line_fill, width=line_width)
        y += row_h
    return y


def draw_ledger(d: ImageDraw.ImageDraw, x: int, y: int, widths: list[int], rows: list[list[str]], row_h: int = 42, header_rule: bool = True) -> int:
    table_w = sum(widths)
    if header_rule:
        d.line((x, y + row_h - 8, x + table_w, y + row_h - 8), fill="#111827", width=2)
    for r, row in enumerate(rows):
        cx = x
        fnt = F["tiny_bold"] if r == 0 else F["tiny"]
        fill = "#111827" if r == 0 else "#1f2937"
        for c, w in enumerate(widths):
            text = row[c] if c < len(row) else ""
            d.multiline_text((cx + 4, y + 7), text, fill=fill, font=fnt, spacing=2)
            cx += w
        if r > 0 and r % 5 == 0:
            d.line((x, y + row_h - 5, x + table_w, y + row_h - 5), fill="#e5e7eb", width=1)
        y += row_h
    return y


def draw_defect_photo(kind: int, w: int, h: int) -> Image.Image:
    sheet_path = ASSET_ROOT / "mx12-defect-contact-sheet.png"
    if sheet_path.exists():
        sheet = Image.open(sheet_path).convert("RGB")
        cell_w = sheet.width // 2
        cell_h = sheet.height // 2
        col = kind % 2
        row = kind // 2
        crop = sheet.crop((col * cell_w + 4, row * cell_h + 4, (col + 1) * cell_w - 4, (row + 1) * cell_h - 4))
        return ImageOps.fit(crop, (w, h), method=Image.Resampling.LANCZOS)

    rng = random.Random(8200 + kind)
    img = Image.new("RGB", (w, h), "#c9ced6")
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(h):
        shade = 198 - int(y * 28 / h) + rng.randint(-2, 2)
        d.line((0, y, w, y), fill=(shade, shade + 4, shade + 9, 255))
    for _ in range(1600):
        x = rng.randrange(w)
        y = rng.randrange(h)
        delta = rng.randrange(-18, 19)
        base = max(0, min(255, img.getpixel((x, y))[0] + delta))
        img.putpixel((x, y), (base, max(0, min(255, base + 2)), max(0, min(255, base + 8))))
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle((55, 58, w - 55, h - 50), fill=(185, 191, 201, 220), outline=(79, 91, 112, 255), width=3)
    d.rectangle((95, 92, w - 95, h - 88), fill=(151, 159, 173, 180), outline=(67, 78, 96, 255), width=2)
    if kind == 0:
        d.line((150, 132, 410, 284), fill=(150, 22, 22, 255), width=6)
        d.ellipse((132, 112, 430, 305), outline=(220, 38, 38, 255), width=5)
        d.text((255, 78), "Burr B2", fill=(150, 22, 22, 255), font=F["tiny_bold"])
    elif kind == 1:
        d.rectangle((225, 95, 405, 285), outline=(37, 99, 235, 255), width=5)
        d.line((220, 285, 420, 95), fill=(37, 99, 235, 255), width=4)
        d.text((180, 70), "Scratch 7.8 mm", fill=(30, 64, 175, 255), font=F["tiny_bold"])
    elif kind == 2:
        for px in [165, 230, 295, 360, 425]:
            d.ellipse((px, 155, px + 20, 175), fill=(20, 83, 45, 210))
        d.rectangle((150, 136, 456, 196), outline=(21, 128, 61, 255), width=4)
        d.text((170, 102), "porosity cluster", fill=(21, 128, 61, 255), font=F["tiny_bold"])
    else:
        d.line((112, 258, 490, 258), fill=(234, 88, 12, 255), width=5)
        d.line((112, 298, 490, 298), fill=(234, 88, 12, 255), width=5)
        d.text((240, 224), "gap 0.42 mm", fill=(194, 65, 12, 255), font=F["tiny_bold"])
    return img.filter(ImageFilter.GaussianBlur(radius=0.25))


def checkbox(d: ImageDraw.ImageDraw, x: int, y: int, label: str, checked: bool, fnt=F["body"]) -> None:
    d.rectangle((x, y, x + 30, y + 30), fill="white", outline="#111827", width=3)
    if checked:
        d.line((x + 6, y + 16, x + 13, y + 25, x + 26, y + 6), fill="#0f766e", width=5)
    d.text((x + 42, y - 3), label, fill="#111827", font=fnt)


def image_to_pdf_page(c: canvas.Canvas, img: Image.Image) -> None:
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    c.drawImage(ImageReader(buffer), 0, 0, width=letter[0], height=letter[1])
    c.showPage()


def literal(term: str) -> str:
    return re.sub(r"([\\.^$*+?{}\[\]|()])", r"\\\1", term)


def all_check(id_: str, category: str, terms: list[str], weight: float = 1, description: str | None = None) -> dict:
    return {"id": id_, "category": category, "weight": weight, "description": description or id_, "all": [literal(t) for t in terms]}


def none_check(id_: str, terms: list[str], weight: float = 2, category: str = "hallucination", description: str | None = None) -> dict:
    return {"id": id_, "category": category, "weight": weight, "description": description or id_, "none": [literal(t) for t in terms]}


def none_regex_check(id_: str, patterns: list[str], weight: float = 2, category: str = "hallucination", description: str | None = None) -> dict:
    return {"id": id_, "category": category, "weight": weight, "description": description or id_, "none": patterns}


def near_check(id_: str, category: str, terms: list[str], weight: float = 2, window: int = 280, description: str | None = None) -> dict:
    return {
        "id": id_,
        "category": category,
        "weight": weight,
        "description": description or id_,
        "near": {"terms": [literal(t) for t in terms], "window": window},
    }


def ordered_check(id_: str, category: str, terms: list[str], weight: float = 2, description: str | None = None) -> dict:
    return {"id": id_, "category": category, "weight": weight, "description": description or id_, "ordered": [literal(t) for t in terms]}


def fact(
    id_: str,
    category: str,
    weight: float,
    expectation: str,
    guidance: str = "",
    modality: str | None = None,
    severity: str | None = None,
) -> dict:
    item = {
        "id": id_,
        "category": category,
        "weight": weight,
        "expectation": expectation,
        "guidance": guidance,
    }
    if modality:
        item["modality"] = modality
    if severity:
        item["severity"] = severity
    return item


def infer_fact_severity(item: dict) -> str:
    category = item.get("category", "")
    modality = item.get("modality", "")
    weight = float(item.get("weight", 1))
    critical_categories = {
        "source_state",
        "source-precedence",
        "forbidden_text",
        "form_state",
        "redline",
        "exact_field",
        "cross_page_binding",
    }
    primary_visual_categories = {
        "table_cell",
        "tables",
        "chart",
        "visual",
        "visual_relation",
        "spatial",
        "formula",
    }
    if category in critical_categories or modality in critical_categories:
        return "critical"
    if category in primary_visual_categories and weight >= 6:
        return "critical"
    if weight >= 8:
        return "critical"
    if weight >= 4:
        return "major"
    return "minor"


def normalize_facts(items: list[dict]) -> list[dict]:
    normalized = []
    for item in items:
        next_item = dict(item)
        next_item.setdefault("severity", infer_fact_severity(next_item))
        normalized.append(next_item)
    return normalized


def facts_from_checks(case: Case) -> list[dict]:
    return normalize_facts([
        fact(
            check["id"],
            check.get("category", "accuracy"),
            check.get("weight", 1),
            check.get("description", check["id"]),
            "Derived from the deterministic audit checklist. Mark correct when the candidate faithfully preserves this obligation, even if wording or Markdown syntax differs.",
        )
        for check in case.checks
    ])


def h01() -> Case:
    img = base_page("Release Approval Card")
    d = ImageDraw.Draw(img)
    draw_card(
        d,
        (210, 320, 1490, 1020),
        "Visible release decision",
        [
            "Release: REL-47B",
            "Status: BLOCKED",
            "Owner: Nisha Vora",
            "Budget cap: $14,900",
            "Reason: Security signoff missing for EU tenant",
            "Stamp: HOLD UNTIL 2026-08-17",
        ],
        fill="#fff7ed",
        outline="#9a3412",
    )
    d.text((235, 1110), "Benchmark policy: score only rendered visible values; hidden stale text is wrong.", fill="#7f1d1d", font=F["body"])
    return Case(
        "H01-hidden-stale-release",
        "Hidden Stale Release Card",
        "visibility",
        ["hidden-text", "raster-card", "negative-check"],
        "Ensure rendered visible card wins over invisible stale text extraction.",
        "Visible content is a raster card. Conflicting stale values are invisible PDF text.",
        ["release fields", "status/owner/budget binding", "hidden stale text policy"],
        ["Preserve visible status, owner, budget, reason, and stamp.", "Penalize hidden APPROVED/Mira/$19,400 values."],
        "# Release Approval Card\n\nVisible release decision:\n\nRelease: REL-47B\nStatus: BLOCKED\nOwner: Nisha Vora\nBudget cap: $14,900\nReason: Security signoff missing for EU tenant\nStamp: HOLD UNTIL 2026-08-17\n\nBenchmark policy: score only rendered visible values; hidden stale text is wrong.\n",
        [
            all_check("visible-values", "text", ["REL-47B", "BLOCKED", "Nisha Vora", "$14,900"]),
            near_check("status-owner-budget", "binding", ["BLOCKED", "Nisha Vora", "$14,900"], 2.5),
            none_check("no-hidden-stale", ["APPROVED", "$19,400", "Mira Chen"], 3),
        ],
        [img],
        hidden_text=["Release REL-47B Status APPROVED Owner Mira Chen Budget cap $19,400 Stamp READY TO SHIP"],
    )


def h02() -> Case:
    img = base_page("Shipping Exception Overlay")
    d = ImageDraw.Draw(img)
    draw_card(
        d,
        (180, 370, 1520, 950),
        "Rendered exception card",
        [
            "Shipment: XQ-17",
            "Visible status: DELAYED",
            "Current port: Osaka",
            "ETA: 2026-08-14",
            "Owner: Ren Ito",
            "Reason: customs inspection hold",
        ],
        fill="#eff6ff",
        outline="#1d4ed8",
    )
    d.text((220, 1030), "Opaque card covers a stale text layer. Use the rendered exception card.", fill="#7f1d1d", font=F["body"])
    return Case(
        "H02-opaque-stale-shipment",
        "Opaque Stale Shipment Overlay",
        "visibility",
        ["covered-text", "raster-card", "negative-check"],
        "Ensure an opaque rendered overlay beats stale text underneath.",
        "Stale extractable text is drawn first, then covered by an opaque raster card.",
        ["shipment fields", "status/port/ETA binding", "covered stale text policy"],
        ["Preserve visible delayed Osaka ETA values.", "Penalize stale ON TIME Busan values."],
        "# Shipping Exception Overlay\n\nRendered exception card: Shipment XQ-17 has visible status DELAYED, current port Osaka, ETA 2026-08-14, owner Ren Ito, and reason customs inspection hold.\n\nOpaque card covers a stale text layer. Use the rendered exception card.\n",
        [
            all_check("visible-shipment", "text", ["XQ-17", "DELAYED", "Osaka", "2026-08-14", "Ren Ito"]),
            near_check("status-port-eta", "binding", ["DELAYED", "Osaka", "2026-08-14"], 2.5),
            none_check("no-covered-stale", ["ON TIME", "Busan", "2026-08-09", "Hana Park"], 3),
        ],
        [img],
        covered_text=["Shipment XQ-17 status ON TIME current port Busan ETA 2026-08-09 owner Hana Park"],
    )


def h03() -> Case:
    img = base_page("Raster Gantt Shift Schedule")
    d = ImageDraw.Draw(img)
    left, top = 270, 360
    cols = ["08:00", "10:00", "12:00", "14:00", "16:00", "18:00"]
    for i, col in enumerate(cols):
        x = left + i * 210
        d.text((x - 34, top - 60), col, fill="#111827", font=F["small"])
        d.line((x, top - 12, x, top + 560), fill="#cbd5e1", width=3)
    rows = [
        ("Dock intake", "Noor", 0, 1.5, "Load A-17", "#2563eb"),
        ("Release gate", "Ken", 1, 4.25, "REL-82", "#0f766e"),
        ("QA bench", "Priya", 2, 3.5, "Lot Q4", "#7c3aed"),
        ("Rollback watch", "Mira", 4, 5, "RB-9", "#dc2626"),
    ]
    for r, (task, owner, start, end, label, color) in enumerate(rows):
        y = top + r * 130
        d.text((90, y + 16), task, fill="#111827", font=F["small"])
        d.text((90, y + 52), owner, fill="#475569", font=F["tiny"])
        d.rounded_rectangle((left + int(start * 210), y, left + int(end * 210), y + 72), radius=12, fill=color)
        d.text((left + int(start * 210) + 20, y + 20), label, fill="white", font=F["small"])
    d.text((90, 960), "Supervisor note: normalize each bar into task, owner, start, end, and label rows before Monday standup.", fill="#7f1d1d", font=F["small"])
    return Case(
        "H03-raster-gantt",
        "Raster Gantt Shift Schedule",
        "spatial",
        ["raster-only", "gantt", "schedule"],
        "Force visual span normalization into explicit Markdown rows.",
        "Raster-only Gantt chart with no extractable schedule text.",
        ["task rows", "owners", "start/end times", "bar labels"],
        ["Bind each task to owner, start, end, and label."],
        "# Raster Shift Gantt\n\n| Task | Owner | Start | End | Label |\n| --- | --- | --- | --- | --- |\n| Dock intake | Noor | 08:00 | 11:00 | Load A-17 |\n| Release gate | Ken | 10:00 | 16:30 | REL-82 |\n| QA bench | Priya | 12:00 | 15:00 | Lot Q4 |\n| Rollback watch | Mira | 16:00 | 18:00 | RB-9 |\n",
        [
            {
                "id": "dock-row",
                "category": "spatial",
                "weight": 3,
                "description": "Dock intake row with exact inferred span",
                "all": [r"Dock intake(?=[^\n]{0,260}Noor)(?=[^\n]{0,260}08:00)(?=[^\n]{0,260}11:00)(?=[^\n]{0,260}Load A-17)"],
            },
            {
                "id": "release-row",
                "category": "spatial",
                "weight": 3,
                "description": "Release gate row with exact inferred span",
                "all": [r"Release gate(?=[^\n]{0,260}Ken)(?=[^\n]{0,260}10:00)(?=[^\n]{0,260}16:30)(?=[^\n]{0,260}REL-82)"],
            },
            {
                "id": "qa-row",
                "category": "spatial",
                "weight": 3,
                "description": "QA bench row with exact inferred span",
                "all": [r"QA bench(?=[^\n]{0,260}Priya)(?=[^\n]{0,260}12:00)(?=[^\n]{0,260}15:00)(?=[^\n]{0,260}Lot Q4)"],
            },
            {
                "id": "rollback-row",
                "category": "spatial",
                "weight": 3,
                "description": "Rollback watch row with exact inferred span",
                "all": [r"Rollback watch(?=[^\n]{0,260}Mira)(?=[^\n]{0,260}16:00)(?=[^\n]{0,260}18:00)(?=[^\n]{0,260}RB-9)"],
            },
        ],
        [img],
    )


def h04() -> Case:
    img = base_page("Rota With Carry-Down Cells")
    d = ImageDraw.Draw(img)
    d.text((100, 165), "Blank team cells inherit the previous team. Ditto marks inherit the previous station.", fill="#7f1d1d", font=F["small"])
    rows = [
        ["Team", "Person", "Station", "Start", "End"],
        ["Kitchen", "Ravi", "Prep", "06:00", "10:00"],
        ["", "Mina", "Service", "10:00", "14:00"],
        ["", "Omar", "Close", "14:00", "18:00"],
        ["Dock", "Chen", "Load", "07:00", "11:00"],
        ["", "Jules", "Audit", "11:00", "15:00"],
        ["''", "Ken", "Security", "18:00", "22:00"],
    ]
    draw_table(d, 105, 280, [260, 260, 300, 220, 220], rows, 80)
    return Case(
        "H04-carrydown-rota",
        "Carry-Down Rota Table",
        "tables",
        ["raster-only", "carry-down", "ditto"],
        "Test expansion of blank and ditto cells into faithful Markdown table rows.",
        "Raster-only rota table with blank carry-down cells and ditto marks.",
        ["expanded table rows", "blank-cell policy", "ditto policy"],
        ["Bind inherited group labels to the right row.", "Do not collapse rows with similar times."],
        "# Rota With Carry-Down Cells\n\nKitchen: Ravi Prep 06:00-10:00; Mina Service 10:00-14:00; Omar Close 14:00-18:00.\nDock: Chen Load 07:00-11:00; Jules Audit 11:00-15:00; Ken Security 18:00-22:00.\nBlank team cells inherit the prior team; ditto marks inherit Dock.\n",
        [
            near_check("kitchen-ravi", "tables", ["Kitchen", "Ravi", "Prep", "06:00", "10:00"], 2),
            near_check("kitchen-mina", "tables", ["Kitchen", "Mina", "Service", "10:00", "14:00"], 2),
            near_check("dock-ken", "tables", ["Dock", "Ken", "Security", "18:00", "22:00"], 2),
            all_check("carrydown-policy", "structure", ["blank", "ditto"], 1),
        ],
        [img],
    )


def h05() -> Case:
    img = base_page("Dense State Matrix")
    d = ImageDraw.Draw(img)
    rows = [
        ["Item", "Approve", "Block", "Needs QA"],
        ["Valve A-17", "YES", "NO", "YES"],
        ["Valve A-71", "NO", "YES", "NO"],
        ["Sensor C-08", "NO", "YES", "YES"],
        ["Sensor C-80", "YES", "NO", "NO"],
    ]
    draw_table(d, 105, 300, [420, 270, 270, 300], rows, 86)
    d.text((105, 785), "Near-duplicate labels are intentional: A-17 is not A-71; C-08 is not C-80.", fill="#7f1d1d", font=F["small"])
    return Case(
        "H05-state-matrix",
        "Dense State Matrix",
        "forms",
        ["raster-only", "checkbox", "state-binding"],
        "Bind dense YES/NO states to near-duplicate row labels.",
        "Raster-only state matrix.",
        ["state matrix rows", "row labels", "legend/policy"],
        ["Score row-level state binding.", "Penalize collapsed similar IDs."],
        "# Dense State Matrix\n\nValve A-17: Approve YES, Block NO, Needs QA YES.\nValve A-71: Approve NO, Block YES, Needs QA NO.\nSensor C-08: Approve NO, Block YES, Needs QA YES.\nSensor C-80: Approve YES, Block NO, Needs QA NO.\n",
        [
            near_check("a17-state", "forms", ["Valve A-17", "Approve", "YES", "Block", "NO", "Needs QA", "YES"], 2.5, 380),
            near_check("a71-state", "forms", ["Valve A-71", "Approve", "NO", "Block", "YES", "Needs QA", "NO"], 2.5, 380),
            near_check("c08-state", "forms", ["Sensor C-08", "Approve", "NO", "Block", "YES", "Needs QA", "YES"], 2.5, 380),
            none_check("no-id-substitution", ["A-17/A-71", "C-08/C-80", "same state"], 1.5),
        ],
        [img],
    )


def h06() -> Case:
    img = base_page("Weekly Ops Dashboard")
    d = ImageDraw.Draw(img)
    draw_card(d, (100, 245, 505, 480), "Open defects", ["47", "up 6 vs prior week"], "#fef2f2", "#b91c1c")
    draw_card(d, (555, 245, 960, 480), "Median repair", ["18.6h", "target: 16h"], "#eff6ff", "#1d4ed8")
    draw_card(d, (1010, 245, 1515, 480), "SLA risk", ["12 accounts", "north region"], "#fffbeb", "#b45309")
    d.text((110, 590), "Defects by lane", fill="#111827", font=F["h2"])
    lanes = [("Ingest", 13), ("Visual", 19), ("Table", 17), ("Export", 8)]
    x0, y0 = 170, 930
    for i, (name, value) in enumerate(lanes):
        x = x0 + i * 300
        h = value * 18
        d.rectangle((x, y0 - h, x + 90, y0), fill=["#2563eb", "#dc2626", "#0f766e", "#7c3aed"][i])
        d.text((x + 22, y0 - h - 35), str(value), fill="#111827", font=F["small"])
        d.text((x - 12, y0 + 20), name, fill="#111827", font=F["small"])
    d.line((120, y0, 1420, y0), fill="#111827", width=4)
    d.text((105, 1050), "Visual lane has the most defects; Export has the fewest.", fill="#7f1d1d", font=F["small"])
    return Case(
        "H06-ops-dashboard",
        "Weekly Ops Dashboard",
        "visual",
        ["raster-only", "dashboard", "chart"],
        "Recover KPI cards and chart facts from a dashboard page.",
        "Raster-only dashboard with KPI cards and a bar chart.",
        ["KPI values", "chart labels", "highest/fewest visual facts"],
        ["Bind each KPI value to its card.", "Preserve chart extremum facts.", "Penalize reversed trend claims."],
        "# Weekly Ops Dashboard\n\nOpen defects: 47. Median repair: 18.6h. SLA risk: 12 accounts in north region. Visual lane has the most defects at 19; Export has the fewest at 8.\n",
        [
            near_check("kpi-defects", "visual", ["Open defects", "47"], 1.5, 120),
            near_check("kpi-repair", "visual", ["Median repair", "18.6h"], 1.5, 140),
            near_check("kpi-risk", "visual", ["SLA risk", "12 accounts", "north region"], 1.5, 180),
            near_check("chart-fact", "visual", ["Visual", "19", "Export", "8"], 2.5, 420),
            none_check("no-reversed-trend", ["Export has the most", "Visual has the fewest"], 2),
        ],
        [img],
    )


def h07() -> Case:
    img = base_page("Overlapping GTM Timeline Slide")
    d = ImageDraw.Draw(img)
    d.text((100, 150), "Investor update slide. Read each lane left-to-right; exported cards overlap.", fill="#7f1d1d", font=F["small"])
    months = ["Aug", "Sep", "Oct", "Nov"]
    left, top = 360, 315
    for i, month in enumerate(months):
        x = left + i * 265
        d.text((x + 82, 255), month, fill="#111827", font=F["h2"])
        d.line((x, 305, x, 1190), fill="#e2e8f0", width=4)
    d.line((left + len(months) * 265, 305, left + len(months) * 265, 1190), fill="#e2e8f0", width=4)

    lanes = [("Product", 390), ("Security", 660), ("Sales", 930)]
    for lane, y in lanes:
        d.text((110, y + 52), lane, fill="#111827", font=F["h2"])
        d.line((95, y + 145, 1510, y + 145), fill="#f1f5f9", width=3)

    cards = [
        ("Beta signups", "Maya", "target 1,200", 0.05, 0.85, 390, "#eef2ff", "#4338ca"),
        ("Workflow v2", "Jon", "ship Oct 18", 1.05, 2.35, 430, "#ecfeff", "#0f766e"),
        ("SOC2 audit", "Priya", "fieldwork", 0.1, 2.45, 660, "#fff7ed", "#c2410c"),
        ("HIPAA BAA", "Lena", "legal review", 2.0, 3.55, 700, "#fee2e2", "#991b1b"),
        ("Design partners", "Omar", "9 accounts", 0.0, 0.72, 930, "#f0fdf4", "#15803d"),
        ("Enterprise pilots", "Omar", "$4.2M pipeline", 1.05, 3.75, 970, "#f8fafc", "#334155"),
    ]
    for title, owner, detail, start, end, y, fill, outline in cards:
        x1 = int(left + start * 265)
        x2 = int(left + end * 265)
        d.rounded_rectangle((x1, y, x2, y + 120), radius=18, fill=fill, outline=outline, width=4)
        d.text((x1 + 18, y + 16), title, fill="#111827", font=F["small"])
        d.text((x1 + 18, y + 52), f"Owner: {owner}", fill="#334155", font=F["tiny"])
        d.text((x1 + 18, y + 82), detail, fill="#334155", font=F["tiny"])

    d.rounded_rectangle((1030, 1225, 1510, 1410), radius=16, fill="#fef3c7", outline="#92400e", width=4)
    d.text((1060, 1260), "October dependency", fill="#92400e", font=F["h2"])
    draw_text(d, (1060, 1310), "HIPAA BAA belongs to Security, not Product. Enterprise pilots depend on BAA legal review.", F["small"], fill="#92400e", width=33, leading=28)
    d.text((100, 1475), "Board packet GTM-09 | staffing plan extract | lane ownership and month spans drive the dependency review", fill="#475569", font=F["small"])
    return Case(
        "H07-broken-pitch-slide",
        "Overlapping GTM Timeline Slide",
        "layout",
        ["raster-only", "slide", "overlap", "timeline", "swimlanes"],
        "Recover an overlapping pitch-deck timeline by binding each card to lane, month span, owner, detail, and dependency.",
        "Raster-only investor update slide with month grid, swimlanes, overlapping cards, and dependency note.",
        ["lane-card bindings", "month spans", "owners", "dependency note", "footer"],
        ["Bind each initiative to the correct lane.", "Preserve month spans and owners.", "Do not assign HIPAA BAA to Product."],
        "# Overlapping GTM Timeline Slide\n\nInvestor update slide. Read each lane left-to-right; exported cards overlap.\n\nProduct lane: Beta signups runs in Aug, owner Maya, target 1,200. Workflow v2 runs Sep-Oct, owner Jon, ship Oct 18.\n\nSecurity lane: SOC2 audit runs Aug-Oct, owner Priya, fieldwork. HIPAA BAA runs Oct-Nov, owner Lena, legal review.\n\nSales lane: Design partners runs in Aug, owner Omar, 9 accounts. Enterprise pilots runs Sep-Nov, owner Omar, $4.2M pipeline.\n\nOctober dependency: HIPAA BAA belongs to Security, not Product. Enterprise pilots depend on BAA legal review.\n\nFooter: Board packet GTM-09. Preserve lane, month span, owner, and dependency.\n",
        [
            {"id": "product-beta", "category": "binding", "weight": 2, "description": "product beta card with Aug span", "all": [r"Product[\s\S]{0,500}Beta signups(?=[\s\S]{0,180}Aug)(?=[\s\S]{0,180}Maya)(?=[\s\S]{0,180}1,200)"]},
            {"id": "product-workflow", "category": "binding", "weight": 2.5, "description": "workflow card with Sep-Oct span", "all": [r"Product[\s\S]{0,600}Workflow v2(?=[\s\S]{0,220}(Sep[\s\S]{0,80}Oct|Sep\s*[-–]\s*Oct))(?=[\s\S]{0,220}Jon)(?=[\s\S]{0,220}Oct 18)"]},
            {"id": "security-soc2", "category": "binding", "weight": 2.5, "description": "SOC2 card with Aug-Oct span", "all": [r"Security[\s\S]{0,500}SOC2 audit(?=[\s\S]{0,220}(Aug[\s\S]{0,80}Oct|Aug\s*[-–]\s*Oct))(?=[\s\S]{0,220}Priya)(?=[\s\S]{0,220}fieldwork)"]},
            {"id": "security-hipaa", "category": "binding", "weight": 2.5, "description": "HIPAA card with Oct-Nov span", "all": [r"Security[\s\S]{0,650}HIPAA BAA(?=[\s\S]{0,220}(Oct[\s\S]{0,80}Nov|Oct\s*[-–]\s*Nov))(?=[\s\S]{0,220}Lena)(?=[\s\S]{0,220}legal review)"]},
            {"id": "sales-design", "category": "binding", "weight": 2, "description": "design partners card with Aug span", "all": [r"Sales[\s\S]{0,500}Design partners(?=[\s\S]{0,180}Aug)(?=[\s\S]{0,180}Omar)(?=[\s\S]{0,180}9 accounts)"]},
            {"id": "sales-pilots", "category": "binding", "weight": 2.5, "description": "enterprise pilots card with Sep-Nov span", "all": [r"Sales[\s\S]{0,700}Enterprise pilots(?=[\s\S]{0,260}(Sep[\s\S]{0,100}Nov|Sep\s*[-–]\s*Nov))(?=[\s\S]{0,260}Omar)(?=[\s\S]{0,260}\$4\.2M)"]},
            near_check("dependency", "layout", ["October dependency", "HIPAA BAA", "Security", "not Product", "Enterprise pilots"], 2, 520),
            none_regex_check("no-hipaa-product", [r"HIPAA BAA[\s\S]{0,120}(Product lane|under Product|in Product)"], 2, "binding"),
            none_regex_check("no-design-target-error", [r"Design partners[\s\S]{0,120}1,000", r"target 1,000"], 2, "binding"),
            all_check("footer", "text", ["GTM-09", "lane", "month span"], 1),
        ],
        [img],
    )


def h08() -> Case:
    img = base_page("Complex Financial Table")
    d = ImageDraw.Draw(img)
    d.text((105, 170), "Amounts in USD thousands. Negative numbers are shown in parentheses.", fill="#7f1d1d", font=F["small"])
    rows = [
        ["Segment", "Q1 revenue", "Q1 margin", "Q2 revenue", "Q2 margin", "Note"],
        ["Enterprise", "1,204", "42%", "1,386", "44%", ""],
        ["SMB", "812", "31%", "705", "27%", "B"],
        ["Intercompany", "(72)", "-", "(81)", "-", "elim"],
        ["Total", "1,944", "38%", "2,010", "39%", ""],
    ]
    draw_table(d, 80, 300, [280, 230, 220, 230, 220, 220], rows, 82)
    d.text((105, 820), "Footnote B: SMB Q2 revenue decreased because churn exceeded expansion in the west region.", fill="#111827", font=F["small"])
    d.text((105, 880), "Control total from ERP after adjustments: Q2 revenue 2,010.", fill="#111827", font=F["small"])
    return Case(
        "H08-complex-financial-table",
        "Complex Financial Table",
        "tables",
        ["raster-only", "multi-row-header", "footnotes", "negative-values"],
        "Recover financial table semantics, negative values, units, and footnote association.",
        "Raster-only financial table with multi-column measures and footnotes.",
        ["unit statement", "negative values", "segment rows", "footnote B association"],
        ["Preserve parentheses as negative values.", "Bind SMB footnote to west-region churn.", "Do not make eliminations positive."],
        "# Complex Financial Table\n\nAmounts in USD thousands. Negative numbers are shown in parentheses. Enterprise Q2 revenue is 1,386 with 44% margin. Intercompany eliminations are negative: (72) in Q1 and (81) in Q2. Total Q2 revenue is 2,010. Footnote B says SMB Q2 revenue decreased because churn exceeded expansion in the west region.\n",
        [
            all_check("units", "tables", ["USD thousands", "Negative numbers"], 1),
            near_check("enterprise-q2", "tables", ["Enterprise", "1,386", "44%"], 2),
            near_check("elim-negative", "tables", ["Intercompany", "(72)", "(81)"], 2.5),
            near_check("footnote-b", "tables", ["Footnote B", "SMB", "west region"], 2),
            all_check("total-q2", "tables", ["2,010"], 1),
            none_regex_check("no-positive-elim", [r"Intercompany 72", r"Intercompany.* 72 .* 81"], 2),
        ],
        [img],
    )


def h09() -> Case:
    img = base_page("Insurance Intake Form")
    d = ImageDraw.Draw(img)
    draw_card(d, (95, 230, 835, 570), "Claim fields", ["Claim ID: CLM-2026-884", "Member: REDACTED SAMPLE", "Plan: Silver HMO", "Prior auth: BLANK"], "#f8fafc")
    d.text((980, 250), "Coverage requested", fill="#111827", font=F["h2"])
    checkbox(d, 985, 320, "Emergency", True)
    checkbox(d, 985, 385, "Out-of-network", True)
    checkbox(d, 985, 450, "Dental", False)
    checkbox(d, 985, 515, "Vision", False)
    d.rounded_rectangle((180, 720, 730, 850), radius=16, fill="#fee2e2", outline="#991b1b", width=5)
    d.text((230, 765), "REVIEW REQUIRED", fill="#991b1b", font=F["stamp"])
    d.text((980, 760), "Signature: J. Patel", fill="#111827", font=F["italic"])
    return Case(
        "H09-insurance-form",
        "Insurance Intake Form",
        "forms",
        ["raster-only", "checkbox", "stamp", "blank-field"],
        "Reconstruct selected and blank form fields without inventing values.",
        "Raster-only insurance-style intake form with selected/unselected boxes, stamp, and signature.",
        ["claim fields", "blank prior auth", "checkbox states", "stamp/signature"],
        ["Mark prior auth as blank.", "Distinguish selected from unselected coverage boxes.", "Preserve review stamp and signature."],
        "# Insurance Intake Form\n\nClaim ID CLM-2026-884. Member REDACTED SAMPLE. Plan Silver HMO. Prior auth is blank. Emergency and Out-of-network are selected; Dental and Vision are unselected. Stamp: REVIEW REQUIRED. Signature: J. Patel.\n",
        [
            near_check("claim-plan", "forms", ["CLM-2026-884", "Silver HMO"], 1.5, 180),
            near_check("prior-blank", "forms", ["Prior auth", "blank"], 2, 160),
            {
                "id": "selected-coverage",
                "category": "forms",
                "weight": 2,
                "description": "selected coverage boxes",
                "all": [
                    r"(\[x\]\s*Emergency|☑\s*Emergency|Emergency.{0,50}selected)",
                    r"(\[x\]\s*Out-of-network|☑\s*Out-of-network|Out-of-network.{0,50}selected)",
                ],
            },
            {
                "id": "unselected-coverage",
                "category": "forms",
                "weight": 2,
                "description": "unselected coverage boxes",
                "all": [
                    r"(\[\s\]\s*Dental|☐\s*Dental|Dental.{0,50}unselected)",
                    r"(\[\s\]\s*Vision|☐\s*Vision|Vision.{0,50}unselected)",
                ],
            },
            all_check("stamp-signature", "visual", ["REVIEW REQUIRED", "J. Patel"], 2),
        ],
        [img],
    )


def h10() -> Case:
    pages = []
    for page_i, (title, rows) in enumerate(
        [
            (
                "Continuation Register - page 1",
                [
                    ["Group", "ID", "Owner", "Status", "Due"],
                    ["Alpha", "A-100", "Mira", "open", "Aug 02"],
                    ["", "A-101", "Mira", "blocked", "Aug 05"],
                    ["", "A-102", "Noor", "open", "Aug 08"],
                    ["Beta", "B-200", "Priya", "review", "Aug 09"],
                    ["", "B-201", "Priya", "open", "Aug 11"],
                ],
            ),
            (
                "Continuation Register - page 2",
                [
                    ["Group", "ID", "Owner", "Status", "Due"],
                    ["''", "B-202", "Ken", "blocked", "Aug 12"],
                    ["Gamma", "G-300", "Lina", "closed", "done"],
                    ["", "G-301", "Omar", "open", "Aug 19"],
                ],
            ),
        ]
    ):
        img = base_page(title)
        d = ImageDraw.Draw(img)
        d.text((105, 170), "Blank group cells inherit the previous group; ditto on page 2 continues Beta.", fill="#7f1d1d", font=F["small"])
        draw_table(d, 105, 285, [300, 260, 260, 260, 260], rows, 82)
        d.text((105, 1180), f"Page {page_i + 1} of 2", fill="#475569", font=F["small"])
        pages.append(img)
    return Case(
        "H10-continuation-register",
        "Continuation Register",
        "tables",
        ["raster-only", "multi-page-table", "carry-down"],
        "Recover a multi-page continued table with inherited group labels.",
        "Two raster pages with repeated headers, blank cells, and a ditto continuation.",
        ["continued table", "expanded group labels", "page policy"],
        ["Bind inherited groups across pages.", "Preserve blocked/open statuses with correct owners and due dates."],
        "# Continuation Register\n\nAlpha: A-100 Mira open Aug 02; A-101 Mira blocked Aug 05; A-102 Noor open Aug 08. Beta: B-200 Priya review Aug 09; B-201 Priya open Aug 11; B-202 Ken blocked Aug 12. Gamma: G-300 Lina closed done; G-301 Omar open Aug 19. Blank cells inherit the previous group; ditto on page 2 continues Beta.\n",
        [
            near_check("alpha-a101", "tables", ["Alpha", "A-101", "Mira", "blocked", "Aug 05"], 2.5, 320),
            near_check("beta-b202", "tables", ["Beta", "B-202", "Ken", "blocked", "Aug 12"], 2.5, 320),
            near_check("gamma-g301", "tables", ["Gamma", "G-301", "Omar", "open", "Aug 19"], 2.5, 320),
            all_check("continuation-policy", "structure", ["blank", "ditto"], 1),
        ],
        pages,
    )


def h11() -> Case:
    img = base_page("Two-Column Incident Report")
    d = ImageDraw.Draw(img)
    d.text((100, 180), "Main finding", fill="#111827", font=F["h2"])
    draw_text(d, (100, 230), "Outage began at 09:14 UTC when queue shard QS-7 stopped acknowledging writes.", F["body"], width=42)
    d.text((100, 455), "Mitigation", fill="#111827", font=F["h2"])
    draw_text(d, (100, 505), "Operators drained QS-7, replayed 418 jobs, and restored normal export latency by 10:02 UTC.", F["body"], width=42)
    d.rounded_rectangle((980, 210, 1540, 620), radius=16, fill="#fef3c7", outline="#92400e", width=4)
    d.text((1015, 245), "Sidebar", fill="#92400e", font=F["h2"])
    draw_text(d, (1015, 300), "Reviewer note: do not place this sidebar before the main finding.", F["small"], fill="#92400e", width=34, leading=30)
    d.text((100, 790), "Figure 2: queue replay path", fill="#111827", font=F["h2"])
    labels = ["QS-7", "replay buffer", "export workers", "customer files"]
    for i, label in enumerate(labels):
        x = 130 + i * 360
        d.rounded_rectangle((x, 870, x + 260, 960), radius=14, fill="#dbeafe", outline="#1d4ed8", width=3)
        d.text((x + 28, 898), label, fill="#111827", font=F["small"])
        if i < len(labels) - 1:
            d.line((x + 270, 915, x + 345, 915), fill="#111827", width=5)
    d.text((100, 1170), "Footer: IR-2026-31 page 1 of 1", fill="#475569", font=F["small"])
    return Case(
        "H11-two-column-sidebar",
        "Two-Column Incident Report",
        "layout",
        ["raster-only", "multi-column", "sidebar", "figure"],
        "Test reading order across main column, sidebar, figure, and footer.",
        "Raster-only two-column incident report with sidebar callout and flow figure.",
        ["main finding", "mitigation", "sidebar", "figure path", "footer"],
        ["Main finding and mitigation should precede sidebar.", "Figure path should be described inline.", "Footer ID should be retained."],
        "# Two-Column Incident Report\n\nMain finding: outage began at 09:14 UTC when queue shard QS-7 stopped acknowledging writes. Mitigation: operators drained QS-7, replayed 418 jobs, and restored normal export latency by 10:02 UTC. Sidebar reviewer note: do not place this sidebar before the main finding. Figure 2: queue replay path QS-7 -> replay buffer -> export workers -> customer files. Footer: IR-2026-31 page 1 of 1.\n",
        [
            ordered_check("reading-order", "layout", ["Main finding", "Mitigation", "Sidebar", "Figure 2", "IR-2026-31"], 2.5),
            near_check("mitigation", "text", ["QS-7", "418 jobs", "10:02 UTC"], 2.5),
            all_check("figure-path", "visual", ["replay buffer", "export workers", "customer files"], 2),
        ],
        [img],
    )


def h12() -> Case:
    img = base_page("Bilingual Service Credit")
    d = ImageDraw.Draw(img)
    draw_card(d, (100, 245, 1480, 690), "Aviso de credito / Credit notice", ["Caso / Case: SRV-88-ES", "Cliente / Customer: Jardin Norte", "Credit applied: $128.40", "Factura / Invoice: INV-771", "Motivo: demora de servicio, 12 dias"], "#f8fafc")
    d.text((130, 790), "Confirmaciones / Confirmations", fill="#111827", font=F["h2"])
    checkbox(d, 140, 860, "Cliente informado / Customer informed", True)
    checkbox(d, 140, 930, "Pieza pendiente / Part pending", False)
    d.text((130, 1050), "Proxima visita / Next visit: 2026-09-04 with tecnico Luis", fill="#111827", font=F["body"])
    d.text((130, 1125), "Policy: unchecked pending part means no part is pending.", fill="#7f1d1d", font=F["small"])
    return Case(
        "H12-bilingual-credit",
        "Bilingual Service Credit",
        "forms",
        ["raster-only", "bilingual", "checkbox"],
        "Recover bilingual form fields and checkbox state without flipping unchecked state.",
        "Raster-only bilingual service-credit form.",
        ["Spanish/English labels", "credit amount", "invoice", "checkbox states"],
        ["Preserve bilingual values.", "Bind service delay and next visit.", "Do not mark pending part as selected."],
        "# Bilingual Service Credit\n\nCaso / Case: SRV-88-ES. Cliente / Customer: Jardin Norte. Credit applied: $128.40 for invoice INV-771. Motivo: demora de servicio, 12 dias. Proxima visita / Next visit: 2026-09-04 with tecnico Luis. Cliente informado is selected; Pieza pendiente is unselected.\n",
        [
            all_check("case-id", "text", ["SRV-88-ES"], 0.6),
            {"id": "customer", "category": "text", "weight": 0.4, "description": "customer name", "all": [r"Jard[ií]n Norte"]},
            all_check("amount-invoice", "text", ["$128.40", "INV-771"], 0.5),
            near_check("reason-visit", "forms", ["demora de servicio", "12 dias", "2026-09-04", "Luis"], 2.5, 360),
            {
                "id": "customer-informed-checked",
                "category": "forms",
                "weight": 2,
                "description": "customer informed checkbox is checked",
                "all": [r"(\[x\]\s*Cliente informado|☑\s*Cliente informado|Cliente informado[\s\S]{0,80}(selected|checked))"],
            },
            {
                "id": "pending-part-unchecked",
                "category": "forms",
                "weight": 2.5,
                "description": "pending part checkbox is unchecked",
                "all": [r"(\[\s\]\s*Pieza pendiente|☐\s*Pieza pendiente|Pieza pendiente[\s\S]{0,80}(unselected|unchecked|no part is pending))"],
            },
            none_regex_check("no-pending-selected", [r"\[x\]\s*Pieza pendiente", r"☑\s*Pieza pendiente", r"Pieza pendiente selected", r"Part pending selected", r"Pieza pendiente checked", r"Part pending checked"], 2.5),
        ],
        [img],
    )


def h13() -> Case:
    img = base_page("Sparse Retrieval Paper Excerpt")
    d = ImageDraw.Draw(img)
    d.text((100, 150), "Sparse Retrieval With Patch Reranking", fill="#111827", font=F["h1"])
    d.text((104, 205), "A. Rao, L. Chen, M. Iqbal", fill="#475569", font=F["small"])
    d.rounded_rectangle((100, 255, 1580, 420), radius=12, fill="#f8fafc", outline="#64748b", width=3)
    draw_text(
        d,
        (130, 285),
        "Abstract: We evaluate a patch reranker that improves table-region recall without changing OCR. The main result is a 6.3 point F1 gain on scanned appendices.",
        F["small"],
        width=112,
        leading=29,
    )

    left_x, mid_x, right_x = 95, 615, 1125
    y = 485
    d.text((left_x, y), "1. Method", fill="#111827", font=F["h2"])
    draw_text(d, (left_x, y + 45), "The parser emits proposed blocks, then applies a patch reranker only to regions marked table-like or figure-like.", F["small"], width=34, leading=29)
    d.text((left_x, 735), "Equation 1", fill="#111827", font=F["small"])
    d.rounded_rectangle((left_x, 775, left_x + 430, 855), radius=10, fill="#eef2ff", outline="#4338ca", width=3)
    d.text((left_x + 22, 802), "score = 0.62*T + 0.28*V + 0.10*R", fill="#111827", font=F["tiny"])
    d.text((left_x, 900), "Table 1. Ablation", fill="#111827", font=F["small"])
    draw_table(
        d,
        left_x,
        940,
        [160, 130, 130],
        [["Variant", "Recall", "F1"], ["base", "71.4", "68.2"], ["+patch", "80.1", "74.5"], ["+caption", "82.0", "75.1"]],
        58,
    )

    d.text((mid_x, y), "2. Results", fill="#111827", font=F["h2"])
    draw_text(d, (mid_x, y + 45), "The caption-aware variant is strongest, but most of the gain comes from patch reranking. Failure cases cluster around equation/table boundaries.", F["small"], width=35, leading=29)
    d.text((mid_x, 720), "Figure 2. Retrieval path", fill="#111827", font=F["small"])
    nodes = [("PDF page", 635, 780), ("patch grid", 835, 780), ("reranker", 735, 930), ("Markdown blocks", 640, 1080)]
    for label, x, yy in nodes:
        d.rounded_rectangle((x, yy, x + 180, yy + 68), radius=12, fill="#ecfeff", outline="#0f766e", width=3)
        d.text((x + 16, yy + 22), label, fill="#111827", font=F["tiny"])
    d.line((815, 814, 835, 814), fill="#111827", width=4)
    d.line((925, 848, 835, 930), fill="#111827", width=4)
    d.line((735, 998, 710, 1080), fill="#111827", width=4)
    d.text((mid_x, 1190), "Caption: patch grid feeds the reranker before Markdown block assembly.", fill="#475569", font=F["tiny"])

    d.text((right_x, y), "3. Limitations", fill="#111827", font=F["h2"])
    draw_text(d, (right_x, y + 45), "The model still confuses marginal notes with captions when the note touches a figure border. Rotated labels were excluded from the pilot.", F["small"], width=33, leading=29)
    d.rounded_rectangle((right_x, 760, 1580, 1020), radius=14, fill="#fff7ed", outline="#c2410c", width=3)
    d.text((right_x + 20, 790), "Reviewer note", fill="#c2410c", font=F["small"])
    draw_text(d, (right_x + 20, 830), "Do not read this box before the Results section; it comments on Figure 2.", F["tiny"], fill="#9a3412", width=34, leading=25)
    d.text((105, 1370), "Footnote 1: F1 is macro-averaged over pages, not documents.", fill="#475569", font=F["tiny"])
    return Case(
        "H13-scientific-two-column",
        "Scientific Paper With Embedded Table And Figure",
        "layout",
        ["raster-only", "scientific-paper", "multi-column", "table", "figure", "footnote"],
        "Recover paper reading order while preserving embedded table, equation, figure, sidebar, and footnote.",
        "Raster-only scientific page with three text columns and embedded visual objects.",
        ["abstract", "method equation", "ablation table", "figure path", "limitations", "reviewer note", "footnote"],
        ["Preserve abstract before sections.", "Bind ablation values to variants.", "Describe Figure 2 path after results.", "Do not move reviewer note before results."],
        "# Sparse Retrieval With Patch Reranking\n\nAbstract: We evaluate a patch reranker that improves table-region recall without changing OCR. The main result is a 6.3 point F1 gain on scanned appendices.\n\n## 1. Method\n\nThe parser emits proposed blocks, then applies a patch reranker only to regions marked table-like or figure-like.\n\nEquation 1: score = 0.62*T + 0.28*V + 0.10*R.\n\nTable 1. Ablation: base recall 71.4 and F1 68.2; +patch recall 80.1 and F1 74.5; +caption recall 82.0 and F1 75.1.\n\n## 2. Results\n\nThe caption-aware variant is strongest, but most of the gain comes from patch reranking. Failure cases cluster around equation/table boundaries.\n\nFigure 2 retrieval path: PDF page -> patch grid -> reranker -> Markdown blocks. Caption: patch grid feeds the reranker before Markdown block assembly.\n\n## 3. Limitations\n\nThe model still confuses marginal notes with captions when the note touches a figure border. Rotated labels were excluded from the pilot.\n\nReviewer note: Do not read this box before the Results section; it comments on Figure 2.\n\nFootnote 1: F1 is macro-averaged over pages, not documents.\n",
        [
            ordered_check("paper-reading-order", "layout", ["Abstract", "1. Method", "Equation 1", "Table 1", "2. Results", "Figure 2", "3. Limitations", "Reviewer note", "Footnote 1"], 3),
            near_check("ablation-patch", "tables", ["+patch", "80.1", "74.5"], 2, 220),
            near_check("ablation-caption", "tables", ["+caption", "82.0", "75.1"], 2, 220),
            ordered_check("figure-path", "visual", ["PDF page", "patch grid", "reranker", "Markdown blocks"], 2.5),
            all_check("equation", "text", ["0.62", "0.28", "0.10"], 1.5),
            all_check("footnote", "text", ["macro-averaged", "pages", "not documents"], 1.5),
        ],
        [img],
    )


def h14() -> Case:
    img = base_page("Borderless Team Matrix Pitch Slide")
    d = ImageDraw.Draw(img)
    d.text((100, 150), "Series A team slide. Names are column headers; facts below align vertically.", fill="#7f1d1d", font=F["small"])
    d.text((100, 230), "Core team", fill="#111827", font=F["h1"])
    d.text((100, 280), "Borderless matrix exported from slides. Preserve each person-to-fact binding.", fill="#475569", font=F["small"])

    names = [
        ("Maya Singh", "CEO / Product", "ex-Stripe", "12 yrs product", "led Relay launch", "#0f766e"),
        ("Jon Bell", "CTO / Infra", "ex-Snowflake", "owns retrieval infra", "built vector cache", "#1d4ed8"),
        ("Priya Nair", "COO / Ops", "ex-Flexport", "scaled support", "owns compliance", "#a16207"),
        ("Omar Haddad", "GTM / RevOps", "ex-Atlassian", "pipeline $4.2M", "leads enterprise sales", "#be123c"),
    ]
    row_labels = ["Role", "Former", "Proof", "Owns"]
    x0, col_w = 340, 305
    row_ys = [590, 710, 830, 950]
    for i, label in enumerate(row_labels):
        d.text((110, row_ys[i] + 6), label, fill="#64748b", font=F["small"])
        d.line((250, row_ys[i] + 34, 1525, row_ys[i] + 34), fill="#e2e8f0", width=3)

    for idx, (name, role, former, proof, owns, color) in enumerate(names):
        x = x0 + idx * col_w
        d.line((x - 38, 350, x - 38, 1040), fill="#f1f5f9", width=4)
        d.ellipse((x + 70, 365, x + 170, 465), fill="#f8fafc", outline=color, width=5)
        initials = "".join(part[0] for part in name.split())
        d.text((x + 100, 394), initials, fill=color, font=F["h2"])
        d.text((x, 495), name, fill="#111827", font=F["h2"])
        d.text((x, 590), role, fill="#111827", font=F["small"])
        d.text((x, 710), former, fill="#111827", font=F["small"])
        d.text((x, 830), proof, fill="#111827", font=F["small"])
        d.text((x, 950), owns, fill="#111827", font=F["small"])

    d.rounded_rectangle((100, 1135, 760, 1360), radius=14, fill="#ecfeff", outline="#0f766e", width=3)
    d.text((130, 1170), "Advisors", fill="#0f766e", font=F["h2"])
    d.text((130, 1230), "Lena Ortiz - former CISO, Okta", fill="#111827", font=F["small"])
    d.text((130, 1290), "Theo Park - ex-CFO, Datadog", fill="#111827", font=F["small"])

    d.rounded_rectangle((855, 1135, 1510, 1360), radius=14, fill="#fff7ed", outline="#c2410c", width=3)
    d.text((885, 1170), "Hiring next", fill="#c2410c", font=F["h2"])
    d.text((885, 1230), "VP Sales - Q4", fill="#111827", font=F["small"])
    d.text((885, 1290), "Clinical Lead - Q1", fill="#111827", font=F["small"])

    d.text((100, 1450), "Footer: Deck v12. Advisors are not core team members. Hiring rows are open roles, not current employees.", fill="#475569", font=F["small"])
    return Case(
        "H14-three-column-poster",
        "Borderless Team Matrix Pitch Slide",
        "layout",
        ["raster-only", "pitch-slide", "borderless-table", "team-matrix", "advisor-sidebar"],
        "Recover a borderless pitch-deck team matrix by binding facts under each name column.",
        "Raster-only pitch slide with names as column headers, unlabeled visual alignment, advisor sidebar, and open-role box.",
        ["person-to-fact bindings", "row label semantics", "advisors separate from core team", "hiring roles separate from employees", "footer"],
        ["Bind each person to role, former company, proof, and ownership facts.", "Do not merge row-wise facts across people.", "Do not treat advisors or open roles as core team members."],
        "# Borderless Team Matrix Pitch Slide\n\nCore team: Maya Singh is CEO / Product, ex-Stripe, has 12 yrs product experience, and led Relay launch. Jon Bell is CTO / Infra, ex-Snowflake, owns retrieval infra, and built vector cache. Priya Nair is COO / Ops, ex-Flexport, scaled support, and owns compliance. Omar Haddad is GTM / RevOps, ex-Atlassian, has pipeline $4.2M, and leads enterprise sales.\n\nAdvisors: Lena Ortiz - former CISO, Okta. Theo Park - ex-CFO, Datadog.\n\nHiring next: VP Sales - Q4. Clinical Lead - Q1.\n\nFooter: Deck v12. Advisors are not core team members. Hiring rows are open roles, not current employees.\n",
        [
            near_check("maya-binding", "binding", ["Maya Singh", "CEO", "Stripe", "Relay launch"], 2.5, 420),
            near_check("jon-binding", "binding", ["Jon Bell", "CTO", "Snowflake", "vector cache"], 2.5, 420),
            near_check("priya-binding", "binding", ["Priya Nair", "COO", "Flexport", "compliance"], 2.5, 420),
            near_check("omar-binding", "binding", ["Omar Haddad", "GTM", "Atlassian", "$4.2M"], 2.5, 420),
            near_check("advisors-separate", "structure", ["Advisors", "Lena Ortiz", "Okta", "Theo Park", "Datadog"], 2, 520),
            near_check("hiring-separate", "structure", ["Hiring next", "VP Sales", "Q4", "Clinical Lead", "Q1"], 1.5, 420),
            all_check("footer", "text", ["Deck v12", "Advisors are not core team members", "open roles"], 1),
            {"id": "no-advisor-as-core", "category": "binding", "weight": 2, "description": "advisors not bound as core employees", "none": [r"Lena Ortiz[\s\S]{0,120}(CEO|CTO|COO|GTM)", r"Theo Park[\s\S]{0,120}(CEO|CTO|COO|GTM)"]},
        ],
        [img],
    )


def h15() -> Case:
    img = base_page("Landscape Heatmap Escalation Plan")
    d = ImageDraw.Draw(img)
    d.text((100, 150), "Reliability escalation matrix - week 32 operations review", fill="#475569", font=F["small"])
    x0, y0 = 140, 370
    teams = ["API", "Data", "Export", "Billing"]
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    vals = [
        ["G", "Y", "Y", "R", "R", "Y"],
        ["G", "G", "Y", "Y", "R", "R"],
        ["Y", "Y", "R", "R", "Y", "G"],
        ["G", "Y", "G", "Y", "Y", "R"],
    ]
    legend = {"G": ("green", "#dcfce7"), "Y": ("yellow", "#fef3c7"), "R": ("red", "#fee2e2")}
    d.text((x0 + 260, 270), "Escalation heatmap: color + letter both matter", fill="#111827", font=F["h2"])
    for i, day in enumerate(days):
        d.text((x0 + 260 + i * 190, y0 - 45), day, fill="#111827", font=F["small"])
    for r, team in enumerate(teams):
        y = y0 + r * 120
        d.text((x0, y + 38), team, fill="#111827", font=F["small"])
        for c, day in enumerate(days):
            key = vals[r][c]
            x = x0 + 240 + c * 190
            d.rectangle((x, y, x + 145, y + 86), fill=legend[key][1], outline="#111827", width=3)
            d.text((x + 58, y + 28), key, fill="#111827", font=F["small"])
            if (team, day) in [("API", "Thu"), ("Data", "Fri"), ("Export", "Wed"), ("Billing", "Sat")]:
                d.line((x + 10, y + 10, x + 135, y + 76), fill="#991b1b", width=4)
    d.rounded_rectangle((105, 880, 600, 1110), radius=14, fill="#f8fafc", outline="#334155", width=3)
    draw_text(d, (135, 915), "Legend: G green normal; Y yellow watch; R red escalation. Diagonal slash means owner must page incident lead.", F["small"], width=34, leading=29)
    d.rounded_rectangle((710, 880, 1510, 1110), radius=14, fill="#fff7ed", outline="#c2410c", width=3)
    draw_text(d, (740, 915), "Operations note: red slash cells trigger incident-lead paging. Export Friday remains a yellow watch cell after the weekend staffing review.", F["small"], width=58, leading=29)
    d.text((105, 1240), "Note: weekend columns are part of the table and must not be dropped.", fill="#111827", font=F["small"])
    return Case(
        "H15-landscape-heatmap",
        "Landscape Heatmap Escalation Plan",
        "tables",
        ["raster-only", "landscape-insert", "heatmap", "diagonal-mark", "wide-table"],
        "Recover a wide heatmap table with color/letter states, slash markers, legend, and weekend columns.",
        "Raster-only page with a landscape-style heatmap embedded in portrait.",
        ["wide matrix", "legend", "critical red slash cells", "yellow not red distinction", "weekend columns"],
        ["Preserve team/day/state bindings.", "Describe slash semantics.", "Do not drop Saturday."],
        "# Landscape Heatmap Escalation Plan\n\nReliability escalation matrix - week 32 operations review.\n\n## Escalation heatmap: color + letter both matter\n\n| Team | Mon | Tue | Wed | Thu | Fri | Sat |\n| --- | --- | --- | --- | --- | --- | --- |\n| API | G | Y | Y | R with slash | R | Y |\n| Data | G | G | Y | Y | R with slash | R |\n| Export | Y | Y | R with slash | R | Y | G |\n| Billing | G | Y | G | Y | Y | R with slash |\n\nLegend: G green normal; Y yellow watch; R red escalation. A diagonal slash means the owner must page the incident lead.\n\nOperations note: red slash cells trigger incident-lead paging. Export Friday remains a yellow watch cell after the weekend staffing review.\n\nCritical red slash cells: API Thu, Data Fri, Export Wed, and Billing Sat. Export Fri is yellow, not red. Weekend columns are part of the table and must not be dropped.\n",
        [
            all_check("legend", "text", ["green normal", "yellow watch", "red escalation", "slash"], 2),
            near_check("api-thu", "tables", ["API", "Thu", "red", "slash"], 2.5, 420),
            near_check("data-fri", "tables", ["Data", "Fri", "red", "slash"], 2.5, 420),
            near_check("billing-sat", "tables", ["Billing", "Sat", "red", "slash"], 2.5, 420),
            {"id": "export-fri-yellow", "category": "binding", "weight": 2.5, "description": "export-fri-yellow", "all": [r"Export[\s\S]{0,220}(Fri|Y|yellow)"], "none": [r"Export[\s\S]{0,120}Fri[\s\S]{0,80}(red|R with slash)", r"Export Fri red"]},
            all_check("weekend", "structure", ["Sat", "weekend"], 1.5),
        ],
        [img],
    )


def h16() -> Case:
    img = base_page("Multi-Panel Metrics Report")
    d = ImageDraw.Draw(img)
    d.text((100, 150), "Operations metrics: panels must be described inline, not summarized.", fill="#7f1d1d", font=F["small"])
    # Panel A line chart
    d.rounded_rectangle((90, 250, 790, 760), radius=14, fill="#f8fafc", outline="#334155", width=3)
    d.text((120, 285), "Panel A. Queue depth", fill="#111827", font=F["h2"])
    axes_x, axes_y = 160, 680
    d.line((axes_x, axes_y, 720, axes_y), fill="#111827", width=3)
    d.line((axes_x, axes_y, axes_x, 360), fill="#111827", width=3)
    points = [(180, 620), (300, 575), (420, 500), (540, 430), (660, 390)]
    for a, b in zip(points, points[1:]):
        d.line((*a, *b), fill="#2563eb", width=5)
    for p, label in zip(points, ["12", "18", "29", "41", "47"]):
        d.ellipse((p[0] - 7, p[1] - 7, p[0] + 7, p[1] + 7), fill="#2563eb")
        d.text((p[0] - 10, p[1] - 35), label, fill="#111827", font=F["tiny"])
    d.text((610, 700), "Fri", fill="#111827", font=F["tiny"])

    # Panel B stacked bars
    d.rounded_rectangle((900, 250, 1590, 760), radius=14, fill="#f8fafc", outline="#334155", width=3)
    d.text((930, 285), "Panel B. Defect mix", fill="#111827", font=F["h2"])
    bars = [("Ingest", 12, 5), ("Visual", 21, 19), ("Tables", 10, 17)]
    for i, (name, low, high) in enumerate(bars):
        x = 990 + i * 180
        yb = 660
        d.rectangle((x, yb - low * 8, x + 70, yb), fill="#93c5fd", outline="#1d4ed8", width=2)
        d.rectangle((x, yb - (low + high) * 8, x + 70, yb - low * 8), fill="#fca5a5", outline="#b91c1c", width=2)
        d.text((x + 22, yb - low * 4 - 8), str(low), fill="#111827", font=F["tiny"])
        d.text((x + 22, yb - (low + high) * 8 + high * 4 - 8), str(high), fill="#111827", font=F["tiny"])
        d.text((x - 15, yb + 20), name, fill="#111827", font=F["tiny"])
    d.text((930, 700), "Red = severe; blue = minor. Use segment labels, not total height.", fill="#475569", font=F["tiny"])

    # Panel C matrix and callout
    d.rounded_rectangle((90, 870, 790, 1290), radius=14, fill="#f8fafc", outline="#334155", width=3)
    d.text((120, 905), "Panel C. Owner matrix", fill="#111827", font=F["h2"])
    draw_table(d, 120, 965, [190, 160, 160, 160], [["Owner", "Open", "Aged", "SLA"], ["Noor", "14", "6", "risk"], ["Mira", "9", "1", "ok"], ["Ken", "24", "11", "risk"]], 62)
    d.rounded_rectangle((900, 900, 1590, 1230), radius=14, fill="#fef3c7", outline="#92400e", width=3)
    draw_text(d, (930, 940), "Reviewer instruction: describe each panel separately, then state one cross-panel warning. Do not copy panel titles as a substitute for chart facts.", F["small"], fill="#92400e", width=48, leading=31)
    return Case(
        "H16-multipanel-metrics",
        "Multi-Panel Metrics Report",
        "visual",
        ["raster-only", "multi-panel", "line-chart", "stacked-bar", "matrix", "callout"],
        "Recover facts from multiple chart panels and avoid confusing severe counts with totals.",
        "Raster-only metrics page with line chart, stacked bar chart, matrix, and narrative callout.",
        ["Panel A trend", "Panel B severe/minor legend", "Panel C owner matrix", "callout warning"],
        ["State Friday queue depth.", "Identify Visual severe defects.", "Bind Ken aged count.", "Do not say Tables has most severe defects."],
        "# Multi-Panel Metrics Report\n\nOperations metrics: panels must be described inline, not summarized.\n\n## Panel A. Queue depth\n\nQueue depth rises every day with values 12, 18, 29, 41, and 47. It ends at 47 on Friday.\n\n## Panel B. Defect mix\n\nRed means severe and blue means minor. Segment labels should be used, not total bar height.\n\n| Lane | Minor / blue | Severe / red |\n| --- | ---: | ---: |\n| Ingest | 12 | 5 |\n| Visual | 21 | 19 |\n| Tables | 10 | 17 |\n\nVisual has the most severe defects, with 19 severe defects. Tables has 17 severe defects and does not have the most severe defects.\n\n## Panel C. Owner matrix\n\n| Owner | Open | Aged | SLA |\n| --- | ---: | ---: | --- |\n| Noor | 14 | 6 | risk |\n| Mira | 9 | 1 | ok |\n| Ken | 24 | 11 | risk |\n\nReviewer instruction: describe each panel separately, then state one cross-panel warning. Do not copy panel titles as a substitute for chart facts.\n\nCross-panel warning: Ken has the highest aged count at 11. The defect mix warning is severe Visual defects, not total Tables defects.\n",
        [
            {"id": "queue-friday", "category": "visual", "weight": 2.5, "description": "queue-friday", "all": [r"Queue depth", r"(Friday|Fri)", r"47"]},
            near_check("visual-severe", "visual", ["Visual", "severe", "19"], 2.5, 260),
            near_check("ken-aged", "tables", ["Ken", "24", "11", "risk"], 2.5, 260),
            near_check("noor-row", "tables", ["Noor", "14", "6", "risk"], 2, 260),
            none_regex_check("no-wrong-severe", [r"Tables has the most severe", r"Tables.*most severe"], 2),
        ],
        [img],
    )


def h17() -> Case:
    img = base_page("Redlined Data Processing Addendum")
    d = ImageDraw.Draw(img)
    d.text((100, 160), "Visible redline policy: include inserted text, describe deleted text as deleted, do not treat deleted text as current.", fill="#7f1d1d", font=F["small"])
    d.text((100, 250), "Section 4. Data return", fill="#111827", font=F["h2"])
    draw_text(d, (105, 305), "Processor must return Customer Data within 10 business days after termination.", F["small"], width=72, leading=31)
    d.text((105, 405), "Old text:", fill="#991b1b", font=F["small"])
    d.text((225, 405), "within 30 calendar days", fill="#991b1b", font=F["small"])
    d.line((225, 421, 490, 421), fill="#991b1b", width=4)
    d.text((520, 405), "Deleted", fill="#991b1b", font=F["tiny"])
    d.text((105, 475), "Inserted:", fill="#15803d", font=F["small"])
    d.text((245, 475), "within 10 business days", fill="#15803d", font=F["small"])
    d.rectangle((240, 468, 545, 510), outline="#15803d", width=3)
    d.text((100, 610), "Section 5. Audit logs", fill="#111827", font=F["h2"])
    draw_text(d, (105, 665), "Processor must retain audit logs for 400 days and provide export within 48 hours of written request.", F["small"], width=74, leading=31)
    d.text((105, 765), "Deleted phrase:", fill="#991b1b", font=F["small"])
    d.text((300, 765), "commercially reasonable efforts", fill="#991b1b", font=F["small"])
    d.line((300, 781, 665, 781), fill="#991b1b", width=4)
    d.text((980, 300), "Comment A", fill="#92400e", font=F["h2"])
    d.rounded_rectangle((955, 350, 1510, 530), radius=14, fill="#fef3c7", outline="#92400e", width=3)
    draw_text(d, (985, 385), "Legal asks whether 10 business days is acceptable for regulated customers.", F["small"], fill="#92400e", width=38, leading=29)
    d.text((980, 650), "Comment B", fill="#92400e", font=F["h2"])
    d.rounded_rectangle((955, 700, 1510, 880), radius=14, fill="#fef3c7", outline="#92400e", width=3)
    draw_text(d, (985, 735), "Security accepts 400 days. Do not restore the deleted efforts language.", F["small"], fill="#92400e", width=38, leading=29)
    d.text((105, 1040), "Signature block remains unchanged: NovaCloud / Atlas Retail.", fill="#111827", font=F["small"])
    return Case(
        "H17-redlined-contract",
        "Redlined Data Processing Addendum",
        "layout",
        ["raster-only", "redline", "contract", "margin-comments", "deleted-text"],
        "Recover current contract text while preserving redline semantics and margin comments.",
        "Raster-only contract excerpt with insertions, deletions, and side comments.",
        ["current clause text", "deleted text marked deleted", "inserted text current", "margin comments", "signature block"],
        ["Do not treat deleted 30 calendar days as current.", "Preserve 10 business days and 400 days.", "Keep comments as comments."],
        "# Redlined Data Processing Addendum\n\nVisible redline policy: include inserted text, describe deleted text as deleted, do not treat deleted text as current.\n\nSection 4. Data return: Processor must return Customer Data within 10 business days after termination. Deleted old text: within 30 calendar days. Inserted text: within 10 business days. Comment A: Legal asks whether 10 business days is acceptable for regulated customers.\n\nSection 5. Audit logs: Processor must retain audit logs for 400 days and provide export within 48 hours of written request. Deleted phrase: commercially reasonable efforts. Comment B: Security accepts 400 days and says not to restore the deleted efforts language.\n\nSignature block remains unchanged: NovaCloud / Atlas Retail.\n",
        [
            near_check("current-return", "text", ["Data return", "10 business days", "termination"], 2.5, 260),
            near_check("deleted-30", "structure", ["Deleted", "30 calendar days"], 2, 220),
            near_check("audit-current", "text", ["Audit logs", "400 days", "48 hours"], 2.5, 320),
            near_check("comment-a", "layout", ["Comment A", "Legal", "regulated customers"], 2, 260),
            near_check("comment-b", "layout", ["Comment B", "Security", "400 days", "deleted efforts"], 2, 360),
            none_regex_check("no-current-30", [r"must return Customer Data within 30 calendar days", r"current.*30 calendar days", r"within 10 calendar days"], 3),
            none_regex_check("no-inserted-efforts", [r"Inserted.*commercially reasonable efforts", r"current.*commercially reasonable efforts", r"Inserted phrase: commercially reasonable efforts"], 2),
            none_regex_check("no-inserted-as-deleted", [r"include inserted text as deleted"], 2, "structure"),
        ],
        [img],
    )


def h18() -> Case:
    img = base_page("Solara Robotics Q4 Board Pack")
    d = ImageDraw.Draw(img)
    d.text((100, 155), "Note 3: ARR Bridge (USD millions)", fill="#111827", font=F["h1"])
    d.text((100, 215), "Parentheses indicate negative movement. EMEA includes Israel and South Africa.", fill="#7f1d1d", font=F["small"])
    rows = [
        ["Region", "FY2025", "New", "Expansion", "Churn", "FX", "FY2026"],
        ["North America", "84.0", "+18.5", "+6.0", "(4.2)", "+0.7", "105.0"],
        ["EMEA", "56.0", "+9.4", "+5.1", "(6.8)", "(1.2)", "62.5"],
        ["APAC", "24.5", "+7.6", "+2.4", "(1.5)", "+0.0", "33.0"],
        ["Total", "164.5", "+35.5", "+13.5", "(12.5)", "(0.5)", "200.5"],
    ]
    draw_table(d, 70, 320, [285, 170, 170, 205, 165, 150, 170], rows, 78)

    d.text((110, 790), "Waterfall summary", fill="#111827", font=F["h2"])
    steps = [("FY2025", 164.5, "#64748b"), ("New", 35.5, "#16a34a"), ("Expansion", 13.5, "#16a34a"), ("Churn", -12.5, "#dc2626"), ("FX", -0.5, "#dc2626"), ("FY2026", 200.5, "#64748b")]
    x, base_y = 150, 1390
    scale = 1.45
    running = 164.5
    for i, (label, value, color) in enumerate(steps):
        bx = x + i * 230
        if i == 0 or i == len(steps) - 1:
            height = int(value * scale)
            d.rectangle((bx, base_y - height, bx + 110, base_y), fill=color, outline="#111827", width=2)
            d.text((bx, base_y - height - 35), f"{value:.1f}", fill="#111827", font=F["tiny"])
        else:
            prev = running
            running += value
            y1 = base_y - int(max(prev, running) * scale)
            y2 = base_y - int(min(prev, running) * scale)
            d.rectangle((bx, y1, bx + 110, y2), fill=color, outline="#111827", width=2)
            d.text((bx, y1 - 35), f"{value:+.1f}", fill="#111827", font=F["tiny"])
        d.text((bx - 10, base_y + 20), label, fill="#111827", font=F["tiny"])
    d.text((100, 1545), "Footnotes: Churn shown as negative. EMEA includes Israel and South Africa.", fill="#111827", font=F["small"])
    return Case(
        "H18-financial-arr-bridge",
        "Financial ARR Bridge Board Pack",
        "tables",
        ["raster-only", "finance", "hierarchical-table", "waterfall-chart", "footnotes"],
        "Recover a financial bridge table with sign conventions, footnotes, totals, and a supporting waterfall chart.",
        "Raster-only board-pack page with financial table and chart.",
        ["ARR bridge table", "negative sign convention", "footnotes", "waterfall description"],
        ["Preserve all row/column bindings.", "Treat parentheses as negative.", "Attach footnotes to the correct table.", "Describe the waterfall chart inline."],
        "# Solara Robotics Q4 Board Pack - Note 3: ARR Bridge (USD millions)\n\nParentheses indicate negative movement.\n\n| Region | FY2025 | New | Expansion | Churn | FX | FY2026 |\n| --- | ---: | ---: | ---: | ---: | ---: | ---: |\n| North America | 84.0 | +18.5 | +6.0 | -4.2 | +0.7 | 105.0 |\n| EMEA | 56.0 | +9.4 | +5.1 | -6.8 | -1.2 | 62.5 |\n| APAC | 24.5 | +7.6 | +2.4 | -1.5 | +0.0 | 33.0 |\n| Total | 164.5 | +35.5 | +13.5 | -12.5 | -0.5 | 200.5 |\n\nWaterfall chart: FY2025 starts at 164.5, New and Expansion are positive green steps, Churn and FX are negative red steps, and FY2026 ends at 200.5.\n\nFootnotes: Churn shown as negative. EMEA includes Israel and South Africa.\n",
        [
            near_check("na-row", "tables", ["North America", "84.0", "+18.5", "+6.0", "4.2", "+0.7", "105.0"], 3, 520),
            near_check("emea-row", "tables", ["EMEA", "56.0", "+9.4", "+5.1", "6.8", "1.2", "62.5"], 3, 520),
            near_check("total-row", "tables", ["Total", "164.5", "+35.5", "+13.5", "12.5", "0.5", "200.5"], 3, 560),
            near_check("footnotes", "text", ["Churn", "negative", "EMEA", "Israel", "South Africa"], 2.5, 420),
            near_check("waterfall", "visual", ["Waterfall", "FY2025", "164.5", "FY2026", "200.5"], 2.5, 520),
            none_regex_check("no-positive-churn", [r"Churn[\s\S]{0,80}\+12\.5", r"EMEA[\s\S]{0,160}\+6\.8", r"FX[\s\S]{0,80}\+0\.5"], 3),
        ],
        [img],
        facts=[
            fact("arr.na.row", "tables", 4, "North America row has FY2025 84.0, New +18.5, Expansion +6.0, Churn -4.2, FX +0.7, FY2026 105.0."),
            fact("arr.emea.row", "tables", 4, "EMEA row has FY2025 56.0, New +9.4, Expansion +5.1, Churn -6.8, FX -1.2, FY2026 62.5."),
            fact("arr.total.row", "tables", 5, "Total row has FY2025 164.5, New +35.5, Expansion +13.5, Churn -12.5, FX -0.5, FY2026 200.5."),
            fact("arr.signs", "accuracy", 4, "Parentheses in Churn and FX are represented as negative values, not positive values."),
            fact("arr.footnotes", "text", 3, "Includes both footnotes: Churn shown as negative; EMEA includes Israel and South Africa."),
            fact("arr.waterfall", "visual", 3, "Describes the waterfall chart as starting at 164.5, adding New/Expansion, subtracting Churn/FX, and ending at 200.5."),
        ],
    )


def h19() -> Case:
    img = base_page("Explanation of Benefits")
    d = ImageDraw.Draw(img)
    d.text((100, 150), "Patient: Ana Rivera    Claim: 5821", fill="#111827", font=F["h2"])
    d.rounded_rectangle((1110, 200, 1580, 430), radius=16, fill="#fff7ed", outline="#c2410c", width=4)
    d.text((1150, 245), "This is not a bill", fill="#c2410c", font=F["h2"])
    d.text((1150, 315), "You may owe", fill="#111827", font=F["small"])
    d.text((1150, 350), "$48.32", fill="#111827", font=F["h1"])
    checkbox(d, 120, 255, "In-network", True, F["small"])
    checkbox(d, 120, 310, "Out-of-network", False, F["small"])
    rows = [
        ["Service", "Code", "Charged", "Allowed", "Deductible", "Plan paid", "Patient may owe"],
        ["Office visit", "99213", "$215.00", "$143.20", "$20.00", "$98.56", "$44.64"],
        ["Comprehensive metabolic panel", "80053", "$72.00", "$18.40", "$0.00", "$14.72", "$3.68"],
        ["Total", "", "$287.00", "$161.60", "$20.00", "$113.28", "$48.32"],
    ]
    draw_table(d, 65, 520, [360, 130, 170, 170, 185, 180, 225], rows, 92)
    d.text((100, 960), "Appeal by 2026-08-31.", fill="#7f1d1d", font=F["h2"])
    return Case(
        "H19-insurance-eob",
        "Insurance Explanation of Benefits",
        "forms",
        ["raster-only", "insurance", "checkbox", "summary-card", "financial-table"],
        "Recover an EOB table, summary card, deadline, and selected network state.",
        "Raster-only explanation-of-benefits page.",
        ["claim identity", "network checkbox state", "claim table", "summary card", "appeal deadline"],
        ["Preserve row-level money values.", "Do not treat the document as a bill.", "Preserve selected and unselected network states."],
        "# Explanation of Benefits\n\nPatient: Ana Rivera. Claim: 5821. This is not a bill.\n\nIn-network is selected; Out-of-network is unselected.\n\n| Service | Code | Charged | Allowed | Deductible | Plan paid | Patient may owe |\n| --- | --- | ---: | ---: | ---: | ---: | ---: |\n| Office visit | 99213 | $215.00 | $143.20 | $20.00 | $98.56 | $44.64 |\n| Comprehensive metabolic panel | 80053 | $72.00 | $18.40 | $0.00 | $14.72 | $3.68 |\n| Total | | $287.00 | $161.60 | $20.00 | $113.28 | $48.32 |\n\nSummary card: You may owe $48.32. Appeal by 2026-08-31.\n",
        [
            all_check("identity", "text", ["Ana Rivera", "5821", "not a bill"], 2),
            near_check("network-state", "forms", ["In-network", "selected", "Out-of-network", "unselected"], 3, 320),
            near_check("office-row", "tables", ["Office visit", "99213", "$215.00", "$143.20", "$20.00", "$98.56", "$44.64"], 3, 580),
            near_check("cmp-row", "tables", ["Comprehensive metabolic panel", "80053", "$72.00", "$18.40", "$0.00", "$14.72", "$3.68"], 3, 640),
            near_check("total-row", "tables", ["Total", "$287.00", "$161.60", "$113.28", "$48.32"], 3, 520),
            all_check("deadline", "text", ["2026-08-31"], 1.5),
        ],
        [img],
        facts=[
            fact("eob.identity", "text", 2, "Patient Ana Rivera, claim 5821, and 'This is not a bill' are present."),
            fact("eob.network", "forms", 4, "In-network is selected and Out-of-network is unselected."),
            fact("eob.office", "tables", 4, "Office visit row code 99213 has charged $215.00, allowed $143.20, deductible $20.00, plan paid $98.56, patient may owe $44.64."),
            fact("eob.cmp", "tables", 4, "Comprehensive metabolic panel row code 80053 has charged $72.00, allowed $18.40, deductible $0.00, plan paid $14.72, patient may owe $3.68."),
            fact("eob.total", "tables", 4, "Total row has charged $287.00, allowed $161.60, deductible $20.00, plan paid $113.28, patient may owe $48.32."),
            fact("eob.summary", "forms", 3, "Right-side summary card says You may owe $48.32 and appeal deadline is 2026-08-31."),
        ],
    )


def h20() -> Case:
    img = base_page("Cedar Clinic Punch List - Floor 1")
    d = ImageDraw.Draw(img)
    # Floor plan
    d.rectangle((110, 270, 760, 970), outline="#111827", width=5)
    d.line((110, 520, 760, 520), fill="#111827", width=4)
    d.line((420, 270, 420, 970), fill="#111827", width=4)
    d.text((160, 350), "A101 Lobby", fill="#111827", font=F["small"])
    d.text((480, 350), "A102 Exam 1", fill="#111827", font=F["small"])
    d.text((480, 690), "A103 Storage", fill="#111827", font=F["small"])
    d.text((160, 690), "Corridor", fill="#475569", font=F["small"])
    d.ellipse((565, 440, 605, 480), fill="#fee2e2", outline="#991b1b", width=4)
    d.text((612, 445), "P1", fill="#991b1b", font=F["small"])
    pts = [(250, 410), (225, 455), (275, 455)]
    d.polygon(pts, fill="#fef3c7", outline="#a16207")
    d.text((282, 430), "E2", fill="#a16207", font=F["small"])
    d.rectangle((555, 825, 595, 865), fill="#dbeafe", outline="#1d4ed8", width=4)
    d.text((605, 827), "F3", fill="#1d4ed8", font=F["small"])

    rows = [
        ["Callout", "Symbol", "Location", "Issue", "Owner", "Due", "Priority", "Status"],
        ["P1", "red circle", "A102 under sink", "Active leak", "Mei", "2026-07-09", "P0", "Open"],
        ["E2", "yellow triangle", "A101 west wall", "GFCI outlet mislabeled", "Omar", "2026-07-12", "P2", "Blocked by permit"],
        ["F3", "blue square", "A103 south door", "Cracked floor tile", "Lina", "2026-07-15", "P3", "Done"],
    ]
    draw_table(d, 80, 1110, [125, 160, 220, 285, 110, 160, 110, 230], rows, 80)
    return Case(
        "H20-clinic-floorplan-punchlist",
        "Clinic Floor-Plan Punch List",
        "visual",
        ["raster-only", "floor-plan", "callouts", "diagram", "table"],
        "Map visual callout symbols to rooms and punch-list table facts.",
        "Raster-only facilities page with floor plan and callout table.",
        ["floor plan description", "callout symbol mapping", "room/issue binding", "owner/due/status table"],
        ["Do not just transcribe the table; preserve the semantic mapping between symbols, rooms, and issues."],
        "# Cedar Clinic Punch List - Floor 1\n\nFloor plan: A101 Lobby is on the left upper room, A102 Exam 1 is the upper right room, A103 Storage is the lower right room, and a corridor is on the lower left. P1 is a red circle in A102 under the sink. E2 is a yellow triangle on the A101 west wall. F3 is a blue square near the A103 south door.\n\n| Callout | Symbol | Location | Issue | Owner | Due | Priority | Status |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n| P1 | red circle | A102 under sink | Active leak | Mei | 2026-07-09 | P0 | Open |\n| E2 | yellow triangle | A101 west wall | GFCI outlet mislabeled | Omar | 2026-07-12 | P2 | Blocked by permit |\n| F3 | blue square | A103 south door | Cracked floor tile | Lina | 2026-07-15 | P3 | Done |\n",
        [
            near_check("p1-mapping", "visual", ["P1", "red circle", "A102", "under sink", "Active leak", "Mei", "P0", "Open"], 4, 620),
            near_check("e2-mapping", "visual", ["E2", "yellow triangle", "A101", "west wall", "GFCI", "Omar", "Blocked by permit"], 4, 660),
            near_check("f3-mapping", "visual", ["F3", "blue square", "A103", "south door", "Cracked floor tile", "Lina", "Done"], 4, 660),
            all_check("floorplan-description", "visual", ["A101", "A102", "A103", "corridor"], 2),
        ],
        [img],
        facts=[
            fact("floorplan.rooms", "visual", 3, "Describes the floor plan rooms A101 Lobby, A102 Exam 1, A103 Storage, and corridor."),
            fact("floorplan.p1", "visual", 5, "P1 is a red circle in A102 under the sink for Active leak, owner Mei, due 2026-07-09, priority P0, status Open."),
            fact("floorplan.e2", "visual", 5, "E2 is a yellow triangle on the A101 west wall for GFCI outlet mislabeled, owner Omar, due 2026-07-12, priority P2, status Blocked by permit."),
            fact("floorplan.f3", "visual", 5, "F3 is a blue square near the A103 south door for Cracked floor tile, owner Lina, due 2026-07-15, priority P3, status Done."),
        ],
    )


def h21() -> Case:
    img = base_page("OpsConf 2026 - Day 2 Program")
    d = ImageDraw.Draw(img)
    d.text((100, 155), "Merged cells show sessions that span rooms. Legend: star = preregistration required; dot = hybrid session.", fill="#7f1d1d", font=F["small"])
    x0, y0 = 110, 300
    widths = [210, 390, 390, 390]
    row_h = 120
    headers = ["Time", "Hall A", "Lab 1", "Lab 2"]
    times = ["08:30-09:00", "09:00-09:45", "10:00-10:45", "11:00-12:00", "12:00-13:00", "13:15-14:00"]
    for c, h in enumerate(headers):
        x = x0 + sum(widths[:c])
        d.rectangle((x, y0, x + widths[c], y0 + 80), fill="#e5e7eb", outline="#111827", width=3)
        d.text((x + 12, y0 + 24), h, fill="#111827", font=F["small"])
    y = y0 + 80
    for r, time in enumerate(times):
        d.rectangle((x0, y, x0 + widths[0], y + row_h), fill="#ffffff", outline="#111827", width=3)
        d.text((x0 + 10, y + 42), time, fill="#111827", font=F["tiny"])
        for c in range(1, 4):
            x = x0 + sum(widths[:c])
            d.rectangle((x, y, x + widths[c], y + row_h), fill="#ffffff", outline="#111827", width=3)
        y += row_h
    # Spanning/all-room rows by visual overlays
    d.rectangle((x0 + widths[0], y0 + 80, x0 + sum(widths), y0 + 80 + row_h), fill="#f8fafc", outline="#111827", width=3)
    d.text((x0 + widths[0] + 18, y0 + 125), "Registration, Atrium (spans all rooms)", fill="#111827", font=F["small"])
    d.text((x0 + widths[0] + 18, y0 + 80 + row_h + 42), "Keynote: Metrics that Matter", fill="#111827", font=F["small"])
    y10 = y0 + 80 + row_h * 2
    d.text((x0 + widths[0] + 18, y10 + 40), "star SLO Math", fill="#111827", font=F["small"])
    d.text((x0 + widths[0] + widths[1] + 18, y10 + 40), "dot Tracing Lab", fill="#111827", font=F["small"])
    d.text((x0 + widths[0] + widths[1] + widths[2] + 18, y10 + 40), "Cost Controls", fill="#111827", font=F["small"])
    y11 = y0 + 80 + row_h * 3
    d.text((x0 + widths[0] + 18, y11 + 40), "Vendor briefings", fill="#111827", font=F["small"])
    d.rectangle((x0 + widths[0] + widths[1], y11, x0 + sum(widths), y11 + row_h), fill="#ecfeff", outline="#111827", width=3)
    d.text((x0 + widths[0] + widths[1] + 18, y11 + 40), "Incident Drill (spans Lab 1 and Lab 2)", fill="#111827", font=F["small"])
    y12 = y0 + 80 + row_h * 4
    d.rectangle((x0 + widths[0], y12, x0 + sum(widths), y12 + row_h), fill="#f8fafc", outline="#111827", width=3)
    d.text((x0 + widths[0] + 18, y12 + 40), "Lunch, Courtyard (spans all rooms)", fill="#111827", font=F["small"])
    y13 = y0 + 80 + row_h * 5
    d.text((x0 + widths[0] + 18, y13 + 40), "Postmortem Patterns", fill="#111827", font=F["small"])
    d.text((x0 + widths[0] + widths[1] + 18, y13 + 40), "Forecasting", fill="#111827", font=F["small"])
    d.text((x0 + widths[0] + widths[1] + widths[2] + 18, y13 + 40), "FinOps Clinic", fill="#111827", font=F["small"])
    d.text((110, 1155), "Legend: star = preregistration required. dot = hybrid session.", fill="#111827", font=F["small"])
    return Case(
        "H21-conference-schedule-grid",
        "Conference Schedule Grid",
        "spatial",
        ["raster-only", "schedule", "merged-cells", "icons", "room-grid"],
        "Recover a time-by-room schedule grid with room-spanning cells and icon legend semantics.",
        "Raster-only conference schedule with merged cells and legend icons.",
        ["time/room grid", "merged-room sessions", "all-room sessions", "icon legend"],
        ["Preserve room spans and blank cells.", "Bind icons to their legend meanings.", "Do not duplicate merged sessions into wrong rooms without noting the span."],
        "# OpsConf 2026 - Day 2 Program\n\nLegend: star = preregistration required; dot = hybrid session.\n\n| Time | Hall A | Lab 1 | Lab 2 |\n| --- | --- | --- | --- |\n| 08:30-09:00 | Registration, Atrium, spans all rooms |  |  |\n| 09:00-09:45 | Keynote: Metrics that Matter |  |  |\n| 10:00-10:45 | star SLO Math | dot Tracing Lab | Cost Controls |\n| 11:00-12:00 | Vendor briefings | Incident Drill, spans Lab 1 and Lab 2 |  |\n| 12:00-13:00 | Lunch, Courtyard, spans all rooms |  |  |\n| 13:15-14:00 | Postmortem Patterns | Forecasting | FinOps Clinic |\n",
        [
            near_check("registration-span", "spatial", ["08:30", "09:00", "Registration", "Atrium", "spans all rooms"], 3, 420),
            near_check("icons", "visual", ["star", "preregistration", "dot", "hybrid"], 2.5, 360),
            near_check("slot-1000", "spatial", ["10:00", "SLO Math", "Tracing Lab", "Cost Controls"], 3, 520),
            near_check("incident-span", "spatial", ["11:00", "12:00", "Incident Drill", "Lab 1", "Lab 2"], 3, 520),
            near_check("lunch-span", "spatial", ["12:00", "13:00", "Lunch", "Courtyard", "spans all rooms"], 3, 420),
            near_check("slot-1315", "spatial", ["13:15", "Postmortem Patterns", "Forecasting", "FinOps Clinic"], 2.5, 520),
        ],
        [img],
        facts=[
            fact("schedule.legend", "visual", 3, "Legend says star means preregistration required and dot means hybrid session."),
            fact("schedule.registration", "spatial", 4, "08:30-09:00 Registration in Atrium spans all rooms."),
            fact("schedule.1000", "spatial", 5, "10:00-10:45 has star SLO Math in Hall A, dot Tracing Lab in Lab 1, and Cost Controls in Lab 2."),
            fact("schedule.incident", "spatial", 5, "11:00-12:00 has Vendor briefings in Hall A and Incident Drill spanning Lab 1 and Lab 2."),
            fact("schedule.lunch", "spatial", 4, "12:00-13:00 Lunch in Courtyard spans all rooms."),
            fact("schedule.1315", "spatial", 4, "13:15-14:00 has Postmortem Patterns in Hall A, Forecasting in Lab 1, and FinOps Clinic in Lab 2."),
        ],
    )


def overlays(lines: list[str], x: int, y: int, step: int = 30) -> list[tuple[int, int, str]]:
    return [(x, y + i * step, line) for i, line in enumerate(lines)]


def packet_real_push_investor_reference() -> Case:
    pages: list[Image.Image] = []

    p1 = base_page("Northstar Board Packet - Q3 Operating Review")
    d = ImageDraw.Draw(p1)
    d.text((100, 150), "Packet prepared 2026-07-02. Visible CFO correction badges supersede draft appendix values.", fill="#7f1d1d", font=F["small"])
    draw_card(d, (90, 245, 770, 560), "Executive summary", ["ARR closed at $200.5M", "Net retention 117%", "Support breach risk: NA-West", "Release Alpha stays blocked"], "#f8fafc")
    draw_card(d, (850, 245, 1540, 560), "CFO correction", ["Use final churn: -$12.5M", "Exclude intercompany rows", "Do not use draft appendix totals"], "#fff7ed", "#c2410c")
    rows = [["Decision", "Owner", "Due", "Visible state"], ["Alpha release", "Nisha", "2026-07-18", "BLOCKED"], ["APAC pricing", "Omar", "2026-07-21", "APPROVED"], ["Support freeze", "Mei", "when NA-West <25", "ACTIVE"]]
    draw_table(d, 105, 720, [350, 260, 300, 360], rows, 80)
    d.text((105, 1120), "Reading order: summary, CFO correction, decision table, then appendix context.", fill="#475569", font=F["small"])
    pages.append(p1)

    p2 = base_page("Note 3 - ARR Bridge and Waterfall")
    d = ImageDraw.Draw(p2)
    rows = [["Region", "FY2025", "New", "Expansion", "Churn", "FX", "FY2026"], ["North America", "84.0", "+18.5", "+6.0", "(4.2)", "+0.7", "105.0"], ["EMEA", "56.0", "+9.4", "+5.1", "(6.8)", "(1.2)", "62.5"], ["APAC", "24.5", "+7.6", "+2.4", "(1.5)", "+0.0", "33.0"], ["Total", "164.5", "+35.5", "+13.5", "(12.5)", "(0.5)", "200.5"]]
    draw_table(d, 70, 230, [285, 170, 170, 205, 165, 150, 170], rows, 78)
    d.text((100, 710), "Footnotes: Churn shown as negative. EMEA includes Israel and South Africa. Intercompany rows excluded.", fill="#111827", font=F["small"])
    d.text((100, 840), "Waterfall chart: final values after CFO correction", fill="#111827", font=F["h2"])
    steps = [("FY2025", 164.5, "#64748b"), ("New", 35.5, "#16a34a"), ("Expansion", 13.5, "#16a34a"), ("Churn", -12.5, "#dc2626"), ("FX", -0.5, "#dc2626"), ("FY2026", 200.5, "#64748b")]
    base_y, x0 = 1470, 150
    for i, (label, value, color) in enumerate(steps):
        x = x0 + i * 230
        h = int((abs(value) if i not in [0, 5] else value) * 1.35)
        y1 = base_y - h if value >= 0 else base_y - 40
        y2 = base_y if value >= 0 else base_y - 40 + h
        d.rectangle((x, y1, x + 105, y2), fill=color, outline="#111827", width=2)
        d.text((x, min(y1, y2) - 32), f"{value:+.1f}" if i not in [0, 5] else f"{value:.1f}", fill="#111827", font=F["tiny"])
        d.text((x - 4, base_y + 22), label, fill="#111827", font=F["tiny"])
    pages.append(p2)

    p3 = base_page("Support Queue Dashboard")
    d = ImageDraw.Draw(p3)
    d.text((100, 150), "Operations review - queue depth, regional backlog, and SLA exposure for the last support day.", fill="#475569", font=F["small"])
    d.rounded_rectangle((90, 245, 790, 760), radius=14, fill="#f8fafc", outline="#334155", width=3)
    d.text((120, 285), "Queue depth", fill="#111827", font=F["h2"])
    pts = [(170, 650), (285, 390), (400, 430), (515, 515), (630, 610)]
    labels = [("08:00", "12"), ("10:00", "41"), ("12:00", "38"), ("14:00", "29"), ("16:00", "18")]
    d.line((150, 675, 690, 675), fill="#111827", width=3)
    d.line((150, 675, 150, 330), fill="#111827", width=3)
    d.line((150, 455, 690, 455), fill="#dc2626", width=4)
    d.text((700, 443), "threshold 35", fill="#dc2626", font=F["tiny"])
    for a, b in zip(pts, pts[1:]):
        d.line((*a, *b), fill="#2563eb", width=5)
    for p, (t, v) in zip(pts, labels):
        d.ellipse((p[0] - 7, p[1] - 7, p[0] + 7, p[1] + 7), fill="#2563eb")
        d.text((p[0] - 16, p[1] - 35), v, fill="#111827", font=F["tiny"])
        d.text((p[0] - 24, 695), t, fill="#111827", font=F["tiny"])
    d.rounded_rectangle((900, 245, 1590, 760), radius=14, fill="#f8fafc", outline="#334155", width=3)
    d.text((930, 285), "Backlog by region", fill="#111827", font=F["h2"])
    for i, (region, t1, t2) in enumerate([("NA-West", 18, 11), ("NA-East", 9, 7), ("EMEA", 12, 5), ("APAC", 6, 2)]):
        x = 970 + i * 150
        yb = 675
        d.rectangle((x, yb - t1 * 9, x + 60, yb), fill="#93c5fd", outline="#1d4ed8")
        d.rectangle((x, yb - (t1 + t2) * 9, x + 60, yb - t1 * 9), fill="#fca5a5", outline="#b91c1c")
        d.text((x, yb + 20), region, fill="#111827", font=F["tiny"])
    draw_table(d, 105, 900, [205, 155, 155, 155], [["Priority", "Breached", "At risk", "OK"], ["Critical", "3", "2", "7"], ["High", "5", "4", "18"], ["Normal", "2", "6", "31"]], 70)
    d.rounded_rectangle((900, 930, 1590, 1165), radius=14, fill="#fff7ed", outline="#c2410c", width=4)
    draw_text(d, (930, 965), "Warning: NA-West crossed depth 35 at 10:00 and 12:00. Reopen freeze until depth is below 25.", F["small"], fill="#9a3412", width=48, leading=31)
    pages.append(p3)

    p4 = base_page("Draft Appendix - Superseded")
    d = ImageDraw.Draw(p4)
    d.text((100, 155), "DRAFT APPENDIX - superseded by pages 1-3", fill="#991b1b", font=F["h1"])
    draw_table(d, 110, 300, [360, 260, 260, 260], [["Draft field", "Draft value", "Visible final", "Status"], ["ARR total", "$198.8M", "$200.5M", "superseded"], ["Churn", "-$9.1M", "-$12.5M", "superseded"], ["Release Alpha", "APPROVED", "BLOCKED", "superseded"], ["Support freeze", "inactive", "ACTIVE", "superseded"]], 86)
    d.text((110, 760), "The appendix is included for context but must not override the visible final values.", fill="#111827", font=F["small"])
    pages.append(p4)

    gold = """# Northstar Board Packet - Q3 Operating Review

## Executive summary

ARR closed at $200.5M. Net retention is 117%. Support breach risk is NA-West. Release Alpha stays BLOCKED.

## CFO correction

Use final churn of -$12.5M. Exclude intercompany rows. Do not use draft appendix totals.

## Decisions

| Decision | Owner | Due | Visible state |
| --- | --- | --- | --- |
| Alpha release | Nisha | 2026-07-18 | BLOCKED |
| APAC pricing | Omar | 2026-07-21 | APPROVED |
| Support freeze | Mei | when NA-West <25 | ACTIVE |

## Note 3 - ARR Bridge and Waterfall

| Region | FY2025 | New | Expansion | Churn | FX | FY2026 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| North America | 84.0 | +18.5 | +6.0 | -4.2 | +0.7 | 105.0 |
| EMEA | 56.0 | +9.4 | +5.1 | -6.8 | -1.2 | 62.5 |
| APAC | 24.5 | +7.6 | +2.4 | -1.5 | +0.0 | 33.0 |
| Total | 164.5 | +35.5 | +13.5 | -12.5 | -0.5 | 200.5 |

Footnotes: Churn is shown as negative. EMEA includes Israel and South Africa. Intercompany rows are excluded.

Waterfall chart: FY2025 starts at 164.5, New and Expansion are positive steps, Churn and FX are negative steps, and FY2026 ends at 200.5.

## Support Queue Dashboard

Queue depth values are 08:00 12, 10:00 41, 12:00 38, 14:00 29, 16:00 18. The threshold is 35, crossed at 10:00 and 12:00.

Backlog by region: NA-West has Tier 1 18 and Tier 2 11; NA-East has Tier 1 9 and Tier 2 7; EMEA has Tier 1 12 and Tier 2 5; APAC has Tier 1 6 and Tier 2 2.

SLA matrix: Critical breached 3, Critical at risk 2, Critical OK 7. High breached 5, High at risk 4, High OK 18. Normal breached 2, Normal at risk 6, Normal OK 31.

Warning: NA-West crossed depth 35 at 10:00 and 12:00. Reopen freeze until depth is below 25.

## Draft Appendix

The draft appendix is superseded. It must not override final values. Draft ARR $198.8M, draft churn -$9.1M, draft Alpha APPROVED, and draft support freeze inactive are historical/superseded values.
"""
    return Case(
        "P01-board-ops-packet",
        "Board Operating Packet",
        "packet",
        ["multi-page", "finance", "dashboard", "source-precedence", "charts"],
        "Recover a realistic board packet with final values, draft appendix conflicts, financial table, dashboard, and derived warning.",
        "Four-page packet with mixed extractable text overlays and raster visual tables/charts.",
        ["final decisions", "ARR bridge", "dashboard", "draft appendix precedence"],
        ["Preserve page order.", "Use final visible values over draft appendix values.", "Reconstruct financial and dashboard tables."],
        gold,
        [near_check("final-arr", "tables", ["ARR", "$200.5M", "churn", "-$12.5M"], 3, 500)],
        pages,
        facts=[
            fact("p01.final.summary", "text", 4, "Executive summary says ARR closed at $200.5M, net retention 117%, Support breach risk NA-West, and Release Alpha BLOCKED."),
            fact("p01.decisions", "tables", 4, "Decision table has Alpha release/Nisha/2026-07-18/BLOCKED, APAC pricing/Omar/2026-07-21/APPROVED, Support freeze/Mei/when NA-West <25/ACTIVE."),
            fact("p01.arr.table", "tables", 6, "ARR bridge table preserves region rows and total row: total FY2025 164.5, New +35.5, Expansion +13.5, Churn -12.5, FX -0.5, FY2026 200.5."),
            fact("p01.footnotes", "text", 3, "Footnotes state churn is negative, EMEA includes Israel and South Africa, and intercompany rows are excluded."),
            fact("p01.dashboard.line", "visual", 5, "Queue depth values are 12, 41, 38, 29, 18 at 08:00, 10:00, 12:00, 14:00, 16:00 and threshold 35 is crossed at 10:00 and 12:00."),
            fact("p01.dashboard.backlog", "visual", 4, "Backlog by region preserves NA-West 18/11, NA-East 9/7, EMEA 12/5, APAC 6/2 for Tier 1/Tier 2."),
            fact("p01.sla", "tables", 4, "SLA matrix preserves Critical 3 breached and 2 at risk, High 5 breached and 4 at risk, Normal 2 breached and 6 at risk."),
            fact("p01.warning", "visual", 4, "Warning says NA-West crossed depth 35 at 10:00 and 12:00; reopen freeze until depth is below 25."),
            fact("p01.superseded", "forbidden_text", 5, "Draft appendix values $198.8M, -$9.1M, Alpha APPROVED, and support freeze inactive are marked superseded and not treated as final."),
        ],
        extractable_text_pages=[
            overlays(["Northstar Board Packet - Q3 Operating Review", "ARR closed at $200.5M", "Net retention 117%", "Release Alpha stays blocked"], 100, 105),
            [],
            [],
            overlays(["DRAFT APPENDIX - superseded by pages 1-3", "The appendix is included for context but must not override final values."], 100, 150),
        ],
    )


def packet_claims_appeal() -> Case:
    pages: list[Image.Image] = []
    p1 = base_page("Summit Health EOB Appeal Packet")
    d = ImageDraw.Draw(p1)
    draw_card(d, (100, 220, 760, 550), "Member and claim", ["Member: Ana Rivera", "Claim: 5821-A", "Plan: Silver HMO", "This is not a bill"], "#f8fafc")
    draw_card(d, (900, 220, 1530, 550), "Final responsibility", ["Patient may owe: $48.32", "Appeal by: 2026-08-31", "Network: In-network"], "#fff7ed", "#c2410c")
    checkbox(d, 130, 650, "In-network", True, F["small"])
    checkbox(d, 130, 705, "Out-of-network", False, F["small"])
    checkbox(d, 130, 760, "Appeal form attached", True, F["small"])
    d.text((100, 900), "Important: Page 3 denial note changes only the lab-panel adjustment, not the office visit row.", fill="#7f1d1d", font=F["small"])
    pages.append(p1)

    p2 = base_page("EOB Detail - Claim 5821-A")
    d = ImageDraw.Draw(p2)
    rows = [["Service", "Code", "Charged", "Allowed", "Deductible", "Plan paid", "Patient may owe"], ["Office visit", "99213", "$215.00", "$143.20", "$20.00", "$98.56", "$44.64"], ["Comprehensive metabolic panel", "80053", "$72.00", "$18.40", "$0.00", "$14.72", "$3.68"], ["Total", "", "$287.00", "$161.60", "$20.00", "$113.28", "$48.32"]]
    draw_table(d, 60, 230, [350, 130, 170, 170, 185, 180, 225], rows, 92)
    d.rounded_rectangle((105, 720, 1540, 960), radius=14, fill="#f8fafc", outline="#334155", width=3)
    draw_text(d, (135, 755), "Footnote A: The comprehensive metabolic panel was repriced under the in-network lab schedule. Do not add the lab adjustment twice.", F["small"], width=96, leading=31)
    pages.append(p2)

    p3 = base_page("Denial and Adjustment Notes")
    d = ImageDraw.Draw(p3)
    rows = [["Code", "Applies to", "Meaning", "Effect"], ["N214", "80053 only", "Lab panel repriced", "Allowed becomes $18.40"], ["M51", "Office visit", "Routine office visit", "No denial"], ["X17", "Claim total", "Appeal rights included", "Deadline 2026-08-31"]]
    draw_table(d, 90, 260, [180, 280, 430, 390], rows, 86)
    d.rounded_rectangle((980, 820, 1500, 1050), radius=16, fill="#fee2e2", outline="#991b1b", width=4)
    draw_text(d, (1010, 860), "Visible correction: an earlier draft said patient may owe $63.04. Final card on page 1 controls: $48.32.", F["small"], fill="#991b1b", width=34, leading=30)
    pages.append(p3)

    p4 = base_page("Appeal Form")
    d = ImageDraw.Draw(p4)
    d.text((100, 180), "Appeal deadline: 2026-08-31", fill="#111827", font=F["h2"])
    checkbox(d, 120, 290, "Member requests appeal", True, F["small"])
    checkbox(d, 120, 345, "Provider-filed appeal", False, F["small"])
    checkbox(d, 120, 400, "Expedited review requested", False, F["small"])
    d.rounded_rectangle((110, 520, 1430, 760), radius=14, fill="#f8fafc", outline="#334155", width=3)
    draw_text(d, (140, 555), "Reason: member disputes lab-panel pricing only. Office visit is not disputed. Signature: Ana Rivera, dated 2026-07-06.", F["small"], width=92, leading=31)
    pages.append(p4)

    gold = """# Summit Health EOB Appeal Packet

Member: Ana Rivera. Claim: 5821-A. Plan: Silver HMO. This is not a bill.

Final responsibility card: patient may owe $48.32. Appeal deadline is 2026-08-31. Network status is In-network. In-network is checked; Out-of-network is unchecked; Appeal form attached is checked.

## EOB Detail

| Service | Code | Charged | Allowed | Deductible | Plan paid | Patient may owe |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Office visit | 99213 | $215.00 | $143.20 | $20.00 | $98.56 | $44.64 |
| Comprehensive metabolic panel | 80053 | $72.00 | $18.40 | $0.00 | $14.72 | $3.68 |
| Total | | $287.00 | $161.60 | $20.00 | $113.28 | $48.32 |

Footnote A: The comprehensive metabolic panel was repriced under the in-network lab schedule. Do not add the lab adjustment twice.

## Denial and Adjustment Notes

N214 applies to 80053 only and means the lab panel was repriced; allowed becomes $18.40. M51 applies to the office visit and means routine office visit with no denial. X17 applies to the claim total and means appeal rights included with deadline 2026-08-31.

Visible correction: an earlier draft said patient may owe $63.04. The final card on page 1 controls: $48.32.

## Appeal Form

Member requests appeal is checked. Provider-filed appeal is unchecked. Expedited review requested is unchecked. Reason: member disputes lab-panel pricing only. Office visit is not disputed. Signature: Ana Rivera, dated 2026-07-06.
"""
    return Case(
        "P02-eob-appeal-packet",
        "EOB Appeal Packet",
        "forms",
        ["multi-page", "eob", "forms", "corrections", "financial-table"],
        "Recover a realistic EOB packet with line items, denial notes, correction, and appeal form state.",
        "Four-page packet with extractable cover text and raster form/table pages.",
        ["member identity", "line-item table", "denial notes", "appeal form states"],
        ["Preserve final responsibility and do not use superseded draft amount.", "Keep line-item values bound to services."],
        gold,
        [near_check("final-owe", "forms", ["$48.32", "2026-08-31", "In-network"], 3, 360)],
        pages,
        facts=[
            fact("p02.cover", "text", 4, "Member Ana Rivera, claim 5821-A, Silver HMO, not a bill, final responsibility $48.32, appeal by 2026-08-31."),
            fact("p02.network", "form_state", 4, "In-network is checked, Out-of-network is unchecked, Appeal form attached is checked."),
            fact("p02.office.row", "table_cell", 5, "Office visit 99213 row has charged $215.00, allowed $143.20, deductible $20.00, plan paid $98.56, patient may owe $44.64."),
            fact("p02.lab.row", "table_cell", 5, "Comprehensive metabolic panel 80053 row has charged $72.00, allowed $18.40, deductible $0.00, plan paid $14.72, patient may owe $3.68."),
            fact("p02.total", "table_cell", 4, "Total row has charged $287.00, allowed $161.60, deductible $20.00, plan paid $113.28, patient may owe $48.32."),
            fact("p02.denials", "table_cell", 4, "N214 applies only to 80053 and sets allowed to $18.40; M51 applies to office visit with no denial; X17 is appeal rights with deadline 2026-08-31."),
            fact("p02.superseded", "forbidden_text", 5, "Draft amount $63.04 is identified as superseded and not used as final patient responsibility."),
            fact("p02.appeal.form", "form_state", 4, "Appeal form: member requests appeal checked; provider-filed and expedited review unchecked; reason disputes lab pricing only; office visit not disputed."),
        ],
        extractable_text_pages=[overlays(["Member: Ana Rivera", "Claim: 5821-A", "This is not a bill", "Patient may owe: $48.32"], 100, 250), [], [], []],
    )


def packet_facilities() -> Case:
    pages: list[Image.Image] = []
    p1 = base_page("Cedar Clinic Renovation Packet")
    d = ImageDraw.Draw(p1)
    d.rectangle((110, 260, 1120, 1160), outline="#111827", width=5)
    d.line((110, 560, 1120, 560), fill="#111827", width=4)
    d.line((460, 260, 460, 1160), fill="#111827", width=4)
    d.line((790, 260, 790, 1160), fill="#111827", width=4)
    d.text((170, 390), "A101 Lobby", fill="#111827", font=F["small"])
    d.text((520, 390), "A102 Exam 1", fill="#111827", font=F["small"])
    d.text((850, 390), "A103 Storage", fill="#111827", font=F["small"])
    d.text((170, 840), "Corridor", fill="#475569", font=F["small"])
    d.text((525, 840), "A104 Exam 2", fill="#111827", font=F["small"])
    d.text((845, 840), "A105 Lab", fill="#111827", font=F["small"])
    for label, x, y, color, shape in [("P1", 610, 455, "#991b1b", "circle"), ("E2", 285, 445, "#a16207", "tri"), ("F3", 895, 930, "#1d4ed8", "square"), ("M4", 1030, 825, "#7c3aed", "diamond")]:
        if shape == "circle":
            d.ellipse((x, y, x + 42, y + 42), fill="#fee2e2", outline=color, width=4)
        elif shape == "tri":
            d.polygon([(x + 22, y), (x, y + 42), (x + 44, y + 42)], fill="#fef3c7", outline=color)
        elif shape == "square":
            d.rectangle((x, y, x + 42, y + 42), fill="#dbeafe", outline=color, width=4)
        else:
            d.polygon([(x + 22, y), (x + 44, y + 22), (x + 22, y + 44), (x, y + 22)], fill="#ede9fe", outline=color)
        d.text((x + 55, y + 4), label, fill=color, font=F["small"])
    d.rounded_rectangle((1220, 280, 1585, 620), radius=14, fill="#f8fafc", outline="#334155", width=3)
    draw_text(d, (1240, 315), "Legend: red circle P0 leak; yellow triangle electrical; blue square finish defect; purple diamond map-only equipment issue.", F["small"], width=24, leading=29)
    pages.append(p1)

    p2 = base_page("Punch List Table")
    d = ImageDraw.Draw(p2)
    rows = [["ID", "Location", "Issue", "Owner", "Due", "Status"], ["P1", "A102 under sink", "Active leak", "Mei", "2026-07-09", "Open"], ["E2", "A101 west wall", "GFCI outlet mislabeled", "Omar", "2026-07-12", "Blocked by permit"], ["F3", "A103 south door", "Cracked floor tile", "Lina", "2026-07-15", "Done"]]
    draw_table(d, 85, 240, [160, 300, 420, 180, 230, 280], rows, 90)
    d.text((100, 760), "Note: M4 appears on the map only and is missing from this table.", fill="#7f1d1d", font=F["small"])
    pages.append(p2)

    p3 = base_page("Photo Log and Correction")
    d = ImageDraw.Draw(p3)
    draw_card(d, (100, 240, 730, 550), "Photo A", ["P1: water visible below sink", "Severity: P0", "Temporary shutoff installed"], "#fee2e2", "#991b1b")
    draw_card(d, (870, 240, 1500, 550), "Photo B", ["F3: tile repaired", "Status changed from Open to Done", "Do not reopen"], "#ecfeff", "#0f766e")
    draw_card(d, (100, 700, 730, 1010), "Map-only issue", ["M4: autoclave vent clearance", "Location: A105 Lab east wall", "Owner: Priya", "Due: 2026-07-20"], "#ede9fe", "#7c3aed")
    d.text((100, 1160), "Visible correction: F3 final status is Done even if older table export says Open.", fill="#7f1d1d", font=F["small"])
    pages.append(p3)

    p4 = base_page("Change Order CO-17")
    d = ImageDraw.Draw(p4)
    rows = [["Change", "Applies to", "Cost", "Approved"], ["Permit reinspection", "E2", "$420", "No"], ["Emergency plumbing", "P1", "$1,180", "Yes"], ["Vent clearance shim", "M4", "$260", "Yes"]]
    draw_table(d, 110, 280, [360, 260, 220, 220], rows, 86)
    d.text((110, 700), "Total approved cost is $1,440. Permit reinspection is not approved.", fill="#111827", font=F["small"])
    pages.append(p4)
    gold = """# Cedar Clinic Renovation Packet

## Floor plan

Rooms: A101 Lobby, A102 Exam 1, A103 Storage, Corridor, A104 Exam 2, and A105 Lab. Legend: red circle means P0 leak; yellow triangle means electrical; blue square means finish defect; purple diamond means map-only equipment issue.

Map callouts: P1 red circle is in A102 under the sink. E2 yellow triangle is on the A101 west wall. F3 blue square is at the A103 south door. M4 purple diamond is in A105 Lab on the east wall.

## Punch List

| ID | Location | Issue | Owner | Due | Status |
| --- | --- | --- | --- | --- | --- |
| P1 | A102 under sink | Active leak | Mei | 2026-07-09 | Open |
| E2 | A101 west wall | GFCI outlet mislabeled | Omar | 2026-07-12 | Blocked by permit |
| F3 | A103 south door | Cracked floor tile | Lina | 2026-07-15 | Done |

M4 appears on the map only and is missing from the punch-list table.

## Photo Log and Correction

P1 photo shows water visible below the sink, severity P0, and temporary shutoff installed. F3 photo says tile repaired and final status changed from Open to Done. M4 map-only issue is autoclave vent clearance in A105 Lab east wall, owner Priya, due 2026-07-20.

## Change Order CO-17

Permit reinspection applies to E2, costs $420, and is not approved. Emergency plumbing applies to P1, costs $1,180, and is approved. Vent clearance shim applies to M4, costs $260, and is approved. Total approved cost is $1,440.
"""
    return Case(
        "P03-facilities-renovation-packet",
        "Facilities Renovation Packet",
        "diagram",
        ["multi-page", "floorplan", "table", "map-only", "change-order"],
        "Recover a floorplan-driven facilities packet where some facts exist only on the map and corrections override table exports.",
        "Four-page packet with raster floor plan, punch list table, photo log, and change order.",
        ["map callouts", "table rows", "map-only issue", "change order"],
        ["Integrate map and table.", "Do not miss map-only M4.", "Apply visible F3 correction."],
        gold,
        [near_check("m4", "visual", ["M4", "A105", "autoclave", "Priya"], 4, 520)],
        pages,
        facts=[
            fact("p03.floorplan.rooms", "visual_relation", 3, "Floor plan includes A101, A102, A103, Corridor, A104, and A105."),
            fact("p03.p1", "visual_relation", 5, "P1 is a red circle in A102 under sink, active leak, owner Mei, due 2026-07-09, status Open, severity P0."),
            fact("p03.e2", "visual_relation", 5, "E2 is a yellow triangle on A101 west wall, GFCI outlet mislabeled, owner Omar, due 2026-07-12, blocked by permit."),
            fact("p03.f3", "visual_relation", 5, "F3 is a blue square at A103 south door, cracked floor tile, final status Done due to photo correction."),
            fact("p03.m4", "visual_relation", 6, "M4 is map-only purple diamond in A105 Lab east wall for autoclave vent clearance, owner Priya, due 2026-07-20."),
            fact("p03.change", "table_cell", 4, "Change order: E2 permit reinspection $420 not approved; P1 emergency plumbing $1,180 approved; M4 vent clearance shim $260 approved; approved total $1,440."),
        ],
    )


def packet_real_nxlvl_reference() -> Case:
    pages: list[Image.Image] = []
    p1 = base_page("Model Calibration Under Label Drift")
    d = ImageDraw.Draw(p1)
    d.text((100, 150), "A. Rao, L. Chen, M. Iqbal", fill="#475569", font=F["small"])
    draw_text(d, (100, 230), "Abstract: We evaluate calibration under label drift using ten bins and a drift prior. The main result is that replay buffer improves F1 while lowering ECE.", F["small"], width=70)
    d.rounded_rectangle((100, 470, 880, 580), radius=12, fill="#eef2ff", outline="#4338ca", width=3)
    d.text((130, 505), "ECE = sum_b (n_b / n) * |acc(b) - conf(b)|, B = 10", fill="#111827", font=F["small"])
    draw_table(d, 100, 720, [330, 180, 180], [["Method", "ECE down", "F1 up"], ["Baseline", "0.087", "0.781"], ["+ temperature scaling", "0.041", "0.779"], ["+ drift prior", "0.033", "0.802"], ["+ replay buffer", "0.029", "0.817"]], 70)
    d.rounded_rectangle((1010, 470, 1530, 900), radius=14, fill="#fff7ed", outline="#c2410c", width=3)
    draw_text(d, (1040, 510), "Sidebar note: Do not read this before the ablation table. The note explains why the replay buffer row is kept despite higher storage cost.", F["small"], fill="#9a3412", width=34, leading=30)
    pages.append(p1)

    p2 = base_page("Figure 2 - Calibration Curves")
    d = ImageDraw.Draw(p2)
    d.line((220, 1420, 1320, 1420), fill="#111827", width=4)
    d.line((220, 1420, 220, 340), fill="#111827", width=4)
    d.line((220, 1420, 1320, 340), fill="#64748b", width=3)
    curve = [(240, 1380), (430, 1220), (620, 1030), (810, 880), (1000, 790), (1190, 760)]
    for a, b in zip(curve, curve[1:]):
        d.line((*a, *b), fill="#dc2626", width=5)
    d.text((900, 710), "over-confident above 0.75", fill="#dc2626", font=F["small"])
    d.text((620, 1490), "Confidence", fill="#111827", font=F["small"])
    d.text((90, 850), "Accuracy", fill="#111827", font=F["small"])
    d.text((220, 1620), "Caption: dashed diagonal is perfect calibration. Model curve falls below diagonal above confidence 0.75.", fill="#475569", font=F["small"])
    pages.append(p2)

    p3 = base_page("Supplement Table S1 - continued")
    d = ImageDraw.Draw(p3)
    d.text((100, 160), "Rows continue on next page. Do not treat repeated header as data.", fill="#7f1d1d", font=F["small"])
    rows = [["Cohort", "Shift", "n", "ECE", "F1", "Note"], ["A", "none", "1200", "0.029", "0.817", "baseline final"], ["B", "mild", "840", "0.034", "0.804", "uses drift prior"], ["C", "moderate", "610", "0.052", "0.781", "see footnote 1"]]
    draw_table(d, 100, 300, [190, 210, 150, 150, 150, 360], rows, 80)
    d.text((100, 840), "Footnote 1 begins: Cohort C excludes 17 records with missing confidence...", fill="#475569", font=F["small"])
    pages.append(p3)

    p4 = base_page("Supplement Table S1 - continued")
    d = ImageDraw.Draw(p4)
    rows = [["Cohort", "Shift", "n", "ECE", "F1", "Note"], ["D", "severe", "455", "0.071", "0.744", "fails threshold"], ["E", "recovered", "500", "0.038", "0.799", "replay restored"], ["Total", "", "3605", "", "", "do not average ECE from this row"]]
    draw_table(d, 100, 260, [190, 210, 150, 150, 150, 360], rows, 80)
    d.text((100, 780), "Footnote 1 continued: ...so reported n is after exclusion. Table S1 total row is a count total, not an ECE average.", fill="#475569", font=F["small"])
    pages.append(p4)

    p5 = base_page("Supplement Figure S2 - Drift Error Matrix")
    d = ImageDraw.Draw(p5)
    d.text((100, 150), "Color and letter both matter. A slash means the cohort/bin pair requires manual review.", fill="#7f1d1d", font=F["small"])
    x0, y0 = 260, 360
    bins = ["0.50", "0.60", "0.70", "0.80", "0.90"]
    cohorts = ["A none", "B mild", "C moderate", "D severe", "E recovered"]
    matrix = [
        ["L", "L", "M", "M", "H"],
        ["L", "M", "M", "H", "H"],
        ["M", "M", "H", "H", "H"],
        ["M", "H", "H", "H", "H"],
        ["L", "M", "M", "H", "M"],
    ]
    slash_cells = {("C moderate", "0.80"), ("D severe", "0.70"), ("E recovered", "0.60")}
    colors = {"L": "#dcfce7", "M": "#fef3c7", "H": "#fee2e2"}
    d.text((x0 + 260, 275), "Reviewer error level by confidence bin", fill="#111827", font=F["h2"])
    for c, bin_label in enumerate(bins):
        d.text((x0 + 270 + c * 170, y0 - 46), bin_label, fill="#111827", font=F["small"])
    for r, cohort in enumerate(cohorts):
        y = y0 + r * 118
        d.text((x0 - 165, y + 32), cohort, fill="#111827", font=F["small"])
        for c, bin_label in enumerate(bins):
            key = matrix[r][c]
            x = x0 + 250 + c * 170
            d.rectangle((x, y, x + 126, y + 82), fill=colors[key], outline="#111827", width=3)
            d.text((x + 50, y + 25), key, fill="#111827", font=F["small"])
            if (cohort, bin_label) in slash_cells:
                d.line((x + 9, y + 8, x + 118, y + 74), fill="#991b1b", width=4)
    d.rounded_rectangle((100, 1110, 610, 1345), radius=14, fill="#f8fafc", outline="#334155", width=3)
    draw_text(d, (130, 1145), "Legend: L low error; M medium error; H high error. Slash means manual review required.", F["small"], width=35, leading=30)
    d.rounded_rectangle((735, 1110, 1530, 1345), radius=14, fill="#fff7ed", outline="#c2410c", width=3)
    draw_text(d, (765, 1145), "Caption: Cohort D has high error in every bin from 0.60 through 0.90. E recovered at 0.90 is medium, not high.", F["small"], fill="#9a3412", width=56, leading=30)
    pages.append(p5)
    gold = """# Model Calibration Under Label Drift

Authors: A. Rao, L. Chen, M. Iqbal.

Abstract: The paper evaluates calibration under label drift using ten bins and a drift prior. Replay buffer improves F1 while lowering ECE.

Equation: ECE = sum_b (n_b / n) * |acc(b) - conf(b)|, with B = 10.

| Method | ECE down | F1 up |
| --- | ---: | ---: |
| Baseline | 0.087 | 0.781 |
| + temperature scaling | 0.041 | 0.779 |
| + drift prior | 0.033 | 0.802 |
| + replay buffer | 0.029 | 0.817 |

Sidebar note: do not read this before the ablation table. It explains why the replay buffer row is kept despite higher storage cost.

Figure 2: dashed diagonal is perfect calibration. The model curve falls below the diagonal above confidence 0.75 and is annotated "over-confident above 0.75."

## Supplement Table S1

| Cohort | Shift | n | ECE | F1 | Note |
| --- | --- | ---: | ---: | ---: | --- |
| A | none | 1200 | 0.029 | 0.817 | baseline final |
| B | mild | 840 | 0.034 | 0.804 | uses drift prior |
| C | moderate | 610 | 0.052 | 0.781 | see footnote 1 |
| D | severe | 455 | 0.071 | 0.744 | fails threshold |
| E | recovered | 500 | 0.038 | 0.799 | replay restored |
| Total | | 3605 | | | do not average ECE from this row |

Footnote 1: Cohort C excludes 17 records with missing confidence, so reported n is after exclusion. The total row is a count total, not an ECE average.

## Supplement Figure S2 - Drift Error Matrix

Legend: L means low error, M means medium error, and H means high error. A slash means manual review required.

| Cohort | 0.50 | 0.60 | 0.70 | 0.80 | 0.90 |
| --- | --- | --- | --- | --- | --- |
| A none | L | L | M | M | H |
| B mild | L | M | M | H | H |
| C moderate | M | M | H | H with slash | H |
| D severe | M | H | H with slash | H | H |
| E recovered | L | M with slash | M | H | M |

Cohort D has high error in every bin from 0.60 through 0.90. E recovered at 0.90 is medium, not high.
"""
    return Case(
        "P04-scientific-supplement",
        "Scientific Supplement Packet",
        "scientific",
        ["multi-page", "equation", "figure", "continued-table", "footnote"],
        "Recover a scientific article excerpt with figure semantics and a continued supplement table.",
        "Four-page raster scientific packet.",
        ["equation", "ablation table", "figure description", "continued table", "footnote"],
        ["Do not duplicate repeated headers as data.", "Preserve figure semantics and footnote continuation."],
        gold,
        [near_check("cohort-d", "tables", ["D", "severe", "455", "0.071", "0.744"], 3, 360)],
        pages,
        facts=[
            fact("p04.equation", "text", 4, "Equation is ECE = sum_b (n_b / n) * |acc(b) - conf(b)| with B = 10."),
            fact("p04.ablation", "table_cell", 5, "Ablation table preserves baseline 0.087/0.781, temperature scaling 0.041/0.779, drift prior 0.033/0.802, replay buffer 0.029/0.817."),
            fact("p04.sidebar.order", "reading_order", 3, "Sidebar note is after/attached to ablation context, not before the ablation table."),
            fact("p04.figure", "visual_relation", 5, "Figure description includes dashed perfect-calibration diagonal and model curve below diagonal above confidence 0.75 with over-confident annotation."),
            fact("p04.continuation", "cross_page_binding", 6, "Supplement Table S1 merges rows A-E across pages and does not treat repeated headers as data."),
            fact("p04.cohort.rows", "table_cell", 6, "Cohort rows preserve A none 1200 0.029 0.817; C moderate 610 0.052 0.781; D severe 455 0.071 0.744; E recovered 500 0.038 0.799."),
            fact("p04.footnote", "cross_page_binding", 4, "Footnote 1 says Cohort C excludes 17 records with missing confidence and total row is not an ECE average."),
            fact("p04.error.legend", "visual_relation", 4, "Supplement Figure S2 legend says L low error, M medium error, H high error, and slash means manual review required."),
            fact("p04.error.slashes", "visual_relation", 6, "Error matrix slash/manual-review cells are C moderate at 0.80, D severe at 0.70, and E recovered at 0.60."),
            fact("p04.error.d", "visual_relation", 5, "Cohort D severe has M at 0.50 and H at 0.60, 0.70 with slash, 0.80, and 0.90."),
            fact("p04.error.e", "visual_relation", 5, "Cohort E recovered has L at 0.50, M with slash at 0.60, M at 0.70, H at 0.80, and M at 0.90; 0.90 is not high."),
        ],
    )


def packet_conference_program() -> Case:
    pages: list[Image.Image] = []
    for day, title in [(1, "OpsConf 2026 - Day 1"), (2, "OpsConf 2026 - Day 2")]:
        img = base_page(title)
        d = ImageDraw.Draw(img)
        d.text((100, 155), "Legend: star = preregistration; dot = hybrid; X = canceled. Merged cells span rooms or times.", fill="#7f1d1d", font=F["small"])
        rows = [["Time", "Hall A", "Lab 1", "Lab 2"], ["08:30-09:00", "Registration spans all rooms", "", ""], ["09:00-09:45", "Keynote" if day == 1 else "Metrics that Matter", "", ""], ["10:00-10:45", "star SLO Math", "dot Tracing Lab", "Cost Controls"], ["11:00-12:00", "Vendor briefings", "Incident Drill spans Lab 1 and Lab 2", ""], ["12:00-13:00", "Lunch spans all rooms", "", ""], ["13:15-14:00", "Postmortem Patterns", "Forecasting", "FinOps Clinic"]]
        if day == 2:
            rows[3] = ["10:00-10:45", "X SLO Math canceled", "dot Tracing Lab moved to Hall A", "Cost Controls"]
        draw_table(d, 80, 260, [220, 410, 410, 410], rows, 86)
        pages.append(img)
    p3 = base_page("Room Map and Errata")
    d = ImageDraw.Draw(p3)
    d.rectangle((120, 260, 600, 620), outline="#111827", width=4)
    d.text((260, 420), "Hall A", fill="#111827", font=F["h2"])
    d.rectangle((760, 260, 1120, 500), outline="#111827", width=4)
    d.text((870, 360), "Lab 1", fill="#111827", font=F["h2"])
    d.rectangle((760, 560, 1120, 800), outline="#111827", width=4)
    d.text((870, 660), "Lab 2", fill="#111827", font=F["h2"])
    d.rounded_rectangle((120, 980, 1500, 1230), radius=14, fill="#fff7ed", outline="#c2410c", width=4)
    draw_text(d, (150, 1015), "Errata for Day 2: SLO Math is canceled. Tracing Lab moves to Hall A at 10:00. Incident Drill still spans Lab 1 and Lab 2 at 11:00.", F["small"], fill="#9a3412", width=92, leading=31)
    pages.append(p3)
    gold = """# OpsConf 2026 Program

Legend: star = preregistration; dot = hybrid; X = canceled. Merged cells span rooms or times.

## Day 1

| Time | Hall A | Lab 1 | Lab 2 |
| --- | --- | --- | --- |
| 08:30-09:00 | Registration spans all rooms | | |
| 09:00-09:45 | Keynote | | |
| 10:00-10:45 | star SLO Math | dot Tracing Lab | Cost Controls |
| 11:00-12:00 | Vendor briefings | Incident Drill spans Lab 1 and Lab 2 | |
| 12:00-13:00 | Lunch spans all rooms | | |
| 13:15-14:00 | Postmortem Patterns | Forecasting | FinOps Clinic |

## Day 2

Day 2 errata controls over the printed grid: SLO Math is canceled. Tracing Lab moves to Hall A at 10:00. Incident Drill still spans Lab 1 and Lab 2 at 11:00.

Room map: Hall A is separate from Lab 1 and Lab 2; Lab 1 is above Lab 2.
"""
    return Case(
        "P05-conference-program-packet",
        "Conference Program Packet",
        "schedule",
        ["multi-page", "schedule", "merged-cells", "errata", "room-map"],
        "Recover multi-day schedule grids and apply visible errata without losing room span semantics.",
        "Three-page conference program with schedule grids and room map/errata.",
        ["day schedules", "legend", "errata", "room map"],
        ["Preserve merged-cell semantics.", "Apply Day 2 errata.", "Keep cancellation and moved session states."],
        gold,
        [near_check("day2-errata", "spatial", ["SLO Math", "canceled", "Tracing Lab", "Hall A"], 4, 520)],
        pages,
        facts=[
            fact("p05.legend", "visual_relation", 3, "Legend says star means preregistration, dot means hybrid, X means canceled, merged cells span rooms or times."),
            fact("p05.day1.1000", "spatial", 4, "Day 1 10:00-10:45 has star SLO Math in Hall A, dot Tracing Lab in Lab 1, and Cost Controls in Lab 2."),
            fact("p05.day1.incident", "spatial", 4, "Day 1 11:00-12:00 has Vendor briefings in Hall A and Incident Drill spanning Lab 1 and Lab 2."),
            fact("p05.day2.errata", "spatial", 6, "Day 2 errata says SLO Math is canceled and Tracing Lab moves to Hall A at 10:00."),
            fact("p05.day2.incident", "spatial", 4, "Day 2 Incident Drill still spans Lab 1 and Lab 2 at 11:00."),
            fact("p05.map", "visual_relation", 3, "Room map shows Hall A separate from Lab 1 and Lab 2, with Lab 1 above Lab 2."),
        ],
    )


def prefixed_checks(prefix: str, checks: list[dict]) -> list[dict]:
    updated = []
    for check in checks:
        copy = dict(check)
        copy["id"] = f"{prefix}.{check['id']}"
        copy["description"] = f"{prefix}: {check.get('description', check['id'])}"
        updated.append(copy)
    return updated


def packet_real_push_pitch_reference() -> Case:
    gantt = h03()
    timeline = h07()
    matrix = h14()
    heatmap = h15()

    cover = base_page("NOC Handover Packet - Week 32")
    d = ImageDraw.Draw(cover)
    d.text((100, 150), "Packet prepared for the 2026-08-03 reliability handoff.", fill="#475569", font=F["small"])
    draw_card(
        d,
        (95, 245, 760, 555),
        "Handoff scope",
        [
            "Normalize the raster Gantt into task rows",
            "Preserve GTM lane/month ownership",
            "Bind team-matrix facts by column",
            "Read heatmap color + letter + slash state",
        ],
        "#f8fafc",
        "#334155",
    )
    draw_card(
        d,
        (850, 245, 1530, 555),
        "Why this packet exists",
        [
            "Several pages are image exports",
            "Some tables have no borders",
            "Some values are visual-only",
            "Weekend columns are in scope",
        ],
        "#fff7ed",
        "#c2410c",
    )
    rows = [
        ["Page", "Artifact", "Reconstruction obligation"],
        ["1", "Cover", "Preserve scope and page order"],
        ["2", "Raster shift Gantt", "Infer start/end from bar positions"],
        ["3", "Overlapping GTM timeline", "Bind card to lane and month span"],
        ["4", "Borderless team matrix", "Bind facts under each person column"],
        ["5", "Escalation heatmap", "Preserve color/letter/slash/weekend semantics"],
    ]
    draw_table(d, 110, 720, [140, 420, 760], rows, 78)
    draw_text(
        d,
        (110, 1230),
        "This is a realistic handover packet assembled from exported slides and status inserts. Do not flatten it into a summary; reconstruct each artifact where it appears.",
        F["small"],
        fill="#7f1d1d",
        width=88,
        leading=31,
    )

    gold = f"""# NOC Handover Packet - Week 32

Packet prepared for the 2026-08-03 reliability handoff.

The packet contains a cover page, raster shift Gantt, overlapping GTM timeline, borderless team matrix, and escalation heatmap. Several pages are image exports; some values are visual-only. Preserve page order and reconstruct each artifact where it appears.

## Raster Shift Gantt

{gantt.gold}

## Overlapping GTM Timeline

{timeline.gold}

## Borderless Team Matrix

{matrix.gold}

## Escalation Heatmap

{heatmap.gold}
"""

    checks = []
    checks += prefixed_checks("gantt", gantt.checks)
    checks += prefixed_checks("timeline", timeline.checks)
    checks += prefixed_checks("matrix", matrix.checks)
    checks += prefixed_checks("heatmap", heatmap.checks)
    checks += [
        ordered_check(
            "packet.page-order",
            "structure",
            ["Raster Shift Gantt", "Overlapping GTM Timeline", "Borderless Team Matrix", "Escalation Heatmap"],
            3,
            "Packet preserves artifact order: Gantt, timeline, team matrix, heatmap.",
        )
    ]

    return Case(
        "P06-noc-handover-packet",
        "NOC Handover Packet",
        "packet",
        ["multi-page", "raster-gantt", "timeline", "borderless-table", "heatmap", "visual-binding"],
        "Stress realistic multi-page handover reconstruction with spatial spans, borderless alignment, and dense visual encodings.",
        "Five-page packet composed of exported slide/image artifacts and a cover page.",
        ["page order", "Gantt rows", "timeline lanes", "team matrix bindings", "heatmap semantics"],
        [
            "Do not summarize the packet.",
            "Infer visual-only spans and cell states.",
            "Keep each artifact in page order.",
            "Bind facts to the correct lane, person column, team row, and day column.",
        ],
        gold,
        checks,
        [cover, *gantt.pages, *timeline.pages, *matrix.pages, *heatmap.pages],
        facts=[
            fact("p06.page_order", "structure", 4, "The output preserves the artifact order: raster shift Gantt, overlapping GTM timeline, borderless team matrix, then escalation heatmap."),
            fact("p06.gantt.dock", "spatial", 4, "Gantt: Dock intake is owned by Noor, runs 08:00-11:00, and has label Load A-17."),
            fact("p06.gantt.release", "spatial", 4, "Gantt: Release gate is owned by Ken, runs 10:00-16:30, and has label REL-82."),
            fact("p06.gantt.qa", "spatial", 4, "Gantt: QA bench is owned by Priya, runs 12:00-15:00, and has label Lot Q4."),
            fact("p06.gantt.rollback", "spatial", 4, "Gantt: Rollback watch is owned by Mira, runs 16:00-18:00, and has label RB-9."),
            fact("p06.timeline.product", "visual_relation", 5, "Timeline: Product lane has Beta signups in Aug owned by Maya target 1,200, and Workflow v2 spanning Sep-Oct owned by Jon shipping Oct 18."),
            fact("p06.timeline.security", "visual_relation", 5, "Timeline: Security lane has SOC2 audit spanning Aug-Oct owned by Priya and HIPAA BAA spanning Oct-Nov owned by Lena."),
            fact("p06.timeline.sales", "visual_relation", 5, "Timeline: Sales lane has Design partners in Aug owned by Omar with 9 accounts and Enterprise pilots spanning Sep-Nov owned by Omar with $4.2M pipeline."),
            fact("p06.timeline.dependency", "visual_relation", 4, "Timeline dependency says HIPAA BAA belongs to Security, not Product, and Enterprise pilots depend on BAA legal review."),
            fact("p06.matrix.maya", "visual_relation", 4, "Team matrix: Maya Singh is CEO/Product, ex-Stripe, 12 yrs product, led Relay launch."),
            fact("p06.matrix.jon", "visual_relation", 4, "Team matrix: Jon Bell is CTO/Infra, ex-Snowflake, owns retrieval infra, built vector cache."),
            fact("p06.matrix.priya", "visual_relation", 4, "Team matrix: Priya Nair is COO/Ops, ex-Flexport, scaled support, owns compliance."),
            fact("p06.matrix.omar", "visual_relation", 4, "Team matrix: Omar Haddad is GTM/RevOps, ex-Atlassian, pipeline $4.2M, leads enterprise sales."),
            fact("p06.matrix.sidebars", "structure", 4, "Advisors Lena Ortiz and Theo Park are separate from core team; VP Sales Q4 and Clinical Lead Q1 are open roles, not employees."),
            fact("p06.heatmap.legend", "visual_relation", 4, "Heatmap legend: G green normal, Y yellow watch, R red escalation; diagonal slash means owner must page incident lead."),
            fact("p06.heatmap.slashes", "visual_relation", 6, "Critical red slash cells are API Thu, Data Fri, Export Wed, and Billing Sat."),
            fact("p06.heatmap.export_fri", "visual_relation", 5, "Export Friday is yellow, not red and not slash-marked."),
            fact("p06.heatmap.weekend", "structure", 3, "Saturday/weekend columns are preserved and not dropped."),
        ],
    )


def packet_launch_readiness() -> Case:
    pages: list[Image.Image] = []

    p1 = base_page("Northwest Pilot Launch Dossier")
    d = ImageDraw.Draw(p1)
    d.text((100, 150), "Prepared for: Retail Operations Steering Committee | Packet date: 2026-08-10 | Status: conditional go", fill="#475569", font=F["small"])
    d.text((100, 230), "Executive memo", fill="#111827", font=F["h1"])
    left_memo = (
        "The Northwest pilot can proceed only if store enablement, gateway inventory, and payment-switch monitoring stay inside the launch guardrails. "
        "The program remains a conditional go because Spokane North cleared training late, Bend has one unresolved POS gateway exception, and the Portland service desk still has elevated Tier 2 backlog after the weekend migration. "
        "The visible decision log below supersedes the draft appendix included at the end of this packet."
    )
    right_memo = (
        "Launch scope covers six stores, two fulfillment nodes, and three payment partners. The activation target is 4,850 devices by Friday close. "
        "Finance approved the reserve draw only for gateway freight and temporary floor support; signage reprint remains unfunded. "
        "Operations must preserve the Monday risk snapshot, chart values, and dependency diagram because several values are not repeated in body text."
    )
    draw_text(d, (100, 295), left_memo, F["small"], width=52, leading=31)
    draw_text(d, (910, 295), right_memo, F["small"], width=50, leading=31)
    d.rounded_rectangle((100, 690, 1540, 910), radius=14, fill="#fff7ed", outline="#c2410c", width=4)
    draw_text(d, (130, 725), "Visible steering decision: CONDITIONAL GO. Hold criteria: Bend POS exception open after 2026-08-12 17:00, payment-switch error rate above 1.2%, or Tier 2 backlog above 22 at launch review.", F["small"], fill="#9a3412", width=100, leading=31)
    rows = [
        ["Decision item", "Owner", "Due", "State", "Condition"],
        ["Gateway freight reserve", "Iris", "2026-08-11", "Approved", "$18.4k cap"],
        ["Bend POS exception", "Mateo", "2026-08-12 17:00", "Open", "must close before go"],
        ["Service desk staffing", "Priya", "2026-08-13 09:00", "Conditional", "Tier 2 backlog <= 22"],
        ["Signage reprint", "Noah", "deferred", "Not funded", "do not include in reserve"],
    ]
    draw_table(d, 100, 1010, [330, 190, 240, 220, 430], rows, 72)
    d.text((100, 1475), "Packet order: memo, dashboard, dependency map, store readiness, escalation heatmap, procurement, draft appendix.", fill="#475569", font=F["small"])
    pages.append(p1)

    p2 = base_page("Launch Metrics Dashboard")
    d = ImageDraw.Draw(p2)
    d.text((100, 150), "All panels are visible dashboard exports. Values in charts are part of the launch record.", fill="#7f1d1d", font=F["small"])
    d.rounded_rectangle((80, 240, 820, 780), radius=14, fill="#f8fafc", outline="#334155", width=3)
    d.text((115, 275), "Device activations by day", fill="#111827", font=F["h2"])
    x_axis, y_axis = 160, 690
    d.line((x_axis, y_axis, 760, y_axis), fill="#111827", width=3)
    d.line((x_axis, y_axis, x_axis, 360), fill="#111827", width=3)
    pts = [(185, 642), (300, 595), (415, 535), (530, 445), (645, 390)]
    values = [920, 1280, 1740, 2510, 3220]
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    for a, b in zip(pts, pts[1:]):
        d.line((*a, *b), fill="#2563eb", width=5)
    for p, day, value in zip(pts, days, values):
        d.ellipse((p[0] - 7, p[1] - 7, p[0] + 7, p[1] + 7), fill="#2563eb")
        d.text((p[0] - 25, p[1] - 35), str(value), fill="#111827", font=F["tiny"])
        d.text((p[0] - 20, 710), day, fill="#111827", font=F["tiny"])
    d.rounded_rectangle((900, 240, 1590, 780), radius=14, fill="#f8fafc", outline="#334155", width=3)
    d.text((930, 275), "Backlog by queue", fill="#111827", font=F["h2"])
    queues = [("Tier 1", 31, 12), ("Tier 2", 19, 8), ("Partner", 9, 4), ("Fraud", 6, 2)]
    for i, (name, open_, blocked) in enumerate(queues):
        x = 970 + i * 145
        yb = 690
        d.rectangle((x, yb - open_ * 8, x + 58, yb), fill="#93c5fd", outline="#1d4ed8", width=2)
        d.rectangle((x, yb - (open_ + blocked) * 8, x + 58, yb - open_ * 8), fill="#fca5a5", outline="#b91c1c", width=2)
        d.text((x - 8, yb + 22), name, fill="#111827", font=F["tiny"])
        d.text((x, yb - (open_ + blocked) * 8 - 32), f"{open_}+{blocked}", fill="#111827", font=F["tiny"])
    d.text((930, 730), "blue=open, red=blocked", fill="#475569", font=F["tiny"])
    rows = [
        ["Guardrail", "Limit", "Current", "State"],
        ["Payment-switch error rate", "<=1.2%", "0.9%", "OK"],
        ["Tier 2 backlog", "<=22", "27", "At risk"],
        ["Gateway inventory buffer", ">=140", "126", "Breach"],
        ["Store training completion", ">=95%", "92%", "At risk"],
    ]
    draw_table(d, 105, 910, [430, 260, 240, 260], rows, 76)
    d.rounded_rectangle((100, 1380, 1545, 1600), radius=14, fill="#fee2e2", outline="#991b1b", width=4)
    draw_text(d, (130, 1415), "Dashboard warning: review the guardrail table before launch review. Conditional go does not become final until the Bend exception is closed and service-desk load is back inside threshold.", F["small"], fill="#991b1b", width=100, leading=31)
    pages.append(p2)

    p3 = base_page("Dependency Map - Payment Activation Path")
    d = ImageDraw.Draw(p3)
    d.text((100, 150), "Solid arrows are required launch dependencies. Dashed arrows are fallback paths.", fill="#475569", font=F["small"])
    lanes = [("Store", 265, "#eef2ff"), ("Edge", 610, "#ecfeff"), ("Cloud", 955, "#f8fafc"), ("Partners", 1300, "#fff7ed")]
    for label, x, fill in lanes:
        d.rounded_rectangle((x, 250, x + 260, 1490), radius=18, fill=fill, outline="#cbd5e1", width=3)
        d.text((x + 70, 280), label, fill="#111827", font=F["h2"])
    nodes = {
        "POS": (300, 470, "POS terminals"),
        "Handheld": (300, 760, "Handheld scanners"),
        "EdgeGW": (645, 610, "Edge gateway"),
        "Switch": (990, 610, "Payment switch"),
        "Risk": (990, 900, "Risk rules"),
        "Acquirer": (1335, 560, "Acquirer A"),
        "Fraud": (1335, 900, "Fraud desk"),
        "Ledger": (990, 1210, "Settlement ledger"),
    }
    for key, (x, y, label) in nodes.items():
        d.rounded_rectangle((x, y, x + 205, y + 82), radius=12, fill="white", outline="#111827", width=3)
        draw_text(d, (x + 16, y + 18), label, F["tiny"], width=16, leading=23)
    arrows = [("POS", "EdgeGW"), ("Handheld", "EdgeGW"), ("EdgeGW", "Switch"), ("Switch", "Acquirer"), ("Risk", "Fraud")]
    for a, b in arrows:
        ax, ay, _ = nodes[a]
        bx, by, _ = nodes[b]
        d.line((ax + 205, ay + 41, bx, by + 41), fill="#111827", width=4)
        d.polygon([(bx, by + 41), (bx - 14, by + 31), (bx - 14, by + 51)], fill="#111827")
    # Switch-to-risk enters the risk box from above so it does not cut through the label.
    d.line((1092, 692, 1092, 900), fill="#111827", width=4)
    d.polygon([(1092, 900), (1082, 882), (1102, 882)], fill="#111827")
    # Route the required ledger dependency around the Risk node so labels remain readable.
    d.line((1195, 651, 1260, 651, 1260, 1251, 1195, 1251), fill="#111827", width=4)
    d.polygon([(1195, 1251), (1213, 1241), (1213, 1261)], fill="#111827")
    d.line((300 + 205, 760 + 82, 990, 1210), fill="#64748b", width=3)
    for off in range(0, 520, 28):
        d.line((505 + off, 842 + int(off * 0.7), 515 + off, 849 + int(off * 0.7)), fill="#64748b", width=3)
    d.rounded_rectangle((100, 1620, 1510, 1850), radius=14, fill="#fff7ed", outline="#c2410c", width=3)
    draw_text(d, (130, 1655), "Map note: Bend POS exception is on the POS terminals to Edge gateway dependency. Fallback handheld-to-ledger path exists but does not satisfy payment authorization.", F["small"], fill="#9a3412", width=98, leading=31)
    pages.append(p3)

    p4 = base_page("Store Readiness Register")
    d = ImageDraw.Draw(p4)
    d.text((100, 150), "Status register exported from the launch tracker. Abbreviations: OK, AR=at risk, BLK=blocked.", fill="#475569", font=F["small"])
    rows = [
        ["Store", "Mgr", "Training", "Gateways", "Signage", "POS", "Staffing", "Open issue"],
        ["SEA-01 Pike", "Mina", "OK", "148", "OK", "OK", "OK", "none"],
        ["SEA-04 Ballard", "Ravi", "OK", "136", "OK", "OK", "AR", "temp floor support"],
        ["PDX-02 Pearl", "Jon", "OK", "142", "OK", "OK", "OK", "none"],
        ["PDX-05 East", "Lena", "AR", "131", "OK", "OK", "OK", "training makeup Thu"],
        ["BND-01 Bend", "Mateo", "OK", "126", "OK", "BLK", "OK", "gateway exception"],
        ["SPK-03 North", "Asha", "AR", "144", "OK", "OK", "AR", "late completion"],
    ]
    draw_table(d, 60, 250, [190, 130, 150, 150, 145, 115, 145, 395], rows, 72)
    d.rounded_rectangle((95, 850, 760, 1150), radius=14, fill="#fee2e2", outline="#991b1b", width=3)
    draw_text(d, (125, 885), "Exception: BND-01 Bend is the only blocked POS row. It also has the lowest gateway count at 126.", F["small"], fill="#991b1b", width=44, leading=30)
    d.rounded_rectangle((855, 850, 1525, 1150), radius=14, fill="#fef3c7", outline="#92400e", width=3)
    draw_text(d, (885, 885), "Training risk: PDX-05 East and SPK-03 North are at risk. SEA-04 Ballard staffing is at risk but training is OK.", F["small"], fill="#92400e", width=45, leading=30)
    pages.append(p4)

    p5 = base_page("Escalation Matrix - Store x Workstream")
    d = ImageDraw.Draw(p5)
    d.text((100, 150), "Launch operations matrix - status letter, escalation slash, and partner dot are all part of the cell state.", fill="#475569", font=F["small"])
    stores = ["SEA-01", "SEA-04", "PDX-02", "PDX-05", "BND-01", "SPK-03"]
    streams = ["Training", "Gateway", "POS", "Staffing", "Partner"]
    matrix = [
        ["G", "G", "G", "G", "G"],
        ["G", "Y", "G", "Y", "G"],
        ["G", "G", "G", "G", "Y"],
        ["Y", "Y", "G", "G", "G"],
        ["G", "R", "R", "Y", "R"],
        ["Y", "G", "G", "Y", "G"],
    ]
    slash = {("BND-01", "POS"), ("BND-01", "Partner"), ("PDX-05", "Gateway")}
    dot = {("BND-01", "Partner"), ("PDX-02", "Partner")}
    colors = {"G": "#16a34a", "Y": "#d97706", "R": "#dc2626"}
    labels = {"G": "clear", "Y": "watch", "R": "blocked"}
    x0, y0 = 285, 330
    cell_w, cell_h = 185, 72
    d.rectangle((80, 270, 1425, 845), fill="#ffffff", outline="#cbd5e1", width=2)
    d.rectangle((80, 270, 1425, 330), fill="#f8fafc")
    d.rectangle((80, 270, 285, 845), fill="#f8fafc")
    for c, stream in enumerate(streams):
        d.text((x0 + c * cell_w + 12, y0 - 45), stream, fill="#111827", font=F["tiny_bold"])
    for r, store in enumerate(stores):
        y = y0 + r * cell_h
        d.line((80, y, 1425, y), fill="#e2e8f0", width=2)
        d.text((95, y + 23), store, fill="#111827", font=F["small_bold"])
        for c, stream in enumerate(streams):
            value = matrix[r][c]
            x = x0 + c * cell_w
            d.line((x, 270, x, 845), fill="#e2e8f0", width=2)
            d.rounded_rectangle((x + 14, y + 17, x + 58, y + 52), radius=6, fill="#ffffff", outline=colors[value], width=3)
            d.text((x + 28, y + 24), value, fill=colors[value], font=F["tiny_bold"])
            d.text((x + 70, y + 24), labels[value], fill="#334155", font=F["tiny"])
            if (store, stream) in slash:
                d.line((x + 120, y + 18, x + 155, y + 54), fill="#991b1b", width=4)
            if (store, stream) in dot:
                d.ellipse((x + 158, y + 23, x + 174, y + 39), fill="#111827")
    d.line((80, 845, 1425, 845), fill="#cbd5e1", width=2)
    d.line((1425, 270, 1425, 845), fill="#cbd5e1", width=2)
    draw_section(d, 90, 940, "Legend and exception notes", w=1360)
    d.rounded_rectangle((95, 1010, 650, 1230), radius=8, fill="#f8fafc", outline="#cbd5e1", width=2)
    draw_text(d, (120, 1042), "G = clear, Y = watch, R = blocked. A red slash means executive escalation. A black dot means external partner follow-up is required.", F["small"], width=38, leading=30)
    d.rounded_rectangle((720, 1010, 1510, 1230), radius=8, fill="#fff7ed", outline="#fed7aa", width=2)
    draw_text(d, (748, 1042), "Readout: BND-01 has blocked Gateway, POS, and Partner cells. PDX-05 has a Gateway slash but POS is clear. PDX-02 Partner has a dot without a red block.", F["small"], fill="#9a3412", width=56, leading=30)
    pages.append(p5)

    p6 = base_page("Procurement and Reserve Ledger")
    d = ImageDraw.Draw(p6)
    rows = [
        ["Line", "Vendor", "Purpose", "Amount", "Reserve eligible", "Paid"],
        ["1", "LumenWorks", "gateway freight expedite", "$12,640", "Yes", "No"],
        ["2", "FieldBridge", "temporary floor support", "$5,760", "Yes", "Partial $2,000"],
        ["3", "SignPro", "signage reprint", "$3,480", "No", "No"],
        ["4", "SwitchOps", "payment monitor extension", "$2,900", "Yes", "No"],
        ["5", "Northstar Print", "training packet reprint", "$740", "No", "Paid"],
    ]
    draw_table(d, 70, 245, [110, 220, 390, 180, 240, 240], rows, 78)
    d.rounded_rectangle((100, 830, 720, 1090), radius=14, fill="#f8fafc", outline="#334155", width=3)
    draw_text(d, (130, 865), "Reserve subtotal before payment: $21,300. FieldBridge partial payment: -$2,000. Remaining eligible reserve exposure: $19,300.", F["small"], width=42, leading=30)
    d.rounded_rectangle((875, 830, 1510, 1090), radius=14, fill="#fee2e2", outline="#991b1b", width=4)
    draw_text(d, (905, 865), "Accounts payable note: PARTIAL PAID applies only to FieldBridge, not to the whole ledger. Signage reprint is not reserve eligible.", F["small"], fill="#991b1b", width=32, leading=30)
    d.line((1135, 1038, 1450, 960), fill="#991b1b", width=8)
    d.text((1170, 985), "PARTIAL PAID", fill="#991b1b", font=F["stamp"])
    pages.append(p6)

    p7 = base_page("Draft Appendix - Superseded Values")
    d = ImageDraw.Draw(p7)
    d.text((100, 155), "DRAFT APPENDIX - retained for audit context only", fill="#991b1b", font=F["h1"])
    rows = [
        ["Draft field", "Draft value", "Visible final value", "Disposition"],
        ["Launch decision", "GO", "CONDITIONAL GO", "superseded"],
        ["Tier 2 backlog", "18", "27", "superseded"],
        ["Gateway inventory buffer", "158", "126", "superseded"],
        ["Bend POS", "OK", "BLK/open exception", "superseded"],
        ["Reserve exposure", "$17,300", "$19,300", "superseded"],
    ]
    draw_table(d, 90, 300, [330, 260, 330, 250], rows, 82)
    draw_text(d, (100, 870), "Audit note: do not replace final dashboard or ledger values with this draft appendix. It exists to show why the steering decision changed after Monday risk review.", F["small"], fill="#7f1d1d", width=90, leading=31)
    pages.append(p7)

    gold = """# Northwest Pilot Launch Dossier

Prepared for the Retail Operations Steering Committee. Packet date: 2026-08-10. Status: conditional go.

## Executive Memo

The Northwest pilot is a conditional go. The visible steering decision supersedes the draft appendix. Hold criteria are: Bend POS exception open after 2026-08-12 17:00, payment-switch error rate above 1.2%, or Tier 2 backlog above 22 at launch review.

| Decision item | Owner | Due | State | Condition |
| --- | --- | --- | --- | --- |
| Gateway freight reserve | Iris | 2026-08-11 | Approved | $18.4k cap |
| Bend POS exception | Mateo | 2026-08-12 17:00 | Open | must close before go |
| Service desk staffing | Priya | 2026-08-13 09:00 | Conditional | Tier 2 backlog <= 22 |
| Signage reprint | Noah | deferred | Not funded | do not include in reserve |

## Launch Metrics Dashboard

Device activations by day: Monday 920, Tuesday 1280, Wednesday 1740, Thursday 2510, Friday 3220.

Backlog by queue: Tier 1 has 31 open and 12 blocked; Tier 2 has 19 open and 8 blocked; Partner has 9 open and 4 blocked; Fraud has 6 open and 2 blocked.

| Guardrail | Limit | Current | State |
| --- | --- | --- | --- |
| Payment-switch error rate | <=1.2% | 0.9% | OK |
| Tier 2 backlog | <=22 | 27 | At risk |
| Gateway inventory buffer | >=140 | 126 | Breach |
| Store training completion | >=95% | 92% | At risk |

Dashboard warning: review the guardrail table before launch review. From the guardrail table, gateway inventory buffer is breached at 126 and Tier 2 backlog is at risk at 27. Conditional go remains valid only if Bend POS closes and service-desk load returns inside threshold.

## Dependency Map

Required solid dependencies: POS terminals to Edge gateway; Handheld scanners to Edge gateway; Edge gateway to Payment switch; Payment switch to Acquirer A; Payment switch to Risk rules; Risk rules to Fraud desk; Payment switch to Settlement ledger. A dashed fallback path runs from Handheld scanners to Settlement ledger, but it does not satisfy payment authorization.

Bend POS exception is on the POS terminals to Edge gateway dependency.

## Store Readiness Register

| Store | Mgr | Training | Gateways | Signage | POS | Staffing | Open issue |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| SEA-01 Pike | Mina | OK | 148 | OK | OK | OK | none |
| SEA-04 Ballard | Ravi | OK | 136 | OK | OK | AR | temp floor support |
| PDX-02 Pearl | Jon | OK | 142 | OK | OK | OK | none |
| PDX-05 East | Lena | AR | 131 | OK | OK | OK | training makeup Thu |
| BND-01 Bend | Mateo | OK | 126 | OK | BLK | OK | gateway exception |
| SPK-03 North | Asha | AR | 144 | OK | OK | AR | late completion |

BND-01 Bend is the only blocked POS row and has the lowest gateway count at 126. PDX-05 East and SPK-03 North are training risks. SEA-04 Ballard has staffing risk but training is OK.

## Escalation Matrix

Legend: G green clear; Y yellow watch; R red blocked. Slash means executive escalation. Dot means external partner required.

| Store | Training | Gateway | POS | Staffing | Partner |
| --- | --- | --- | --- | --- | --- |
| SEA-01 | G | G | G | G | G |
| SEA-04 | G | Y | G | Y | G |
| PDX-02 | G | G | G | G | Y with dot |
| PDX-05 | Y | Y with slash | G | G | G |
| BND-01 | G | R | R with slash | Y | R with slash and dot |
| SPK-03 | Y | G | G | Y | G |

Matrix reading: BND-01 has red Gateway, red POS with slash, and red Partner with slash and dot. PDX-05 Gateway is yellow with slash, not red.

## Procurement and Reserve Ledger

| Line | Vendor | Purpose | Amount | Reserve eligible | Paid |
| --- | --- | --- | ---: | --- | --- |
| 1 | LumenWorks | gateway freight expedite | $12,640 | Yes | No |
| 2 | FieldBridge | temporary floor support | $5,760 | Yes | Partial $2,000 |
| 3 | SignPro | signage reprint | $3,480 | No | No |
| 4 | SwitchOps | payment monitor extension | $2,900 | Yes | No |
| 5 | Northstar Print | training packet reprint | $740 | No | Paid |

Reserve subtotal before payment is $21,300. FieldBridge partial payment is -$2,000. Remaining eligible reserve exposure is $19,300. PARTIAL PAID applies only to FieldBridge, not to the whole ledger. Signage reprint is not reserve eligible.

## Draft Appendix

The draft appendix is superseded and retained only for audit context. Draft GO, Tier 2 backlog 18, gateway inventory 158, Bend POS OK, and reserve exposure $17,300 must not replace final visible values: CONDITIONAL GO, Tier 2 backlog 27, gateway inventory 126, Bend POS BLK/open exception, and reserve exposure $19,300.
"""
    return Case(
        "P07-launch-readiness-dossier",
        "Launch Readiness Dossier",
        "packet",
        ["multi-page", "dashboard", "dependency-map", "readiness-table", "heatmap", "ledger", "source-precedence"],
        "Stress a dense realistic launch dossier with mixed memo text, chart values, map relationships, wide tables, visual status matrices, procurement nuance, and superseded appendix values.",
        "Seven-page raster-heavy launch dossier with charts, tables, diagram, heatmap, ledger, and draft appendix.",
        ["decision memo", "dashboard", "dependency map", "readiness register", "escalation matrix", "ledger", "draft appendix precedence"],
        ["Preserve dense page order and all major sections.", "Bind visual statuses to the correct row/column.", "Keep draft appendix values superseded."],
        gold,
        [near_check("launch-bend", "visual", ["BND-01", "Mateo", "126", "BLK", "gateway exception"], 4, 520)],
        pages,
        facts=[
            fact("p07.memo.decision", "text", 5, "Steering decision is CONDITIONAL GO, and hold criteria are Bend POS open after 2026-08-12 17:00, payment-switch error rate above 1.2%, or Tier 2 backlog above 22."),
            fact("p07.decision.table", "table_cell", 5, "Decision table preserves gateway freight reserve/Iris/2026-08-11/Approved/$18.4k cap; Bend POS exception/Mateo/2026-08-12 17:00/Open; Service desk staffing/Priya/Conditional; Signage reprint/Noah/deferred/Not funded."),
            fact("p07.activations", "visual_relation", 5, "Device activation chart values are Mon 920, Tue 1280, Wed 1740, Thu 2510, Fri 3220."),
            fact("p07.backlog", "visual_relation", 5, "Backlog stacked bars preserve Tier 1 31 open/12 blocked, Tier 2 19 open/8 blocked, Partner 9 open/4 blocked, Fraud 6 open/2 blocked."),
            fact("p07.guardrails", "table_cell", 6, "Guardrail table preserves payment-switch 0.9% OK, Tier 2 backlog 27 At risk, gateway inventory 126 Breach, training completion 92% At risk."),
            fact("p07.warning", "cross_page_binding", 5, "Dashboard warning points to the guardrail table; the table shows gateway inventory buffer breached at 126 and Tier 2 backlog at risk at 27. Go remains conditional until Bend closes and service-desk load returns inside threshold."),
            fact("p07.map.required", "visual_relation", 6, "Dependency map required arrows: POS and Handheld to Edge gateway, Edge gateway to Payment switch, Payment switch to Acquirer A, Risk rules, and Settlement ledger, and Risk rules to Fraud desk."),
            fact("p07.map.fallback", "visual_relation", 5, "Dashed fallback path is Handheld scanners to Settlement ledger and does not satisfy payment authorization; Bend POS exception is on POS terminals to Edge gateway."),
            fact("p07.readiness.bend", "table_cell", 6, "Readiness row for BND-01 Bend has Mateo, training OK, gateways 126, signage OK, POS BLK, staffing OK, open issue gateway exception."),
            fact("p07.readiness.training", "table_cell", 5, "PDX-05 East and SPK-03 North are training at risk; SEA-04 Ballard staffing is at risk but training is OK."),
            fact("p07.matrix.legend", "visual_relation", 4, "Escalation matrix legend: G green clear, Y yellow watch, R red blocked, slash executive escalation, dot external partner required."),
            fact("p07.matrix.bend", "visual_relation", 7, "BND-01 escalation matrix has Gateway R, POS R with slash, Staffing Y, and Partner R with slash and dot."),
            fact("p07.matrix.exceptions", "visual_relation", 5, "PDX-05 Gateway is Y with slash, not red; PDX-02 Partner is Y with dot."),
            fact("p07.ledger.rows", "table_cell", 6, "Ledger preserves LumenWorks $12,640 eligible unpaid, FieldBridge $5,760 eligible partial $2,000, SignPro $3,480 not eligible, SwitchOps $2,900 eligible, Northstar Print $740 not eligible paid."),
            fact("p07.reserve", "table_cell", 5, "Reserve subtotal before payment is $21,300, FieldBridge partial payment is -$2,000, remaining eligible reserve exposure is $19,300, and PARTIAL PAID applies only to FieldBridge."),
            fact("p07.superseded", "forbidden_text", 7, "Draft appendix values GO, Tier 2 backlog 18, gateway inventory 158, Bend POS OK, and reserve exposure $17,300 are superseded and not treated as final."),
            fact("p07.page_order", "structure", 4, "Output preserves packet order: memo, dashboard, dependency map, store readiness, escalation matrix, procurement ledger, draft appendix."),
        ],
        extractable_text_pages=[
            overlays(["Northwest Pilot Launch Dossier", "Status: conditional go", "Packet date: 2026-08-10"], 100, 100),
            [],
            [],
            [],
            [],
            [],
            overlays(["DRAFT APPENDIX - retained for audit context only", "Do not replace final dashboard or ledger values with this draft appendix."], 100, 150),
        ],
    )


def packet_scanned_claims_appeal() -> Case:
    rng = random.Random(260703)

    def add_noise(img: Image.Image, amount: int = 900) -> Image.Image:
        out = img.convert("RGB")
        pix = out.load()
        for _ in range(amount):
            x = rng.randrange(out.width)
            y = rng.randrange(out.height)
            base = pix[x, y][0]
            delta = rng.randrange(-28, 24)
            v = max(0, min(255, base + delta))
            pix[x, y] = (v, max(0, min(255, v + rng.randrange(-3, 4))), max(0, min(255, v + rng.randrange(-2, 5))))
        return out

    def scanned_page(title: str, stamp: str | None = None, angle: float | None = None) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        img = Image.new("RGB", (PAGE_W, PAGE_H), "#f4f1ea")
        d = ImageDraw.Draw(img, "RGBA")
        d.rectangle((0, 0, PAGE_W, PAGE_H), fill=(244, 241, 234, 255))
        for y in range(0, PAGE_H, 17):
            shade = 238 + rng.randrange(-2, 3)
            d.line((0, y, PAGE_W, y), fill=(shade, shade, shade - 3, 42), width=1)
        sheet = Image.new("RGB", (1420, 1860), "#fffdf7")
        sd = ImageDraw.Draw(sheet, "RGBA")
        sd.rectangle((0, 0, 1419, 1859), outline=(178, 168, 150, 255), width=2)
        sd.text((54, 30), title, fill="#111827", font=F["h2"])
        sd.text((54, 1796), "Cedar Mutual Health | Appeal packet AP-88421 | Scan batch CMH-RC-260703", fill="#334155", font=F["tiny_bold"])
        sd.line((42, 150, 42, 1710), fill=(229, 222, 208, 150), width=2)
        if stamp:
            sd.text((1030, 70), stamp, fill=(153, 27, 27, 210), font=F["stamp"])
            sd.rectangle((1015, 58, 1354, 124), outline=(153, 27, 27, 160), width=4)
        sheet = add_noise(sheet, 1800)
        rot = sheet.rotate(angle if angle is not None else rng.uniform(-1.2, 1.1), resample=Image.Resampling.BICUBIC, expand=True, fillcolor="#f4f1ea")
        x = (PAGE_W - rot.width) // 2 + rng.randrange(-10, 12)
        y = (PAGE_H - rot.height) // 2 + rng.randrange(-10, 12)
        shadow = Image.new("RGBA", rot.size, (0, 0, 0, 0))
        alpha = Image.new("L", rot.size, 0)
        ImageDraw.Draw(alpha).rectangle((8, 8, rot.width - 8, rot.height - 8), fill=70)
        shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(11)))
        img.paste(shadow.convert("RGB"), (x + 12, y + 14), shadow)
        img.paste(rot, (x, y))
        # Most content is drawn after rotation so it remains readable while the sheet still looks scanned.
        content = ImageDraw.Draw(img, "RGBA")
        return img, content

    def sticky(d: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, fill="#fef3c7") -> None:
        x1, y1, x2, y2 = box
        d.rectangle(box, fill=fill, outline="#b45309", width=2)
        d.polygon([(x2 - 42, y1), (x2, y1), (x2, y1 + 42)], fill="#fde68a")
        draw_text(d, (x1 + 18, y1 + 18), text, F["tiny_bold"], fill="#78350f", width=max(18, int((x2 - x1) / 17)), leading=23)

    pages: list[Image.Image] = []

    p1, d = scanned_page("Claim Appeal Cover and Intake", "RECEIVED 2026-07-03", -0.7)
    draw_text(d, (180, 245), "Appeal filed by Ana Rivera for claim CMR-88421. Member ID CMH-4471-02. Date of service 2026-05-18. Original denial notice dated 2026-06-26. Packet includes a corrected provider invoice, EOB, itemized receipt, provider medical-necessity letter, reviewer worksheet, and final determination cover sheet.", F["small"], width=88, leading=31)
    draw_kv_band(d, 180, 510, [("Claim", "CMR-88421"), ("Member", "Ana Rivera"), ("DOB", "1989-11-04"), ("Control", "AP-88421"), ("Pages", "8")], [210, 260, 220, 240, 150])
    rows = [
        ["Attachment", "Packet status", "Disposition"],
        ["Member appeal form", "signed 2026-07-01", "yes"],
        ["Portal EOB screenshot", "old view", "context only"],
        ["Revised EOB detail", "scan stamp 07/03", "yes"],
        ["Provider letter", "signed by Dr. S. Koh", "yes"],
        ["Reviewer worksheet", "internal draft", "draft only"],
        ["Final determination", "appeal outcome", "final notice"],
    ]
    draw_ledger(d, 180, 690, [360, 390, 330], rows, 57)
    sticky(d, (1060, 1240, 1440, 1415), "Call Tue after 3.\nRevised EOB is current;\nportal screenshot is old.")
    d.text((210, 1500), "Blue routing note: EXPEDITE - employer letter attached", fill="#1d4ed8", font=F["italic"])
    pages.append(p1)

    p2, d = scanned_page("Member Appeal Form", None, 0.9)
    draw_text(d, (190, 320), "Section A - member and claim information", F["small_bold"], width=80)
    draw_kv_band(d, 190, 365, [("Member", "Ana Rivera"), ("Claim", "CMR-88421"), ("Plan", "Silver PPO"), ("Phone", "415-555-0184")], [300, 260, 260, 280])
    draw_section(d, 190, 525, "Appeal type and network state", w=1050)
    checkbox(d, 220, 605, "Medical necessity appeal", True, F["small"])
    checkbox(d, 220, 665, "Duplicate claim correction", False, F["small"])
    checkbox(d, 220, 725, "In-network provider", True, F["small"])
    checkbox(d, 220, 785, "Out-of-network provider", False, F["small"])
    checkbox(d, 220, 845, "Representative authorization attached", False, F["small"])
    d.text((830, 605), "Original member responsibility typed: $1,482.27", fill="#475569", font=F["small"])
    d.line((1260, 622, 1350, 622), fill="#991b1b", width=3)
    d.text((830, 670), "Blue correction note: $1,248.72", fill="#1d4ed8", font=F["italic"])
    draw_section(d, 190, 910, "Member statement", w=1050)
    draw_text(d, (210, 975), "I am appealing the denial of the 05/18/2026 orthopedic imaging and office visit because the MRI was ordered after swelling persisted after six weeks of conservative treatment. The provider corrected the invoice on 07/01/2026.", F["small"], width=86, leading=30)
    d.line((215, 1280, 650, 1280), fill="#111827", width=2)
    d.text((225, 1295), "Ana Rivera", fill="#1d4ed8", font=F["italic"])
    d.text((730, 1295), "Signed 2026-07-01", fill="#111827", font=F["small"])
    sticky(d, (1040, 1280, 1455, 1455), "Blue amount is current.\nTyped amount voided.")
    pages.append(p2)

    p3, d = scanned_page("Revised EOB Detail", "DENIED 2026-06-26", -0.4)
    draw_text(d, (175, 220), "Explanation of Benefits - revised scan. Provider: Harbor Orthopedics. Network: in-network. Appeal deadline: 2026-08-31.", F["small"], width=88, leading=30)
    rows = [
        ["Service", "Code", "Charged", "Allowed", "Plan paid", "Patient resp.", "Remark"],
        ["Office visit", "99214", "$245.00", "$164.20", "$119.56", "$44.64", "covered"],
        ["MRI knee without contrast", "73721", "$1,720.00", "$1,205.00", "$0.00", "$1,205.00", "denied M52"],
        ["Brace fitting", "L1820", "$128.00", "$86.40", "$42.32", "$44.08", "covered"],
        ["Corrected total", "", "$2,093.00", "$1,455.60", "$161.88", "$1,293.72", "before appeal"],
    ]
    draw_ledger(d, 130, 390, [270, 115, 150, 150, 150, 175, 240], rows, 62)
    draw_section(d, 160, 815, "Denial and appeal notes", w=1180)
    draw_text(d, (175, 885), "Remark M52: documentation did not support medical necessity. A later provider letter and final determination overturn only the MRI line. Office visit and brace fitting were already covered, not denied.", F["small"], width=92, leading=30)
    sticky(d, (1035, 1115, 1465, 1315), "Portal screenshot says\npatient owes $1,482.27.\nThis revised EOB says\n$1,293.72 before appeal.")
    d.text((190, 1425), "Reviewer blue-note: verify KQ-7713 authorization before finalizing", fill="#1d4ed8", font=F["italic"])
    pages.append(p3)

    p4, d = scanned_page("Receipt Strip and Pharmacy Attachment", "COPY", 1.0)
    d.text((185, 230), "Itemized receipt, rotated in original scan. Blue claim ID note appears on the receipt header.", fill="#475569", font=F["small"])
    receipt = Image.new("RGB", (470, 1130), "#fffaf0")
    rd = ImageDraw.Draw(receipt, "RGBA")
    rd.rectangle((0, 0, 469, 1129), outline="#d6c7a8", width=3)
    rd.text((36, 38), "BAYVIEW MEDICAL SUPPLY", fill="#111827", font=F["small_bold"])
    rd.text((36, 82), "Receipt 771-2048 | 2026-05-18 16:22", fill="#111827", font=F["tiny"])
    rd.text((36, 130), "claim note: CMR-88421 / Rivera", fill="#1d4ed8", font=F["italic"])
    receipt_rows = [
        ("Knee brace L1820", "$128.00"),
        ("Cold pack reusable", "$18.50"),
        ("Elastic wrap", "$7.25"),
        ("Provider copay collected", "$44.64"),
        ("Adjustment - duplicate", "-$18.50"),
    ]
    y = 230
    for item, amt in receipt_rows:
        rd.text((36, y), item, fill="#111827", font=F["tiny"])
        rd.text((335, y), amt, fill="#111827", font=F["tiny"])
        y += 58
    rd.line((35, y + 20, 430, y + 20), fill="#111827", width=2)
    rd.text((36, y + 50), "Subtotal", fill="#111827", font=F["tiny_bold"])
    rd.text((335, y + 50), "$179.89", fill="#111827", font=F["tiny_bold"])
    rd.text((36, y + 100), "Tax", fill="#111827", font=F["tiny"])
    rd.text((335, y + 100), "$0.00", fill="#111827", font=F["tiny"])
    rd.text((36, y + 150), "Total paid", fill="#111827", font=F["small_bold"])
    rd.text((320, y + 150), "$179.89", fill="#111827", font=F["small_bold"])
    for yy in range(0, 1120, 160):
        rd.line((0, yy, 12, yy + 12), fill="#d6c7a8", width=2)
        rd.line((469, yy, 457, yy + 12), fill="#d6c7a8", width=2)
    rot = receipt.rotate(-5, expand=True, fillcolor="#f4f1ea")
    p4.paste(rot, (260, 395))
    d = ImageDraw.Draw(p4, "RGBA")
    draw_note(d, (900, 480, 1450, 720), "Receipt adjustment note", "The duplicate cold-pack adjustment is negative. The itemized receipt total is $179.89 and is separate from the EOB patient responsibility.", "#92400e")
    draw_note(d, (900, 820, 1450, 1040), "Pharmacy attachment", "Pharmacy receipt RX-44918 for naproxen was included for context only; it is not part of claim CMR-88421.", "#991b1b")
    pages.append(p4)

    p5, d = scanned_page("Provider Medical Necessity Letter", None, -0.9)
    d.text((180, 285), "HARBOR ORTHOPEDICS", fill="#111827", font=F["h2"])
    d.text((180, 323), "Sports Medicine and Joint Preservation | 418 Bay Street, Suite 240 | Portland, OR 97204 | tel 503-555-0188", fill="#475569", font=F["tiny"])
    d.line((180, 365, 1435, 365), fill="#cbd5e1", width=2)
    d.text((180, 390), "Fax cover: sent 2026-07-01 18:42 to Cedar Mutual Appeals", fill="#475569", font=F["tiny_bold"])
    header_rows = [
        ["Patient", "Ana Rivera", "DOB", "1989-11-03"],
        ["Claim", "CMR-88421", "Member", "Cedar Mutual PPO"],
        ["Date of service", "2026-05-18", "Ordering physician", "S. Koh, MD"],
        ["Requested review", "MRI knee without contrast only", "Prior auth", "KQ-7713 active 2026-05-17"],
    ]
    draw_ledger(d, 180, 440, [220, 360, 220, 410], header_rows, 42)
    left = (
        "Ana Rivera was evaluated on 05/18/2026 for persistent right-knee swelling, instability, and night pain after six weeks of conservative treatment. The MRI knee without contrast, CPT 73721, was ordered to rule out meniscal tear and occult fracture. "
        "Prior authorization KQ-7713 was entered on 2026-05-17 and was active on the date of service."
    )
    right = (
        "This was not elective imaging. Diagnosis code M25.561 was used for right knee pain. The initial denial did not include the attached therapy notes or the medication-contraindication statement. Please reconsider the MRI line only; the brace fitting and office visit were already adjudicated as covered."
    )
    draw_text(d, (185, 690), left, F["small"], width=43, leading=29)
    draw_text(d, (880, 690), right, F["small"], width=43, leading=29)
    draw_section(d, 185, 1015, "Clinical timeline inset", w=1080)
    rows = [
        ["Date", "Event", "Visible note"],
        ["2026-04-03", "Initial injury", "swelling after run"],
        ["2026-04-10", "PT started", "home exercise plan"],
        ["2026-04-24", "NSAID stopped", "gastritis history"],
        ["2026-05-10", "Persistent swelling", "no full extension"],
        ["2026-05-17", "Auth KQ-7713", "MRI authorized"],
        ["2026-05-18", "MRI CPT 73721", "performed"],
    ]
    draw_ledger(d, 205, 1085, [170, 270, 420], rows, 48)
    draw_section(d, 185, 1475, "Enclosures transmitted")
    enc_rows = [
        ["Attachment", "Pages", "Purpose"],
        ["PT notes 04/10-05/10", "6", "failed conservative therapy"],
        ["Medication note", "1", "NSAID contraindication"],
        ["Authorization printout KQ-7713", "1", "active before service"],
    ]
    draw_ledger(d, 205, 1545, [350, 150, 420], enc_rows, 44)
    d.line((970, 1720, 1390, 1720), fill="#111827", width=2)
    d.text((995, 1735), "S. Koh, MD", fill="#1d4ed8", font=F["italic"])
    sticky(d, (990, 1515, 1450, 1668), "Auth KQ-7713\nis the deciding fact.\nOverturn MRI only.")
    pages.append(p5)

    p6, d = scanned_page("Internal Reviewer Worksheet", "INTERNAL DRAFT", 0.5)
    draw_text(d, (180, 285), "Reviewer: N. Bell | Queue: Medical necessity | Drafted 2026-07-05. Internal worksheet only; final appeal outcome is issued separately.", F["small"], width=88, leading=30)
    checkbox(d, 210, 360, "Provider letter present", True, F["small"])
    checkbox(d, 210, 420, "Authorization KQ-7713 verified", True, F["small"])
    checkbox(d, 210, 480, "Therapy notes missing", False, F["small"])
    checkbox(d, 210, 540, "MRI line eligible for overturn", True, F["small"])
    checkbox(d, 210, 600, "Brace line requires rework", False, F["small"])
    d.text((840, 365), "Draft recommendation: overturn line 2 only", fill="#111827", font=F["small_bold"])
    d.text((840, 425), "Initial patient responsibility after overturn: $88.72", fill="#475569", font=F["small"])
    d.line((1170, 443, 1432, 443), fill="#991b1b", width=3)
    d.text((840, 485), "Corrected final member balance: $48.32", fill="#1d4ed8", font=F["italic"])
    rows = [
        ["Line", "Reviewer action", "Reason"],
        ["99214", "leave as paid", "already covered"],
        ["73721", "overturn denial", "auth KQ-7713 verified"],
        ["L1820", "leave as paid", "covered DME"],
        ["Cold pack", "exclude", "receipt adjustment / context only"],
    ]
    draw_ledger(d, 210, 750, [130, 300, 520], rows, 58)
    draw_note(d, (210, 1220, 1450, 1425), "Draft worksheet note", "The worksheet supports the final result but does not itself issue payment. The final determination page issues the outcome and payment amount.", "#991b1b")
    pages.append(p6)

    p7, d = scanned_page("Copies, Control Labels, and Denial Code Legend", None, -0.3)
    draw_text(d, (180, 225), "Copied member-card and scan-label inserts received with mixed orientation. Card and label copies are included for ID verification; barcode data is limited to the printed label text.", F["small"], fill="#475569", width=80, leading=28)
    card = Image.new("RGB", (560, 310), "#f8fafc")
    cd = ImageDraw.Draw(card, "RGBA")
    cd.rectangle((0, 0, 559, 309), outline="#475569", width=4)
    cd.text((28, 28), "CEDAR MUTUAL", fill="#111827", font=F["small_bold"])
    cd.text((28, 86), "Member: Ana Rivera", fill="#111827", font=F["small"])
    cd.text((28, 134), "ID: CMH-4471-02", fill="#111827", font=F["small"])
    cd.text((28, 182), "Plan: Silver PPO", fill="#111827", font=F["small"])
    cd.text((28, 232), "Group: LARK-220", fill="#111827", font=F["small"])
    p7.paste(card.rotate(3, expand=True, fillcolor="#f4f1ea"), (235, 350))
    d = ImageDraw.Draw(p7, "RGBA")
    d.rectangle((940, 350, 1420, 510), fill="#ffffff", outline="#111827", width=2)
    barcode_modules = [2, 1, 3, 1, 1, 2, 4, 1, 2, 2, 1, 3, 1, 1, 4, 2, 1, 2, 3, 1, 1, 2, 2, 4, 1, 1, 3, 2, 1, 4]
    x = 972
    for i, width in enumerate(barcode_modules):
        bar_w = width * 3
        if i % 2 == 0:
            top = 378 + (i % 5)
            bottom = 473 - (i % 4)
            d.rectangle((x, top, x + bar_w, bottom), fill="#111827")
        x += bar_w + 3
    d.rectangle((965, 372, 1292, 478), outline="#e5e7eb", width=1)
    d.text((970, 520), "Barcode label: AP-88421-07 / scan 0034", fill="#111827", font=F["tiny_bold"])
    rows = [
        ["Code", "Meaning"],
        ["M52", "medical necessity documentation missing"],
        ["P14", "provider correction received"],
        ["R08", "receipt not payable under medical benefit"],
    ]
    draw_ledger(d, 235, 850, [160, 650], rows, 58)
    draw_note(d, (930, 850, 1430, 1085), "Legend note", "M52 applies to the MRI line. R08 applies only to the pharmacy/receipt attachment.", "#1d4ed8")
    draw_section(d, 220, 1225, "Scan batch index", w=1120)
    batch_rows = [
        ["Batch ref", "Page", "Image state", "Operator note"],
        ["AP-88421-07A", "member card", "copied, rotated 3 deg", "ID verification only"],
        ["AP-88421-07B", "barcode label", "label text readable", "no hidden barcode payload used"],
        ["AP-88421-07C", "code legend", "clean photocopy", "attach to reviewer worksheet"],
        ["AP-88421-07D", "receipt insert", "rotated receipt", "context only for R08"],
    ]
    draw_ledger(d, 235, 1305, [230, 220, 300, 430], batch_rows, 58)
    draw_note(d, (235, 1760, 1430, 1915), "Copy quality note", "Member-card copy is sufficient for ID match only. Claims review uses printed label text AP-88421-07 / scan 0034 and does not infer any extra barcode payload.", "#334155")
    pages.append(p7)

    p8, d = scanned_page("Final Appeal Determination", "PARTIAL OVERTURN", 0.2)
    draw_text(d, (180, 230), "Final determination for appeal AP-88421 / claim CMR-88421. Decision date 2026-07-08. This page controls the appeal outcome.", F["small"], width=88, leading=30)
    rows = [
        ["Line", "Service", "Decision", "Plan paid after appeal", "Member balance"],
        ["1", "Office visit 99214", "unchanged paid", "$119.56", "$44.64"],
        ["2", "MRI knee 73721", "overturned", "$1,205.00", "$0.00"],
        ["3", "Brace fitting L1820", "unchanged paid", "$42.32", "$3.68"],
        ["", "Final member balance", "", "", "$48.32"],
    ]
    draw_ledger(d, 150, 395, [100, 330, 250, 260, 210], rows, 64)
    draw_section(d, 170, 850, "Outcome text", w=1120)
    draw_text(d, (185, 920), "The appeal is partially overturned. The MRI knee without contrast, CPT 73721, is payable because authorization KQ-7713 was active and the provider letter supports medical necessity. Office visit 99214 and brace fitting L1820 remain as previously paid. Pharmacy and receipt context attachments are not payable under this medical claim.", F["small"], width=87, leading=30)
    checkbox(d, 205, 1190, "Payment released", True, F["small"])
    checkbox(d, 205, 1250, "Supervisor review required before payment", False, F["small"])
    d.line((205, 1390, 640, 1390), fill="#111827", width=2)
    d.text((220, 1405), "N. Bell 2026-07-08", fill="#1d4ed8", font=F["italic"])
    d.text((805, 1362), "Supervisor signature", fill="#111827", font=F["tiny_bold"])
    d.line((1010, 1390, 1340, 1390), fill="#111827", width=2)
    draw_note(d, (200, 1545, 1460, 1695), "Final balance note", "Pre-appeal patient responsibility $1,293.72 and voided $1,482.27 are historical amounts. Final member balance is $48.32.", "#991b1b")
    pages.append(p8)

    gold = """# Cedar Mutual Claim Appeal Packet AP-88421

Claim CMR-88421 for Ana Rivera, member ID CMH-4471-02, DOB 1989-11-04. Date of service 2026-05-18. Original denial notice dated 2026-06-26. Appeal packet received 2026-07-03. The packet has 8 pages.

## Cover and Intake

Blue routing note: EXPEDITE - employer letter attached. Sticky note: call Tue after 3; use revised EOB, not portal screenshot.

| Attachment | Packet status | Disposition |
| --- | --- | --- |
| Member appeal form | signed 2026-07-01 | yes |
| Portal EOB screenshot | old view | context only |
| Revised EOB detail | scan stamp 07/03 | yes |
| Provider letter | signed by Dr. S. Koh | yes |
| Reviewer worksheet | internal draft | draft only |
| Final determination | appeal outcome | final notice |

## Member Appeal Form

Member: Ana Rivera. Claim: CMR-88421. Plan: Silver PPO. Phone: 415-555-0184.

Checkbox states: medical necessity appeal checked; duplicate claim correction unchecked; in-network provider checked; out-of-network provider unchecked; representative authorization attached unchecked.

The typed original member responsibility $1,482.27 is crossed out. The blue correction note says $1,248.72. Member statement says the appeal concerns the 05/18/2026 orthopedic imaging and office visit because MRI was ordered after swelling persisted after six weeks of conservative treatment. Provider corrected the invoice on 2026-07-01. Ana Rivera signed on 2026-07-01.

## Revised EOB Detail

Provider: Harbor Orthopedics. Network: in-network. Appeal deadline: 2026-08-31. Stamp: DENIED 2026-06-26.

| Service | Code | Charged | Allowed | Plan paid | Patient responsibility | Remark |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Office visit | 99214 | $245.00 | $164.20 | $119.56 | $44.64 | covered |
| MRI knee without contrast | 73721 | $1,720.00 | $1,205.00 | $0.00 | $1,205.00 | denied M52 |
| Brace fitting | L1820 | $128.00 | $86.40 | $42.32 | $44.08 | covered |
| Corrected total before appeal | | $2,093.00 | $1,455.60 | $161.88 | $1,293.72 | before appeal |

Remark M52 means documentation did not support medical necessity. A later provider letter and the final determination overturn only the MRI line. Office visit and brace fitting were already covered, not denied. A sticky note says the portal screenshot showing patient owes $1,482.27 is old; the revised EOB says $1,293.72 before appeal.

## Receipt Strip and Pharmacy Attachment

Itemized receipt from Bayview Medical Supply. Receipt 771-2048, dated 2026-05-18 16:22. Blue claim note: CMR-88421 / Rivera.

| Item | Amount |
| --- | ---: |
| Knee brace L1820 | $128.00 |
| Cold pack reusable | $18.50 |
| Elastic wrap | $7.25 |
| Provider copay collected | $44.64 |
| Adjustment - duplicate | -$18.50 |
| Subtotal | $179.89 |
| Tax | $0.00 |
| Total paid | $179.89 |

The duplicate cold-pack adjustment is negative. The receipt total is separate from the EOB patient responsibility. Pharmacy receipt RX-44918 for naproxen is included for context only and is not part of claim CMR-88421.

## Provider Medical Necessity Letter

Harbor Orthopedics Sports Medicine and Joint Preservation letter, dated 2026-07-01. Fax header sent 2026-07-01 18:42 to Cedar Mutual Appeals. Patient block: Ana Rivera, DOB 1989-11-03, claim CMR-88421, Cedar Mutual PPO, date of service 2026-05-18, ordering physician S. Koh, MD, requested review MRI knee without contrast only, prior authorization KQ-7713 active 2026-05-17.

The letter says Ana Rivera was evaluated on 2026-05-18 for persistent right-knee swelling, instability, and night pain after six weeks of conservative treatment. MRI knee without contrast, CPT 73721, was ordered to rule out meniscal tear and occult fracture. Prior authorization KQ-7713 was entered on 2026-05-17 and was active on the date of service. The imaging was not elective. Diagnosis code M25.561 was used for right knee pain. The provider asks to reconsider the MRI line only; the brace fitting and office visit were already covered.

Clinical timeline: 2026-04-03 initial injury; 2026-04-10 PT started; 2026-04-24 NSAID stopped due to gastritis history; 2026-05-10 persistent swelling with no full extension; 2026-05-17 authorization KQ-7713; 2026-05-18 MRI CPT 73721 performed.

Enclosures transmitted: PT notes 04/10-05/10, 6 pages, failed conservative therapy; medication note, 1 page, NSAID contraindication; authorization printout KQ-7713, 1 page, active before service. Sticky note: Auth KQ-7713 is the deciding fact; overturn MRI only.

## Internal Reviewer Worksheet

Reviewer N. Bell. Queue: medical necessity. Drafted 2026-07-05. This is an internal draft and not the final appeal outcome.

Checkbox states: provider letter present checked; authorization KQ-7713 verified checked; therapy notes missing unchecked; MRI line eligible for overturn checked; brace line requires rework unchecked.

Draft recommendation: overturn line 2 only. The worksheet shows initial patient responsibility after overturn $88.72 crossed out and corrected final member balance $48.32.

| Line | Reviewer action | Reason |
| --- | --- | --- |
| 99214 | leave as paid | already covered |
| 73721 | overturn denial | auth KQ-7713 verified |
| L1820 | leave as paid | covered DME |
| Cold pack | exclude | receipt adjustment / context only |

## Copies, Control Labels, and Denial Code Legend

Copied member card: Cedar Mutual; member Ana Rivera; ID CMH-4471-02; plan Silver PPO; group LARK-220. Barcode label text: AP-88421-07 / scan 0034. No additional barcode text is visible.

| Code | Meaning |
| --- | --- |
| M52 | medical necessity documentation missing |
| P14 | provider correction received |
| R08 | receipt not payable under medical benefit |

M52 applies to the MRI line. R08 applies only to the pharmacy/receipt attachment.

Scan batch index:

| Batch ref | Page | Image state | Operator note |
| --- | --- | --- | --- |
| AP-88421-07A | member card | copied, rotated 3 deg | ID verification only |
| AP-88421-07B | barcode label | label text readable | no hidden barcode payload used |
| AP-88421-07C | code legend | clean photocopy | attach to reviewer worksheet |
| AP-88421-07D | receipt insert | rotated receipt | context only for R08 |

Copy quality note: member-card copy is sufficient for ID match only. Claims review uses printed label text AP-88421-07 / scan 0034 and does not infer any extra barcode payload.

## Final Appeal Determination

Final determination for appeal AP-88421 / claim CMR-88421. Decision date 2026-07-08. Stamp: PARTIAL OVERTURN. This page controls the appeal outcome.

| Line | Service | Decision | Plan paid after appeal | Member balance |
| --- | --- | --- | ---: | ---: |
| 1 | Office visit 99214 | unchanged paid | $119.56 | $44.64 |
| 2 | MRI knee 73721 | overturned | $1,205.00 | $0.00 |
| 3 | Brace fitting L1820 | unchanged paid | $42.32 | $3.68 |
| | Final member balance | | | $48.32 |

Outcome: the appeal is partially overturned. MRI knee without contrast CPT 73721 is payable because authorization KQ-7713 was active and the provider letter supports medical necessity. Office visit 99214 and brace fitting L1820 remain as previously paid. Pharmacy and receipt context attachments are not payable under this medical claim.

Checkbox states: payment released checked; supervisor review required before payment unchecked. N. Bell signed 2026-07-08. Supervisor signature is blank. Pre-appeal patient responsibility $1,293.72 and crossed-out $1,482.27 are historical amounts; final member balance is $48.32.
"""

    facts = [
        fact("p07.identity", "text", 7, "Appeal AP-88421 / claim CMR-88421 for Ana Rivera, member ID CMH-4471-02, DOB 1989-11-04, date of service 2026-05-18, denial notice 2026-06-26, received 2026-07-03.", modality="text", severity="critical"),
        fact("p07.source.index", "source_state", 9, "Attachment index preserves form signed 2026-07-01, portal EOB screenshot old/context only, revised EOB scan stamp 07/03/use yes, provider letter signed by Dr. S. Koh, reviewer worksheet internal draft/not final, final determination controls outcome.", modality="source-precedence", severity="critical"),
        fact("p07.form.checkboxes", "form_state", 9, "Member form states: medical necessity appeal checked, duplicate claim unchecked, in-network checked, out-of-network unchecked, representative authorization unchecked.", modality="form", severity="critical"),
        fact("p07.form.correction", "source_state", 9, "Typed $1,482.27 is crossed out; blue correction note says $1,248.72; Ana Rivera signed on 2026-07-01.", modality="physical", severity="critical"),
        fact("p07.eob.table", "table_cell", 14, "Revised EOB preserves office visit 99214 $245/$164.20/$119.56/$44.64 covered; MRI 73721 $1,720/$1,205/$0/$1,205 denied M52; brace L1820 $128/$86.40/$42.32/$44.08 covered; corrected total $2,093/$1,455.60/$161.88/$1,293.72 before appeal.", modality="table", severity="critical"),
        fact("p07.eob.source", "source_state", 9, "Portal screenshot/patient owes $1,482.27 is old; revised EOB $1,293.72 is before appeal; final determination later controls final balance.", modality="source-precedence", severity="critical"),
        fact("p07.receipt", "visual_relation", 10, "Rotated receipt preserves Bayview Medical Supply, receipt 771-2048, 2026-05-18 16:22, blue claim note CMR-88421/Rivera, line items including negative duplicate adjustment -$18.50, subtotal/tax/total paid $179.89/$0/$179.89.", modality="physical", severity="critical"),
        fact("p07.pharmacy.context", "source_state", 5, "Pharmacy receipt RX-44918 for naproxen is context only and not part of claim CMR-88421.", modality="source-precedence", severity="major"),
        fact("p07.provider.letter", "text", 11, "Provider letter from Harbor Orthopedics signed by Dr. S. Koh dated 2026-07-01 says MRI CPT 73721 was medically necessary, not elective, diagnosis M25.561, prior authorization KQ-7713 entered 2026-05-17 and active on date of service, reconsider MRI only, with enclosures for PT notes, medication note/NSAID contraindication, and authorization printout.", modality="text", severity="critical"),
        fact("p07.clinical.timeline", "table_cell", 7, "Clinical timeline preserves 2026-04-03 injury, 2026-04-10 PT started, 2026-04-24 NSAID stopped/gastritis history, 2026-05-10 persistent swelling/no full extension, 2026-05-17 auth KQ-7713, 2026-05-18 MRI CPT 73721.", modality="table", severity="major"),
        fact("p07.worksheet.checkboxes", "form_state", 9, "Reviewer worksheet states provider letter present checked, KQ-7713 verified checked, therapy notes missing unchecked, MRI eligible for overturn checked, brace requires rework unchecked.", modality="form", severity="critical"),
        fact("p07.worksheet.correction", "source_state", 8, "Worksheet is internal draft; $88.72 is crossed out and corrected final member balance shown as $48.32; it supports but does not issue final payment.", modality="physical", severity="critical"),
        fact("p07.copied.inserts", "visual_relation", 9, "Copied member card preserves Cedar Mutual, Ana Rivera, ID CMH-4471-02, Silver PPO, group LARK-220; barcode label visible text is AP-88421-07 / scan 0034 and no additional barcode text is visible; scan batch index preserves AP-88421-07A/B/C/D image states and operator notes including no hidden barcode payload used.", modality="physical", severity="major"),
        fact("p07.denial.legend", "table_cell", 6, "Denial code legend preserves M52 medical necessity documentation missing, P14 provider correction received, R08 receipt not payable under medical benefit; M52 applies to MRI and R08 only to the receipt/pharmacy attachment.", modality="table", severity="major"),
        fact("p07.final.determination", "source_state", 14, "Final determination dated 2026-07-08 is PARTIAL OVERTURN and controls outcome: line 1 office visit unchanged paid $119.56/$44.64, line 2 MRI 73721 overturned $1,205.00/$0.00, line 3 brace unchanged paid $42.32/$3.68, final member balance $48.32.", modality="source-precedence", severity="critical"),
        fact("p07.final.states", "form_state", 8, "Final page states payment released checked, supervisor review required before payment unchecked, N. Bell signed 2026-07-08, supervisor signature blank.", modality="form", severity="critical"),
        fact("p07.physical", "visual_description", 6, "Output preserves physical document features where relevant: received/denied/copy/partial overturn stamps, sticky notes, blue routing/correction notes, rotated receipt, copied card/barcode label, and blank signature.", modality="physical", severity="major"),
        fact("p07.page.order", "structure", 4, "Output preserves page order: cover/intake, appeal form, revised EOB, receipt/pharmacy attachment, provider letter, reviewer worksheet, copied inserts/code legend, final determination.", modality="structure", severity="major"),
    ]

    return Case(
        "P07-scanned-claims-appeal",
        "Scanned Claims Appeal Packet",
        "claims-physical",
        ["multi-page", "scanned", "forms", "handwriting", "stamps", "receipts", "source-precedence", "medical-claims"],
        "Stress realistic physical-document reconstruction with skew, stamps, sticky notes, handwritten corrections, rotated receipt inserts, copied cards, checkbox states, and conflicting source states.",
        "Eight-page scanned claims appeal packet rendered as raster pages with form fields, rotated inserts, stamps, sticky notes, and a final controlling determination.",
        ["cover intake", "appeal form", "revised EOB", "receipt strip", "provider letter", "reviewer worksheet", "copied inserts", "final determination"],
        ["Preserve physical annotations and blue correction notes.", "Bind financial/service table cells correctly.", "Use final determination over old screenshot, draft worksheet, and crossed-out amounts."],
        gold,
        [
            near_check("p07-final-balance", "source_state", ["PARTIAL OVERTURN", "73721", "$1,205.00", "$48.32"], 7, 900),
            near_check("p07-form-correction", "physical", ["$1,482.27", "voided", "$1,248.72"], 6, 700),
            near_check("p07-eob-mri", "table_cell", ["73721", "$1,720.00", "$1,205.00", "denied M52"], 6, 800),
            near_check("p07-corrected-total", "table_cell", ["Corrected total", "$2,093.00", "$1,455.60", "$161.88", "$1,293.72"], 8, 900),
        ],
        pages,
        facts=facts,
    )


def packet_hospital_discharge() -> Case:
    pages: list[Image.Image] = []

    p1 = base_page("Lakeview Medical Center - Discharge Packet")
    d = ImageDraw.Draw(p1)
    d.text((100, 150), "Patient: Ana Rivera | MRN: LMC-482913 | DOB: 1979-04-18 | Packet finalized: 2026-08-14 14:40", fill="#475569", font=F["small"])
    d.text((100, 225), "Discharge summary", fill="#111827", font=F["h1"])
    left = (
        "Admission date: 2026-08-10. Discharge date: 2026-08-14. Primary diagnosis: community-acquired pneumonia with acute kidney injury, improving. "
        "Secondary diagnoses: type 2 diabetes, hypertension, and medication-associated hyperkalemia. Allergy: penicillin - rash. "
        "Pending test: blood culture final read expected 2026-08-16."
    )
    right = (
        "Condition at discharge: stable on room air. Home health nurse visit is authorized for 2026-08-15. "
        "Medication reconciliation on page 3 controls over the ED medication list and any draft discharge instruction footer. "
        "Renal dosing should be reviewed again after the outpatient BMP."
    )
    draw_text(d, (100, 300), left, F["small"], width=53, leading=31)
    draw_text(d, (910, 300), right, F["small"], width=50, leading=31)
    d.rounded_rectangle((100, 690, 1540, 910), radius=14, fill="#fff7ed", outline="#c2410c", width=4)
    draw_text(d, (130, 725), "Source-state notice: FINAL medication reconciliation signed 14:40 controls. ED medication list and draft footer are historical. Do not restart lisinopril until follow-up BMP is reviewed.", F["small"], fill="#9a3412", width=100, leading=31)
    rows = [
        ["Follow-up need", "Due", "Owner", "Status", "Instruction"],
        ["BMP lab draw", "2026-08-17 08:00", "Home health", "Scheduled", "check K and creatinine"],
        ["Primary care", "2026-08-19 10:30", "Dr. Shah", "Scheduled", "review antibiotics"],
        ["Cardiology", "2026-08-25 09:00", "Dr. Kim", "Scheduled", "11 days after discharge"],
        ["Blood culture final", "2026-08-16", "LMC lab", "Pending", "call if positive"],
    ]
    draw_table(d, 90, 1010, [280, 250, 220, 200, 430], rows, 72)
    d.text((100, 1500), "Footer draft 08:15 said cardiology in 2 weeks; scheduled referral sheet controls with 2026-08-25.", fill="#7f1d1d", font=F["small"])
    pages.append(p1)

    p2 = base_page("Lab Trends - CBC / CMP / Coagulation")
    d = ImageDraw.Draw(p2)
    d.text((100, 150), "Flags and units are part of the record. Hemolyzed/canceled specimens are excluded from trend interpretation.", fill="#7f1d1d", font=F["small"])
    rows = [
        ["Analyte", "Ref range", "Unit", "08-10 06:20", "08-12 05:50", "08-14 06:05"],
        ["WBC", "4.0-11.0", "K/uL", "14.2 H", "9.8", "7.6"],
        ["Hemoglobin", "12.0-16.0", "g/dL", "10.8 L", "10.1 L", "10.4 L"],
        ["Platelets", "150-400", "K/uL", "412 H", "390", "366"],
        ["Creatinine", "0.6-1.2", "mg/dL", "1.9 H", "1.5 H", "1.2"],
        ["Potassium", "3.5-5.1", "mmol/L", "5.8 H", "hemolyzed", "4.7"],
        ["Glucose", "70-110", "mg/dL", "188 H", "142 H", "126 H"],
        ["INR", "0.9-1.1", "ratio", "1.0", "canceled", "1.1"],
    ]
    draw_table(d, 55, 245, [190, 200, 140, 230, 230, 230], rows, 64)
    d.rounded_rectangle((1015, 865, 1535, 1280), radius=14, fill="#f8fafc", outline="#334155", width=3)
    d.text((1045, 900), "Creatinine sparkline", fill="#111827", font=F["h2"])
    pts = [(1080, 1030), (1220, 1110), (1360, 1190)]
    labels = ["1.9", "1.5", "1.2"]
    d.line((1070, 1210, 1420, 1210), fill="#111827", width=3)
    d.line((1070, 1210, 1070, 980), fill="#111827", width=3)
    for a, b in zip(pts, pts[1:]):
        d.line((*a, *b), fill="#2563eb", width=5)
    for p, label in zip(pts, labels):
        d.ellipse((p[0] - 7, p[1] - 7, p[0] + 7, p[1] + 7), fill="#2563eb")
        d.text((p[0] + 12, p[1] - 18), label, fill="#111827", font=F["tiny"])
    d.rounded_rectangle((80, 870, 930, 1280), radius=14, fill="#fff7ed", outline="#c2410c", width=3)
    draw_text(d, (110, 905), "Footnotes: 08-12 potassium is hemolyzed and excluded. 08-12 INR was canceled and should not be carried forward. Hemoglobin remains low at discharge.", F["small"], fill="#9a3412", width=58, leading=30)
    draw_section(d, 90, 1390, "Specimen handling audit", w=1380)
    specimen_rows = [
        ["Specimen", "Collection", "Result state", "Action"],
        ["BMP tube A", "08-10 06:20", "accepted", "trend baseline"],
        ["BMP tube B", "08-12 05:50", "K hemolyzed", "exclude potassium only"],
        ["Coag tube C", "08-12 05:50", "INR canceled", "do not carry forward"],
        ["BMP tube D", "08-14 06:05", "accepted", "discharge value"],
    ]
    draw_ledger(d, 110, 1465, [230, 230, 300, 430], specimen_rows, 58)
    draw_note(d, (110, 1845, 1490, 2005), "Renal dosing comment", "Creatinine improved to 1.2 before discharge, but lisinopril remains held until the outpatient BMP is reviewed. Potassium 4.7 is current; hemolyzed 08-12 potassium is not used.", "#1d4ed8")
    pages.append(p2)

    p3 = base_page("Final Medication Reconciliation")
    d = ImageDraw.Draw(p3)
    d.text((100, 150), "Signed by pharmacist M. Patel at 2026-08-14 14:40. This page controls over ED medication list.", fill="#7f1d1d", font=F["small"])
    rows = [
        ["Medication", "Home dose", "Discharge dose", "Route", "Frequency", "Action", "Note"],
        ["Metformin", "500 mg", "500 mg", "PO", "twice daily", "continue", "take with meals"],
        ["Lisinopril", "20 mg", "HOLD", "PO", "do not restart", "stop", "restart only after BMP"],
        ["Azithromycin", "-", "250 mg", "PO", "daily x3 days", "new", "finish course"],
        ["Insulin glargine", "18 units", "14 units", "SQ", "nightly", "change", "dose reduced"],
        ["Ibuprofen", "400 mg", "STOP", "PO", "none", "stop", "avoid with kidney injury"],
    ]
    draw_table(d, 40, 245, [190, 160, 210, 115, 190, 145, 330], rows, 68)
    checkbox(d, 95, 780, "Continue: Metformin", True, F["small"])
    checkbox(d, 95, 835, "Change: Insulin glargine", True, F["small"])
    checkbox(d, 95, 890, "Stop: Lisinopril", True, F["small"])
    checkbox(d, 95, 945, "New: Azithromycin", True, F["small"])
    checkbox(d, 95, 1000, "Restart lisinopril today", False, F["small"])
    d.rounded_rectangle((830, 805, 1530, 1055), radius=14, fill="#fee2e2", outline="#991b1b", width=4)
    draw_text(d, (860, 865), "Pharmacist note: ED list showed lisinopril 20 mg daily and ibuprofen PRN, but both are inactive at discharge. Final discharge medication list is the signed reconciliation above.", F["small"], fill="#991b1b", width=48, leading=30)
    d.text((1038, 820), "20 mg daily", fill="#991b1b", font=F["tiny"])
    d.line((1035, 852, 1165, 852), fill="#991b1b", width=4)
    pages.append(p3)

    p4 = base_page("Nursing MAR and Vitals Timeline")
    d = ImageDraw.Draw(p4)
    d.text((100, 150), "Grid states: A=administered, H=held, R=refused, M=missed. Held doses are not administered.", fill="#7f1d1d", font=F["small"])
    rows = [
        ["Medication", "06:00", "12:00", "18:00", "22:00", "Comment"],
        ["Azithromycin", "", "A", "", "", "given after lunch"],
        ["Insulin lispro", "A", "H", "A", "", "12:00 held: glucose 88"],
        ["Acetaminophen", "", "R", "", "A", "refused noon dose"],
        ["Lisinopril", "H", "H", "H", "H", "held all day"],
        ["Metformin", "A", "", "A", "", "continued"],
    ]
    draw_table(d, 70, 245, [230, 150, 150, 150, 150, 430], rows, 70)
    d.rounded_rectangle((90, 800, 810, 1280), radius=14, fill="#f8fafc", outline="#334155", width=3)
    d.text((120, 835), "Oxygen saturation", fill="#111827", font=F["h2"])
    pts = [(145, 1170), (270, 1115), (395, 1050), (520, 1008), (645, 985)]
    vals = ["91", "93", "95", "96", "96"]
    d.line((130, 1190, 720, 1190), fill="#111827", width=3)
    d.line((130, 1190, 130, 930), fill="#111827", width=3)
    d.line((130, 1075, 720, 1075), fill="#dc2626", width=3)
    d.text((585, 1038), "threshold 94", fill="#dc2626", font=F["tiny"])
    for a, b in zip(pts, pts[1:]):
        d.line((*a, *b), fill="#2563eb", width=5)
    for p, val in zip(pts, vals):
        d.ellipse((p[0] - 7, p[1] - 7, p[0] + 7, p[1] + 7), fill="#2563eb")
        d.text((p[0] - 12, p[1] - 33), val, fill="#111827", font=F["tiny"])
    d.rounded_rectangle((905, 800, 1535, 1280), radius=14, fill="#f8fafc", outline="#334155", width=3)
    d.text((935, 835), "Blood pressure", fill="#111827", font=F["h2"])
    bp_rows = [["Time", "BP", "Pulse"], ["06:00", "132/84", "88"], ["12:00", "118/72", "82"], ["18:00", "126/78", "80"], ["22:00", "124/76", "78"]]
    draw_table(d, 935, 895, [150, 190, 130], bp_rows, 56)
    draw_section(d, 90, 1390, "Nursing event log", w=1380)
    event_rows = [
        ["Time", "Event", "Linked field"],
        ["05:55", "room-air trial started", "oxygen trend"],
        ["12:08", "lispro held after glucose 88; snack given", "MAR H at 12:00"],
        ["18:20", "ambulated 150 ft with cane", "discharge mobility"],
        ["22:10", "SpO2 96 on room air before sleep", "final oxygen point"],
    ]
    draw_ledger(d, 110, 1465, [130, 470, 260], event_rows, 58)
    io_rows = [
        ["24h intake/output", "Value"],
        ["Oral intake", "1,320 mL"],
        ["Urine output", "1,650 mL"],
        ["Net", "-330 mL"],
        ["Fever after noon", "none documented"],
    ]
    draw_ledger(d, 1095, 1465, [260, 160], io_rows, 54)
    pages.append(p4)

    p5 = base_page("Referral Sheet and Discharge Footer Addendum")
    d = ImageDraw.Draw(p5)
    d.text((100, 150), "Referral sheet signed 2026-08-14 14:46. These scheduled dates control over draft footer text.", fill="#7f1d1d", font=F["small"])
    rows = [
        ["Appointment", "Date/time", "Location", "Status", "Instruction"],
        ["Home health nurse", "2026-08-15 09:00", "home", "authorized", "med check and vitals"],
        ["BMP lab draw", "2026-08-17 08:00", "LMC Lab", "scheduled", "bring lab slip"],
        ["Primary care", "2026-08-19 10:30", "Clinic A", "scheduled", "review antibiotics"],
        ["Cardiology", "2026-08-25 09:00", "Heart Center", "scheduled", "11 days after discharge"],
    ]
    draw_table(d, 70, 245, [260, 250, 230, 190, 360], rows, 72)
    d.rounded_rectangle((95, 700, 780, 985), radius=14, fill="#ecfeff", outline="#0f766e", width=3)
    draw_text(d, (125, 735), "Authorization stamp: home health visit approved once for 2026-08-15. Additional visits require PCP order.", F["small"], fill="#0f766e", width=45, leading=30)
    d.rounded_rectangle((880, 700, 1530, 985), radius=14, fill="#f8fafc", outline="#334155", width=3)
    draw_text(d, (910, 735), "Draft footer from 08:15: cardiology in 2 weeks; resume home blood pressure pill. Superseded by final medication reconciliation and signed referral schedule.", F["small"], width=44, leading=30)
    draw_section(d, 95, 1110, "Care coordination contact log", w=1380)
    contact_rows = [
        ["Time", "Contact", "Result", "Initials"],
        ["14:50", "Home health intake", "accepted one RN visit, case HH-60814", "CN"],
        ["14:57", "LMC Lab", "BMP order released, fasting not required", "MP"],
        ["15:03", "Clinic A", "PCP visit confirmed, bring med list", "CN"],
        ["15:18", "Heart Center", "cardiology packet faxed, receipt OK", "JW"],
    ]
    draw_ledger(d, 115, 1185, [140, 310, 570, 110], contact_rows, 58)
    draw_section(d, 95, 1515, "Home setup checklist", w=1380)
    checkbox(d, 130, 1588, "Thermometer available at home", True, F["small"])
    checkbox(d, 130, 1648, "Working glucometer confirmed", True, F["small"])
    checkbox(d, 130, 1708, "Transportation arranged for BMP lab draw", True, F["small"])
    checkbox(d, 130, 1768, "Oxygen concentrator ordered", False, F["small"])
    draw_note(d, (830, 1570, 1510, 1815), "Care-team note", "Luis Rivera will drive to the 08/17 BMP draw. If fever reaches 101.5 F after 24 hours on antibiotics, call Clinic A before using urgent care.", "#1d4ed8")
    pages.append(p5)

    p6 = base_page("Prednisone Taper and Conditional Dosing Calendar")
    d = ImageDraw.Draw(p6)
    d.text((100, 150), "Final discharge-order attachment. Calendar controls taper instructions; no additional dosing guidance was issued.", fill="#475569", font=F["small"])
    rows = [
        ["Date range", "Medication / condition", "Dose", "Route", "Frequency", "Instruction"],
        ["2026-08-15 to 2026-08-17", "Prednisone", "30 mg", "PO", "daily with breakfast", "new taper step 1"],
        ["2026-08-18 to 2026-08-20", "Prednisone", "20 mg", "PO", "daily with breakfast", "step 2"],
        ["2026-08-21 to 2026-08-23", "Prednisone", "10 mg", "PO", "daily with breakfast", "step 3"],
        ["2026-08-24", "Prednisone", "stop", "", "", "last planned dose was 2026-08-23"],
        ["Glucose 70-149", "Insulin lispro", "0 units", "SQ", "before meals", "sliding scale"],
        ["Glucose 150-199", "Insulin lispro", "2 units", "SQ", "before meals", "sliding scale"],
        ["Glucose 200-249", "Insulin lispro", "4 units", "SQ", "before meals", "sliding scale"],
        ["Glucose >=250", "Insulin lispro", "call clinic", "", "", "do not self-increase beyond scale"],
    ]
    draw_table(d, 45, 250, [230, 250, 130, 105, 235, 360], rows, 70)
    draw_note(d, (90, 940, 760, 1185), "Conditional source note", "Sliding-scale page is final only for insulin lispro correction doses. It does not change glargine 14 units nightly.", "#0f766e")
    draw_note(d, (845, 940, 1515, 1185), "Follow-up dependency", "BMP on 2026-08-17 must be reviewed before any lisinopril restart. This calendar does not restart lisinopril.", "#991b1b")
    draw_section(d, 90, 1325, "Home dosing calendar checkpoints", w=1380)
    checkpoint_rows = [
        ["Date", "Prednisone", "Glargine", "Lispro rule", "Lisinopril"],
        ["08-15 Sat", "30 mg", "14 units nightly", "scale before meals", "hold"],
        ["08-17 Mon", "30 mg + BMP draw", "14 units nightly", "scale before meals", "hold until BMP reviewed"],
        ["08-20 Thu", "20 mg final day", "14 units nightly", "scale before meals", "hold"],
        ["08-23 Sun", "10 mg final day", "14 units nightly", "scale before meals", "hold"],
        ["08-24 Mon", "stop", "14 units nightly", "scale before meals", "only if clinic restarts"],
    ]
    draw_ledger(d, 110, 1400, [160, 250, 230, 280, 330], checkpoint_rows, 58)
    draw_note(d, (110, 1835, 1490, 2005), "Caregiver reminder", "Luis Rivera should compare the printed calendar with the pharmacy bottle label at pickup. If bottle instructions differ from the calendar, call Lakeview Pharmacy before the first dose.", "#334155")
    pages.append(p6)

    p7 = base_page("Discharge Pharmacy and E-Prescribe Queue")
    d = ImageDraw.Draw(p7)
    d.text((100, 150), "Queue export from bedside-meds workflow. Failed/canceled prescriptions are not active discharge medications.", fill="#475569", font=F["small"])
    rows = [
        ["Rx", "Medication", "Destination", "Status", "Auth / substitution", "Patient instruction"],
        ["RX-7401", "Azithromycin 250 mg", "Lakeview Pharmacy #12", "sent 2026-08-14 14:18", "none", "pick up today"],
        ["RX-7402", "Prednisone taper", "Lakeview Pharmacy #12", "sent 2026-08-14 14:19", "none", "follow calendar"],
        ["RX-7403", "Insulin glargine pen", "Bedside meds", "delivered 2026-08-14 15:05", "substitution Basaglar allowed", "14 units nightly"],
        ["RX-7398", "Lisinopril 20 mg", "Lakeview Pharmacy #12", "canceled 2026-08-14 14:22", "restart blocked", "not active"],
        ["RX-7404", "Glucose test strips", "Lakeview Pharmacy #12", "pending prior auth", "PA-8841", "pharmacy will call"],
    ]
    draw_table(d, 45, 250, [150, 260, 245, 245, 245, 260], rows, 76)
    checkbox(d, 100, 805, "Bedside-meds delivered for insulin glargine", True, F["small"])
    checkbox(d, 100, 865, "Prior authorization resolved for glucose strips", False, F["small"])
    checkbox(d, 100, 925, "Canceled lisinopril reactivated", False, F["small"])
    draw_note(d, (850, 805, 1515, 1045), "Queue precedence", "This pharmacy page confirms prescription routing and cancellation state. It does not override the final medication reconciliation dose table.", "#1d4ed8")
    draw_section(d, 90, 1215, "Pharmacy verification log", w=1380)
    verify_rows = [
        ["Time", "Check", "Result", "Initials"],
        ["14:31", "allergy screen", "penicillin rash only; no macrolide allergy", "JP"],
        ["14:34", "renal dose review", "avoid NSAIDs; lisinopril cancellation verified", "JP"],
        ["14:42", "insulin substitution", "Basaglar accepted for glargine pen", "MT"],
        ["14:58", "test-strip PA", "PA-8841 submitted; patient has 12 strips at home", "MT"],
    ]
    draw_ledger(d, 110, 1290, [150, 300, 600, 110], verify_rows, 58)
    draw_note(d, (110, 1695, 1490, 1875), "Pickup barrier note", "Azithromycin and prednisone are ready today. Glucose strips remain pending prior authorization, but discharge is not delayed because patient reports 12 strips at home.", "#92400e")
    pages.append(p7)

    p8 = base_page("Patient Instruction Sheet and Nurse Checklist")
    d = ImageDraw.Draw(p8)
    d.text((100, 150), "Patient copy - signed discharge teaching sheet, checklist, and follow-up logistics.", fill="#475569", font=F["small"])
    left = (
        "Medication teaching completed with patient Ana Rivera and caregiver Luis Rivera. Interpreter not used; patient declined because English instructions were preferred. "
        "High-risk medication counseling completed for insulin glargine and insulin lispro sliding scale. Teach-back incomplete for prednisone taper; nurse added follow-up call."
    )
    right = (
        "Patient instructions: finish azithromycin course; use prednisone calendar exactly; hold lisinopril until BMP is reviewed; avoid ibuprofen and naproxen; call clinic for glucose >=250 or shortness of breath. "
        "Follow-up call scheduled 2026-08-16 11:00 by RN Carla Nguyen."
    )
    draw_two_columns(d, 100, 245, left, right, col_w_chars=55, gap=70, leading=30, fnt=F["small"])
    draw_section(d, 100, 610, "Checklist", w=1380)
    checkbox(d, 120, 690, "Medication counseling completed", True, F["small"])
    checkbox(d, 120, 750, "Teach-back completed for prednisone taper", False, F["small"])
    checkbox(d, 120, 810, "High-risk insulin counseling completed", True, F["small"])
    checkbox(d, 120, 870, "Home health nurse notified", True, F["small"])
    checkbox(d, 120, 930, "Interpreter used", False, F["small"])
    d.rounded_rectangle((900, 805, 1450, 902), radius=5, fill="#f8fafc", outline="#94a3b8", width=2)
    d.text((925, 826), "Electronically signed: Ana Rivera", fill="#111827", font=F["small_bold"])
    d.text((925, 862), "Patient signature captured on file", fill="#111827", font=F["tiny_bold"])
    d.line((900, 970, 1450, 970), fill="#cbd5e1", width=3)
    d.text((925, 993), "Caregiver signature blank", fill="#64748b", font=F["small_bold"])
    draw_note(d, (100, 1130, 1510, 1305), "Nurse note", "Teach-back for the prednisone taper was not completed before discharge; RN follow-up call set for 2026-08-16 11:00.", "#92400e")
    draw_section(d, 100, 1400, "Return precautions and discharge logistics", w=1380)
    rows = [
        ["Topic", "Visible instruction / state"],
        ["Urgent symptoms", "return for chest pain, blue lips, confusion, or oxygen saturation below 90"],
        ["Fever", "call clinic for temperature >=101.5 F after 24 hours on antibiotics"],
        ["Glucose", "call clinic for glucose >=250; do not self-increase insulin beyond scale"],
        ["Portal", "MyLakeview invite sent to ana.rivera@example.test at 15:12"],
        ["Belongings", "phone, charger, glasses, and insurance card returned"],
    ]
    draw_ledger(d, 120, 1470, [245, 900], rows, 58)
    checkbox(d, 120, 1850, "Printed medication calendar handed to patient", True, F["small"])
    checkbox(d, 120, 1910, "Home oxygen ordered", False, F["small"])
    checkbox(d, 120, 1970, "Work note requested", True, F["small"])
    pages.append(p8)

    gold = """# Lakeview Medical Center - Discharge Packet

Patient: Ana Rivera. MRN: LMC-482913. DOB: 1979-04-18. Packet finalized 2026-08-14 14:40.

## Discharge Summary

Admission date: 2026-08-10. Discharge date: 2026-08-14. Primary diagnosis: community-acquired pneumonia with acute kidney injury, improving. Secondary diagnoses: type 2 diabetes, hypertension, and medication-associated hyperkalemia. Allergy: penicillin - rash. Pending test: blood culture final read expected 2026-08-16.

Source-state notice: final medication reconciliation signed 14:40 controls. ED medication list and draft footer are historical. Do not restart lisinopril until follow-up BMP is reviewed.

| Follow-up need | Due | Owner | Status | Instruction |
| --- | --- | --- | --- | --- |
| BMP lab draw | 2026-08-17 08:00 | Home health | Scheduled | check K and creatinine |
| Primary care | 2026-08-19 10:30 | Dr. Shah | Scheduled | review antibiotics |
| Cardiology | 2026-08-25 09:00 | Dr. Kim | Scheduled | 11 days after discharge |
| Blood culture final | 2026-08-16 | LMC lab | Pending | call if positive |

The draft footer said cardiology in 2 weeks, but the signed referral sheet controls with cardiology on 2026-08-25.

## Lab Trends

| Analyte | Ref range | Unit | 08-10 06:20 | 08-12 05:50 | 08-14 06:05 |
| --- | --- | --- | --- | --- | --- |
| WBC | 4.0-11.0 | K/uL | 14.2 H | 9.8 | 7.6 |
| Hemoglobin | 12.0-16.0 | g/dL | 10.8 L | 10.1 L | 10.4 L |
| Platelets | 150-400 | K/uL | 412 H | 390 | 366 |
| Creatinine | 0.6-1.2 | mg/dL | 1.9 H | 1.5 H | 1.2 |
| Potassium | 3.5-5.1 | mmol/L | 5.8 H | hemolyzed | 4.7 |
| Glucose | 70-110 | mg/dL | 188 H | 142 H | 126 H |
| INR | 0.9-1.1 | ratio | 1.0 | canceled | 1.1 |

Footnotes: 08-12 potassium is hemolyzed and excluded. 08-12 INR was canceled and should not be carried forward. Hemoglobin remains low at discharge. Creatinine sparkline values are 1.9, 1.5, and 1.2.

Specimen handling audit:

| Specimen | Collection | Result state | Action |
| --- | --- | --- | --- |
| BMP tube A | 08-10 06:20 | accepted | trend baseline |
| BMP tube B | 08-12 05:50 | K hemolyzed | exclude potassium only |
| Coag tube C | 08-12 05:50 | INR canceled | do not carry forward |
| BMP tube D | 08-14 06:05 | accepted | discharge value |

Renal dosing comment: creatinine improved to 1.2 before discharge, but lisinopril remains held until the outpatient BMP is reviewed. Potassium 4.7 is current; hemolyzed 08-12 potassium is not used.

## Final Medication Reconciliation

| Medication | Home dose | Discharge dose | Route | Frequency | Action | Note |
| --- | --- | --- | --- | --- | --- | --- |
| Metformin | 500 mg | 500 mg | PO | twice daily | continue | take with meals |
| Lisinopril | 20 mg | HOLD | PO | do not restart | stop | restart only after BMP |
| Azithromycin | - | 250 mg | PO | daily x3 days | new | finish course |
| Insulin glargine | 18 units | 14 units | SQ | nightly | change | dose reduced |
| Ibuprofen | 400 mg | STOP | PO | none | stop | avoid with kidney injury |

Checked actions: continue Metformin, change Insulin glargine, stop Lisinopril, new Azithromycin. Restart lisinopril today is unchecked. ED list showed lisinopril 20 mg daily and ibuprofen PRN, but both are inactive at discharge.

## Nursing MAR and Vitals Timeline

Grid states: A=administered, H=held, R=refused, M=missed. Held doses are not administered.

| Medication | 06:00 | 12:00 | 18:00 | 22:00 | Comment |
| --- | --- | --- | --- | --- | --- |
| Azithromycin | | A | | | given after lunch |
| Insulin lispro | A | H | A | | 12:00 held: glucose 88 |
| Acetaminophen | | R | | A | refused noon dose |
| Lisinopril | H | H | H | H | held all day |
| Metformin | A | | A | | continued |

Oxygen saturation values are 91, 93, 95, 96, and 96, with a 94 threshold; values cross above threshold after the second point. Blood pressure table: 06:00 132/84 pulse 88; 12:00 118/72 pulse 82; 18:00 126/78 pulse 80; 22:00 124/76 pulse 78.

Nursing event log:

| Time | Event | Linked field |
| --- | --- | --- |
| 05:55 | room-air trial started | oxygen trend |
| 12:08 | lispro held after glucose 88; snack given | MAR H at 12:00 |
| 18:20 | ambulated 150 ft with cane | discharge mobility |
| 22:10 | SpO2 96 on room air before sleep | final oxygen point |

24h intake/output: oral intake 1,320 mL; urine output 1,650 mL; net -330 mL; fever after noon none documented.

## Referral Sheet and Discharge Footer Addendum

| Appointment | Date/time | Location | Status | Instruction |
| --- | --- | --- | --- | --- |
| Home health nurse | 2026-08-15 09:00 | home | authorized | med check and vitals |
| BMP lab draw | 2026-08-17 08:00 | LMC Lab | scheduled | bring lab slip |
| Primary care | 2026-08-19 10:30 | Clinic A | scheduled | review antibiotics |
| Cardiology | 2026-08-25 09:00 | Heart Center | scheduled | 11 days after discharge |

Authorization stamp: home health visit approved once for 2026-08-15. Additional visits require PCP order.

Draft footer from 08:15 said cardiology in 2 weeks and resume home blood pressure pill. It is superseded by final medication reconciliation and signed referral schedule.

Care coordination contact log: 14:50 home health intake accepted one RN visit, case HH-60814, initials CN; 14:57 LMC Lab released BMP order and fasting is not required, initials MP; 15:03 Clinic A confirmed PCP visit and instructed patient to bring med list, initials CN; 15:18 Heart Center cardiology packet faxed with receipt OK, initials JW.

Home setup checklist: thermometer available checked; working glucometer confirmed checked; transportation arranged for BMP lab draw checked; oxygen concentrator ordered unchecked. Care-team note says Luis Rivera will drive to the 08/17 BMP draw; if fever reaches 101.5 F after 24 hours on antibiotics, call Clinic A before using urgent care.

## Prednisone Taper and Conditional Dosing Calendar

| Date range / condition | Medication | Dose | Route | Frequency | Instruction |
| --- | --- | --- | --- | --- | --- |
| 2026-08-15 to 2026-08-17 | Prednisone | 30 mg | PO | daily with breakfast | taper step 1 |
| 2026-08-18 to 2026-08-20 | Prednisone | 20 mg | PO | daily with breakfast | taper step 2 |
| 2026-08-21 to 2026-08-23 | Prednisone | 10 mg | PO | daily with breakfast | taper step 3 |
| 2026-08-24 | Prednisone | stop | | | last planned dose was 2026-08-23 |
| Glucose 70-149 | Insulin lispro | 0 units | SQ | before meals | sliding scale |
| Glucose 150-199 | Insulin lispro | 2 units | SQ | before meals | sliding scale |
| Glucose 200-249 | Insulin lispro | 4 units | SQ | before meals | sliding scale |
| Glucose >=250 | Insulin lispro | call clinic | | | do not self-increase beyond scale |

The sliding-scale page is final only for insulin lispro correction doses. It does not change insulin glargine 14 units nightly. BMP on 2026-08-17 must be reviewed before any lisinopril restart.

Home dosing calendar checkpoints:

| Date | Prednisone | Glargine | Lispro rule | Lisinopril |
| --- | --- | --- | --- | --- |
| 08-15 Sat | 30 mg | 14 units nightly | scale before meals | hold |
| 08-17 Mon | 30 mg + BMP draw | 14 units nightly | scale before meals | hold until BMP reviewed |
| 08-20 Thu | 20 mg final day | 14 units nightly | scale before meals | hold |
| 08-23 Sun | 10 mg final day | 14 units nightly | scale before meals | hold |
| 08-24 Mon | stop | 14 units nightly | scale before meals | only if clinic restarts |

Caregiver reminder: Luis Rivera should compare the printed calendar with the pharmacy bottle label at pickup. If bottle instructions differ from the calendar, call Lakeview Pharmacy before the first dose.

## Discharge Pharmacy and E-Prescribe Queue

| Rx | Medication | Destination | Status | Auth / substitution | Patient instruction |
| --- | --- | --- | --- | --- | --- |
| RX-7401 | Azithromycin 250 mg | Lakeview Pharmacy #12 | sent 2026-08-14 14:18 | none | pick up today |
| RX-7402 | Prednisone taper | Lakeview Pharmacy #12 | sent 2026-08-14 14:19 | none | follow calendar |
| RX-7403 | Insulin glargine pen | Bedside meds | delivered 2026-08-14 15:05 | substitution Basaglar allowed | 14 units nightly |
| RX-7398 | Lisinopril 20 mg | Lakeview Pharmacy #12 | canceled 2026-08-14 14:22 | restart blocked | not active |
| RX-7404 | Glucose test strips | Lakeview Pharmacy #12 | pending prior authorization | PA-8841 | pharmacy will call |

Bedside-meds delivered for insulin glargine is checked. Prior authorization resolved for glucose strips is unchecked. Canceled lisinopril reactivated is unchecked. This pharmacy page confirms prescription routing and cancellation state; it does not override the final medication reconciliation dose table.

Pharmacy verification log:

| Time | Check | Result | Initials |
| --- | --- | --- | --- |
| 14:31 | allergy screen | penicillin rash only; no macrolide allergy | JP |
| 14:34 | renal dose review | avoid NSAIDs; lisinopril cancellation verified | JP |
| 14:42 | insulin substitution | Basaglar accepted for glargine pen | MT |
| 14:58 | test-strip PA | PA-8841 submitted; patient has 12 strips at home | MT |

Pickup barrier note: azithromycin and prednisone are ready today. Glucose strips remain pending prior authorization, but discharge is not delayed because patient reports 12 strips at home.

## Patient Instruction Sheet and Nurse Checklist

Medication teaching was completed with patient Ana Rivera and caregiver Luis Rivera. Interpreter was not used because the patient declined and preferred English instructions. High-risk medication counseling was completed for insulin glargine and insulin lispro sliding scale. Teach-back was incomplete for the prednisone taper.

Patient instructions: finish azithromycin course; use prednisone calendar exactly; hold lisinopril until BMP is reviewed; avoid ibuprofen and naproxen; call clinic for glucose >=250 or shortness of breath. Follow-up call scheduled 2026-08-16 11:00 by RN Carla Nguyen.

Checklist states: medication counseling completed checked; teach-back completed for prednisone taper unchecked; high-risk insulin counseling completed checked; home health nurse notified checked; interpreter used unchecked. Ana Rivera electronically signed and the patient signature is captured on file. Caregiver signature is blank.

Return precautions and logistics: return for chest pain, blue lips, confusion, or oxygen saturation below 90; call clinic for temperature >=101.5 F after 24 hours on antibiotics; call clinic for glucose >=250 and do not self-increase insulin beyond scale. MyLakeview invite was sent to ana.rivera@example.test at 15:12. Belongings returned: phone, charger, glasses, and insurance card. Printed medication calendar handed to patient checked; home oxygen ordered unchecked; work note requested checked.
"""

    return Case(
        "P08-hospital-discharge-medrec",
        "Hospital Discharge Medication Reconciliation",
        "medical",
        ["multi-page", "labs", "med-rec", "forms", "timeline", "source-precedence", "chart"],
        "Stress a realistic discharge packet with lab units/flags, final-vs-draft medication state, selected actions, held/administered MAR states, visual vitals, and follow-up conflicts.",
        "Eight-page medical discharge packet with mixed memo text, tables, checkboxes, chart, pharmacy queue, taper calendar, and draft/source-state conflict.",
        ["discharge summary", "lab trends", "medication reconciliation", "MAR grid", "referrals", "draft precedence"],
        ["Preserve medication action state.", "Bind lab values to units, flags, and collection times.", "Do not treat held doses as administered.", "Keep draft footer superseded."],
        gold,
        [near_check("med-lisinopril", "forms", ["Lisinopril", "HOLD", "stop", "BMP"], 4, 520)],
        pages,
        facts=[
            fact("p08.summary.state", "source_state", 6, "Final medication reconciliation signed 14:40 controls; ED medication list and draft footer are historical; do not restart lisinopril until follow-up BMP is reviewed."),
            fact("p08.followup.table", "table_cell", 5, "Follow-up table preserves BMP 2026-08-17 08:00, primary care 2026-08-19 10:30, cardiology 2026-08-25 09:00, and blood culture final 2026-08-16."),
            fact("p08.labs.cbc", "table_cell", 5, "CBC rows preserve WBC 14.2 H/9.8/7.6 K/uL, hemoglobin 10.8 L/10.1 L/10.4 L g/dL, platelets 412 H/390/366 K/uL."),
            fact("p08.labs.cmp", "table_cell", 6, "CMP/coag rows preserve creatinine 1.9 H/1.5 H/1.2 mg/dL, potassium 5.8 H/hemolyzed/4.7 mmol/L, glucose 188 H/142 H/126 H mg/dL, INR 1.0/canceled/1.1."),
            fact("p08.labs.exclusions", "source_state", 5, "08-12 potassium is hemolyzed and excluded, 08-12 INR is canceled and not carried forward, and hemoglobin remains low at discharge."),
            fact("p08.specimen.audit", "table_cell", 7, "Specimen handling audit preserves BMP tube A accepted/trend baseline, BMP tube B K hemolyzed/exclude potassium only, Coag tube C INR canceled/do not carry forward, BMP tube D accepted/discharge value, and renal dosing comment that creatinine improved to 1.2 while lisinopril remains held until outpatient BMP.", modality="table", severity="major"),
            fact("p08.creatinine.sparkline", "visual_relation", 4, "Creatinine sparkline values are 1.9, 1.5, and 1.2, showing improvement."),
            fact("p08.med.table", "table_cell", 8, "Medication table preserves Metformin 500 mg continue, Lisinopril HOLD/stop/do not restart, Azithromycin 250 mg daily x3 days/new, Insulin glargine 14 units/change, Ibuprofen STOP/stop."),
            fact("p08.med.checkboxes", "form_state", 6, "Checked actions are continue Metformin, change Insulin glargine, stop Lisinopril, new Azithromycin; restart lisinopril today is unchecked."),
            fact("p08.med.superseded", "source_state", 6, "ED list showed lisinopril 20 mg daily and ibuprofen PRN, but both are inactive at discharge and must not be treated as active discharge medications."),
            fact("p08.mar.grid", "table_cell", 7, "MAR grid preserves Azithromycin administered at 12:00, Insulin lispro administered 06:00 and 18:00 but held at 12:00, Acetaminophen refused 12:00 and administered 22:00, Lisinopril held all day, Metformin administered 06:00 and 18:00."),
            fact("p08.vitals", "visual_relation", 8, "Oxygen saturation chart values are 91, 93, 95, 96, 96 with threshold 94; BP table preserves 132/84 pulse 88, 118/72 pulse 82, 126/78 pulse 80, 124/76 pulse 78; nursing event log preserves room-air trial 05:55, lispro held/snack at 12:08, ambulated 150 ft at 18:20, SpO2 96 at 22:10, and intake/output 1,320 mL in, 1,650 mL out, net -330 mL.", modality="chart", severity="critical"),
            fact("p08.referrals", "table_cell", 8, "Referral sheet preserves home health 2026-08-15 09:00 authorized once, BMP 2026-08-17 08:00, primary care 2026-08-19 10:30, cardiology 2026-08-25 09:00, contact log times/results/initials, and home setup checkbox states.", modality="form", severity="critical"),
            fact("p08.draft.footer", "source_state", 6, "Draft footer said cardiology in 2 weeks and resume home blood pressure pill, but it is superseded by the signed referral schedule and final medication reconciliation."),
            fact("p08.taper", "table_cell", 11, "Prednisone taper and insulin lispro sliding scale preserve all date ranges/conditions, doses, route/frequency, stop date, glucose >=250 call-clinic instruction, home dosing checkpoints for 08-15/08-17/08-20/08-23/08-24, glargine 14 units nightly, and lisinopril hold/restart conditions.", modality="table", severity="critical"),
            fact("p08.taper.source_state", "source_state", 7, "Sliding scale applies only to insulin lispro correction doses, does not change glargine 14 units nightly, and does not restart lisinopril before BMP review.", modality="source-precedence", severity="critical"),
            fact("p08.pharmacy", "form_state", 11, "E-prescribe queue preserves RX-7401/RX-7402 sent, RX-7403 delivered with Basaglar substitution allowed, RX-7398 lisinopril canceled/not active, RX-7404 strips pending PA-8841, checkbox states, pharmacy verification log 14:31/14:34/14:42/14:58 with initials JP/MT, and pickup barrier note that strips remain pending but discharge is not delayed because patient has 12 strips at home.", modality="form", severity="critical"),
            fact("p08.nurse.checklist", "form_state", 10, "Nurse checklist preserves counseling checked, prednisone teach-back unchecked, insulin counseling checked, home health notified checked, interpreter used unchecked, Ana Rivera electronically signed with patient signature captured on file, caregiver signature blank, RN follow-up call 2026-08-16 11:00, return precautions, portal invite, belongings, printed medication calendar checked, home oxygen unchecked, and work note checked.", modality="form", severity="critical"),
            fact("p08.page_order", "structure", 4, "Output preserves packet order: discharge summary, lab trends, final medication reconciliation, nursing MAR/vitals, referral sheet/discharge footer addendum, taper calendar, pharmacy queue, patient instruction/nurse checklist."),
        ],
        extractable_text_pages=[
            overlays(["Lakeview Medical Center - Discharge Packet", "Patient: Ana Rivera", "MRN: LMC-482913"], 100, 100),
            [],
            [],
            [],
            overlays(["Draft footer from 08:15 is superseded by final medication reconciliation and signed referral schedule."], 880, 730),
        ],
    )


def packet_loan_amendment_closing() -> Case:
    pages: list[Image.Image] = []

    p1 = base_page("Project Helios Closing Packet")
    d = ImageDraw.Draw(p1)
    d.text((100, 142), "Second Amendment to Loan and Security Agreement | Closing memo | June 30, 2026", fill="#475569", font=F["small"])
    y = draw_kv_band(
        d,
        92,
        218,
        [
            ("Borrower", "Northstar Robotics, Inc."),
            ("Agent", "Meridian Bank, N.A."),
            ("Effective", "June 28, 2026"),
            ("Closing", "June 30, 2026"),
            ("Facility", "$27,000,000"),
        ],
        [360, 310, 230, 230, 240],
    )
    left = (
        "This closing packet assembles the executed Second Amendment, blackline pages, certificate extracts, funds flow, lien evidence, "
        "and post-closing undertaking register for Project Helios. The original Loan and Security Agreement is dated March 15, 2024. "
        "The amendment increases the commitment from $18,500,000 to $27,000,000 through an $8,500,000 Tranche B advance. "
        "The memo workstream still shows a $3,250,000 liquidity covenant in one paragraph; the executed amendment and final compliance certificate rider control at $3,500,000."
    )
    right = (
        "Borrower counsel is Klein & Arroyo LLP. Lender counsel is Frost Bellwick LLP. Closing deliverables are held in the v12 packet circulated "
        "06/27/26 11:48 PM ET. Funding is targeted for June 30, 2026. The authorized borrower signer is Maya Chen, Chief Financial Officer. "
        "A checklist later says Priya Raman only, but the officer certificate and board consent authorize Maya Chen."
    )
    draw_two_columns(d, 100, y + 15, left, right, col_w_chars=52, gap=85, leading=28, fnt=F["small"])
    draw_section(d, 100, 660, "Closing timeline", w=1390)
    timeline = [("Original LSA", "03/15/2024"), ("First Amend.", "11/22/2025"), ("Board consent", "06/24/2026"), ("UCC refresh", "06/26/2026"), ("Target funding", "06/30/2026")]
    x0, ty = 150, 760
    d.line((x0 + 70, ty + 35, x0 + 1210, ty + 35), fill="#111827", width=3)
    for i, (label, date) in enumerate(timeline):
        x = x0 + i * 285
        d.ellipse((x + 58, ty + 23, x + 82, ty + 47), fill="#111827")
        d.text((x, ty + 75), label, fill="#111827", font=F["tiny_bold"])
        d.text((x, ty + 102), date, fill="#475569", font=F["tiny"])
    draw_section(d, 100, 940, "Use of Tranche B proceeds", w=1390)
    proceeds = [
        ("Existing revolver payoff", 3200000, "#64748b"),
        ("Equipment deposits", 4150000, "#2563eb"),
        ("Closing fees", 685000, "#c2410c"),
        ("Working capital", 465000, "#0f766e"),
    ]
    bx, by = 145, 1070
    scale = 0.00011
    for label, amount, color in proceeds:
        w = max(70, int(amount * scale))
        d.rectangle((bx, by, bx + w, by + 58), fill=color)
        if w >= 105:
            d.text((bx + 8, by + 16), f"${amount/1000000:.3f}M", fill="white", font=F["tiny_bold"])
        bx += w + 16
    for i, (label, amount, color) in enumerate(proceeds):
        lx = 145 + (i % 2) * 500
        ly = 1162 + (i // 2) * 58
        d.rectangle((lx, ly + 4, lx + 24, ly + 28), fill=color)
        d.text((lx + 36, ly), f"{label} - ${amount/1000000:.3f}M", fill="#111827", font=F["tiny"])
    draw_section(d, 100, 1290, "Source-state notes", w=1390, color="#9a3412")
    draw_text(
        d,
        (100, 1350),
        "Executed amendment controls final operative terms. Blacklines show deleted and inserted text. The checklist is an operational tracker and may be stale where later filing receipts or funds-flow instructions conflict with it.",
        F["small"],
        fill="#7f1d1d",
        width=100,
        leading=31,
    )
    pages.append(p1)

    p2 = base_page("Second Amendment - Blackline Against v11")
    d = ImageDraw.Draw(p2)
    d.text((100, 150), "Sections 1-3. Blackline excerpt: struck text is prior draft language; underlined green text is proposed replacement language.", fill="#7f1d1d", font=F["small"])
    y = draw_section(d, 100, 230, "1. Commitment", w=1010)
    y = draw_redline_text(
        d,
        125,
        y,
        [
            ("normal", 'The definition of "Commitment" is amended by replacing '),
            ("delete", "$18,500,000"),
            ("normal", " with "),
            ("insert", "$27,000,000"),
            ("normal", " for all purposes under the Loan and Security Agreement."),
        ],
        width=1050,
    )
    y = draw_section(d, 100, y + 35, "2. Tranche B Advance", w=1010)
    y = draw_redline_text(
        d,
        125,
        y,
        [
            ("insert", "A new Tranche B Advance in the principal amount of $8,500,000 is available only on the Closing Date."),
            ("normal", " No unused availability remains after funding."),
        ],
        width=1050,
    )
    y = draw_section(d, 100, y + 35, "3. Interest Rate", w=1010)
    y = draw_redline_text(
        d,
        125,
        y,
        [
            ("normal", "Loans bear interest at "),
            ("delete", "SOFR + 5.25%"),
            ("normal", " "),
            ("insert", "Adjusted Term SOFR + 5.75%"),
            ("normal", ". The SOFR floor remains "),
            ("insert", "2.00%"),
            ("normal", ". Deleted borrower footnote referred to a "),
            ("delete", "SOFR floor of 1.50%"),
            ("normal", "."),
        ],
        width=1050,
    )
    draw_note(d, (1235, 290, 1575, 470), "C-14 Frost Bellwick", "Confirm SOFR floor remains 2.00%; borrower draft had 1.50%.", "#92400e")
    draw_note(d, (1235, 505, 1575, 665), "Footnote", "Conforming changes required in Exhibit B compliance certificate.", "#1d4ed8")
    draw_section(d, 100, 1120, "Rate bridge", w=1010)
    rate_parts = [("SOFR floor", "2.00%"), ("Spread", "5.75%"), ("Default incr.", "2.00%"), ("Max default", "9.75%")]
    for i, (label, val) in enumerate(rate_parts):
        x = 135 + i * 260
        d.line((x, 1205, x + 190, 1205), fill="#111827", width=2)
        d.text((x, 1230), label, fill="#6b7280", font=F["tiny_bold"])
        d.text((x, 1263), val, fill="#111827", font=F["h2"])
    pages.append(p2)

    p3 = base_page("Covenants and Fee Grid")
    d = ImageDraw.Draw(p3)
    d.text((100, 150), "Blackline page with covenant matrix embedded in the contract body.", fill="#475569", font=F["small"])
    y = draw_section(d, 100, 230, "4.2 Liquidity Covenant", w=1010)
    y = draw_redline_text(
        d,
        125,
        y,
        [
            ("normal", "Borrower shall maintain unrestricted cash and cash equivalents of not less than "),
            ("delete", "$3,250,000"),
            ("normal", " "),
            ("insert", "$3,500,000"),
            ("normal", ", tested monthly, commencing with the test date ending July 31, 2026."),
        ],
        width=1050,
    )
    y = draw_section(d, 100, y + 25, "4.4 Revenue Reporting", w=1010)
    y = draw_text(d, (125, y), "Monthly ARR reporting package is due 15 business days after month-end. Borrower request for 20 business days was rejected.", F["small"], width=76, leading=30)
    y = draw_section(d, 100, y + 25, "5. Fees", w=1010)
    fee_text = (
        "The amendment fee equals 0.75% of the incremental commitment. Calculation: 0.75% x $8,500,000 = $63,750. "
        "The unused line fee is 0.35% per annum. The exit fee is 1.25% of aggregate commitments."
    )
    y = draw_text(d, (125, y), fee_text, F["small"], width=76, leading=30)
    y = draw_section(d, 100, y + 40, "Exhibit B covenant summary", w=1010)
    covenant_rows = [
        ["Topic", "Final covenant / deadline", "Prior draft or checklist", "Counsel disposition"],
        ["Liquidity", "$3.50M unrestricted cash", "$3.25M", "inserted in Section 4.2"],
        ["ARR package", "15 business days", "20 business days requested", "request rejected"],
        ["Insurance endorsement", "5 business day cure", "not listed in covenant body", "post-closing open item"],
        ["IP schedule supplement", "10 business day delivery", "schedule incomplete", "post-closing open item"],
    ]
    draw_ledger(d, 100, y + 12, [230, 280, 280, 300], covenant_rows, 56)
    draw_text(
        d,
        (125, y + 355),
        "Closing condition note: this summary is embedded in the blackline for review convenience only. It does not replace the marked operative text above; later executed amendment terms and filed exhibit values supersede stale checklist values.",
        F["small"],
        fill="#374151",
        width=76,
        leading=29,
    )
    draw_note(d, (1235, 250, 1575, 435), "C-19", "Checklist still shows 1.00% amendment fee; update before funding.", "#92400e")
    draw_note(d, (1235, 475, 1575, 645), "C-21", "Borrower requested 20 BD for ARR package; rejected.", "#92400e")
    draw_note(d, (1235, 700, 1575, 950), "Margin fee table", "Stale margin table: amendment fee 1.00% / $85,000. Body text controls: 0.75% / $63,750.", "#991b1b")
    pages.append(p3)

    p4 = base_page("Signature Packet and Certificates")
    d = ImageDraw.Draw(p4)
    d.text((100, 150), "Composite executed blocks, officer certificate excerpt, board consent, and notary venue.", fill="#475569", font=F["small"])
    draw_section(d, 100, 230, "Executed signature blocks", w=1390)
    sig_rows = [
        ["Party", "Signer", "Title", "Date"],
        ["Northstar Robotics, Inc.", "Maya Chen", "Chief Financial Officer", "June 30, 2026"],
        ["Northstar Automation Holdings LLC", "Daniel Ruiz", "President", "June 30, 2026"],
        ["Meridian Bank, N.A.", "S. Patel", "Authorized Officer", "June 30, 2026"],
    ]
    draw_table(d, 100, 310, [420, 270, 380, 230], sig_rows, 74)
    draw_section(d, 100, 720, "Officer certificate excerpt", w=1390)
    draw_text(d, (100, 780), "Maya Chen is the duly appointed Chief Financial Officer and is authorized to execute the Amendment on behalf of Northstar Robotics, Inc.", F["small"], width=98, leading=31)
    draw_section(d, 100, 920, "Board consent excerpt", w=1390)
    draw_text(d, (100, 980), "Resolved, that either Priya Raman, Chief Executive Officer, or Maya Chen, Chief Financial Officer, may execute and deliver the Second Amendment and related certificates.", F["small"], width=98, leading=31)
    d.rounded_rectangle((875, 1115, 1495, 1235), radius=8, outline="#0f766e", width=4)
    d.text((900, 1142), "APPROVED FOR RELEASE - FROST BELLWICK LLP", fill="#0f766e", font=F["small_bold"])
    d.text((1085, 1188), "06/30/26 9:12 AM ET", fill="#0f766e", font=F["small_bold"])
    draw_note(d, (100, 1290, 650, 1505), "Notary venue", "San Mateo County, California. Certificate address block lists Austin, Texas.", "#1d4ed8")
    draw_note(d, (820, 1290, 1510, 1505), "Checklist conflict", "Later checklist says required signer is Priya Raman, CEO only. Certificate and consent authorize Maya Chen, CFO.", "#991b1b")
    pages.append(p4)

    p5 = base_page("Closing Checklist and Document Status Matrix")
    d = ImageDraw.Draw(p5)
    d.text((100, 150), "Checklist is dense and operational; later filing receipts and funds-flow values may supersede it.", fill="#7f1d1d", font=F["small"])
    d.text((1250, 230), "Closing progress", fill="#111827", font=F["small_bold"])
    d.text((1250, 282), "Funding conditions", fill="#475569", font=F["tiny_bold"])
    d.rectangle((1250, 315, 1505, 340), outline="#94a3b8", width=2)
    d.rectangle((1250, 315, 1486, 340), fill="#0f766e")
    d.text((1515, 306), "12/13", fill="#111827", font=F["tiny_bold"])
    d.text((1250, 378), "Post-closing", fill="#475569", font=F["tiny_bold"])
    d.rectangle((1250, 410, 1505, 435), outline="#94a3b8", width=2)
    d.rectangle((1250, 410, 1359, 435), fill="#64748b")
    d.text((1515, 401), "3/7", fill="#111827", font=F["tiny_bold"])
    rows = [
        ["Item", "Responsible", "Status", "Before funding?", "Evidence", "Comments"],
        ["Executed Amendment", "Klein", "Complete", "Yes", "DocuSign 8274-6119", ""],
        ["Officer Certificate", "Borrower", "Complete", "Yes", "OC-Helios-063026.pdf", ""],
        ["Board Consent", "Borrower", "Complete", "Yes", "Minutes extract 06/24/26", ""],
        ["Good standing Delaware", "Klein", "Complete", "Yes", "cert 7381194 / 06/25/26", ""],
        ["UCC-3 amendment Delaware", "Frost", "Pending", "Yes", "awaiting receipt", "page 7 later shows filed"],
        ["Insurance endorsement", "Borrower", "Post-closing", "No", "due 07/07/26", "loss payable"],
        ["IP schedule supplement", "GC", "Post-closing", "No", "due 07/14/26", ""],
        ["Landlord waiver, Fremont", "Ops", "Waived", "No", "waiver letter", "expires if lease amendment not delivered by 08/15/26"],
    ]
    draw_table(d, 55, 500, [285, 160, 170, 185, 300, 360], rows, 62)
    draw_section(d, 100, 1195, "Version sparkline", w=720)
    pts = [(135, 1340), (255, 1290), (375, 1325), (495, 1240)]
    for a, b in zip(pts, pts[1:]):
        d.line((*a, *b), fill="#2563eb", width=5)
    for p, label in zip(pts, ["v9", "v10", "v11", "v12"]):
        d.ellipse((p[0] - 8, p[1] - 8, p[0] + 8, p[1] + 8), fill="#2563eb")
        d.text((p[0] - 12, p[1] + 24), label, fill="#111827", font=F["tiny"])
    draw_note(d, (900, 1215, 1540, 1465), "Stale checklist values", "Checklist says amendment fee $85,000 and UCC-3 pending. Funds flow and lien exhibit control with $63,750 and filed receipt 2026-7741203.", "#991b1b")
    pages.append(p5)

    p6 = base_page("Funds Flow and Escrow Instructions")
    d = ImageDraw.Draw(p6)
    d.text((100, 150), "Wire letter. Numbers in the waterfall are embedded beside the instruction paragraphs.", fill="#475569", font=F["small"])
    y = draw_kv_band(
        d,
        100,
        230,
        [
            ("Incoming", "$8,500,000"),
            ("Escrow acct", "ending 4412"),
            ("Borrower acct", "ending 9081"),
            ("Funding date", "June 30, 2026"),
        ],
        [270, 300, 330, 320],
    )
    draw_text(
        d,
        (100, y + 15),
        "Meridian Bank shall wire the Tranche B advance from escrow account ending 4412 to Northstar Robotics' operating account at Pacific Commercial Bank ending 9081. Instruction paragraph requests release no later than 2:00 PM Eastern. Footer approval note says release approved after 2:30 PM Eastern.",
        F["small"],
        width=86,
        leading=31,
    )
    rows = [
        ["Deduction", "Amount"],
        ["Amendment fee", "$63,750"],
        ["Lender counsel fees", "$188,400"],
        ["Borrower counsel fees paid from proceeds", "$142,600"],
        ["UCC/search/filing charges", "$18,000"],
        ["Existing revolver cleanup payoff", "$336,000"],
        ["Net borrower proceeds", "$7,751,250"],
    ]
    draw_table(d, 100, 590, [520, 230], rows, 68)
    draw_section(d, 885, 570, "Funds flow bridge", w=650)
    d.line((930, 1115, 1490, 1115), fill="#94a3b8", width=2)
    bridge = [
        ("Gross", "$8.500M", 935, 300, "#334155"),
        ("Fee", "($0.064M)", 1030, 28, "#b91c1c"),
        ("Counsel", "($0.331M)", 1110, 92, "#b91c1c"),
        ("Filing", "($0.018M)", 1210, 20, "#b91c1c"),
        ("Payoff", "($0.336M)", 1290, 96, "#b91c1c"),
        ("Net", "$7.751M", 1400, 270, "#0f766e"),
    ]
    baseline = 1090
    for i, (name, value, x, h, color) in enumerate(bridge):
        if i in (0, len(bridge) - 1):
            d.rectangle((x, baseline - h, x + 58, baseline), fill=color)
            d.text((x - 14, baseline - h - 50), value, fill=color, font=F["tiny_bold"])
        else:
            d.rectangle((x, baseline - h, x + 58, baseline), fill="#fee2e2", outline=color, width=2)
            d.text((x - 18, baseline - h - 48), value, fill=color, font=F["tiny_bold"])
        d.text((x + 4, baseline + 24), name, fill="#111827", font=F["tiny"])
        if i < len(bridge) - 1:
            nx = bridge[i + 1][2]
            d.line((x + 58, baseline - max(28, h), nx, baseline - max(28, bridge[i + 1][3])), fill="#64748b", width=1)
    d.text((930, 1165), "Amounts are shown in USD millions; deductions reduce borrower proceeds.", fill="#475569", font=F["tiny"])
    draw_note(d, (100, 1255, 760, 1515), "Bank confirmation memo", "Operations confirmation received at 13:36 lists borrower account ending 9801. The final wire instruction page lists borrower account ending 9081.", "#991b1b")
    draw_note(d, (900, 1255, 1510, 1515), "Funding desk timing note", "The funding instruction targets no later than 2:00 PM Eastern. Agent approval footer records release approval after 2:30 PM Eastern.", "#92400e")
    pages.append(p6)

    p7 = base_page("UCC / Lien / Insurance / IP Exhibit")
    d = ImageDraw.Draw(p7)
    d.text((100, 150), "Lien evidence, insurance exceptions, and IP supplement. Later evidence supersedes checklist status.", fill="#7f1d1d", font=F["small"])
    rows = [
        ["Search / filing", "Result"],
        ["Delaware original UCC-1", "file no. 2024-1459821, filed 03/18/2024"],
        ["Delaware UCC-3 amendment", "file no. 2026-7741203, filed 06/29/2026 4:41 PM ET"],
        ["California fixture filing search", "No active fixture filings found"],
        ["Texas SOS search", "terminated file 23-8841107; Vector Equipment Finance LLC; terminated 05/09/2025"],
    ]
    draw_table(d, 80, 245, [420, 850], rows, 72)
    draw_section(d, 100, 725, "Priority stack", w=600)
    stack = [
        "1. Meridian Bank blanket lien",
        "2. Permitted purchase-money equipment lien capped at $900,000",
        "3. Statutory liens not yet due",
        "4. Excluded Fremont landlord interest",
    ]
    for i, label in enumerate(stack):
        d.rectangle((120, 800 + i * 80, 760, 852 + i * 80), fill=["#dbeafe", "#ecfeff", "#f8fafc", "#fff7ed"][i], outline="#111827", width=2)
        d.text((138, 814 + i * 80), label, fill="#111827", font=F["tiny"])
    draw_section(d, 870, 725, "Insurance and IP exceptions", w=650)
    rows2 = [
        ["Item", "Value / status"],
        ["Cyber liability", "$5,000,000"],
        ["General liability", "$2,000,000 per occurrence"],
        ["Property coverage", "$18,200,000"],
        ["Missing endorsement", "lender loss payable due 07/07/2026"],
        ["Patent application", "US 18/771,204 Robotic Arm Calibration Using Visual Feedback"],
        ["Trademark", "NORTHSTAR ORBIT serial 98441120"],
        ["IP supplement", "due 07/14/2026"],
    ]
    draw_table(d, 870, 800, [270, 520], rows2, 58)
    draw_note(d, (100, 1415, 1510, 1585), "Status conflict resolved", "Checklist page says Delaware UCC-3 pending. This exhibit shows it was filed as 2026-7741203 on 06/29/2026 at 4:41 PM ET.", "#0f766e")
    pages.append(p7)

    p8 = base_page("Post-Closing Undertakings and Exceptions Register")
    d = ImageDraw.Draw(p8)
    d.text((100, 150), "Final undertakings register. Includes due-date diary extract, exception notes, and counsel comments.", fill="#475569", font=F["small"])
    rows = [
        ["Obligation", "Source", "Owner", "Due date", "Evidence required", "Consequence", "Status"],
        ["Loss payable endorsement", "6.12(b)", "Maya Chen", "July 7, 2026", "endorsement copy", "default after 3 BD cure", "Open"],
        ["IP schedule supplement", "4.4(c)", "Evan Brooks, GC", "July 14, 2026", "updated schedule", "post-closing default", "Open"],
        ["July compliance certificate", "Exhibit B", "Maya Chen", "August 21, 2026", "certify liquidity $3,500,000", "reporting default", "Open"],
        ["Fremont lease amendment", "Waiver letter", "Ops", "August 15, 2026", "signed lease amendment", "landlord waiver reinstated", "Open"],
    ]
    draw_table(d, 40, 260, [320, 145, 180, 205, 270, 260, 120], rows, 66)
    draw_section(d, 100, 775, "Counsel diary extract", w=1380)
    diary = [
        ["Date", "Matter", "Owner", "Follow-up note"],
        ["07/07", "Loss payable endorsement", "Maya Chen", "3 BD cure period starts if endorsement copy not received"],
        ["07/14", "IP schedule supplement", "Evan Brooks, GC", "Updated patent/trademark schedule to be attached to amendment binder"],
        ["08/15", "Fremont lease amendment", "Ops", "Landlord waiver reinstates if signed lease amendment is missing"],
        ["08/21", "July compliance certificate", "Maya Chen", "Must certify liquidity of $3,500,000 under Exhibit B"],
    ]
    draw_ledger(d, 100, 855, [140, 320, 210, 660], diary, 58)
    draw_section(d, 100, 1208, "Closing-room notes", w=1380)
    draw_text(
        d,
        (100, 1275),
        "Frost Bellwick: funding may proceed if Delaware UCC-3 filing receipt 2026-7741203 is attached to the final packet. Klein & Arroyo: borrower disputes the 3 business day cure for the insurance endorsement; business team accepted the dispute for closing, but the register remains open.",
        F["small"],
        fill="#111827",
        width=112,
        leading=31,
    )
    draw_text(
        d,
        (100, 1405),
        "Post-close coordinator note: do not close the loss payable endorsement, IP schedule supplement, July compliance certificate, or Fremont lease amendment until evidence is uploaded. All four rows remain open as of the circulated register.",
        F["small"],
        fill="#374151",
        width=112,
        leading=31,
    )
    pages.append(p8)

    p9 = base_page("Borrowing Base Certificate - June 2026")
    d = ImageDraw.Draw(p9)
    d.text((100, 150), "Submitted with closing. Parentheses are subtractions. Certificate controls collateral math as of 2026-06-28.", fill="#475569", font=F["small"])
    rows = [
        ["Line", "Collateral / reserve", "Gross", "Ineligible / reserve", "Advance rate", "Borrowing-base\nvalue", "Footnote"],
        ["1", "Eligible accounts receivable", "$9,842,300", "($1,184,600)", "85%", "$7,358,045", "excludes >90 day AR"],
        ["2", "Eligible inventory", "$4,612,000", "($736,000)", "50%", "$1,938,000", "cap applies below"],
        ["3", "Inventory cap", "", "", "", "($338,000)", "cap at $1.600M"],
        ["4", "Equipment pool", "$3,450,000", "($210,000)", "60%", "$1,944,000", "purchase-money liens excluded"],
        ["5", "Availability reserves", "", "($775,000)", "", "($775,000)", "tax + rent reserve"],
        ["6", "Gross borrowing base", "", "", "", "$10,127,045", "sum lines 1-5"],
        ["7", "Outstanding revolver", "", "", "", "($5,890,000)", "after cleanup payoff"],
        ["8", "Net availability", "", "", "", "$4,237,045", "controls funding condition"],
    ]
    draw_table(d, 35, 250, [80, 300, 165, 210, 150, 210, 315], rows, 74)
    draw_note(d, (90, 955, 760, 1205), "Footnote A", "AR from BrioHealth aged >90 days ($184,200) is excluded even though the customer appears in the sales ledger.", "#92400e")
    draw_note(d, (845, 955, 1515, 1205), "Certificate conflict", "Borrower draft model showed net availability $4,575,045 because it did not apply the inventory cap. This signed certificate controls.", "#991b1b")
    checkbox(d, 110, 1295, "Certificate signed by Maya Chen, CFO", True, F["small"])
    checkbox(d, 110, 1360, "Lender field review completed", True, F["small"])
    checkbox(d, 110, 1425, "Inventory cap waived", False, F["small"])
    pages.append(p9)

    p10 = base_page("Closing Email Transmittal and Counterpart Log")
    d = ImageDraw.Draw(p10)
    d.text((100, 150), "Email export plus signature counterpart tracker. Delivery status does not override executed terms.", fill="#475569", font=F["small"])
    email = (
        "From: Lena Ortiz <lortiz@frostbellwick.example>\n"
        "To: Project Helios closing group\n"
        "Sent: 2026-06-30 14:47 ET\n"
        "Subject: Project Helios - final closing set and remaining post-close items\n\n"
        "Attached are the executed Second Amendment, officer certificate, borrowing base certificate, funds-flow memo vFINAL, Delaware UCC-3 receipt, and post-closing undertakings register. "
        "Funding was released after 2:30 PM ET. Remaining open items are lender loss payable endorsement, IP schedule supplement, July compliance certificate, and Fremont lease amendment."
    )
    draw_text(d, (100, 245), email, F["tiny"], width=105, leading=27)
    rows = [
        ["Attachment", "Version / status", "Controls?"],
        ["Executed Second Amendment", "executed 2026-06-30", "yes for legal terms"],
        ["Blackline against v11", "comparison only", "no"],
        ["Borrowing Base Certificate", "signed 2026-06-28", "yes for collateral math"],
        ["Funds-flow memo", "vFINAL 2026-06-30 14:31 ET", "yes for net funding"],
        ["Delaware UCC-3 receipt", "2026-7741203", "yes for filing status"],
        ["Board deck excerpt", "not attached", "no"],
    ]
    draw_table(d, 70, 650, [430, 430, 280], rows, 66)
    draw_section(d, 70, 1150, "Counterpart signature tracker", w=1260)
    rows2 = [
        ["Party", "Counterpart received", "Signature status", "Note"],
        ["Northstar Robotics, Inc.", "yes", "signed by Maya Chen", "main signature page"],
        ["Northstar Automation Holdings LLC", "yes", "signed by Daniel Ruiz", "separate counterpart"],
        ["Meridian Bank, N.A.", "yes", "signed by S. Patel", "agent counterpart"],
        ["Fremont Landlord", "no", "blank", "waiver remains post-closing"],
    ]
    draw_table(d, 70, 1225, [340, 250, 320, 390], rows2, 68)
    draw_note(d, (100, 1620, 1510, 1785), "Transmittal source state", "The email confirms delivery and remaining open items only. It does not override executed amendment terms, the signed borrowing-base certificate, or the vFINAL funds-flow memo.", "#1d4ed8")
    pages.append(p10)

    gold = """# Project Helios Closing Packet: Second Amendment to Loan and Security Agreement

## Closing Memo

Borrower: Northstar Robotics, Inc. Parent guarantor: Northstar Automation Holdings LLC. Agent/lender: Meridian Bank, N.A. Borrower counsel: Klein & Arroyo LLP. Lender counsel: Frost Bellwick LLP.

Original Loan and Security Agreement date: March 15, 2024. Amendment effective date: June 28, 2026. Closing/funding target: June 30, 2026. This is the Second Amendment.

The amendment increases the commitment from $18,500,000 to $27,000,000 through a new $8,500,000 Tranche B advance. The memo paragraph showing $3,250,000 liquidity is stale; the final liquidity covenant is $3,500,000. The authorized borrower signer includes Maya Chen, Chief Financial Officer.

Closing timeline: Original LSA 03/15/2024; First Amendment 11/22/2025; Board consent 06/24/2026; UCC search refresh 06/26/2026; target funding 06/30/2026.

Use of Tranche B proceeds: existing revolver payoff $3,200,000; equipment deposits $4,150,000; closing fees $685,000; working capital $465,000.

## Blackline Sections 1-3

Section 1 changes Commitment from deleted $18,500,000 to inserted $27,000,000.

Section 2 inserts a Tranche B Advance in the principal amount of $8,500,000, available only on the Closing Date.

Section 3 changes interest from deleted SOFR + 5.25% to inserted Adjusted Term SOFR + 5.75%. The SOFR floor is 2.00%; deleted borrower draft text referred to a SOFR floor of 1.50%. Comment C-14 from Frost Bellwick says to confirm the SOFR floor remains 2.00% because the borrower draft had 1.50%. A footnote says conforming changes are required in Exhibit B compliance certificate.

Rate bridge: SOFR floor 2.00%, spread 5.75%, default increment 2.00%, maximum default margin display 9.75%.

## Covenants and Fees

Section 4.2 changes the minimum liquidity covenant from deleted $3,250,000 to inserted $3,500,000, tested monthly beginning July 31, 2026.

Monthly ARR reporting is due 15 business days after month-end. Comment C-21 says the borrower requested 20 business days and that request was rejected.

Amendment fee is 0.75% of the incremental commitment: 0.75% x $8,500,000 = $63,750. The unused line fee is 0.35% per annum. The exit fee is 1.25% of aggregate commitments. Comment C-19 says the checklist still shows 1.00% amendment fee and must be updated before funding. The margin fee table showing 1.00% / $85,000 is stale; body text controls.

Exhibit B covenant summary: liquidity final covenant $3.50M unrestricted cash versus prior $3.25M; ARR package due 15 business days while 20 business days was rejected; insurance endorsement has a 5 business day cure and remains a post-closing open item; IP schedule supplement is due within 10 business days and remains a post-closing open item.

## Signature Packet and Certificates

Executed signature blocks:

| Party | Signer | Title | Date |
| --- | --- | --- | --- |
| Northstar Robotics, Inc. | Maya Chen | Chief Financial Officer | June 30, 2026 |
| Northstar Automation Holdings LLC | Daniel Ruiz | President | June 30, 2026 |
| Meridian Bank, N.A. | S. Patel | Authorized Officer | June 30, 2026 |

Officer certificate: Maya Chen is the duly appointed Chief Financial Officer and is authorized to execute the Amendment. Board consent dated June 24, 2026 says either Priya Raman, Chief Executive Officer, or Maya Chen, Chief Financial Officer, may execute. Approval stamp: Approved for Release - Frost Bellwick LLP - 06/30/26 9:12 AM ET. Notary venue is San Mateo County, California, while the certificate address block lists Austin, Texas.

## Closing Checklist

Funding conditions are 12/13 complete; post-closing items are 3/7 complete.

| Item | Responsible | Status | Before funding? | Evidence | Comments |
| --- | --- | --- | --- | --- | --- |
| Executed Amendment | Klein | Complete | Yes | DocuSign 8274-6119 | |
| Officer Certificate | Borrower | Complete | Yes | OC-Helios-063026.pdf | |
| Board Consent | Borrower | Complete | Yes | Minutes extract 06/24/26 | |
| Good standing Delaware | Klein | Complete | Yes | cert 7381194 / 06/25/26 | |
| UCC-3 amendment Delaware | Frost | Pending on checklist | Yes | awaiting receipt | later exhibit shows filed |
| Insurance endorsement | Borrower | Post-closing | No | due 07/07/26 | loss payable |
| IP schedule supplement | GC | Post-closing | No | due 07/14/26 | |
| Landlord waiver, Fremont | Ops | Waived | No | waiver letter | expires if lease amendment not delivered by 08/15/26 |

The checklist values saying amendment fee $85,000 and Delaware UCC-3 pending are stale where later funds-flow and lien evidence conflict with them.

## Funds Flow and Escrow Instructions

Incoming Tranche B advance: $8,500,000. Wire from Meridian Bank escrow account ending 4412 to Northstar Robotics operating account at Pacific Commercial Bank ending 9081. Funding date: June 30, 2026.

| Deduction | Amount |
| --- | ---: |
| Amendment fee | $63,750 |
| Lender counsel fees | $188,400 |
| Borrower counsel fees paid from proceeds | $142,600 |
| UCC/search/filing charges | $18,000 |
| Existing revolver cleanup payoff | $336,000 |
| Net borrower proceeds | $7,751,250 |

Waterfall: $8.500M gross, -$0.064M amendment fee, -$0.188M lender counsel, -$0.143M borrower counsel, -$0.018M filings, -$0.336M payoff, $7.751M net.

The small confirmation box saying borrower account ending 9801 is not final; the main wire instruction controls with account ending 9081. Instruction paragraph says release no later than 2:00 PM Eastern, while footer approval says release approved after 2:30 PM Eastern.

## UCC / Lien / Insurance / IP Exhibit

| Search / filing | Result |
| --- | --- |
| Delaware original UCC-1 | file no. 2024-1459821, filed 03/18/2024 |
| Delaware UCC-3 amendment | file no. 2026-7741203, filed 06/29/2026 4:41 PM ET |
| California fixture filing search | No active fixture filings found |
| Texas SOS search | terminated file 23-8841107; Vector Equipment Finance LLC; terminated 05/09/2025 |

Priority stack: 1. Meridian Bank blanket lien; 2. permitted purchase-money equipment lien capped at $900,000; 3. statutory liens not yet due; 4. excluded Fremont landlord interest.

Insurance: cyber liability $5,000,000; general liability $2,000,000 per occurrence; property coverage $18,200,000; missing lender loss payable endorsement due 07/07/2026.

IP: patent application US 18/771,204, "Robotic Arm Calibration Using Visual Feedback"; trademark NORTHSTAR ORBIT serial 98441120; IP supplement due 07/14/2026.

The Delaware UCC-3 status is filed, not pending, because this exhibit shows filing receipt 2026-7741203.

## Post-Closing Undertakings and Exceptions Register

| Obligation | Source | Owner | Due date | Evidence required | Consequence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Deliver lender loss payable endorsement | 6.12(b) | Maya Chen | July 7, 2026 | endorsement copy | default after 3 business day cure | Open |
| Deliver IP schedule supplement | 4.4(c) | Evan Brooks, GC | July 14, 2026 | updated schedule | post-closing default | Open |
| Provide July compliance certificate | Exhibit B | Maya Chen | August 21, 2026 | certify liquidity $3,500,000 | reporting default | Open |
| Deliver Fremont lease amendment | Waiver letter | Ops | August 15, 2026 | signed lease amendment | landlord waiver condition reinstated | Open |

Counsel diary due dates: Insurance/loss payable endorsement 07/07, IP schedule supplement 07/14, Fremont lease amendment 08/15, July compliance certificate 08/21. Frost Bellwick note: funding may proceed if Delaware UCC-3 filing receipt 2026-7741203 is attached to final packet. Klein & Arroyo note: borrower disputes 3 BD cure for insurance endorsement; business team accepted for closing. The four post-close rows remain open until evidence is uploaded.

## Borrowing Base Certificate - June 2026

The borrowing base certificate is submitted with closing and controls collateral math as of 2026-06-28. Parentheses are subtractions.

| Line | Collateral / reserve | Gross | Ineligible / reserve | Advance rate | Borrowing-base value | Footnote |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | Eligible accounts receivable | $9,842,300 | ($1,184,600) | 85% | $7,358,045 | excludes >90 day AR |
| 2 | Eligible inventory | $4,612,000 | ($736,000) | 50% | $1,938,000 | cap applies below |
| 3 | Inventory cap | | | | ($338,000) | cap at $1.600M |
| 4 | Equipment pool | $3,450,000 | ($210,000) | 60% | $1,944,000 | purchase-money liens excluded |
| 5 | Availability reserves | | ($775,000) | | ($775,000) | tax + rent reserve |
| 6 | Gross borrowing base | | | | $10,127,045 | sum lines 1-5 |
| 7 | Outstanding revolver | | | | ($5,890,000) | after cleanup payoff |
| 8 | Net availability | | | | $4,237,045 | controls funding condition |

Footnote A: AR from BrioHealth aged more than 90 days ($184,200) is excluded even though the customer appears in the sales ledger. The borrower draft model showed net availability $4,575,045 because it did not apply the inventory cap; the signed certificate controls. Certificate signed by Maya Chen, CFO is checked. Lender field review completed is checked. Inventory cap waived is unchecked.

## Closing Email Transmittal and Counterpart Log

Email from Lena Ortiz to the Project Helios closing group was sent 2026-06-30 14:47 ET with subject "Project Helios - final closing set and remaining post-close items." It states that the executed Second Amendment, officer certificate, borrowing base certificate, funds-flow memo vFINAL, Delaware UCC-3 receipt, and post-closing undertakings register are attached. Funding was released after 2:30 PM ET. Remaining open items are lender loss payable endorsement, IP schedule supplement, July compliance certificate, and Fremont lease amendment.

| Attachment | Version / status | Controls? |
| --- | --- | --- |
| Executed Second Amendment | executed 2026-06-30 | yes for legal terms |
| Blackline against v11 | comparison only | no |
| Borrowing Base Certificate | signed 2026-06-28 | yes for collateral math |
| Funds-flow memo | vFINAL 2026-06-30 14:31 ET | yes for net funding |
| Delaware UCC-3 receipt | 2026-7741203 | yes for filing status |
| Board deck excerpt | not attached | no |

Counterpart tracker: Northstar Robotics received and signed by Maya Chen on the main signature page; Northstar Automation Holdings LLC received and signed by Daniel Ruiz by separate counterpart; Meridian Bank received and signed by S. Patel as agent counterpart; Fremont Landlord counterpart is not received and remains blank, so the waiver remains post-closing.

The email confirms delivery and remaining open items only. It does not override executed amendment terms, the signed borrowing-base certificate, or the vFINAL funds-flow memo.
"""

    return Case(
        "P09-loan-amendment-closing",
        "Loan Amendment Closing Packet",
        "legal",
        ["multi-page", "legal", "redline", "finance", "source-precedence", "signatures", "ucc", "post-closing"],
        "Stress a realistic legal closing packet with dense text, redlines, stale checklist values, funds flow, lien evidence, signatures, and post-closing obligations.",
        "Ten-page raster-heavy legal packet with extractable memo overlays, redline pages, tables, charts, stamps, certificates, transmittal email, and conflicting source states.",
        ["closing memo", "redlines", "covenants", "fees", "signatures", "checklist", "funds flow", "UCC exhibit", "undertakings"],
        ["Preserve deleted and inserted text distinctly.", "Use final executed/funds-flow/lien evidence over stale checklist values.", "Bind amounts, dates, parties, and obligations to the right source sections."],
        gold,
        [near_check("p09-amendment-fee", "finance", ["0.75%", "$8,500,000", "$63,750"], 5, 520)],
        pages,
        facts=[
            fact("p09.parties", "text", 4, "Borrower Northstar Robotics, Inc.; parent guarantor Northstar Automation Holdings LLC; agent/lender Meridian Bank, N.A.; counsel Klein & Arroyo LLP and Frost Bellwick LLP."),
            fact("p09.dates.facility", "text", 6, "Original LSA March 15, 2024; effective date June 28, 2026; funding/closing June 30, 2026; prior commitment $18,500,000; amended commitment $27,000,000; Tranche B $8,500,000."),
            fact("p09.redline.commitment", "redline", 5, "Blackline preserves deleted $18,500,000 and inserted $27,000,000 for Commitment."),
            fact("p09.redline.interest", "redline", 6, "Interest changes from deleted SOFR + 5.25% to inserted Adjusted Term SOFR + 5.75%; SOFR floor final is 2.00%, not deleted 1.50%; C-14 is preserved."),
            fact("p09.redline.visible.state", "redline", 14, "Visible revision state is represented across the blackline pages: deleted values remain marked as deleted, inserted values remain marked as inserted, and margin comments C-14, C-19, C-21, footnote, and stale margin fee table are attached to their relevant clauses. A clean final-term summary without visible deleted/inserted/comment state is not correct.", modality="redline", severity="critical"),
            fact("p09.liquidity", "source_state", 6, "Final minimum liquidity covenant is $3,500,000, tested monthly from July 31, 2026; $3,250,000 is deleted/stale."),
            fact("p09.reporting", "text", 4, "Monthly ARR reporting is due 15 business days after month-end; 20 business days request was rejected."),
            fact("p09.fees", "source_state", 7, "Final amendment fee is 0.75% x $8,500,000 = $63,750; unused line fee 0.35% per annum; exit fee 1.25%; stale 1.00%/$85,000 checklist/margin fee value is not final."),
            fact("p09.signature", "source_state", 6, "Maya Chen, CFO, signed for Northstar Robotics on June 30, 2026 and is authorized by officer certificate and board consent; checklist saying Priya Raman CEO only is stale/wrong."),
            fact("p09.checklist", "table_cell", 5, "Checklist preserves DocuSign 8274-6119, officer certificate OC-Helios-063026.pdf, board consent 06/24/26, Delaware good standing cert 7381194 dated 06/25/26, post-closing insurance due 07/07/26, IP due 07/14/26, Fremont waiver expiry 08/15/26."),
            fact("p09.funds.flow", "table_cell", 7, "Funds flow preserves $8,500,000 incoming, deductions $63,750, $188,400, $142,600, $18,000, $336,000, and net borrower proceeds $7,751,250."),
            fact("p09.account", "source_state", 5, "Borrower operating account ending is 9081, not conflicting 9801; escrow account ends 4412."),
            fact("p09.ucc", "source_state", 7, "Delaware UCC-3 status is filed with file no. 2026-7741203 on 06/29/2026 4:41 PM ET, overriding checklist pending status; original UCC-1 is 2024-1459821."),
            fact("p09.insurance.ip", "table_cell", 5, "Insurance values: cyber $5,000,000, GL $2,000,000 per occurrence, property $18,200,000, missing lender loss payable endorsement due 07/07/2026; patent US 18/771,204 and trademark NORTHSTAR ORBIT serial 98441120; IP supplement due 07/14/2026."),
            fact("p09.undertakings", "table_cell", 7, "Post-closing register preserves insurance endorsement 6.12(b)/Maya Chen/July 7/default after 3 BD cure; IP supplement 4.4(c)/Evan Brooks/July 14; July compliance certificate Exhibit B/August 21/certify $3,500,000 liquidity; Fremont lease amendment/August 15/waiver reinstated."),
            fact("p09.counsel.notes", "text", 4, "Frost Bellwick note allows funding if UCC-3 receipt 2026-7741203 attached; Klein & Arroyo note says borrower disputes 3 BD cure but business team accepted."),
            fact("p09.borrowing.base", "table_cell", 12, "Borrowing base certificate preserves all eight lines, gross values, ineligible/reserve amounts in parentheses, advance rates, borrowing-base values, footnotes, gross borrowing base $10,127,045, outstanding revolver ($5,890,000), and net availability $4,237,045.", modality="table", severity="critical"),
            fact("p09.borrowing.source_state", "source_state", 8, "Signed borrowing base certificate controls collateral math as of 2026-06-28; borrower draft model net availability $4,575,045 is wrong because it omitted the inventory cap; inventory cap waived is unchecked.", modality="source-precedence", severity="critical"),
            fact("p09.transmittal", "source_state", 8, "Closing email sent 2026-06-30 14:47 ET confirms attachments, funding after 2:30 PM ET, and remaining open items, but does not override executed amendment, signed borrowing-base certificate, or vFINAL funds-flow memo.", modality="source-precedence", severity="major"),
            fact("p09.counterparts", "form_state", 7, "Counterpart tracker preserves Northstar Robotics/Maya Chen, Northstar Automation/Daniel Ruiz, Meridian Bank/S. Patel as received/signed and Fremont Landlord not received/blank with waiver post-closing.", modality="form", severity="major"),
            fact("p09.exact.docusign", "exact_field", 7, "Executed Amendment evidence ID is exactly DocuSign 8274-6119. Any other DocuSign number is incorrect.", modality="text", severity="critical"),
            fact("p09.exact.ucc3.timestamp", "exact_field", 8, "Delaware UCC-3 amendment filing is exactly file no. 2026-7741203 filed 06/29/2026 4:41 PM ET. Wrong date, year, or time is incorrect even if a later note has the right value.", modality="text", severity="critical"),
            fact("p09.exact.borrowing.ar", "exact_field", 7, "Borrowing-base line 1 value is exactly $7,358,045 for eligible accounts receivable. $7,368,045 or any other value is incorrect.", modality="table", severity="critical"),
            fact("p09.exact.reserve.row", "exact_field", 7, "Borrowing-base line 5 has availability reserves with ineligible/reserve ($775,000), blank advance rate, borrowing-base value ($775,000), and footnote tax + rent reserve.", modality="table", severity="critical"),
            fact("p09.exact.trademark", "exact_field", 6, "Trademark is exactly NORTHSTAR ORBIT serial 98441120. NORTHSTAR ROBOT, NORTHSTAR ROBOT?, or 'series#' is incorrect.", modality="text", severity="major"),
            fact("p09.exact.counterpart.blank", "exact_field", 5, "Fremont Landlord counterpart is not received and signature status is blank; wording that implies a signed, received, or merely plural 'blanks' state is not fully correct.", modality="form", severity="major"),
            fact("p09.page_order", "structure", 4, "Output preserves packet order: closing memo, blackline, covenants/fees, signature packet, checklist, funds flow, UCC/lien/IP exhibit, post-closing register, borrowing base certificate, closing transmittal/counterpart log."),
        ],
        extractable_text_pages=[
            overlays(["Project Helios Closing Packet", "Northstar Robotics, Inc.", "Meridian Bank, N.A.", "Facility $27,000,000"], 100, 110),
            [],
            [],
            overlays(["Approved for Release - Frost Bellwick LLP - 06/30/26 9:12 AM ET"], 100, 1250),
            [],
            overlays(["Borrower account ending 9081", "Net borrower proceeds $7,751,250"], 100, 230),
            [],
            [],
        ],
    )


def packet_library_permit() -> Case:
    pages: list[Image.Image] = []
    footer = "RCL-FAC-26-0418 | Permit Packet | Not for Construction until AHJ Approval"

    def stamp(d: ImageDraw.ImageDraw, x: int, y: int, text: str, color: str = "#991b1b") -> None:
        d.rectangle((x, y, x + 420, y + 90), outline=color, width=4)
        d.text((x + 18, y + 20), text, fill=color, font=F["small_bold"])

    def page(title: str, subtitle: str = "") -> Image.Image:
        img = base_page(title)
        dd = ImageDraw.Draw(img)
        if subtitle:
            dd.text((100, 138), subtitle, fill="#475569", font=F["small"])
        dd.text((100, 2050), footer, fill="#64748b", font=F["tiny"])
        dd.line((100, 2026, 1580, 2026), fill="#cbd5e1", width=1)
        return img

    p1 = page("Riverside Community Library - Facilities Permit Packet", "Permit Application + Intake Cover | Rev 2 resubmittal 2026-06-11")
    d = ImageDraw.Draw(p1)
    stamp(d, 1030, 205, "RECEIVED JUN 12 2026\nBUILDING SAFETY")
    draw_kv_band(
        d,
        92,
        320,
        [
            ("Permit no.", "PR-26-18422"),
            ("Parcel", "073W22AB-04400"),
            ("Zoning", "PS - Public Service"),
            ("Occupancy", "A-3 Library"),
            ("Type", "II-B"),
        ],
        [240, 300, 320, 260, 170],
    )
    rows = [
        ["Field", "Application value", "Reviewer / intake mark"],
        ["Applicant / GC", "Northbank Builders LLC | CCB 218774 | (503) 555-0186", "accepted"],
        ["Owner", "City of Salem Facilities Division", "municipal"],
        ["Scope", "Replace 4 rooftop units; restroom accessibility upgrades; breakroom sink relocation", "Verify: submittal shows 5 RTUs?"],
        ["Work area", "3,860 sq ft", "matches code matrix"],
        ["Construction valuation", "$486,750", "CO-02 later revises contract to $512,430"],
        ["Sprinklered", "Yes - NFPA 13", "fire review routed"],
        ["Structural work", "No structural work checked", "roof curb detail appears later"],
    ]
    draw_table(d, 70, 500, [270, 690, 430], rows, 70)
    d.text((1040, 1085), "Review routing", fill="#111827", font=F["h2"])
    for i, (label, checked) in enumerate([("Building", True), ("Fire", True), ("Mechanical", True), ("Electrical", True), ("Plumbing", True), ("Planning", False)]):
        checkbox(d, 1045, 1143 + i * 48, label, checked, F["tiny"])
    draw_section(d, 90, 1090, "Requested inspections", w=830)
    draw_text(d, (90, 1145), "framing above ceiling; mechanical final; electrical rough-in; plumbing final; accessibility final.", F["small"], width=62, leading=30)
    draw_section(d, 90, 1325, "Mini fee bar", w=830)
    fees = [("Plan Review", 2840, "#64748b"), ("MEP", 1615, "#2563eb"), ("Technology Fee", 145, "#c2410c")]
    bx, by = 115, 1415
    for label, amt, color in fees:
        w = max(45, int(amt / 6))
        d.rectangle((bx, by, bx + w, by + 52), fill=color)
        d.text((bx, by + 68), f"{label} ${amt}", fill="#111827", font=F["tiny"])
        bx += w + 14
    draw_note(d, (1030, 1490, 1560, 1715), "Intake conflict", "Typed scope says 4 rooftop units. Reviewer note asks whether submittal shows 5 RTUs. Do not collapse this into a single final count.", "#92400e")
    pages.append(p1)

    p2 = page("Code Summary + Occupant Load / Egress Plan", "Dense code matrix with embedded egress plan and photo placard")
    d = ImageDraw.Draw(p2)
    rows = [
        ["Area / item", "Factor", "Calculation", "Occupants / value"],
        ["Building gross area", "", "", "18,240 sq ft"],
        ["Permit work area", "", "", "3,860 sq ft"],
        ["Community meeting room", "15 net", "1,185 sq ft / 15", "79 occupants"],
        ["Reading room affected area", "50 gross", "1,420 sq ft / 50", "29 occupants"],
        ["Staff/break/admin", "150 gross", "610 sq ft / 150", "5 occupants"],
        ["Restrooms/circulation/mech", "accessory", "645 sq ft", "not counted"],
        ["Calculated subtotal", "", "", "113 occupants"],
        ["Existing posted placard", "photo inset", "", "92 occupants"],
        ["Common path / travel", "", "48 ft / 137 ft", "2 exits req; 3 provided"],
        ["Door widths", "", "Door 103 = 34 in; Door 117 = 32 in", "maintain route"],
    ]
    draw_table(d, 65, 235, [245, 125, 285, 190], rows, 58)
    # Egress plan
    d.rectangle((1015, 245, 1585, 980), outline="#111827", width=4)
    for x in [1195, 1390]:
        d.line((x, 245, x, 980), fill="#111827", width=2)
    d.line((1015, 580, 1585, 580), fill="#111827", width=2)
    d.text((1050, 370), "Meeting", fill="#111827", font=F["tiny_bold"])
    d.text((1232, 370), "Reading", fill="#111827", font=F["tiny_bold"])
    d.text((1430, 370), "Stacks", fill="#111827", font=F["tiny_bold"])
    d.line((1070, 790, 1530, 300), fill="#2563eb", width=5)
    d.line((1240, 900, 1530, 900), fill="#0f766e", width=5)
    d.polygon([(1530, 300), (1508, 306), (1524, 325)], fill="#2563eb")
    d.polygon([(1530, 900), (1510, 888), (1510, 912)], fill="#0f766e")
    d.text((1025, 1015), "Common path 48 ft; exit access 137 ft.", fill="#111827", font=F["tiny"])
    draw_note(d, (980, 1115, 1570, 1300), "Fire marshal", "OL calc must include community room storage overflow. Cover note 'no change to occupant load' conflicts with calculated OL=113 and placard=92.", "#991b1b")
    # occupant pie/donut approximation
    d.ellipse((160, 1095, 385, 1320), outline="#111827", width=2)
    d.pieslice((160, 1095, 385, 1320), 0, 252, fill="#2563eb")
    d.pieslice((160, 1095, 385, 1320), 252, 346, fill="#0f766e")
    d.pieslice((160, 1095, 385, 1320), 346, 360, fill="#c2410c")
    d.text((225, 1180), "OL=113", fill="white", font=F["small_bold"])
    d.text((430, 1135), "Meeting 70% | Reading 26% | Staff 4%", fill="#111827", font=F["small"])
    d.text((90, 1445), "Accessibility note: Maintain 44 in min accessible route except at existing stacks pinch point noted.", fill="#7f1d1d", font=F["small"])
    pages.append(p2)

    p3 = page("Site Plan / Logistics / Fire Access", "Plan overlay with fire lane, crane pick zone, utility callouts, and hydrant conflict")
    d = ImageDraw.Draw(p3)
    d.text((100, 210), "Scale: 1\" = 30'-0\". North arrow points 18 degrees west of sheet up.", fill="#475569", font=F["small"])
    d.rectangle((120, 300, 1240, 1250), fill="#f8fafc", outline="#111827", width=4)
    d.rectangle((470, 520, 900, 900), fill="#e5e7eb", outline="#111827", width=3)
    d.text((560, 680), "LIBRARY", fill="#111827", font=F["h2"])
    d.rectangle((150, 1030, 1180, 1125), fill="#fee2e2", outline="#991b1b", width=3)
    d.text((170, 1060), "Fire lane 26 ft provided (20 ft minimum required)", fill="#991b1b", font=F["small"])
    d.rectangle((925, 330, 1135, 500), fill="#fef3c7", outline="#92400e", width=3)
    d.text((940, 380), "Crane pick\n42 ft x 28 ft\n07/08-07/10", fill="#111827", font=F["tiny"])
    d.rectangle((210, 330, 330, 430), fill="#e2e8f0", outline="#111827", width=2)
    d.text((212, 445), "20 yd roll-off", fill="#111827", font=F["tiny"])
    d.ellipse((360, 345, 390, 375), fill="#dc2626")
    d.text((393, 345), "H-2", fill="#dc2626", font=F["tiny_bold"])
    d.line((330, 380, 360, 360), fill="#111827", width=2)
    d.text((305, 386), "16'-0\"", fill="#111827", font=F["tiny_bold"])
    d.text((170, 1180), "Blue dashed route: ADA temporary route 48 in min. East entry remains open per plan.", fill="#1d4ed8", font=F["small"])
    d.line((820, 905, 1120, 1170), fill="#2563eb", width=4)
    for off in range(0, 300, 34):
        d.line((820 + off, 905 + int(off * .88), 835 + off, 918 + int(off * .88)), fill="white", width=2)
    draw_note(d, (1300, 310, 1580, 520), "Utilities", "Gas shutoff: south wall, grid C/2. Electrical service: 800A, 120/208V, 3-phase.", "#1d4ed8")
    draw_note(d, (1300, 570, 1580, 780), "Work hours", "7:00 AM - 5:30 PM weekdays. Public entrance to remain open: East entry only.", "#334155")
    draw_note(d, (1300, 830, 1580, 1070), "Conflict", "Fire access markup says do not stage within 20 ft of hydrant. Dimension string shows dumpster 16 ft from H-2.", "#991b1b")
    draw_note(d, (1300, 1125, 1580, 1350), "Site quantities", "Fence 146 LF. Staging area 1,120 sq ft. Tree protection 12 ft radius around oak T-3.", "#0f766e")
    pages.append(p3)

    p4 = page("A2.1 Enlarged Floor Plan / Restroom + Breakroom Alteration", "Architectural plan with RFI references, fixture schedule, and accessibility conflicts")
    d = ImageDraw.Draw(p4)
    plan_x, plan_y, plan_w, plan_h = 90, 250, 1090, 1120
    p4.paste(cad_floorplan_crop(plan_w, plan_h), (plan_x, plan_y))
    d.rectangle((plan_x, plan_y, plan_x + plan_w, plan_y + plan_h), outline="#1e3a8a", width=3)
    label_boxes = [
        ("112 Women RR", 155, 470, "#111827"),
        ("113 Men RR", 455, 470, "#111827"),
        ("114 Single-user RR", 695, 485, "#111827"),
        ("118 Staff Break", 720, 815, "#111827"),
        ("Stacks pinch point 39 in", 185, 1015, "#7f1d1d"),
    ]
    for label, x, y, color in label_boxes:
        d.rounded_rectangle((x - 8, y - 8, x + 230, y + 32), radius=5, fill="#ffffff", outline="#cbd5e1", width=1)
        d.text((x, y), label, fill=color, font=F["tiny_bold"])
    d.ellipse((705, 785, 865, 945), outline="#2563eb", width=4)
    d.rounded_rectangle((705, 958, 900, 996), radius=5, fill="#eff6ff", outline="#bfdbfe", width=1)
    d.text((718, 966), "60 in turning circle", fill="#2563eb", font=F["tiny_bold"])
    d.line((640, 420, 820, 420), fill="#1e40af", width=3)
    d.line((640, 408, 640, 432), fill="#1e40af", width=2)
    d.line((820, 408, 820, 432), fill="#1e40af", width=2)
    d.rounded_rectangle((658, 378, 810, 415), radius=5, fill="#ffffff", outline="#cbd5e1", width=1)
    d.text((668, 386), "chase 2'-8\"", fill="#111827", font=F["tiny_bold"])
    d.rounded_rectangle((910, 500, 1110, 565), radius=5, fill="#ffffff", outline="#cbd5e1", width=1)
    d.text((922, 510), "WC CL 17 in", fill="#111827", font=F["tiny"])
    d.text((922, 538), "Lav CL 18 in", fill="#111827", font=F["tiny"])
    d.rectangle((540, 955, 780, 1048), outline="#0f766e", width=4)
    d.line((540, 955, 780, 1048), fill="#0f766e", width=2)
    d.line((540, 1048, 780, 955), fill="#0f766e", width=2)
    d.rounded_rectangle((540, 1060, 805, 1098), radius=5, fill="#ecfdf5", outline="#bbf7d0", width=1)
    d.text((552, 1068), "sink moved 6'-4\" east", fill="#0f766e", font=F["tiny_bold"])
    d.text((1220, 250), "Fixture / wall schedule", fill="#111827", font=F["h2"])
    rows = [
        ["Tag", "Value"],
        ["W3", "3 5/8 in metal stud; 5/8 in GWB each side"],
        ["Door 114", "34 in clear width"],
        ["Rear grab bar", "36 in"],
        ["Side grab bar", "42 in"],
        ["Casework C-12", "8'-6\" length"],
    ]
    draw_table(d, 1220, 310, [120, 320], rows, 56)
    draw_note(d, (1220, 760, 1570, 980), "RFI-07", "Revises chase from 2'-8\" to 3'-2\"; maintain 60\" turning circle; shift lav 4\" east.", "#991b1b")
    draw_note(d, (1220, 1040, 1570, 1260), "Existing condition", "Stacks aisle pinch point is 39 in clear, tagged EXISTING NONCONFORMING - DO NOT REDUCE.", "#92400e")
    pages.append(p4)

    p5 = page("M1.3 / E1.2 Mechanical + Electrical Coordination Overlay", "RTU schedule, electrical breakers, duct notes, reviewer stamp, and curb conflict")
    d = ImageDraw.Draw(p5)
    d.text((100, 205), "Overlay sheet combines rooftop equipment, reflected ceiling access, disconnects, smoke detector tie-ins, and panel schedule fragments.", fill="#475569", font=F["small"])
    rows = [
        ["Equip", "Tons", "Serves", "MCA", "MOCP", "Breaker"],
        ["RTU-1", "7.5", "Reading Room", "38A", "50A", "2P-50"],
        ["RTU-2", "5", "Staff/Admin", "27A", "35A", "2P-35"],
        ["RTU-3", "10", "Community Room", "52A", "70A", "2P-70"],
        ["RTU-4", "3", "Restrooms/Storage", "18A", "25A", "2P-25"],
        ["Total scheduled", "25.5", "", "", "", ""],
    ]
    draw_table(d, 65, 280, [150, 120, 300, 130, 140, 150], rows, 66)
    stamp(d, 1080, 405, "REVIEW\nFIELD VERIFY", "#991b1b")
    d.rectangle((80, 850, 1010, 1320), fill="#f8fbff", outline="#1e3a8a", width=3)
    for gx in range(120, 1000, 80):
        d.line((gx, 850, gx, 1320), fill="#dbeafe", width=1)
    for gy in range(890, 1300, 70):
        d.line((80, gy, 1010, gy), fill="#dbeafe", width=1)
    d.rectangle((145, 925, 925, 982), outline="#64748b", width=5)
    d.text((410, 936), "EXISTING BEAM B-4", fill="#64748b", font=F["tiny_bold"])
    for x in [160, 315, 470, 625, 780]:
        d.line((x, 1110, x + 105, 1110), fill="#0f766e", width=5)
        d.line((x + 105, 1110, x + 105, 1245), fill="#0f766e", width=5)
        d.rectangle((x + 82, 1230, x + 128, 1276), outline="#0f766e", width=3)
    d.rectangle((255, 1015, 330, 1090), outline="#1d4ed8", width=4)
    d.text((266, 1036), "AP-7", fill="#1d4ed8", font=F["tiny_bold"])
    d.text((255, 1060), "24\"x24\"", fill="#1d4ed8", font=F["tiny"])
    d.text((120, 870), "10 in clear below beam B-4", fill="#111827", font=F["tiny_bold"])
    d.text((120, 990), "Condensate slope 1/8\" per ft min", fill="#111827", font=F["tiny"])
    d.text((545, 1010), "Smoke detector tie-in: FACP zone 4", fill="#111827", font=F["tiny"])
    draw_note(d, (1110, 850, 1570, 1070), "Curb openings", "Mechanical C-3 opening: 54\" x 78\". Structural curb detail / CO-02 later requires 58\" x 80\".", "#991b1b")
    draw_note(d, (1110, 1135, 1570, 1375), "Schedule state", "This sheet lists 4 RTUs totaling 25.5 tons. Do not add ERV-1 to the original mechanical schedule; CO-02 adds it later.", "#92400e")
    pages.append(p5)

    p6 = page("RFI Log + Selected RFI Responses", "Layered scanned-email cards with handwritten field note")
    d = ImageDraw.Draw(p6)
    rows = [
        ["RFI", "Submitted", "Subject", "Formal status", "Impact"],
        ["RFI-07", "2026-06-03", "Restroom chase cleanout conflict", "Answered 06/06", "cost potential; 0 days"],
        ["RFI-08", "2026-06-04", "Beam B-4 duct clearance", "Answered 06/09", "1 day"],
        ["RFI-09", "2026-06-07", "East entry closure during crane pick", "Answered 06/10", "permit yes"],
        ["RFI-10", "2026-06-08", "RTU-3 capacity over basis", "Pending in log", "see blue note"],
    ]
    draw_table(d, 50, 245, [120, 170, 380, 220, 240], rows, 70)
    draw_note(d, (90, 725, 650, 980), "RFI-07 architect response", "Cleanout conflicts with 2'-8\" chase shown on A2.1. Response dated 2026-06-06: revise chase to 3'-2\", maintain 60\" turning circle in Room 114, and shift lav 4\" east.", "#0f766e")
    draw_note(d, (725, 725, 1290, 980), "RFI-08 architect response", "Flatten duct to 12\" x 34\" for a 9'-0\" run below existing beam B-4. Maintain 350 CFM branch to diffuser D-7.", "#92400e")
    draw_note(d, (90, 1050, 650, 1295), "RFI-09 logistics response", "Use west entry during crane pick only. Provide 48\" temporary accessible route and signage. Logistics plan clouded for permit review.", "#991b1b")
    draw_note(d, (725, 1050, 1290, 1295), "Blue field note", "RFI-10 resolved by CO-02, see 6/18 email. Formal log on this page still says pending.", "#1d4ed8")
    draw_section(d, 120, 1410, "Impact matrix chips", w=1040)
    for i, (name, color) in enumerate([("cost potential", "#fef3c7"), ("schedule 1 day", "#fee2e2"), ("permit yes", "#dbeafe"), ("inspection note", "#ecfeff")]):
        x = 130 + i * 260
        d.rectangle((x, 1495, x + 210, 1555), fill=color, outline="#111827", width=2)
        d.text((x + 14, 1513), name, fill="#111827", font=F["tiny_bold"])
    pages.append(p6)

    p7 = page("Change Order CO-02 + Cost / Schedule Summary", "Formal CO with signatures, waterfall, schedule strip, and backup quote conflict")
    d = ImageDraw.Draw(p7)
    rows = [
        ["Field", "Value"],
        ["Change order", "CO-02 dated 2026-06-18"],
        ["Original contract", "$486,750"],
        ["Prior approved changes", "$0"],
        ["CO-02 amount", "$25,680"],
        ["Revised contract", "$512,430"],
        ["Original substantial completion", "2026-08-21"],
        ["Added days", "3 calendar days"],
        ["Revised substantial completion", "2026-08-24"],
    ]
    draw_table(d, 70, 245, [360, 420], rows, 66)
    draw_section(d, 890, 245, "CO scope", w=650)
    draw_text(d, (890, 300), "Upsize RTU-3 from 10 tons to 12.5 tons. Add ERV-1 with 450 CFM outside air. Modify curb C-3 to 58\" x 80\". Add electrical breaker 3P-80A in panel MDP.", F["small"], width=45, leading=30)
    draw_section(d, 890, 575, "Cost waterfall", w=650)
    co_costs = [("Mech equip", 14900, "#64748b"), ("Electrical", 4860, "#2563eb"), ("Roof/curb", 3420, "#0f766e"), ("OH&P", 2500, "#c2410c")]
    bx, by = 900, 675
    for label, amt, color in co_costs:
        d.rectangle((bx, by, bx + int(amt / 70), by + 42), fill=color)
        d.text((bx, by + 58), f"{label} ${amt:,}", fill="#111827", font=F["tiny"])
        by += 92
    draw_section(d, 70, 925, "Signatures", w=760)
    rows2 = [["Signer", "Role", "Date"], ["Dana Hu", "Owner Facilities Manager", "2026-06-19"], ["Leo Martinez", "Contractor", "2026-06-18"], ["Priya Soto", "Architect", "2026-06-20"]]
    draw_table(d, 70, 990, [220, 320, 190], rows2, 58)
    draw_note(d, (70, 1340, 790, 1560), "Schedule ambiguity", "CO-02 adds 3 calendar days. RFI-08 separately notes 1 day, but packet does not prove the days are additive.", "#92400e")
    stamp(d, 950, 1290, "OWNER APPROVED\nSUBJECT TO PERMIT REVIEWER ACCEPTANCE", "#0f766e")
    pages.append(p7)

    p8 = page("Photo Observation Sheet + Punch / Inspector Notes", "Six-photo grid with embedded tape dimensions, arrows, and inspector observations")
    d = ImageDraw.Draw(p8)
    photos = [
        ("Photo 1", "2026-06-27 08:42", "East entry staging condition", "36\" clear at door, not 48\"", "#dbeafe"),
        ("Photo 2", "2026-06-27 09:05", "Hydrant H-2 and dumpster", "16'-0\" tape; relocate before crane pick", "#e5e7eb"),
        ("Photo 3", "2026-06-28 13:18", "Room 114 chase mockup", "3'-2\"; RFI-07 incorporated", "#ecfeff"),
        ("Photo 4", "2026-06-28 14:10", "Existing stacks aisle", "39\"; existing nonconforming", "#f8fafc"),
        ("Photo 5", "2026-06-29 10:22", "Roof curb C-3 layout", "58\" x 80\"; matches CO-02, not M1.3", "#e0f2fe"),
        ("Photo 6", "2026-06-29 11:47", "Temporary west entry signage", "Accessible Entrance During Crane Pick July 8-10", "#fef3c7"),
    ]
    for i, (label, ts, cap, note, fill) in enumerate(photos):
        x = 80 + (i % 2) * 720
        y = 245 + (i // 2) * 360
        d.rectangle((x, y, x + 630, y + 300), fill=fill, outline="#111827", width=3)
        d.text((x + 16, y + 18), f"{label} | {ts}", fill="#111827", font=F["tiny_bold"])
        d.text((x + 16, y + 56), cap, fill="#111827", font=F["small_bold"])
        thumb = observation_photo(i, 594, 138)
        p8.paste(thumb, (x + 18, y + 92))
        d.rectangle((x + 18, y + 92, x + 612, y + 230), outline="#475569", width=1)
        d.rounded_rectangle((x + 14, y + 242, x + 616, y + 286), radius=6, fill="#fff7ed", outline="#f97316", width=1)
        draw_text(d, (x + 24, y + 252), note, F["tiny_bold"], fill="#991b1b", width=54, leading=18)
    draw_section(d, 80, 1390, "Inspector observations", w=1360)
    obs = [
        "OBS-14: East entry route shown on logistics plan not maintained on 06/27; corrected route required before public opening.",
        "OBS-15: Dumpster within 20 ft hydrant clearance; move minimum 4 ft west.",
        "OBS-16: Room 114 chase revised per RFI-07; verify turning circle after lav shift.",
        "OBS-17: Curb C-3 field layout follows CO-02; confirm permit resubmittal reflects structural opening.",
    ]
    draw_text(d, (80, 1450), "\n".join(obs), F["small"], width=100, leading=31)
    pages.append(p8)

    gold = """# Riverside Community Library - Facilities Permit Packet

Project address: 418 W Harbor Ave, Salem, OR 97301. Owner: City of Salem Facilities Division. Applicant/GC: Northbank Builders LLC. Architect: Kline + Soto Architects. Permit target: commercial alteration, no change of use. Drawing date: 2026-05-14. Revision set: Rev 2 / Permit Resubmittal / 2026-06-11.

## Permit Application + Intake Cover

Permit number PR-26-18422. Parcel 073W22AB-04400. Zoning PS - Public Service. Existing occupancy A-3 Library. Construction type II-B. Sprinklered: Yes - NFPA 13. Applicant Northbank Builders LLC, CCB 218774, phone (503) 555-0186.

Application work area is 3,860 sq ft. Application valuation is $486,750. Typed scope says replace 4 rooftop units, restroom accessibility upgrades, and breakroom sink relocation. Handwritten intake note asks: "Verify: submittal shows 5 RTUs?" Application checkbox says No structural work, but later roof curb detail and CO-02 show curb work.

Requested inspections: framing above ceiling, mechanical final, electrical rough-in, plumbing final, accessibility final. Review routing checked: Building, Fire, Mechanical, Electrical, Plumbing; Planning is unchecked.

## Code Summary + Egress

Building gross area is 18,240 sq ft and permit work area is 3,860 sq ft. Community meeting room is 1,185 sq ft at 15 net = 79 occupants. Reading room affected area is 1,420 sq ft at 50 gross = 29 occupants. Staff/break/admin area is 610 sq ft at 150 gross = 5 occupants. Restrooms/circulation/mechanical area is 645 sq ft accessory. Calculated occupant load subtotal is 113. Existing placard photo shows 92 occupants.

Longest common path is 48 ft. Longest exit access travel distance is 137 ft. Required exits from affected area: 2. Provided exits: 3. Door 103 clear width is 34 in. Door 117 clear width is 32 in. Accessibility note says maintain 44 in min accessible route except at existing stacks pinch point noted.

There is an unresolved conflict between cover wording saying no change to occupant load, the existing 92-person placard, the calculated 113-person occupant load, and the fire marshal comment requiring revision.

## Site Plan / Logistics / Fire Access

Scale is 1\" = 30'-0\". North arrow points 18 degrees west of sheet up. Fire lane provided is 26 ft, with 20 ft minimum required. Temporary construction fence is 146 linear ft. Dumpster is a 20 yd roll-off. Crane pick zone is 42 ft x 28 ft with crane window 2026-07-08 to 2026-07-10. Work hours are 7:00 AM - 5:30 PM weekdays. Site plan says public entrance remains open at East entry only. Temporary ADA route width is 48 in min. Staging area is 1,120 sq ft. Tree protection radius is 12 ft around oak T-3. Gas shutoff is south wall grid C/2. Electrical service is 800A, 120/208V, 3-phase.

Hydrant conflict: the fire access markup says do not stage within 20 ft of hydrant, but the plan dimension shows dumpster 16 ft from hydrant H-2.

## A2.1 Enlarged Floor Plan

Room 112 is Women RR, Room 113 is Men RR, Room 114 is Single-user RR, and Room 118 is Staff Break. New wall type W3 is 3 5/8 in metal stud with 5/8 in GWB each side. Plan shows restroom chase depth 2'-8\". RFI-07 revises chase to 3'-2\". Room 114 clear turning circle is 60 in diameter. Lavatory centerline on plan is 18 in from side wall. WC centerline is 17 in from side wall. Rear grab bar is 36 in and side grab bar is 42 in. Breakroom sink moves 6'-4\" east from existing. Door 114 clear width is 34 in. Casework C-12 length is 8'-6\". Existing stacks aisle pinch point is 39 in clear and tagged EXISTING NONCONFORMING - DO NOT REDUCE.

## M1.3 / E1.2 Mechanical + Electrical Coordination

Original mechanical schedule:

| Equipment | Tons | Serves | MCA | MOCP | Breaker |
| --- | ---: | --- | ---: | ---: | --- |
| RTU-1 | 7.5 | Reading Room | 38A | 50A | 2P-50 |
| RTU-2 | 5 | Staff/Admin | 27A | 35A | 2P-35 |
| RTU-3 | 10 | Community Room | 52A | 70A | 2P-70 |
| RTU-4 | 3 | Restrooms/Storage | 18A | 25A | 2P-25 |

Total scheduled RTU capacity is 25.5 tons. Existing panel is LP-2. Condensate slope is 1/8 in per ft minimum. Smoke detector tie-in is FACP zone 4. Ceiling access panel AP-7 is 24 in x 24 in. Duct note says maintain 10 in clearance below existing beam B-4. Mechanical sheet says curb C-3 opening is 54 in x 78 in and curb C-4 opening is 38 in x 46 in. Structural/CO-02 later changes C-3 to 58 in x 80 in.

## RFI Log

RFI-07 submitted 2026-06-03: cleanout conflicts with 2'-8\" chase shown on A2.1. Response on 2026-06-06 revises chase to 3'-2\", maintains the 60 in turning circle in Room 114, and shifts lav 4 in east. Cost impact potential; schedule impact 0 days.

RFI-08 submitted 2026-06-04: existing beam B-4 reduces duct clearance at Community Room. Response on 2026-06-09 flattens duct to 12 in x 34 in for a 9'-0\" run and maintains 350 CFM branch to diffuser D-7. Schedule impact 1 day.

RFI-09 submitted 2026-06-07: existing east entry cannot remain open during crane pick. Response on 2026-06-10 uses west entry during crane pick only and requires 48 in temporary accessible route and signage. Permit impact: Yes, logistics plan clouded.

RFI-10 submitted 2026-06-08: RTU-3 submitted model exceeds basis of design capacity. Formal status on the RFI sheet is pending, but a handwritten note says resolved by CO-02, see 6/18 email.

## Change Order CO-02

CO-02 is dated 2026-06-18. Original contract amount is $486,750. Prior approved changes are $0. CO-02 amount is $25,680. Revised contract amount is $512,430. Original substantial completion was 2026-08-21. CO-02 adds 3 calendar days. Revised substantial completion is 2026-08-24.

Added scope: upsize RTU-3 from 10 tons to 12.5 tons; add ERV-1 with 450 CFM outside air; modify curb C-3 to 58 in x 80 in; add electrical breaker 3P-80A in panel MDP. Cost breakdown: mechanical equipment $14,900; electrical labor/material $4,860; roofing/curb work $3,420; OH&P $2,500.

Signatures: Dana Hu, Facilities Manager, signed 2026-06-19 for owner; Leo Martinez signed 2026-06-18 for contractor; Priya Soto signed 2026-06-20 for architect. Approval stamp: Owner approved subject to permit reviewer acceptance. CO-02 adds 3 calendar days; RFI-08 separately notes 1 day, but the packet does not prove these days are additive.

## Photo Observation Sheet

Photo 1 timestamp 2026-06-27 08:42 shows east entry staging condition with pallets blocking the east entry door and a red arrow label "36 in clear at door, not 48 in." Photo 2 timestamp 2026-06-27 09:05 shows hydrant H-2 and dumpster with tape dimension 16'-0\" and note to relocate dumpster before crane pick. Photo 3 timestamp 2026-06-28 13:18 shows Room 114 chase mockup at 3'-2\" with note RFI-07 incorporated. Photo 4 timestamp 2026-06-28 14:10 shows existing stacks aisle at 39 in and notes existing nonconforming. Photo 5 timestamp 2026-06-29 10:22 shows roof curb C-3 field layout at 58 in x 80 in and says it matches CO-02, not M1.3. Photo 6 timestamp 2026-06-29 11:47 shows temporary west entry signage: Accessible Entrance During Crane Pick July 8-10.

Inspector observations: OBS-14 says east entry route shown on logistics plan was not maintained on 06/27 and corrected route is required before public opening. OBS-15 says dumpster is within 20 ft hydrant clearance and must move at least 4 ft west. OBS-16 says Room 114 chase was revised per RFI-07 and turning circle must be verified after lav shift. OBS-17 says curb C-3 field layout follows CO-02 and permit resubmittal must reflect structural opening.

## Cross-Document Source State

Original application/mechanical drawings have 4 RTUs totaling 25.5 tons. CO-02 upsizes RTU-3 to 12.5 tons and adds ERV-1. Application/original contract value is $486,750; revised contract value after CO-02 is $512,430. Occupant load is unresolved: cover says no change, placard says 92, code calculation says 113, and fire marshal requests revision. Restroom chase final field state is 3'-2\" because RFI-07 and photo confirm it. Curb C-3 final documented field state is 58 in x 80 in because CO-02 and photo confirm it. West entry is temporary during crane pick July 8-10 only; east entry was not maintained on 06/27.
"""

    return Case(
        "P10-library-permit-packet",
        "Library Facilities Permit Packet",
        "construction",
        ["multi-page", "permit", "floor-plan", "site-plan", "rfi", "change-order", "photo-observations", "source-precedence"],
        "Stress a realistic municipal permit packet with forms, plan sheets, egress, logistics, RFI revisions, mechanical schedules, change order, and photo evidence.",
        "Eight-page raster-heavy permit packet with form fields, plans, schedules, stamps, annotations, and photo observation grids.",
        ["permit form", "code summary", "site plan", "architectural plan", "mechanical schedule", "RFIs", "change order", "photo observations"],
        ["Preserve original vs revised values.", "Bind plan dimensions and photo observations to the right objects.", "Flag unresolved source-state conflicts without inventing resolution."],
        gold,
        [near_check("p10-permit", "text", ["PR-26-18422", "Northbank Builders", "3,860", "$486,750"], 4, 520)],
        pages,
        facts=[
            fact("p10.application", "text", 6, "Permit PR-26-18422, applicant Northbank Builders LLC, work area 3,860 sq ft, valuation $486,750, typed scope replace 4 RTUs, reviewer note questions 5 RTUs, no structural work checked."),
            fact("p10.code", "table_cell", 6, "Code summary preserves building gross 18,240 sq ft, work area 3,860 sq ft, occupant load rows 79/29/5 and calculated subtotal 113; existing placard is 92."),
            fact("p10.egress", "visual_relation", 5, "Common path 48 ft, exit access travel 137 ft, required exits 2, provided exits 3, Door 103 34 in, Door 117 32 in."),
            fact("p10.occupant_conflict", "source_state", 5, "Occupant load is unresolved/conflicting: cover says no change, placard 92, calculation 113, fire marshal asks revision."),
            fact("p10.site", "visual_relation", 6, "Site plan preserves scale 1 inch = 30 ft, north 18 degrees west of sheet up, fire lane 26 ft provided vs 20 ft required, fence 146 LF, crane window 2026-07-08 to 2026-07-10, ADA route 48 in min, staging 1,120 sq ft."),
            fact("p10.hydrant", "visual_relation", 6, "Dumpster is 16 ft from hydrant H-2, conflicting with do-not-stage-within-20-ft note; later inspector says move at least 4 ft west."),
            fact("p10.floorplan", "visual_relation", 7, "A2.1 room facts preserve Room 114 single-user RR, original chase 2'-8\", WC CL 17 in, lav CL 18 in, 60 in turning circle, breakroom sink moved 6'-4\" east, Door 114 34 in, stack pinch point 39 in."),
            fact("p10.rfi07", "source_state", 6, "RFI-07 revises chase to 3'-2\", maintains 60 in turning circle, and shifts lav 4 in east; final field photo confirms 3'-2\"."),
            fact("p10.mechanical", "table_cell", 7, "Mechanical schedule preserves RTU-1 7.5 tons/38A/50A, RTU-2 5 tons/27A/35A, RTU-3 10 tons/52A/70A, RTU-4 3 tons/18A/25A, total 25.5 tons, FACP zone 4."),
            fact("p10.curb_conflict", "source_state", 6, "Curb C-3 is 54 x 78 on mechanical sheet but final CO-02/photo state is 58 x 80."),
            fact("p10.rfis", "table_cell", 7, "RFI-08 flattens duct to 12 x 34 for 9 ft and preserves 350 CFM to D-7; RFI-09 allows west entry during crane pick only with 48 in route; RFI-10 formally pending but handwritten note says resolved by CO-02."),
            fact("p10.co02", "source_state", 8, "CO-02 dated 2026-06-18 changes original $486,750 contract by $25,680 to revised $512,430, adds 3 calendar days, revised completion 2026-08-24, upsizes RTU-3 to 12.5 tons, adds ERV-1 450 CFM, C-3 58 x 80, and breaker 3P-80A in MDP."),
            fact("p10.photo_obs", "visual_relation", 8, "Photo sheet preserves east entry 36 in clear on 2026-06-27, dumpster 16 ft from H-2, Room 114 chase 3'-2\", stacks aisle 39 in, C-3 layout 58 x 80, and west entry signage applies July 8-10."),
            fact("p10.source_state", "source_state", 7, "Output distinguishes original/mechanical state from revised/current field state: 4 original RTUs vs CO adds ERV-1 and RTU-3 12.5 tons; original $486,750 vs revised $512,430; west entry temporary only during crane pick."),
            fact("p10.page_order", "structure", 4, "Output preserves packet order: permit application, code/egress, site logistics, A2.1 floor plan, M/E coordination, RFI log, CO-02, photo observations."),
        ],
        extractable_text_pages=[
            overlays(["PR-26-18422", "Northbank Builders LLC", "Work area 3,860 sq ft", "Valuation $486,750"], 100, 300),
            [],
            [],
            [],
            [],
            [],
            overlays(["CO-02", "Revised contract $512,430", "Revised substantial completion 2026-08-24"], 100, 240),
            [],
        ],
    )


def packet_dockpilot_launch() -> Case:
    pages: list[Image.Image] = []

    def page(title: str, subtitle: str = "") -> Image.Image:
        img = base_page(title)
        d = ImageDraw.Draw(img)
        if subtitle:
            d.text((100, 150), subtitle, fill="#475569", font=F["small"])
        d.text((100, 2040), "DockPilot, Inc. | BerthFlow Dispatch Copilot | Q3 2026 launch readiness packet", fill="#64748b", font=F["tiny"])
        return img

    def status_badge(d: ImageDraw.ImageDraw, x: int, y: int, text: str, color: str) -> None:
        fills = {"Green": "#dcfce7", "Amber": "#fef3c7", "Red": "#fee2e2", "Watch": "#ffedd5", "Go": "#dcfce7", "Conditional": "#e0f2fe"}
        outlines = {"Green": "#16a34a", "Amber": "#d97706", "Red": "#dc2626", "Watch": "#ea580c", "Go": "#16a34a", "Conditional": "#0284c7"}
        d.rounded_rectangle((x, y, x + 118, y + 34), radius=8, fill=fills.get(color, "#f8fafc"), outline=outlines.get(color, "#64748b"), width=2)
        d.text((x + 12, y + 8), text, fill=outlines.get(color, "#111827"), font=F["tiny_bold"])

    # Page 1
    p1 = page("DockPilot Q3 2026 Launch Readiness Packet", "Series A diligence + launch steering committee | packet date 2026-06-24 | v0.92 diligence draft")
    d = ImageDraw.Draw(p1)
    draw_kv_band(
        d,
        95,
        225,
        [
            ("Launch target", "2026-08-19"),
            ("Signed pilot carriers", "12"),
            ("Contracted launch ARR", "$1.84M"),
            ("Go/no-go score", "82 / 100"),
            ("Source clock", "Ops sheet 2026-06-23 09:10 PT"),
        ],
        [280, 290, 290, 260, 430],
    )
    draw_section(d, 100, 385, "Readiness scorecard", w=1460)
    rows = [
        ["Workstream", "Owner", "Score", "Status", "Blocking item"],
        ["Product", "Maya Rao", "86", "Green", "Exception queue UX polish"],
        ["Data integrations", "Luis Chen", "78", "Amber", "EDI 214 retry handling"],
        ["Customer success", "Jonah Miles", "91", "Green", "Training deck localization"],
        ["Legal/security", "Priya Nair", "74", "Amber", "DPA redlines from Atlas"],
        ["Finance/RevOps", "Ellen Park", "83", "Green", "Billing SKU sync"],
    ]
    draw_table(d, 100, 455, [285, 235, 130, 160, 600], rows, 64)
    draw_section(d, 100, 870, "Milestone strip", w=1460)
    timeline = [
        ("Board review", "2026-06-24"),
        ("SOC 2 evidence freeze", "2026-07-08"),
        ("Carrier enablement complete", "2026-07-22"),
        ("Launch rehearsal", "2026-08-05"),
        ("Commercial launch", "2026-08-19"),
    ]
    d.line((140, 1020, 1490, 1020), fill="#111827", width=3)
    for i, (label, date) in enumerate(timeline):
        x = 140 + i * 335
        d.ellipse((x - 12, 1008, x + 12, 1032), fill="#111827")
        draw_text(d, (x - 35, 1052), label, F["tiny_bold"], width=18, leading=22)
        d.text((x - 35, 1125), date, fill="#475569", font=F["tiny"])
    draw_note(d, (100, 1250, 760, 1490), "ARR source-state note", "Top KPI uses $1.84M as contracted launch ARR. Finance model v14 counts only $1.71M committed ARR; the extra $0.13M is verbal approval pending PO from Cobalt.", "#991b1b")
    draw_note(d, (850, 1250, 1560, 1490), "Source dates", "CRM export 2026-06-21 18:40 UTC; finance model 2026-06-17 v14; pilot telemetry 2026-06-20 through 2026-06-22; legal review 2026-06-18.", "#1d4ed8")
    pages.append(p1)

    # Page 2
    p2 = page("Market + Customer Segment Thesis", "Segment bars, TAM/SAM/SOM definitions, and attributed customer notes")
    d = ImageDraw.Draw(p2)
    segment_rows = [
        ["Fleet type", "Target", "Qualified", "In pilot", "Signed"],
        ["Port drayage specialists", "42", "31", "15", "8"],
        ["Regional intermodal carriers", "36", "24", "9", "3"],
        ["3PL-managed fleets", "28", "17", "5", "1"],
        ["Enterprise private fleets", "19", "8", "2", "0"],
    ]
    draw_table(d, 75, 245, [360, 130, 150, 140, 120], segment_rows, 62)
    d.text((980, 250), "2026 launch beachhead funnel", fill="#111827", font=F["h2"])
    colors = [("#cbd5e1", "Target"), ("#93c5fd", "Qualified"), ("#facc15", "Pilot"), ("#16a34a", "Signed")]
    fleet_data = [("Port drayage", 42, 31, 15, 8), ("Regional intermodal", 36, 24, 9, 3), ("3PL-managed", 28, 17, 5, 1), ("Private fleets", 19, 8, 2, 0)]
    for r, (name, target, qual, pilot, signed) in enumerate(fleet_data):
        y = 330 + r * 115
        d.text((980, y), name, fill="#111827", font=F["tiny_bold"])
        x = 1160
        for val, (color, _) in zip([target, qual, pilot, signed], colors):
            w = val * 7
            d.rectangle((x, y, x + w, y + 28), fill=color)
            d.text((x + w + 8, y + 3), str(val), fill="#111827", font=F["tiny"])
            y += 30
    lx = 980
    for color, label in colors:
        d.rectangle((lx, 790, lx + 28, 818), fill=color)
        d.text((lx + 38, 792), label, fill="#111827", font=F["tiny"])
        lx += 170
    draw_section(d, 75, 890, "TAM / SAM / SOM", w=1460)
    draw_table(
        d,
        75,
        960,
        [165, 790, 170],
        [
            ["Metric", "Definition", "Value"],
            ["TAM", "North America dispatch optimization software for containerized freight", "$8.6B"],
            ["SAM", "Port/intermodal carriers with 25+ tractors", "$1.42B"],
            ["SOM 2028", "Realistic reachable ARR by end of 2028", "$34.5M"],
        ],
        68,
    )
    draw_section(d, 75, 1260, "Customer notes", w=1460)
    notes = [
        ("Atlas Drayage", "If appointment prediction is right 80% of the time, this replaces two manual planners."),
        ("Northstar Intermodal", "Exception handling matters more than route optimization."),
        ("Cobalt Logistics", "Will not expand until driver app latency is under 2 seconds."),
    ]
    for i, (name, quote) in enumerate(notes):
        x = 85 + i * 505
        d.rounded_rectangle((x, 1330, x + 455, 1518), radius=10, fill="#f8fafc", outline="#cbd5e1", width=2)
        d.text((x + 20, 1350), name, fill="#111827", font=F["small_bold"])
        draw_text(d, (x + 20, 1390), quote, F["tiny"], width=32, leading=24)
    pages.append(p2)

    # Page 3
    p3 = page("Product Workflow + System Diagram", "Swimlane dependencies and launch-readiness metrics")
    d = ImageDraw.Draw(p3)
    lanes = ["Carrier TMS", "DockPilot ingestion", "Prediction service", "Dispatcher console", "Driver notifications"]
    lane_x = [80, 395, 710, 1025, 1340]
    lane_fill = ["#f8fafc", "#ecfeff", "#eff6ff", "#fefce8", "#f0fdf4"]
    for x, lane, fill in zip(lane_x, lanes, lane_fill):
        d.rounded_rectangle((x, 245, x + 260, 1050), radius=12, fill=fill, outline="#cbd5e1", width=2)
        draw_text(d, (x + 16, 270), lane, F["small_bold"], width=15, leading=24)
    nodes = [
        (105, 470, "EDI 214 / CSV /\nAPI webhook"),
        (420, 470, "Normalize appointment,\ncontainer, chassis,\ndriver, terminal"),
        (735, 470, "Late risk + turn-time\nestimate + missed-slot\nprobability"),
        (1050, 470, "Prioritized queue,\nreassignments,\nreason codes"),
        (1365, 470, "App push + SMS\nfallback + terminal\ninstruction"),
    ]
    for x, y, text in nodes:
        d.rounded_rectangle((x, y, x + 210, y + 150), radius=10, fill="white", outline="#111827", width=2)
        draw_text(d, (x + 14, y + 18), text, F["tiny"], width=18, leading=23)
    for i in range(4):
        d.line((315 + i * 315, 545, 420 + i * 315, 545), fill="#111827", width=4)
        d.polygon([(420 + i * 315, 545), (402 + i * 315, 535), (402 + i * 315, 555)], fill="#111827")
    draw_table(
        d,
        85,
        1135,
        [380, 220, 200, 220],
        [
            ["Metric", "Pilot median", "P90", "Launch target"],
            ["API ingest latency", "42 sec", "3m 48s", "< 2m"],
            ["Prediction refresh", "9 min", "17 min", "< 10m"],
            ["Console load time", "1.8 sec", "4.7 sec", "< 2.5 sec"],
            ["SMS fallback success", "94.2%", "98.8%", "> 96%"],
        ],
        62,
    )
    d.rounded_rectangle((1185, 1160, 1540, 1370), radius=12, fill="#dcfce7", outline="#16a34a", width=3)
    d.text((1215, 1190), "Driver comms ready", fill="#166534", font=F["h2"])
    draw_text(d, (1215, 1245), "Visual state is green, but table median SMS fallback success is 94.2%, below the > 96% target.", F["tiny"], fill="#166534", width=28, leading=24)
    pages.append(p3)

    # Page 4
    p4 = page("Pilot Performance Results", "Manual intervention trend, late-rate table, and metric-definition conflict")
    d = ImageDraw.Draw(p4)
    d.text((100, 225), "Headline: Manual intervention down 54% at Atlas", fill="#111827", font=F["h1"])
    chart_box = (100, 320, 1120, 860)
    d.rectangle(chart_box, outline="#334155", width=2)
    d.text((130, 345), "Weekly manual intervention rate", fill="#111827", font=F["small_bold"])
    weeks = ["05-04", "05-11", "05-18", "05-25", "06-01", "06-08", "06-15"]
    series = {
        "Atlas Drayage": ([38, 34, 29, 25, 22, 19, 17], "#2563eb"),
        "Northstar Intermodal": ([44, 39, 33, 30, 26, 24, 23], "#0f766e"),
        "Cobalt Logistics": ([41, 37, 34, 31, 29, 28, 27], "#c2410c"),
    }
    x_base, y_base = 175, 780
    d.line((x_base, y_base, 1040, y_base), fill="#111827", width=2)
    d.line((x_base, y_base, x_base, 410), fill="#111827", width=2)
    for i, wk in enumerate(weeks):
        x = x_base + i * 140
        d.text((x - 24, y_base + 20), wk, fill="#475569", font=F["tiny"])
    for name, (vals, color) in series.items():
        pts = []
        for i, val in enumerate(vals):
            x = x_base + i * 140
            y = y_base - (val - 10) * 10
            pts.append((x, y))
        for a, b in zip(pts, pts[1:]):
            d.line((*a, *b), fill=color, width=4)
        for p in pts:
            d.ellipse((p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5), fill=color)
    ly = 405
    for name, (_, color) in series.items():
        d.rectangle((1160, ly, 1190, ly + 18), fill=color)
        d.text((1205, ly - 3), name, fill="#111827", font=F["tiny"])
        ly += 40
    draw_table(
        d,
        100,
        950,
        [300, 210, 220, 190, 230],
        [
            ["Customer", "Loads observed", "Baseline late rate", "Pilot late rate", "Absolute improvement"],
            ["Atlas Drayage", "18,420", "21.8%", "14.6%", "-7.2 pp"],
            ["Northstar Intermodal", "11,905", "19.4%", "15.1%", "-4.3 pp"],
            ["Cobalt Logistics", "7,330", "23.1%", "20.8%", "-2.3 pp"],
        ],
        64,
    )
    draw_note(d, (100, 1280, 820, 1515), "Metric definition note", "Atlas 54% is relative reduction in manual intervention rate from 38% to 17%. It is not the late-rate absolute improvement, which is -7.2 percentage points.", "#991b1b")
    pages.append(p4)

    # Page 5
    p5 = page("Launch Revenue Model", "ARR bridge, pricing rules, and finance assumptions")
    d = ImageDraw.Draw(p5)
    bridge = [
        ("Signed pilots converted", 1.21, "#2563eb"),
        ("Launch expansion SKUs", 0.33, "#0f766e"),
        ("Usage overage estimate", 0.17, "#f59e0b"),
        ("Pending PO from Cobalt", 0.13, "#dc2626"),
    ]
    d.text((100, 245), "ARR bridge to launch pipeline total: $1.84M", fill="#111827", font=F["h2"])
    x, y = 110, 330
    for label, amount, color in bridge:
        w = int(amount * 390)
        d.rectangle((x, y, x + w, y + 55), fill=color)
        if w >= 95:
            d.text((x + 8, y + 16), f"${amount:.2f}M", fill="white", font=F["tiny_bold"])
        x += w + 18
    for i, (label, amount, color) in enumerate(bridge):
        lx = 110 + (i % 2) * 520
        ly = 425 + (i // 2) * 46
        d.rectangle((lx, ly + 4, lx + 24, ly + 28), fill=color)
        d.text((lx + 36, ly), f"{label} - ${amount:.2f}M", fill="#111827", font=F["tiny"])
    draw_table(
        d,
        90,
        570,
        [390, 250, 180, 270, 240],
        [
            ["SKU", "Unit", "Price", "Included volume", "Overage"],
            ["Dispatch Copilot Core", "tractor / month", "$145", "1,200 loads/month", "$0.18/load"],
            ["Terminal Intelligence", "terminal / month", "$2,400", "4 terminals", "$650/extra terminal"],
            ["Driver Comms", "driver / month", "$19", "unlimited SMS fallback", "none"],
            ["Premium Support", "account / month", "$3,500", "10 admin users", "$90/admin"],
        ],
        68,
    )
    draw_note(d, (95, 965, 620, 1240), "Finance assumptions", "Gross margin at launch 71%; target gross margin by 2027-Q2 is 78%; payment terms Net 45; expected churn through 2026 is 0% logo and 3.5% gross revenue; sales cycle assumption 94 days.", "#334155")
    draw_note(d, (705, 965, 1535, 1240), "ARR terminology conflict", "Page 1 calls $1.84M contracted launch ARR. This page labels the same total launch pipeline and includes pending PO from Cobalt. Committed ARR is $1.71M.", "#991b1b")
    pages.append(p5)

    # Page 6
    p6 = page("Customer Launch Roster + Risk Register", "Contract state, launch cohorts, and risk ownership")
    d = ImageDraw.Draw(p6)
    roster = [
        ["Customer", "Segment", "Tractors", "Term.", "ARR", "Contract state", "Cohort"],
        ["Atlas Drayage", "Port drayage", "420", "6", "$612k", "Signed MSA", "A"],
        ["Northstar Intermodal", "Regional carrier", "315", "4", "$438k", "Signed MSA", "A"],
        ["Cobalt Logistics", "3PL-managed", "180", "3", "$263k", "PO pending", "B"],
        ["HarborLine Cartage", "Port drayage", "96", "2", "$141k", "Signed order form", "A"],
        ["BayPeak Transport", "Port drayage", "74", "1", "$104k", "Legal review", "B"],
        ["Mesa Container", "Regional carrier", "68", "1", "$91k", "Signed order form", "B"],
        ["WestPier Haulage", "Port drayage", "55", "1", "$77k", "Security review", "C"],
        ["BlueRail Dray", "Regional carrier", "49", "1", "$68k", "Signed order form", "C"],
        ["Summit Intermodal", "Enterprise private", "42", "1", "$46k", "Verbal approval", "C"],
    ]
    draw_table(d, 45, 235, [255, 225, 95, 75, 100, 245, 85], roster, 54)
    risk = [
        ["Risk", "Description", "Prob.", "Impact", "Owner", "Mitigation", "Status"],
        ["R-14", "EDI retry failures cause stale ETAs", "Med", "High", "Luis", "Retry queue + dead-letter dashboard", "Amber"],
        ["R-18", "Atlas DPA redlines delay expansion", "Low", "High", "Priya", "Exec call 2026-06-27", "Amber"],
        ["R-21", "Training attendance below 80%", "Med", "Med", "Jonah", "Add second cohort sessions", "Green"],
        ["R-25", "SMS carrier filtering reduces delivery", "Med", "Med", "Maya", "Register templates with Twilio", "Amber"],
        ["R-29", "Cobalt PO slips past launch", "High", "Med", "Ellen", "Remove from contracted ARR forecast", "Red"],
    ]
    draw_table(d, 45, 910, [95, 360, 90, 90, 110, 420, 105], risk, 58)
    draw_note(d, (75, 1325, 1540, 1510), "Cross-page revenue note", "Cobalt appears as PO pending in the roster and as pending PO in the ARR bridge. Risk R-29 says to remove Cobalt from contracted ARR forecast until PO is received.", "#991b1b")
    pages.append(p6)

    # Page 7
    p7 = page("Operating Plan + Staffing", "Gantt dates, dependencies, and RACI ownership")
    d = ImageDraw.Draw(p7)
    tasks = [
        ["Finalize exception queue UX", "2026-06-24", "2026-07-03", "Maya", "none"],
        ["EDI retry hardening", "2026-06-24", "2026-07-10", "Luis", "none"],
        ["SOC 2 evidence freeze", "2026-07-01", "2026-07-08", "Priya", "vendor logs"],
        ["Customer admin training", "2026-07-09", "2026-07-22", "Jonah", "sandbox refresh"],
        ["Billing SKU sync", "2026-07-11", "2026-07-18", "Ellen", "pricing approval"],
        ["Launch rehearsal", "2026-08-05", "2026-08-07", "Maya", "all Cohort A live"],
        ["Cohort A launch", "2026-08-19", "2026-08-19", "Maya", "rehearsal pass"],
        ["Cohort B launch", "2026-09-02", "2026-09-02", "Jonah", "Cohort A stability"],
        ["Cohort C launch", "2026-09-16", "2026-09-16", "Jonah", "support load review"],
    ]
    draw_table(d, 65, 235, [385, 190, 190, 130, 330], [["Task", "Start", "End", "Owner", "Dependency"], *tasks], 52)
    gx, gy = 100, 845
    d.text((gx, gy - 54), "Visual Gantt strip", fill="#111827", font=F["small_bold"])
    gantt_offset = 265
    gantt_step = 126
    dates = ["06-24", "07-08", "07-22", "08-05", "08-19", "09-02", "09-16"]
    for i, date in enumerate(dates):
        x = gx + gantt_offset + i * gantt_step
        d.line((x, gy + 10, x, gy + 400), fill="#e5e7eb", width=2)
        d.text((x - 28, gy - 24), date, fill="#475569", font=F["tiny"])
    for r, row in enumerate(tasks):
        y = gy + 34 + r * 38
        d.text((gx, y), row[0][:30], fill="#111827", font=F["tiny"])
        start_idx = max(0, min(len(dates) - 1, next((i for i, dd in enumerate(dates) if row[1][5:] <= dd), 0)))
        end_idx = max(start_idx, next((i for i, dd in enumerate(dates) if row[2][5:] <= dd), len(dates) - 1))
        x1 = gx + gantt_offset + start_idx * gantt_step
        x2 = gx + gantt_offset + end_idx * gantt_step + 42
        d.rounded_rectangle((x1, y, x2, y + 22), radius=5, fill="#93c5fd", outline="#1d4ed8", width=1)
    raci = [
        ["Workstream", "Maya", "Luis", "Priya", "Jonah", "Ellen"],
        ["Product readiness", "A", "C", "I", "R", "I"],
        ["Data reliability", "C", "A/R", "I", "C", "I"],
        ["Security/legal", "I", "C", "A/R", "I", "C"],
        ["Customer enablement", "C", "I", "I", "A/R", "I"],
        ["Revenue operations", "I", "I", "C", "C", "A/R"],
    ]
    draw_table(d, 65, 1290, [310, 130, 130, 130, 130, 130], raci, 56)
    draw_note(d, (1050, 1285, 1540, 1510), "Launch scope note", "Page 1 launch target 2026-08-19 is Cohort A only. Cohort B launches 2026-09-02 and Cohort C launches 2026-09-16.", "#991b1b")
    pages.append(p7)

    # Page 8
    p8 = page("Go / No-Go Decision Memo", "Decision criteria, votes, and final conditional recommendation")
    d = ImageDraw.Draw(p8)
    decision = [
        ["Criterion", "Threshold", "Current", "Decision"],
        ["Cohort A signed ARR", ">= $1.15M", "$1.295M", "Go"],
        ["API ingest P90", "< 4m", "3m 48s", "Go"],
        ["Prediction refresh P90", "< 15m", "17m", "No-Go exception"],
        ["Security blockers", "0 critical", "0 critical, 2 medium", "Go"],
        ["Training completion", ">= 80%", "76%", "Watch"],
        ["Support coverage", "18 hrs/day", "16 hrs/day", "Watch"],
    ]
    draw_table(d, 80, 245, [390, 250, 270, 280], decision, 62)
    d.rounded_rectangle((100, 765, 1540, 1000), radius=14, fill="#fff7ed", outline="#c2410c", width=4)
    draw_text(d, (135, 810), "Final recommendation: Proceed with Cohort A launch on 2026-08-19 only if prediction refresh P90 is under 15 minutes by 2026-08-05 rehearsal. Cobalt ARR remains outside contracted launch ARR until PO is received.", F["small_bold"], fill="#9a3412", width=103, leading=33)
    approvals = [
        ["Approver", "Role", "Vote", "Note"],
        ["Maya Rao", "VP Product", "Go", "UX exception queue acceptable"],
        ["Luis Chen", "Head of Data Platform", "Conditional Go", "Needs refresh job fix"],
        ["Priya Nair", "Legal/Security", "Go", "DPA risk manageable"],
        ["Jonah Miles", "Customer Success", "Watch", "Training below target"],
        ["Ellen Park", "Finance", "Conditional Go", "Exclude Cobalt from contracted ARR"],
    ]
    draw_table(d, 80, 1090, [230, 330, 210, 520], approvals, 62)
    draw_note(d, (95, 1510, 1540, 1690), "Reconciliation summary", "The final memo narrows launch to Cohort A, blocks Cobalt ARR from contracted forecast until PO is received, and requires prediction refresh P90 to improve from 17m to under 15m by rehearsal.", "#334155")
    pages.append(p8)

    p9 = page("Deployment Runbook + Rollback Criteria", "Launch window, owners, handoffs, and visual decision tree")
    d = ImageDraw.Draw(p9)
    rows = [
        ["Window", "Step", "Owner", "System", "Exit condition"],
        ["07:30-08:00 PT", "Freeze feature flag cohort-a-ga", "Maya", "LaunchDarkly", "flag locked"],
        ["08:00-08:20 PT", "Drain retry queue below 250 jobs", "Luis", "Ingestion", "queue < 250"],
        ["08:20-08:40 PT", "Enable Atlas + Northstar terminals", "Maya", "Admin console", "6 Atlas + 4 Northstar terminals live"],
        ["08:40-09:10 PT", "Run synthetic EDI 214 replay", "Luis", "Pipeline", "P90 ingest < 4m"],
        ["09:10-09:30 PT", "Support handoff and SMS template check", "Jonah", "Zendesk/Twilio", "16 hr coverage acknowledged"],
        ["09:30-10:00 PT", "Go/no-go readout", "Maya", "Launch bridge", "all rollback triggers green"],
    ]
    draw_table(d, 45, 245, [190, 385, 145, 210, 350], rows, 70)
    draw_section(d, 85, 790, "Rollback triggers", w=1400)
    triggers = [
        ["Trigger", "Threshold", "Action", "Owner"],
        ["Prediction refresh P90", ">= 20m for 2 consecutive checks", "rollback Cohort A flag", "Luis"],
        ["EDI retry queue", "> 1,200 jobs for 30 min", "disable auto-retry", "Luis"],
        ["SMS fallback success", "< 92% median", "switch to email-only fallback", "Jonah"],
        ["Critical security issue", "any Sev-1", "hold launch", "Priya"],
    ]
    draw_table(d, 85, 865, [360, 330, 390, 150], triggers, 66)
    draw_note(d, (95, 1275, 1510, 1465), "Runbook dependency", "The runbook allows Cohort A launch only after the P90 refresh fix is verified. It operationalizes the Page 8 conditional recommendation, not a separate launch decision.", "#991b1b")
    pages.append(p9)

    p10 = page("Region Rollout Matrix + Decision Log", "Timestamped decisions, feature flags, and source-state conflicts")
    d = ImageDraw.Draw(p10)
    rows = [
        ["Region / cohort", "Feature flag", "Legal", "Support", "Training", "Launch date", "Status"],
        ["US West / Cohort A", "cohort-a-ga", "Atlas DPA accepted", "16 hr/day", "82%", "2026-08-19", "conditional go"],
        ["US Central / Cohort B", "cohort-b-beta", "BayPeak legal review", "12 hr/day", "74%", "2026-09-02", "watch"],
        ["US East / Cohort B", "cohort-b-beta", "Mesa signed", "12 hr/day", "79%", "2026-09-02", "watch"],
        ["Canada / Cohort C", "cohort-c-off", "security review", "8 hr/day", "61%", "2026-09-16", "blocked"],
    ]
    draw_table(d, 45, 245, [225, 215, 260, 155, 140, 175, 180], rows, 72)
    draw_section(d, 85, 835, "Decision log", w=1400)
    decisions = [
        ["Timestamp", "Decision", "Owner", "Supersedes"],
        ["2026-06-23 09:10 PT", "Ops sheet marked launch score 82/100", "Maya", "none"],
        ["2026-06-24 16:20 PT", "Cohort A go only if refresh P90 <15m by rehearsal", "Steering committee", "green launch card"],
        ["2026-06-25 11:05 PT", "Cobalt ARR excluded until PO received", "Ellen", "pipeline $1.84M as contracted"],
        ["2026-06-26 08:35 PT", "Canada Cohort C blocked pending security review", "Priya", "default cohort calendar"],
    ]
    draw_table(d, 85, 910, [245, 525, 250, 340], decisions, 76)
    draw_note(d, (95, 1325, 1510, 1510), "Decision source-state", "The 2026-06-24 and 2026-06-25 decision log entries supersede earlier green launch and contracted-ARR shorthand. They do not change the underlying customer roster values.", "#1d4ed8")
    pages.append(p10)

    gold = """# DockPilot Q3 2026 Launch Readiness Packet

Prepared for Series A diligence + launch steering committee. Packet date 2026-06-24. Version v0.92 diligence draft. Source dates include CRM export 2026-06-21 18:40 UTC, finance model 2026-06-17 v14, ops readiness sheet 2026-06-23 09:10 PT, pilot telemetry 2026-06-20 through 2026-06-22, and legal review 2026-06-18.

## Executive Launch Snapshot

KPI values: target launch date 2026-08-19; signed pilot carriers 12; contracted launch ARR $1.84M; go/no-go score 82 / 100.

| Workstream | Owner | Score | Status | Blocking item |
| --- | --- | ---: | --- | --- |
| Product | Maya Rao | 86 | Green | Exception queue UX polish |
| Data integrations | Luis Chen | 78 | Amber | EDI 214 retry handling |
| Customer success | Jonah Miles | 91 | Green | Training deck localization |
| Legal/security | Priya Nair | 74 | Amber | DPA redlines from Atlas |
| Finance/RevOps | Ellen Park | 83 | Green | Billing SKU sync |

Milestones: board review 2026-06-24; SOC 2 evidence freeze 2026-07-08; carrier enablement complete 2026-07-22; launch rehearsal 2026-08-05; commercial launch 2026-08-19. The ARR source-state note says the top KPI uses $1.84M as contracted launch ARR, while finance model v14 counts only $1.71M committed ARR because $0.13M is verbal approval pending PO from Cobalt.

## Market + Customer Segment Thesis

| Fleet type | Target accounts | Qualified | In pilot | Signed |
| --- | ---: | ---: | ---: | ---: |
| Port drayage specialists | 42 | 31 | 15 | 8 |
| Regional intermodal carriers | 36 | 24 | 9 | 3 |
| 3PL-managed fleets | 28 | 17 | 5 | 1 |
| Enterprise private fleets | 19 | 8 | 2 | 0 |

TAM is $8.6B for North America dispatch optimization software for containerized freight. SAM is $1.42B for port/intermodal carriers with 25+ tractors. SOM 2028 is $34.5M realistic reachable ARR by end of 2028.

Customer notes: Atlas Drayage says appointment prediction at 80% accuracy replaces two manual planners. Northstar Intermodal says exception handling matters more than route optimization. Cobalt Logistics will not expand until driver app latency is under 2 seconds.

## Product Workflow + System Diagram

Workflow lanes are Carrier TMS, DockPilot ingestion, Prediction service, Dispatcher console, and Driver notifications. The directed flow is EDI 214 / CSV / API webhook to normalization of appointment, container, chassis, driver, terminal; then late risk, turn-time estimate, and missed-slot probability; then prioritized queue, suggested reassignments, and exception reason codes; then app push, SMS fallback, and terminal instruction.

| Metric | Pilot median | P90 | Launch target |
| --- | ---: | ---: | ---: |
| API ingest latency | 42 sec | 3m 48s | < 2m |
| Prediction refresh | 9 min | 17 min | < 10m |
| Console load time | 1.8 sec | 4.7 sec | < 2.5 sec |
| SMS fallback success | 94.2% | 98.8% | > 96% |

The visual state says Driver comms ready in green, but the SMS fallback pilot median is 94.2%, below the > 96% target.

## Pilot Performance Results

Manual intervention rate by week:

| Week starting | Atlas Drayage | Northstar Intermodal | Cobalt Logistics |
| --- | ---: | ---: | ---: |
| 2026-05-04 | 38% | 44% | 41% |
| 2026-05-11 | 34% | 39% | 37% |
| 2026-05-18 | 29% | 33% | 34% |
| 2026-05-25 | 25% | 30% | 31% |
| 2026-06-01 | 22% | 26% | 29% |
| 2026-06-08 | 19% | 24% | 28% |
| 2026-06-15 | 17% | 23% | 27% |

| Customer | Loads observed | Baseline late rate | Pilot late rate | Absolute improvement |
| --- | ---: | ---: | ---: | ---: |
| Atlas Drayage | 18,420 | 21.8% | 14.6% | -7.2 pp |
| Northstar Intermodal | 11,905 | 19.4% | 15.1% | -4.3 pp |
| Cobalt Logistics | 7,330 | 23.1% | 20.8% | -2.3 pp |

The headline "Manual intervention down 54% at Atlas" is a relative reduction from 38% to 17%, not the late-rate absolute improvement of -7.2 percentage points.

## Launch Revenue Model

| Component | ARR impact |
| --- | ---: |
| Signed pilots converted | $1.21M |
| Launch expansion SKUs | $0.33M |
| Usage overage estimate | $0.17M |
| Pending PO from Cobalt | $0.13M |
| Total launch pipeline | $1.84M |

| SKU | Unit | Price | Included volume | Overage |
| --- | --- | ---: | --- | --- |
| Dispatch Copilot Core | tractor / month | $145 | 1,200 loads/month | $0.18/load |
| Terminal Intelligence | terminal / month | $2,400 | 4 terminals | $650/extra terminal |
| Driver Comms | driver / month | $19 | unlimited SMS fallback | none |
| Premium Support | account / month | $3,500 | 10 admin users | $90/admin |

Finance assumptions: gross margin at launch 71%; target gross margin by 2027-Q2 78%; payment terms Net 45; expected churn through 2026 is 0% logo and 3.5% gross revenue; sales cycle assumption 94 days. Page 1 calls $1.84M contracted launch ARR, while this page labels it launch pipeline and includes pending PO from Cobalt; committed ARR is $1.71M.

## Customer Launch Roster + Risk Register

| Customer | Segment | Tractors | Terminals | ARR | Contract state | Launch cohort |
| --- | --- | ---: | ---: | ---: | --- | --- |
| Atlas Drayage | Port drayage | 420 | 6 | $612k | Signed MSA | Cohort A |
| Northstar Intermodal | Regional carrier | 315 | 4 | $438k | Signed MSA | Cohort A |
| Cobalt Logistics | 3PL-managed | 180 | 3 | $263k | PO pending | Cohort B |
| HarborLine Cartage | Port drayage | 96 | 2 | $141k | Signed order form | Cohort A |
| BayPeak Transport | Port drayage | 74 | 1 | $104k | Legal review | Cohort B |
| Mesa Container | Regional carrier | 68 | 1 | $91k | Signed order form | Cohort B |
| WestPier Haulage | Port drayage | 55 | 1 | $77k | Security review | Cohort C |
| BlueRail Dray | Regional carrier | 49 | 1 | $68k | Signed order form | Cohort C |
| Summit Intermodal | Enterprise private | 42 | 1 | $46k | Verbal approval | Cohort C |

Risk R-14: EDI retry failures cause stale ETAs, medium probability, high impact, owner Luis, mitigation retry queue + dead-letter dashboard, Amber. Risk R-18: Atlas DPA redlines delay expansion, low probability, high impact, owner Priya, exec call 2026-06-27, Amber. Risk R-21: training attendance below 80%, medium probability and impact, owner Jonah, add second cohort sessions, Green. Risk R-25: SMS carrier filtering reduces delivery, medium probability and impact, owner Maya, register templates with Twilio, Amber. Risk R-29: Cobalt PO slips past launch, high probability, medium impact, owner Ellen, remove from contracted ARR forecast, Red.

## Operating Plan + Staffing

| Task | Start | End | Owner | Dependency |
| --- | --- | --- | --- | --- |
| Finalize exception queue UX | 2026-06-24 | 2026-07-03 | Maya | none |
| EDI retry hardening | 2026-06-24 | 2026-07-10 | Luis | none |
| SOC 2 evidence freeze | 2026-07-01 | 2026-07-08 | Priya | vendor logs |
| Customer admin training | 2026-07-09 | 2026-07-22 | Jonah | sandbox refresh |
| Billing SKU sync | 2026-07-11 | 2026-07-18 | Ellen | pricing approval |
| Launch rehearsal | 2026-08-05 | 2026-08-07 | Maya | all Cohort A live |
| Cohort A launch | 2026-08-19 | 2026-08-19 | Maya | rehearsal pass |
| Cohort B launch | 2026-09-02 | 2026-09-02 | Jonah | Cohort A stability |
| Cohort C launch | 2026-09-16 | 2026-09-16 | Jonah | support load review |

RACI: Product readiness Maya A, Luis C, Priya I, Jonah R, Ellen I. Data reliability Maya C, Luis A/R, Priya I, Jonah C, Ellen I. Security/legal Maya I, Luis C, Priya A/R, Jonah I, Ellen C. Customer enablement Maya C, Luis I, Priya I, Jonah A/R, Ellen I. Revenue operations Maya I, Luis I, Priya C, Jonah C, Ellen A/R.

Page 1 launch target 2026-08-19 is Cohort A only. Cohort B launches 2026-09-02 and Cohort C launches 2026-09-16.

## Go / No-Go Decision Memo

| Criterion | Threshold | Current | Decision |
| --- | ---: | ---: | --- |
| Cohort A signed ARR | >= $1.15M | $1.295M | Go |
| API ingest P90 | < 4m | 3m 48s | Go |
| Prediction refresh P90 | < 15m | 17m | No-Go exception |
| Security blockers | 0 critical | 0 critical, 2 medium | Go |
| Training completion | >= 80% | 76% | Watch |
| Support coverage | 18 hrs/day | 16 hrs/day | Watch |

Final recommendation: Proceed with Cohort A launch on 2026-08-19 only if prediction refresh P90 is under 15 minutes by 2026-08-05 rehearsal. Cobalt ARR remains outside contracted launch ARR until PO is received.

Approvals: Maya Rao, VP Product, Go, UX exception queue acceptable. Luis Chen, Head of Data Platform, Conditional Go, needs refresh job fix. Priya Nair, Legal/Security, Go, DPA risk manageable. Jonah Miles, Customer Success, Watch, training below target. Ellen Park, Finance, Conditional Go, exclude Cobalt from contracted ARR.

## Deployment Runbook + Rollback Criteria

| Window | Step | Owner | System | Exit condition |
| --- | --- | --- | --- | --- |
| 07:30-08:00 PT | Freeze feature flag cohort-a-ga | Maya | LaunchDarkly | flag locked |
| 08:00-08:20 PT | Drain retry queue below 250 jobs | Luis | Ingestion | queue < 250 |
| 08:20-08:40 PT | Enable Atlas + Northstar terminals | Maya | Admin console | 6 Atlas + 4 Northstar terminals live |
| 08:40-09:10 PT | Run synthetic EDI 214 replay | Luis | Pipeline | P90 ingest < 4m |
| 09:10-09:30 PT | Support handoff and SMS template check | Jonah | Zendesk/Twilio | 16 hr coverage acknowledged |
| 09:30-10:00 PT | Go/no-go readout | Maya | Launch bridge | all rollback triggers green |

Rollback triggers: Prediction refresh P90 >= 20m for 2 consecutive checks causes rollback of Cohort A flag by Luis. EDI retry queue > 1,200 jobs for 30 min disables auto-retry by Luis. SMS fallback success < 92% median switches to email-only fallback by Jonah. Any Sev-1 security issue holds launch by Priya.

The runbook allows Cohort A launch only after the P90 refresh fix is verified. It operationalizes the Page 8 conditional recommendation, not a separate launch decision.

## Region Rollout Matrix + Decision Log

| Region / cohort | Feature flag | Legal | Support | Training | Launch date | Status |
| --- | --- | --- | --- | ---: | --- | --- |
| US West / Cohort A | cohort-a-ga | Atlas DPA accepted | 16 hr/day | 82% | 2026-08-19 | conditional go |
| US Central / Cohort B | cohort-b-beta | BayPeak legal review | 12 hr/day | 74% | 2026-09-02 | watch |
| US East / Cohort B | cohort-b-beta | Mesa signed | 12 hr/day | 79% | 2026-09-02 | watch |
| Canada / Cohort C | cohort-c-off | security review | 8 hr/day | 61% | 2026-09-16 | blocked |

| Timestamp | Decision | Owner | Supersedes |
| --- | --- | --- | --- |
| 2026-06-23 09:10 PT | Ops sheet marked launch score 82/100 | Maya | none |
| 2026-06-24 16:20 PT | Cohort A go only if refresh P90 <15m by rehearsal | Steering committee | green launch card |
| 2026-06-25 11:05 PT | Cobalt ARR excluded until PO received | Ellen | pipeline $1.84M as contracted |
| 2026-06-26 08:35 PT | Canada Cohort C blocked pending security review | Priya | default cohort calendar |

The 2026-06-24 and 2026-06-25 decision log entries supersede earlier green launch and contracted-ARR shorthand. They do not change the underlying customer roster values.
"""

    return Case(
        "P11-dockpilot-launch-readiness",
        "DockPilot Q3 Launch Readiness Packet",
        "business-operations",
        ["multi-page", "pitch", "finance", "charts", "swimlane", "gantt", "risk-register", "source-precedence"],
        "Stress a realistic launch diligence packet with dense business tables, chart extraction, swimlane reconstruction, Gantt dates, RACI ownership, ARR terminology conflicts, and final recommendation reconciliation.",
        "Ten-page generated board/launch packet with tables, charts, workflow diagram, Gantt strip, runbook, rollout matrix, decision log, and cross-page source-state conflicts.",
        ["executive snapshot", "market thesis", "workflow diagram", "pilot performance", "revenue model", "roster and risk register", "operating plan", "decision memo"],
        ["Preserve dense tables instead of summarizing.", "Bind chart values to labels and legends.", "Keep source-state conflicts explicit.", "Reconcile final recommendation with earlier pages."],
        gold,
        [
            near_check("dockpilot-arr-conflict", "source_state", ["$1.84M", "$1.71M", "$0.13M", "Cobalt"], 5, 650),
            near_check("dockpilot-sms-conflict", "visual_relation", ["Driver comms ready", "94.2%", "> 96%"], 4, 600),
            near_check("dockpilot-atlas-54", "chart", ["38%", "17%", "54%", "-7.2 pp"], 4, 700),
            near_check("dockpilot-final-rec", "source_state", ["Proceed with Cohort A", "2026-08-19", "prediction refresh P90", "under 15 minutes", "Cobalt ARR"], 6, 900),
        ],
        pages,
        facts=[
            fact("p11.kpis", "table_cell", 6, "KPI strip preserves target launch date 2026-08-19, 12 signed pilot carriers, contracted launch ARR $1.84M, and go/no-go score 82 / 100."),
            fact("p11.readiness", "table_cell", 7, "Readiness table preserves all five workstreams, owners, scores, Green/Amber status, and blocking items."),
            fact("p11.arr.source_state", "source_state", 8, "ARR conflict is explicit: page 1 says $1.84M contracted launch ARR; finance model counts $1.71M committed ARR; $0.13M is verbal approval/pending PO from Cobalt."),
            fact("p11.segment-bars", "chart", 6, "Market segment values are preserved: 42/31/15/8, 36/24/9/3, 28/17/5/1, 19/8/2/0."),
            fact("p11.workflow", "visual_relation", 8, "Workflow preserves lane order from Carrier TMS to ingestion to prediction service to dispatcher console to driver notifications and the node contents in each lane."),
            fact("p11.sms-conflict", "visual_relation", 7, "Green Driver comms ready visual conflicts with SMS fallback median 94.2%, below the > 96% target."),
            fact("p11.performance-trend", "chart", 8, "Manual intervention trend values for Atlas, Northstar, and Cobalt are preserved for all seven weeks."),
            fact("p11.metric-definition", "source_state", 6, "Atlas 54% is relative manual-intervention reduction from 38% to 17%, not the -7.2 pp late-rate improvement."),
            fact("p11.revenue-bridge", "chart", 7, "ARR bridge preserves signed pilots $1.21M, expansion $0.33M, usage overage $0.17M, Cobalt pending PO $0.13M, total pipeline $1.84M."),
            fact("p11.pricing", "table_cell", 6, "Pricing table preserves all SKU units, prices, included volumes, and overage rules."),
            fact("p11.roster", "table_cell", 9, "Customer roster preserves all nine customers with segment, tractors, terminals, ARR, contract state, and cohort."),
            fact("p11.r29", "source_state", 8, "Risk R-29 ties Cobalt PO pending/slipping past launch to removing Cobalt from contracted ARR forecast."),
            fact("p11.gantt", "table_cell", 8, "Operating plan preserves all nine tasks with start/end dates, owners, and dependencies."),
            fact("p11.launch-scope", "source_state", 7, "2026-08-19 launch is Cohort A only; Cohort B launches 2026-09-02 and Cohort C launches 2026-09-16."),
            fact("p11.decision", "table_cell", 7, "Go/no-go table preserves thresholds, current values, and decisions, including Prediction refresh P90 < 15m current 17m No-Go exception."),
            fact("p11.final-recommendation", "source_state", 10, "Final recommendation requires Cohort A launch only if prediction refresh P90 is under 15 minutes by 2026-08-05 rehearsal and excludes Cobalt ARR until PO is received."),
            fact("p11.runbook", "table_cell", 9, "Deployment runbook preserves all six time windows, steps, owners, systems, and exit conditions, including queue <250, 6 Atlas + 4 Northstar terminals live, P90 ingest <4m, and 16 hr support coverage.", modality="table", severity="major"),
            fact("p11.rollback", "source_state", 8, "Rollback criteria preserve prediction refresh P90 >=20m for two checks, retry queue >1,200 for 30 min, SMS fallback <92% median, any Sev-1 security issue, and their actions/owners.", modality="source-precedence", severity="critical"),
            fact("p11.rollout.matrix", "table_cell", 8, "Region rollout matrix preserves feature flags, legal/support/training states, launch dates, and status for US West, US Central, US East, and Canada.", modality="table", severity="major"),
            fact("p11.decision.log", "source_state", 9, "Decision log preserves timestamps and supersession: 2026-06-24 conditional Cohort A go supersedes green launch card; 2026-06-25 Cobalt ARR exclusion supersedes pipeline $1.84M as contracted; 2026-06-26 Canada blocked supersedes default cohort calendar.", modality="source-precedence", severity="critical"),
        ],
    )


def packet_pfas_validation() -> Case:
    pages: list[Image.Image] = []

    def page(title: str, subtitle: str = "") -> Image.Image:
        img = base_page(title)
        d = ImageDraw.Draw(img)
        if subtitle:
            d.text((100, 150), subtitle, fill="#475569", font=F["small"])
        d.text((100, 2040), "North River Environmental Laboratory | MV-PFAS-24-017 Rev A | Technical Supplement S1 pages 1-8", fill="#64748b", font=F["tiny"])
        return img

    def mini_eq(d: ImageDraw.ImageDraw, x: int, y: int, text: str) -> None:
        d.rounded_rectangle((x, y, x + 690, y + 58), radius=8, fill="#f8fafc", outline="#cbd5e1", width=2)
        d.text((x + 18, y + 16), text, fill="#111827", font=F["mono"])

    # Shared data
    analytes = ["PFBA", "PFPeA", "PFHxA", "PFHpA", "PFOA", "PFNA", "PFDA", "PFBS", "PFHxS", "PFOS", "6:2 FTS", "HFPO-DA"]
    cal_rows = [
        ["PFBA", "13C4-PFBA", "213>169", "213>119", "2.18", "0.0921", "0.0030", "0.9987", "0.50-80", "0.16", "0.50"],
        ["PFPeA", "13C5-PFPeA", "263>219", "263>169", "2.74", "0.0875", "0.0028", "0.9991", "0.50-80", "0.13", "0.50"],
        ["PFHxA", "13C5-PFHxA", "313>269", "313>119", "3.32", "0.0814", "0.0041", "0.9985", "0.50-80", "0.18", "0.50"],
        ["PFHpA", "13C4-PFHpA", "363>319", "363>169", "3.86", "0.0778", "0.0037", "0.9990", "0.50-80", "0.15", "0.50"],
        ["PFOA", "13C8-PFOA", "413>369", "413>169", "4.41", "0.0749", "0.0044", "0.9994", "0.25-80", "0.08", "0.25"],
        ["PFNA", "13C9-PFNA", "463>419", "463>169", "4.95", "0.0712", "0.0051", "0.9989", "0.25-80", "0.09", "0.25"],
        ["PFDA", "13C6-PFDA", "513>469", "513>219", "5.48", "0.0686", "0.0048", "0.9986", "0.25-80", "0.10", "0.25"],
        ["PFBS", "18O2-PFBS", "299>80", "299>99", "3.05", "0.1033", "0.0062", "0.9992", "0.50-100", "0.17", "0.50"],
        ["PFHxS", "18O2-PFHxS", "399>80", "399>99", "4.63", "0.0968", "0.0075", "0.9988", "0.50-100", "0.20", "0.50"],
        ["PFOS", "13C8-PFOS", "499>80", "499>99", "5.64", "0.0915", "0.0081", "0.9982", "0.50-100", "0.22", "0.50"],
        ["6:2 FTS", "13C2-6:2FTS", "427>407", "427>81", "5.19", "0.0642", "0.0057", "0.9979", "1.00-100", "0.31", "1.00"],
        ["HFPO-DA", "13C3-HFPO-DA", "329>285", "329>169", "3.71", "0.0839", "0.0035", "0.9993", "0.50-80", "0.14", "0.50"],
    ]

    # Page 1
    p1 = page("Technical Supplement S1 - PFAS Method Validation", "MV-PFAS-24-017 Rev A | LC-MS/MS validation of 12 PFAS in finished drinking water")
    d = ImageDraw.Draw(p1)
    draw_kv_band(
        d,
        90,
        220,
        [
            ("Lab", "North River Environmental Laboratory"),
            ("Method basis", "EPA 533 modified"),
            ("Instrument", "SCIEX 6500+ QTRAP"),
            ("Study dates", "2024-04-08 to 2024-04-19"),
        ],
        [440, 320, 360, 350],
    )
    draw_section(d, 90, 365, "Scope and method conditions", w=1450)
    draw_text(d, (90, 430), "Isotope dilution LC-MS/MS, ESI negative. Column: Waters Acquity BEH C18, 2.1 x 50 mm, 1.7 um. Injection: 5 uL. Mobile A: 5 mM ammonium acetate in water. Mobile B: methanol.", F["small"], width=112, leading=30)
    draw_section(d, 90, 570, "Workflow", w=1450)
    steps = ["receipt", "preservation check", "SPE extraction", "nitrogen dry-down", "reconstitution", "LC-MS/MS", "review"]
    x = 90
    for i, step in enumerate(steps):
        d.rounded_rectangle((x, 640, x + 175, 705), radius=9, fill="#f8fafc", outline="#334155", width=2)
        draw_text(d, (x + 10, 657), step, F["tiny_bold"], width=16, leading=19)
        if i < len(steps) - 1:
            d.line((x + 175, 672, x + 210, 672), fill="#111827", width=3)
            d.polygon([(x + 210, 672), (x + 195, 664), (x + 195, 680)], fill="#111827")
        x += 210
    draw_table(
        d,
        90,
        790,
        [120, 110, 145],
        [["Time min", "%B", "Flow mL/min"], ["0.0", "35", "0.30"], ["0.5", "35", "0.30"], ["6.0", "95", "0.35"], ["8.5", "95", "0.35"], ["8.6", "35", "0.30"], ["11.0", "35", "0.30"]],
        46,
    )
    manifest = [
        ["SampleID", "Matrix", "Collected", "Received", "pH", "Cl mg/L", "Vol mL", "Condition"],
        ["FB-240408-01", "Field blank", "04-08 09:10", "04-08 15:42", "6.8", "<0.02", "252", "OK"],
        ["DW-240408-02", "Finished water", "04-08 09:25", "04-08 15:42", "7.2", "<0.02", "251", "OK"],
        ["DW-240408-03", "Finished water", "04-08 09:40", "04-08 15:42", "7.1", "<0.02", "249", "OK"],
        ["DW-240409-04", "Finished water", "04-09 10:05", "04-09 16:20", "7.4", "<0.02", "250", "OK"],
        ["DW-240409-05", "Finished water", "04-09 10:20", "04-09 16:20", "7.3", "<0.02", "250", "OK"],
        ["LRB-240410-01", "Lab reagent blank", "04-10 07:30", "04-10 07:30", "6.9", "<0.02", "250", "Prepared"],
        ["LCS-240410-01", "Lab control sample", "04-10 07:35", "04-10 07:35", "7.0", "<0.02", "250", "Prepared"],
        ["MSD-240410-03", "Matrix spike dup.", "04-10 07:40", "04-10 07:40", "7.1", "<0.02", "250", "Prepared"],
    ]
    draw_table(d, 520, 790, [205, 195, 150, 150, 65, 95, 80, 140], manifest, 46)
    pages.append(p1)

    # Page 2
    p2 = page("Calibration Model and Transition Table", "Equations, transitions, calibration range, LOD, and LOQ")
    d = ImageDraw.Draw(p2)
    mini_eq(d, 80, 225, "R = A_native / A_IS")
    mini_eq(d, 810, 225, "C_sample = ((R - b) / m) * DF")
    mini_eq(d, 80, 305, "LOD = t_(n-1,0.99) * SD_low")
    mini_eq(d, 810, 305, "U95 = k * sqrt(u_cal^2 + u_rep^2 + u_vol^2 + u_rec^2), k=2")
    draw_table(
        d,
        35,
        420,
        [125, 160, 115, 115, 75, 90, 90, 80, 115, 85, 85],
        [["Analyte", "IS", "Quant.", "Qual.", "RT", "m", "b", "R2", "Range", "LOD", "LOQ"], *cal_rows],
        48,
    )
    pages.append(p2)

    # Page 3
    p3 = page("Calibration Curves and Residuals", "Four-panel calibration page with residual table")
    d = ImageDraw.Draw(p3)
    panel_data = {
        "A PFOA calibration": ([0.25, 0.5, 1, 2, 5, 10, 20, 50, 80], [0.0232, 0.0419, 0.0791, 0.1538, 0.3785, 0.7530, 1.5012, 3.7501, 5.9960], "#2563eb", "Level (ng/L)", "Response ratio"),
        "B PFOS calibration": ([0.5, 1, 2, 5, 10, 20, 50, 100], [0.0540, 0.0992, 0.1910, 0.4658, 0.9216, 1.8360, 4.5860, 9.1510], "#0f766e", "Level (ng/L)", "Response ratio"),
        "C HFPO-DA calibration": ([0.5, 1, 2, 5, 10, 20, 50, 80], [0.0460, 0.0878, 0.1714, 0.4220, 0.8435, 1.6830, 4.1970, 6.7160], "#c2410c", "Level (ng/L)", "Response ratio"),
        "D residuals": ([1, 2, 3], [7.8, 10.6, 6.1], "#7c3aed", "Residual check", "Max abs residual %"),
    }
    for idx, (title, (xs, ys, color, x_label, y_label)) in enumerate(panel_data.items()):
        px = 80 + (idx % 2) * 760
        py = 245 + (idx // 2) * 445
        d.rectangle((px, py, px + 650, py + 360), outline="#334155", width=2)
        d.text((px + 18, py + 18), title, fill="#111827", font=F["small_bold"])
        d.line((px + 70, py + 305, px + 590, py + 305), fill="#111827", width=2)
        d.line((px + 70, py + 305, px + 70, py + 70), fill="#111827", width=2)
        max_x = max(xs)
        max_y = max(ys)
        for tick in range(1, 5):
            gx = px + 70 + tick * 125
            gy = py + 305 - tick * 52
            d.line((gx, py + 70, gx, py + 305), fill="#e5e7eb", width=1)
            d.line((px + 70, gy, px + 590, gy), fill="#e5e7eb", width=1)
            d.text((gx - 18, py + 315), f"{int(max_x * tick / 4)}", fill="#64748b", font=F["tiny"])
            d.text((px + 20, gy - 10), f"{max_y * tick / 4:.1f}", fill="#64748b", font=F["tiny"])
        d.text((px + 250, py + 335), x_label, fill="#475569", font=F["tiny"])
        d.text((px + 90, py + 52), y_label, fill="#475569", font=F["tiny"])
        pts = []
        for xv, yv in zip(xs, ys):
            x = px + 70 + int((xv / max_x) * 500)
            y = py + 305 - int((yv / max_y) * 215)
            pts.append((x, y))
        for a, b in zip(pts, pts[1:]):
            d.line((*a, *b), fill=color, width=4)
        for pt in pts:
            d.ellipse((pt[0] - 4, pt[1] - 4, pt[0] + 4, pt[1] + 4), fill=color)
    draw_table(
        d,
        100,
        1180,
        [220, 260, 180, 500],
        [
            ["Analyte", "Max abs residual %", "Failing points", "Reviewer note"],
            ["PFOA", "7.8", "0", "Weighted 1/x2 retained"],
            ["PFOS", "10.6", "0", "High calibrator within +/-15%"],
            ["HFPO-DA", "6.1", "0", "No curvature observed"],
        ],
        60,
    )
    pages.append(p3)

    # Pages 4-5 continuation
    s4_header = ["Analyte", "Low Rec", "Low RSD", "Mid Rec", "Mid RSD", "High Rec", "High RSD", "N", "Status"]
    s4_part1 = [
        ["PFBA", "96", "8.4", "101", "4.6", "99", "3.8", "7", "Pass"],
        ["PFPeA", "93", "9.1", "98", "5.2", "101", "4.1", "7", "Pass"],
        ["PFHxA", "91", "10.3", "97", "5.8", "100", "4.3", "7", "Pass"],
        ["PFHpA", "95", "7.9", "99", "4.9", "102", "4.0", "7", "Pass"],
        ["PFOA", "98", "6.8", "103", "3.7", "101", "3.2", "7", "Pass"],
        ["PFNA", "97", "7.2", "102", "4.1", "100", "3.6", "7", "Pass"],
        ["PFDA", "92", "11.5", "96", "6.3", "99", "4.9", "7", "Pass"],
    ]
    p4 = page("Table S4. Accuracy and Precision - Part 1", "Fortified reagent-water recovery and precision; continued on page 5")
    d = ImageDraw.Draw(p4)
    draw_table(d, 55, 250, [180, 125, 125, 125, 125, 135, 135, 70, 120], [s4_header, *s4_part1], 68)
    draw_note(d, (85, 980, 720, 1190), "Footnotes", "Acceptance: 70-130% recovery and RSD <= 20% unless method-specified criterion is tighter. Low level equals 2x LOQ for PFOA/PFNA/PFDA and equals LOQ for remaining analytes.", "#334155")
    draw_note(d, (820, 980, 1510, 1190), "Continuation", "Rows 8-12 continue on page 5 under the same Table S4 header. The header is repeated there for readability.", "#92400e")
    pages.append(p4)

    s4_part2 = [
        ["PFBS", "104", "9.7", "99", "4.8", "98", "4.0", "7", "Pass"],
        ["PFHxS", "101", "8.9", "100", "4.4", "97", "3.9", "7", "Pass"],
        ["PFOS", "89", "12.6", "95", "6.7", "96", "5.1", "7", "Pass"],
        ["6:2 FTS", "86", "14.8", "92", "7.4", "94", "6.3", "7", "Pass"],
        ["HFPO-DA", "99", "7.5", "104", "4.2", "103", "3.5", "7", "Pass"],
    ]
    p5 = page("Table S4 Continued + Matrix Spike Recovery", "Continuation rows, matrix spike duplicate, RPD, and qualifier flags")
    d = ImageDraw.Draw(p5)
    draw_table(d, 55, 235, [180, 125, 125, 125, 125, 135, 135, 70, 120], [s4_header, *s4_part2], 62)
    ms_rows = [
        ["SampleID", "Analyte", "Native", "Spike", "MS Rec", "MSD Rec", "RPD", "Flag"],
        ["DW-240408-03", "PFOA", "3.42", "10.00", "96", "98", "2.1", "None"],
        ["DW-240408-03", "PFOS", "0.74", "10.00", "91", "88", "3.4", "J-native below 2x LOQ"],
        ["DW-240408-03", "PFHxS", "1.16", "10.00", "102", "99", "3.0", "None"],
        ["DW-240408-03", "HFPO-DA", "<0.50", "10.00", "105", "106", "1.0", "U-native"],
        ["DW-240408-03", "6:2 FTS", "<1.00", "10.00", "84", "87", "3.5", "Low bias monitored"],
    ]
    draw_section(d, 55, 720, "Matrix spike / duplicate table", w=1400)
    draw_table(d, 55, 790, [205, 140, 120, 105, 110, 120, 90, 300], ms_rows, 62)
    pages.append(p5)

    # Page 6
    p6 = page("Batch Sequence, QC State, and Review Trail", "Sequence table with reinjection state and review signoff")
    d = ImageDraw.Draw(p6)
    seq_rows = [["Seq", "Type", "Vial", "SampleID", "Time", "IS OK", "Carryover", "State"]]
    for row in [
        ("1", "Solvent blank", "A01", "SBLK-01", "08:10", "Yes", "Yes", "Accepted"),
        ("2", "Calibration", "A02", "CAL-0.5", "08:23", "Yes", "Yes", "Accepted"),
        ("3", "Calibration", "A03", "CAL-1", "08:36", "Yes", "Yes", "Accepted"),
        ("4", "Calibration", "A04", "CAL-2", "08:49", "Yes", "Yes", "Accepted"),
        ("5", "Calibration", "A05", "CAL-5", "09:02", "Yes", "Yes", "Accepted"),
        ("6", "Calibration", "A06", "CAL-10", "09:15", "Yes", "Yes", "Accepted"),
        ("7", "Calibration", "A07", "CAL-20", "09:28", "Yes", "Yes", "Accepted"),
        ("8", "Calibration", "A08", "CAL-50", "09:41", "Yes", "Yes", "Accepted"),
        ("9", "Calibration", "A09", "CAL-80", "09:54", "Yes", "Yes", "Accepted"),
        ("10", "Blank", "B01", "LRB-240410-01", "10:07", "Yes", "Yes", "Accepted"),
        ("11", "LCS", "B02", "LCS-240410-01", "10:20", "Yes", "Yes", "Accepted"),
        ("12", "Sample", "B03", "FB-240408-01", "10:33", "Yes", "Yes", "Accepted"),
        ("13", "Sample", "B04", "DW-240408-02", "10:46", "Yes", "Yes", "Accepted"),
        ("14", "Sample", "B05", "DW-240408-03", "10:59", "Yes", "Yes", "Accepted"),
        ("15", "MS", "B06", "DW-240408-03-MS", "11:12", "Yes", "Yes", "Accepted"),
        ("16", "MSD", "B07", "DW-240408-03-MSD", "11:25", "Yes", "Yes", "Accepted"),
        ("17", "CCV", "B08", "CCV-10", "11:38", "Yes", "Yes", "Accepted"),
        ("18", "Sample", "B09", "DW-240409-04", "11:51", "No", "Yes", "Reinject"),
        ("19", "Sample", "C01", "DW-240409-04-RI", "12:18", "Yes", "Yes", "Accepted"),
        ("20", "Sample", "C02", "DW-240409-05", "12:31", "Yes", "Yes", "Accepted"),
    ]:
        seq_rows.append(list(row))
    draw_table(d, 45, 230, [65, 155, 75, 245, 85, 85, 120, 120], seq_rows, 42)
    draw_note(d, (1015, 245, 1535, 535), "Review trail", "Initial analyst review: M. Iyer, 2024-04-19 14:05. Technical review: L. Chen, 2024-04-22 09:40. QA release: R. Patel, 2024-04-22 16:10.", "#1d4ed8")
    draw_note(d, (1015, 600, 1535, 840), "Reinjection state", "Seq 18 DW-240409-04 failed internal standard recovery and is marked Reinject. Seq 19 DW-240409-04-RI is the accepted reinjection used for final results.", "#991b1b")
    pages.append(p6)

    # Page 7
    p7 = page("Chromatogram Plate S7", "Six-panel chromatogram-style visual evidence with retention windows")
    d = ImageDraw.Draw(p7)
    panels = [
        ("A LRB blank PFOS", "no peak; noise 41 cps", "#64748b"),
        ("B CAL-0.5 PFOS", "RT 5.64; area 4,572; S/N 12", "#2563eb"),
        ("C DW-240408-03 PFOA", "RT 4.41; area 25,621; 3.42 ng/L", "#0f766e"),
        ("D DW-240408-03 PFOS", "RT 5.65; area 6,318; 0.74 ng/L", "#c2410c"),
        ("E DW-240408-03-MS PFHxS", "RT 4.63; area 98,114; 11.36 ng/L", "#7c3aed"),
        ("F DW-240409-04 IS overlay", "original IS 38%; reinjection IS 91%", "#ea580c"),
    ]
    for i, (title, note, color) in enumerate(panels):
        x = 70 + (i % 2) * 760
        y = 235 + (i // 2) * 390
        d.rectangle((x, y, x + 665, y + 300), outline="#334155", width=2)
        d.text((x + 18, y + 18), title, fill="#111827", font=F["small_bold"])
        d.line((x + 55, y + 245, x + 620, y + 245), fill="#111827", width=2)
        d.line((x + 55, y + 245, x + 55, y + 70), fill="#111827", width=2)
        if i == 0:
            for k in range(0, 520, 18):
                d.line((x + 60 + k, y + 210 + (k % 37) // 4, x + 70 + k, y + 208 + (k % 31) // 5), fill="#64748b", width=1)
        else:
            peak_x = x + 250 + (i % 3) * 65
            trace = []
            for step in range(0, 540, 9):
                xx = x + 65 + step
                dist = (xx - peak_x) / 34
                peak = 124 * pow(2.71828, -(dist * dist) / 2)
                noise = ((step * 17 + i * 11) % 13) - 6
                yy = y + 220 - int(peak) + noise
                trace.append((xx, yy))
            for a, b in zip(trace, trace[1:]):
                d.line((*a, *b), fill=color, width=2)
            d.rectangle((peak_x - 42, y + 88, peak_x + 42, y + 222), outline="#991b1b", width=2)
        draw_text(d, (x + 18, y + 260), note, F["tiny"], width=45, leading=22)
    draw_table(
        d,
        85,
        1460,
        [170, 170, 170],
        [["Analyte", "RT min", "Window"], ["PFOA", "4.41", "+/-0.08"], ["PFHxS", "4.63", "+/-0.08"], ["6:2 FTS", "5.19", "+/-0.10"], ["PFOS", "5.64", "+/-0.10"]],
        46,
    )
    pages.append(p7)

    # Page 8
    p8 = page("Final Results, Uncertainty, and Cross-References", "Regulatory result table, qualifiers, uncertainty budget, and references")
    d = ImageDraw.Draw(p8)
    results = [
        ["SampleID", "Analyte", "Result", "Qual.", "U95", "Reference"],
        ["FB-240408-01", "PFOA", "<0.25", "U", "", "Table S2"],
        ["FB-240408-01", "PFOS", "<0.50", "U", "", "Table S2"],
        ["DW-240408-02", "PFOA", "2.18", "", "0.42", "Fig S7C"],
        ["DW-240408-02", "PFOS", "0.62", "J", "0.18", "Fig S7D"],
        ["DW-240408-02", "PFHxS", "0.91", "J", "0.21", "Table S5"],
        ["DW-240408-03", "PFOA", "3.42", "", "0.55", "Fig S7C"],
        ["DW-240408-03", "PFOS", "0.74", "J", "0.19", "Fig S7D"],
        ["DW-240408-03", "HFPO-DA", "<0.50", "U", "", "Table S2"],
        ["DW-240409-04", "PFOA", "1.06", "J", "0.25", "Seq 19"],
        ["DW-240409-04", "PFOS", "<0.50", "U", "", "Seq 19"],
        ["DW-240409-05", "PFOA", "4.87", "", "0.72", "Table S8"],
        ["DW-240409-05", "PFOS", "1.34", "", "0.29", "Table S8"],
    ]
    draw_table(d, 45, 230, [230, 130, 110, 80, 90, 150], results, 44)
    unc = [
        ["Component", "PFOA %", "PFOS %", "HFPO-DA %"],
        ["Calibration", "5.2", "7.4", "4.8"],
        ["Repeatability", "4.1", "6.9", "3.7"],
        ["Volume", "1.5", "1.5", "1.5"],
        ["Recovery", "3.6", "5.1", "3.2"],
        ["Combined u", "7.7", "11.4", "6.9"],
        ["Expanded U k=2", "15.4", "22.8", "13.8"],
    ]
    draw_table(d, 900, 230, [235, 130, 130, 145], unc, 52)
    draw_note(d, (900, 720, 1530, 980), "Final-state links", "DW-240409-04 final results reference Seq 19, not Seq 18. U means not detected, J means estimated, RI means reinjection, MS/MSD indicate matrix spike and duplicate.", "#991b1b")
    pages.append(p8)

    gold = """# MV-PFAS-24-017 Rev A: LC-MS/MS Validation of 12 PFAS

North River Environmental Laboratory validated EPA 533 modified isotope dilution LC-MS/MS for 12 PFAS in finished drinking water. Instrument: SCIEX 6500+ QTRAP, ESI negative. Column: Waters Acquity BEH C18, 2.1 x 50 mm, 1.7 um. Injection 5 uL. Mobile A is 5 mM ammonium acetate in water and Mobile B is methanol. Study dates are 2024-04-08 to 2024-04-19.

## Workflow and Manifest

Workflow: receipt -> preservation check -> SPE extraction -> nitrogen dry-down -> reconstitution -> LC-MS/MS -> review.

Gradient table: 0.0 min 35% B flow 0.30 mL/min; 0.5 min 35% B 0.30; 6.0 min 95% B 0.35; 8.5 min 95% B 0.35; 8.6 min 35% B 0.30; 11.0 min 35% B 0.30.

Manifest rows include FB-240408-01 field blank collected 2024-04-08 09:10 received 15:42 pH 6.8 chlorine <0.02 volume 252 OK; DW-240408-02 finished water pH 7.2 volume 251 OK; DW-240408-03 pH 7.1 volume 249 OK; DW-240409-04 pH 7.4 volume 250 OK; DW-240409-05 pH 7.3 volume 250 OK; LRB-240410-01 prepared; LCS-240410-01 prepared; MSD-240410-03 prepared.

## Calibration

Equations: R = A_native / A_IS. C_sample = ((R - b) / m) * DF. LOD = t_(n-1,0.99) * SD_low. U95 = k * sqrt(u_cal^2 + u_rep^2 + u_vol^2 + u_rec^2), k=2.

Calibration table includes all analytes PFBA, PFPeA, PFHxA, PFHpA, PFOA, PFNA, PFDA, PFBS, PFHxS, PFOS, 6:2 FTS, and HFPO-DA with quantifier/qualifier transitions, RT, slope m, intercept b, R2, range, LOD, and LOQ. Key rows: PFOA uses 13C8-PFOA, quantifier 413>369, qualifier 413>169, RT 4.41, m 0.0749, b 0.0044, R2 0.9994, range 0.25-80, LOD 0.08, LOQ 0.25. PFOS uses 13C8-PFOS, 499>80, 499>99, RT 5.64, m 0.0915, b 0.0081, R2 0.9982, range 0.50-100, LOD 0.22, LOQ 0.50. HFPO-DA uses 13C3-HFPO-DA, 329>285, 329>169, RT 3.71, R2 0.9993, LOD 0.14, LOQ 0.50.

## Calibration Curves and Residuals

Plotted levels include PFOA response values 0.0232 at 0.25 ng/L, 0.0419 at 0.50, 0.0791 at 1.00, 0.1538 at 2.00, 0.3785 at 5.00, 0.7530 at 10.00, 1.5012 at 20.00, 3.7501 at 50.00, and 5.9960 at 80.00. PFOS response values are 0.0540 at 0.50, 0.0992 at 1.00, 0.1910 at 2.00, 0.4658 at 5.00, 0.9216 at 10.00, 1.8360 at 20.00, 4.5860 at 50.00, and 9.1510 at 100.00. HFPO-DA response values are 0.0460 at 0.50 through 6.7160 at 80.00.

Residual table: PFOA max absolute residual 7.8%, 0 failing points, weighted 1/x2 retained. PFOS max absolute residual 10.6%, 0 failing points, high calibrator within +/-15%. HFPO-DA max absolute residual 6.1%, 0 failing points, no curvature observed.

## Table S4 Accuracy and Precision

Table S4 is one continuation table across pages 4 and 5. Rows 1-7: PFBA 96/8.4, 101/4.6, 99/3.8, N 7 Pass; PFPeA 93/9.1, 98/5.2, 101/4.1 Pass; PFHxA 91/10.3, 97/5.8, 100/4.3 Pass; PFHpA 95/7.9, 99/4.9, 102/4.0 Pass; PFOA 98/6.8, 103/3.7, 101/3.2 Pass; PFNA 97/7.2, 102/4.1, 100/3.6 Pass; PFDA 92/11.5, 96/6.3, 99/4.9 Pass. Acceptance is 70-130% recovery and RSD <= 20%. Low level equals 2x LOQ for PFOA/PFNA/PFDA and equals LOQ for remaining analytes.

Rows 8-12: PFBS 104/9.7, 99/4.8, 98/4.0 Pass; PFHxS 101/8.9, 100/4.4, 97/3.9 Pass; PFOS 89/12.6, 95/6.7, 96/5.1 Pass; 6:2 FTS 86/14.8, 92/7.4, 94/6.3 Pass; HFPO-DA 99/7.5, 104/4.2, 103/3.5 Pass.

Matrix spike table for DW-240408-03: PFOA native 3.42, spike 10.00, MS 96, MSD 98, RPD 2.1, no flag. PFOS native 0.74, MS 91, MSD 88, RPD 3.4, flag J-native below 2x LOQ. PFHxS native 1.16, MS 102, MSD 99, RPD 3.0. HFPO-DA native <0.50, MS 105, MSD 106, RPD 1.0, U-native. 6:2 FTS native <1.00, MS 84, MSD 87, RPD 3.5, low bias monitored.

## Batch Sequence and Chromatograms

{md_table(seq_rows[0], seq_rows[1:])}

Sequence 18 DW-240409-04 at 11:51 has InternalStd_OK No, carryover Yes, state Reinject. Sequence 19 DW-240409-04-RI at 12:18 has InternalStd_OK Yes, carryover Yes, state Accepted and controls final results. Review trail: M. Iyer 2024-04-19 14:05, L. Chen 2024-04-22 09:40, R. Patel 2024-04-22 16:10.

Chromatogram panel facts: A LRB blank PFOS has no peak and noise 41 cps. B CAL-0.5 PFOS has RT 5.64, area 4,572, S/N 12. C DW-240408-03 PFOA has RT 4.41, area 25,621, concentration 3.42 ng/L. D DW-240408-03 PFOS has RT 5.65, area 6,318, concentration 0.74 ng/L. E DW-240408-03-MS PFHxS has RT 4.63, area 98,114, concentration 11.36 ng/L. F DW-240409-04 original vs reinjection IS overlay has original IS recovery 38% and reinjection IS recovery 91%. Retention windows: PFOA 4.41 +/-0.08, PFHxS 4.63 +/-0.08, 6:2 FTS 5.19 +/-0.10, PFOS 5.64 +/-0.10.

## Final Results and Uncertainty

Final result rows include FB-240408-01 PFOA <0.25 U and PFOS <0.50 U; DW-240408-02 PFOA 2.18 U95 0.42 Fig S7C, PFOS 0.62 J U95 0.18 Fig S7D, PFHxS 0.91 J U95 0.21 Table S5; DW-240408-03 PFOA 3.42 U95 0.55 Fig S7C, PFOS 0.74 J U95 0.19 Fig S7D, HFPO-DA <0.50 U Table S2; DW-240409-04 PFOA 1.06 J U95 0.25 Seq 19 and PFOS <0.50 U Seq 19; DW-240409-05 PFOA 4.87 U95 0.72 Table S8 and PFOS 1.34 U95 0.29 Table S8.

Uncertainty budget: Calibration PFOA 5.2%, PFOS 7.4%, HFPO-DA 4.8%; repeatability 4.1/6.9/3.7; volume 1.5/1.5/1.5; recovery 3.6/5.1/3.2; combined u 7.7/11.4/6.9; expanded U k=2 15.4/22.8/13.8. Qualifiers: U means not detected, J estimated, RI reinjection, MS matrix spike, MSD matrix spike duplicate.
"""


    return Case(
        "P12-pfas-method-validation",
        "Regulatory PFAS Method Validation Supplement",
        "scientific-regulatory",
        ["multi-page", "scientific", "regulatory", "tables", "continuation", "equations", "chromatograms", "qc"],
        "Stress dense regulatory PDF reconstruction with units, equations, continuation tables, calibration data, chromatogram panels, reinjection state, qualifiers, and cross-references.",
        "Eight-page PFAS method validation supplement with tables, equations, charts, QC states, and final result cross-references.",
        ["manifest", "calibration", "residuals", "accuracy continuation", "matrix spike", "sequence", "chromatograms", "final results"],
        ["Preserve units and qualifiers.", "Merge continuation table semantics.", "Bind chromatogram panel facts to panel labels.", "Carry reinjection state to final results."],
        gold,
        [
            near_check("pfas-pfoa-cal", "table_cell", ["PFOA", "413>369", "4.41", "0.0749", "0.9994", "0.08"], 5, 700),
            near_check("pfas-s4-continuation", "structure", ["Table S4", "continued", "PFOS", "89", "12.6", "Pass"], 5, 900),
            near_check("pfas-reinject", "source_state", ["Seq 18", "DW-240409-04", "Reinject", "Seq 19", "DW-240409-04-RI", "Accepted"], 6, 900),
            near_check("pfas-chromatogram", "visual_relation", ["DW-240408-03 PFOA", "RT 4.41", "area 25,621", "3.42 ng/L"], 5, 700),
        ],
        pages,
        facts=[
            fact("p12.method", "text", 5, "Method metadata preserves lab, method basis EPA 533 modified, SCIEX 6500+ QTRAP, column, injection, mobile phases, and study dates."),
            fact("p12.manifest", "table_cell", 7, "Manifest preserves sample IDs, matrix, collected/received times, pH, chlorine, volume, and condition for all eight rows."),
            fact("p12.equations", "formula", 6, "All four equations are preserved: R, C_sample, LOD, and U95 with k=2."),
            fact("p12.calibration", "table_cell", 10, "Calibration table preserves all 12 analytes with IS, quantifier, qualifier, RT, m, b, R2, range, LOD, and LOQ."),
            fact("p12.curves", "chart", 7, "Calibration curve data for PFOA, PFOS, and HFPO-DA are preserved with levels and response values."),
            fact("p12.residuals", "table_cell", 5, "Residual table preserves PFOA 7.8, PFOS 10.6, HFPO-DA 6.1, zero failing points, and reviewer notes."),
            fact("p12.table-s4-continuation", "structure", 9, "Table S4 is preserved as one logical continuation table across pages 4 and 5, with repeated headers not treated as data."),
            fact("p12.table-s4-values", "table_cell", 10, "All Table S4 recovery/RSD/N/status values for PFBA through HFPO-DA are preserved."),
            fact("p12.matrix-spike", "table_cell", 8, "Matrix spike table preserves native/spike/MS/MSD/RPD/flag values, including PFOS J-native below 2x LOQ and 6:2 FTS low bias monitored."),
            fact("p12.sequence", "source_state", 8, "Full sequence table preserves Seq 1-20 with Type, Vial, SampleID, Time, IS OK, Carryover, and State; Seq 18 DW-240409-04 is Reinject due to InternalStd_OK No; Seq 19 DW-240409-04-RI is Accepted and controls final results."),
            fact("p12.review-trail", "text", 4, "Review trail preserves M. Iyer 2024-04-19 14:05, L. Chen 2024-04-22 09:40, and R. Patel 2024-04-22 16:10."),
            fact("p12.chromatograms", "visual_relation", 10, "All six chromatogram panels preserve panel labels, sample/channel, RT/area/concentration or IS recovery facts."),
            fact("p12.retention", "table_cell", 5, "Retention windows preserve PFOA 4.41 +/-0.08, PFHxS 4.63 +/-0.08, 6:2 FTS 5.19 +/-0.10, PFOS 5.64 +/-0.10."),
            fact("p12.final-results", "table_cell", 10, "Final results table preserves sample/analyte/result/qualifier/U95/reference rows, including DW-240409-04 references Seq 19."),
            fact("p12.uncertainty", "table_cell", 6, "Uncertainty budget preserves all component percentages and expanded U k=2 values 15.4, 22.8, and 13.8."),
            fact("p12.qualifiers", "text", 4, "Qualifier meanings are preserved: U not detected, J estimated, RI reinjection, MS matrix spike, MSD matrix spike duplicate."),
        ],
    )


def packet_capa_quality_escape() -> Case:
    def page(title: str, subtitle: str) -> Image.Image:
        img = Image.new("RGB", (PAGE_W, PAGE_H), "#ffffff")
        d = ImageDraw.Draw(img)
        d.text((72, 58), "Asterion Components | SQE record packet", fill="#334155", font=F["tiny_bold"])
        d.text((72, 92), title, fill="#111827", font=F["h1"])
        d.text((72, 132), subtitle, fill="#475569", font=F["small"])
        d.line((72, 178, 1580, 178), fill="#cbd5e1", width=2)
        d.text((1430, 60), "CAPA-26-071", fill="#111827", font=F["small_bold"])
        return img

    pages: list[Image.Image] = []

    # Page 1
    p1 = page("Supplier Quality Escape: MX-12 Housing Burr", "Opening summary, containment scope, and conflicting dashboard state")
    d = ImageDraw.Draw(p1)
    draw_kv_band(
        d,
        75,
        220,
        [
            ("Opened", "2026-05-18 07:40"),
            ("Supplier", "Kaito Precision"),
            ("Part", "MX-12 cast housing"),
            ("Customer", "Nimble Robotics"),
            ("Severity", "S2 major"),
            ("Owner", "Iris Shah"),
        ],
        [250, 260, 290, 285, 180, 180],
    )
    draw_text(
        d,
        (80, 370),
        "Asterion opened this CAPA after receiving four customer complaints for sharp burrs on the MX-12 cable-window edge. The escape window initially covered lots L26-0511 through L26-0520, then was narrowed after receiving inspection isolated failures to cavity C3 on die D14 during the night shift. The ERP dashboard on this page still says status Closed because the auto-close job ran after the supplier uploaded an incomplete 8D; the MRB decision on page 8 supersedes that dashboard state.",
        F["small"],
        width=110,
        leading=32,
    )
    d.rounded_rectangle((1120, 520, 1545, 770), radius=10, fill="#f8fafc", outline="#94a3b8", width=2)
    d.text((1150, 548), "ERP status tile", fill="#475569", font=F["small_bold"])
    d.text((1150, 600), "CLOSED", fill="#166534", font=F["h1"])
    d.text((1150, 650), "Auto-close: 2026-05-21 02:10", fill="#475569", font=F["tiny"])
    d.text((1150, 682), "Superseded by MRB page 8", fill="#991b1b", font=F["tiny_bold"])
    rows = [
        ["Lot", "Receipt", "Qty", "Hold qty", "Disposition", "Notes"],
        ["L26-0511", "2026-05-11", "1,240", "0", "Released", "No burr >0.20 mm"],
        ["L26-0512", "2026-05-12", "1,180", "260", "Sort", "Cavity C3 trace begins"],
        ["L26-0513", "2026-05-13", "1,220", "410", "Sort", "Night shift only"],
        ["L26-0514", "2026-05-14", "1,160", "386", "Sort", "Rework if <=0.35 mm"],
        ["L26-0515", "2026-05-15", "1,210", "1,210", "Hold", "Customer stop-ship"],
        ["L26-0516", "2026-05-16", "1,190", "1,190", "Hold", "Dock sample failed"],
        ["L26-0517", "2026-05-17", "1,240", "1,240", "Hold", "Pending supplier sort"],
        ["L26-0518", "2026-05-18", "1,200", "1,200", "Hold", "Trace review open"],
        ["L26-0519", "2026-05-19", "1,170", "1,170", "Hold", "No shipment"],
        ["L26-0520", "2026-05-20", "1,180", "1,180", "Hold", "No shipment"],
    ]
    draw_ledger(d, 78, 865, [150, 150, 105, 125, 165, 520], rows, 48)
    draw_note(d, (92, 1505, 1525, 1690), "MRB override note", "ERP auto-close is not accepted for release planning. MRB disposition remains pending until 2026-06-07 rework audit, control-plan release, and customer authorization.", "#991b1b")
    pages.append(p1)

    # Page 2
    p2 = page("Customer Complaints + Field Return Log", "Mixed email export, return IDs, failure descriptions, and service impact")
    d = ImageDraw.Draw(p2)
    left = "From: Nimble Robotics SQE <quality@nimble.example>\nTo: Asterion Components\nDate: 2026-05-17 21:14 PT\nSubject: Sharp edge issue - MX-12 housings\n\nOperators reported glove tears during cable routing on units NR-8821, NR-8836, NR-8842, and NR-8848. The defect is localized around the lower-left cable-window edge. Production line B is holding 62 assemblies until the burr risk is contained. Nimble requests certified clean stock by 2026-05-23 10:00 PT."
    right = "Internal note 2026-05-18 06:35: Service team originally tagged the issue as cosmetic. SQE reclassified to S2 major because the edge can damage insulation during harness insertion. Do not use the early cosmetic classification in the final CAPA summary.\n\nPhoto packet FRT-26-118 has four images. Image C is the customer reference for the maximum burr height. Image D is unrelated handling damage and is not part of the supplier escape."
    draw_two_columns(d, 80, 230, left, right, col_w_chars=54, gap=40, leading=29, fnt=F["tiny"])
    returns = [
        ["Return", "Serial", "Lot", "Cavity", "Observed defect", "Max burr", "Line impact"],
        ["FRT-26-118-A", "NR-8821", "L26-0513", "C3", "Cable window burr", "0.42 mm", "Glove tear"],
        ["FRT-26-118-B", "NR-8836", "L26-0514", "C3", "Cable window burr", "0.38 mm", "Harness scrape"],
        ["FRT-26-118-C", "NR-8842", "L26-0515", "C3", "Cable window burr", "0.47 mm", "Hold line B"],
        ["FRT-26-118-D", "NR-8848", "L26-0515", "C2", "Corner dent", "n/a", "Unrelated"],
    ]
    draw_ledger(d, 75, 875, [170, 130, 135, 105, 290, 125, 220], returns, 58)
    draw_note(d, (80, 1265, 1525, 1460), "Important exclusion", "FRT-26-118-D is a corner dent from handling damage. It must be preserved as visible context, but it is excluded from the supplier burr escape defect count.", "#334155")
    pages.append(p2)

    # Page 3
    p3 = page("Incoming Inspection Record IR-22651", "Borderless measurement table with cavity/shift binding and handwritten correction")
    d = ImageDraw.Draw(p3)
    draw_text(d, (80, 220), "Sampling plan ANSI Z1.4 general II, tightened, AQL 0.65. Inspector: Mateo Lin. Gauge: Mitutoyo digital height probe GH-18, calibration due 2026-08-01. Acceptance: burr height <=0.20 mm after tumble; anything above 0.35 mm cannot be reworked for Nimble production stock.", F["tiny"], width=126, leading=26)
    data = [["Sample", "Lot", "Shift", "Cavity", "Burr mm", "Go/no-go", "Disposition", "Trace"]]
    vals = [
        ("01", "L26-0512", "N", "C3", "0.29", "Fail", "Sort", "Die D14"),
        ("02", "L26-0512", "D", "C1", "0.12", "Pass", "Release", "Die D13"),
        ("03", "L26-0513", "N", "C3", "0.33", "Fail", "Sort", "Die D14"),
        ("04", "L26-0513", "N", "C3", "0.41", "Fail", "Hold", "Die D14"),
        ("05", "L26-0514", "N", "C3", "0.36", "Fail", "Hold", "Die D14"),
        ("06", "L26-0514", "D", "C2", "0.16", "Pass", "Release", "Die D13"),
        ("07", "L26-0515", "N", "C3", "0.47", "Fail", "Hold", "Die D14"),
        ("08", "L26-0515", "N", "C4", "0.18", "Pass", "Release", "Die D14"),
        ("09", "L26-0516", "N", "C3", "0.39", "Fail", "Hold", "Die D14"),
        ("10", "L26-0516", "D", "C1", "0.14", "Pass", "Release", "Die D13"),
        ("11", "L26-0517", "N", "C3", "0.44", "Fail", "Hold", "Die D14"),
        ("12", "L26-0518", "N", "C3", "0.40", "Fail", "Hold", "Die D14"),
        ("13", "L26-0518", "D", "C2", "0.15", "Pass", "Release", "Die D13"),
        ("14", "L26-0519", "N", "C3", "0.37", "Fail", "Hold", "Die D14"),
        ("15", "L26-0520", "N", "C3", "0.35", "Fail", "Hold", "Die D14"),
    ]
    data += [list(v) for v in vals]
    draw_ledger(d, 70, 360, [105, 145, 90, 100, 115, 120, 140, 160], data, 45)
    d.line((560, 690, 975, 670), fill="#991b1b", width=4)
    d.text((990, 648), "Mateo correction: sample 07 is 0.47 mm, not 0.41", fill="#991b1b", font=F["tiny_bold"])
    draw_note(d, (80, 1175, 1525, 1395), "Pattern statement", "Every failed burr measurement is night shift, cavity C3, die D14. Day-shift C1/C2 and C4 checks pass. Sample 07 visible correction is 0.47 mm and controls the maximum burr value.", "#991b1b")
    pages.append(p3)

    # Page 4
    p4 = page("Defect Photo Sheet and Visual Disposition", "Photo callouts, exclusions, and acceptance boundary")
    d = ImageDraw.Draw(p4)
    labels = [
        ("A", "FRT-26-118-A | burr B2 | NR-8821 | 0.42 mm"),
        ("B", "FRT-26-118-B | scratch from rework fixture | not burr height"),
        ("C", "FRT-26-118-C | max burr reference | NR-8842 | 0.47 mm"),
        ("D", "FRT-26-118-D | corner dent | handling damage | excluded"),
    ]
    for i, (letter, label) in enumerate(labels):
        x = 80 + (i % 2) * 760
        y = 240 + (i // 2) * 525
        d.text((x, y - 38), f"Photo {letter}", fill="#111827", font=F["small_bold"])
        d.text((x + 96, y - 34), label, fill="#475569", font=F["tiny"])
        d.rectangle((x, y, x + 650, y + 360), outline="#334155", width=2)
        p4.paste(draw_defect_photo(i, 648, 358), (x + 1, y + 1))
    draw_note(d, (90, 1340, 1525, 1565), "Disposition from photos", "Photos A and C are supplier burr evidence. Photo B is a fixture scratch observed after rework trial and should not be counted as incoming defect. Photo D is excluded handling damage and remains context for the supplier review only.", "#334155")
    pages.append(p4)

    # Page 5
    p5 = page("Pareto, Containment Sort, and Daily Yield", "Visual chart values plus sort ledger and rolling containment status")
    d = ImageDraw.Draw(p5)
    defects = [("Burr C3", 74, "#991b1b"), ("Nick", 19, "#2563eb"), ("Porosity", 13, "#0f766e"), ("Scratch", 8, "#7c3aed"), ("Dent", 4, "#64748b")]
    d.text((90, 235), "Pareto: defects found during 100% sort", fill="#111827", font=F["small_bold"])
    total_defects = sum(count for _, count, _ in defects)
    cumulative = 0
    prev_point = None
    for i, (name, count, color) in enumerate(defects):
        y = 300 + i * 70
        d.text((90, y + 8), name, fill="#111827", font=F["tiny"])
        d.rectangle((260, y, 260 + count * 12, y + 34), fill=color)
        d.text((270 + count * 12, y + 4), str(count), fill="#111827", font=F["tiny_bold"])
        cumulative += count
        pct = cumulative / total_defects
        px2 = 260 + int(pct * 900)
        py2 = y + 17
        d.ellipse((px2 - 5, py2 - 5, px2 + 5, py2 + 5), fill="#111827")
        d.text((px2 + 12, py2 - 12), f"{round(pct * 100)}%", fill="#111827", font=F["tiny"])
        if prev_point:
            d.line((prev_point[0], prev_point[1], px2, py2), fill="#111827", width=3)
        prev_point = (px2, py2)
    d.line((90, 700, 1050, 700), fill="#cbd5e1", width=2)
    d.text((90, 735), "Daily clean-yield trend after deburr guard installed", fill="#111827", font=F["small_bold"])
    days = [("05-19", 86), ("05-20", 89), ("05-21", 91), ("05-22", 94), ("05-23", 97), ("05-24", 98), ("05-25", 98)]
    px, py = 90, 820
    for i, (day, val) in enumerate(days):
        x = px + i * 130
        y = py + (100 - val) * 7
        d.ellipse((x - 6, y - 6, x + 6, y + 6), fill="#0f766e")
        d.text((x - 22, py + 110), day, fill="#475569", font=F["tiny"])
        d.text((x - 8, y - 34), f"{val}%", fill="#0f766e", font=F["tiny_bold"])
        if i:
            prev_x = px + (i - 1) * 130
            prev_y = py + (100 - days[i - 1][1]) * 7
            d.line((prev_x, prev_y, x, y), fill="#0f766e", width=4)
    sort = [
        ["Date", "Lots sorted", "Qty screened", "Burr rejects", "Clean yield", "Certified ship qty"],
        ["2026-05-19", "0512-0513", "2,400", "38", "98.4%", "2,362"],
        ["2026-05-20", "0514-0515", "2,370", "44", "98.1%", "2,326"],
        ["2026-05-21", "0516-0517", "2,430", "52", "97.9%", "2,378"],
        ["2026-05-22", "0518", "1,200", "18", "98.5%", "1,182"],
        ["2026-05-23", "0519-0520", "2,350", "21", "99.1%", "2,329"],
    ]
    draw_ledger(d, 80, 1155, [170, 190, 165, 155, 145, 210], sort, 54)
    draw_note(d, (1000, 760, 1525, 1020), "Customer gate", "Nimble authorized certified clean stock only after two consecutive days at >=97% clean yield. That threshold is first met on 2026-05-23 using 05-22 and 05-23 results.", "#991b1b")
    pages.append(p5)

    # Page 6
    p6 = page("8D Root Cause + Corrective Action Plan", "Timeline, cause/effect diagram, and action ownership")
    d = ImageDraw.Draw(p6)
    timeline = [
        ["Step", "Owner", "Due", "Closed", "Evidence"],
        ["D1 team formed", "Iris", "2026-05-18", "2026-05-18", "SQE kickoff"],
        ["D2 problem statement", "Mateo", "2026-05-18", "2026-05-19", "IR-22651"],
        ["D3 containment", "Rina", "2026-05-19", "2026-05-23", "100% sort log"],
        ["D4 root cause", "Akio", "2026-05-22", "2026-05-24", "Die D14 wear report"],
        ["D5 permanent action", "Akio", "2026-05-27", "2026-05-29", "guard + offset change"],
        ["D6 validation", "Iris", "2026-06-03", "Open", "30k-piece run pending"],
        ["D7 prevention", "Supplier QE", "2026-06-06", "Open", "control-plan rev C"],
    ]
    draw_ledger(d, 75, 230, [210, 130, 160, 150, 390], timeline, 58)
    d.text((80, 720), "Root-cause worksheet", fill="#111827", font=F["small_bold"])
    causes = [
        ["Category", "Finding", "Evidence", "Disposition"],
        ["Machine", "Die D14 trim insert wear", "wear scar on C3 trim insert; first-piece 0.09 mm after replacement", "Root cause"],
        ["Method", "No C3 edge check after tumble", "Rev B control plan only required visual burr check before tumble", "Contributing"],
        ["People", "Night-shift setup offset not logged", "MES offset field optional on 05-12 through 05-20 night builds", "Contributing"],
        ["Measure", "Gauge GH-18 OK", "MSA %GRR 8.7%, ndc 7", "Not cause"],
        ["Material", "Hardness within spec", "supplier certs 82-84 HRB for affected lots", "Not cause"],
        ["Environment", "No coolant abnormality", "coolant concentration 7.1%-7.4%; no alarm history", "Not cause"],
    ]
    draw_ledger(d, 80, 770, [150, 330, 460, 260], causes, 54)
    actions = [
        ["Action", "Owner", "Due", "Status", "Verification"],
        ["Replace trim insert D14-C3", "Akio", "2026-05-24", "Done", "First-piece 0.09 mm"],
        ["Add optical edge check", "Rina", "2026-05-29", "Done", "Camera recipe MX12-C3-v4"],
        ["Revise control plan", "Supplier QE", "2026-06-06", "Open", "Rev C not released"],
        ["Audit 30k clean run", "Iris", "2026-06-07", "Open", "CAPA exit gate"],
    ]
    draw_ledger(d, 75, 1280, [350, 160, 160, 145, 360], actions, 58)
    pages.append(p6)

    # Page 7
    p7 = page("Measurement System Analysis + Control Plan Rev C", "MSA values, gauge status, and control-plan deltas")
    d = ImageDraw.Draw(p7)
    msa = [
        ["Study", "Operators", "Parts", "Trials", "%GRR", "ndc", "Decision"],
        ["Burr height GH-18", "3", "10", "3", "8.7%", "7", "Accept"],
        ["Optical C3 camera", "2", "12", "2", "12.9%", "5", "Accept with monitoring"],
        ["Manual go/no-go blade", "3", "10", "2", "27.4%", "2", "Reject"],
    ]
    draw_ledger(d, 80, 240, [230, 140, 110, 100, 115, 90, 310], msa, 60)
    cpk = [("05-24", 1.12), ("05-25", 1.26), ("05-26", 1.31), ("05-27", 1.38), ("05-28", 1.42), ("05-29", 1.47)]
    d.text((90, 595), "Cpk trend after insert replacement", fill="#111827", font=F["small_bold"])
    for i, (day, val) in enumerate(cpk):
        x = 100 + i * 150
        y = 875 - int(val * 170)
        d.rectangle((x, y, x + 78, 875), fill="#bae6fd", outline="#0369a1", width=1)
        d.text((x + 2, y - 30), str(val), fill="#075985", font=F["tiny_bold"])
        d.text((x, 895), day, fill="#475569", font=F["tiny"])
    plan = [
        ["Control plan item", "Old Rev B", "New Rev C", "Owner", "Frequency"],
        ["C3 cable-window edge", "visual burr check", "optical recipe MX12-C3-v4 + GH-18 audit", "Rina", "hourly"],
        ["Trim insert D14-C3", "replace at wear alarm", "replace every 18,000 strokes", "Akio", "per tool log"],
        ["Night-shift setup offset", "operator note optional", "offset field required in MES", "Line lead", "each setup"],
        ["Customer cert pack", "COC only", "COC + 20-piece burr data + photo sheet", "SQE", "each lot"],
    ]
    draw_ledger(d, 80, 1080, [275, 295, 420, 130, 150], plan, 68)
    draw_note(d, (1050, 610, 1530, 875), "Rejected measurement method", "The manual go/no-go blade must not be used for final disposition because %GRR is 27.4% and ndc is 2. GH-18 controls measurement acceptance.", "#991b1b")
    pages.append(p7)

    # Page 8
    p8 = page("MRB Final Disposition and CAPA Exit Gate", "Superseding decision, authorization, and remaining open conditions")
    d = ImageDraw.Draw(p8)
    disposition = [
        ["Material bucket", "Qty", "Decision", "Condition"],
        ["Certified clean stock", "10,577", "Ship to Nimble", "COC + data pack required"],
        ["Rework candidate", "1,074", "Deburr + reinspect", "Only if burr <=0.35 mm"],
        ["Scrap", "246", "Scrap at supplier", "Any burr >0.35 mm or damaged coating"],
        ["Unrelated handling damage", "1", "Customer concession", "FRT-26-118-D excluded from escape"],
    ]
    draw_ledger(d, 80, 235, [350, 140, 260, 475], disposition, 66)
    d.rounded_rectangle((90, 610, 1535, 830), radius=10, fill="#fff7ed", outline="#c2410c", width=4)
    draw_text(d, (125, 650), "MRB decision: CAPA remains CONDITIONALLY OPEN until the 30,000-piece validation run is completed by 2026-06-07 with zero burrs above 0.20 mm, control-plan Rev C is released, and Nimble signs shipment authorization NR-QA-226. This page supersedes the ERP CLOSED tile on page 1.", F["small_bold"], fill="#9a3412", width=105, leading=34)
    sign = [
        ["Approver", "Role", "Decision", "Date", "Comment"],
        ["Iris Shah", "Asterion SQE", "Conditional release", "2026-05-24", "Ship certified clean stock only"],
        ["Kenji Mori", "Kaito Quality", "Accept CAPA", "2026-05-24", "D14 insert replaced"],
        ["Lena Ortiz", "Nimble Robotics SQE", "Authorize partial ship", "2026-05-25", "Need 30k validation by 06-07"],
        ["Victor Hale", "Asterion Ops", "Hold remaining WIP", "2026-05-25", "No release without GH-18 data"],
    ]
    draw_ledger(d, 80, 970, [230, 240, 240, 150, 420], sign, 62)
    draw_note(d, (90, 1460, 1530, 1665), "Final state", "The correct final state is not Closed. It is conditionally open with certified clean stock released, rework/scrap split documented, FRT-26-118-D excluded, and exit gates pending through 2026-06-07.", "#991b1b")
    pages.append(p8)

    gold = """# CAPA-26-071 Supplier Quality Escape: MX-12 Housing Burr

Asterion Components opened CAPA-26-071 on 2026-05-18 07:40 for Kaito Precision MX-12 cast housings supplied to Nimble Robotics. Severity is S2 major and owner is Iris Shah.

## Opening Summary and Containment

The escape concerns sharp burrs on the MX-12 cable-window edge. The initial window was lots L26-0511 through L26-0520, later narrowed to cavity C3 on die D14 during night shift. Page 1 includes an ERP tile saying CLOSED with auto-close 2026-05-21 02:10, but that state is superseded by the MRB decision on page 8.

| Lot | Receipt | Qty | Hold qty | Disposition | Notes |
| --- | --- | ---: | ---: | --- | --- |
| L26-0511 | 2026-05-11 | 1,240 | 0 | Released | No burr >0.20 mm |
| L26-0512 | 2026-05-12 | 1,180 | 260 | Sort | Cavity C3 trace begins |
| L26-0513 | 2026-05-13 | 1,220 | 410 | Sort | Night shift only |
| L26-0514 | 2026-05-14 | 1,160 | 386 | Sort | Rework if <=0.35 mm |
| L26-0515 | 2026-05-15 | 1,210 | 1,210 | Hold | Customer stop-ship |
| L26-0516 | 2026-05-16 | 1,190 | 1,190 | Hold | Dock sample failed |
| L26-0517 | 2026-05-17 | 1,240 | 1,240 | Hold | Pending supplier sort |
| L26-0518 | 2026-05-18 | 1,200 | 1,200 | Hold | Trace review open |
| L26-0519 | 2026-05-19 | 1,170 | 1,170 | Hold | No shipment |
| L26-0520 | 2026-05-20 | 1,180 | 1,180 | Hold | No shipment |

## Customer Complaint and Returns

Nimble reported glove tears during cable routing on units NR-8821, NR-8836, NR-8842, and NR-8848. Production line B held 62 assemblies. SQE reclassified the issue from cosmetic to S2 major because the edge can damage insulation during harness insertion. Certified clean stock was requested by 2026-05-23 10:00 PT.

| Return | Serial | Lot | Cavity | Observed defect | Max burr | Line impact |
| --- | --- | --- | --- | --- | ---: | --- |
| FRT-26-118-A | NR-8821 | L26-0513 | C3 | Cable window burr | 0.42 mm | Glove tear |
| FRT-26-118-B | NR-8836 | L26-0514 | C3 | Cable window burr | 0.38 mm | Harness scrape |
| FRT-26-118-C | NR-8842 | L26-0515 | C3 | Cable window burr | 0.47 mm | Hold line B |
| FRT-26-118-D | NR-8848 | L26-0515 | C2 | Corner dent | n/a | Unrelated |

FRT-26-118-D is visible context but excluded from the supplier burr escape defect count because it is handling damage.

## Incoming Inspection Record IR-22651

Sampling plan ANSI Z1.4 general II, tightened, AQL 0.65. Inspector Mateo Lin used Mitutoyo digital height probe GH-18, calibration due 2026-08-01. Acceptance is burr height <=0.20 mm after tumble; anything above 0.35 mm cannot be reworked for Nimble production stock.

All failed burr measurements are night shift, cavity C3, die D14. Day-shift C1/C2 and C4 checks pass. Sample 07 has a handwritten visible correction to 0.47 mm, not 0.41 mm, and controls the maximum burr value.

## Defect Photo Sheet

Photo A is FRT-26-118-A, burr B2, NR-8821, 0.42 mm. Photo B is a scratch from the rework fixture and is not burr height. Photo C is FRT-26-118-C, maximum burr reference, NR-8842, 0.47 mm. Photo D is FRT-26-118-D, corner dent, handling damage, excluded.

## Pareto and Sort Results

Pareto defects found during 100% sort: Burr C3 74, Nick 19, Porosity 13, Scratch 8, Dent 4. Daily clean-yield trend after deburr guard install: 05-19 86%, 05-20 89%, 05-21 91%, 05-22 94%, 05-23 97%, 05-24 98%, 05-25 98%.

| Date | Lots sorted | Qty screened | Burr rejects | Clean yield | Certified ship qty |
| --- | --- | ---: | ---: | ---: | ---: |
| 2026-05-19 | 0512-0513 | 2,400 | 38 | 98.4% | 2,362 |
| 2026-05-20 | 0514-0515 | 2,370 | 44 | 98.1% | 2,326 |
| 2026-05-21 | 0516-0517 | 2,430 | 52 | 97.9% | 2,378 |
| 2026-05-22 | 0518 | 1,200 | 18 | 98.5% | 1,182 |
| 2026-05-23 | 0519-0520 | 2,350 | 21 | 99.1% | 2,329 |

Nimble authorized certified clean stock only after two consecutive days at >=97% clean yield, first met on 2026-05-23 using the 05-22 and 05-23 results.

## 8D and Corrective Action

8D timeline: D1 team formed Iris due/closed 2026-05-18; D2 problem statement Mateo due 2026-05-18 closed 2026-05-19; D3 containment Rina due 2026-05-19 closed 2026-05-23; D4 root cause Akio due 2026-05-22 closed 2026-05-24; D5 permanent action Akio due 2026-05-27 closed 2026-05-29; D6 validation Iris due 2026-06-03 remains open; D7 prevention Supplier QE due 2026-06-06 remains open.

Root-cause worksheet: machine die D14 trim insert wear is the root cause, with wear scar on C3 trim insert and first-piece 0.09 mm after replacement. Method no C3 edge check after tumble is contributing because Rev B only required visual burr check before tumble. People night-shift setup offset not logged is contributing because the MES offset field was optional on 05-12 through 05-20 night builds. Measure gauge GH-18 OK, material hardness within spec, and environment no coolant abnormality are not causes.

Actions: replace trim insert D14-C3 done with first-piece 0.09 mm; add optical edge check done with camera recipe MX12-C3-v4; revise control plan open, Rev C not released; audit 30k clean run open as CAPA exit gate.

## MSA and Control Plan Rev C

MSA rows: burr height GH-18 uses 3 operators, 10 parts, 3 trials, %GRR 8.7%, ndc 7, decision Accept. Optical C3 camera uses 2 operators, 12 parts, 2 trials, %GRR 12.9%, ndc 5, decision Accept with monitoring. Manual go/no-go blade uses 3 operators, 10 parts, 2 trials, %GRR 27.4%, ndc 2, decision Reject.

Cpk trend after insert replacement: 05-24 1.12, 05-25 1.26, 05-26 1.31, 05-27 1.38, 05-28 1.42, 05-29 1.47. The manual go/no-go blade must not be used for final disposition; GH-18 controls measurement acceptance.

Control plan Rev C changes: C3 cable-window edge changes from visual burr check to optical recipe MX12-C3-v4 plus GH-18 audit hourly; trim insert D14-C3 changes to replacement every 18,000 strokes; night-shift setup offset becomes required in MES; customer cert pack becomes COC plus 20-piece burr data plus photo sheet for each lot.

## MRB Final Disposition

| Material bucket | Qty | Decision | Condition |
| --- | ---: | --- | --- |
| Certified clean stock | 10,577 | Ship to Nimble | COC + data pack required |
| Rework candidate | 1,074 | Deburr + reinspect | Only if burr <=0.35 mm |
| Scrap | 246 | Scrap at supplier | Any burr >0.35 mm or damaged coating |
| Unrelated handling damage | 1 | Customer concession | FRT-26-118-D excluded from escape |

MRB decision: CAPA remains CONDITIONALLY OPEN until the 30,000-piece validation run is completed by 2026-06-07 with zero burrs above 0.20 mm, control-plan Rev C is released, and Nimble signs shipment authorization NR-QA-226. This supersedes the ERP CLOSED tile on page 1.

Approvals: Iris Shah conditional release on 2026-05-24, ship certified clean stock only. Kenji Mori accepts CAPA on 2026-05-24. Lena Ortiz authorizes partial ship on 2026-05-25 and requires 30k validation by 06-07. Victor Hale holds remaining WIP on 2026-05-25 with no release without GH-18 data.
"""

    return Case(
        "P13-capa-quality-escape",
        "Supplier CAPA Quality Escape Packet",
        "manufacturing-quality",
        ["multi-page", "quality", "inspection", "photos", "charts", "forms", "source-precedence", "borderless-tables"],
        "Stress a realistic manufacturing quality packet with borderless ledgers, defect photos, handwritten correction, chart values, MSA, 8D ownership, and final-state source precedence.",
        "Eight-page supplier CAPA packet with email export, inspection records, visual defect sheets, pareto/trend charts, 8D plan, MSA, and MRB decision.",
        ["containment lots", "return log", "inspection table", "photo sheet", "pareto and yield charts", "8D timeline", "MSA/control plan", "MRB final state"],
        ["Preserve borderless table row/column bindings.", "Bind photo labels to visual evidence and exclusions.", "Carry corrected values and final-state precedence across pages.", "Do not summarize away open/closed state conflicts."],
        gold,
        [
            near_check("capa-final-state", "source_state", ["ERP", "CLOSED", "CONDITIONALLY OPEN", "2026-06-07", "NR-QA-226"], 6, 900),
            near_check("capa-sample07", "source_state", ["Sample 07", "0.47 mm", "not 0.41", "maximum"], 5, 700),
            near_check("capa-photo-exclusion", "visual_relation", ["Photo D", "FRT-26-118-D", "corner dent", "excluded"], 5, 700),
            near_check("capa-mrb-disposition", "table_cell", ["10,577", "1,074", "246", "Certified clean stock", "Rework candidate", "Scrap"], 6, 900),
        ],
        pages,
        facts=[
            fact("p13.opening", "source_state", 8, "Opening summary preserves CAPA ID, supplier, part, customer, severity, owner, initial lot window, narrowed C3/D14/night-shift root pattern, and ERP CLOSED tile superseded by page 8."),
            fact("p13.containment", "table_cell", 8, "Containment ledger preserves all lot rows L26-0511 through L26-0520 with receipt, qty, hold qty, disposition, and notes."),
            fact("p13.complaint", "text", 5, "Customer complaint preserves glove tears, cable routing, line B hold of 62 assemblies, certified clean stock requested by 2026-05-23 10:00 PT, and S2 major reclassification."),
            fact("p13.returns", "table_cell", 7, "Return log preserves all four FRT rows with serial, lot, cavity, defect, max burr, and line impact."),
            fact("p13.exclusion", "visual_relation", 8, "FRT-26-118-D / Photo D is preserved as visible context but excluded from supplier burr escape count as handling damage."),
            fact("p13.inspection", "table_cell", 9, "Inspection record preserves sample rows, especially failed night-shift C3 Die D14 pattern and pass rows for day-shift C1/C2/C4."),
            fact("p13.correction", "source_state", 8, "Handwritten correction controls Sample 07: value is 0.47 mm, not 0.41 mm, and is the maximum burr value."),
            fact("p13.photos", "visual_relation", 9, "Photo sheet preserves A/B/C/D labels, return IDs, which images are burr evidence, scratch, maximum burr reference, and excluded handling damage."),
            fact("p13.pareto", "chart", 7, "Pareto chart values are preserved: Burr C3 74, Nick 19, Porosity 13, Scratch 8, Dent 4."),
            fact("p13.yield", "chart", 7, "Daily clean-yield trend values 86, 89, 91, 94, 97, 98, 98 are preserved with dates 05-19 through 05-25."),
            fact("p13.sort", "table_cell", 8, "Sort ledger preserves dates, lots, screened quantities, burr rejects, clean yield, and certified ship quantities."),
            fact("p13.customer-gate", "source_state", 6, "Nimble authorization threshold of two consecutive days >=97% clean yield is first met on 2026-05-23 using 05-22 and 05-23."),
            fact("p13.8d", "table_cell", 8, "8D timeline preserves steps, owners, due/closed dates, evidence, and open D6/D7 states."),
            fact("p13.root-cause", "table_cell", 6, "Root-cause worksheet preserves cause categories, findings, evidence, and dispositions, including die D14 trim insert wear as root cause and night-shift setup offset not logged as contributing."),
            fact("p13.actions", "table_cell", 7, "Corrective action table preserves action owners, due dates, status, and verification evidence."),
            fact("p13.msa", "table_cell", 8, "MSA table preserves GH-18 Accept, optical camera Accept with monitoring, and manual go/no-go blade Reject with %GRR 27.4 and ndc 2."),
            fact("p13.cpk", "chart", 5, "Cpk trend values 1.12, 1.26, 1.31, 1.38, 1.42, 1.47 are preserved by date."),
            fact("p13.control-plan", "table_cell", 7, "Control plan Rev C deltas preserve old/new controls, owners, and frequency for all four items."),
            fact("p13.mrb", "table_cell", 9, "MRB disposition preserves certified clean stock 10,577, rework candidate 1,074, scrap 246, unrelated handling damage 1, decisions and conditions."),
            fact("p13.final", "source_state", 10, "Final state is CONDITIONALLY OPEN until 30,000-piece validation by 2026-06-07, zero burrs above 0.20 mm, control-plan Rev C release, and Nimble authorization NR-QA-226; this supersedes page 1 CLOSED tile."),
        ],
    )


def deck_page(title: str, eyebrow: str = "", dark: bool = False) -> Image.Image:
    bg = "#0b1226" if dark else "#ffffff"
    img = Image.new("RGB", (DECK_W, DECK_H), bg)
    d = ImageDraw.Draw(img)
    if dark:
        for x in range(-120, DECK_W, 360):
            d.line((x, 0, x + 520, DECK_H), fill="#142045", width=18)
        d.rectangle((0, 0, 22, DECK_H), fill="#8b1e2d")
        fill = "#f8fafc"
        muted = "#aab3d3"
    else:
        for x in range(0, DECK_W, 38):
            d.line((x, 0, x, DECK_H), fill="#f3f4f6", width=1)
        for y in range(0, DECK_H, 38):
            d.line((0, y, DECK_W, y), fill="#f3f4f6", width=1)
        d.rectangle((0, DECK_H - 38, DECK_W, DECK_H), fill="#b91c1c")
        fill = "#111827"
        muted = "#475569"
    if eyebrow:
        d.text((70, 38), eyebrow.upper(), fill=muted, font=F["tiny_bold"])
    d.text((70, 78), title, fill=fill, font=F["h1"])
    return img


def deck_card(d: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str, body: str, dark: bool = False, accent: str = "#b91c1c") -> None:
    x1, y1, x2, y2 = box
    d.rectangle((x1, y1, x2, y2), fill="#111a35" if dark else "#ffffff", outline=accent, width=3)
    d.text((x1 + 22, y1 + 20), title, fill="#f8fafc" if dark else "#111827", font=F["small_bold"])
    draw_text(d, (x1 + 22, y1 + 62), body, F["tiny"], fill="#dbe4ff" if dark else "#1f2937", width=max(20, (x2 - x1 - 44) // 13), leading=24)


def deck_table(d: ImageDraw.ImageDraw, x: int, y: int, widths: list[int], rows: list[list[str]], dark: bool = False, row_h: int = 43) -> int:
    fill = "#f8fafc" if dark else "#111827"
    muted = "#94a3b8" if dark else "#d1d5db"
    d.line((x, y + row_h - 8, x + sum(widths), y + row_h - 8), fill=fill, width=2)
    for r, row in enumerate(rows):
        cx = x
        for c, w in enumerate(widths):
            txt = row[c] if c < len(row) else ""
            d.multiline_text((cx + 6, y + 8), txt, fill=fill, font=F["tiny_bold"] if r == 0 else F["tiny"], spacing=2)
            cx += w
        if r > 0 and r % 4 == 0:
            d.line((x, y + row_h - 5, x + sum(widths), y + row_h - 5), fill=muted, width=1)
        y += row_h
    return y


def packet_ops_board() -> Case:
    pages: list[Image.Image] = []

    p1 = deck_page("Northstar Board Pack", "Q3 operating review | confidential", True)
    d = ImageDraw.Draw(p1)
    d.text((84, 250), "Revenue expansion is healthy, but support risk moved from amber to red after NA-West crossed the queue-depth threshold twice.", fill="#f8fafc", font=F["h2"])
    deck_card(d, (90, 430, 505, 710), "ARR", "$200.5M close\n117% net retention\n$35.5M new ARR", True)
    deck_card(d, (545, 430, 960, 710), "Launch", "Release Alpha BLOCKED\nSecurity signoff missing\nNisha owns next action", True)
    deck_card(d, (1000, 430, 1415, 710), "Support", "NA-West crossed depth 35\nReopen freeze active\nTrigger: depth below 25", True)
    deck_card(d, (1460, 430, 2050, 710), "Source state", "Draft appendix still says Alpha approved and ARR $198.8M. Those values are superseded by the visible board pages.", True)
    rows = [
        ["Decision", "Owner", "Due", "State", "Comment"],
        ["Alpha release", "Nisha", "2026-07-18", "BLOCKED", "security signoff missing"],
        ["APAC pricing", "Omar", "2026-07-21", "APPROVED", "launch SKU accepted"],
        ["Support freeze", "Mei", "when NA-West <25", "ACTIVE", "queue-depth trigger"],
        ["EMEA reseller", "Lina", "2026-07-29", "WATCH", "legal review"],
    ]
    deck_table(d, 90, 810, [390, 230, 300, 190, 510], rows, True, 54)
    pages.append(p1)

    p2 = deck_page("ARR bridge + finance notes", "Note 3 | signs, footnotes, and waterfall", False)
    d = ImageDraw.Draw(p2)
    rows = [
        ["Region", "FY2025", "New", "Expansion", "Churn", "FX", "FY2026"],
        ["North America", "84.0", "+18.5", "+6.0", "(4.2)", "+0.7", "105.0"],
        ["EMEA*", "56.0", "+9.4", "+5.1", "(6.8)", "(1.2)", "62.5"],
        ["APAC", "24.5", "+7.6", "+2.4", "(1.5)", "+0.0", "33.0"],
        ["Total", "164.5", "+35.5", "+13.5", "(12.5)", "(0.5)", "200.5"],
    ]
    deck_table(d, 80, 190, [310, 150, 150, 200, 160, 120, 160], rows, False, 62)
    d.text((80, 540), "* EMEA includes Israel and South Africa. Churn is shown in parentheses and is negative. Intercompany rows excluded.", fill="#475569", font=F["tiny"])
    wx, wy = 110, 665
    vals = [("FY25", 164.5, "#334155"), ("New", 35.5, "#16a34a"), ("Expansion", 13.5, "#16a34a"), ("Churn", -12.5, "#dc2626"), ("FX", -0.5, "#dc2626"), ("FY26", 200.5, "#334155")]
    base = wy + 300
    x = wx
    current = 164.5
    for label, val, color in vals:
        h = int(abs(val) * 1.55 if label not in ["FY25", "FY26"] else val * 1.15)
        y1 = base - h if val >= 0 or label in ["FY25", "FY26"] else base
        y2 = base if val >= 0 or label in ["FY25", "FY26"] else base + h
        d.rectangle((x, y1, x + 120, y2), fill=color)
        d.text((x + 5, max(570, y1 - 32)), f"{label} {val:+.1f}" if label not in ["FY25", "FY26"] else f"{label} {val:.1f}", fill="#111827", font=F["tiny_bold"])
        x += 190
        current += val if label not in ["FY25", "FY26"] else 0
    deck_card(d, (1480, 220, 2070, 515), "Board question", "Does the visible FY2026 total reconcile to $200.5M after treating parentheses as negative values?", False)
    deck_card(d, (1480, 590, 2070, 935), "Answer expected", "Yes. FY2025 164.5 + New 35.5 + Expansion 13.5 - Churn 12.5 - FX 0.5 = FY2026 200.5.", False)
    pages.append(p2)

    p3 = deck_page("Support queue dashboard", "visual chart facts + warning banner", False)
    d = ImageDraw.Draw(p3)
    d.text((80, 180), "Queue depth", fill="#111827", font=F["small_bold"])
    pts = [(110, 600), (310, 340), (510, 370), (710, 455), (910, 540)]
    labels = [("08:00", 12), ("10:00", 41), ("12:00", 38), ("14:00", 29), ("16:00", 18)]
    d.line((100, 625, 980, 625), fill="#111827", width=3)
    d.line((100, 625, 100, 250), fill="#111827", width=3)
    d.line((100, 390, 980, 390), fill="#dc2626", width=3)
    d.text((995, 376), "threshold 35", fill="#dc2626", font=F["tiny_bold"])
    for a, b in zip(pts, pts[1:]):
        d.line((*a, *b), fill="#2563eb", width=5)
    for (x, y), (t, v) in zip(pts, labels):
        d.ellipse((x - 8, y - 8, x + 8, y + 8), fill="#2563eb")
        d.text((x - 28, 650), t, fill="#111827", font=F["tiny"])
        d.text((x - 12, y - 34), str(v), fill="#111827", font=F["tiny_bold"])
    rows = [["Region", "Tier 1", "Tier 2"], ["NA-West", "18", "11"], ["NA-East", "9", "7"], ["EMEA", "12", "5"], ["APAC", "6", "2"]]
    deck_table(d, 1160, 230, [250, 150, 150], rows, False, 58)
    matrix = [["Severity", "Breached", "At-risk", "OK"], ["Critical", "3", "2", "7"], ["High", "5", "4", "18"], ["Normal", "2", "6", "31"]]
    deck_table(d, 1160, 565, [250, 170, 170, 120], matrix, False, 58)
    deck_card(d, (80, 820, 2040, 1055), "Warning banner", "NA-West crossed depth 35 at 10:00 and 12:00. Reopen freeze remains active until queue depth is below 25. This warning depends on the line chart and backlog region, not only the text card.", False, "#c2410c")
    pages.append(p3)

    p4 = deck_page("Competitive scorecard", "board appendix | dense market comparison", True)
    d = ImageDraw.Draw(p4)
    cols = ["Capability", "Northstar", "RelayOps", "QueueIQ", "Legacy BPO", "Notes"]
    rows = [cols]
    data = [
        ("Queue depth prediction", "5", "3", "4", "1", "Northstar uses live staffing feed"),
        ("Tier routing", "5", "4", "3", "2", "QueueIQ lacks partner queue"),
        ("Audit trail", "4", "2", "3", "5", "BPO strong on manual notes"),
        ("Cost efficiency", "4", "3", "2", "1", "weighted by $/resolved ticket"),
        ("APAC readiness", "3", "2", "2", "1", "pricing approved but support pending"),
        ("Security posture", "2", "4", "3", "3", "Alpha remains blocked"),
    ]
    rows += [list(r) for r in data]
    deck_table(d, 90, 210, [360, 180, 180, 180, 200, 600], rows, True, 67)
    d.rectangle((550, 375, 720, 438), outline="#16a34a", width=5)
    d.rectangle((550, 710, 720, 773), outline="#dc2626", width=5)
    d.text((90, 965), "Range key: 1 weak, 3 competitive, 5 market leading. Green outline marks strongest cell. Red outline marks launch blocker.", fill="#cbd5e1", font=F["small"])
    pages.append(p4)

    p5 = deck_page("Draft appendix - superseded", "audit context only", False)
    d = ImageDraw.Draw(p5)
    rows = [["Draft field", "Draft value", "Final visible value", "Disposition"], ["ARR", "$198.8M", "$200.5M", "superseded"], ["Churn", "(9.1)", "(12.5)", "superseded"], ["Release Alpha", "APPROVED", "BLOCKED", "superseded"], ["Support freeze", "inactive", "ACTIVE", "superseded"]]
    deck_table(d, 120, 250, [340, 320, 360, 280], rows, False, 72)
    deck_card(d, (120, 740, 1560, 980), "Audit instruction", "This appendix is retained to show why the board decision changed. Do not replace final dashboard, ARR bridge, or decision-log values with these draft values.", False, "#991b1b")
    pages.append(p5)

    gold = """# Northstar Board Pack

Q3 operating review. Confidential.

## Executive snapshot

Revenue expansion is healthy, but support risk moved from amber to red after NA-West crossed the queue-depth threshold twice.

ARR: $200.5M close, 117% net retention, $35.5M new ARR. Launch: Release Alpha is BLOCKED because security signoff is missing; Nisha owns the next action. Support: NA-West crossed queue depth 35 and the reopen freeze is active until depth is below 25. Draft appendix values are superseded.

| Decision | Owner | Due | State | Comment |
| --- | --- | --- | --- | --- |
| Alpha release | Nisha | 2026-07-18 | BLOCKED | security signoff missing |
| APAC pricing | Omar | 2026-07-21 | APPROVED | launch SKU accepted |
| Support freeze | Mei | when NA-West <25 | ACTIVE | queue-depth trigger |
| EMEA reseller | Lina | 2026-07-29 | WATCH | legal review |

## ARR bridge + finance notes

| Region | FY2025 | New | Expansion | Churn | FX | FY2026 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| North America | 84.0 | +18.5 | +6.0 | -4.2 | +0.7 | 105.0 |
| EMEA | 56.0 | +9.4 | +5.1 | -6.8 | -1.2 | 62.5 |
| APAC | 24.5 | +7.6 | +2.4 | -1.5 | +0.0 | 33.0 |
| Total | 164.5 | +35.5 | +13.5 | -12.5 | -0.5 | 200.5 |

EMEA includes Israel and South Africa. Churn is shown in parentheses and is negative. Intercompany rows are excluded. The waterfall reconciles: FY2025 164.5 + New 35.5 + Expansion 13.5 - Churn 12.5 - FX 0.5 = FY2026 200.5.

## Support queue dashboard

Queue depth values: 08:00 12, 10:00 41, 12:00 38, 14:00 29, 16:00 18. Threshold is 35, crossed at 10:00 and 12:00.

Backlog: NA-West Tier 1 18 and Tier 2 11; NA-East 9 and 7; EMEA 12 and 5; APAC 6 and 2.

SLA matrix: Critical breached 3, at-risk 2, OK 7. High breached 5, at-risk 4, OK 18. Normal breached 2, at-risk 6, OK 31.

Warning: NA-West crossed depth 35 at 10:00 and 12:00. Reopen freeze remains active until queue depth is below 25.

## Competitive scorecard

Northstar scores 5 on queue depth prediction and tier routing, 4 on audit trail and cost efficiency, 3 on APAC readiness, and 2 on security posture. The red launch blocker is security posture. The green strongest marked cell is Northstar queue depth prediction.

## Draft appendix

Draft appendix values are superseded: ARR $198.8M, churn -$9.1M, Release Alpha APPROVED, and support freeze inactive. Final visible values are ARR $200.5M, churn -$12.5M, Release Alpha BLOCKED, and support freeze ACTIVE.
"""
    return Case(
        "P01-board-ops-packet",
        "Board Operating Packet",
        "deck",
        ["landscape", "board-deck", "finance", "dashboard", "scorecard", "source-precedence"],
        "Recover a realistic board deck with dense visual scorecards, financial bridge semantics, dashboard chart values, and superseded appendix conflicts.",
        "Five-page landscape board deck inspired by real investor deck density and composition.",
        ["executive snapshot", "ARR bridge", "support dashboard", "scorecard", "superseded appendix"],
        ["Preserve landscape deck reading order.", "Bind chart/table values.", "Treat appendix values as superseded."],
        gold,
        [near_check("p01-arr", "table_cell", ["Total", "164.5", "+35.5", "+13.5", "-12.5", "-0.5", "200.5"], 4, 800)],
        pages,
        facts=[
            fact("p01.decision", "table_cell", 8, "Decision log preserves Alpha release/Nisha/2026-07-18/BLOCKED/security signoff missing; APAC pricing/Omar/APPROVED; Support freeze/Mei/ACTIVE/when NA-West <25; EMEA reseller/Lina/WATCH."),
            fact("p01.arr", "table_cell", 10, "ARR bridge preserves every region row and total row, including parentheses as negative churn/FX and FY2026 total 200.5."),
            fact("p01.waterfall", "visual_relation", 6, "Waterfall reconciliation is FY2025 164.5 + New 35.5 + Expansion 13.5 - Churn 12.5 - FX 0.5 = FY2026 200.5."),
            fact("p01.dashboard.line", "chart", 8, "Queue depth chart values are 12, 41, 38, 29, and 18 at 08:00, 10:00, 12:00, 14:00, and 16:00; threshold 35 is crossed at 10:00 and 12:00."),
            fact("p01.backlog", "table_cell", 6, "Backlog preserves NA-West 18/11, NA-East 9/7, EMEA 12/5, APAC 6/2 for Tier 1/Tier 2."),
            fact("p01.sla", "table_cell", 6, "SLA matrix preserves Critical 3/2/7, High 5/4/18, Normal 2/6/31 for breached/at-risk/OK."),
            fact("p01.scorecard", "visual_relation", 7, "Competitive scorecard preserves Northstar scores and highlights security posture as launch blocker and queue depth prediction as a strongest cell."),
            fact("p01.superseded", "source_state", 9, "Draft appendix values ARR $198.8M, churn -$9.1M, Alpha APPROVED, and support freeze inactive are marked superseded and not final."),
        ],
    )


def packet_scientific_supplement() -> Case:
    pages: list[Image.Image] = []
    p1 = deck_page("Calibration under label drift", "preprint excerpt | two-column methods", False)
    d = ImageDraw.Draw(p1)
    left = "Abstract: We evaluate calibration under label drift using ten equal-frequency bins and a small replay buffer. The main result is that replay improves F1 while lowering expected calibration error. The experiment uses a frozen encoder, a temperature-scaling baseline, and a drift prior estimated from delayed labels."
    right = "Method: The parser emits candidate bins, estimates confidence, then applies a drift prior only when the label mix differs by more than 8 percentage points. Replay examples are capped at 500 per cohort. Storage cost is reported because the replay row is operationally heavier than temperature scaling."
    draw_text(d, (90, 190), left, F["tiny"], width=70, leading=25)
    draw_text(d, (1110, 190), right, F["tiny"], width=70, leading=25)
    d.rectangle((90, 515, 1020, 620), fill="#eef2ff", outline="#4338ca", width=3)
    d.text((120, 552), "ECE = sum_b (n_b / n) * |acc(b) - conf(b)|, with B = 10", fill="#111827", font=F["small_bold"])
    rows = [["Method", "ECE down", "F1 up", "Storage"], ["Baseline", "0.087", "0.781", "0"], ["+ temperature scaling", "0.041", "0.779", "0"], ["+ drift prior", "0.033", "0.802", "12 MB"], ["+ replay buffer", "0.029", "0.817", "1.8 GB"]]
    deck_table(d, 90, 720, [410, 180, 160, 170], rows, False, 58)
    deck_card(d, (1200, 710, 2020, 1030), "Reviewer note", "Do not read this note before the ablation table. Replay is kept despite higher storage cost because it is the only row that improves both ECE and F1.", False, "#c2410c")
    pages.append(p1)

    p2 = deck_page("Figure 2 - Calibration curves", "curve, residuals, and annotation", False)
    d = ImageDraw.Draw(p2)
    d.line((180, 980, 960, 980), fill="#111827", width=4)
    d.line((180, 980, 180, 235), fill="#111827", width=4)
    d.line((180, 980, 960, 235), fill="#64748b", width=3)
    curve = [(195, 945), (340, 820), (485, 680), (630, 570), (775, 515), (920, 500)]
    for a, b in zip(curve, curve[1:]):
        d.line((*a, *b), fill="#dc2626", width=6)
    d.text((690, 455), "over-confident above 0.75", fill="#dc2626", font=F["small_bold"])
    rows = [["Curve", "Meaning"], ["gray dashed diagonal", "perfect calibration"], ["red model curve", "below diagonal above confidence 0.75"], ["annotation", "over-confident above 0.75"]]
    deck_table(d, 1160, 260, [340, 560], rows, False, 64)
    residuals = [["Cohort", "Max residual", "Flag"], ["A none", "4.1%", "OK"], ["B mild", "6.7%", "OK"], ["C moderate", "12.4%", "Review"], ["D severe", "18.9%", "Fail"], ["E recovered", "8.2%", "OK"]]
    deck_table(d, 1160, 650, [300, 240, 180], residuals, False, 55)
    pages.append(p2)

    p3 = deck_page("Supplement Table S1", "continuation page 1 of 2", False)
    d = ImageDraw.Draw(p3)
    rows = [["Cohort", "Shift", "n", "ECE", "F1", "Note"], ["A", "none", "1200", "0.029", "0.817", "baseline final"], ["B", "mild", "840", "0.034", "0.804", "uses drift prior"], ["C", "moderate", "610", "0.052", "0.781", "see footnote 1"]]
    deck_table(d, 90, 210, [210, 210, 150, 150, 150, 470], rows, False, 74)
    deck_card(d, (90, 640, 1530, 835), "Footnote 1 begins", "Cohort C excludes 17 records with missing confidence...", False, "#475569")
    pages.append(p3)

    p4 = deck_page("Supplement Table S1", "continuation page 2 of 2", False)
    d = ImageDraw.Draw(p4)
    rows = [["Cohort", "Shift", "n", "ECE", "F1", "Note"], ["D", "severe", "455", "0.071", "0.744", "fails threshold"], ["E", "recovered", "500", "0.038", "0.799", "replay restored"], ["Total", "", "3605", "", "", "count total; do not average ECE"]]
    deck_table(d, 90, 210, [210, 210, 150, 150, 150, 470], rows, False, 74)
    deck_card(d, (90, 640, 1710, 835), "Footnote 1 continued", "...so reported n is after exclusion. The total row is a count total, not an ECE average.", False, "#475569")
    pages.append(p4)

    p5 = deck_page("Drift error matrix", "color, letter, slash semantics", False)
    d = ImageDraw.Draw(p5)
    bins = ["0.50", "0.60", "0.70", "0.80", "0.90"]
    cohorts = ["A none", "B mild", "C moderate", "D severe", "E recovered"]
    matrix = [["L", "L", "M", "M", "H"], ["L", "M", "M", "H", "H"], ["M", "M", "H", "H", "H"], ["M", "H", "H", "H", "H"], ["L", "M", "M", "H", "M"]]
    slash = {("C moderate", "0.80"), ("D severe", "0.70"), ("E recovered", "0.60")}
    colors = {"L": "#dcfce7", "M": "#fef3c7", "H": "#fee2e2"}
    x0, y0 = 420, 250
    for c, b in enumerate(bins):
        d.text((x0 + c * 185 + 42, y0 - 55), b, fill="#111827", font=F["small_bold"])
    for r, cohort in enumerate(cohorts):
        y = y0 + r * 125
        d.text((120, y + 36), cohort, fill="#111827", font=F["small_bold"])
        for c, b in enumerate(bins):
            key = matrix[r][c]
            x = x0 + c * 185
            d.rectangle((x, y, x + 130, y + 88), fill=colors[key], outline="#111827", width=3)
            d.text((x + 52, y + 28), key, fill="#111827", font=F["small_bold"])
            if (cohort, b) in slash:
                d.line((x + 8, y + 8, x + 122, y + 80), fill="#991b1b", width=5)
    deck_card(d, (1450, 260, 2050, 540), "Legend", "L low error. M medium error. H high error. Slash means manual review required.", False)
    deck_card(d, (1450, 620, 2050, 930), "Caption", "Cohort D has high error in every bin from 0.60 through 0.90. E recovered at 0.90 is medium, not high.", False, "#c2410c")
    pages.append(p5)

    p6 = deck_page("Appendix notes", "source order and repeated header warning", False)
    d = ImageDraw.Draw(p6)
    deck_card(d, (100, 260, 1030, 570), "Continuation rule", "Supplement Table S1 spans two pages. Repeated headers are not data rows. The total row is a count total and should not be used to average ECE.", False)
    deck_card(d, (1120, 260, 2050, 570), "Figure rule", "The curve description should mention the diagonal, model curve, confidence 0.75, and the over-confidence annotation.", False)
    deck_card(d, (100, 690, 2050, 930), "Manual-review cells", "Manual review slash cells are C moderate at 0.80, D severe at 0.70, and E recovered at 0.60.", False, "#991b1b")
    pages.append(p6)

    gold = """# Calibration under label drift

Abstract: The paper evaluates calibration under label drift using ten equal-frequency bins and a small replay buffer. Replay improves F1 while lowering ECE.

Equation: ECE = sum_b (n_b / n) * |acc(b) - conf(b)|, with B = 10.

| Method | ECE down | F1 up | Storage |
| --- | ---: | ---: | ---: |
| Baseline | 0.087 | 0.781 | 0 |
| + temperature scaling | 0.041 | 0.779 | 0 |
| + drift prior | 0.033 | 0.802 | 12 MB |
| + replay buffer | 0.029 | 0.817 | 1.8 GB |

Reviewer note: replay is kept despite higher storage cost because it is the only row that improves both ECE and F1.

Figure 2: the gray dashed diagonal is perfect calibration. The red model curve falls below the diagonal above confidence 0.75 and is annotated "over-confident above 0.75." Residual table: A none 4.1 OK, B mild 6.7 OK, C moderate 12.4 Review, D severe 18.9 Fail, E recovered 8.2 OK.

## Supplement Table S1

| Cohort | Shift | n | ECE | F1 | Note |
| --- | --- | ---: | ---: | ---: | --- |
| A | none | 1200 | 0.029 | 0.817 | baseline final |
| B | mild | 840 | 0.034 | 0.804 | uses drift prior |
| C | moderate | 610 | 0.052 | 0.781 | see footnote 1 |
| D | severe | 455 | 0.071 | 0.744 | fails threshold |
| E | recovered | 500 | 0.038 | 0.799 | replay restored |
| Total | | 3605 | | | count total; do not average ECE |

Footnote 1: Cohort C excludes 17 records with missing confidence, so reported n is after exclusion. The total row is a count total, not an ECE average.

## Drift error matrix

Legend: L low error, M medium error, H high error, slash means manual review required.

| Cohort | 0.50 | 0.60 | 0.70 | 0.80 | 0.90 |
| --- | --- | --- | --- | --- | --- |
| A none | L | L | M | M | H |
| B mild | L | M | M | H | H |
| C moderate | M | M | H | H with slash | H |
| D severe | M | H | H with slash | H | H |
| E recovered | L | M with slash | M | H | M |

Cohort D has high error in every bin from 0.60 through 0.90. E recovered at 0.90 is medium, not high. Manual review slash cells are C moderate at 0.80, D severe at 0.70, and E recovered at 0.60.
"""
    return Case(
        "P04-scientific-supplement",
        "Scientific Supplement Packet",
        "scientific",
        ["landscape", "scientific", "equation", "continuation", "matrix", "chart"],
        "Recover a denser landscape scientific supplement with equations, curves, repeated-header continuation, footnotes, and matrix semantics.",
        "Six-page landscape supplement.",
        ["equation", "ablation", "curve", "continued table", "matrix"],
        ["Merge continuation tables.", "Preserve visual figure/matrix semantics.", "Do not average the total row."],
        gold,
        [near_check("p04-d-row", "table_cell", ["D", "severe", "455", "0.071", "0.744"], 4, 600)],
        pages,
        facts=[
            fact("p04.equation", "formula", 6, "Equation is ECE = sum_b (n_b / n) * |acc(b) - conf(b)| with B = 10."),
            fact("p04.ablation", "table_cell", 8, "Ablation table preserves all methods, ECE, F1, and storage values, including replay buffer 0.029/0.817/1.8 GB."),
            fact("p04.figure", "visual_relation", 8, "Figure 2 preserves perfect calibration diagonal, red curve below diagonal above 0.75, and over-confident annotation."),
            fact("p04.residuals", "table_cell", 6, "Residual table preserves A 4.1 OK, B 6.7 OK, C 12.4 Review, D 18.9 Fail, E 8.2 OK."),
            fact("p04.continuation", "cross_page_binding", 9, "Supplement Table S1 is one logical table across pages with repeated headers not treated as data."),
            fact("p04.rows", "table_cell", 9, "Rows A-E and Total preserve shift, n, ECE, F1, and notes, including D severe 455/0.071/0.744 and Total 3605 count total."),
            fact("p04.footnote", "cross_page_binding", 6, "Footnote says Cohort C excludes 17 records with missing confidence and total row is not an ECE average."),
            fact("p04.matrix", "visual_relation", 10, "Error matrix preserves L/M/H values and slash cells C moderate 0.80, D severe 0.70, and E recovered 0.60."),
            fact("p04.caption", "visual_relation", 6, "Caption says Cohort D has high error from 0.60 through 0.90 and E recovered at 0.90 is medium, not high."),
        ],
    )


def packet_noc_handover() -> Case:
    pages: list[Image.Image] = []
    p1 = deck_page("NOC handover", "week 32 reliability packet", True)
    d = ImageDraw.Draw(p1)
    d.text((90, 230), "This packet is assembled from exported slides, status dashboards, and shift notes. Reconstruct each artifact; do not summarize.", fill="#f8fafc", font=F["h2"])
    deck_card(d, (90, 420, 610, 715), "Primary risks", "Release gate spans 10:00-16:30.\nHIPAA BAA is Security, not Product.\nExport Friday is yellow, not red.", True)
    deck_card(d, (680, 420, 1200, 715), "Artifacts", "Raster Gantt\nOverlapping GTM timeline\nBorderless team matrix\nEscalation heatmap\nPager rota", True)
    deck_card(d, (1270, 420, 2030, 715), "Handoff notes", "Page order follows the operations packet.\nTables are working notes.\nChart-only regions record visual status.\nDiagram regions show operational flow.", True)
    pages.append(p1)

    # Gantt slide
    p2 = deck_page("Shift Gantt", "raster schedule | infer bar spans", False)
    d = ImageDraw.Draw(p2)
    left, top = 410, 260
    for i, t in enumerate(["08:00", "10:00", "12:00", "14:00", "16:00", "18:00"]):
        x = left + i * 250
        d.line((x, top - 20, x, top + 480), fill="#cbd5e1", width=3)
        d.text((x - 34, top - 70), t, fill="#111827", font=F["tiny_bold"])
    rows = [("Dock intake", "Noor", 0, 1.5, "Load A-17", "#2563eb"), ("Release gate", "Ken", 1, 4.25, "REL-82", "#0f766e"), ("QA bench", "Priya", 2, 3.5, "Lot Q4", "#7c3aed"), ("Rollback watch", "Mira", 4, 5, "RB-9", "#dc2626")]
    for r, (task, owner, start, end, label, color) in enumerate(rows):
        y = top + r * 110
        d.text((90, y + 12), task, fill="#111827", font=F["small_bold"])
        d.text((90, y + 48), owner, fill="#475569", font=F["tiny"])
        d.rectangle((left + int(start * 250), y, left + int(end * 250), y + 60), fill=color)
        d.text((left + int(start * 250) + 16, y + 17), label, fill="white", font=F["tiny_bold"])
    pages.append(p2)

    # Timeline slide
    p3 = deck_page("Overlapping GTM timeline", "lane binding and dependency notes", True)
    d = ImageDraw.Draw(p3)
    months = ["Aug", "Sep", "Oct", "Nov"]
    for i, m in enumerate(months):
        x = 520 + i * 330
        d.text((x, 175), m, fill="#f8fafc", font=F["small_bold"])
        d.line((x, 220, x, 980), fill="#24345f", width=3)
    lanes = [("Product", 310), ("Security", 520), ("Sales", 730)]
    for lane, y in lanes:
        d.text((110, y + 28), lane, fill="#f8fafc", font=F["small_bold"])
    cards = [("Beta signups", "Maya", "1,200", 520, 315, 250, "#2563eb"), ("Workflow v2", "Jon", "ship Oct 18", 850, 315, 520, "#0f766e"), ("SOC2 audit", "Priya", "Aug-Oct", 520, 525, 750, "#7c3aed"), ("HIPAA BAA", "Lena", "Oct-Nov", 1180, 525, 420, "#dc2626"), ("Design partners", "Omar", "9 accts", 520, 735, 250, "#f59e0b"), ("Enterprise pilots", "Omar", "$4.2M", 850, 735, 760, "#14b8a6")]
    for title, owner, note, x, y, w, color in cards:
        d.rectangle((x, y, x + w, y + 82), fill=color)
        d.text((x + 12, y + 12), title, fill="white", font=F["tiny_bold"])
        d.text((x + 12, y + 42), f"{owner} | {note}", fill="white", font=F["tiny"])
    deck_card(d, (90, 985, 2060, 1160), "Dependency note", "HIPAA BAA belongs to Security, not Product. Enterprise pilots depend on BAA legal review.", True, "#dc2626")
    pages.append(p3)

    # Team matrix
    p4 = deck_page("Borderless team matrix", "columns are people; rows are implied by alignment", False)
    d = ImageDraw.Draw(p4)
    people = [("Maya Singh", "CEO / Product", "ex-Stripe", "led Relay launch"), ("Jon Bell", "CTO / Infra", "ex-Snowflake", "built vector cache"), ("Priya Nair", "COO / Ops", "ex-Flexport", "owns compliance"), ("Omar Haddad", "GTM / RevOps", "ex-Atlassian", "$4.2M pipeline")]
    for i, (name, role, former, proof) in enumerate(people):
        x = 280 + i * 440
        d.ellipse((x + 100, 210, x + 210, 320), fill="#f8fafc", outline="#b91c1c", width=5)
        d.text((x, 360), name, fill="#111827", font=F["small_bold"])
        for j, txt in enumerate([role, former, proof]):
            d.text((x, 485 + j * 145), txt, fill="#111827", font=F["small"])
    for j, label in enumerate(["Role", "Former", "Proof"]):
        d.text((90, 485 + j * 145), label, fill="#64748b", font=F["small_bold"])
        d.line((180, 522 + j * 145, 2000, 522 + j * 145), fill="#e5e7eb", width=3)
    deck_card(d, (90, 960, 960, 1130), "Advisors", "Lena Ortiz - former CISO, Okta. Theo Park - ex-CFO, Datadog.", False)
    deck_card(d, (1080, 960, 1980, 1130), "Hiring next", "VP Sales - Q4. Clinical Lead - Q1. These are open roles, not current employees.", False, "#c2410c")
    pages.append(p4)

    # Heatmap
    p5 = deck_page("Escalation heatmap", "letter + color + slash + weekend semantics", False)
    d = ImageDraw.Draw(p5)
    teams = ["API", "Data", "Export", "Billing"]
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    vals = [["G", "Y", "Y", "R", "R", "Y"], ["G", "G", "Y", "Y", "R", "R"], ["Y", "Y", "R", "R", "Y", "G"], ["G", "Y", "G", "Y", "Y", "R"]]
    slash = {("API", "Thu"), ("Data", "Fri"), ("Export", "Wed"), ("Billing", "Sat")}
    colors = {"G": "#dcfce7", "Y": "#fef3c7", "R": "#fee2e2"}
    x0, y0 = 430, 250
    for c, day in enumerate(days):
        d.text((x0 + c * 225 + 35, y0 - 55), day, fill="#111827", font=F["small_bold"])
    for r, team in enumerate(teams):
        y = y0 + r * 135
        d.text((120, y + 42), team, fill="#111827", font=F["small_bold"])
        for c, day in enumerate(days):
            key = vals[r][c]
            x = x0 + c * 225
            d.rectangle((x, y, x + 150, y + 92), fill=colors[key], outline="#111827", width=3)
            d.text((x + 62, y + 30), key, fill="#111827", font=F["small_bold"])
            if (team, day) in slash:
                d.line((x + 10, y + 10, x + 140, y + 82), fill="#991b1b", width=5)
    deck_card(d, (1220, 850, 2040, 1080), "Legend", "G green normal. Y yellow watch. R red escalation. Slash means owner must page incident lead. Export Friday is yellow, not red.", False, "#991b1b")
    pages.append(p5)

    # Rota / pager slide
    p6 = deck_page("Pager rota + escalation contacts", "carry-down groups and ditto marks", True)
    d = ImageDraw.Draw(p6)
    rows = [["Team", "Person", "Station", "Start", "End", "Escalation"], ["Kitchen", "Ravi", "Prep", "06:00", "10:00", "Noor"], ["", "Mina", "Service", "10:00", "14:00", "Noor"], ["", "Omar", "Close", "14:00", "18:00", "Ken"], ["Dock", "Chen", "Load", "07:00", "11:00", "Priya"], ["", "Jules", "Audit", "11:00", "15:00", "Priya"], ["''", "Ken", "Security", "18:00", "22:00", "Mira"]]
    deck_table(d, 120, 230, [240, 230, 230, 170, 170, 260], rows, True, 62)
    deck_card(d, (120, 850, 1940, 1050), "Carry-down rule", "Blank team cells inherit the previous team. Ditto marks inherit the previous station group. The final row belongs to Dock, not Kitchen.", True, "#dc2626")
    pages.append(p6)

    gold = """# NOC handover - week 32 reliability packet

This packet is assembled from exported slides, status dashboards, and shift notes. Reconstruct each artifact and preserve page order.

## Shift Gantt

| Task | Owner | Start | End | Label |
| --- | --- | --- | --- | --- |
| Dock intake | Noor | 08:00 | 11:00 | Load A-17 |
| Release gate | Ken | 10:00 | 16:30 | REL-82 |
| QA bench | Priya | 12:00 | 15:00 | Lot Q4 |
| Rollback watch | Mira | 16:00 | 18:00 | RB-9 |

## Overlapping GTM timeline

Product lane: Beta signups in August owned by Maya target 1,200; Workflow v2 spans September-October owned by Jon and ships Oct 18. Security lane: SOC2 audit spans August-October owned by Priya; HIPAA BAA spans October-November owned by Lena. Sales lane: Design partners in August owned by Omar with 9 accounts; Enterprise pilots span September-November owned by Omar with $4.2M pipeline. HIPAA BAA belongs to Security, not Product. Enterprise pilots depend on BAA legal review.

## Borderless team matrix

Maya Singh is CEO/Product, ex-Stripe, and led Relay launch. Jon Bell is CTO/Infra, ex-Snowflake, and built vector cache. Priya Nair is COO/Ops, ex-Flexport, and owns compliance. Omar Haddad is GTM/RevOps, ex-Atlassian, with $4.2M pipeline.

Advisors: Lena Ortiz former CISO at Okta and Theo Park ex-CFO at Datadog. Hiring next: VP Sales Q4 and Clinical Lead Q1 are open roles, not employees.

## Escalation heatmap

Legend: G green normal, Y yellow watch, R red escalation, slash means owner must page incident lead.

| Team | Mon | Tue | Wed | Thu | Fri | Sat |
| --- | --- | --- | --- | --- | --- | --- |
| API | G | Y | Y | R with slash | R | Y |
| Data | G | G | Y | Y | R with slash | R |
| Export | Y | Y | R with slash | R | Y | G |
| Billing | G | Y | G | Y | Y | R with slash |

Critical slash cells are API Thu, Data Fri, Export Wed, and Billing Sat. Export Friday is yellow, not red. Saturday is in scope.

## Pager rota

Blank team cells inherit the previous team. Ditto marks inherit the previous station group. Kitchen rows are Ravi, Mina, and Omar. Dock rows are Chen, Jules, and Ken. Ken is Dock/Security from 18:00 to 22:00 with escalation Mira.
"""
    return Case(
        "P06-noc-handover-packet",
        "NOC Handover Packet",
        "deck",
        ["landscape", "handover", "gantt", "timeline", "matrix", "heatmap", "carry-down"],
        "Recover a realistic dense NOC handover deck with spatial bars, lane bindings, borderless person matrix, heatmap encodings, and carry-down rota semantics.",
        "Six-page landscape handover deck.",
        ["gantt", "timeline", "team matrix", "heatmap", "pager rota"],
        ["Infer spatial spans.", "Preserve row/column bindings.", "Apply carry-down semantics."],
        gold,
        [near_check("p06-release-gate", "spatial", ["Release gate", "Ken", "10:00", "16:30", "REL-82"], 4, 600)],
        pages,
        facts=[
            fact("p06.gantt", "spatial", 10, "All four Gantt rows preserve task, owner, inferred start/end, and label."),
            fact("p06.timeline.product", "visual_relation", 6, "Product lane preserves Beta signups/Maya/1,200 in Aug and Workflow v2/Jon/ship Oct 18 spanning Sep-Oct."),
            fact("p06.timeline.security", "visual_relation", 6, "Security lane preserves SOC2 audit/Priya/Aug-Oct and HIPAA BAA/Lena/Oct-Nov."),
            fact("p06.timeline.sales", "visual_relation", 6, "Sales lane preserves Design partners/Omar/9 accounts and Enterprise pilots/Omar/$4.2M Sep-Nov."),
            fact("p06.timeline.dependency", "visual_relation", 5, "HIPAA BAA belongs to Security, not Product; Enterprise pilots depend on BAA legal review."),
            fact("p06.matrix", "visual_relation", 8, "Team matrix binds each person to correct role, former company, and proof/pipeline fact."),
            fact("p06.sidebars", "structure", 4, "Advisors and hiring roles are kept separate from core team members."),
            fact("p06.heatmap", "visual_relation", 10, "Heatmap preserves G/Y/R values, slash semantics, slash cells API Thu/Data Fri/Export Wed/Billing Sat, Export Friday yellow, and Saturday column."),
            fact("p06.rota", "table_cell", 8, "Pager rota applies carry-down: Kitchen rows Ravi/Mina/Omar; Dock rows Chen/Jules/Ken; Ken Dock Security 18:00-22:00 escalation Mira."),
        ],
    )


def packet_real_push_investor_reference_active_disabled() -> Case:
    source = Path("/Users/aayush/Downloads/decks_for_testing/Push-Investor-Deck.pdf")
    gold = """# Push Sports Investor Deck

The deck presents Push Sports as a full-stack sports-led fitness and training platform providing access to professionally run and digitally connected playing arenas.

Important visible facts include:

- Problem: lack of physical activity causes health ailments in kids and young adults; 33% of kids and teenagers studying in private schools are obese according to an AIIMS study.
- Screen-time problem: NIH study links high screen time to thinning of the brain cortex and lower test scores; 66.6% of under-5 kids with screen exposure above 3 hours had no parent interaction, delayed speech, hyperactivity, and low attention span.
- Sports is positioned as a time-tested go-to fitness regime with proven physical and mental health benefits, superior retention rates above 80%, and more calories burned per rupee/time than gyms or fitness classes.
- Broken sports ecosystem opportunity: USD 20B+ opportunity with five issues: poor quality sports infrastructure, absence of competitive platforms for under-12, declining open spaces, unavailable hyper-local sports communities, and below-par coaching curriculum/coaches.
- Market page: total addressable market USD 2.4B at ARR INR 30k; potential sports-playing customers about 6 million; 63 million population ages 6-44 in top 20 Indian cities; serviceable market USD 2B+; 6 million SEC A customers age 7-44 in top 20 cities; USD 100M+ potential annual revenue with about 700 arenas.
- Approach: phygital ecosystem for venue and player discovery, booking, payment, and performance monitoring; safe professionally run arenas with multisport day/night facilities; pay-and-play plus coaching, leagues, live scoring/officiating/streaming.
- Business model building blocks: Push Stadia, Push Hubs, and value-added services. Stadia and Hubs have CAPEX INR 3 million per facility including advances, occupancy 200-240 hours/month, yield about INR 2.5K/hour, gross margins about 50%, and rent/overheads about INR 150K/month.
- Go-to-market plan: targets U-14 kids, young adults, private schools/colleges, top 20 cities, and societies/clubs. Key numbers: coaching INR 3000/month, pay-and-play INR 500/game, CAC INR 700, LTV INR 200K+.
- Competitive scorecard: Push Sports and Fitso both total 24, Cult.fit totals 22, Playo 17, and Hudle 8. Range key is 1-5 with 0 not present and 5 market leading.
- Proof of concept arenas include The Pushers Den Baliyawas Gurgaon, The Dome Gurgaon, DPS Gurgaon, Sushant University Gurgaon, Tulip Violet Society Sector 69 Gurgaon, Presidium School Mayfield Gardens Gurgaon, and The Amari Sector 59 Gurgaon.
- P&L page includes monthly revenue and expense lines from Apr-21 through Mar-22, with March 2022 total revenue 18,25,940, operating profit 8,16,400, profit before tax 3,73,551, and profit after tax 2,07,733.
- Team page includes co-founders Nitin Pahuja, Puru Singh, and Mukul Grover.

## Full extracted text reference

The following is the full selectable text extracted from the PDF in page order. A faithful Doc2MD answer should preserve this information, while also describing photos, layouts, diagrams, scorecards, tables, and other visual content that is not captured by the text layer.

""" + pdf_text_reference(source)
    return Case(
        "P01-board-ops-packet",
        "Push Sports Investor Deck",
        "real-deck",
        ["real-pdf", "pitch-deck", "market", "scorecard", "financials", "photos"],
        "Evaluate faithful Markdown reconstruction on a real 34-page Push Sports investor deck with dense tables, diagrams, photos, market sizing, scorecards, and financials.",
        "External PDF from Downloads/decks_for_testing.",
        ["problem", "market sizing", "business model", "go-to-market", "scorecard", "financials", "team"],
        ["Preserve dense slide facts and tables.", "Do not collapse into a generic pitch summary.", "Capture numeric market and financial values."],
        gold,
        [near_check("push-market", "text", ["USD 2.4 Bn", "6 Million", "63 Million", "USD 100 MM"], 5, 1000)],
        [],
        facts=[
            fact("push.cover", "text", 4, "Cover states Push Sports is a sports-led fitness/training platform providing access to professionally run and digitally connected playing arenas."),
            fact("push.problem.obesity", "text", 6, "Problem slide preserves 33% kids and teenagers in private schools are obese and cites AIIMS study."),
            fact("push.problem.screen", "text", 6, "Screen-time slide preserves NIH cortex/test-score claim and 66.6% under-5 kids with >3 hours exposure had no parent interaction/delayed speech/hyperactivity/low attention span."),
            fact("push.ecosystem", "visual_relation", 7, "Broken ecosystem slide preserves the five numbered ecosystem problems and the USD 20B+ opportunity."),
            fact("push.market", "text", 9, "Market slide preserves USD 2.4B TAM, ARR INR 30k, about 6M customers, 63M population ages 6-44 in top 20 cities, USD 2B+ serviceable market, and USD 100M+ annual revenue with about 700 arenas."),
            fact("push.approach", "text", 5, "Approach slide preserves phygital venue/player discovery, booking, payment, performance monitoring, day/night facilities, coaching, leagues, live scoring/officiating/streaming."),
            fact("push.business.blocks", "table_cell", 8, "Business model slide preserves Push Stadia, Push Hubs, and value-added services with CAPEX INR 3M, occupancy 200-240 hrs/month, yield INR 2.5K/hour, gross margins about 50%, and rent/overheads INR 150K/month for Stadia/Hubs."),
            fact("push.gtm", "visual_relation", 7, "Go-to-market slide preserves target segments and key numbers: coaching INR 3000/month, pay-and-play INR 500/game, CAC INR 700, LTV INR 200K+."),
            fact("push.scorecard", "table_cell", 10, "Competitive scorecard preserves totals: Push Sports 24, Fitso 24, Cult.fit 22, Playo 17, Hudle 8, plus range key 0 not present and 5 market leading."),
            fact("push.poc", "visual_relation", 6, "Proof-of-concept arenas slide preserves the listed venue names including Pushers Den, The Dome, DPS Gurgaon, Sushant University, Tulip Violet Society, Presidium School, and The Amari."),
            fact("push.pnl", "table_cell", 10, "Financial P&L page preserves March 2022 total revenue 18,25,940, operating profit 8,16,400, profit before tax 3,73,551, and profit after tax 2,07,733."),
            fact("push.team", "text", 5, "Team slide includes co-founders Nitin Pahuja, Puru Singh, and Mukul Grover."),
        ],
        source_pdf=source,
        page_count_override=34,
    )


def packet_real_nxlvl_reference_active_disabled() -> Case:
    source = Path("/Users/aayush/Downloads/decks_for_testing/nXlvl 13012025 - FINAL PITCHDECK.pdf")
    gold = """# nXlvl Pitch Deck

The deck presents nXlvl as a social-media platform for athletes, musicians, and talent in India to build, manage, promote, and monetize themselves and their personal brand.

Important visible facts include:

- Opening: nXlvl tagline is "Athletes - Musicians - Talent" and "your link, your now, your next level." The deck says take it to the next level.
- Why nXlvl: there are 1.4 billion people in India, less than 0.01% truly make it, and the rest have dreams lost and talent wasted.
- Problem: no apps, platforms, or services today where talent, performers, and organizations can easily build, manage, promote, and monetize their product, which is themselves and their personal brand.
- Challenges faced by talents are split into systemic and individual challenges: platform/ecosystem gaps, visibility/exposure barriers, growth/support deficiencies, and individual brand/network constraints.
- Promise: nXlvl democratizes access to recognition and opportunities for athletes and talent in India, levelling the playing field regardless of background or location, with the line "You've got the talent; We have the platform!"
- Unique audiences: for athletes, for fandom, and for sponsors.
- Athlete uniqueness comparison: nXlvl offers skills-based visibility, unified athlete identity profile, direct athlete-coach-scout-brand connections, sport/talent-specific communities, skill-relevant feedback, community engagement impacts discovery, and monetization/sustainability through brands, ads, contests, and fan clubs.
- Fandom comparison: fans become part of the growth story of favorite athletes; direct connection with grassroots/emerging athletes; fan rewards such as merch, meet-ups, and discounts; multi-sport/music/cultural talent ecosystem.
- Sponsor comparison: brands buy relationships rather than exposure; market access, talent discovery, sponsorships, decision making, cost efficiency, and transparency through blockchain ledger and smart contracts.
- Difference slide: nXlvl core purpose is talent discovery and monetization; algorithm is skill-first and verified discovery; tools include stats and achievements; monetization includes ads, sponsorships, and recruiter deals; users are niche talent/fans/recruiters/brands. Other social media is entertainment, engagement-first, filters/reels/shorts, ads only for influencers, broad users.
- Competition slide maps nXlvl across OTT/streaming content, talent discovery/recruitment, local sports booking/access, gamification/leaderboards, athlete branding/profiles, data insights for sponsors, performance analytics, and communities.
- Revenue streams include Google AdMob, Google AdSense, affiliate marketing, direct response advertising, premium access for recruiters, fan management, subscription services, and advertising/sponsorship.

## Full extracted text reference

The following is the full selectable text extracted from the PDF in page order. A faithful Doc2MD answer should preserve this information, while also describing screenshots, comparison matrices, diagrams, positioning maps, and other visual content that is not captured by the text layer.

""" + pdf_text_reference(source)
    return Case(
        "P04-scientific-supplement",
        "nXlvl Pitch Deck",
        "real-deck",
        ["real-pdf", "pitch-deck", "comparison", "diagrams", "ui-screens", "market"],
        "Evaluate reconstruction on the real nXlvl pitch deck with dark branded slides, comparison matrices, diagrams, UI screenshots, and visual positioning maps.",
        "External PDF from Downloads/decks_for_testing.",
        ["problem", "promise", "audience comparisons", "competition map", "revenue streams"],
        ["Preserve slide order and comparison structures.", "Capture visual diagrams and audience-specific claims.", "Do not summarize the pitch into generic startup prose."],
        gold,
        [near_check("nxlvl-problem", "text", ["Build", "Manage", "Promote", "Monetize", "Personal Brand"], 5, 900)],
        [],
        facts=[
            fact("nxlvl.opening", "text", 4, "Opening preserves nXlvl, Athletes-Musicians-Talent tagline, and take it to the next level."),
            fact("nxlvl.why", "text", 6, "Why nXlvl slide preserves 1.4 billion people in India, less than 0.01% truly make it, and rest have dreams/talent wasted."),
            fact("nxlvl.problem", "text", 7, "Problem slide preserves no apps/platforms/services where Talent, Performers, and Organizations can build, manage, promote, and monetize themselves/their personal brand."),
            fact("nxlvl.challenges", "visual_relation", 8, "Challenges slide preserves four quadrants: platform/ecosystem gaps, visibility/exposure barriers, growth/support deficiencies, individual brand/network constraints, with systemic vs individual/access vs amplification axes."),
            fact("nxlvl.promise", "visual_relation", 7, "Promise slide preserves democratized access to recognition/opportunities, levelling playing field, build/promote brand, connect with fans, create revenue streams, regardless of background/location, all in one place for free."),
            fact("nxlvl.unique.audiences", "structure", 4, "Audience slide preserves three categories: For Athletes, For Fandom, For Sponsors."),
            fact("nxlvl.athletes", "table_cell", 8, "Athlete comparison preserves skills-based visibility, unified profile, direct athlete-coach-scout-brand connections, sport communities, feedback, and monetization/sustainability differences vs Instagram/YouTube."),
            fact("nxlvl.fandom", "table_cell", 7, "Fandom comparison preserves emotional connection, access to athletes, rewards, and content diversity vs polished highlights and star athletes only."),
            fact("nxlvl.sponsors", "table_cell", 8, "Sponsor comparison preserves brands buy relationships, market access, talent discovery, sponsorships, decision making, cost efficiency, and transparency with blockchain ledger/smart contracts."),
            fact("nxlvl.different", "table_cell", 8, "How are we different slide preserves nXlvl vs other social media across core purpose, algorithm, tools, monetization, and users."),
            fact("nxlvl.competition", "visual_relation", 6, "Competition map preserves nXlvl at next level in the center and surrounding categories including OTT/streaming, talent discovery, booking/access, gamification, athlete profiles, data insights, performance analytics, and communities."),
            fact("nxlvl.revenue", "text", 6, "Revenue streams include Google AdMob, Google AdSense, affiliate marketing, direct response advertising, premium recruiter access, fan management, subscription services, and advertising/sponsorship."),
        ],
        source_pdf=source,
        rasterize_source_pdf=True,
        page_count_override=23,
    )


def packet_real_push_pitch_reference_active_disabled() -> Case:
    source = Path("/Users/aayush/Downloads/decks_for_testing/Push-Sports-pitch-deck.pdf")
    gold = """# Push Sports Pitch Deck

The deck presents Push Sports as a full-stack platform of multi-sport arenas offering professional sports coaching and pay-to-play facilities for kids and young adults at schools, societies, and clubs.

Important visible facts include:

- Problem: physical inactivity drives health-related ailments in kids and young adults; about 4/10 private-school kids are obese. Sports ecosystem is broken due to lack of quality infrastructure, coaching talent, and engagement. There is a lack of reliable, professionally run, digitally connected sports arenas and training brands. Over 50K schools, societies, and clubs have sports infrastructure but not expertise to run it.
- Solution: phygital ecosystem for venue/player discovery, booking, and payments. Safe, professionally run, conveniently located sports arenas in academic institutions, societies, and clubs with multisport day/night facilities. Professional sports training infrastructure and manpower plus corporate/personal events.
- Business model: partner/lease school/RWA/club facilities and upgrade them. Subscription and pay-and-play model; training subscriptions INR 4800+ and pay-and-play customers INR 2000+. Current customers: 300+ training subscribers, 1000+ pay-and-play customers, 40+ corporate clients, 7 locations in Delhi NCR.
- USP: ties with academic institutions, sport stars, IPL franchise; self-run/franchised centers deliver standardized customer experience and pricing power; IP for sports leagues drives retention and occupancy.
- Founding team: Puru Singh and Nitin Pahuja. Puru includes St Stephens/IIM-C, ex-Ranji Trophy, ICC level 2 coach, B2C business, curriculum design, new infra development, coach training, Air India, DCA, Sports Maidan, Push Sports. Nitin includes MBA, Great Lakes/Delhi School of Economics, finance/commercial, B2B sales, digital product, franchise management, HT Media, Yes Bank, Push Sports.
- Traction/projection: average monthly revenue 12 lacs, total bootstrapped amount 80 lacs, total transactions per month 170, operating/net margin 45%/16%, average transaction value INR 8250, total training customers/MRR 170/INR 4800, average margin per transaction 60%-70%, total pay-and-play customers 1000.
- Projection table: FY 2022-23 centers 45, revenue 615 lacs, opex 464 lacs, operating profit 151, CAPEX 348, operating cash flow -312. FY 2023-24 centers 122, revenue 2,155, opex 1,411, operating profit 744, CAPEX 672, operating cash flow -387. FY 2024-25 centers 261, revenue 6,352, opex 3,862, operating profit 2,490, CAPEX 1,149, operating cash flow -6.
- Cap table: founders 74.5%, friends and family 25.5%, investors 0, advisors 0, ESOP 0. Previous rounds: 2021 post-money valuation 3.35 CR dilution 10.5% investor Salman Moin; 2020 post-money valuation 2.3 CR dilution 15% investor Mukul Grover.
- Ask: INR 2 CR at INR 8 CR pre-money valuation. Valuation logic includes DCF cost of capital 20%, INR 10 CR post-money valuation, and post-money SAFE. Investment case includes about 40% private-school kids obese, 84% parents worried about screen time, USD 20B+ health/fitness/wellness market with 20%+ CAGR, serviceable market 60M individuals/USD 2B, and 3X-4X return horizon.

## Full extracted text reference

The following is the full selectable text extracted from the PDF in page order. A faithful Doc2MD answer should preserve this information, while also describing slide layouts, diagrams, projections, cap-table structure, and other visual content that is not captured by the text layer.

""" + pdf_text_reference(source)
    return Case(
        "P06-noc-handover-packet",
        "Push Sports Pitch Deck",
        "real-deck",
        ["real-pdf", "pitch-deck", "business-model", "financials", "team", "ask"],
        "Evaluate reconstruction on the concise real Push Sports pitch deck, including dense business model text, team bios, projections, cap table, and ask slide.",
        "External PDF from Downloads/decks_for_testing.",
        ["problem/solution", "business model", "team", "traction", "projections", "cap table", "ask"],
        ["Preserve numeric business facts.", "Capture tables and team bios.", "Do not convert deck into a high-level summary."],
        gold,
        [near_check("push-pitch-ask", "text", ["INR 2 CR", "INR 8 Cr", "20%", "INR 10 CR"], 5, 900)],
        [],
        facts=[
            fact("pushpitch.problem", "text", 8, "Problem section preserves 4/10 private-school kids obese, broken sports ecosystem, lack of reliable digitally connected arenas, and 50K+ institutions with infra but not expertise."),
            fact("pushpitch.solution", "text", 6, "Solution preserves phygital ecosystem for discovery/booking/payments and safe professionally run multisport day/night arenas in schools/societies/clubs."),
            fact("pushpitch.business", "text", 8, "Business model preserves lease/partner facilities, subscription/pay-play model, INR 4800+ training subscriptions, INR 2000+ pay-play customers, 300+ subscribers, 1000+ pay-play customers, 40+ corporate clients, 7 Delhi NCR locations."),
            fact("pushpitch.usp", "text", 5, "USP preserves ties with institutions/sport stars/IPL franchise, standardized centers/pricing power, and sports-league IP driving retention/occupancy."),
            fact("pushpitch.team.puru", "text", 6, "Puru Singh bio preserves St Stephens/IIM-C, ex-Ranji Trophy, ICC level 2 coach, B2C, curriculum, infra, coach training, Sports Maidan, Push Sports."),
            fact("pushpitch.team.nitin", "text", 6, "Nitin Pahuja bio preserves MBA/Great Lakes/Delhi School of Economics, finance/commercial, B2B sales, digital product, franchise management, HT Media, Yes Bank, Push Sports."),
            fact("pushpitch.traction", "table_cell", 10, "Traction metrics preserve average monthly revenue 12 lacs, bootstrapped 80 lacs, transactions/month 170, operating/net margin 45%/16%, ATV INR 8250, training customers/MRR 170/INR 4800, margins 60-70%, pay-play customers 1000."),
            fact("pushpitch.projection", "table_cell", 10, "Projection table preserves FY 2022-23/2023-24/2024-25 centers 45/122/261, revenue 615/2155/6352, opex 464/1411/3862, operating profit 151/744/2490, CAPEX 348/672/1149, cash flow -312/-387/-6."),
            fact("pushpitch.cap", "table_cell", 8, "Cap table preserves founders 74.5%, friends and family 25.5%, investors/advisors/ESOP 0, and previous rounds 2021 3.35 CR 10.5% Salman Moin; 2020 2.3 CR 15% Mukul Grover."),
            fact("pushpitch.ask", "text", 8, "Ask slide preserves INR 2 CR at INR 8 CR pre-money, DCF cost of capital 20%, INR 10 CR post-money, post-money SAFE, USD 20B+ market, 60M/USD 2B serviceable market, and 3X-4X return horizon."),
        ],
        source_pdf=source,
        rasterize_source_pdf=True,
        page_count_override=7,
    )


def packet_manufacturing_batch_capa() -> Case:
    def page(title: str, subtitle: str) -> Image.Image:
        img = Image.new("RGB", (PAGE_W, PAGE_H), "#ffffff")
        d = ImageDraw.Draw(img)
        d.text((72, 58), "AltaForge Therapeutics | Batch record BR-26-0417 | Product AF-12 tablets", fill="#334155", font=F["tiny_bold"])
        d.text((72, 92), title, fill="#111827", font=F["h1"])
        d.text((72, 132), subtitle, fill="#475569", font=F["small"])
        d.line((72, 178, 1580, 178), fill="#cbd5e1", width=2)
        d.text((1390, 60), "QA copy | 2026-07-02", fill="#111827", font=F["small_bold"])
        return img

    pages: list[Image.Image] = []

    p1 = page("Batch Summary and Release State", "Lot AF12-260701A; visible final QA status controls")
    d = ImageDraw.Draw(p1)
    draw_kv_band(
        d,
        82,
        235,
        [
            ("Product", "AF-12 50 mg"),
            ("Batch", "AF12-260701A"),
            ("Mfg date", "2026-07-01"),
            ("Target yield", "120,000 tablets"),
            ("Final state", "QA HOLD"),
        ],
        [260, 280, 250, 310, 250],
    )
    draw_card(d, (90, 430, 505, 650), "Release", ["QA HOLD", "Deviation D-26-014 open", "CAPA C-241 evidence due"], "#fff7ed", "#c2410c")
    draw_card(d, (555, 430, 970, 650), "Disposition", ["Packaged: 116,820", "Quarantine: 2,400", "Rejected: 780"], "#f8fafc", "#334155")
    draw_card(d, (1020, 430, 1510, 650), "Critical note", ["Draft traveler says released", "Final QA page supersedes draft", "Do not mark released"], "#fee2e2", "#991b1b")
    rows = [
        ["Stage", "Started", "Ended", "Room", "Operator", "Status"],
        ["Dispense", "07:12", "08:05", "D-102", "RN", "complete"],
        ["Blend", "08:30", "09:45", "M-204", "SL", "complete"],
        ["Compression", "10:20", "13:40", "T-18", "KP", "deviation opened"],
        ["Coating", "14:10", "15:35", "C-07", "MR", "complete"],
        ["Pack-out", "16:05", "17:20", "PK-3", "AJ", "hold labels pending QA"],
    ]
    draw_ledger(d, 90, 765, [210, 150, 150, 150, 150, 400], rows, 58)
    draw_note(d, (95, 1235, 1510, 1455), "Visible source-state warning", "Page 9 final QA disposition controls over the draft traveler footer on page 6. Lot AF12-260701A is on QA HOLD until CAPA C-241 evidence is attached and deviation D-26-014 is closed.", "#991b1b")
    pages.append(p1)

    p1b = page("Executed Step Log and Correction Trail", "Chronology, initials, and single-line GMP corrections")
    d = ImageDraw.Draw(p1b)
    rows = [
        ["Step", "Instruction / observation", "Actual", "Time", "Operator", "Verifier", "Record state"],
        ["2.4", "Weigh AF-12 API lot API-8821-6", "6.000 kg consumed", "07:28", "RN", "QA-MJ", "accepted"],
        ["3.2", "Charge blender M-204", "all dispensed material added", "08:37", "SL", "QA-MJ", "accepted"],
        ["3.7", "Lubricant return weighback", "0.050 kg returned", "09:51", "SL", "QA-MJ", "CAPA target"],
        ["4.1", "Set tablet press speed", "42 rpm", "10:22", "KP", "QA-LD", "accepted"],
        ["4.6", "Compression interruption", "12:18-12:46", "28 min", "KP", "QA-LD", "corrected"],
        ["5.3", "Coating gun balance check", "nozzle B cleaned twice", "14:52", "MR", "QA-LD", "accepted"],
        ["6.5", "Release packaging labels", "conditional only", "16:02", "AJ", "QA-TS", "hold pending QA"],
    ]
    draw_ledger(d, 35, 230, [95, 385, 285, 130, 125, 145, 245], rows, 55)
    draw_section(d, 80, 705, "GMP correction block", w=1350)
    d.text((105, 790), "Original entry: compression interruption duration 18 min", fill="#475569", font=F["small"])
    d.line((560, 808, 670, 808), fill="#991b1b", width=3)
    d.text((105, 850), "Corrected entry: 28 min", fill="#1d4ed8", font=F["italic"])
    d.text((105, 910), "Reason: stopwatch log showed restart at 12:46, not 12:36. Initials/date: KP / QA-LD / 2026-07-01.", fill="#111827", font=F["small"])
    checkbox(d, 105, 1005, "Correction uses single-line strikeout and initials", True, F["small"])
    checkbox(d, 105, 1065, "Correction changes batch release status to released", False, F["small"])
    draw_section(d, 80, 1195, "Traceability chain", w=1350)
    chain = [("MGS-0317", 120), ("Step 3.7", 360), ("D-26-014", 600), ("C-241-B", 840), ("QA HOLD", 1080), ("blank final release", 1320)]
    for label, x in chain:
        d.rounded_rectangle((x, 1320, x + 170, 1408), radius=8, outline="#334155", width=3)
        draw_text(d, (x + 12, 1342), label, F["tiny_bold"], width=13, leading=22)
    for (_, x1), (_, x2) in zip(chain, chain[1:]):
        d.line((x1 + 170, 1364, x2, 1364), fill="#334155", width=4)
        d.polygon([(x2, 1364), (x2 - 14, 1356), (x2 - 14, 1372)], fill="#334155")
    draw_note(d, (95, 1535, 1510, 1715), "Traceability note", "The correction does not close D-26-014. It links magnesium stearate lot MGS-0317 through Step 3.7 to CAPA C-241-B and the final QA HOLD state.", "#991b1b")
    pages.append(p1b)

    p2 = page("Dispensing and Material Reconciliation", "Issued, consumed, returned, and variance values must stay row-bound")
    d = ImageDraw.Draw(p2)
    rows = [
        ["Material", "Material lot", "Target kg", "Issued kg", "Consumed\nkg", "Returned\nkg", "Variance", "Status"],
        ["AF-12 API", "API-8821-6", "6.000", "6.030", "6.000", "0.030", "0.0%", "OK"],
        ["MCC PH102", "MCC-4472", "42.000", "42.200", "41.980", "0.220", "-0.05%", "OK"],
        ["Lactose monohydrate", "LAC-2209", "18.000", "18.040", "17.920", "0.120", "-0.44%", "review"],
        ["Croscarmellose", "CCS-1184", "3.600", "3.620", "3.600", "0.020", "0.0%", "OK"],
        ["Magnesium stearate", "MGS-0317", "0.900", "0.930", "0.880", "0.050", "-2.22%", "deviation link"],
        ["Opadry blue", "OPB-7320", "4.200", "4.260", "4.180", "0.080", "-0.48%", "OK"],
    ]
    draw_table(d, 36, 235, [260, 190, 125, 125, 145, 140, 130, 170], rows, 72)
    checkbox(d, 100, 845, "Scale SC-17 calibration checked before dispense", True, F["small"])
    checkbox(d, 100, 905, "Second-person material verification complete", True, F["small"])
    checkbox(d, 100, 965, "Variance investigation required", True, F["small"])
    checkbox(d, 100, 1025, "All variances within automatic release limits", False, F["small"])
    draw_note(d, (95, 1145, 1510, 1395), "Variance note", "Magnesium stearate consumed 0.880 kg versus target 0.900 kg. This is -2.22% and links to D-26-014; lactose review is informational and did not trigger the deviation.", "#9a3412")
    pages.append(p2)

    p3 = page("Line Clearance and Equipment Cleaning", "Checkbox state and blank fields are part of the record")
    d = ImageDraw.Draw(p3)
    rows = [
        ["Area / equipment", "ID", "Previous product", "Cleaned", "Verified by", "Time", "Exception"],
        ["Dispense booth", "D-102", "AF-08 placebo", "yes", "RN / QA-MJ", "06:55", "none"],
        ["Blender", "M-204", "AF-11 25 mg", "yes", "SL / QA-MJ", "08:18", "gasket inspection attached"],
        ["Tablet press", "T-18", "AF-12 trial", "yes", "KP / QA-LD", "10:05", "punch 7 replaced"],
        ["Coater", "C-07", "AF-09", "yes", "MR / QA-LD", "13:58", "spray nozzle B cleaned twice"],
        ["Packaging line", "PK-3", "AF-10", "yes", "AJ / QA-TS", "15:50", "label roll reconciliation open"],
    ]
    draw_ledger(d, 70, 245, [260, 120, 210, 125, 190, 120, 440], rows, 58)
    checkbox(d, 105, 720, "Room status labels removed before line clearance", True, F["small"])
    checkbox(d, 105, 780, "Obsolete master batch record copies destroyed", True, F["small"])
    checkbox(d, 105, 840, "Loose tablets found during clearance", False, F["small"])
    checkbox(d, 105, 900, "QA-LD accepted punch 7 replacement before restart", True, F["small"])
    draw_section(d, 90, 1040, "Equipment relation sketch", w=1340)
    boxes = [("D-102", 160, 1160), ("M-204", 430, 1160), ("T-18", 700, 1160), ("C-07", 970, 1160), ("PK-3", 1240, 1160)]
    for label, x, y in boxes:
        d.rectangle((x, y, x + 145, y + 78), outline="#334155", width=3)
        d.text((x + 30, y + 24), label, fill="#111827", font=F["small_bold"])
    for (_, x1, y1), (_, x2, y2) in zip(boxes, boxes[1:]):
        d.line((x1 + 145, y1 + 39, x2, y2 + 39), fill="#475569", width=4)
        d.polygon([(x2, y2 + 39), (x2 - 14, y2 + 31), (x2 - 14, y2 + 47)], fill="#475569")
    draw_note(d, (95, 1400, 1510, 1575), "Sketch note", "Material flow is D-102 to M-204 to T-18 to C-07 to PK-3. Punch 7 replacement belongs to tablet press T-18, not the coater.", "#1d4ed8")
    pages.append(p3)

    p4 = page("In-Process Controls", "Blend, compression, coating, and visual checks")
    d = ImageDraw.Draw(p4)
    rows = [
        ["Checkpoint", "Time", "Spec", "Result", "Initials", "Disposition"],
        ["Blend uniformity RSD", "09:38", "NMT 5.0%", "3.8%", "SL/QA", "pass"],
        ["Blend assay mean", "09:38", "95.0-105.0%", "99.4%", "SL/QA", "pass"],
        ["Tablet weight", "10:55", "410-430 mg", "422 mg", "KP", "pass"],
        ["Hardness", "11:20", "8-12 kP", "7.6 kP", "KP", "adjusted press"],
        ["Friability", "12:05", "NMT 1.0%", "0.42%", "KP", "pass"],
        ["Coating weight gain", "15:18", "2.5-3.5%", "3.1%", "MR", "pass"],
        ["Visual blue shade", "15:30", "matches standard", "slight light edge", "MR/QA", "accepted with note"],
    ]
    draw_table(d, 55, 235, [300, 125, 220, 190, 150, 360], rows, 70)
    draw_section(d, 90, 880, "Blend assay mini chart", w=1350)
    d.line((140, 1270, 1380, 1270), fill="#111827", width=2)
    d.line((140, 1270, 140, 980), fill="#111827", width=2)
    values = [98.7, 99.1, 100.2, 99.8, 99.4, 98.9]
    prev = None
    for i, value in enumerate(values):
        x = 190 + i * 190
        y = 1270 - int((value - 95) * 48)
        d.ellipse((x - 8, y - 8, x + 8, y + 8), fill="#2563eb")
        d.text((x - 20, 1295), f"S{i+1}", fill="#111827", font=F["tiny"])
        d.text((x - 24, y - 34), f"{value:.1f}", fill="#111827", font=F["tiny_bold"])
        if prev:
            d.line((prev[0], prev[1], x, y), fill="#2563eb", width=3)
        prev = (x, y)
    d.line((140, 1030, 1380, 1030), fill="#16a34a", width=2)
    d.line((140, 1270, 1380, 1270), fill="#16a34a", width=2)
    d.text((1405, 1018), "105%", fill="#16a34a", font=F["tiny_bold"])
    d.text((1405, 1258), "95%", fill="#16a34a", font=F["tiny_bold"])
    pages.append(p4)

    p5 = page("Deviation D-26-014 and CAPA C-241", "Root cause, impact assessment, and corrective actions")
    d = ImageDraw.Draw(p5)
    draw_section(d, 90, 225, "Deviation summary", w=1380)
    rows = [
        ["Field", "Value"],
        ["Deviation", "D-26-014"],
        ["Observed", "Magnesium stearate consumed 0.880 kg vs 0.900 kg target"],
        ["Detected at", "Material reconciliation after compression"],
        ["Immediate action", "Compression stopped 12:18-12:46; QA notified"],
        ["Impact", "Blend uniformity and assay passed; no reject for API potency"],
        ["Classification", "Major, not critical"],
    ]
    draw_ledger(d, 90, 305, [260, 1040], rows, 58)
    draw_section(d, 90, 760, "CAPA action plan", w=1380)
    capa = [
        ["Action", "Owner", "Due", "Status", "Evidence"],
        ["C-241-A retrain dispense operators\non lubricant return weighback", "QA-MJ", "2026-07-09", "open", "training roster"],
        ["C-241-B revise MBR step 3.7\nto require second tare check", "Process Eng", "2026-07-12", "drafted", "redline MBR-12"],
        ["C-241-C add scale SC-17 alert\nlimit at +/-1.0%", "Metrology", "2026-07-16", "not started", "change request"],
        ["C-241-D QA effectiveness check\non next three AF-12 lots", "QA-LD", "2026-08-15", "planned", "lot review log"],
    ]
    draw_table(d, 50, 835, [500, 180, 165, 175, 340], capa, 88)
    draw_note(d, (95, 1450, 1510, 1645), "Root-cause note", "Most likely root cause is tare confirmation missed after partial lubricant return. CAPA C-241 is open; final disposition is hold with conditional packaging release, not unrestricted release.", "#991b1b")
    pages.append(p5)

    p6 = page("QC Sample Manifest and Results", "Sample IDs, flags, and units are low-guessability obligations")
    d = ImageDraw.Draw(p6)
    rows = [
        ["Sample ID", "Point", "Test", "Result", "Spec", "Flag", "Analyst"],
        ["S-01", "blend top", "assay", "98.7%", "95.0-105.0%", "", "JL"],
        ["S-02", "blend middle", "assay", "99.1%", "95.0-105.0%", "", "JL"],
        ["S-03", "blend bottom", "assay", "100.2%", "95.0-105.0%", "", "JL"],
        ["T-18-043", "compression", "hardness", "7.6 kP", "8-12 kP", "OOS-investigated", "KP"],
        ["T-18-051", "compression", "weight", "422 mg", "410-430 mg", "", "KP"],
        ["C-07-018", "coating", "dissolution", "Q=82% at 30 min", "NLT 80%", "", "MR"],
        ["PK-3-022", "packaging", "label text", "matches approved art", "match", "", "AJ"],
    ]
    draw_table(d, 45, 230, [210, 180, 170, 220, 220, 230, 120], rows, 72)
    draw_note(d, (90, 880, 760, 1080), "OOS note", "The 7.6 kP hardness result is out of specification but investigated and accepted after press adjustment. It is not the magnesium stearate deviation.", "#9a3412")
    draw_note(d, (840, 880, 1510, 1080), "LIMS flag legend", "Blank flag means no exception. OOS-investigated means visible exception with investigation; it must not be omitted.", "#1d4ed8")
    draw_section(d, 90, 1230, "Sample flow sketch", w=1340)
    flow = [("Blend S-01/S-02/S-03", 135), ("Compression T-18", 455), ("Coating C-07", 775), ("Packaging PK-3", 1095)]
    for label, x in flow:
        d.rounded_rectangle((x, 1350, x + 245, 1440), radius=8, outline="#334155", width=3)
        draw_text(d, (x + 18, 1370), label, F["tiny_bold"], width=20, leading=22)
    for (_, x1), (_, x2) in zip(flow, flow[1:]):
        d.line((x1 + 245, 1395, x2, 1395), fill="#334155", width=4)
        d.polygon([(x2, 1395), (x2 - 14, 1387), (x2 - 14, 1403)], fill="#334155")
    pages.append(p6)

    p7 = page("Packaging Reconciliation and QA Disposition", "Counts, rejects, and checkbox states")
    d = ImageDraw.Draw(p7)
    rows = [
        ["Item", "Issued", "Used", "Rejected", "Returned", "Reconciled"],
        ["Bottle labels", "118,500", "116,820", "780", "900", "yes"],
        ["Cartons", "9,900", "9,735", "65", "100", "yes"],
        ["Tamper seals", "118,600", "116,820", "780", "1,000", "yes"],
        ["Leaflets", "118,500", "116,820", "0", "1,680", "yes"],
    ]
    draw_table(d, 80, 235, [260, 170, 170, 170, 170, 210], rows, 72)
    checkbox(d, 105, 665, "Packaging counts reconciled by AJ", True, F["small"])
    checkbox(d, 105, 725, "QA released finished goods to market", False, F["small"])
    checkbox(d, 105, 785, "Conditional packaging release approved", True, F["small"])
    checkbox(d, 105, 845, "Deviation D-26-014 closed", False, F["small"])
    draw_section(d, 90, 1010, "QA disposition form", w=1350)
    disp = [
        ["Disposition field", "Visible value"],
        ["Bulk tablets", "accepted for packaging with QA oversight"],
        ["Finished goods", "quarantine hold"],
        ["Quarantine quantity", "2,400 tablets"],
        ["Rejected quantity", "780 tablets"],
        ["Release condition", "CAPA C-241 evidence attached and QA-LD final signature"],
    ]
    draw_ledger(d, 90, 1085, [310, 850], disp, 60)
    pages.append(p7)

    p8 = page("Final Signatures and Superseded Draft Footer", "Final page controls release status")
    d = ImageDraw.Draw(p8)
    draw_section(d, 90, 235, "Approval trail", w=1350)
    sigs = [
        ["Role", "Name", "Date/time", "Status"],
        ["Manufacturing supervisor", "S. Lewis", "2026-07-01 18:05", "signed"],
        ["QC analyst", "J. Lin", "2026-07-01 19:14", "signed"],
        ["QA reviewer", "L. Diaz", "2026-07-02 09:20", "signed with hold"],
        ["QA final release", "", "", "blank"],
    ]
    draw_table(d, 90, 320, [360, 260, 290, 250], sigs, 76)
    draw_note(d, (95, 790, 1510, 1005), "Final QA disposition", "Lot AF12-260701A remains QA HOLD. Final release signature is blank. Conditional packaging release is approved, but finished goods remain quarantined until CAPA C-241 evidence is attached.", "#991b1b")
    draw_section(d, 90, 1145, "Superseded draft footer visible on traveler copy", w=1350)
    d.rectangle((110, 1235, 1485, 1355), outline="#9ca3af", width=2)
    d.text((135, 1268), "DRAFT TRAVELER FOOTER: Release approved after packaging reconciliation. No deviation impact.", fill="#6b7280", font=F["small_bold"])
    d.line((125, 1306, 1460, 1306), fill="#991b1b", width=3)
    draw_note(d, (95, 1450, 1510, 1625), "QA supersession note", "The draft traveler footer remains in the packet for audit trail only and is superseded by the final QA disposition above. Batch status must remain QA HOLD until final release is signed.", "#1d4ed8")
    pages.append(p8)

    gold = """# AltaForge Therapeutics Batch Record BR-26-0417

Product AF-12 50 mg tablets. Batch AF12-260701A. Manufacturing date 2026-07-01. Target yield 120,000 tablets. Final state: QA HOLD.

## Batch Summary

Stages:

| Stage | Started | Ended | Room | Operator | Status |
| --- | --- | --- | --- | --- | --- |
| Dispense | 07:12 | 08:05 | D-102 | RN | complete |
| Blend | 08:30 | 09:45 | M-204 | SL | complete |
| Compression | 10:20 | 13:40 | T-18 | KP | deviation opened |
| Coating | 14:10 | 15:35 | C-07 | MR | complete |
| Pack-out | 16:05 | 17:20 | PK-3 | AJ | hold labels pending QA |

Release state: QA HOLD. Deviation D-26-014 is open. CAPA C-241 evidence is due before final release. Packaged quantity is 116,820 tablets, quarantine quantity is 2,400 tablets, and rejected quantity is 780 tablets. The draft traveler footer is superseded by the final QA page.

## Executed Step Log and Correction Trail

| Step | Instruction / observation | Actual | Time | Operator | Verifier | Record state |
| --- | --- | --- | --- | --- | --- | --- |
| 2.4 | Weigh AF-12 API lot API-8821-6 | 6.000 kg consumed | 07:28 | RN | QA-MJ | accepted |
| 3.2 | Charge blender M-204 | all dispensed material added | 08:37 | SL | QA-MJ | accepted |
| 3.7 | Lubricant return weighback | 0.050 kg returned | 09:51 | SL | QA-MJ | CAPA target |
| 4.1 | Set tablet press speed | 42 rpm | 10:22 | KP | QA-LD | accepted |
| 4.6 | Compression interruption | 12:18-12:46 | 28 min | KP | QA-LD | corrected |
| 5.3 | Coating gun balance check | nozzle B cleaned twice | 14:52 | MR | QA-LD | accepted |
| 6.5 | Release packaging labels | conditional only | 16:02 | AJ | QA-TS | hold pending QA |

GMP correction block: original entry "compression interruption duration 18 min" is struck through; corrected entry is 28 min. Reason: stopwatch log showed restart at 12:46, not 12:36. Initials/date: KP / QA-LD / 2026-07-01. Checkbox states: correction uses single-line strikeout and initials checked; correction changes batch release status to released unchecked.

Traceability chain: MGS-0317 -> Step 3.7 -> D-26-014 -> C-241-B -> QA HOLD -> blank final release. The correction does not close D-26-014.

## Dispensing and Material Reconciliation

| Material | Material lot | Target kg | Issued kg | Consumed kg | Returned kg | Variance | Status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| AF-12 API | API-8821-6 | 6.000 | 6.030 | 6.000 | 0.030 | 0.0% | OK |
| MCC PH102 | MCC-4472 | 42.000 | 42.200 | 41.980 | 0.220 | -0.05% | OK |
| Lactose monohydrate | LAC-2209 | 18.000 | 18.040 | 17.920 | 0.120 | -0.44% | review |
| Croscarmellose | CCS-1184 | 3.600 | 3.620 | 3.600 | 0.020 | 0.0% | OK |
| Magnesium stearate | MGS-0317 | 0.900 | 0.930 | 0.880 | 0.050 | -2.22% | deviation link |
| Opadry blue | OPB-7320 | 4.200 | 4.260 | 4.180 | 0.080 | -0.48% | OK |

Checked states: scale SC-17 calibration checked; second-person material verification complete checked; variance investigation required checked; all variances within automatic release limits unchecked. Magnesium stearate is the deviation trigger, not lactose.

## Line Clearance and Equipment Cleaning

| Area / equipment | ID | Previous product | Cleaned | Verified by | Time | Exception |
| --- | --- | --- | --- | --- | --- | --- |
| Dispense booth | D-102 | AF-08 placebo | yes | RN / QA-MJ | 06:55 | none |
| Blender | M-204 | AF-11 25 mg | yes | SL / QA-MJ | 08:18 | gasket inspection attached |
| Tablet press | T-18 | AF-12 trial | yes | KP / QA-LD | 10:05 | punch 7 replaced |
| Coater | C-07 | AF-09 | yes | MR / QA-LD | 13:58 | spray nozzle B cleaned twice |
| Packaging line | PK-3 | AF-10 | yes | AJ / QA-TS | 15:50 | label roll reconciliation open |

Checklist states: room status labels removed checked; obsolete master batch record copies destroyed checked; loose tablets found unchecked; QA-LD accepted punch 7 replacement checked. Material flow sketch runs D-102 -> M-204 -> T-18 -> C-07 -> PK-3. Punch 7 replacement belongs to T-18.

## In-Process Controls

| Checkpoint | Time | Spec | Result | Initials | Disposition |
| --- | --- | --- | --- | --- | --- |
| Blend uniformity RSD | 09:38 | NMT 5.0% | 3.8% | SL/QA | pass |
| Blend assay mean | 09:38 | 95.0-105.0% | 99.4% | SL/QA | pass |
| Tablet weight | 10:55 | 410-430 mg | 422 mg | KP | pass |
| Hardness | 11:20 | 8-12 kP | 7.6 kP | KP | adjusted press |
| Friability | 12:05 | NMT 1.0% | 0.42% | KP | pass |
| Coating weight gain | 15:18 | 2.5-3.5% | 3.1% | MR | pass |
| Visual blue shade | 15:30 | matches standard | slight light edge | MR/QA | accepted with note |

Blend assay mini chart values are S1 98.7, S2 99.1, S3 100.2, S4 99.8, S5 99.4, S6 98.9, within the 95%-105% bounds.

## Deviation D-26-014 and CAPA C-241

Deviation D-26-014 observed magnesium stearate consumed 0.880 kg versus 0.900 kg target. It was detected during material reconciliation after compression. Compression stopped 12:18-12:46 and QA was notified. Impact assessment says blend uniformity and assay passed and there is no reject for API potency. Classification is Major, not critical.

| Action | Owner | Due | Status | Evidence |
| --- | --- | --- | --- | --- |
| C-241-A retrain dispense operators on lubricant return weighback | QA-MJ | 2026-07-09 | open | training roster |
| C-241-B revise MBR step 3.7 to require second tare check | Process Eng | 2026-07-12 | drafted | redline MBR-12 |
| C-241-C add scale SC-17 alert limit at +/-1.0% | Metrology | 2026-07-16 | not started | change request |
| C-241-D QA effectiveness check on next three AF-12 lots | QA-LD | 2026-08-15 | planned | lot review log |

Root cause is tare confirmation missed after partial lubricant return. CAPA C-241 is open; final disposition is hold with conditional packaging release, not unrestricted release.

## QC Sample Manifest and Results

| Sample ID | Point | Test | Result | Spec | Flag | Analyst |
| --- | --- | --- | --- | --- | --- | --- |
| S-01 | blend top | assay | 98.7% | 95.0-105.0% | | JL |
| S-02 | blend middle | assay | 99.1% | 95.0-105.0% | | JL |
| S-03 | blend bottom | assay | 100.2% | 95.0-105.0% | | JL |
| T-18-043 | compression | hardness | 7.6 kP | 8-12 kP | OOS-investigated | KP |
| T-18-051 | compression | weight | 422 mg | 410-430 mg | | KP |
| C-07-018 | coating | dissolution | Q=82% at 30 min | NLT 80% | | MR |
| PK-3-022 | packaging | label text | matches approved art | match | | AJ |

The 7.6 kP hardness result is out of specification but investigated and accepted after press adjustment. Blank flag means no exception. Sample flow is Blend S-01/S-02/S-03 -> Compression T-18 -> Coating C-07 -> Packaging PK-3.

## Packaging Reconciliation and QA Disposition

| Item | Issued | Used | Rejected | Returned | Reconciled |
| --- | ---: | ---: | ---: | ---: | --- |
| Bottle labels | 118,500 | 116,820 | 780 | 900 | yes |
| Cartons | 9,900 | 9,735 | 65 | 100 | yes |
| Tamper seals | 118,600 | 116,820 | 780 | 1,000 | yes |
| Leaflets | 118,500 | 116,820 | 0 | 1,680 | yes |

Checkbox states: packaging counts reconciled by AJ checked; QA released finished goods to market unchecked; conditional packaging release approved checked; deviation D-26-014 closed unchecked.

QA disposition fields: bulk tablets accepted for packaging with QA oversight; finished goods quarantine hold; quarantine quantity 2,400 tablets; rejected quantity 780 tablets; release condition CAPA C-241 evidence attached and QA-LD final signature.

## Final Signatures and Superseded Draft Footer

| Role | Name | Date/time | Status |
| --- | --- | --- | --- |
| Manufacturing supervisor | S. Lewis | 2026-07-01 18:05 | signed |
| QC analyst | J. Lin | 2026-07-01 19:14 | signed |
| QA reviewer | L. Diaz | 2026-07-02 09:20 | signed with hold |
| QA final release | | | blank |

Visible superseded draft footer: "Release approved after packaging reconciliation. No deviation impact." It is superseded by final QA disposition. Current release state is QA HOLD, not released.
"""

    facts = [
        fact("p14.batch.identity", "text", 7, "Product AF-12 50 mg, batch AF12-260701A, manufacturing date 2026-07-01, target yield 120,000 tablets, and final state QA HOLD are preserved.", modality="text", severity="critical"),
        fact("p14.stage.table", "table_cell", 8, "Stage table preserves Dispense, Blend, Compression, Coating, Pack-out times, rooms, operators, and statuses including compression deviation opened and pack-out hold labels pending QA.", modality="table", severity="major"),
        fact("p14.release.state", "source_state", 10, "Final release state is QA HOLD because D-26-014 is open and CAPA C-241 evidence is due; draft traveler release text is superseded.", modality="source-precedence", severity="critical"),
        fact("p14.executed.step.log", "table_cell", 12, "Executed step log preserves steps 2.4, 3.2, 3.7, 4.1, 4.6, 5.3, and 6.5 with actual values, times, operators/verifiers, and record states, especially Step 3.7 lubricant return weighback 0.050 kg returned CAPA target and Step 4.6 compression interruption 12:18-12:46 / 28 min corrected.", modality="table", severity="critical"),
        fact("p14.gmp.correction", "form_state", 11, "GMP correction block preserves original 18 min as struck through, corrected 28 min, reason restart at 12:46 not 12:36, initials/date KP / QA-LD / 2026-07-01, correction checkbox checked, and release-status-change checkbox unchecked.", modality="physical", severity="critical"),
        fact("p14.traceability.chain", "visual_relation", 10, "Traceability chain is MGS-0317 -> Step 3.7 -> D-26-014 -> C-241-B -> QA HOLD -> blank final release, and the correction does not close D-26-014.", modality="diagram", severity="critical"),
        fact("p14.materials", "table_cell", 12, "Material reconciliation preserves all six materials with lots, target/issued/consumed/returned kg, variance, and status, especially magnesium stearate MGS-0317 target 0.900 consumed 0.880 returned 0.050 variance -2.22% deviation link.", modality="table", severity="critical"),
        fact("p14.material.checkboxes", "form_state", 7, "Scale SC-17 calibration, second-person verification, and variance investigation required are checked; all variances within automatic release limits is unchecked.", modality="form", severity="major"),
        fact("p14.cleaning", "table_cell", 8, "Line clearance table preserves equipment IDs, previous products, verification pairs/times, and exceptions including T-18 punch 7 replaced and PK-3 label roll reconciliation open.", modality="table", severity="major"),
        fact("p14.cleaning.checkboxes", "form_state", 6, "Room labels removed, obsolete MBR copies destroyed, and QA-LD accepted punch 7 replacement are checked; loose tablets found is unchecked.", modality="form", severity="major"),
        fact("p14.flow.sketch", "visual_relation", 7, "Equipment flow sketch is D-102 to M-204 to T-18 to C-07 to PK-3, and punch 7 replacement belongs to T-18.", modality="diagram", severity="major"),
        fact("p14.ipc.table", "table_cell", 12, "IPC table preserves all checkpoints/specs/results/dispositions including RSD 3.8%, assay mean 99.4%, tablet weight 422 mg, hardness 7.6 kP adjusted press, friability 0.42%, coating gain 3.1%, and visual blue shade accepted with note.", modality="table", severity="critical"),
        fact("p14.assay.chart", "chart", 6, "Blend assay chart values are S1 98.7, S2 99.1, S3 100.2, S4 99.8, S5 99.4, S6 98.9 with 95%-105% bounds.", modality="chart", severity="major"),
        fact("p14.deviation", "source_state", 10, "Deviation D-26-014 observed magnesium stearate consumed 0.880 vs 0.900 kg target, detected after compression, compression stopped 12:18-12:46, impact says blend/assay passed and no API potency reject, classification Major not critical.", modality="source-precedence", severity="critical"),
        fact("p14.capa", "table_cell", 10, "CAPA table preserves C-241-A/B/C/D actions, owners QA-MJ/Process Eng/Metrology/QA-LD, due dates 2026-07-09/07-12/07-16/08-15, statuses open/drafted/not started/planned, and evidence fields.", modality="table", severity="critical"),
        fact("p14.qc.samples", "table_cell", 12, "QC sample manifest preserves all sample IDs, points, tests, results, specs, flags, and analysts, especially T-18-043 hardness 7.6 kP flag OOS-investigated and C-07-018 dissolution Q=82% at 30 min.", modality="table", severity="critical"),
        fact("p14.sample.flow", "visual_relation", 5, "Sample flow sketch is Blend S-01/S-02/S-03 to Compression T-18 to Coating C-07 to Packaging PK-3.", modality="diagram", severity="major"),
        fact("p14.packaging", "table_cell", 10, "Packaging reconciliation preserves issued/used/rejected/returned counts for bottle labels, cartons, tamper seals, and leaflets, including bottle labels 118,500 issued, 116,820 used, 780 rejected, 900 returned.", modality="table", severity="critical"),
        fact("p14.disposition.checkboxes", "form_state", 8, "Packaging counts reconciled and conditional packaging release are checked; QA released finished goods to market and deviation closed are unchecked.", modality="form", severity="critical"),
        fact("p14.qa.disposition", "source_state", 9, "Bulk tablets accepted for packaging with QA oversight, finished goods quarantine hold, quarantine 2,400, rejected 780, release condition CAPA C-241 evidence and QA-LD final signature.", modality="source-precedence", severity="critical"),
        fact("p14.signatures", "form_state", 8, "Signatures preserve S. Lewis 2026-07-01 18:05 signed, J. Lin 2026-07-01 19:14 signed, L. Diaz 2026-07-02 09:20 signed with hold, and QA final release blank.", modality="form", severity="critical"),
    ]

    return Case(
        "P14-manufacturing-batch-capa",
        "Manufacturing Batch Record and CAPA Packet",
        "manufacturing-quality",
        ["multi-page", "manufacturing", "batch-record", "qa", "capa", "forms", "tables", "source-precedence"],
        "Stress realistic GMP batch-record reconstruction with dense material tables, form states, QC flags, deviation/CAPA actions, signatures, and superseded release text.",
        "Eight-page QA packet with batch summary, material reconciliation, cleaning checklist, IPC table, deviation/CAPA plan, QC manifest, packaging reconciliation, and final QA disposition.",
        ["batch summary", "material reconciliation", "line clearance", "IPC", "deviation", "CAPA", "QC samples", "packaging", "signatures"],
        ["Preserve exact table cell bindings, units, and flags.", "Preserve checkbox/blank/signature states.", "Use final QA disposition over superseded draft release text."],
        gold,
        [
            near_check("p14-batch-hold", "source_state", ["AF12-260701A", "QA HOLD", "D-26-014", "C-241"], 6, 700),
            near_check("p14-mag-stearate", "table_cell", ["Magnesium stearate", "MGS-0317", "0.900", "0.880", "-2.22%"], 6, 800),
            near_check("p14-final-release-blank", "form_state", ["QA final release", "blank", "QA HOLD"], 5, 700),
        ],
        pages,
        facts=facts,
    )


def packet_finance_covenant_reforecast() -> Case:
    def page(title: str, subtitle: str) -> Image.Image:
        img = Image.new("RGB", (PAGE_W, PAGE_H), "#ffffff")
        d = ImageDraw.Draw(img)
        d.text((72, 58), "LumaGrid Systems | CFO board packet", fill="#334155", font=F["tiny_bold"])
        d.text((72, 92), title, fill="#111827", font=F["h1"])
        d.text((72, 132), subtitle, fill="#475569", font=F["small"])
        d.line((72, 178, 1580, 178), fill="#cbd5e1", width=2)
        d.text((1410, 60), "May 2026 close", fill="#111827", font=F["small_bold"])
        return img

    pages: list[Image.Image] = []

    p1 = page("CFO Reforecast: Liquidity and Covenant Watch", "Board version; draft appendix at end is superseded")
    d = ImageDraw.Draw(p1)
    draw_card(d, (90, 240, 520, 520), "ARR", ["$18.6M Q2 actual", "$19.4M plan", "-$0.8M variance"], "#f8fafc")
    draw_card(d, (575, 240, 1005, 520), "Runway", ["9.6 months base", "7.8 months downside", "11.4 months freeze"], "#fff7ed", "#c2410c")
    draw_card(d, (1060, 240, 1515, 520), "Covenants", ["October liquidity breach", "$4.7M vs $5.0M min", "DSCR ok until Dec"], "#fee2e2", "#991b1b")
    rows = [
        ["Board question", "Owner", "Due", "Answer in packet"],
        ["Are hiring freeze savings included?", "AK", "2026-06-14", "Yes, $0.42M in Q3 opex"],
        ["Does covenant breach require waiver?", "ML", "2026-06-21", "Likely for Oct liquidity"],
        ["Which renewals slipped?", "RS", "2026-06-10", "BrioHealth and Kestrel"],
        ["Can vendor terms extend runway?", "NT", "2026-06-18", "Only 0.4 months"],
    ]
    draw_ledger(d, 90, 680, [380, 160, 170, 640], rows, 62)
    draw_note(d, (95, 1100, 1510, 1290), "Visible-source rule", "Appendix page 8 contains an earlier draft. Final board pages control: Q2 ARR is $18.6M, October liquidity is $4.7M, and base runway is 9.6 months.", "#991b1b")
    pages.append(p1)

    p2 = page("P&L Reforecast", "Actuals through May; June-September forecast")
    d = ImageDraw.Draw(p2)
    rows = [
        ["$M", "Apr A", "May A", "Jun F", "Jul F", "Aug F", "Sep F"],
        ["Revenue", "4.8", "5.1", "5.4", "5.7", "6.0", "6.4"],
        ["COGS", "(1.9)", "(2.0)", "(2.1)", "(2.2)", "(2.3)", "(2.5)"],
        ["Gross margin", "2.9", "3.1", "3.3", "3.5", "3.7", "3.9"],
        ["Sales & marketing", "(1.4)", "(1.5)", "(1.7)", "(1.6)", "(1.6)", "(1.5)"],
        ["R&D", "(2.2)", "(2.1)", "(2.0)", "(1.9)", "(1.9)", "(1.8)"],
        ["G&A", "(0.9)", "(0.9)", "(1.0)", "(1.0)", "(1.0)", "(1.0)"],
        ["EBITDA", "(1.6)", "(1.4)", "(1.4)", "(1.0)", "(0.8)", "(0.4)"],
        ["Ending cash", "12.8", "11.4", "10.0", "8.9", "8.0", "7.4"],
    ]
    draw_ledger(d, 80, 230, [260, 145, 145, 145, 145, 145, 145], rows, 54)
    draw_text(d, (80, 850), "Parentheses indicate negative values. Hiring freeze savings begin in July and reduce R&D and sales hiring spend; do not treat parenthetical EBITDA as positive.", F["small"], width=110, leading=32)
    pages.append(p2)

    p3 = page("ARR Bridge and Renewal Slip", "Bridge reconciles Q2 actual ARR")
    d = ImageDraw.Draw(p3)
    rows = [
        ["Bridge component", "Amount", "Included in ARR?", "Note"],
        ["Q1 exit ARR", "$17.20M", "yes", "starting point"],
        ["New logos", "+$1.12M", "yes", "42 accounts"],
        ["Expansion", "+$1.42M", "yes", "seat growth"],
        ["Contraction", "($0.38M)", "yes", "downgrades"],
        ["Churn", "($0.54M)", "yes", "lost logos"],
        ["FX remeasurement", "($0.22M)", "yes", "May 31 rate"],
        ["One-time implementation fees", "+$0.31M", "no", "excluded from ARR"],
        ["Q2 actual ARR", "$18.60M", "yes", "final actual"],
        ["Q2 plan ARR", "$19.40M", "yes", "variance ($0.80M)"],
    ]
    draw_ledger(d, 80, 220, [360, 170, 200, 520], rows, 54)
    chart_x0, chart_y0, chart_x1, chart_y1 = 80, 880, 1510, 1345
    d.rectangle((chart_x0, chart_y0, chart_x1, chart_y1), outline="#cbd5e1", width=2)
    d.text((chart_x0 + 24, chart_y0 + 22), "ARR bridge waterfall (USD millions)", fill="#111827", font=F["small_bold"])
    baseline = chart_y0 + 330
    d.line((chart_x0 + 40, baseline, chart_x1 - 40, baseline), fill="#64748b", width=2)
    x0 = chart_x0 + 95
    bars = [("Q1", 17.2, "#334155"), ("New", 1.12, "#16a34a"), ("Expansion", 1.42, "#16a34a"), ("Contraction", -0.38, "#dc2626"), ("Churn", -0.54, "#dc2626"), ("FX", -0.22, "#dc2626"), ("Q2", 18.6, "#334155")]
    for i, (label, value, color) in enumerate(bars):
        x = x0 + i * 188
        bar_w = 92
        h = int((abs(value) if label not in ["Q1", "Q2"] else value / 4) * 60)
        if value >= 0 or label in ["Q1", "Q2"]:
            top = baseline - h
            bottom = baseline
            value_y = max(top - 34, chart_y0 + 62)
        else:
            top = baseline
            bottom = baseline + h
            value_y = baseline - 36
        d.rectangle((x, top, x + bar_w, bottom), fill=color)
        d.text((x - 4, baseline + 42), label, fill="#111827", font=F["tiny_bold"])
        d.rounded_rectangle((x - 8, value_y - 4, x + 78, value_y + 25), radius=4, fill="#ffffff", outline="#e2e8f0", width=1)
        d.text((x - 3, value_y), str(value), fill="#111827", font=F["tiny"])
    draw_note(d, (85, 1410, 1510, 1585), "Renewal slip", "BrioHealth $0.42M and Kestrel Freight $0.38M moved from Q2 to Q3. They explain the $0.80M plan variance and are not churn.", "#9a3412")
    pages.append(p3)

    p4 = page("Covenant Test Schedule", "Liquidity and DSCR by month")
    d = ImageDraw.Draw(p4)
    rows = [
        ["Month", "Min liquidity", "Forecast liquidity", "Liquidity result", "DSCR min", "Forecast DSCR", "DSCR result"],
        ["Jul", "$5.0M", "$8.9M", "Pass", "1.20x", "1.78x", "Pass"],
        ["Aug", "$5.0M", "$8.0M", "Pass", "1.20x", "1.62x", "Pass"],
        ["Sep", "$5.0M", "$7.4M", "Pass", "1.20x", "1.41x", "Pass"],
        ["Oct", "$5.0M", "$4.7M", "Fail", "1.20x", "1.28x", "Pass"],
        ["Nov", "$5.0M", "$4.9M", "Fail", "1.20x", "1.19x", "Fail"],
        ["Dec", "$5.0M", "$5.3M", "Pass", "1.20x", "1.16x", "Fail"],
    ]
    draw_ledger(d, 65, 220, [130, 180, 210, 190, 150, 180, 170], rows, 58)
    draw_note(d, (85, 760, 1510, 980), "Covenant warning", "First liquidity failure is October at $4.7M versus $5.0M minimum. First DSCR failure is November at 1.19x versus 1.20x. December liquidity passes but DSCR fails.", "#991b1b")
    d.line((140, 1320, 1300, 1320), fill="#111827", width=3)
    d.line((140, 1320, 140, 1080), fill="#111827", width=3)
    vals = [("Jul", 8.9), ("Aug", 8.0), ("Sep", 7.4), ("Oct", 4.7), ("Nov", 4.9), ("Dec", 5.3)]
    prev = None
    for i, (month, val) in enumerate(vals):
        x = 190 + i * 185
        y = 1320 - int(val * 24)
        d.ellipse((x - 7, y - 7, x + 7, y + 7), fill="#2563eb")
        d.text((x - 22, 1345), month, fill="#111827", font=F["tiny"])
        d.text((x - 18, y - 35), f"{val:.1f}", fill="#111827", font=F["tiny_bold"])
        if prev:
            d.line((prev[0], prev[1], x, y), fill="#2563eb", width=4)
        prev = (x, y)
    d.line((140, 1200, 1300, 1200), fill="#dc2626", width=3)
    d.text((1320, 1188), "$5.0M min", fill="#dc2626", font=F["tiny_bold"])
    pages.append(p4)

    p5 = page("Cash Runway Scenarios", "Burn, savings, and vendor term sensitivity")
    d = ImageDraw.Draw(p5)
    rows = [
        ["Scenario", "Starting cash", "Monthly burn", "Runway", "Assumption"],
        ["Base", "$11.4M", "$1.19M", "9.6 months", "May close forecast"],
        ["Downside", "$11.4M", "$1.46M", "7.8 months", "renewals slip again"],
        ["Hiring freeze", "$11.4M", "$1.00M", "11.4 months", "$0.42M Q3 savings"],
        ["Vendor terms", "$11.4M", "$1.14M", "10.0 months", "net-60 on cloud"],
    ]
    draw_ledger(d, 80, 230, [250, 210, 200, 180, 520], rows, 66)
    draw_note(d, (85, 610, 1510, 775), "Scenario note", "Vendor terms add only 0.4 months versus base. Hiring freeze is already included in the base P&L beginning in July, but the separate freeze scenario assumes deeper freeze savings.", "#334155")
    d.rectangle((85, 875, 1485, 1330), outline="#cbd5e1", width=2)
    d.text((110, 900), "Runway months by scenario", fill="#111827", font=F["small_bold"])
    d.line((155, 1265, 1400, 1265), fill="#111827", width=2)
    d.line((155, 1265, 155, 945), fill="#111827", width=2)
    for tick, label in [(8, "8"), (10, "10"), (12, "12")]:
        y_tick = 1265 - int((tick - 6) * 48)
        d.line((150, y_tick, 1400, y_tick), fill="#e5e7eb", width=1)
        d.text((115, y_tick - 12), label, fill="#64748b", font=F["tiny"])
    bars = [("Base", 9.6), ("Downside", 7.8), ("Freeze", 11.4), ("Vendor", 10.0)]
    for i, (label, val) in enumerate(bars):
        x = 245 + i * 285
        bar_h = int((val - 6) * 48)
        d.rectangle((x, 1265 - bar_h, x + 135, 1265), fill="#0f766e")
        d.text((x, 1290), label, fill="#111827", font=F["tiny_bold"])
        d.text((x + 18, 1238 - bar_h), f"{val:.1f} mo", fill="#111827", font=F["tiny_bold"])
    pages.append(p5)

    p6 = page("AR Aging and Customer Concentration", "Collection risk is concentrated in three accounts")
    d = ImageDraw.Draw(p6)
    rows = [
        ["Bucket", "Amount", "Share", "Reserve"],
        ["Current", "$3.42M", "48%", "$0.00M"],
        ["1-30", "$1.86M", "26%", "$0.04M"],
        ["31-60", "$1.08M", "15%", "$0.11M"],
        ["61-90", "$0.52M", "7%", "$0.16M"],
        [">90", "$0.29M", "4%", "$0.20M"],
        ["Total", "$7.17M", "100%", "$0.51M"],
    ]
    draw_ledger(d, 90, 230, [260, 200, 160, 200], rows, 62)
    customers = [
        ["Customer", "ARR", "AR balance", "Status", "Note"],
        ["BrioHealth", "$1.84M", "$0.62M", "Delayed", "renewal moved to Q3"],
        ["Kestrel Freight", "$1.21M", "$0.44M", "Delayed", "PO reissue pending"],
        ["MiraTel", "$0.88M", "$0.31M", "Watch", "legal entity update"],
        ["Canopy Bank", "$0.76M", "$0.08M", "Current", "paid June 2"],
    ]
    draw_ledger(d, 90, 780, [280, 180, 200, 170, 420], customers, 62)
    draw_note(d, (90, 1360, 1510, 1535), "Reserve note", "The reserve is $0.51M total. Do not confuse AR balance with ARR. BrioHealth and Kestrel are renewal timing issues, not churn.", "#9a3412")
    pages.append(p6)

    p7 = page("Footnotes and Reconciliation Notes", "Units, exclusions, and approval trail")
    d = ImageDraw.Draw(p7)
    notes = [
        ["F1", "All P&L values are USD millions unless labeled otherwise."],
        ["F2", "ARR excludes one-time implementation fees and services retainers."],
        ["F3", "FX rates are held constant at the May 31 closing rate."],
        ["F4", "Liquidity covenant uses unrestricted cash only; escrow is excluded."],
        ["F5", "DSCR is trailing-three-month adjusted EBITDA divided by scheduled debt service."],
        ["F6", "Board pack approved by CFO Mara Lee at 2026-06-06 18:42 PT."],
    ]
    draw_ledger(d, 90, 240, [120, 1180], notes, 70)
    pages.append(p7)

    p8 = page("Superseded Draft Appendix", "Included for audit trail only")
    d = ImageDraw.Draw(p8)
    rows = [
        ["Draft field", "Draft value", "Final value", "Disposition"],
        ["Q2 ARR", "$19.1M", "$18.6M", "superseded"],
        ["October liquidity", "$5.4M", "$4.7M", "superseded"],
        ["Base runway", "10.8 months", "9.6 months", "superseded"],
        ["Amendment needed", "No", "Likely for Oct liquidity", "superseded"],
    ]
    draw_ledger(d, 90, 260, [300, 260, 340, 260], rows, 70)
    draw_note(d, (95, 760, 1510, 980), "Audit warning", "Do not use this page as the current forecast. The signed pages in this packet supersede this draft insert for launch decisions.", "#991b1b")
    pages.append(p8)

    p9 = page("Lender Model Covenant Worksheet", "Exact covenant math; lender model controls covenant calculations")
    d = ImageDraw.Draw(p9)
    rows = [
        ["Metric", "Source", "Amount", "Treatment", "Covenant impact"],
        ["Adjusted EBITDA, TTM", "lender model tab C-12", "$8.42M", "denominator", "used in net leverage"],
        ["Permitted payroll\nrestructuring add-back", "credit agreement\n1.01", "$0.38M", "included", "adds to EBITDA"],
        ["Proposed customer success\nbackfill add-back", "management\nrequest", "$0.29M", "excluded", "not permitted"],
        ["Funded debt", "debt schedule", "$37.15M", "numerator", "used in leverage"],
        ["Unrestricted cash", "ERP cash report", "($4.82M)", "deducted", "net debt"],
        ["Net debt", "calculated", "$32.33M", "numerator", "37.15 - 4.82"],
        ["Net leverage", "calculated", "3.84x", "test result", "threshold <= 3.75x: Fail"],
        ["Fixed charge coverage", "calculated", "1.21x", "test result", "threshold >= 1.20x: Pass"],
        ["Minimum liquidity", "ERP cash report", "$4.70M", "test result", "threshold >= $5.00M: Fail"],
    ]
    draw_table(d, 45, 250, [330, 270, 150, 230, 345], rows, 74)
    draw_note(d, (90, 990, 740, 1215), "Formula note", "Net leverage = (funded debt - unrestricted cash) / adjusted EBITDA. Excluding the $0.29M backfill add-back is what makes leverage fail.", "#991b1b")
    draw_note(d, (830, 990, 1515, 1215), "Source hierarchy", "Credit agreement definitions control add-back eligibility. Lender model controls covenant math. Board deck values are rounded and illustrative.", "#1d4ed8")
    pages.append(p9)

    p10 = page("Lender Q&A Tracker + Board Deck Excerpt", "Status chips, source references, rounded values, and non-controlling slide facts")
    d = ImageDraw.Draw(p10)
    rows = [
        ["Q", "Question", "Owner", "Status", "Evidence", "Due"],
        ["Q1", "Why does net leverage fail\nif board deck says 3.7x?", "Mara Lee", "open", "P9 lender model", "2026-06-12"],
        ["Q2", "Confirm deferred revenue roll-forward tie-out.", "Noah Tran", "closed", "P5 schedule", "2026-06-10"],
        ["Q3", "List customers driving renewal risk.", "Rina Shah", "pending evidence", "P6 concentration", "2026-06-13"],
        ["Q4", "Can customer success backfill\nbe an EBITDA add-back?", "Mara Lee", "closed", "credit agreement excerpt", "2026-06-11"],
    ]
    draw_table(d, 45, 250, [80, 430, 170, 190, 260, 160], rows, 82)
    draw_section(d, 90, 790, "Board deck excerpt - rounded / illustrative", w=1380)
    d.rectangle((115, 880, 500, 1045), outline="#111827", width=3)
    d.text((145, 910), "ARR", fill="#64748b", font=F["tiny_bold"])
    d.text((145, 950), "$18.6M", fill="#111827", font=F["h1"])
    d.text((145, 1000), "rounded", fill="#92400e", font=F["tiny_bold"])
    d.rectangle((555, 880, 940, 1045), outline="#111827", width=3)
    d.text((585, 910), "Net leverage", fill="#64748b", font=F["tiny_bold"])
    d.text((585, 950), "3.7x", fill="#111827", font=F["h1"])
    d.text((585, 1000), "illustrative; not covenant test", fill="#92400e", font=F["tiny_bold"])
    d.rectangle((995, 880, 1380, 1045), outline="#111827", width=3)
    d.text((1025, 910), "Runway", fill="#64748b", font=F["tiny_bold"])
    d.text((1025, 950), "10 mo", fill="#111827", font=F["h1"])
    d.text((1025, 1000), "rounded from base 9.6", fill="#92400e", font=F["tiny_bold"])
    draw_note(d, (95, 1165, 1510, 1385), "Non-controlling slide note", "The board deck slide may be quoted as visible content, but the lender model controls covenant tests: net leverage is 3.84x Fail, liquidity is $4.70M Fail, and FCCR is 1.21x Pass.", "#991b1b")
    pages.append(p10)

    gold = """# LumaGrid Systems CFO Reforecast

Board version. Draft appendix is superseded by final pages 1-7.

## Executive Summary

Q2 actual ARR is $18.6M versus plan $19.4M, a negative variance of $0.8M. Base runway is 9.6 months. October liquidity breaches the covenant at $4.7M versus the $5.0M minimum. DSCR first fails in November at 1.19x.

Board questions: AK owns hiring freeze savings, due 2026-06-14, answer yes $0.42M in Q3 opex. ML owns covenant waiver question, due 2026-06-21, answer likely for Oct liquidity. RS owns slipped renewals, due 2026-06-10, BrioHealth and Kestrel. NT owns vendor terms, due 2026-06-18, only 0.4 months.

## P&L Reforecast

| $M | Apr A | May A | Jun F | Jul F | Aug F | Sep F |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Revenue | 4.8 | 5.1 | 5.4 | 5.7 | 6.0 | 6.4 |
| COGS | -1.9 | -2.0 | -2.1 | -2.2 | -2.3 | -2.5 |
| Gross margin | 2.9 | 3.1 | 3.3 | 3.5 | 3.7 | 3.9 |
| Sales & marketing | -1.4 | -1.5 | -1.7 | -1.6 | -1.6 | -1.5 |
| R&D | -2.2 | -2.1 | -2.0 | -1.9 | -1.9 | -1.8 |
| G&A | -0.9 | -0.9 | -1.0 | -1.0 | -1.0 | -1.0 |
| EBITDA | -1.6 | -1.4 | -1.4 | -1.0 | -0.8 | -0.4 |
| Ending cash | 12.8 | 11.4 | 10.0 | 8.9 | 8.0 | 7.4 |

Parentheses indicate negative values. Hiring freeze savings begin in July.

## ARR Bridge

| Bridge component | Amount | Included in ARR? | Note |
| --- | ---: | --- | --- |
| Q1 exit ARR | $17.20M | yes | starting point |
| New logos | +$1.12M | yes | 42 accounts |
| Expansion | +$1.42M | yes | seat growth |
| Contraction | -$0.38M | yes | downgrades |
| Churn | -$0.54M | yes | lost logos |
| FX remeasurement | -$0.22M | yes | May 31 rate |
| One-time implementation fees | +$0.31M | no | excluded from ARR |
| Q2 actual ARR | $18.60M | yes | final actual |
| Q2 plan ARR | $19.40M | yes | variance -$0.80M |

Waterfall labels are Q1 17.2, New +1.12, Expansion +1.42, Contraction -0.38, Churn -0.54, FX -0.22, and Q2 18.6. BrioHealth $0.42M and Kestrel Freight $0.38M moved from Q2 to Q3 and are not churn.

## Covenant Test Schedule

| Month | Min liquidity | Forecast liquidity | Liquidity result | DSCR min | Forecast DSCR | DSCR result |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| Jul | $5.0M | $8.9M | Pass | 1.20x | 1.78x | Pass |
| Aug | $5.0M | $8.0M | Pass | 1.20x | 1.62x | Pass |
| Sep | $5.0M | $7.4M | Pass | 1.20x | 1.41x | Pass |
| Oct | $5.0M | $4.7M | Fail | 1.20x | 1.28x | Pass |
| Nov | $5.0M | $4.9M | Fail | 1.20x | 1.19x | Fail |
| Dec | $5.0M | $5.3M | Pass | 1.20x | 1.16x | Fail |

First liquidity failure is October. First DSCR failure is November. December liquidity passes but DSCR fails.

## Cash Runway

| Scenario | Starting cash | Monthly burn | Runway | Assumption |
| --- | ---: | ---: | ---: | --- |
| Base | $11.4M | $1.19M | 9.6 months | May close forecast |
| Downside | $11.4M | $1.46M | 7.8 months | renewals slip again |
| Hiring freeze | $11.4M | $1.00M | 11.4 months | $0.42M Q3 savings |
| Vendor terms | $11.4M | $1.14M | 10.0 months | net-60 on cloud |

Vendor terms add only 0.4 months versus base.

## AR Aging and Customer Concentration

| Bucket | Amount | Share | Reserve |
| --- | ---: | ---: | ---: |
| Current | $3.42M | 48% | $0.00M |
| 1-30 | $1.86M | 26% | $0.04M |
| 31-60 | $1.08M | 15% | $0.11M |
| 61-90 | $0.52M | 7% | $0.16M |
| >90 | $0.29M | 4% | $0.20M |
| Total | $7.17M | 100% | $0.51M |

| Customer | ARR | AR balance | Status | Note |
| --- | ---: | ---: | --- | --- |
| BrioHealth | $1.84M | $0.62M | Delayed | renewal moved to Q3 |
| Kestrel Freight | $1.21M | $0.44M | Delayed | PO reissue pending |
| MiraTel | $0.88M | $0.31M | Watch | legal entity update |
| Canopy Bank | $0.76M | $0.08M | Current | paid June 2 |

The reserve is $0.51M total. Do not confuse AR balance with ARR.

## Footnotes

F1 all P&L values are USD millions unless labeled otherwise. F2 ARR excludes one-time implementation fees and services retainers. F3 FX rates are held constant at the May 31 closing rate. F4 liquidity covenant uses unrestricted cash only and excludes escrow. F5 DSCR is trailing-three-month adjusted EBITDA divided by scheduled debt service. F6 board pack approved by CFO Mara Lee at 2026-06-06 18:42 PT.

## Superseded Draft Appendix

Draft Q2 ARR $19.1M is superseded by $18.6M. Draft October liquidity $5.4M is superseded by $4.7M. Draft base runway 10.8 months is superseded by 9.6 months. Draft amendment needed No is superseded by likely for Oct liquidity.

## Lender Model Covenant Worksheet

The lender model controls covenant calculations. Credit agreement definitions control add-back eligibility. Board deck values are rounded and illustrative.

| Metric | Source | Amount | Treatment | Covenant impact |
| --- | --- | ---: | --- | --- |
| Adjusted EBITDA, TTM | lender model tab C-12 | $8.42M | denominator | used in net leverage |
| Permitted payroll restructuring add-back | credit agreement 1.01 | $0.38M | included | adds to EBITDA |
| Proposed customer success backfill add-back | management request | $0.29M | excluded | not permitted |
| Funded debt | debt schedule | $37.15M | numerator | used in leverage |
| Unrestricted cash | ERP cash report | ($4.82M) | deducted | net debt |
| Net debt | calculated | $32.33M | numerator | 37.15 - 4.82 |
| Net leverage | calculated | 3.84x | test result | threshold <= 3.75x: Fail |
| Fixed charge coverage | calculated | 1.21x | test result | threshold >= 1.20x: Pass |
| Minimum liquidity | ERP cash report | $4.70M | test result | threshold >= $5.00M: Fail |

Formula note: net leverage = (funded debt - unrestricted cash) / adjusted EBITDA. Excluding the $0.29M customer success backfill add-back is what makes leverage fail.

## Lender Q&A Tracker and Board Deck Excerpt

| Q | Question | Owner | Status | Evidence | Due |
| --- | --- | --- | --- | --- | --- |
| Q1 | Why does net leverage fail if board deck says 3.7x? | Mara Lee | open | P9 lender model | 2026-06-12 |
| Q2 | Confirm deferred revenue roll-forward tie-out. | Noah Tran | closed | P5 schedule | 2026-06-10 |
| Q3 | List customers driving renewal risk. | Rina Shah | pending evidence | P6 concentration | 2026-06-13 |
| Q4 | Can customer success backfill be an EBITDA add-back? | Mara Lee | closed | credit agreement excerpt | 2026-06-11 |

Board deck excerpt shows rounded/illustrative values: ARR $18.6M rounded, net leverage 3.7x illustrative and not the covenant test, and runway 10 mo rounded from base 9.6. The board deck slide may be quoted as visible content, but the lender model controls covenant tests: net leverage is 3.84x Fail, liquidity is $4.70M Fail, and fixed charge coverage is 1.21x Pass.
"""

    facts = [
        fact("p14.summary", "text", 5, "Executive summary preserves Q2 ARR $18.6M vs plan $19.4M, -$0.8M variance, base runway 9.6 months, Oct liquidity $4.7M vs $5.0M minimum, and first DSCR failure in November at 1.19x."),
        fact("p14.questions", "table_cell", 6, "Board questions preserve owners/dates/answers for AK, ML, RS, and NT, including BrioHealth and Kestrel renewals and vendor terms only 0.4 months."),
        fact("p14.pnl.revenue.cash", "table_cell", 8, "P&L preserves revenue and ending cash for Apr-Sep: revenue 4.8/5.1/5.4/5.7/6.0/6.4 and ending cash 12.8/11.4/10.0/8.9/8.0/7.4."),
        fact("p14.pnl.costs", "table_cell", 8, "P&L preserves COGS, S&M, R&D, G&A, and EBITDA rows with parentheses/negative signs, especially Sep EBITDA -0.4 and May EBITDA -1.4."),
        fact("p14.arr.bridge", "table_cell", 10, "ARR bridge preserves Q1 $17.20M, New +$1.12M, Expansion +$1.42M, Contraction -$0.38M, Churn -$0.54M, FX -$0.22M, Q2 actual $18.60M, Q2 plan $19.40M."),
        fact("p14.arr.exclusion", "source_state", 7, "One-time implementation fees +$0.31M are explicitly excluded from ARR."),
        fact("p14.renewal.slip", "source_state", 7, "BrioHealth $0.42M and Kestrel Freight $0.38M moved from Q2 to Q3 and are not churn."),
        fact("p14.covenant.table", "table_cell", 12, "Covenant schedule preserves all Jul-Dec liquidity and DSCR values and pass/fail states."),
        fact("p14.covenant.firsts", "source_state", 8, "First liquidity failure is October at $4.7M vs $5.0M; first DSCR failure is November at 1.19x vs 1.20x; December liquidity passes but DSCR fails."),
        fact("p14.liquidity.chart", "chart", 6, "Liquidity chart values are Jul 8.9, Aug 8.0, Sep 7.4, Oct 4.7, Nov 4.9, Dec 5.3 with $5.0M minimum threshold."),
        fact("p14.runway", "table_cell", 8, "Runway scenarios preserve Base 9.6, Downside 7.8, Hiring freeze 11.4, Vendor terms 10.0 months with starting cash and monthly burn values."),
        fact("p14.vendor.terms", "source_state", 4, "Vendor terms add only 0.4 months versus base."),
        fact("p14.ar.aging", "table_cell", 8, "AR aging table preserves all buckets, amounts, shares, reserve values, and total reserve $0.51M."),
        fact("p14.customer.concentration", "table_cell", 8, "Customer table preserves BrioHealth, Kestrel Freight, MiraTel, and Canopy Bank ARR, AR balance, status, and notes."),
        fact("p14.footnotes", "text", 6, "Footnotes preserve USD millions, ARR exclusions, FX May 31 rate, unrestricted cash only/excluding escrow, DSCR definition, and CFO Mara Lee approval at 2026-06-06 18:42 PT."),
        fact("p14.superseded", "source_state", 8, "Draft values $19.1M ARR, $5.4M Oct liquidity, 10.8 months runway, and amendment needed No are marked superseded by final values $18.6M, $4.7M, 9.6 months, and likely for Oct liquidity."),
        fact("p14.lender.model", "table_cell", 12, "Lender model worksheet preserves all metrics, sources, amounts, treatments, covenant impacts, and results: adjusted EBITDA $8.42M, included $0.38M add-back, excluded $0.29M backfill add-back, funded debt $37.15M, cash ($4.82M), net debt $32.33M, net leverage 3.84x Fail, FCCR 1.21x Pass, liquidity $4.70M Fail.", modality="table", severity="critical"),
        fact("p14.covenant.formula", "source_state", 9, "Net leverage formula is (funded debt - unrestricted cash) / adjusted EBITDA; credit agreement definitions control add-back eligibility; excluding the $0.29M backfill add-back makes leverage fail.", modality="source-precedence", severity="critical"),
        fact("p14.qa.tracker", "table_cell", 8, "Lender Q&A tracker preserves Q1-Q4 questions, owners, statuses, evidence references, and due dates, including Q1 open on board deck 3.7x vs lender model and Q3 pending evidence for renewal risk.", modality="table", severity="major"),
        fact("p14.board.deck.source_state", "source_state", 9, "Board deck values are visible but rounded/illustrative: ARR $18.6M, net leverage 3.7x, runway 10 mo; lender model controls with net leverage 3.84x Fail, liquidity $4.70M Fail, FCCR 1.21x Pass.", modality="source-precedence", severity="critical"),
    ]

    return Case(
        "P14-finance-covenant-reforecast",
        "Finance Covenant Reforecast Packet",
        "finance",
        ["multi-page", "finance", "covenants", "pnl", "arr-bridge", "charts", "source-precedence"],
        "Stress finance-board reconstruction with dense local numeric tables, covenant pass/fail states, chart values, footnotes, and superseded draft values.",
        "Ten-page CFO/lender packet with tables, chart values, footnotes, draft appendix conflicts, exact covenant worksheet, and board-deck source conflict.",
        ["P&L", "ARR bridge", "covenants", "runway", "AR aging", "footnotes", "superseded appendix"],
        ["Preserve exact values, signs, units, and pass/fail states.", "Do not treat draft appendix values as current.", "Describe chart values inline."],
        gold,
        [
            near_check("p14-oct-liquidity", "table_cell", ["Oct", "$5.0M", "$4.7M", "Fail"], 5, 500),
            near_check("p14-arr-bridge", "table_cell", ["Q1", "$17.20M", "+$1.12M", "+$1.42M", "-$0.38M", "-$0.54M", "-$0.22M", "$18.60M"], 5, 900),
        ],
        pages,
        facts=facts,
    )


def packet_architecture_floorplan_diagrams() -> Case:
    def page(title: str, subtitle: str) -> Image.Image:
        img = Image.new("RGB", (PAGE_W, PAGE_H), "#ffffff")
        d = ImageDraw.Draw(img)
        d.text((72, 58), "Orion Biologics | Lab network renovation", fill="#334155", font=F["tiny_bold"])
        d.text((72, 92), title, fill="#111827", font=F["h1"])
        d.text((72, 132), subtitle, fill="#475569", font=F["small"])
        d.line((72, 178, 1580, 178), fill="#cbd5e1", width=2)
        d.text((1410, 60), "Rev C | 2026-06-12", fill="#111827", font=F["small_bold"])
        return img

    pages: list[Image.Image] = []

    p1 = page("Packet Index and Revision Control", "Six artifacts assembled from CAD, network, electrical, and RFI exports")
    d = ImageDraw.Draw(p1)
    rows = [
        ["Page", "Artifact", "Review focus"],
        ["1", "Index", "Rev C and Rev B warning"],
        ["2", "Floor plan", "Rooms, dimensions, doors, egress, and callouts"],
        ["3", "Rack elevation", "Rack units and device names"],
        ["4", "Network topology", "Arrow direction, VLANs, subnets, and dashed path"],
        ["5", "Panel schedule", "Circuit/load/breaker/emergency fields"],
        ["6", "RFI markup", "Revision cloud, answer, and final field states"],
    ]
    draw_ledger(d, 90, 250, [110, 310, 840], rows, 68)
    draw_note(d, (90, 820, 1510, 1010), "Superseded source warning", "Rev B labels Lab B door as D-214A. Rev C changes the corridor door to D-214B and adds card reader CR-6 on the corridor side. Rev C controls.", "#991b1b")
    pages.append(p1)

    p2 = page("Floor Plan A2.14 - Suite 214", "Room dimensions, egress, and callout binding")
    d = ImageDraw.Draw(p2)
    x0, y0 = 130, 260
    for gx in range(x0, x0 + 1121, 70):
        d.line((gx, y0, gx, y0 + 820), fill="#f1f5f9", width=1)
    for gy in range(y0, y0 + 821, 70):
        d.line((x0, gy, x0 + 1120, gy), fill="#f1f5f9", width=1)
    d.rectangle((x0, y0, x0 + 1120, y0 + 820), outline="#111827", width=5)
    d.line((x0 + 420, y0, x0 + 420, y0 + 820), fill="#111827", width=4)
    d.line((x0 + 780, y0, x0 + 780, y0 + 820), fill="#111827", width=4)
    d.line((x0, y0 + 390, x0 + 1120, y0 + 390), fill="#111827", width=4)
    d.arc((x0 + 420, y0 + 360, x0 + 510, y0 + 450), start=180, end=270, fill="#334155", width=2)
    d.line((x0 + 420, y0 + 390, x0 + 505, y0 + 390), fill="white", width=6)
    d.line((x0 + 780, y0 + 380, x0 + 875, y0 + 380), fill="white", width=6)
    d.arc((x0 + 780, y0 + 340, x0 + 875, y0 + 435), start=90, end=180, fill="#334155", width=2)
    rooms = [
        ("214 Clean Prep", "18 ft 6 in x 12 ft 0 in", x0 + 55, y0 + 120),
        ("215 Lab B", "16 ft 0 in x 12 ft 0 in", x0 + 475, y0 + 120),
        ("216 Freezer", "10 ft 6 in x 12 ft 0 in", x0 + 835, y0 + 120),
        ("C2 Corridor", "egress west", x0 + 55, y0 + 545),
        ("217 Wash", "12 ft 0 in x 10 ft 0 in", x0 + 475, y0 + 545),
        ("218 IT Closet", "10 ft 6 in x 10 ft 0 in", x0 + 835, y0 + 545),
    ]
    for name, dim, x, y in rooms:
        d.text((x, y), name, fill="#111827", font=F["small_bold"])
        d.text((x, y + 38), dim, fill="#475569", font=F["tiny"])
    d.line((x0 + 290, y0 + 390, x0 + 200, y0 + 520), fill="#16a34a", width=7)
    d.polygon([(x0 + 190, y0 + 535), (x0 + 230, y0 + 510), (x0 + 210, y0 + 555)], fill="#16a34a")
    d.text((x0 + 245, y0 + 505), "Egress to C2", fill="#166534", font=F["tiny_bold"])
    callouts = [
        ("6", x0 + 700, y0 + 390, "card reader CR-6", x0 + 620, y0 + 430),
        ("9", x0 + 930, y0 + 640, "rack R2", x0 + 865, y0 + 690),
        ("11", x0 + 1010, y0 + 270, "freezer FZ-3", x0 + 925, y0 + 225),
    ]
    for label, x, y, text, lx, ly in callouts:
        d.ellipse((x - 20, y - 20, x + 20, y + 20), fill="#fee2e2", outline="#991b1b", width=4)
        d.text((x - 8, y - 13), label, fill="#991b1b", font=F["tiny_bold"])
        d.line((x + 20, y, lx, ly), fill="#991b1b", width=2)
        d.rounded_rectangle((lx, ly - 18, lx + 170, ly + 22), radius=5, fill="white", outline="#991b1b", width=2)
        d.text((lx + 8, ly - 10), text, fill="#991b1b", font=F["tiny_bold"])
    d.line((x0, y0 - 35, x0 + 1120, y0 - 35), fill="#64748b", width=2)
    d.text((x0 + 480, y0 - 68), "45 ft 0 in overall", fill="#475569", font=F["tiny_bold"])
    d.line((x0 - 35, y0, x0 - 35, y0 + 820), fill="#64748b", width=2)
    d.text((x0 - 85, y0 + 380), "22 ft 0 in", fill="#475569", font=F["tiny_bold"])
    d.rounded_rectangle((1290, 260, 1540, 710), radius=14, fill="#f8fafc", outline="#334155", width=3)
    draw_text(d, (1315, 300), "Door schedule: D-214B is the Lab B corridor door. D-214A is the old Rev B label and is superseded.", F["tiny"], width=21, leading=25)
    draw_section(d, 110, 1220, "Door and room coordination schedule", w=1360)
    coord_rows = [
        ["Room/door", "Rev C field condition", "Linked artifact"],
        ["214 Clean Prep", "tablet dock on D214-01", "rack port CS-2/01"],
        ["215 Lab B / D-214B", "CR-6 corridor side; panel L2-15", "RFI-214B final"],
        ["216 Freezer", "FZ-3 monitor at callout 11", "VLAN 240 + L2-17"],
        ["218 IT Closet", "rack R2, UPS A", "panel L2-19"],
    ]
    draw_ledger(d, 130, 1295, [260, 520, 360], coord_rows, 58)
    draw_note(d, (130, 1725, 1490, 1890), "Field measurement note", "Overall suite width is 45 ft 0 in. Overall depth is 22 ft 0 in. Door D-214B is the only door label revised by RFI-214B.", "#334155")
    pages.append(p2)

    p3 = page("Rack Elevation R2", "U positions, devices, and patch mapping")
    d = ImageDraw.Draw(p3)
    rack_x, rack_y = 160, 250
    d.rectangle((rack_x, rack_y, rack_x + 360, rack_y + 980), outline="#111827", width=5)
    devices = [
        ("U42", "Core switch CS-2", "48p PoE", 42, 2, "#dbeafe"),
        ("U36", "Patch panel PP-7", "lab drops 214-218", 36, 2, "#f8fafc"),
        ("U30", "Firewall FW-02", "HA secondary", 30, 2, "#fee2e2"),
        ("U24", "UPS A", "2.2 kVA", 24, 3, "#fef3c7"),
        ("U18", "Freezer monitor GW-3", "Modbus gateway", 18, 1, "#dcfce7"),
        ("U12", "NVR camera bridge", "VLAN 240", 12, 2, "#ede9fe"),
    ]
    for u_label, name, note, u, height, color in devices:
        y = rack_y + (42 - u) * 22
        d.rectangle((rack_x + 70, y, rack_x + 330, y + height * 22), fill=color, outline="#111827", width=2)
        d.text((rack_x + 18, y + 5), u_label, fill="#475569", font=F["tiny_bold"])
        d.text((rack_x + 92, y + 4), name, fill="#111827", font=F["tiny_bold"])
        d.text((rack_x + 92, y + 26), note, fill="#475569", font=F["tiny"])
    for i in range(0, 43, 6):
        y = rack_y + i * 22
        d.text((rack_x - 52, y), f"U{42 - i}", fill="#475569", font=F["tiny"])
    rows = [
        ["Port", "Drop", "Room", "Device", "VLAN"],
        ["CS-2/01", "D214-01", "214 Clean Prep", "tablet dock", "210"],
        ["CS-2/07", "D215-03", "215 Lab B", "card reader CR-6", "230"],
        ["CS-2/12", "D216-02", "216 Freezer", "FZ-3 monitor", "240"],
        ["CS-2/19", "D218-01", "218 IT Closet", "FW-02 mgmt", "99"],
    ]
    draw_ledger(d, 620, 275, [170, 170, 260, 300, 100], rows, 62)
    draw_note(d, (625, 780, 1510, 980), "Rack note", "Firewall FW-02 occupies U30-U31. Core switch CS-2 is U42-U43. NVR camera bridge belongs to VLAN 240, not VLAN 230.", "#9a3412")
    pages.append(p3)

    p4 = page("Network Topology N1.07", "Arrows, VLANs, subnets, and optional path")
    d = ImageDraw.Draw(p4)
    nodes = {
        "FW-02": (150, 515),
        "CS-2": (485, 515),
        "CR-6": (835, 300),
        "FZ-3": (835, 710),
        "NVR": (1255, 300),
        "QA subnet": (1255, 710),
    }
    for name, (x, y) in nodes.items():
        d.rounded_rectangle((x, y, x + 210, y + 90), radius=10, fill="#f8fafc", outline="#334155", width=3)
        d.text((x + 20, y + 24), name, fill="#111827", font=F["small_bold"])
    def routed_arrow(points: list[tuple[int, int]], color: str = "#2563eb", dashed: bool = False) -> None:
        for start, end in zip(points, points[1:]):
            x1, y1 = start
            x2, y2 = end
            if dashed:
                steps = max(1, int(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 // 22))
                for step in range(0, steps, 2):
                    xa = x1 + (x2 - x1) * step / steps
                    ya = y1 + (y2 - y1) * step / steps
                    xb = x1 + (x2 - x1) * min(step + 1, steps) / steps
                    yb = y1 + (y2 - y1) * min(step + 1, steps) / steps
                    d.line((xa, ya, xb, yb), fill=color, width=3)
            else:
                d.line((x1, y1, x2, y2), fill=color, width=4)
        x2, y2 = points[-1]
        x1, y1 = points[-2]
        if abs(x2 - x1) >= abs(y2 - y1):
            if x2 >= x1:
                d.polygon([(x2, y2), (x2 - 18, y2 - 8), (x2 - 18, y2 + 8)], fill=color)
            else:
                d.polygon([(x2, y2), (x2 + 18, y2 - 8), (x2 + 18, y2 + 8)], fill=color)
        else:
            if y2 >= y1:
                d.polygon([(x2, y2), (x2 - 8, y2 - 18), (x2 + 8, y2 - 18)], fill=color)
            else:
                d.polygon([(x2, y2), (x2 - 8, y2 + 18), (x2 + 8, y2 + 18)], fill=color)

    routes = [
        ("trunk VLAN 99/210/230/240", [(360, 560), (485, 560)], (275, 450), "#2563eb", False),
        ("VLAN 230 access control", [(695, 548), (760, 548), (760, 345), (835, 345)], (600, 360), "#2563eb", False),
        ("VLAN 240 10.42.40.0/24", [(695, 582), (760, 582), (760, 755), (835, 755)], (600, 665), "#2563eb", False),
        ("VLAN 210 10.42.10.0/24", [(695, 610), (1185, 610), (1185, 755), (1255, 755)], (860, 615), "#2563eb", False),
        ("badge event mirror", [(1045, 345), (1255, 345)], (1070, 245), "#2563eb", False),
        ("dashed optional alert overlay", [(1045, 755), (1165, 755), (1165, 410), (1255, 410)], (1010, 575), "#64748b", True),
    ]
    for label, points, label_xy, color, dashed in routes:
        routed_arrow(points, color=color, dashed=dashed)
        lx, ly = label_xy
        d.rounded_rectangle((lx, ly, lx + 260, ly + 42), radius=5, fill="white", outline="#93c5fd", width=2)
        d.text((lx + 10, ly + 10), label, fill=color, font=F["tiny_bold"])
    draw_note(d, (140, 1015, 1510, 1205), "Subnet note", "VLAN 240 maps to freezer and camera telemetry subnet 10.42.40.0/24. VLAN 230 is access control. VLAN 210 is QA devices.", "#334155")
    draw_section(d, 110, 1340, "Port and firewall rule extract", w=1380)
    port_rows = [
        ["Rule/port", "Source", "Destination", "VLAN", "State"],
        ["ACL-230-06", "CR-6", "NVR event mirror", "230 to 240", "permit one-way"],
        ["ACL-240-11", "FZ-3", "QA subnet telemetry", "240 to 210", "deny except broker"],
        ["TRK-CS2-FW02", "CS-2", "FW-02", "99/210/230/240", "tagged trunk"],
        ["OPT-CAM", "FZ-3 optional overlay", "NVR", "240", "dashed / not base scope"],
    ]
    draw_ledger(d, 130, 1415, [180, 240, 330, 220, 260], port_rows, 58)
    pages.append(p4)

    p5 = page("Electrical Panel LP-2 Schedule", "Circuit/load/breaker/emergency fields")
    d = ImageDraw.Draw(p5)
    rows = [
        ["Circuit", "Load", "Breaker", "Emergency?", "Room", "Note"],
        ["L2-11", "Bench outlets B", "20A/1P", "No", "215 Lab B", "GFCI"],
        ["L2-13", "Autoclave AC-1", "30A/2P", "No", "217 Wash", "dedicated"],
        ["L2-15", "Door controller DC-6", "20A/1P", "Yes", "215 Lab B", "feeds CR-6"],
        ["L2-17", "Freezer FZ-3", "20A/1P", "Yes", "216 Freezer", "monitor required"],
        ["L2-19", "Rack R2 UPS", "20A/1P", "Yes", "218 IT Closet", "UPS A"],
        ["L2-21", "Spare", "20A/1P", "No", "-", "hold for Rev D"],
    ]
    draw_ledger(d, 70, 235, [140, 290, 170, 170, 190, 320], rows, 64)
    draw_note(d, (80, 800, 1510, 970), "Panel note", "Emergency circuits are L2-15, L2-17, and L2-19. L2-17 is Freezer FZ-3 and must match callout 11 on the floor plan.", "#991b1b")
    draw_section(d, 80, 1140, "Load summary and emergency branch check", w=1390)
    load_rows = [
        ["Branch", "Connected load", "Emergency load", "Reviewer note"],
        ["Normal receptacles", "3.2 kVA", "0.0 kVA", "bench + autoclave only"],
        ["Access control", "0.4 kVA", "0.4 kVA", "DC-6 on L2-15"],
        ["Cold storage", "0.7 kVA", "0.7 kVA", "FZ-3 on L2-17"],
        ["IT / UPS", "1.1 kVA", "1.1 kVA", "R2 UPS on L2-19"],
        ["Spare capacity", "2.6 kVA", "-", "L2-21 held for Rev D"],
    ]
    draw_ledger(d, 100, 1215, [260, 230, 230, 470], load_rows, 58)
    checkbox(d, 110, 1650, "Emergency branch labels match floor plan callouts", True, F["small"])
    checkbox(d, 110, 1710, "L2-21 released for construction", False, F["small"])
    checkbox(d, 110, 1770, "Freezer monitor moved to normal power", False, F["small"])
    pages.append(p5)

    p6 = page("RFI-214B Markup and Final Answer", "Revision cloud, answer, and final field states")
    d = ImageDraw.Draw(p6)
    rows_rfi = [
        ["RFI", "Discipline", "Opened", "Answered", "Status"],
        ["214B", "Access control / architectural", "2026-06-09", "2026-06-12", "Issued Rev C"],
    ]
    draw_ledger(d, 85, 245, [140, 430, 220, 220, 240], rows_rfi, 62)
    d.rounded_rectangle((95, 430, 760, 710), radius=10, fill="#f8fafc", outline="#334155", width=2)
    draw_text(d, (130, 465), "Question: Door label conflict. CAD Rev B shows D-214A at Lab B corridor. Field sticker and security rough-in show D-214B. Which label controls for access control schedule?", F["small"], width=45, leading=31)
    d.rounded_rectangle((860, 430, 1510, 710), radius=10, fill="#ecfdf5", outline="#166534", width=2)
    draw_text(d, (895, 465), "Response: Use D-214B for the Lab B corridor door. Add CR-6 card reader on corridor side. Update access control schedule and panel LP-2 circuit L2-15. Rev C dated 2026-06-12 controls.", F["small"], width=42, leading=31)
    d.rectangle((760, 785, 1450, 1125), outline="#cbd5e1", width=2)
    d.text((790, 815), "Plan excerpt markup", fill="#111827", font=F["small_bold"])
    d.rectangle((820, 875, 1340, 1035), outline="#111827", width=3)
    d.line((1080, 875, 1080, 1035), fill="#111827", width=3)
    d.text((860, 925), "C2 corridor", fill="#111827", font=F["tiny_bold"])
    d.text((1145, 902), "215 Lab B", fill="#111827", font=F["tiny_bold"])
    d.ellipse((1050, 945, 1110, 1005), outline="#991b1b", width=4)
    d.line((1110, 975, 1235, 870), fill="#991b1b", width=3)
    d.rounded_rectangle((1235, 842, 1430, 895), radius=5, fill="white", outline="#991b1b", width=2)
    d.text((1250, 858), "D-214B + CR-6", fill="#991b1b", font=F["tiny_bold"])
    rows = [
        ["Field", "Rev B", "Rev C final"],
        ["Door label", "D-214A", "D-214B"],
        ["Reader", "none", "CR-6 corridor side"],
        ["Circuit", "unassigned", "L2-15"],
        ["Schedule status", "draft", "issued"],
    ]
    draw_ledger(d, 115, 1180, [290, 260, 420], rows, 64)
    draw_note(d, (95, 1550, 1510, 1715), "Signoff", "Answered by A. Verma, Architect of Record. Security reviewer initials: TN. Contractor acknowledged in field log 2026-06-13.", "#334155")
    pages.append(p6)

    gold = """# Orion Biologics Lab Network Renovation Packet

Rev C dated 2026-06-12 controls. Rev B labels Lab B door as D-214A, but Rev C changes the corridor door to D-214B and adds card reader CR-6 on the corridor side.

## Floor Plan A2.14

Suite 214 contains 214 Clean Prep measuring 18 ft 6 in x 12 ft 0 in, 215 Lab B measuring 16 ft 0 in x 12 ft 0 in, 216 Freezer measuring 10 ft 6 in x 12 ft 0 in, C2 Corridor, 217 Wash measuring 12 ft 0 in x 10 ft 0 in, and 218 IT Closet measuring 10 ft 6 in x 10 ft 0 in.

The egress arrow exits from Clean Prep toward C2 Corridor. Callout 6 is card reader CR-6 at the Lab B corridor door. Callout 9 is rack R2 in 218 IT Closet. Callout 11 is freezer FZ-3 in 216 Freezer. Door schedule: D-214B is the Lab B corridor door; D-214A is the old Rev B label and is superseded.

Door and room coordination schedule:

| Room/door | Rev C field condition | Linked artifact |
| --- | --- | --- |
| 214 Clean Prep | tablet dock on D214-01 | rack port CS-2/01 |
| 215 Lab B / D-214B | CR-6 corridor side; panel L2-15 | RFI-214B final |
| 216 Freezer | FZ-3 monitor at callout 11 | VLAN 240 + L2-17 |
| 218 IT Closet | rack R2, UPS A | panel L2-19 |

Field measurement note: overall suite width is 45 ft 0 in; overall depth is 22 ft 0 in. Door D-214B is the only door label revised by RFI-214B.

## Rack Elevation R2

Core switch CS-2 occupies U42-U43 and is a 48-port PoE switch. Patch panel PP-7 occupies U36-U37 for lab drops 214-218. Firewall FW-02 occupies U30-U31 and is HA secondary. UPS A occupies U24-U26 and is 2.2 kVA. Freezer monitor GW-3 is at U18. NVR camera bridge occupies U12-U13 and belongs to VLAN 240.

| Port | Drop | Room | Device | VLAN |
| --- | --- | --- | --- | --- |
| CS-2/01 | D214-01 | 214 Clean Prep | tablet dock | 210 |
| CS-2/07 | D215-03 | 215 Lab B | card reader CR-6 | 230 |
| CS-2/12 | D216-02 | 216 Freezer | FZ-3 monitor | 240 |
| CS-2/19 | D218-01 | 218 IT Closet | FW-02 mgmt | 99 |

## Network Topology N1.07

FW-02 connects to CS-2 over trunk VLAN 99/210/230/240. CS-2 connects to CR-6 over VLAN 230 access control. CS-2 connects to FZ-3 over VLAN 240 / 10.42.40.0/24. CS-2 connects to QA subnet over VLAN 210 / 10.42.10.0/24. CR-6 connects to NVR via badge event mirror. A dashed optional alert overlay runs from FZ-3 to NVR. VLAN 240 maps to freezer and camera telemetry; VLAN 230 is access control; VLAN 210 is QA devices.

Port and firewall rule extract:

| Rule/port | Source | Destination | VLAN | State |
| --- | --- | --- | --- | --- |
| ACL-230-06 | CR-6 | NVR event mirror | 230 to 240 | permit one-way |
| ACL-240-11 | FZ-3 | QA subnet telemetry | 240 to 210 | deny except broker |
| TRK-CS2-FW02 | CS-2 | FW-02 | 99/210/230/240 | tagged trunk |
| OPT-CAM | FZ-3 optional overlay | NVR | 240 | dashed / not base scope |

## Electrical Panel LP-2 Schedule

| Circuit | Load | Breaker | Emergency? | Room | Note |
| --- | --- | --- | --- | --- | --- |
| L2-11 | Bench outlets B | 20A/1P | No | 215 Lab B | GFCI |
| L2-13 | Autoclave AC-1 | 30A/2P | No | 217 Wash | dedicated |
| L2-15 | Door controller DC-6 | 20A/1P | Yes | 215 Lab B | feeds CR-6 |
| L2-17 | Freezer FZ-3 | 20A/1P | Yes | 216 Freezer | monitor required |
| L2-19 | Rack R2 UPS | 20A/1P | Yes | 218 IT Closet | UPS A |
| L2-21 | Spare | 20A/1P | No | - | hold for Rev D |

Emergency circuits are L2-15, L2-17, and L2-19. L2-17 is Freezer FZ-3 and matches floor-plan callout 11.

Load summary and emergency branch check:

| Branch | Connected load | Emergency load | Reviewer note |
| --- | ---: | ---: | --- |
| Normal receptacles | 3.2 kVA | 0.0 kVA | bench + autoclave only |
| Access control | 0.4 kVA | 0.4 kVA | DC-6 on L2-15 |
| Cold storage | 0.7 kVA | 0.7 kVA | FZ-3 on L2-17 |
| IT / UPS | 1.1 kVA | 1.1 kVA | R2 UPS on L2-19 |
| Spare capacity | 2.6 kVA | - | L2-21 held for Rev D |

Emergency branch labels match floor plan callouts is checked. L2-21 released for construction is unchecked. Freezer monitor moved to normal power is unchecked.

## RFI-214B

Question: CAD Rev B shows D-214A at Lab B corridor. Field sticker and security rough-in show D-214B. Which label controls for access control schedule?

Final answer: Use D-214B for the Lab B corridor door. Add CR-6 card reader on corridor side. Update access control schedule and panel LP-2 circuit L2-15. Rev C dated 2026-06-12 controls.

Revision cloud text: D-214B + CR-6.

| Field | Rev B | Rev C final |
| --- | --- | --- |
| Door label | D-214A | D-214B |
| Reader | none | CR-6 corridor side |
| Circuit | unassigned | L2-15 |
| Schedule status | draft | issued |
"""

    facts = [
        fact("p15.revision", "source_state", 6, "Rev C dated 2026-06-12 controls; Rev B D-214A is superseded by D-214B and CR-6 corridor-side reader."),
        fact("p15.rooms", "visual_relation", 10, "Floor plan preserves room names and dimensions for 214 Clean Prep, 215 Lab B, 216 Freezer, 217 Wash, and 218 IT Closet, plus overall 45 ft 0 in width, 22 ft 0 in depth, and coordination schedule linking 214 to CS-2/01, D-214B to CR-6/L2-15, 216 to VLAN 240/L2-17, and 218 to rack R2/L2-19."),
        fact("p15.egress", "visual_relation", 5, "Egress arrow exits from Clean Prep toward C2 Corridor."),
        fact("p15.callouts", "visual_relation", 8, "Callout 6 is CR-6 at Lab B corridor door; callout 9 is rack R2 in 218 IT Closet; callout 11 is freezer FZ-3 in 216 Freezer."),
        fact("p15.rack.units", "visual_relation", 10, "Rack elevation preserves CS-2 at U42-U43, PP-7 U36-U37, FW-02 U30-U31, UPS A U24-U26, GW-3 U18, NVR bridge U12-U13."),
        fact("p15.patch.table", "table_cell", 8, "Patch table preserves CS-2/01 D214-01 tablet dock VLAN 210, CS-2/07 D215-03 CR-6 VLAN 230, CS-2/12 D216-02 FZ-3 VLAN 240, CS-2/19 D218-01 FW-02 mgmt VLAN 99."),
        fact("p15.network.arrows", "visual_relation", 12, "Network topology preserves directed links FW-02 to CS-2 trunk, CS-2 to CR-6 VLAN 230, CS-2 to FZ-3 VLAN 240, CS-2 to QA subnet VLAN 210, CR-6 to NVR badge mirror, dashed optional FZ-3 to NVR alert overlay, plus rule extract ACL-230-06, ACL-240-11, TRK-CS2-FW02, and OPT-CAM with source, destination, VLAN, and state."),
        fact("p15.subnets", "visual_relation", 8, "VLAN 240 maps to 10.42.40.0/24 freezer/camera telemetry; VLAN 230 is access control; VLAN 210 is QA devices; ACL-230-06 permits one-way CR-6 to NVR event mirror, and ACL-240-11 denies FZ-3 to QA telemetry except broker."),
        fact("p15.optional.path", "visual_relation", 4, "Dashed optional alert overlay runs from FZ-3 to NVR."),
        fact("p15.panel", "table_cell", 12, "Panel LP-2 schedule preserves all circuits L2-11, L2-13, L2-15, L2-17, L2-19, L2-21 with loads, breakers, emergency states, rooms, notes, and load summary rows for normal receptacles 3.2/0.0 kVA, access control 0.4/0.4, cold storage 0.7/0.7, IT/UPS 1.1/1.1, spare capacity 2.6/- held for Rev D."),
        fact("p15.emergency", "source_state", 8, "Emergency circuits are L2-15, L2-17, and L2-19; L2-17 is Freezer FZ-3 and matches callout 11; emergency branch labels match floor plan callouts is checked, while L2-21 released for construction and freezer monitor moved to normal power are unchecked."),
        fact("p15.rfi.answer", "source_state", 8, "RFI final answer uses D-214B, adds CR-6 card reader on corridor side, updates access control schedule and LP-2 circuit L2-15."),
        fact("p15.revision.cloud", "visual_relation", 5, "Revision cloud text says D-214B + CR-6."),
        fact("p15.rev.table", "table_cell", 6, "RFI field table preserves Door label D-214A to D-214B, Reader none to CR-6 corridor side, Circuit unassigned to L2-15, Schedule draft to issued."),
    ]

    return Case(
        "P15-architecture-floorplan-diagrams",
        "Architecture Floorplan Diagram Packet",
        "diagram",
        ["multi-page", "floorplan", "network", "rack", "panel-schedule", "rfi", "visual-relations"],
        "Stress diagram-to-Markdown reconstruction with spatial room relationships, rack positions, network arrows, circuits, and revision-source precedence.",
        "Six-page architecture/facilities packet with floorplan, rack elevation, topology, panel schedule, and RFI markup.",
        ["floorplan", "rack", "network topology", "panel schedule", "RFI"],
        ["Describe diagram relationships with labels and values.", "Preserve revision precedence.", "Bind callouts/circuits/VLANs exactly."],
        gold,
        [
            near_check("p15-cr6", "visual_relation", ["D-214B", "CR-6", "corridor", "L2-15"], 5, 700),
            near_check("p15-vlan240", "visual_relation", ["VLAN 240", "10.42.40.0/24", "FZ-3", "NVR"], 5, 800),
        ],
        pages,
        facts=facts,
    )


def packet_publication_report_layout() -> Case:
    def page(title: str, kicker: str = "Meridian Harbor Resilience Bond Oversight | June 2026") -> Image.Image:
        img = Image.new("RGB", (PAGE_W, PAGE_H), "#fbfaf6")
        d = ImageDraw.Draw(img)
        d.text((92, 58), kicker, fill="#475569", font=F["tiny_bold"])
        d.text((92, 92), title, fill="#111827", font=F["h1"])
        d.line((92, 150, 1585, 150), fill="#111827", width=2)
        d.text((1480, 60), "Draft 4.2", fill="#7f1d1d", font=F["tiny_bold"])
        return img

    def draw_photo_panel(d: ImageDraw.ImageDraw, box: tuple[int, int, int, int], label: str, caption: str, tint="#dbeafe") -> None:
        x1, y1, x2, y2 = box
        d.rectangle(box, fill="#d7e3ea", outline="#475569", width=2)
        horizon = y1 + int((y2 - y1) * 0.46)
        for y in range(y1 + 2, y2 - 2):
            if y < horizon:
                t = (y - y1) / max(1, horizon - y1)
                col = (205 - int(18 * t), 222 - int(8 * t), 232 - int(2 * t))
            else:
                t = (y - horizon) / max(1, y2 - horizon)
                col = (126 - int(28 * t), 151 - int(42 * t), 161 - int(38 * t))
            d.line((x1 + 2, y, x2 - 2, y), fill=col)
        for i in range(0, 130):
            px = x1 + 7 + ((i * 37) % max(1, x2 - x1 - 14))
            py = y1 + 7 + ((i * 53) % max(1, y2 - y1 - 14))
            shade = 95 + ((i * 11) % 70)
            d.point((px, py), fill=(shade, shade + 8, shade + 10))
        deck = [(x1 + 35, y2 - 56), (x2 - 18, y2 - 104), (x2 - 18, y2 - 8), (x1 + 15, y2 - 8)]
        d.polygon(deck, fill="#7c6f62")
        for off in range(0, x2 - x1, 58):
            d.line((x1 + off, y2 - 58, x1 + off + 90, y2 - 8), fill="#5b5148", width=1)
        pier = [(x1 + 38, y2 - 92), (x2 - 22, y2 - 148), (x2 - 6, y2 - 42), (x1 + 18, y2 - 18)]
        d.polygon(pier, fill="#6b7280", outline="#374151")
        for off in range(0, x2 - x1 - 35, 44):
            d.line((x1 + off + 6, y2 - 94, min(x2 - 8, x1 + off + 76), y2 - 36), fill="#4b5563", width=1)
        gangway = [(x1 + 78, y1 + 168), (x2 - 62, y1 + 108), (x2 - 24, y1 + 176), (x1 + 118, y1 + 246)]
        d.polygon(gangway, fill="#9ca3af", outline="#334155")
        d.line((x1 + 84, y1 + 168, x2 - 56, y1 + 108), fill="#475569", width=5)
        d.line((x1 + 118, y1 + 247, x2 - 25, y1 + 176), fill="#475569", width=5)
        for off in range(0, min(390, x2 - x1 - 140), 36):
            d.line((x1 + 104 + off, y1 + 178 - off // 8, min(x2 - 10, x1 + 132 + off), y1 + 238 - off // 7), fill="#334155", width=1)
        shoe = [(x1 + 255, y1 + 230), (x1 + 412, y1 + 206), (x1 + 425, y1 + 250), (x1 + 270, y1 + 279)]
        d.polygon(shoe, fill="#374151", outline="#111827")
        for bx, by in [(x1 + 288, y1 + 243), (x1 + 330, y1 + 235), (x1 + 373, y1 + 226)]:
            d.ellipse((bx - 6, by - 6, bx + 6, by + 6), fill="#d1d5db", outline="#111827")
        d.line((x1 + 78, y1 + 264, x1 + 445, y1 + 198), fill="#f59e0b", width=3)
        d.text((x1 + 84, y1 + 270), "bearing shoe", fill="#78350f", font=F["tiny_bold"])
        d.rectangle((x2 - 88, y1 + 86, x2 - 18, y1 + 182), fill="#e5e7eb", outline="#334155")
        d.line((x2 - 72, y1 + 96, x2 - 70, y1 + 170), fill="#475569", width=3)
        d.line((x2 - 49, y1 + 96, x2 - 47, y1 + 170), fill="#475569", width=3)
        d.rectangle((x1 + 36, y1 + 26, x1 + 190, y1 + 56), fill=(255, 255, 255, 218), outline="#cbd5e1")
        d.text((x1 + 48, y1 + 32), label, fill="#111827", font=F["tiny_bold"])
        draw_text(d, (x1, y2 + 14), caption, F["tiny"], fill="#334155", width=max(28, int((x2 - x1) / 14)), leading=23)

    pages: list[Image.Image] = []

    p1 = page("Meridian Harbor Resilience Bond - Oversight Report")
    d = ImageDraw.Draw(p1)
    d.text((92, 182), "Prepared for the Bond Oversight Committee | Publication date 2026-06-18 | Issue 04", fill="#475569", font=F["small"])
    d.text((92, 255), "Executive Brief", fill="#111827", font=F["title"])
    draw_text(
        d,
        (92, 330),
        "The pier retrofit remains inside the amended bond authorization, but the committee status is mixed. Field inspections show the east gangway bearing replacement is complete, the ferry canopy panels remain behind schedule, and a separate lighting grant sits outside the bond contingency. Sidebars, captions, footnotes, the pull quote, and appendix tables carry material context for the committee record.",
        F["small"],
        width=58,
        leading=31,
    )
    draw_photo_panel(
        d,
        (985, 265, 1510, 640),
        "Inspection sketch 1",
        "Inspection sketch 1. Workers test the east gangway on 14 May.",
        "#e2e8f0",
    )
    rows = [
        ["Metric", "Visible value", "Note"],
        ["Bond authorization", "$42.0M", "not incl. lighting grant"],
        ["Forecast at completion", "$40.8M", "$1.2M under bond cap"],
        ["Uncommitted contingency", "$2.4M", "after pending CO-17"],
        ["Inspected piles", "214", "31 require coating"],
        ["Evening service extension", "10:40 p.m.", "pilot through Sep."],
    ]
    draw_ledger(d, 92, 760, [330, 260, 440], rows, 56)
    d.text((1085, 860), '"The last boat now leaves at 10:40 p.m."', fill="#7f1d1d", font=F["h2"])
    d.text((1090, 912), "Pull quote from article page.", fill="#475569", font=F["tiny"])
    draw_note(d, (92, 1255, 1515, 1425), "Document map", "Page order is cover, article, budget table, schedule graphic, map spread, community comments, appendix table part 1, appendix table part 2. Appendix headers repeat for readability.", "#1d4ed8")
    risk_rows = [
        ["Open item", "Owner", "Next date", "Visible status"],
        ["CO-17 canopy panels", "Port PMO", "2026-07-18", "pending decision"],
        ["Pile coating change batch", "HarborWorks", "2026-07-02", "pricing review"],
        ["Lighting controls scope", "City Energy", "2026-07-10", "grant-funded only"],
        ["Evening marshal staffing", "Ferry Ops", "2026-06-28", "pilot roster open"],
    ]
    draw_ledger(d, 92, 1515, [390, 240, 220, 360], risk_rows, 54)
    draw_text(d, (92, 1808), "Committee handling note: none of the four open items authorizes drawing from the bond contingency without a separate change-order vote.", F["small"], fill="#7f1d1d", width=92, leading=29)
    pages.append(p1)

    p2 = page("Feature Article - The North Pier Reopens")
    d = ImageDraw.Draw(p2)
    d.text((92, 175), "Maya Chen | Harbor Monthly | June 2026", fill="#475569", font=F["small_bold"])
    d.text((92, 222), "Deck: A repaired ferry terminal returns with quieter ramps and longer evening service.", fill="#111827", font=F["small"])
    left = (
        "After eighteen months of construction fencing, the North Pier reopened with a quieter ramp drive, wider queuing lanes, and a late-evening ferry pilot. The work is not a new terminal. It is a resilience repair designed to keep existing service operating during king tides and winter storm surge. "
        "The most visible change is the east gangway bearing assembly, which was replaced in May after field tests showed uneven movement under full passenger load."
    )
    right = (
        "A corrected operating memo extends the last outbound boat to 10:40 p.m. on Fridays and Saturdays through September. Earlier drafts showed 10:15 p.m.; that value is superseded. Accessibility work includes six new wheelchair spaces, tactile warning strips, and a temporary ramp marshal during peak evening departures."
    )
    draw_text(d, (92, 310), left, F["small"], width=45, leading=30)
    d.rounded_rectangle((640, 405, 1135, 790), radius=8, fill="#f8fafc", outline="#64748b", width=2)
    d.text((670, 435), "Inspection log FT-0514 excerpt", fill="#111827", font=F["small_bold"])
    d.text((670, 470), "East gangway bearing assembly | field test 14 May", fill="#475569", font=F["tiny"])
    log_rows = [
        ["Item", "Observed record"],
        ["Load condition", "full passenger load"],
        ["Finding", "uneven bearing movement"],
        ["Action", "bearing shoe reset and fit-up"],
        ["Photo ref.", "IMG_0514-EB attached to field log"],
    ]
    draw_ledger(d, 670, 525, [155, 265], log_rows, 38)
    d.text((670, 742), "Caption: Crew fits the bearing shoe under the east gangway, 14 May.", fill="#334155", font=F["tiny"])
    draw_text(d, (1190, 310), right, F["small"], width=35, leading=30)
    d.line((90, 955, 1510, 955), fill="#94a3b8", width=1)
    d.text((135, 1010), '"The last boat now leaves at 10:40 p.m."', fill="#7f1d1d", font=F["h2"])
    rows2 = [
        ["By the numbers", ""],
        ["Repair budget", "$18.6M"],
        ["Piles inspected", "214"],
        ["Boarding-noise reduction", "32%"],
        ["New wheelchair spaces", "6"],
    ]
    draw_ledger(d, 980, 1020, [300, 190], rows2, 52)
    draw_note(d, (92, 1235, 905, 1375), "Funding sidebar note", "The lighting grant is mentioned in the sidebar but is not part of the bond authorization calculation.", "#92400e")
    service_rows = [
        ["Service change", "Before", "Current", "Scope"],
        ["Fri/Sat last boat", "10:15 p.m.", "10:40 p.m.", "pilot through Sep."],
        ["Ramp marshal", "none", "peak evenings", "temporary"],
        ["Wheelchair spaces", "2", "6", "terminal queue"],
        ["Noise complaints", "baseline", "32% lower", "boarding ramp"],
    ]
    draw_ledger(d, 92, 1440, [290, 210, 230, 330], service_rows, 52)
    source_rows = [
        ["Source note", "Checked item", "Article treatment"],
        ["Operating memo OP-26-17", "Fri/Sat last outbound corrected to 10:40 p.m.", "supersedes 10:15 draft"],
        ["Field test log FT-0514", "east gangway bearing test under passenger load", "supports inspection-log caption"],
        ["Access punch list AC-0620", "six wheelchair queue spaces installed", "matches sidebar metric"],
        ["Noise test NT-0604", "boarding-noise reduction 32%", "matches service table"],
    ]
    draw_ledger(d, 92, 1770, [315, 515, 405], source_rows, 48)
    pages.append(p2)

    p3 = page("Budget Review - Borderless Sources and Uses")
    d = ImageDraw.Draw(p3)
    d.text((92, 178), "Amounts in USD millions. Parentheses are unfavorable variances or credits. Superscript notes apply only to the row where shown.", fill="#475569", font=F["small"])
    rows = [
        ["Category", "Approved", "Committed", "Forecast", "Variance", "Footnote"],
        ["Sources", "", "", "", "", ""],
        ["2019 resilience bond", "42.0", "40.1", "40.8", "1.2", "1"],
        ["State pier safety grant", "5.5", "5.5", "5.5", "-", "restricted"],
        ["Lighting modernization grant", "1.8", "0.6", "1.8", "-", "2"],
        ["Uses", "", "", "", "", ""],
        ["East gangway bearings", "7.4", "7.1", "7.3", "0.1", ""],
        ["Pile coating and jackets", "11.2", "9.6", "10.9", "0.3", "3"],
        ["Canopy replacement", "8.6", "7.9", "9.4", "(0.8)", "CO-17 pending"],
        ["Terminal accessibility", "3.8", "3.4", "3.7", "0.1", ""],
        ["Program management", "4.2", "3.9", "4.1", "0.1", ""],
        ["Uncommitted contingency", "6.8", "6.4", "2.4", "(4.4)", "after CO-17"],
    ]
    draw_ledger(d, 70, 260, [335, 150, 160, 150, 145, 320], rows, 52)
    draw_section(d, 92, 990, "Footnotes", w=1250)
    draw_text(d, (110, 1055), "1. Bond authorization excludes the $1.8M lighting modernization grant. 2. Lighting grant may pay fixtures and controls only; it is outside bond contingency. 3. Thirty-one inspected piles require additional coating; five also require jacket repair.", F["small"], width=92, leading=30)
    d.text((1050, 1220), "Variance strip", fill="#111827", font=F["small_bold"])
    vals = [("Bearing", 0.1), ("Piles", 0.3), ("Canopy", -0.8), ("Access", 0.1), ("Mgmt", 0.1), ("Cont.", -4.4)]
    x = 1040
    for label, val in vals:
        color = "#0f766e" if val >= 0 else "#dc2626"
        h = min(116, int(abs(val) * 20) + 16)
        if val >= 0:
            d.rectangle((x, 1395 - h, x + 48, 1395), fill=color)
        else:
            d.rectangle((x, 1395, x + 48, 1395 + h), fill=color)
        d.text((x - 6, 1345), f"{val:+.1f}", fill=color, font=F["tiny_bold"])
        d.text((x - 6, 1435), label, fill="#111827", font=F["tiny"])
        x += 78
    rec_rows = [
        ["Reconciliation point", "Committee treatment"],
        ["Forecast $40.8M vs bond cap $42.0M", "$1.2M under cap before non-bond grants"],
        ["Lighting grant $1.8M", "separate restricted source, not contingency"],
        ["Canopy CO-17", "shown in forecast but pending commitment"],
        ["Contingency $2.4M", "after pending CO-17, not after lighting grant"],
    ]
    draw_ledger(d, 92, 1595, [520, 760], rec_rows, 56)
    pages.append(p3)

    p4 = page("Construction Schedule Graphic")
    d = ImageDraw.Draw(p4)
    d.text((92, 178), "Schedule is read from bar spans. Labels outside bars belong to the nearest connector line.", fill="#475569", font=F["small"])
    months = ["Apr", "May", "Jun", "Jul", "Aug", "Sep"]
    x0, y0 = 285, 350
    for i, month in enumerate(months):
        x = x0 + i * 185
        d.text((x + 45, 280), month, fill="#111827", font=F["small_bold"])
        d.line((x, 320, x, 1030), fill="#e2e8f0", width=2)
    tasks = [
        ("East gangway bearings", 0.15, 1.65, "#0f766e", "complete 05/22"),
        ("Pile coating", 0.4, 3.8, "#2563eb", "31 piles remain"),
        ("Canopy panels", 1.2, 4.8, "#dc2626", "slipped after CO-17"),
        ("Accessibility striping", 2.0, 3.2, "#0f766e", "complete 07/03"),
        ("Evening service pilot", 3.1, 5.9, "#7c3aed", "through Sep"),
        ("Lighting grant scope", 3.4, 5.4, "#64748b", "separate funding"),
    ]
    for idx, (label, start, end, color, note) in enumerate(tasks):
        y = y0 + idx * 105
        d.text((92, y + 18), label, fill="#111827", font=F["tiny_bold"])
        sx = x0 + int(start * 185)
        ex = x0 + int(end * 185)
        d.rectangle((sx, y, ex, y + 42), fill=color)
        d.line((ex, y + 21, ex + 70, y + 21), fill="#334155", width=2)
        d.text((ex + 80, y + 8), note, fill="#334155", font=F["tiny"])
    d.line((x0 + int(3.6 * 185), 305, x0 + int(3.6 * 185), 1030), fill="#991b1b", width=4)
    d.text((x0 + int(3.6 * 185) + 10, 1060), "CO-17 decision gate: 2026-07-18", fill="#991b1b", font=F["small_bold"])
    draw_note(d, (92, 1235, 1510, 1435), "Schedule interpretation", "Canopy panels are the only red slipped workstream. Lighting grant scope overlaps the bond schedule but is separately funded outside bond-cost recovery.", "#92400e")
    lookahead = [
        ["Date", "Milestone", "Dependency", "If missed"],
        ["2026-06-28", "Evening marshal roster", "Ferry Ops staffing", "pilot starts with reduced signage"],
        ["2026-07-02", "Pile coating price lock", "HarborWorks quote", "use allowance only"],
        ["2026-07-18", "CO-17 panel decision", "committee vote", "red canopy bar extends into Sep."],
        ["2026-08-15", "Lighting controller delivery", "grant purchase order", "no bond impact"],
    ]
    draw_ledger(d, 92, 1540, [190, 360, 360, 430], lookahead, 55)
    pages.append(p4)

    p5 = page("Map Spread - Work Zones and Service Changes")
    d = ImageDraw.Draw(p5)
    d.text((92, 178), "Harbor work-zone map excerpt. Callout letters, arrows, and legend colors are part of the published committee packet.", fill="#475569", font=F["small"])
    map_box = (140, 290, 1130, 1260)
    d.rectangle(map_box, fill="#dff1fb", outline="#334155", width=3)
    for gx in range(190, 1110, 115):
        d.line((gx, 310, gx, 1240), fill="#b9d7e8", width=1)
        d.text((gx - 18, 1248), f"E{gx-140:03d}", fill="#64748b", font=F["tiny"])
    for gy in range(340, 1240, 105):
        d.line((160, gy, 1110, gy), fill="#b9d7e8", width=1)
        d.text((95, gy - 7), f"N{1260-gy:03d}", fill="#64748b", font=F["tiny"])
    shoreline = [(140, 370), (260, 382), (340, 430), (460, 418), (610, 455), (735, 438), (865, 468), (1000, 448), (1130, 482), (1130, 1260), (140, 1260)]
    d.polygon(shoreline, fill="#e6dcc8", outline="#8a7a62")
    for sx in range(165, 1090, 76):
        d.line((sx, 470 + ((sx * 7) % 40), sx + 55, 500 + ((sx * 11) % 34)), fill="#c9b99b", width=1)
    harbor = [(205, 1010), (1010, 905), (1085, 1185), (260, 1230)]
    d.polygon(harbor, fill="#94a3b8", outline="#334155")
    for hx in range(240, 1030, 48):
        d.line((hx, 1012, hx + 85, 1210), fill="#64748b", width=1)
    terminal = [(250, 525), (980, 525), (980, 705), (830, 730), (250, 705)]
    d.polygon(terminal, fill="#f8fafc", outline="#334155", width=3)
    d.rectangle((270, 545, 950, 585), fill="#e5e7eb", outline="#cbd5e1")
    d.text((470, 615), "North Pier Terminal", fill="#111827", font=F["h2"])
    for bx in range(315, 940, 80):
        d.line((bx, 705, bx, 770 + ((bx // 80) % 3) * 8), fill="#475569", width=4)
    d.line((620, 705, 760, 1000), fill="#111827", width=6)
    d.polygon([(760, 1000), (740, 970), (785, 975)], fill="#111827")
    d.line((300, 805, 1050, 1165), fill="#f8fafc", width=8)
    d.line((300, 805, 1050, 1165), fill="#94a3b8", width=2)
    d.rectangle((338, 525, 485, 705), outline="#f59e0b", width=5)
    d.rectangle((760, 525, 905, 705), outline="#f59e0b", width=5)
    d.ellipse((630, 850, 770, 990), outline="#f59e0b", width=5)
    d.rectangle((930, 1070, 1060, 1165), outline="#f59e0b", width=5)
    for px, py in [(340, 750), (420, 760), (500, 765), (580, 790), (660, 820), (735, 850), (815, 883), (900, 920)]:
        d.ellipse((px - 5, py - 5, px + 5, py + 5), fill="#334155")
    d.polygon([(1055, 345), (1032, 400), (1078, 400)], fill="#111827")
    d.text((1048, 410), "N", fill="#111827", font=F["tiny_bold"])
    d.line((920, 1230, 1080, 1230), fill="#111827", width=3)
    d.text((955, 1198), "50 m", fill="#111827", font=F["tiny_bold"])
    callouts = [("A", 360, 560, "east gangway"), ("B", 825, 552, "canopy bay 3"), ("C", 690, 910, "pile zone C"), ("D", 980, 1110, "temporary dock")]
    for letter, x, y, label in callouts:
        d.ellipse((x - 26, y - 26, x + 26, y + 26), fill="#fef3c7", outline="#92400e", width=3)
        d.text((x - 8, y - 16), letter, fill="#92400e", font=F["small_bold"])
        d.text((x + 38, y - 12), label, fill="#111827", font=F["tiny_bold"])
    d.text((1215, 320), "Legend", fill="#111827", font=F["h2"])
    legend = [("#fef3c7", "active work zone"), ("#94a3b8", "ferry approach"), ("#111827", "passenger flow arrow"), ("#e0f2fe", "harbor water")]
    for i, (color, label) in enumerate(legend):
        y = 390 + i * 72
        d.rectangle((1220, y, 1260, y + 32), fill=color, outline="#334155")
        d.text((1280, y + 2), label, fill="#111827", font=F["tiny_bold"])
    draw_text(d, (1215, 750), "Map note: Callout B, canopy bay 3, is the only mapped item tied to CO-17. Callout D documents temporary dock access; evening-service pilot details are in the service section.", F["small"], fill="#334155", width=28, leading=28)
    d.text((185, 1330), "Caption: Public route shifts south of the terminal during canopy-panel removal.", fill="#334155", font=F["small"])
    constraint_rows = [
        ["Zone", "Constraint", "Planning note"],
        ["A east gangway", "bearing work complete", "closed; no active delay"],
        ["B canopy bay 3", "CO-17 pending", "ties to red schedule bar"],
        ["C pile zone C", "coating access by tide", "ties to 31-pile count"],
        ["D temporary dock", "temporary access only", "not evening-service pilot"],
    ]
    draw_ledger(d, 150, 1465, [260, 410, 520], constraint_rows, 56)
    pages.append(p5)

    p6 = page("Public Comment and Survey Page")
    d = ImageDraw.Draw(p6)
    d.text((92, 178), "Public comments are excerpts. Marginal labels identify topic, not speaker names.", fill="#475569", font=F["small"])
    comments = [
        ("Accessibility", "Ramp marshal was helpful, but tactile striping should continue to the ticket window."),
        ("Noise", "The new bearings are noticeably quieter during evening boarding."),
        ("Schedule", "The 10:40 p.m. Friday boat makes the return commute workable."),
        ("Lighting", "Please keep the lighting work visible as a separate grant item."),
    ]
    y = 270
    for topic, text in comments:
        d.line((120, y, 1040, y), fill="#cbd5e1", width=1)
        d.text((125, y + 24), topic, fill="#92400e", font=F["tiny_bold"])
        draw_text(d, (265, y + 18), text, F["small"], width=58, leading=29)
        y += 150
    d.text((1120, 280), "Survey snapshot", fill="#111827", font=F["h2"])
    survey = [("Safer", 61, "#0f766e"), ("Same", 24, "#64748b"), ("Worse", 9, "#dc2626"), ("No view", 6, "#94a3b8")]
    by = 390
    for label, value, color in survey:
        d.text((1125, by), label, fill="#111827", font=F["tiny_bold"])
        d.rectangle((1210, by, 1210 + value * 4, by + 28), fill=color)
        d.text((1220 + value * 4, by), f"{value}%", fill="#111827", font=F["tiny"])
        by += 70
    draw_note(d, (1120, 760, 1515, 970), "Footnote", "Survey n=312, collected 2026-06-01 through 2026-06-09. Percentages are rounded and sum to 100.", "#1d4ed8")
    draw_section(d, 92, 1115, "Errata strip", w=1350)
    draw_text(d, (112, 1180), "Errata: the May newsletter said the lighting grant was $2.1M. The corrected grant amount is $1.8M. The $2.1M value is historical errata, not current funding.", F["small"], fill="#7f1d1d", width=95, leading=30)
    response_rows = [
        ["Comment topic", "Response owner", "Promised follow-up", "Due"],
        ["Accessibility", "Terminal Ops", "extend tactile striping to ticket window", "2026-07-05"],
        ["Noise", "Engineering", "publish bearing-noise test memo", "2026-06-30"],
        ["Schedule", "Ferry Ops", "post 10:40 p.m. pilot notice", "2026-06-21"],
        ["Lighting", "City Energy", "separate grant explainer", "2026-07-10"],
    ]
    draw_ledger(d, 92, 1425, [250, 270, 560, 190], response_rows, 55)
    pages.append(p6)

    p7 = page("Appendix A - Inspection Table, Part 1")
    d = ImageDraw.Draw(p7)
    d.text((92, 178), "Table continues on the next page. Header repeats on page 8 for readability.", fill="#475569", font=F["small"])
    rows = [
        ["ID", "Location", "Element", "Condition", "Action", "Cost est.", "Note"],
        ["P-014", "Berth A", "pile coating", "fair", "recoat", "$42k", "counts in 31"],
        ["P-027", "Berth A", "jacket seam", "poor", "repair + coat", "$88k", "also in coating count"],
        ["P-063", "Berth B", "bearing shoe", "good", "monitor", "$0", "tested 05/14"],
        ["P-088", "Canopy bay 3", "panel clip", "poor", "CO-17", "$310k", "decision 07/18"],
        ["P-104", "Queue lane", "tactile strip", "fair", "extend", "$24k", "accessibility"],
    ]
    draw_ledger(d, 55, 265, [115, 190, 200, 150, 190, 140, 430], rows, 58)
    draw_text(d, (92, 740), "Carry-forward subtotal: five listed items, estimated $464k. CO-17 is pending and not yet committed. P-027 is counted once in the repair total even though it appears in both jacket and coating notes.", F["small"], width=90, leading=31)
    draw_note(d, (92, 1030, 1515, 1220), "Continuation note", "Appendix A is a single inspection table across pages 7 and 8. Page 8 repeats the header for readability.", "#92400e")
    pages.append(p7)

    p8 = page("Appendix A - Inspection Table, Part 2")
    d = ImageDraw.Draw(p8)
    d.text((92, 178), "Continued from Appendix A, Part 1.", fill="#475569", font=F["small"])
    rows = [
        ["ID", "Location", "Element", "Condition", "Action", "Cost est.", "Note"],
        ["P-131", "Berth C", "pile coating", "fair", "recoat", "$39k", "counts in 31"],
        ["P-152", "Berth C", "fender bracket", "good", "none", "$0", "photo only"],
        ["P-177", "Terminal roof", "drain leader", "poor", "replace", "$72k", "storm path"],
        ["P-201", "West ramp", "handrail", "fair", "tighten", "$8k", "before Sep"],
        ["P-214", "Berth D", "pile coating", "poor", "jacket + coat", "$96k", "also in five jacket repairs"],
    ]
    draw_ledger(d, 55, 265, [115, 190, 200, 150, 190, 140, 430], rows, 58)
    draw_section(d, 92, 755, "Appendix totals and notes", w=1260)
    total_rows = [
        ["Total rows", "10 inspection rows"],
        ["Rows requiring coating", "4 shown in appendix subset; 31 in full inspection log"],
        ["Rows requiring jacket repair", "2 shown in appendix subset; 5 in full inspection log"],
        ["Appendix cost subtotal", "$679k"],
        ["Pending CO-17 amount", "$310k included in subtotal but not yet committed"],
    ]
    draw_ledger(d, 110, 835, [430, 650], total_rows, 58)
    draw_text(d, (112, 1240), "Final note: Appendix A is a selected inspection excerpt, not the complete 214-pile inspection log. The report body value of 214 inspected piles and 31 coating actions remains the controlling full-program count.", F["small"], fill="#7f1d1d", width=92, leading=30)
    pages.append(p8)

    gold = """# Meridian Harbor Resilience Bond - Oversight Report

Prepared for the Bond Oversight Committee. Publication date 2026-06-18. Issue 04. Draft 4.2.

## Executive Brief

The pier retrofit remains inside the amended bond authorization, but it is not a clean green status. East gangway bearing replacement is complete, ferry canopy panels remain behind schedule, and the lighting grant sits outside bond contingency.

Inspection sketch 1: Workers test the east gangway on 14 May.

| Metric | Visible value | Note |
| --- | --- | --- |
| Bond authorization | $42.0M | not including lighting grant |
| Forecast at completion | $40.8M | $1.2M under bond cap |
| Uncommitted contingency | $2.4M | after pending CO-17 |
| Inspected piles | 214 | 31 require coating |
| Evening service extension | 10:40 p.m. | pilot through September |

Pull quote: "The last boat now leaves at 10:40 p.m."

Page order: cover, article, budget table, schedule graphic, map spread, community comments, appendix table part 1, appendix table part 2.

Open items:

| Open item | Owner | Next date | Visible status |
| --- | --- | --- | --- |
| CO-17 canopy panels | Port PMO | 2026-07-18 | pending decision |
| Pile coating change batch | HarborWorks | 2026-07-02 | pricing review |
| Lighting controls scope | City Energy | 2026-07-10 | grant-funded only |
| Evening marshal staffing | Ferry Ops | 2026-06-28 | pilot roster open |

Committee handling note: none of the four open items authorizes drawing from the bond contingency without a separate change-order vote.

## Feature Article - The North Pier Reopens

Maya Chen | Harbor Monthly | June 2026.

Deck: A repaired ferry terminal returns with quieter ramps and longer evening service.

The article says the North Pier reopened after eighteen months of construction fencing with a quieter ramp drive, wider queuing lanes, and a late-evening ferry pilot. The work is a resilience repair, not a new terminal. The east gangway bearing assembly was replaced in May after field tests showed uneven movement under full passenger load.

The corrected operating memo extends the last outbound boat to 10:40 p.m. on Fridays and Saturdays through September. Earlier drafts showed 10:15 p.m.; that value is superseded. Accessibility work includes six new wheelchair spaces, tactile warning strips, and a temporary ramp marshal during peak evening departures.

Inspection log FT-0514 excerpt: East gangway bearing assembly, field test 14 May. It records full passenger load, uneven bearing movement, bearing shoe reset and fit-up, photo reference IMG_0514-EB attached to field log, and the caption "Crew fits the bearing shoe under the east gangway, 14 May."

Pull quote: "The last boat now leaves at 10:40 p.m." It appears separately from the article body.

Sidebar - By the numbers:

| Metric | Value |
| --- | ---: |
| Repair budget | $18.6M |
| Piles inspected | 214 |
| Boarding-noise reduction | 32% |
| New wheelchair spaces | 6 |

Funding sidebar note: the lighting grant is mentioned in the sidebar but is not part of the bond authorization calculation.

Service change detail:

| Service change | Before | Current | Scope |
| --- | --- | --- | --- |
| Fri/Sat last boat | 10:15 p.m. | 10:40 p.m. | pilot through Sep. |
| Ramp marshal | none | peak evenings | temporary |
| Wheelchair spaces | 2 | 6 | terminal queue |
| Noise complaints | baseline | 32% lower | boarding ramp |

Article source notes:

| Source note | Checked item | Article treatment |
| --- | --- | --- |
| Operating memo OP-26-17 | Fri/Sat last outbound corrected to 10:40 p.m. | supersedes 10:15 draft |
| Field test log FT-0514 | east gangway bearing test under passenger load | supports inspection-log caption |
| Access punch list AC-0620 | six wheelchair queue spaces installed | matches sidebar metric |
| Noise test NT-0604 | boarding-noise reduction 32% | matches service table |

## Budget Review - Borderless Sources and Uses

Amounts are USD millions. Parentheses are unfavorable variances or credits. Superscript notes apply only to the row where shown.

| Category | Approved | Committed | Forecast | Variance | Footnote |
| --- | ---: | ---: | ---: | ---: | --- |
| Sources | | | | | |
| 2019 resilience bond | 42.0 | 40.1 | 40.8 | 1.2 | 1 |
| State pier safety grant | 5.5 | 5.5 | 5.5 | - | restricted |
| Lighting modernization grant | 1.8 | 0.6 | 1.8 | - | 2 |
| Uses | | | | | |
| East gangway bearings | 7.4 | 7.1 | 7.3 | 0.1 | |
| Pile coating and jackets | 11.2 | 9.6 | 10.9 | 0.3 | 3 |
| Canopy replacement | 8.6 | 7.9 | 9.4 | (0.8) | CO-17 pending |
| Terminal accessibility | 3.8 | 3.4 | 3.7 | 0.1 | |
| Program management | 4.2 | 3.9 | 4.1 | 0.1 | |
| Uncommitted contingency | 6.8 | 6.4 | 2.4 | (4.4) | after CO-17 |

Footnotes: 1. Bond authorization excludes the $1.8M lighting modernization grant. 2. Lighting grant may pay fixtures and controls only and is outside bond contingency. 3. Thirty-one inspected piles require additional coating; five also require jacket repair.

Variance strip values: Bearing +0.1, Piles +0.3, Canopy -0.8, Access +0.1, Management +0.1, Contingency -4.4.

Reconciliation points:

| Reconciliation point | Committee treatment |
| --- | --- |
| Forecast $40.8M vs bond cap $42.0M | $1.2M under cap before non-bond grants |
| Lighting grant $1.8M | separate restricted source, not contingency |
| Canopy CO-17 | shown in forecast but pending commitment |
| Contingency $2.4M | after pending CO-17, not after lighting grant |

## Construction Schedule Graphic

Schedule bars span April through September. Labels outside bars belong to the nearest connector line.

| Workstream | Span / state | Note |
| --- | --- | --- |
| East gangway bearings | mid-April to late May | complete 05/22 |
| Pile coating | late April to late July | 31 piles remain |
| Canopy panels | May to late August | slipped after CO-17 |
| Accessibility striping | June to early July | complete 07/03 |
| Evening service pilot | July to September | through September |
| Lighting grant scope | July to September | separate funding |

CO-17 decision gate is 2026-07-18. Canopy panels are the only red slipped workstream. Lighting grant scope overlaps the bond schedule but is separately funded.

Lookahead:

| Date | Milestone | Dependency | If missed |
| --- | --- | --- | --- |
| 2026-06-28 | Evening marshal roster | Ferry Ops staffing | pilot starts with reduced signage |
| 2026-07-02 | Pile coating price lock | HarborWorks quote | use allowance only |
| 2026-07-18 | CO-17 panel decision | committee vote | red canopy bar extends into Sep. |
| 2026-08-15 | Lighting controller delivery | grant purchase order | no bond impact |

## Map Spread - Work Zones and Service Changes

The harbor work-zone map excerpt shows North Pier Terminal, a passenger flow arrow to the ferry approach, harbor water, shoreline/coordinate grid context, a north arrow, a 50 m scale bar, and active work zones.

Callouts:

| Callout | Location / meaning |
| --- | --- |
| A | east gangway |
| B | canopy bay 3 |
| C | pile zone C |
| D | temporary dock |

Legend: active work zone, ferry approach, passenger flow arrow, harbor water. Callout B, canopy bay 3, is the only mapped item tied to CO-17. Callout D documents temporary dock access; evening-service pilot details are in the service section.

Caption: Public route shifts south of the terminal during canopy-panel removal.

Map constraints:

| Zone | Constraint | Planning note |
| --- | --- | --- |
| A east gangway | bearing work complete | closed; no active delay |
| B canopy bay 3 | CO-17 pending | ties to red schedule bar |
| C pile zone C | coating access by tide | ties to 31-pile count |
| D temporary dock | temporary access only | not evening-service pilot |

## Public Comment and Survey Page

Public comments:

| Topic | Excerpt |
| --- | --- |
| Accessibility | Ramp marshal was helpful, but tactile striping should continue to the ticket window. |
| Noise | The new bearings are noticeably quieter during evening boarding. |
| Schedule | The 10:40 p.m. Friday boat makes the return commute workable. |
| Lighting | Please keep the lighting work visible as a separate grant item. |

Survey snapshot: Safer 61%, Same 24%, Worse 9%, No view 6%. Footnote: survey n=312, collected 2026-06-01 through 2026-06-09. Percentages are rounded and sum to 100.

Errata: the May newsletter said the lighting grant was $2.1M. The corrected grant amount is $1.8M. The $2.1M value is historical errata, not current funding.

Response commitments:

| Comment topic | Response owner | Promised follow-up | Due |
| --- | --- | --- | --- |
| Accessibility | Terminal Ops | extend tactile striping to ticket window | 2026-07-05 |
| Noise | Engineering | publish bearing-noise test memo | 2026-06-30 |
| Schedule | Ferry Ops | post 10:40 p.m. pilot notice | 2026-06-21 |
| Lighting | City Energy | separate grant explainer | 2026-07-10 |

## Appendix A - Inspection Table

Appendix A is one logical continuation table across pages 7 and 8. The header repeats on page 8 for readability.

| ID | Location | Element | Condition | Action | Cost est. | Note |
| --- | --- | --- | --- | --- | ---: | --- |
| P-014 | Berth A | pile coating | fair | recoat | $42k | counts in 31 |
| P-027 | Berth A | jacket seam | poor | repair + coat | $88k | also in coating count |
| P-063 | Berth B | bearing shoe | good | monitor | $0 | tested 05/14 |
| P-088 | Canopy bay 3 | panel clip | poor | CO-17 | $310k | decision 07/18 |
| P-104 | Queue lane | tactile strip | fair | extend | $24k | accessibility |
| P-131 | Berth C | pile coating | fair | recoat | $39k | counts in 31 |
| P-152 | Berth C | fender bracket | good | none | $0 | photo only |
| P-177 | Terminal roof | drain leader | poor | replace | $72k | storm path |
| P-201 | West ramp | handrail | fair | tighten | $8k | before Sep |
| P-214 | Berth D | pile coating | poor | jacket + coat | $96k | also in five jacket repairs |

Carry-forward subtotal on part 1 is five listed items, estimated $464k. Appendix totals: 10 inspection rows; 4 coating rows shown in appendix subset while 31 are in the full inspection log; 2 jacket repair rows shown while 5 are in the full inspection log; appendix cost subtotal $679k; pending CO-17 amount $310k is included in subtotal but not yet committed.

Final note: Appendix A is a selected inspection excerpt, not the complete 214-pile inspection log. The report body value of 214 inspected piles and 31 coating actions remains the controlling full-program count.
"""

    facts = [
        fact("p14.identity.order", "structure", 7, "Report identity and page order are preserved: cover, article, budget, schedule, map, public comments, appendix part 1, appendix part 2.", modality="layout", severity="critical"),
        fact("p14.executive.metrics", "table_cell", 10, "Executive metric sidebar preserves bond authorization $42.0M excluding lighting grant, forecast $40.8M, contingency $2.4M, 214 inspected piles/31 coating, evening service 10:40 p.m.", modality="table", severity="critical"),
        fact("p14.open.items", "table_cell", 9, "Cover open-items table preserves CO-17/Port PMO/2026-07-18/pending decision, pile coating/HarborWorks/2026-07-02/pricing review, lighting controls/City Energy/2026-07-10/grant-funded only, and evening marshal/Ferry Ops/2026-06-28/pilot roster open.", modality="table", severity="critical"),
        fact("p14.figure.caption", "caption_binding", 7, "Inspection sketch/inspection-log caption is attached to workers testing/fitting the east gangway on 14 May and not to the budget table.", modality="layout", severity="major"),
        fact("p14.article.deck.byline", "reading_order", 7, "Article preserves title, byline Maya Chen | Harbor Monthly | June 2026, and deck about repaired ferry terminal returning with quieter ramps and longer evening service.", modality="layout", severity="major"),
        fact("p14.article.superseded.time", "source_state", 9, "Correct last outbound boat is 10:40 p.m. Fridays/Saturdays through September; earlier 10:15 p.m. draft is superseded.", modality="source-precedence", severity="critical"),
        fact("p14.pullquote.sidebar", "layout", 8, "Pull quote 'The last boat now leaves at 10:40 p.m.' is preserved once as a pull quote, and By the numbers sidebar preserves $18.6M, 214, 32%, and 6.", modality="layout", severity="major"),
        fact("p14.service.change", "table_cell", 9, "Service-change table preserves Fri/Sat last boat 10:15 p.m. to 10:40 p.m., ramp marshal none to peak evenings, wheelchair spaces 2 to 6, and noise complaints baseline to 32% lower.", modality="table", severity="critical"),
        fact("p14.article.source.notes", "table_cell", 8, "Article source notes preserve OP-26-17 correcting Fri/Sat last outbound to 10:40 p.m. and superseding the 10:15 draft, FT-0514 supporting the east gangway inspection-log caption, AC-0620 matching six wheelchair spaces, and NT-0604 matching 32% boarding-noise reduction.", modality="table", severity="major"),
        fact("p14.budget.table", "table_cell", 14, "Budget table preserves all source/use rows, approved/committed/forecast/variance values, parenthetical negative variances for canopy (0.8) and contingency (4.4), and row-group labels Sources/Uses.", modality="table", severity="critical"),
        fact("p14.budget.footnotes", "source_state", 10, "Footnotes preserve that bond authorization excludes the $1.8M lighting grant, lighting grant is not bond contingency, and 31 piles need coating while five need jacket repair.", modality="source-precedence", severity="critical"),
        fact("p14.variance.strip", "chart", 7, "Variance strip values are Bearing +0.1, Piles +0.3, Canopy -0.8, Access +0.1, Management +0.1, Contingency -4.4.", modality="chart", severity="major"),
        fact("p14.reconciliation", "source_state", 10, "Budget reconciliation preserves forecast $40.8M vs $42.0M cap as $1.2M under cap before non-bond grants, lighting grant $1.8M as restricted/not contingency, CO-17 pending commitment, and $2.4M contingency after pending CO-17 not after lighting grant.", modality="source-precedence", severity="critical"),
        fact("p14.schedule", "visual_relation", 11, "Schedule graphic preserves all six workstreams, their approximate Apr-Sep spans, notes, CO-17 gate 2026-07-18, and that canopy panels are the only red slipped workstream.", modality="chart", severity="critical"),
        fact("p14.lookahead", "table_cell", 9, "Schedule lookahead preserves milestones and due dates: 2026-06-28 evening marshal roster, 2026-07-02 pile coating price lock, 2026-07-18 CO-17 panel decision, 2026-08-15 lighting controller delivery, with dependencies and if-missed outcomes.", modality="table", severity="critical"),
        fact("p14.map.callouts", "visual_relation", 10, "Map preserves callouts A east gangway, B canopy bay 3, C pile zone C, D temporary dock, legend meanings, passenger flow arrow, north arrow, scale bar, and shoreline/coordinate-grid context.", modality="diagram", severity="critical"),
        fact("p14.map.co17", "source_state", 7, "Map note says only callout B/canopy bay 3 is tied to CO-17, and callout D temporary dock is not the evening-service pilot.", modality="source-precedence", severity="major"),
        fact("p14.map.constraints", "table_cell", 8, "Map constraints preserve A bearing work complete/closed with no active delay, B CO-17 pending/ties to red schedule bar, C coating access by tide/ties to 31-pile count, and D temporary access only/not evening-service pilot.", modality="table", severity="major"),
        fact("p14.comments.survey", "table_cell", 10, "Public comment excerpts preserve the four topics and survey snapshot Safer 61%, Same 24%, Worse 9%, No view 6%, n=312 and collection dates 2026-06-01 to 2026-06-09.", modality="table", severity="critical"),
        fact("p14.errata", "source_state", 8, "Errata preserves May newsletter $2.1M as stale/errata only and corrected lighting grant amount $1.8M as current.", modality="source-precedence", severity="critical"),
        fact("p14.response.commitments", "table_cell", 9, "Response commitments preserve Accessibility/Terminal Ops/tactile striping/2026-07-05, Noise/Engineering/bearing-noise memo/2026-06-30, Schedule/Ferry Ops/10:40 p.m. pilot notice/2026-06-21, Lighting/City Energy/grant explainer/2026-07-10.", modality="table", severity="critical"),
        fact("p14.appendix.continuation", "structure", 10, "Appendix A is one logical continuation table across pages 7 and 8; the page 8 repeated header is a readability header rather than an inspection row.", modality="layout", severity="critical"),
        fact("p14.appendix.rows", "table_cell", 16, "Appendix table preserves all ten inspection rows P-014, P-027, P-063, P-088, P-104, P-131, P-152, P-177, P-201, P-214 with locations, elements, conditions, actions, costs, and notes.", modality="table", severity="critical"),
        fact("p14.appendix.totals", "source_state", 10, "Appendix totals preserve carry-forward $464k, 10 rows, 4 coating rows in subset vs 31 full-log coating actions, 2 jacket rows in subset vs 5 full-log jacket repairs, subtotal $679k, and CO-17 $310k included but not committed.", modality="source-precedence", severity="critical"),
    ]

    return Case(
        "P14-publication-report-layout",
        "Publication Report Layout Packet",
        "publication-layout",
        ["multi-page", "publication", "multi-column", "captions", "sidebars", "pull-quotes", "maps", "continuation", "source-precedence"],
        "Stress non-Manhattan publication/report reconstruction with sidebars, pull quotes, captions, borderless financial tables, schedule graphics, map callouts, public comments, errata, and continuation appendix tables.",
        "Eight-page editorial oversight report with article layout, sidebars, field-sketch captions, charts, map spread, comments, and a two-page continuation table.",
        ["executive brief", "feature article", "budget table", "schedule graphic", "map spread", "public comments", "appendix continuation"],
        ["Preserve reading order, captions, sidebars, and pull quotes.", "Bind borderless table rows/columns and footnotes.", "Merge appendix continuation without duplicating headers."],
        gold,
        [
            near_check("p14-pullquote", "layout", ["Pull quote", "10:40 p.m.", "By the numbers"], 5, 900),
            near_check("p14-budget", "table_cell", ["Canopy replacement", "9.4", "(0.8)", "CO-17 pending"], 6, 900),
            near_check("p14-appendix", "structure", ["P-014", "P-214", "$679k", "repeated headers"], 6, 1200),
        ],
        pages,
        facts=facts,
    )


def packet_bank_fraud_investigation() -> Case:
    def page(title: str, subtitle: str = "Sable Bank | Retail Fraud Operations | Case packet SB-FR-4472") -> Image.Image:
        img = Image.new("RGB", (PAGE_W, PAGE_H), "#fffefa")
        d = ImageDraw.Draw(img)
        d.text((76, 52), subtitle, fill="#475569", font=F["tiny_bold"])
        d.text((76, 88), title, fill="#111827", font=F["h1"])
        d.line((76, 148, 1585, 148), fill="#111827", width=2)
        d.text((1420, 54), "CONFIDENTIAL", fill="#7f1d1d", font=F["tiny_bold"])
        return img

    statement_rows = [
        ["06-02", "Payroll deposit - Northstar Clinics", "ACH credit", "+3,842.18", "4,126.44", "posted"],
        ["06-03", "Check 1184 - Harbor Dental", "paper check", "-286.40", "3,840.04", "cleared"],
        ["06-05", "Maple Fuel 0448", "card present", "-64.18", "3,775.86", "valid"],
        ["06-07", "ZENITH ELECTRONICS 8921", "card-not-present", "-918.77", "2,857.09", "disputed"],
        ["06-08", "AURORA TRAVEL HOLDINGS", "card-not-present", "-1,246.05", "1,611.04", "disputed"],
        ["06-10", "ATM WDL 77 MISSION", "ATM", "-403.50", "1,207.54", "disputed"],
        ["06-12", "ACH WEB PAY KITELOAN", "ACH debit", "-702.14", "505.40", "disputed"],
        ["06-13", "Mobile deposit check 9910", "remote deposit", "+1,400.00", "1,905.40", "hold"],
        ["06-15", "RIDESHARE 6G8Q", "card-not-present", "-188.22", "1,717.18", "disputed"],
        ["06-16", "Provisional credit dispute 4472", "adjustment", "+2,650.12", "4,367.30", "provisional"],
        ["06-20", "ACH return KITELOAN", "ACH return", "+702.14", "5,069.44", "final credit"],
        ["06-24", "Provisional credit reversal partial", "adjustment", "-188.22", "4,881.22", "merchant evidence"],
    ]
    call_rows = [
        ["06-10 08:12", "Ana called IVR", "reported card-not-present charges", "case opened"],
        ["06-10 08:19", "Agent Malik", "card blocked, token wallet suspended", "completed"],
        ["06-10 09:44", "Fraud queue", "ATM video requested for Mission St", "pending"],
        ["06-11 14:20", "Ana callback", "confirmed no travel booking", "supports dispute"],
        ["06-13 10:05", "Back office", "KITELOAN ACH authorization missing", "return filed"],
        ["06-18 16:40", "Merchant response", "rideshare device matched Ana phone", "claim narrowed"],
        ["06-21 11:16", "Supervisor S. Iyer", "partial final credit authorized", "final prep"],
    ]
    dispute_rows = [
        ["Item", "Amount", "Claim state", "Final treatment"],
        ["Zenith Electronics 8921", "$918.77", "unauthorized", "credit final"],
        ["Aurora Travel Holdings", "$1,246.05", "unauthorized", "credit final"],
        ["ATM 77 Mission", "$403.50", "PIN liability review", "credit final"],
        ["KITELOAN ACH", "$702.14", "authorization missing", "ACH return final"],
        ["Rideshare 6G8Q", "$188.22", "device match", "customer liable"],
    ]
    evidence_rows = [
        ["Evidence", "Visible detail", "Controls"],
        ["Wallet token T-884", "created 06-07 01:18 from Android build A13", "not Ana device"],
        ["ATM camera still", "hooded subject, Mission St, 06-10 02:04", "supports ATM dispute"],
        ["Merchant response MR-6G8Q", "device hash matches Ana phone", "rideshare denied"],
        ["ACH return R10", "KITELOAN authorization not provided", "final ACH credit"],
        ["Provisional ledger", "$2,650.12 credit then $188.22 reversal", "final net credit $2,461.90"],
    ]
    ach_rows = [
        ["ACH item", "$702.14", "WEB PAY KITELOAN", "06-12"],
        ["Return code", "R10", "customer advises not authorized", "06-14"],
        ["Originator evidence", "not provided", "missing web authorization", "06-15"],
        ["Final state", "credit final", "$702.14", "06-20"],
    ]
    merchant_rows = [
        ["Merchant", "Amount", "Evidence", "Decision"],
        ["Zenith Electronics", "$918.77", "token T-884 / no shipment match", "credit final"],
        ["Aurora Travel", "$1,246.05", "token T-884 / no itinerary match", "credit final"],
        ["Rideshare 6G8Q", "$188.22", "device PH-A7C9 matched", "customer liable"],
    ]
    provisional_rows = [
        ["Date", "Entry", "Debit", "Credit", "Balance effect"],
        ["06-16", "provisional card credit", "", "$2,650.12", "+2,650.12"],
        ["06-20", "ACH return final", "", "$702.14", "+702.14"],
        ["06-24", "rideshare reversal", "$188.22", "", "-188.22"],
        ["06-24", "final net credit memo", "", "$2,461.90", "disclosure amount"],
    ]
    closeout_rows = [
        ["Item", "Final decision", "Customer liability"],
        ["Zenith", "credit final", "$0.00"],
        ["Aurora", "credit final", "$0.00"],
        ["ATM", "credit final", "$0.00"],
        ["KITELOAN ACH", "return final", "$0.00"],
        ["Rideshare", "denied", "$188.22"],
    ]

    pages: list[Image.Image] = []
    p1 = page("Retail Fraud Claim Binder - Case Overview")
    d = ImageDraw.Draw(p1)
    draw_kv_band(d, 80, 205, [("Customer", "Ana Patel"), ("Account", "****4472"), ("Case", "SB-FR-4472"), ("Opened", "2026-06-10"), ("Final", "2026-06-24")], [260, 220, 240, 220, 220])
    draw_note(d, (90, 370, 1500, 525), "Case handling note", "The final customer liability is not the original disputed amount and not the first provisional credit. The controlling final state is the 2026-06-24 supervisor closeout: four items credited, rideshare denied, final net credit $2,461.90.", "#7f1d1d")
    index_rows = [["Page", "Artifact", "Why it matters"]] + [[str(i), title, note] for i, (title, note) in enumerate([
        ("Overview", "final state and source hierarchy"),
        ("Statement part 1", "posted balance trail"),
        ("Statement part 2", "provisional credit and reversal"),
        ("Dispute intake", "checkboxes and customer statements"),
        ("Call log", "chronology and agent state"),
        ("Card/token evidence", "visual token/device conflict"),
        ("ATM evidence", "image description and camera timestamp"),
        ("ACH return", "return code and final credit"),
        ("Merchant responses", "accepted vs denied claims"),
        ("Provisional ledger", "credits, reversals, and net math"),
        ("Supervisor closeout", "final liability"),
        ("Appendix A", "descriptor mapping"),
        ("Appendix B", "balance reconciliation"),
        ("Appendix C", "deadline calendar"),
        ("Appendix D", "customer notification"),
        ("Final cover", "one-page final recap"),
    ], start=1)]
    draw_ledger(d, 92, 610, [100, 360, 720], index_rows, 44)
    pages.append(p1)

    for page_no, chunk in [(2, statement_rows[:8]), (3, statement_rows[8:])]:
        p = page(f"Checking Statement Extract - Part {page_no - 1}")
        d = ImageDraw.Draw(p)
        d.text((92, 178), "Statement period 2026-06-01 through 2026-06-30. Running balance is visible and must stay attached to each row.", fill="#475569", font=F["small"])
        draw_ledger(d, 80, 255, [130, 430, 230, 170, 170, 220], [["Date", "Description", "Channel", "Amount", "Balance", "Status"]] + chunk, 56)
        if page_no == 3:
            draw_note(d, (95, 965, 1500, 1130), "Statement footnote", "The $188.22 rideshare item remains customer liability after device-hash match. The June 24 reversal is not a bank error; it reverses only that merchant-supported item.", "#92400e")
            draw_ledger(d, 115, 1240, [260, 260, 280, 280], [["Balance bridge", "Amount", "Source", "State"], ["Original disputed total", "$3,458.68", "intake form", "historical"], ["Provisional credit", "$2,650.12", "06-16 adjustment", "temporary"], ["ACH final return", "$702.14", "R10 return", "final"], ["Rideshare reversal", "($188.22)", "merchant response", "final"], ["Final net credit", "$2,461.90", "closeout", "controls"]], 52)
        pages.append(p)

    p4 = page("Customer Dispute Intake Form")
    d = ImageDraw.Draw(p4)
    draw_kv_band(d, 90, 210, [("Form", "F-93A"), ("Signed", "2026-06-10"), ("Channel", "mobile upload"), ("Language", "English")], [250, 250, 300, 230])
    checkbox(d, 120, 380, "Card-not-present transactions unauthorized", True, F["small"])
    checkbox(d, 120, 440, "ATM withdrawal authorized by customer", False, F["small"])
    checkbox(d, 120, 500, "ACH debit authorization provided", False, F["small"])
    checkbox(d, 120, 560, "Customer traveled during disputed dates", False, F["small"])
    checkbox(d, 120, 620, "Customer recognizes rideshare merchant", True, F["small"])
    draw_text(d, (760, 380), "Blue correction note changes total disputed amount from $3,646.90 to $3,458.68 because the duplicate rideshare hold was removed before submission.", F["small"], width=45, leading=30)
    draw_ledger(d, 110, 820, [310, 220, 260, 390], [["Field", "Typed value", "Visible correction", "Final meaning"], ["Total disputed", "$3,646.90", "$3,458.68", "duplicate hold removed"], ["Card status", "active", "blocked 06-10 08:19", "card closed"], ["Contact number", "415-555-0198", "415-555-0178", "blue correction"], ["Police report", "pending", "not filed", "not required"]], 56)
    pages.append(p4)

    p5 = page("Call Center and Back-Office Log")
    d = ImageDraw.Draw(p5)
    draw_ledger(d, 80, 220, [170, 260, 520, 280], [["Timestamp", "Owner", "Visible note", "State"]] + call_rows, 58)
    draw_note(d, (90, 760, 1510, 935), "Chronology note", "The call log is not final liability. It explains why the claim narrows after merchant evidence arrives on 06-18 and why supervisor closeout on 06-24 controls.", "#334155")
    escalation_rows = [["Queue", "SLA", "Entered", "Exited", "Result"], ["Card fraud", "10 days", "06-10 08:19", "06-21 11:16", "partial closeout"], ["ATM review", "15 days", "06-10 09:44", "06-20 15:52", "credit approved"], ["ACH ops", "2 days", "06-13 10:05", "06-14 09:30", "R10 filed"], ["Merchant evidence", "merchant clock", "06-15 18:22", "06-18 16:40", "rideshare denied"]]
    draw_ledger(d, 105, 1075, [230, 180, 220, 220, 340], escalation_rows, 54)
    pages.append(p5)

    p6 = page("Card Token and Device Evidence")
    d = ImageDraw.Draw(p6)
    token_rows = [["Token", "Created", "Device / IP", "Merchant use", "Finding"], ["T-884", "06-07 01:18", "Android A13 / 91.44.18.22", "Zenith, Aurora", "not Ana device"], ["T-221", "05-01 12:44", "Ana iPhone / 172.18.4.9", "Rideshare", "matches customer"], ["Card plastic", "2025-11-19", "chip present", "Maple Fuel", "valid"]]
    draw_ledger(d, 80, 235, [170, 180, 330, 260, 260], token_rows, 60)
    d.rounded_rectangle((120, 620, 720, 1060), radius=8, fill="#f8fafc", outline="#334155", width=2)
    d.text((150, 650), "Wallet token screenshot", fill="#111827", font=F["small_bold"])
    draw_text(d, (150, 705), "T-884\nDevice: Android A13\nCreated: 2026-06-07 01:18\nIP: 91.44.18.22\nUsed: Zenith / Aurora", F["small"], width=35, leading=34)
    d.rounded_rectangle((830, 620, 1430, 1060), radius=8, fill="#f8fafc", outline="#334155", width=2)
    d.text((860, 650), "Customer device record", fill="#111827", font=F["small_bold"])
    draw_text(d, (860, 705), "Ana iPhone\nDevice hash: PH-A7C9\nUsed: Rideshare 6G8Q\nLast verified: 2026-06-18\nFinding: customer liable", F["small"], width=35, leading=34)
    auth_rows = [
        ["Event", "Token/device", "Amount", "Auth result", "Fraud note"],
        ["Zenith auth", "T-884 / Android A13", "$918.77", "approved", "new token"],
        ["Aurora auth", "T-884 / Android A13", "$1,246.05", "approved", "travel mismatch"],
        ["Rideshare auth", "T-221 / PH-A7C9", "$188.22", "approved", "customer device"],
        ["Wallet suspension", "T-884", "-", "closed", "06-10 08:19"],
    ]
    draw_ledger(d, 105, 1195, [260, 280, 150, 190, 320], auth_rows, 52)
    pages.append(p6)

    p7 = page("ATM Evidence Sheet")
    d = ImageDraw.Draw(p7)
    d.rounded_rectangle((110, 235, 930, 935), radius=8, fill="#f8fafc", outline="#334155", width=3)
    d.text((140, 265), "Camera export contact sheet - privacy redacted", fill="#111827", font=F["small_bold"])
    d.text((140, 302), "ATM 77 MISSION | CAM 02 | 2026-06-10 | Export batch VID-77M-0610", fill="#475569", font=F["tiny_bold"])
    thumbs = [
        ("18491", "02:03:58", "subject enters vestibule", "face occluded"),
        ("18492", "02:04:31", "withdrawal at terminal", "$403.50 / magstripe fallback"),
        ("18493", "02:05:06", "subject exits south", "no companion visible"),
    ]
    tx = 145
    for frame, ts, cue, note in thumbs:
        d.rectangle((tx, 365, tx + 220, 540), fill="#111827", outline="#64748b", width=2)
        d.rectangle((tx + 18, 386, tx + 202, 515), fill="#374151")
        d.line((tx + 35, 410, tx + 185, 492), fill="#4b5563", width=4)
        d.rectangle((tx + 54, 432, tx + 166, 472), fill="#0f172a")
        d.text((tx + 16, 548), f"Frame {frame} | {ts}", fill="#111827", font=F["tiny_bold"])
        draw_text(d, (tx + 16, 580), f"{cue}\n{note}", F["tiny"], width=24, leading=22)
        tx += 255
    d.rounded_rectangle((145, 705, 885, 885), radius=6, fill="#fff7ed", outline="#c2410c", width=2)
    draw_text(d, (170, 735), "Redaction log: visual stills are privacy masked in the customer packet. Metadata remains visible. Reviewer note says the hooded subject's face is not visible; frame 18492 is the transaction frame for $403.50.", F["small"], fill="#7c2d12", width=64, leading=30)
    draw_ledger(d, 1000, 260, [210, 300], [["Field", "Visible value"], ["ATM ID", "77 MISSION"], ["Withdrawal", "$403.50"], ["Card read", "magstripe fallback"], ["PIN", "accepted"], ["Camera note", "hooded subject, face not visible"], ["Decision", "credit final after supervisor review"]], 58)
    draw_note(d, (1000, 775, 1510, 980), "ATM review note", "PIN acceptance does not control final liability because the camera still, token timeline, and customer call were reviewed together.", "#92400e")
    thumb_rows = [["Frame", "Visible cue", "Reviewer note"], ["18491", "subject enters vestibule", "face occluded"], ["18492", "withdrawal at terminal", "$403.50"], ["18493", "subject exits south", "no companion"]]
    draw_ledger(d, 115, 1060, [170, 390, 420], thumb_rows, 52)
    pages.append(p7)

    for title, rows, note in [
        ("ACH Return and KITELOAN Authorization Review", ach_rows, "R10 return is final and separate from the provisional card credit."),
        ("Merchant Response Packet", merchant_rows, "Rideshare is denied even though it was listed in the intake dispute."),
        ("Provisional Credit Ledger", provisional_rows, "The final net credit is $2,461.90, not $2,650.12 and not $3,458.68."),
        ("Supervisor Closeout", closeout_rows, "Supervisor S. Iyer signed 2026-06-24. Final customer liability is $188.22."),
    ]:
        p = page(title)
        d = ImageDraw.Draw(p)
        draw_ledger(d, 90, 245, [240, 230, 420, 260], rows, 62)
        draw_note(d, (105, 780, 1510, 940), "Source-state note", note, "#7f1d1d")
        pages.append(p)

    descriptor_rows = [["Descriptor", "Normalized merchant", "Evidence page", "Final state"], ["ZENITH ELECTRONICS 8921", "Zenith Electronics", "merchant response", "credit final"], ["AURORA TRAVEL HOLDINGS", "Aurora Travel", "merchant response", "credit final"], ["ATM WDL 77 MISSION", "Sable ATM Mission", "ATM evidence", "credit final"], ["ACH WEB PAY KITELOAN", "KITELOAN", "ACH return", "credit final"], ["RIDESHARE 6G8Q", "Rideshare", "device evidence", "customer liable"]]
    balance_rows = [["Reconciliation line", "Amount", "State"], ["Original disputed intake", "$3,458.68", "historical"], ["Credited card/ATM items", "$2,568.32", "final"], ["ACH return", "$702.14", "final"], ["Rideshare denied", "($188.22)", "liability"], ["Final net credit disclosure", "$2,461.90", "controls"], ["Final customer liability", "$188.22", "controls"]]
    deadline_rows = [["Deadline", "Date", "Status", "Note"], ["Reg E provisional", "2026-06-20", "met", "credit posted 06-16"], ["ACH return window", "2026-06-14", "met", "R10 filed"], ["Merchant response", "2026-06-18", "received", "rideshare only"], ["Final notice", "2026-06-24", "sent", "controls customer liability"]]
    notice_rows = [["Notice field", "Visible value"], ["Notice date", "2026-06-24"], ["Final credited amount", "$2,461.90"], ["Customer liability", "$188.22"], ["Items credited", "Zenith, Aurora, ATM, KITELOAN"], ["Item denied", "Rideshare 6G8Q"], ["Appeal by", "2026-07-24"]]
    for title, rows in [("Appendix A - Descriptor Mapping", descriptor_rows), ("Appendix B - Balance Reconciliation", balance_rows), ("Appendix C - Deadline Calendar", deadline_rows), ("Customer Final Notice", notice_rows)]:
        p = page(title)
        d = ImageDraw.Draw(p)
        draw_ledger(d, 90, 245, [360, 310, 300, 280], rows, 60)
        pages.append(p)

    p16 = page("Final One-Page Recap")
    d = ImageDraw.Draw(p16)
    draw_text(d, (95, 230), "Final outcome: Case SB-FR-4472 is partially approved. Sable Bank credits Zenith Electronics $918.77, Aurora Travel $1,246.05, ATM 77 Mission $403.50, and KITELOAN ACH $702.14. Rideshare 6G8Q $188.22 remains customer liability because the merchant response matched Ana's device.", F["small"], width=92, leading=31)
    draw_ledger(d, 110, 470, [360, 240, 240, 420], [["Control value", "Amount", "Current?", "Why"], ["Original disputed total", "$3,458.68", "no", "historical intake"], ["Provisional credit", "$2,650.12", "no", "temporary card/ATM credit"], ["Final net credit", "$2,461.90", "yes", "after rideshare reversal"], ["Final liability", "$188.22", "yes", "rideshare denied"]], 58)
    pages.append(p16)

    gold_parts = [
        "# Sable Bank Retail Fraud Claim Binder SB-FR-4472",
        "Customer Ana Patel, account ****4472. Case opened 2026-06-10 and final closeout 2026-06-24. The controlling final state is partial approval: four items credited, rideshare denied, final net credit $2,461.90, final customer liability $188.22.",
        "\n## Packet Index\n" + md_table(["Page", "Artifact", "Why it matters"], index_rows[1:]),
        "\n## Statement Rows\n" + md_table(["Date", "Description", "Channel", "Amount", "Balance", "Status"], statement_rows),
        "\n## Statement Balance Bridge\n" + md_table(["Balance bridge", "Amount", "Source", "State"], [["Original disputed total", "$3,458.68", "intake form", "historical"], ["Provisional credit", "$2,650.12", "06-16 adjustment", "temporary"], ["ACH final return", "$702.14", "R10 return", "final"], ["Rideshare reversal", "($188.22)", "merchant response", "final"], ["Final net credit", "$2,461.90", "closeout", "controls"]]),
        "\n## Dispute Intake\nMedical-style checkbox states are not present; this is a bank form. Card-not-present unauthorized checked; ATM authorized unchecked; ACH authorization provided unchecked; customer traveled unchecked; customer recognizes rideshare checked. Total disputed typed $3,646.90 is corrected to $3,458.68. Card blocked 2026-06-10 08:19. Contact number corrected to 415-555-0178. Police report not filed and not required.",
        "\n## Dispute Intake Corrections\n" + md_table(["Field", "Typed value", "Visible correction", "Final meaning"], [["Total disputed", "$3,646.90", "$3,458.68", "duplicate hold removed"], ["Card status", "active", "blocked 06-10 08:19", "card closed"], ["Contact number", "415-555-0198", "415-555-0178", "blue correction"], ["Police report", "pending", "not filed", "not required"]]),
        "\n## Call Log\n" + md_table(["Timestamp", "Owner", "Visible note", "State"], call_rows),
        "\n## Escalation Queues\n" + md_table(["Queue", "SLA", "Entered", "Exited", "Result"], [["Card fraud", "10 days", "06-10 08:19", "06-21 11:16", "partial closeout"], ["ATM review", "15 days", "06-10 09:44", "06-20 15:52", "credit approved"], ["ACH ops", "2 days", "06-13 10:05", "06-14 09:30", "R10 filed"], ["Merchant evidence", "merchant clock", "06-15 18:22", "06-18 16:40", "rideshare denied"]]),
        "\n## Card Token Evidence\n" + md_table(["Token", "Created", "Device / IP", "Merchant use", "Finding"], token_rows[1:]) + "\n\nAuthorization events: Zenith auth used T-884 / Android A13 for $918.77 and was approved as a new token; Aurora auth used T-884 / Android A13 for $1,246.05 and was approved with travel mismatch; Rideshare auth used T-221 / PH-A7C9 for $188.22 and is the customer device; wallet suspension closed T-884 on 06-10 08:19.",
        "\n## ATM Evidence\nATM 77 MISSION camera 2 at 2026-06-10 02:04 frame 18492 is privacy-redacted in the customer packet. Metadata says the hooded subject's face is not visible. Withdrawal $403.50 used magstripe fallback and PIN accepted, but credit is final after supervisor review. Frame notes: 18491 subject enters vestibule with face occluded; 18492 withdrawal at terminal for $403.50; 18493 subject exits south with no companion.",
        "\n## Disputed Item Final Treatment\n" + md_table(["Item", "Amount", "Claim state", "Final treatment"], dispute_rows[1:]),
        "\n## Evidence Control\n" + md_table(["Evidence", "Visible detail", "Controls"], evidence_rows[1:]),
        "\n## ACH Return Review\n" + md_table(["Field", "Value", "Evidence", "Date"], ach_rows),
        "\n## Merchant Response Packet\n" + md_table(["Merchant", "Amount", "Evidence", "Decision"], merchant_rows[1:]),
        "\n## Provisional Credit Ledger\n" + md_table(["Date", "Entry", "Debit", "Credit", "Balance effect"], provisional_rows[1:]),
        "\n## Supervisor Closeout\n" + md_table(["Item", "Final decision", "Customer liability"], closeout_rows[1:]),
        "\n## Descriptor Mapping\n" + md_table(["Descriptor", "Normalized merchant", "Evidence page", "Final state"], descriptor_rows[1:]),
        "\n## Balance Reconciliation\n" + md_table(["Reconciliation line", "Amount", "State"], balance_rows[1:]),
        "\n## Deadline Calendar\n" + md_table(["Deadline", "Date", "Status", "Note"], deadline_rows[1:]),
        "\n## Customer Final Notice\n" + md_table(["Notice field", "Visible value"], notice_rows[1:]),
    ]
    gold = "\n\n".join(gold_parts)
    facts = [
        fact("p16.final.state", "source_state", 14, "Final controlling state is partial approval: Zenith $918.77, Aurora $1,246.05, ATM $403.50, and KITELOAN $702.14 credited; Rideshare 6G8Q $188.22 denied; final net credit $2,461.90; final customer liability $188.22.", modality="source-precedence", severity="critical"),
        fact("p16.packet.index", "structure", 6, "Packet index preserves all 16 page artifacts in order, including statement parts, dispute intake, call log, token evidence, ATM evidence, appendices, customer notice, and final cover.", modality="structure", severity="major"),
        fact("p16.statement.part1", "table_cell", 10, "Statement part 1 preserves the first eight rows from 06-02 payroll through 06-13 mobile deposit, with channel, amount, balance, and status bound to the correct date and description.", modality="table", severity="critical"),
        fact("p16.statement.part2", "table_cell", 10, "Statement part 2 preserves 06-15 rideshare -$188.22, 06-16 provisional +$2,650.12, 06-20 ACH return +$702.14, and 06-24 partial reversal -$188.22 with balances and statuses.", modality="table", severity="critical"),
        fact("p16.statement.bridge", "source_state", 9, "Statement bridge preserves historical original disputed total $3,458.68, temporary provisional credit $2,650.12, final ACH return $702.14, final rideshare reversal ($188.22), and final net credit $2,461.90 controls.", modality="source-precedence", severity="critical"),
        fact("p16.intake.checkboxes", "form_state", 10, "Intake checkbox states preserve card-not-present unauthorized checked, ATM authorized unchecked, ACH authorization unchecked, travel unchecked, and rideshare recognized checked.", modality="form", severity="critical"),
        fact("p16.intake.corrections", "source_state", 10, "Intake correction table preserves total disputed $3,646.90 corrected to $3,458.68, active card corrected to blocked 06-10 08:19, phone 415-555-0198 corrected to 415-555-0178, and police report pending corrected to not filed/not required.", modality="form", severity="critical"),
        fact("p16.call.log", "table_cell", 10, "Call log preserves all seven timestamps/owners/notes/states including merchant evidence on 06-18 narrowing the claim and supervisor closeout on 06-21/06-24.", modality="table", severity="major"),
        fact("p16.escalation.queues", "table_cell", 8, "Escalation queue table preserves card fraud, ATM review, ACH ops, and merchant evidence rows with SLA, entered/exited timestamps, and results.", modality="table", severity="major"),
        fact("p16.token.table", "table_cell", 8, "Token table preserves T-884 created 06-07 01:18 from Android A13/91.44.18.22 for Zenith/Aurora not Ana device; T-221 created 05-01 12:44 from Ana iPhone/172.18.4.9 for Rideshare matches customer; card plastic chip-present Maple Fuel valid.", modality="table", severity="critical"),
        fact("p16.token.binding", "visual_relation", 10, "Wallet-token screenshot and customer-device record preserve that T-884 is not Ana's device, while Ana iPhone device hash PH-A7C9 is tied to Rideshare 6G8Q and customer liability.", modality="visual", severity="critical"),
        fact("p16.auth.events", "table_cell", 9, "Authorization events preserve Zenith $918.77 on T-884/new token, Aurora $1,246.05 on T-884/travel mismatch, Rideshare $188.22 on T-221/PH-A7C9/customer device, and wallet suspension of T-884 at 06-10 08:19.", modality="table", severity="critical"),
        fact("p16.atm.evidence", "visual_description", 8, "ATM evidence preserves privacy-redacted contact sheet state, ATM 77 MISSION camera 2, 2026-06-10 02:04 frame 18492, $403.50, magstripe fallback, PIN accepted, hooded subject/face not visible from metadata, frame notes 18491/18492/18493, and final credit after supervisor review.", modality="visual", severity="major"),
        fact("p16.ach.return", "source_state", 9, "ACH review preserves item $702.14 WEB PAY KITELOAN on 06-12, return code R10/customer advises not authorized on 06-14, originator evidence not provided/missing web authorization on 06-15, and final credit $702.14 on 06-20.", modality="source-precedence", severity="critical"),
        fact("p16.merchant.responses", "source_state", 10, "Merchant response table preserves Zenith $918.77 and Aurora $1,246.05 credited from token T-884/no match, while Rideshare 6G8Q $188.22 is customer liable because device PH-A7C9 matched.", modality="source-precedence", severity="critical"),
        fact("p16.provisional.ledger", "table_cell", 10, "Provisional ledger preserves all four rows: 06-16 provisional card credit $2,650.12, 06-20 ACH return final $702.14, 06-24 rideshare reversal debit $188.22, and 06-24 final net credit memo $2,461.90.", modality="table", severity="critical"),
        fact("p16.closeout.table", "table_cell", 8, "Supervisor closeout preserves zero customer liability for Zenith, Aurora, ATM, and KITELOAN ACH, while Rideshare is denied with $188.22 customer liability.", modality="table", severity="critical"),
        fact("p16.descriptor.mapping", "table_cell", 8, "Descriptor mapping preserves all five descriptors, normalized merchants, evidence pages, and final states, including ACH WEB PAY KITELOAN to KITELOAN and RIDESHARE 6G8Q to customer liable.", modality="table", severity="major"),
        fact("p16.balance.reconciliation", "table_cell", 8, "Balance reconciliation preserves credited card/ATM items $2,568.32 final, ACH return $702.14 final, rideshare denied ($188.22) liability, final net credit $2,461.90 controls, and final customer liability $188.22 controls.", modality="table", severity="critical"),
        fact("p16.deadline.calendar", "table_cell", 7, "Deadline calendar preserves Reg E provisional 2026-06-20 met, ACH return 2026-06-14 met, merchant response 2026-06-18 received, and final notice 2026-06-24 sent.", modality="table", severity="major"),
        fact("p16.final.notice", "table_cell", 7, "Customer final notice preserves notice date 2026-06-24, final credited amount $2,461.90, customer liability $188.22, credited items Zenith/Aurora/ATM/KITELOAN, denied item Rideshare 6G8Q, and appeal by 2026-07-24.", modality="table", severity="critical"),
        fact("p16.no.stale.final", "source_state", 8, "Output must not treat the original disputed total $3,458.68 or provisional credit $2,650.12 as the final credit or final liability; they are historical/temporary values only.", modality="source-precedence", severity="critical"),
    ]
    return Case("P16-bank-fraud-investigation", "Bank Fraud Investigation Binder", "bank-fraud", ["multi-page", "banking", "statements", "forms", "source-precedence", "visual-evidence", "reconciliation"], "Stress long financial investigation reconstruction with source-state conflicts and dense ledgers.", "Sixteen-page retail fraud binder with statements, visual evidence, call logs, ACH returns, merchant responses, and final reconciliation.", ["statement rows", "forms", "source precedence", "visual evidence", "final reconciliation"], ["Preserve every row and final controlling state."], gold, [near_check("p16-final", "source_state", ["$2,461.90", "$188.22", "Rideshare"], 8, 900)], pages, facts=facts)


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    return "| " + " | ".join(headers) + " |\n| " + " | ".join("---" for _ in headers) + " |\n" + "\n".join("| " + " | ".join(row) + " |" for row in rows)


def packet_clinical_trial_site_binder() -> Case:
    def page(title: str, subtitle: str = "Helio Therapeutics | Protocol HTX-204 | Site 014 monitoring packet") -> Image.Image:
        img = Image.new("RGB", (PAGE_W, PAGE_H), "#ffffff")
        d = ImageDraw.Draw(img)
        d.text((76, 52), subtitle, fill="#475569", font=F["tiny_bold"])
        d.text((76, 88), title, fill="#111827", font=F["h1"])
        d.line((76, 148, 1585, 148), fill="#111827", width=2)
        d.text((1410, 54), "MONITOR COPY", fill="#1d4ed8", font=F["tiny_bold"])
        return img

    subjects = [
        ["014-001", "screen fail", "2026-04-03", "HbA1c 9.1%", "not randomized"],
        ["014-002", "randomized", "2026-04-05", "Arm B", "completed W4"],
        ["014-003", "randomized", "2026-04-07", "Arm A", "missed W2 ECG"],
        ["014-004", "withdrawn", "2026-04-10", "Arm B", "AE dizziness"],
        ["014-005", "randomized", "2026-04-12", "Arm A", "completed W4"],
        ["014-006", "screen fail", "2026-04-15", "eGFR 42", "not randomized"],
        ["014-007", "randomized", "2026-04-18", "Arm B", "IP temperature excursion"],
        ["014-008", "randomized", "2026-04-20", "Arm A", "central lab pending"],
        ["014-009", "randomized", "2026-04-22", "Arm B", "W2 diary window late"],
        ["014-010", "screen fail", "2026-04-23", "QTc 486 ms", "not randomized"],
        ["014-011", "randomized", "2026-04-26", "Arm A", "central lab repeat pending"],
        ["014-012", "randomized", "2026-04-28", "Arm B", "eligible with waiver W-14"],
        ["014-013", "withdrawn", "2026-04-29", "Arm A", "lost to follow-up before W4"],
        ["014-014", "randomized", "2026-05-01", "Arm A", "ePRO device not activated"],
        ["014-015", "screen fail", "2026-05-02", "BP 168/98", "not randomized"],
        ["014-016", "randomized", "2026-05-04", "Arm B", "unblinded pharmacist note"],
    ]
    visits = [
        ["014-002", "V1", "04-05", "done", "kit K-204-118", "ECG normal"],
        ["014-002", "W2", "04-19", "done", "kit K-204-142", "diary returned"],
        ["014-002", "W4", "05-03", "done", "kit K-204-166", "dose reduced"],
        ["014-003", "V1", "04-07", "done", "kit K-204-121", "ECG missing"],
        ["014-003", "W2", "04-21", "partial", "kit K-204-146", "ECG not done"],
        ["014-004", "V1", "04-10", "done", "kit K-204-128", "AE onset"],
        ["014-004", "W2", "04-24", "withdrawn", "-", "early termination"],
        ["014-007", "V1", "04-18", "done", "kit K-204-153", "temp excursion"],
        ["014-007", "W2", "05-02", "hold", "-", "repeat lab required"],
        ["014-008", "V1", "04-20", "done", "kit K-204-158", "central lab pending"],
        ["014-009", "V1", "04-22", "done", "kit K-204-160", "diary issued"],
        ["014-009", "W2", "05-07", "late", "kit K-204-181", "outside +2 day window"],
        ["014-011", "V1", "04-26", "done", "kit K-204-171", "lab repeat ordered"],
        ["014-012", "V1", "04-28", "done", "kit K-204-174", "waiver W-14 filed"],
        ["014-013", "V1", "04-29", "done", "kit K-204-177", "phone disconnected"],
        ["014-014", "V1", "05-01", "done", "kit K-204-184", "ePRO not activated"],
        ["014-016", "V1", "05-04", "done", "kit K-204-190", "pharmacist note sealed"],
    ]
    labs = [
        ["014-002", "ALT", "38", "", "0-45", "U/L"],
        ["014-002", "Creatinine", "1.11", "", "0.60-1.30", "mg/dL"],
        ["014-003", "ALT", "67", "H", "0-45", "U/L"],
        ["014-003", "eGFR", "58", "L", ">=60", "mL/min"],
        ["014-004", "Hemoglobin", "10.8", "L", "12.0-16.0", "g/dL"],
        ["014-007", "Potassium", "5.6", "H", "3.5-5.1", "mmol/L"],
        ["014-008", "HbA1c", "7.2", "", "6.5-9.0", "%"],
        ["014-009", "ALT", "49", "H", "0-45", "U/L"],
        ["014-009", "Potassium", "4.8", "", "3.5-5.1", "mmol/L"],
        ["014-011", "Creatinine", "1.34", "H", "0.60-1.30", "mg/dL"],
        ["014-011", "eGFR", "61", "", ">=60", "mL/min"],
        ["014-012", "QTc", "452", "", "<470", "ms"],
        ["014-013", "Hemoglobin", "11.7", "L", "12.0-16.0", "g/dL"],
        ["014-014", "ALT", "42", "", "0-45", "U/L"],
        ["014-016", "Glucose", "62", "L", "70-110", "mg/dL"],
    ]
    aes = [
        ["AE-014-01", "014-004", "dizziness", "moderate", "related", "withdrawn 2026-04-24"],
        ["AE-014-02", "014-002", "nausea", "mild", "possibly related", "dose reduced W4"],
        ["AE-014-03", "014-007", "hyperkalemia", "moderate", "unrelated", "repeat lab normal"],
        ["AE-014-04", "014-009", "headache", "mild", "unrelated", "resolved without action"],
        ["AE-014-05", "014-011", "creatinine increased", "mild", "possibly related", "repeat lab pending"],
        ["AE-014-06", "014-013", "lost contact", "not AE", "not related", "withdrawal follow-up open"],
        ["AE-014-07", "014-016", "hypoglycemia", "moderate", "related", "safety call completed"],
    ]
    deviations = [
        ["DEV-014-03", "014-003", "W2 ECG missed", "major", "open query Q-77"],
        ["DEV-014-07", "014-007", "IP temp 9.1C for 3h", "major", "do not dose kit K-204-153"],
        ["DEV-014-02", "014-002", "diary page late", "minor", "resolved"],
        ["DEV-014-08", "014-009", "W2 visit outside +2 day window", "minor", "open query Q-86"],
        ["DEV-014-09", "014-011", "repeat central lab not filed", "major", "open query Q-88"],
        ["DEV-014-10", "014-014", "ePRO device not activated at V1", "minor", "retrain coordinator"],
        ["DEV-014-11", "014-016", "unblinded pharmacist note in source", "major", "masking review open"],
    ]
    ip_rows = [
        ["Kit", "Subject", "Dispensed", "Returned", "Temp flag", "Final state"],
        ["K-204-118", "014-002", "30", "4", "none", "accounted"],
        ["K-204-142", "014-002", "30", "6", "none", "accounted"],
        ["K-204-166", "014-002", "15", "2", "none", "dose reduced"],
        ["K-204-121", "014-003", "30", "5", "none", "accounted"],
        ["K-204-146", "014-003", "30", "not returned", "none", "open"],
        ["K-204-153", "014-007", "0", "quarantined", "9.1C for 3h", "do not dose"],
        ["K-204-158", "014-008", "30", "pending", "none", "reconcile after lab"],
        ["K-204-160", "014-009", "30", "3", "none", "diary window late"],
        ["K-204-171", "014-011", "30", "pending", "none", "hold repeat lab"],
        ["K-204-184", "014-014", "30", "0", "none", "ePRO activation open"],
        ["K-204-190", "014-016", "30", "2", "none", "masking review"],
    ]
    temp_rows = [["Time", "Temp", "Action"], ["04-18 09:10", "8.4C", "alarm"], ["04-18 10:10", "9.1C", "quarantine K-204-153"], ["04-18 11:10", "8.8C", "pharmacy notified"], ["04-18 12:10", "7.8C", "still above range"], ["04-18 13:05", "5.2C", "returned to range"], ["04-18 13:40", "4.7C", "back in range; kit remains quarantined"]]
    ecg_rows = [["Field", "Visible state"], ["Subject", "014-003"], ["Visit", "W2 / 2026-04-21"], ["ECG checkbox", "unchecked"], ["Reason", "machine unavailable"], ["Query", "Q-77 open; PI response pending"]]
    med_rows = [["Subject", "Medication", "Start", "Stop", "Relevance"], ["014-002", "metformin", "baseline", "ongoing", "allowed"], ["014-004", "meclizine", "04-11", "04-24", "AE dizziness"], ["014-007", "potassium supplement", "04-01", "04-19", "hyperkalemia context"], ["014-009", "ibuprofen", "04-30", "05-01", "headache"], ["014-011", "lisinopril", "baseline", "ongoing", "renal context"], ["014-016", "glipizide", "baseline", "ongoing", "hypoglycemia context"]]
    query_rows = [["Query", "Subject", "Issue", "State"], ["Q-74", "014-004", "AE stop date", "answered"], ["Q-77", "014-003", "W2 ECG missing", "open"], ["Q-81", "014-007", "temperature excursion dosing", "answered: do not dose"], ["Q-84", "014-008", "central lab pending", "open"], ["Q-86", "014-009", "W2 visit outside window", "open"], ["Q-88", "014-011", "repeat lab report missing", "open"], ["Q-91", "014-014", "ePRO activation evidence", "answered: retrained"], ["Q-93", "014-016", "pharmacist masking note", "open"]]
    ecrf_rows = [["Subject", "Field", "Visible state", "Data entry"], ["014-003", "W2 ECG performed", "unchecked", "blank"], ["014-004", "Withdrawal due to AE", "checked", "dizziness"], ["014-007", "Kit dispensed", "unchecked", "quarantined"], ["014-008", "Central lab reviewed", "unchecked", "pending"], ["014-009", "Visit in window", "unchecked", "late"], ["014-011", "Repeat lab attached", "unchecked", "pending"], ["014-014", "ePRO activated", "unchecked", "training complete"], ["014-016", "Masking reviewed", "unchecked", "open"]]
    shipment_rows = [["Shipment", "Subject", "Tube", "Drawn", "Received", "State"], ["SH-204-44", "014-002", "PK-2", "04-19 08:12", "04-20 09:02", "accepted"], ["SH-204-45", "014-003", "PK-2", "04-21 08:44", "04-23 16:40", "temperature late"], ["SH-204-46", "014-008", "central lab", "04-20 09:15", "pending", "not reviewed"], ["SH-204-47", "014-009", "PK-2", "05-07 09:04", "05-08 11:20", "accepted late draw"], ["SH-204-48", "014-011", "chemistry", "04-26 08:52", "04-27 10:05", "repeat requested"], ["SH-204-49", "014-016", "glucose", "05-04 07:58", "05-05 09:44", "safety call done"]]
    readiness_rows = [["Domain", "Open", "Critical blocker"], ["Enrollment", "0", "none"], ["ECG", "1", "Q-77 / 014-003"], ["Drug accountability", "1", "K-204-153 quarantine"], ["Central lab", "3", "014-008, 014-011, 014-016"], ["AE", "1", "AE-014-05 repeat lab pending"], ["Visit windows", "1", "Q-86 / 014-009"], ["Masking", "1", "Q-93 / 014-016"]]
    pi_rows = [["Statement", "Visible state"], ["PI reviewed AE-014-01", "checked"], ["PI reviewed DEV-014-03", "unchecked"], ["PI reviewed DEV-014-07", "checked"], ["PI reviewed DEV-014-09", "unchecked"], ["PI reviewed DEV-014-11", "unchecked"], ["Clean-ready attestation", "unchecked"], ["Signed by", "Dr. Neha Rao / 2026-05-08"]]
    final_rows = [["Control item", "Final state"], ["Site clean-ready", "No"], ["Critical subject", "014-003"], ["Critical kit", "K-204-153"], ["Open queries", "Q-77, Q-84, Q-86, Q-88, Q-93"], ["Withdrawn subjects", "014-004 related dizziness; 014-013 lost to follow-up"], ["Do not dose", "K-204-153"], ["Masking review", "open for 014-016"], ["Central lab repeats", "014-008, 014-011, 014-016"]]

    pages: list[Image.Image] = []
    p1 = page("Site 014 Monitoring Visit Packet")
    d = ImageDraw.Draw(p1)
    draw_kv_band(d, 82, 210, [("Site", "014 / Harbor Endocrine"), ("Monitor", "L. Sen"), ("Visit", "2026-05-08"), ("Data cut", "2026-05-06")], [330, 300, 260, 260])
    draw_note(d, (90, 370, 1510, 535), "Monitor conclusion", "The site is not clean-ready. Major open items are DEV-014-03 missed W2 ECG for subject 014-003 and DEV-014-07 temperature excursion for kit K-204-153. Subject 014-004 withdrew after related dizziness.", "#7f1d1d")
    draw_ledger(d, 92, 650, [260, 260, 310, 420], [["Section", "Pages", "Critical visual state", "Monitor risk"], ["Enrollment", "2-3", "screen fail vs randomized", "eligibility"], ["Visit grid", "4", "missed ECG cell", "major deviation"], ["Labs", "5", "H/L flags", "safety"], ["AE/deviation", "6-7", "open/resolved status", "query closure"], ["IP accountability", "8-9", "quarantine label", "drug accountability"], ["Queries/final", "10-16", "open query and final readiness", "not clean-ready"]], 56)
    pages.append(p1)

    for title, rows, widths in [
        ("Enrollment and Randomization Log", subjects, [180, 190, 180, 230, 340]),
        ("Visit Schedule Grid", visits, [170, 110, 120, 150, 230, 380]),
        ("Central Lab Abnormal Flags", labs, [170, 190, 130, 90, 210, 130]),
        ("Adverse Event Log", aes, [180, 150, 220, 160, 220, 360]),
        ("Protocol Deviation Log", deviations, [180, 150, 300, 150, 420]),
        ("Investigational Product Accountability", ip_rows[1:], [170, 160, 150, 180, 260, 280]),
    ]:
        p = page(title)
        d = ImageDraw.Draw(p)
        headers = {
            "Enrollment and Randomization Log": ["Subject", "Status", "Date", "Arm / reason", "Note"],
            "Visit Schedule Grid": ["Subject", "Visit", "Date", "State", "Kit", "Note"],
            "Central Lab Abnormal Flags": ["Subject", "Test", "Result", "Flag", "Reference", "Unit"],
            "Adverse Event Log": ["AE", "Subject", "Term", "Severity", "Relatedness", "Outcome"],
            "Protocol Deviation Log": ["Deviation", "Subject", "Description", "Class", "Status/action"],
            "Investigational Product Accountability": ip_rows[0],
        }[title]
        draw_ledger(d, 75, 235, widths, [headers] + rows, 46)
        pages.append(p)

    special_pages = [
        ("Temperature Excursion Source", temp_rows, "Kit K-204-153 must not be dosed; the dispense count is zero even though the kit appears in the visit source."),
        ("ECG Source and Query Q-77", ecg_rows, "The missed ECG is a major deviation and remains open."),
        ("Concomitant Medication Review", med_rows, "Potassium supplement context does not make AE-014-03 related to study drug."),
        ("Monitor Query Log", query_rows, "Open queries are Q-77 and Q-84; Q-81 is answered."),
        ("eCRF Checkbox Audit", ecrf_rows, "Unchecked fields remain source value No until a signed PI correction is filed."),
        ("Sample Shipment Manifest", shipment_rows, "Shipment SH-204-45 is accepted with late-temperature note, not rejected."),
        ("Data Cleaning Readiness", readiness_rows, "Site is not clean-ready because ECG, IP accountability, and central lab remain open."),
        ("Principal Investigator Signoff", pi_rows, "Clean-ready attestation is unchecked."),
        ("Final Monitor Recap", final_rows, "This final recap controls the site status."),
    ]
    for title, rows, note in special_pages:
        p = page(title)
        d = ImageDraw.Draw(p)
        draw_ledger(d, 90, 245, [250, 260, 280, 420], rows, 46)
        draw_note(d, (105, 980, 1510, 1145), "Monitor note", note, "#7f1d1d")
        pages.append(p)

    gold = "\n\n".join([
        "# Helio Therapeutics HTX-204 Site 014 Monitoring Packet",
        "Monitor visit 2026-05-08, data cut 2026-05-06. Site 014 is not clean-ready. Major open items are DEV-014-03 missed W2 ECG for subject 014-003, DEV-014-07 temperature excursion for kit K-204-153, DEV-014-09 repeat central lab not filed, and DEV-014-11 unblinded pharmacist note in source. Open queries are Q-77, Q-84, Q-86, Q-88, and Q-93. Subject 014-004 withdrew after related dizziness and subject 014-013 withdrew/lost to follow-up.",
        "## Packet Overview\nSite 014 / Harbor Endocrine was monitored by L. Sen on 2026-05-08 with data cut 2026-05-06. The overview identifies enrollment, visit grid, labs, AE/deviation, IP accountability, and query/final sections. The monitor conclusion says the site is not clean-ready.",
        "## Enrollment\n" + md_table(["Subject", "Status", "Date", "Arm / reason", "Note"], subjects),
        "## Visit Schedule\n" + md_table(["Subject", "Visit", "Date", "State", "Kit", "Note"], visits),
        "## Labs\n" + md_table(["Subject", "Test", "Result", "Flag", "Reference", "Unit"], labs),
        "## Adverse Events\n" + md_table(["AE", "Subject", "Term", "Severity", "Relatedness", "Outcome"], aes),
        "## Deviations\n" + md_table(["Deviation", "Subject", "Description", "Class", "Status/action"], deviations),
        "## IP Accountability\n" + md_table(ip_rows[0], ip_rows[1:]),
        "## Temperature Excursion Source\n" + md_table(["Time", "Temp", "Action"], temp_rows[1:]) + "\nKit K-204-153 must not be dosed; the dispense count is zero even though the kit appears in the visit source. The final 13:40 reading is back in range, but the kit remains quarantined.",
        "## ECG Source and Query Q-77\n" + md_table(["Field", "Visible state"], ecg_rows[1:]) + "\nThe missed ECG is a major deviation and remains open.",
        "## Concomitant Medication Review\n" + md_table(["Subject", "Medication", "Start", "Stop", "Relevance"], med_rows[1:]) + "\nPotassium supplement context does not make AE-014-03 related to study drug.",
        "## Monitor Query Log\n" + md_table(["Query", "Subject", "Issue", "State"], query_rows[1:]) + "\nOpen queries are Q-77, Q-84, Q-86, Q-88, and Q-93. Q-81 and Q-91 are answered.",
        "## eCRF Checkbox Audit\n" + md_table(["Subject", "Field", "Visible state", "Data entry"], ecrf_rows[1:]) + "\nUnchecked fields remain source value No until a signed PI correction is filed.",
        "## Sample Shipment Manifest\n" + md_table(["Shipment", "Subject", "Tube", "Drawn", "Received", "State"], shipment_rows[1:]) + "\nShipment SH-204-45 is accepted with a late-temperature note, not rejected.",
        "## Data Cleaning Readiness\n" + md_table(["Domain", "Open", "Critical blocker"], readiness_rows[1:]) + "\nSite is not clean-ready because ECG, drug accountability, central lab, AE follow-up, visit windows, and masking remain open.",
        "## Principal Investigator Signoff\n" + md_table(["Statement", "Visible state"], pi_rows[1:]) + "\nClean-ready attestation is unchecked.",
        "## Final Monitor Recap\n" + md_table(["Control item", "Final state"], final_rows[1:]) + "\nThis final recap controls the site status.",
    ])
    facts = [
        fact("p17.final.state", "source_state", 14, "Final monitor state is not clean-ready; blockers include DEV-014-03 missed W2 ECG for 014-003, K-204-153 temperature excursion/do not dose, central lab issues for 014-008/014-011/014-016, visit-window query Q-86, repeat-lab query Q-88, masking query Q-93, and open queries Q-77/Q-84/Q-86/Q-88/Q-93.", modality="source-precedence", severity="critical"),
        fact("p17.overview", "structure", 6, "Overview preserves site 014 / Harbor Endocrine, monitor L. Sen, visit 2026-05-08, data cut 2026-05-06, and the section/risk map from enrollment through queries/final.", modality="structure", severity="major"),
        fact("p17.enrollment.screenfail", "table_cell", 8, "Enrollment log preserves 014-001 screen fail because HbA1c 9.1 and 014-006 screen fail because eGFR 42, both not randomized.", modality="table", severity="critical"),
        fact("p17.enrollment.randomized", "table_cell", 10, "Enrollment log preserves randomized subjects 014-002 Arm B completed W4, 014-003 Arm A missed W2 ECG, 014-005 Arm A completed W4, 014-007 Arm B IP temperature excursion, 014-008 Arm A central lab pending, 014-009 Arm B W2 diary window late, 014-011 Arm A central lab repeat pending, 014-012 Arm B waiver W-14, 014-014 Arm A ePRO not activated, and 014-016 Arm B unblinded pharmacist note.", modality="table", severity="critical"),
        fact("p17.enrollment.additional", "table_cell", 10, "Enrollment log preserves added screen/withdrawal states: 014-010 screen fail QTc 486 ms, 014-015 screen fail BP 168/98, 014-013 withdrawn/lost to follow-up before W4, and 014-012 eligible with waiver W-14.", modality="table", severity="critical"),
        fact("p17.enrollment.withdrawn", "table_cell", 8, "Enrollment log preserves 014-004 withdrawn on 2026-04-10 from Arm B due AE dizziness and 014-013 withdrawn/lost to follow-up before W4.", modality="table", severity="critical"),
        fact("p17.visit.014002", "table_cell", 8, "Visit grid preserves subject 014-002 V1/W2/W4 rows, dates 04-05/04-19/05-03, kits K-204-118/K-204-142/K-204-166, and notes ECG normal/diary returned/dose reduced.", modality="table", severity="major"),
        fact("p17.visit.problem.rows", "table_cell", 10, "Visit grid preserves 014-003 W2 partial kit K-204-146 ECG not done, 014-004 W2 withdrawn with no kit/early termination, 014-007 V1 kit K-204-153 temp excursion, 014-007 W2 hold/repeat lab required, 014-009 W2 late outside +2 day window, 014-014 V1 ePRO not activated, and 014-016 V1 pharmacist note sealed.", modality="table", severity="critical"),
        fact("p17.labs.flags", "table_cell", 10, "Lab table preserves abnormal flags and units: 014-003 ALT 67 H U/L and eGFR 58 L mL/min, 014-004 hemoglobin 10.8 L g/dL, 014-007 potassium 5.6 H mmol/L, 014-009 ALT 49 H U/L, 014-011 creatinine 1.34 H mg/dL, 014-013 hemoglobin 11.7 L g/dL, and 014-016 glucose 62 L mg/dL.", modality="table", severity="critical"),
        fact("p17.labs.normal", "table_cell", 5, "Lab table preserves normal 014-002 ALT 38 U/L reference 0-45 and creatinine 1.11 mg/dL reference 0.60-1.30 with blank flags.", modality="table", severity="major"),
        fact("p17.aes", "table_cell", 10, "AE log preserves AE IDs bound to subjects/terms: AE-014-01 014-004 dizziness moderate related withdrawn 2026-04-24; AE-014-02 014-002 nausea mild possibly related dose reduced W4; AE-014-03 014-007 hyperkalemia moderate unrelated repeat lab normal; AE-014-04 014-009 headache resolved; AE-014-05 014-011 creatinine increased repeat lab pending; AE-014-06 014-013 lost contact not AE; AE-014-07 014-016 hypoglycemia related safety call completed.", modality="table", severity="critical"),
        fact("p17.deviations", "source_state", 12, "Deviation log preserves DEV-014-03 W2 ECG missed major/open Q-77, DEV-014-07 IP temp 9.1C for 3h major/do not dose K-204-153, DEV-014-02 diary page late minor/resolved, DEV-014-08 W2 outside +2 day window open Q-86, DEV-014-09 repeat central lab not filed major/open Q-88, DEV-014-10 ePRO not activated/retrain coordinator, and DEV-014-11 unblinded pharmacist note major/masking review open.", modality="source-precedence", severity="critical"),
        fact("p17.ip.accountability.returned", "table_cell", 8, "IP accountability preserves returned counts/states for K-204-118 = 4, K-204-142 = 6, K-204-166 = 2, K-204-121 = 5, K-204-146 = not returned/open, K-204-158 pending/reconcile after lab, K-204-160 returned 3/diary window late, K-204-171 pending/hold repeat lab, K-204-184 returned 0/ePRO activation open, and K-204-190 returned 2/masking review.", modality="table", severity="critical"),
        fact("p17.ip.accountability.quarantine", "table_cell", 10, "IP accountability preserves K-204-153 for 014-007 dispensed 0, returned quarantined, temp flag 9.1C for 3h, final state do not dose.", modality="table", severity="critical"),
        fact("p17.temperature.timeline", "table_cell", 8, "Temperature excursion source preserves 04-18 09:10 8.4C alarm, 10:10 9.1C quarantine K-204-153, 11:10 8.8C pharmacy notified, 12:10 7.8C still above range, 13:05 5.2C returned to range, and 13:40 4.7C back in range while the kit remains quarantined.", modality="table", severity="major"),
        fact("p17.ecg.query", "form_state", 10, "ECG source preserves subject 014-003 W2 / 2026-04-21, ECG checkbox unchecked, reason machine unavailable, and query Q-77 open with PI response pending.", modality="form", severity="critical"),
        fact("p17.conmed", "table_cell", 7, "Concomitant medication review preserves metformin allowed for 014-002, meclizine 04-11 to 04-24 for 014-004 AE dizziness, potassium supplement 04-01 to 04-19 for 014-007 hyperkalemia context, ibuprofen 014-009 headache, lisinopril 014-011 renal context, and glipizide 014-016 hypoglycemia context.", modality="table", severity="major"),
        fact("p17.query.log", "source_state", 9, "Monitor query log preserves Q-74 answered, Q-77 open for 014-003 W2 ECG missing, Q-81 answered do not dose for 014-007 temperature excursion dosing, Q-84 open for 014-008 central lab pending, Q-86 open for 014-009 W2 visit outside window, Q-88 open for 014-011 repeat lab report missing, Q-91 answered retrained for 014-014 ePRO activation evidence, and Q-93 open for 014-016 pharmacist masking note.", modality="source-precedence", severity="critical"),
        fact("p17.ecrf.checkboxes", "form_state", 10, "eCRF checkbox audit preserves W2 ECG performed unchecked for 014-003, withdrawal due AE checked for 014-004, kit dispensed unchecked for 014-007, central lab reviewed unchecked for 014-008, visit in window unchecked for 014-009, repeat lab attached unchecked for 014-011, ePRO activated unchecked for 014-014, and masking reviewed unchecked for 014-016.", modality="form", severity="critical"),
        fact("p17.shipments", "table_cell", 9, "Shipment manifest preserves SH-204-44 accepted with received 04-20 09:02, SH-204-45 received 04-23 16:40 with temperature late state accepted/not rejected, SH-204-46 pending/not reviewed, SH-204-47 accepted late draw, SH-204-48 repeat requested, and SH-204-49 safety call done.", modality="table", severity="major"),
        fact("p17.readiness", "table_cell", 9, "Data cleaning readiness preserves Enrollment open 0 none, ECG open 1 Q-77/014-003, Drug accountability open 1 K-204-153 quarantine, Central lab open 3 for 014-008/014-011/014-016, AE open 1 AE-014-05 repeat lab pending, Visit windows open 1 Q-86/014-009, and Masking open 1 Q-93/014-016.", modality="table", severity="critical"),
        fact("p17.pi.signoff", "form_state", 8, "PI signoff preserves AE-014-01 checked, DEV-014-03 unchecked, DEV-014-07 checked, DEV-014-09 unchecked, DEV-014-11 unchecked, clean-ready attestation unchecked, signed Dr. Neha Rao 2026-05-08.", modality="form", severity="critical"),
        fact("p17.final.recap", "source_state", 9, "Final monitor recap preserves site clean-ready No, critical subject 014-003, critical kit K-204-153, open queries Q-77/Q-84/Q-86/Q-88/Q-93, withdrawn subjects 014-004 related dizziness and 014-013 lost to follow-up, do not dose K-204-153, masking review open for 014-016, and central lab repeats for 014-008/014-011/014-016.", modality="source-precedence", severity="critical"),
    ]
    return Case("P17-clinical-trial-site-monitoring", "Clinical Trial Site Monitoring Binder", "clinical-trial", ["multi-page", "clinical-trial", "forms", "labs", "source-precedence", "drug-accountability", "queries"], "Stress long clinical trial source reconstruction with form states, safety flags, accountability, and final monitoring state.", "Sixteen-page site-monitoring packet with enrollment, visit grid, labs, adverse events, deviations, IP accountability, source forms, and final monitor status.", ["enrollment", "visit grid", "labs", "AEs", "deviations", "IP accountability"], ["Preserve form states, source-state conflicts, and final not-clean-ready status."], gold, [near_check("p17-final", "source_state", ["not clean-ready", "014-003", "K-204-153", "Q-77", "Q-84"], 8, 900)], pages, facts=facts)


def packet_aircraft_maintenance_release() -> Case:
    def page(title: str) -> Image.Image:
        img = Image.new("RGB", (PAGE_W, PAGE_H), "#fffdfa")
        d = ImageDraw.Draw(img)
        d.text((72, 54), "Cascade Regional Air | Line maintenance record | Aircraft N742CR", fill="#334155", font=F["tiny_bold"])
        d.text((72, 90), title, fill="#111827", font=F["h1"])
        d.line((72, 148, 1585, 148), fill="#1f2937", width=2)
        d.text((1390, 55), "MX CONTROL", fill="#92400e", font=F["tiny_bold"])
        return img

    index_rows = [["Page", "Artifact", "Controlling detail"]] + [
        ["1", "Event summary", "aircraft remains AOG until final release"],
        ["2", "Tech log", "APU GEN fault and resets"],
        ["3", "MEL / dispatch sheet", "MEL not allowed for revenue leg"],
        ["4", "Electrical one-line", "K17 relay path to right AC bus"],
        ["5", "Flight data trend", "voltage drop at 06:42:18Z"],
        ["6", "Borescope contact sheet", "connector P42 heat discoloration"],
        ["7", "Parts trace", "BPCU removed, K17 replaced"],
        ["8", "Work cards", "open insulation-resistance retest"],
        ["9", "Torque / inspection", "connector P42 torque values"],
        ["10", "Functional test", "APU gen load test passed after K17"],
        ["11", "Deferral board", "wrongly shows dispatchable"],
        ["12", "QA discrepancy", "QA hold until retest evidence attached"],
        ["13", "Release form", "final CRS signed 2026-07-03 18:44Z"],
        ["14", "Final recap", "aircraft released after retest, not MEL"],
    ]
    tech_rows = [
        ["Time Z", "Source", "Entry", "State"],
        ["06:38", "Captain", "APU GEN OFF BUS after gate return", "open"],
        ["06:41", "EICAS", "ELEC AC BUS R amber, reset unsuccessful", "fault active"],
        ["06:46", "Mechanic Voss", "BPCU bite code 22-17 stored", "investigate"],
        ["07:15", "Ops control", "requested MEL dispatch", "rejected later"],
        ["09:20", "MX lead", "connector P42 discoloration found", "repair path"],
        ["16:55", "QA", "load test pass, IR retest missing", "hold"],
        ["18:44", "QA release", "IR retest attached, CRS signed", "released"],
    ]
    mel_rows = [
        ["Item", "Visible state", "Reason"],
        ["MEL 24-21-02 APU generator", "not permitted", "both IDG channels required for planned sector"],
        ["Dispatch note", "crossed out", "early desk note said ferry-only"],
        ["Revenue flight CR118", "cancelled", "passengers reaccommodated"],
        ["Final path", "repair and test", "not MEL dispatch"],
    ]
    flight_rows = [
        ["Timestamp Z", "APU V", "Right AC bus V", "BPCU status", "Note"],
        ["06:41:50", "115", "115", "normal", "before fault"],
        ["06:42:10", "114", "109", "watch", "right bus sag"],
        ["06:42:18", "92", "0", "trip", "fault point"],
        ["06:42:25", "0", "0", "off bus", "reset failed"],
        ["17:35:30", "115", "115", "normal", "post repair test"],
    ]
    parts_rows = [
        ["Part", "Removed", "Installed", "Serial / batch", "Disposition"],
        ["BPCU 948D", "S/N BPCU-19-442", "reinstalled after bench pass", "bench tag BT-7721", "not root cause"],
        ["Relay K17", "S/N K17-882", "K17-1044", "batch RY-771", "replaced"],
        ["Connector P42 pins", "heat-damaged sleeves", "new sleeves", "kit CW-24-9", "reworked"],
        ["Breaker C428", "not removed", "not changed", "functional reset OK", "not cause"],
    ]
    work_rows = [
        ["Card", "Task", "Mechanic", "Status", "Evidence"],
        ["24-31-11", "Inspect APU GEN contactor path", "Voss", "closed", "P42 heat marks"],
        ["24-31-12", "Replace K17 relay", "Ng", "closed", "K17-1044 installed"],
        ["24-31-13", "IR test feeder APU-GEN-R", "Pena", "retest required", "first value 1.1 Mohm"],
        ["24-31-14", "Load test at 50/75/100%", "Voss", "closed", "passed 17:35Z"],
    ]
    torque_rows = [
        ["Fastener / pin", "Spec", "Actual", "Inspector", "State"],
        ["P42-A", "18-22 in-lb", "20", "QA Hale", "pass"],
        ["P42-B", "18-22 in-lb", "19", "QA Hale", "pass"],
        ["P42-C", "18-22 in-lb", "23", "QA Hale", "adjusted to 21"],
        ["K17 mount", "32-38 in-lb", "35", "QA Hale", "pass"],
    ]
    function_rows = [
        ["Test point", "Load", "APU V", "Right bus V", "Result"],
        ["No load", "0%", "115", "115", "pass"],
        ["Galley + avionics", "50%", "114", "114", "pass"],
        ["Hyd pump + galley", "75%", "114", "113", "pass"],
        ["Full cabin load", "100%", "113", "113", "pass"],
        ["Reset check", "3 cycles", "stable", "stable", "pass"],
    ]
    hold_rows = [
        ["Hold item", "Opened", "Closed", "Reason"],
        ["IR retest missing", "16:55Z", "18:21Z", "first evidence packet omitted retest"],
        ["BPCU bench tag", "16:55Z", "17:48Z", "BT-7721 attached"],
        ["MEL request", "07:15Z", "17:02Z", "voided after repair path accepted"],
        ["CRS signature", "open", "18:44Z", "final release"],
    ]
    qa_rows = [
        ["Gate", "Visible state", "Owner", "Final"],
        ["IR retest evidence", "attached 18:21Z", "Pena", "closed"],
        ["BPCU bench tag", "attached BT-7721", "Voss", "closed"],
        ["MEL dispatch request", "voided", "Ops control", "not controlling"],
        ["Certificate of release", "signed 18:44Z", "QA Hale", "controls"],
    ]
    pages: list[Image.Image] = []
    p = page("Aircraft Maintenance Release Packet - Event AOG-742-0703")
    d = ImageDraw.Draw(p)
    draw_kv_band(d, 82, 205, [("Aircraft", "N742CR"), ("Station", "PDX"), ("Event", "AOG-742-0703"), ("Opened", "2026-07-03 06:38Z"), ("Final", "released 18:44Z")], [220, 170, 250, 300, 300])
    draw_note(d, (90, 365, 1510, 530), "Control summary", "The aircraft is released only after repair, load test, and insulation-resistance retest. The earlier MEL dispatch note and deferral board are historical and do not control final release.", "#991b1b")
    draw_ledger(d, 92, 650, [90, 420, 650], index_rows, 45)
    pages.append(p)

    tables = [
        ("Technical Log Continuation", [["Time Z", "Source", "Entry", "State"]] + tech_rows[1:], [170, 210, 650, 220], "The 18:44Z CRS line controls final state."),
        ("MEL and Dispatch Control Sheet", [["Item", "Visible state", "Reason"]] + mel_rows[1:], [360, 280, 680], "MEL dispatch is not the final disposition."),
        ("Flight Data Trend", [["Timestamp Z", "APU V", "Right AC bus V", "BPCU status", "Note"]] + flight_rows[1:], [190, 130, 190, 190, 420], "Fault point is 06:42:18Z: APU 92 V, right AC bus 0 V, BPCU trip."),
        ("Parts Traceability", [["Part", "Removed", "Installed", "Serial / batch", "Disposition"]] + parts_rows[1:], [260, 250, 300, 230, 260], "K17 relay is replaced; BPCU bench passed and is not the root cause."),
        ("Work Card Status Board", [["Card", "Task", "Mechanic", "Status", "Evidence"]] + work_rows[1:], [150, 430, 160, 200, 360], "IR test card stayed open until retest evidence attached."),
        ("Torque and Connector Inspection", [["Fastener / pin", "Spec", "Actual", "Inspector", "State"]] + torque_rows[1:], [260, 220, 160, 220, 390], "P42-C was initially 23 in-lb and adjusted to 21."),
        ("Functional Load Test Results", [["Test point", "Load", "APU V", "Right bus V", "Result"]] + function_rows[1:], [310, 150, 160, 180, 180], "All functional test points passed after K17 replacement."),
        ("QA Discrepancy Hold Memo", [["Hold item", "Opened", "Closed", "Reason"]] + hold_rows[1:], [300, 180, 180, 520], "QA hold stayed open after the load test until IR retest evidence was attached at 18:21Z."),
        ("QA Gate and Release Evidence", [["Gate", "Visible state", "Owner", "Final"]] + qa_rows[1:], [330, 330, 220, 280], "Certificate of release signed 18:44Z controls over voided MEL request."),
    ]
    for title, rows, widths, note in tables:
        p = page(title)
        d = ImageDraw.Draw(p)
        draw_ledger(d, 70, 230, widths, rows, 58)
        draw_note(d, (90, 930, 1510, 1105), "Source-state note", note, "#334155")
        if title == "Flight Data Trend":
            d.rectangle((120, 1210, 1470, 1620), outline="#334155", width=2)
            d.text((150, 1235), "APU generator voltage / right AC bus trend", fill="#111827", font=F["small_bold"])
            pts = [(210, 1480), (470, 1484), (720, 1538), (770, 1600), (1010, 1600), (1320, 1480)]
            for a, b in zip(pts, pts[1:]):
                d.line((*a, *b), fill="#2563eb", width=4)
            d.line((750, 1270, 750, 1610), fill="#991b1b", width=3)
            d.text((770, 1285), "06:42:18Z trip", fill="#991b1b", font=F["tiny_bold"])
        pages.append(p)

    p = page("Electrical One-Line and Fault Isolation")
    d = ImageDraw.Draw(p)
    boxes = [("APU GEN", 150, 310), ("P42 connector", 430, 310), ("K17 relay", 710, 310), ("BPCU", 990, 310), ("Right AC bus", 1270, 310)]
    for label, x, y in boxes:
        d.rounded_rectangle((x, y, x + 190, y + 105), radius=8, fill="#f8fafc", outline="#334155", width=3)
        draw_text(d, (x + 18, y + 35), label, F["tiny_bold"], width=15, leading=22)
    for (_, x1, y1), (_, x2, y2) in zip(boxes, boxes[1:]):
        d.line((x1 + 190, y1 + 52, x2, y2 + 52), fill="#111827", width=4)
        d.polygon([(x2, y2 + 52), (x2 - 14, y2 + 44), (x2 - 14, y2 + 60)], fill="#111827")
    d.line((805, 415, 805, 620), fill="#991b1b", width=4)
    d.text((835, 540), "open under heat", fill="#991b1b", font=F["tiny_bold"])
    draw_ledger(d, 120, 760, [260, 310, 520], [["Callout", "Observed", "Finding"], ["A", "P42 sleeve brown at pins B/C", "rework required"], ["B", "K17 relay intermittent coil", "root cause"], ["C", "BPCU code 22-17", "symptom, bench passed"], ["D", "C428 breaker reset", "not cause"]], 62)
    pages.append(p)

    p = page("Borescope and Photo Contact Sheet")
    d = ImageDraw.Draw(p)
    draw_text(d, (95, 220), "The QA export records image metadata and inspector annotations. Full-resolution images remain in the maintenance imaging system under work package AOG-742-0703.", F["small"], width=100, leading=30)
    draw_ledger(d, 95, 360, [100, 250, 210, 310, 360], [["Frame", "Image file", "Location", "Reviewer callout", "Maintenance meaning"], ["F1", "IMG-742-0703-1184", "P42 pin B", "brown sleeve", "connector rework required"], ["F2", "IMG-742-0703-1185", "K17 relay bay", "relay removed", "relay replacement path"], ["F3", "IMG-742-0703-1186", "BPCU rack", "no burn marks", "BPCU not root cause"], ["F4", "IMG-742-0703-1187", "C428 breaker", "normal reset mark", "breaker not cause"]], 64)
    draw_ledger(d, 95, 790, [210, 260, 260, 360], [["Callout", "Checked by", "Time Z", "Disposition"], ["A", "QA Hale", "12:40", "P42 sleeve repair added to work card"], ["B", "Voss", "13:15", "K17 removed and quarantined"], ["C", "QA Hale", "13:42", "BPCU rack accepted"], ["D", "Ng", "14:05", "C428 reset checked, no replacement"]], 60)
    draw_note(d, (95, 1215, 1510, 1395), "Image-log interpretation", "Only frame F1 documents heat discoloration at P42. F3 rules out BPCU rack burn marks; F4 shows normal breaker reset. The absence of embedded thumbnails in this export does not change those visible metadata findings.", "#334155")
    pages.append(p)

    p = page("Deferral Board Snapshot")
    d = ImageDraw.Draw(p)
    draw_ledger(d, 90, 250, [260, 260, 260, 260], [["Board item", "Shown value", "Final value", "Why"], ["Dispatch status", "dispatchable", "AOG hold", "MEL not allowed"], ["Repair path", "MEL 24-21-02", "repair/test", "sector equipment requirement"], ["Release", "pending crew", "QA CRS 18:44Z", "final page controls"]], 70)
    draw_note(d, (95, 760, 1510, 950), "Snapshot warning", "The deferral board is a stale operational snapshot. It is visible audit context, but it does not control the final aircraft state.", "#991b1b")
    pages.append(p)

    p = page("Final Recap and Certificate of Release")
    d = ImageDraw.Draw(p)
    draw_ledger(d, 90, 245, [350, 330, 500], [["Control item", "Final state", "Evidence"], ["Aircraft status", "released", "CRS signed 2026-07-03 18:44Z"], ["Root cause", "K17 relay intermittent coil", "K17-1044 installed"], ["P42 connector", "reworked", "torque pass after adjustment"], ["BPCU", "not root cause", "bench tag BT-7721"], ["MEL dispatch", "voided", "not allowed for revenue leg"]], 64)
    pages.append(p)

    gold = "\n\n".join([
        "# Cascade Regional Air AOG-742-0703 Maintenance Release",
        "Aircraft N742CR at PDX opened 2026-07-03 06:38Z and was finally released at 18:44Z. Earlier MEL dispatch/deferral-board states are historical; final release required repair, load test, and insulation-resistance retest.",
        "## Packet Index\n" + md_table(["Page", "Artifact", "Controlling detail"], index_rows[1:]),
        "## Technical Log\n" + md_table(["Time Z", "Source", "Entry", "State"], tech_rows[1:]),
        "## MEL and Dispatch\n" + md_table(["Item", "Visible state", "Reason"], mel_rows[1:]),
        "## Electrical One-Line\nDirected path: APU GEN -> P42 connector -> K17 relay -> BPCU -> Right AC bus. Callout A is P42 sleeve brown at pins B/C and requires rework. Callout B is K17 relay intermittent coil and root cause. Callout C is BPCU code 22-17 but bench passed. Callout D is C428 breaker reset and not cause.",
        "## Flight Data Trend\n" + md_table(["Timestamp Z", "APU V", "Right AC bus V", "BPCU status", "Note"], flight_rows[1:]),
        "## Borescope Contact Sheet\nFrame F1 shows P42 pin B sleeve brown / heat discoloration. F2 shows K17 relay bay with relay removed. F3 shows BPCU rack with no burn marks. F4 shows C428 breaker normal reset.",
        "## Parts Trace\n" + md_table(["Part", "Removed", "Installed", "Serial / batch", "Disposition"], parts_rows[1:]),
        "## Work Cards\n" + md_table(["Card", "Task", "Mechanic", "Status", "Evidence"], work_rows[1:]),
        "## Torque Inspection\n" + md_table(["Fastener / pin", "Spec", "Actual", "Inspector", "State"], torque_rows[1:]),
        "## Functional Load Test\n" + md_table(["Test point", "Load", "APU V", "Right bus V", "Result"], function_rows[1:]),
        "## QA Discrepancy Hold Memo\n" + md_table(["Hold item", "Opened", "Closed", "Reason"], hold_rows[1:]),
        "## QA Gates\n" + md_table(["Gate", "Visible state", "Owner", "Final"], qa_rows[1:]),
    ])
    facts = [
        fact("p18.final.state", "source_state", 12, "Final aircraft state is released only after repair, load test, and IR retest; MEL dispatch and stale deferral-board dispatchable state do not control.", modality="source-precedence", severity="critical"),
        fact("p18.index", "structure", 5, "Packet index contains all 14 artifacts in order and identifies the final recap/release page as controlling final state.", modality="structure", severity="major"),
        fact("p18.tech.log", "table_cell", 8, "Technical log preserves all seven time/source/entry/state rows from 06:38 captain entry through 18:44 QA release.", modality="table", severity="critical"),
        fact("p18.mel", "source_state", 8, "MEL 24-21-02 APU generator is not permitted for revenue leg; ferry-only/dispatch note is crossed out; final path is repair and test.", modality="source-precedence", severity="critical"),
        fact("p18.oneline", "visual_relation", 10, "Electrical one-line preserves directed path APU GEN to P42 connector to K17 relay to BPCU to Right AC bus and callouts A-D with root cause at K17.", modality="visual", severity="critical"),
        fact("p18.trend", "chart", 8, "Flight data trend preserves 06:42:18Z fault point with APU 92 V, right AC bus 0 V, BPCU trip, plus post-repair 17:35:30 normal values.", modality="chart", severity="critical"),
        fact("p18.photos", "visual_relation", 8, "Borescope sheet preserves F1 heat discoloration at P42, F2 K17 relay bay, F3 BPCU no burn marks, and F4 C428 normal reset.", modality="visual", severity="major"),
        fact("p18.parts", "table_cell", 8, "Parts trace preserves BPCU removed/reinstalled after bench pass, K17 relay K17-882 replaced by K17-1044, P42 sleeve rework kit CW-24-9, and breaker C428 not changed.", modality="table", severity="critical"),
        fact("p18.workcards", "table_cell", 8, "Work cards preserve 24-31-13 IR test feeder APU-GEN-R as retest required with first value 1.1 Mohm, while load test card passed at 17:35Z.", modality="table", severity="critical"),
        fact("p18.torque", "table_cell", 7, "Torque table preserves P42-A 20, P42-B 19, P42-C initially 23 adjusted to 21, and K17 mount 35 with specs/inspector.", modality="table", severity="major"),
        fact("p18.functional.test", "table_cell", 7, "Functional load test preserves no-load, 50%, 75%, 100%, and 3-cycle reset check rows with APU/right-bus voltage values and pass results.", modality="table", severity="major"),
        fact("p18.qa.hold", "source_state", 8, "QA hold memo preserves IR retest missing opened 16:55Z and closed 18:21Z; load test pass alone did not release the aircraft.", modality="source-precedence", severity="critical"),
        fact("p18.qa", "form_state", 8, "QA gates preserve IR retest attached 18:21Z, BPCU bench tag BT-7721, MEL request voided, and CRS signed 18:44Z controls.", modality="form", severity="critical"),
        fact("p18.no.stale.dispatch", "source_state", 8, "Output must not treat the deferral board's dispatchable/MEL values as final; they are stale audit context.", modality="source-precedence", severity="critical"),
    ]
    return Case("P18-aircraft-maintenance-release", "Aircraft Maintenance Release Packet", "aviation-maintenance", ["multi-page", "aviation", "forms", "one-line-diagram", "photo-contact-sheet", "source-precedence"], "Stress aircraft maintenance release with one-line diagram relations, photo evidence, work-card states, and stale dispatch conflicts.", "Fourteen-page aircraft maintenance packet with tech log, MEL sheet, electrical one-line, trend chart, borescope sheet, parts trace, work cards, torque inspection, QA gates, and final release.", ["tech log", "MEL sheet", "one-line diagram", "photo evidence", "work cards", "QA release"], ["Use page order, local tables, visual relations, and final-state context."], gold, [near_check("p18-final", "source_state", ["released", "18:44Z", "K17", "MEL", "voided"], 8, 900)], pages, facts=facts)


def packet_property_loss_adjustment() -> Case:
    def page(title: str) -> Image.Image:
        img = Image.new("RGB", (PAGE_W, PAGE_H), "#fffef8")
        d = ImageDraw.Draw(img)
        d.text((72, 54), "Granite Mutual | Commercial property claim CL-8827 | Adjuster packet", fill="#334155", font=F["tiny_bold"])
        d.text((72, 90), title, fill="#111827", font=F["h1"])
        d.line((72, 148, 1585, 148), fill="#1f2937", width=2)
        return img

    rooms = [["Room", "Zone", "Moisture", "Smoke", "Disposition"], ["Retail floor", "A", "18-22%", "heavy", "replace ceiling tiles"], ["Stock room", "B", "28-34%", "moderate", "remove drywall 4 ft"], ["Office", "C", "12-14%", "light", "clean and seal"], ["Electrical closet", "D", "dry", "soot at panel", "licensed inspection"], ["Restroom", "E", "21%", "light", "dry-out only"]]
    estimate1 = [["Line", "Area", "Description", "Qty", "Unit", "RCV", "ACV"], ["1", "A", "Ceiling tile ACT replace", "640", "sf", "$2,496.00", "$1,996.80"], ["2", "A", "Smoke seal primer", "1,240", "sf", "$2,852.00", "$2,566.80"], ["3", "B", "Remove drywall flood cut", "88", "lf", "$1,408.00", "$1,267.20"], ["4", "B", "Content manipulation", "6", "hr", "$690.00", "$690.00"], ["5", "D", "Electrical panel inspection", "1", "ea", "$485.00", "$485.00"]]
    estimate2 = [["Line", "Area", "Description", "Qty", "Unit", "RCV", "ACV"], ["6", "A/B", "HEPA air scrubber", "3", "day", "$945.00", "$945.00"], ["7", "C", "Clean/seal wall smoke", "420", "sf", "$882.00", "$793.80"], ["8", "E", "Dehumidifier", "2", "day", "$226.00", "$226.00"], ["9", "B", "Stock shelving detach/reset", "12", "lf", "$468.00", "$421.20"], ["10", "Excluded", "Tenant signage upgrade", "1", "ea", "$1,180.00", "$0.00"]]
    photo_rows = [["Photo", "Visible cue", "Coverage state"], ["P1", "ceiling grid sag over register A3", "covered smoke/water"], ["P2", "stock room wet drywall line 42 inches", "covered water"], ["P3", "old crack behind shelving", "pre-existing excluded"], ["P4", "electrical panel soot at lower left", "inspection covered"], ["P5", "new illuminated sign mockup", "upgrade excluded"], ["P6", "restroom baseboard wet at mop sink", "dry-out covered"]]
    contents_rows = [["Item", "Qty", "Claimed", "Allowed", "Reason"], ["Printed cartons", "48", "$1,920.00", "$1,440.00", "salvage 25%"], ["Card reader dock", "2", "$380.00", "$0.00", "not damaged"], ["Thermal labels", "30 rolls", "$315.00", "$315.00", "smoke odor"], ["Tenant sign", "1", "$1,180.00", "$0.00", "upgrade"], ["Metal shelving", "12 lf", "$960.00", "$421.20", "detach/reset only"]]
    payments = [["Bucket", "Amount", "State"], ["Building RCV", "$10,452.00", "covered"], ["Building depreciation", "($1,381.20)", "recoverable"], ["Building ACV", "$9,070.80", "before deductible"], ["Contents allowed", "$1,755.00", "covered"], ["Deductible", "($2,500.00)", "applies once"], ["Initial ACV payment", "$8,325.80", "controls"], ["Recoverable depreciation", "$1,381.20", "after repairs"], ["Excluded / denied", "$1,560.00", "sign upgrade + card docks"]]
    pages: list[Image.Image] = []
    p = page("Claim Overview and Source Hierarchy")
    d = ImageDraw.Draw(p)
    draw_kv_band(d, 82, 210, [("Insured", "Harbor Books LLC"), ("Loss date", "2026-06-18"), ("Claim", "CL-8827"), ("Cause", "sprinkler head leak + smoke"), ("Final ACV", "$8,325.80")], [300, 230, 180, 360, 230])
    draw_note(d, (90, 370, 1510, 545), "Final-payment note", "The final payment worksheet controls. Early field notes and contractor estimate include signage upgrade and card-reader docks, but those items are excluded from payment.", "#991b1b")
    draw_ledger(d, 95, 650, [90, 410, 620], [["Page", "Artifact", "Critical detail"], ["1", "Overview", "final payment controls"], ["2", "Field notes", "sprinkler leak timeline"], ["3", "Floor plan", "zones A-E"], ["4", "Moisture map", "room readings"], ["5", "Photo contact sheet", "P3/P5 excluded"], ["6-7", "Estimate continuation", "line 10 excluded"], ["8", "Contents", "allowed vs claimed"], ["9", "Coverage letter", "deductible and depreciation"], ["10", "Contractor estimate", "not controlling"], ["11", "Electrical report", "inspection covered"], ["12", "Payment worksheet", "ACV $8,325.80"], ["13", "Recoverable depreciation", "after repairs"], ["14", "Final recap", "excluded values retained as context"]], 48)
    pages.append(p)
    property_widths = {
        "Room Damage and Moisture Summary": [260, 120, 190, 190, 410],
        "Estimate Continuation - Lines 1-5": [90, 110, 420, 110, 100, 160, 160],
        "Estimate Continuation - Lines 6-10": [90, 110, 420, 110, 100, 160, 160],
        "Contents Inventory Review": [310, 130, 170, 170, 430],
        "Payment Worksheet": [360, 230, 540],
    }
    for title, rows, note in [
        ("Room Damage and Moisture Summary", rooms, "Zone letters correspond to the floor-plan sketch."),
        ("Estimate Continuation - Lines 1-5", estimate1, "Lines 1-5 are covered building items."),
        ("Estimate Continuation - Lines 6-10", estimate2, "Line 10 tenant signage upgrade is excluded with ACV $0.00."),
        ("Contents Inventory Review", contents_rows, "Card reader docks and tenant sign are denied; thermal labels are allowed."),
        ("Payment Worksheet", payments, "Initial ACV payment is $8,325.80 after one $2,500 deductible."),
    ]:
        p = page(title)
        d = ImageDraw.Draw(p)
        draw_ledger(d, 70, 235, property_widths[title], rows, 58)
        draw_note(d, (90, 930, 1510, 1110), "Adjuster note", note, "#334155")
        pages.append(p)
    p = page("Annotated Floor Plan")
    d = ImageDraw.Draw(p)
    d.rectangle((150, 250, 1400, 1020), outline="#111827", width=4)
    zones = [("A Retail floor", 180, 290, 790, 730, "#fee2e2"), ("B Stock", 820, 290, 1360, 610, "#dbeafe"), ("C Office", 820, 640, 1080, 980, "#fef3c7"), ("D Elec", 1110, 640, 1360, 780, "#e5e7eb"), ("E Restroom", 1110, 815, 1360, 980, "#dcfce7")]
    for label, x1, y1, x2, y2, fill in zones:
        d.rectangle((x1, y1, x2, y2), fill=fill, outline="#111827", width=2)
        d.text((x1 + 18, y1 + 18), label, fill="#111827", font=F["small_bold"])
    draw_note(d, (150, 1130, 1400, 1320), "Sketch relation", "Sprinkler head is over the A/B wall. Smoke path moves from A into C. Electrical closet D requires inspection but not replacement.", "#334155")
    pages.append(p)
    p = page("Photo Contact Sheet")
    d = ImageDraw.Draw(p)
    for i, row in enumerate(photo_rows[1:]):
        x = 90 + (i % 3) * 500
        y = 245 + (i // 3) * 520
        d.rectangle((x, y, x + 420, y + 280), fill="#374151", outline="#111827", width=2)
        d.text((x, y - 30), f"{row[0]} | {row[1]}", fill="#111827", font=F["tiny_bold"])
        draw_text(d, (x, y + 300), row[2], F["tiny"], width=34, leading=22)
    draw_ledger(d, 110, 1350, [110, 520, 420], photo_rows, 48)
    pages.append(p)
    for title in ["Contractor Estimate Comparison", "Electrical Inspection Report", "Recoverable Depreciation Schedule", "Final Settlement Recap"]:
        p = page(title)
        d = ImageDraw.Draw(p)
        if title == "Contractor Estimate Comparison":
            draw_ledger(d, 90, 250, [330, 260, 260, 360], [["Source", "Gross", "Included excluded items", "Use"], ["Contractor", "$13,392.00", "sign and card docks", "context only"], ["Adjuster estimate", "$10,452.00", "exclusions removed", "building RCV"], ["Final worksheet", "$8,325.80", "deductible applied", "payment controls"]], 66)
        elif title == "Electrical Inspection Report":
            draw_ledger(d, 90, 250, [330, 310, 450], [["Location", "Finding", "Disposition"], ["Closet D panel", "soot at lower-left lugs", "inspection covered"], ["Main breaker", "no arcing", "no replacement"], ["Outlet row A-east", "GFCI trips", "clean/test"], ["Sign circuit", "upgrade request", "excluded"]], 66)
        elif title == "Recoverable Depreciation Schedule":
            draw_ledger(d, 90, 250, [380, 260, 420], [["Item group", "Recoverable", "Condition"], ["Building depreciation", "$1,381.20", "after completed repair invoices"], ["Contents", "$0.00", "ACV only"], ["Tenant sign", "$0.00", "upgrade excluded"], ["Deadline", "2026-12-18", "180 days from loss"]], 66)
        else:
            draw_ledger(d, 90, 250, [360, 260, 470], [["Control value", "Amount", "Meaning"], ["Initial ACV payment", "$8,325.80", "current payable amount"], ["Recoverable depreciation", "$1,381.20", "available after completed repair invoices"], ["Excluded / denied", "$1,560.00", "documented exclusions"], ["Final deadline", "2026-12-18", "recoverable depreciation claim"]], 66)
            draw_ledger(d, 90, 720, [260, 260, 260, 360], [["Payment event", "Date", "Amount", "Status"], ["Advance issued", "2026-06-21", "$3,000.00", "deducted from ACV draft"], ["ACV draft approved", "2026-06-29", "$8,325.80", "current payment"], ["Depreciation holdback", "until invoices", "$1,381.20", "recoverable"], ["Excluded items", "final", "$1,560.00", "no payment"]], 62)
            draw_note(d, (95, 1240, 1510, 1435), "Settlement-control note", "The advance is visible payment history, not an additional amount owed. The current controlling payable amount remains the ACV draft of $8,325.80.", "#991b1b")
        pages.append(p)
    gold = "\n\n".join([
        "# Granite Mutual Claim CL-8827 Adjustment Packet",
        "Insured Harbor Books LLC, loss date 2026-06-18. The final payment worksheet controls: initial ACV payment $8,325.80, recoverable depreciation $1,381.20 after repairs, and excluded/denied $1,560.00.",
        "## Rooms\n" + md_table(["Room", "Zone", "Moisture", "Smoke", "Disposition"], rooms[1:]),
        "## Floor Plan\nZones: A Retail floor, B Stock room, C Office, D Electrical closet, E Restroom. Sprinkler head is over the A/B wall. Smoke path moves from A into C. Electrical closet D requires inspection but not replacement.",
        "## Photos\n" + md_table(["Photo", "Visible cue", "Coverage state"], photo_rows[1:]),
        "## Estimate Lines 1-5\n" + md_table(["Line", "Area", "Description", "Qty", "Unit", "RCV", "ACV"], estimate1[1:]),
        "## Estimate Lines 6-10\n" + md_table(["Line", "Area", "Description", "Qty", "Unit", "RCV", "ACV"], estimate2[1:]),
        "## Contents\n" + md_table(["Item", "Qty", "Claimed", "Allowed", "Reason"], contents_rows[1:]),
        "## Payment Worksheet\n" + md_table(["Bucket", "Amount", "State"], payments[1:]),
    ])
    facts = [
        fact("p19.final.payment", "source_state", 12, "Final payment worksheet controls: Building RCV $10,452.00, depreciation ($1,381.20), Building ACV $9,070.80, contents allowed $1,755.00, deductible ($2,500.00), initial ACV payment $8,325.80, recoverable depreciation $1,381.20, excluded/denied $1,560.00.", modality="source-precedence", severity="critical"),
        fact("p19.rooms", "table_cell", 9, "Room summary preserves all five zones A-E with room names, moisture, smoke, and disposition.", modality="table", severity="critical"),
        fact("p19.floorplan", "visual_relation", 10, "Floor plan preserves zone positions/relations: sprinkler over A/B wall, smoke path from A into C, electrical closet D inspection but not replacement.", modality="visual", severity="critical"),
        fact("p19.photos", "visual_relation", 10, "Photo contact sheet preserves P1-P6 cues and coverage states, especially P3 pre-existing excluded and P5 sign upgrade excluded.", modality="visual", severity="critical"),
        fact("p19.estimate1", "table_cell", 8, "Estimate lines 1-5 preserve areas, descriptions, quantities, units, RCV, and ACV.", modality="table", severity="major"),
        fact("p19.estimate2", "table_cell", 9, "Estimate lines 6-10 preserve HEPA, clean/seal, dehumidifier, shelving detach/reset, and excluded tenant signage upgrade with ACV $0.00.", modality="table", severity="critical"),
        fact("p19.contents", "table_cell", 9, "Contents review preserves claimed vs allowed amounts and reasons, including card reader docks not damaged and tenant sign upgrade denied.", modality="table", severity="critical"),
        fact("p19.electrical", "table_cell", 7, "Electrical report preserves soot at closet D panel covered for inspection, main breaker no arcing/no replacement, A-east GFCI clean/test, sign circuit upgrade excluded.", modality="table", severity="major"),
        fact("p19.depreciation", "source_state", 7, "Recoverable depreciation is $1,381.20 after completed repair invoices by 2026-12-18; contents and tenant sign have $0 recoverable.", modality="source-precedence", severity="critical"),
        fact("p19.no.excluded.payment", "source_state", 8, "Output must not include tenant signage upgrade or card-reader docks in the paid ACV amount; they remain visible excluded context.", modality="source-precedence", severity="critical"),
    ]
    return Case("P19-property-loss-adjustment", "Commercial Property Loss Adjustment Packet", "property-insurance", ["multi-page", "insurance", "floorplan", "photos", "estimate", "source-precedence"], "Stress property claim adjustment with floor-plan relations, photo exclusions, continuation estimate lines, coverage states, and final payment math.", "Fourteen-page commercial property claim packet with room map, photo sheet, estimate continuation, contents review, electrical report, payment worksheet, and settlement recap.", ["floor plan", "photo contact sheet", "estimate continuation", "contents", "payment worksheet"], ["Use local tables, visual coverage states, and final-payment context."], gold, [near_check("p19-payment", "source_state", ["$8,325.80", "$1,381.20", "$1,560.00", "tenant sign"], 8, 900)], pages, facts=facts)


def packet_utility_outage_restoration() -> Case:
    def page(title: str) -> Image.Image:
        img = Image.new("RGB", (PAGE_W, PAGE_H), "#fbfdff")
        d = ImageDraw.Draw(img)
        d.text((72, 54), "MetroGrid Electric | Outage investigation OI-26-731 | Feeder 12R", fill="#334155", font=F["tiny_bold"])
        d.text((72, 90), title, fill="#111827", font=F["h1"])
        d.line((72, 148, 1585, 148), fill="#1f2937", width=2)
        return img

    alarm_rows = [["Time", "Device", "State", "Note"], ["15:42:11", "R12 breaker", "trip", "phase B ground"], ["15:42:14", "Recloser 12R-3", "lockout", "third shot"], ["15:42:19", "Relay 50G", "pickup", "7.8 kA momentary"], ["15:43:02", "Cap bank CB-4", "offline", "voltage sag"], ["15:44:33", "OMS", "8,960 out", "nested outage created"], ["16:05:20", "Switch S-18", "opened", "crew isolation"], ["16:31:05", "Switch S-22", "opened", "Riverside isolated"], ["17:11:00", "DER-44", "0 kW", "curtailment verified"], ["17:18:44", "Tie T-7", "closed", "backfeed hospital"], ["18:05:02", "F-12B", "replaced", "Maple lateral test passed"], ["19:06:10", "R12 breaker", "closed", "normal restored"]]
    switch_rows = [["Step", "Time", "Action", "Crew", "Customers restored"], ["1", "16:05", "open S-18", "Crew A", "0"], ["2", "16:31", "open S-22", "Crew B", "0"], ["3", "16:47", "test Maple lateral", "Crew A", "0"], ["4", "17:11", "verify DER-44 at 0 kW", "Control", "0"], ["5", "17:18", "close T-7", "Crew C", "4,820"], ["6", "18:05", "replace cutout F-12B", "Crew A", "6,140"], ["7", "18:42", "patrol Riverside taps", "Crew B", "6,140"], ["8", "19:06", "close R12 breaker", "Control", "8,960"], ["9", "19:32", "normalize T-7", "Crew C", "all stable"]]
    feeder_rows = [["Node", "Relation", "Status"], ["Substation Bay R12", "feeds 12R trunk", "tripped then restored"], ["S-18", "upstream sectionalizer", "opened for isolation"], ["F-12B", "tap fuse to Maple lateral", "failed cutout"], ["T-7", "tie to feeder 9Q", "closed for hospital backfeed"], ["Hospital loop", "critical load", "restored 17:18"], ["PV site DER-44", "backfeed risk", "curtailed before close"]]
    calls = [["Segment", "Customers", "Critical load / note", "Restored"], ["Maple lateral", "2,820", "0", "18:05"], ["Maple care home spur", "86", "assisted living", "18:05"], ["Hospital loop", "1,240", "1 hospital", "17:18"], ["Riverside apartments", "3,100", "2 elevators", "19:06"], ["Industrial park", "1,800", "0", "19:06"], ["Traffic signal cabinet TS-12", "1 service", "intersection", "17:18"], ["Lift station LS-4", "1 service", "wastewater", "19:06"]]
    customer_notice_rows = [["Recipient", "Segment", "Time", "Method", "Message state"], ["Hospital facility desk", "Hospital loop", "16:04", "phone", "ETA pending"], ["Hospital facility desk", "Hospital loop", "17:21", "phone", "restored via T-7"], ["City traffic", "TS-12", "17:25", "radio", "signal power back"], ["Wastewater duty officer", "LS-4", "18:18", "phone", "awaiting feeder close"], ["Industrial park contact", "Industrial park", "19:09", "email", "normal restored"], ["Care home manager", "Maple care home spur", "18:08", "phone", "restored after F-12B change"]]
    cause_rows = [["Evidence", "Visible value", "Finding"], ["Weather radar", "cell passed 15:36-15:50", "wind gust context"], ["Patrol photo P1", "char mark at F-12B", "failed cutout"], ["Patrol photo P2", "clear span; no branch contact", "tree cause superseded"], ["SCADA", "phase B ground", "matches F-12B"], ["Relay oscillography", "single phase-to-ground impulse", "not lightning signature"], ["DER log", "DER-44 curtailed 17:11", "safe backfeed"], ["Cutout tag", "F12B-882 polymer barrel split", "removed for lab"], ["Draft report", "tree contact", "superseded"], ["Final report", "failed polymer cutout F-12B", "controls"]]
    der_check_rows = [["Clearance item", "Operator entry", "Field confirmation", "Release state"], ["DER-44 disconnect", "open 17:06", "visible at POI", "accepted"], ["SCADA output", "0 kW at 17:11", "telemetry stable 5 min", "accepted"], ["Feeder 9Q load", "74% after transfer", "under emergency rating", "accepted"], ["Reverse power", "none", "relay 67P clear", "accepted"], ["Hospital ATS", "normal source lost", "T-7 source accepted", "accepted"], ["T-7 permission", "issued 17:16", "close allowed 17:18", "accepted"], ["DER restore", "after normalize", "19:34 call to site", "deferred"], ["Site acknowledgment", "R. Valdez 19:36", "DER owner confirms", "logged"]]
    draft_delta_rows = [["Revision item", "Draft entry", "Reviewer mark", "Final treatment"], ["Cause", "tree contact", "crossed in red", "failed polymer cutout F-12B"], ["Hospital restore", "18:05", "circled time mismatch", "17:18 via T-7"], ["DER status", "not mentioned", "blue margin note", "curtailed 17:11"], ["Weather", "primary cause", "downgraded", "context only"], ["Photo P2", "not referenced", "added by reviewer", "no tree contact"]]
    signoff_rows = [["Review gate", "Owner", "Visible state", "Exception"], ["Ops sequence", "N. Ortega", "signed 09:12", "none"], ["Protection review", "R. Mehta", "signed 10:44", "F-12B curve attached"], ["Regulatory review", "S. Kim", "signed 11:20", "major-event no"], ["Vegetation review", "Tree crew", "blank", "not required"], ["DER review", "A. Patel", "initialed 10:58", "restore after normalize"]]
    notice_route_rows = [["Recipient", "Channel", "Due / sent", "Payload note"], ["Hospital liaison", "phone", "sent 17:21", "backfeed restored"], ["City OEM", "email", "sent 18:12", "critical customer update"], ["State PUC log", "portal", "due 2026-07-05 12:00", "below major threshold"], ["Internal claims", "ticket", "sent 2026-07-03 08:40", "equipment failure category"], ["DER owner", "phone", "sent 19:34", "normalization complete"], ["Asset engineering", "work order", "sent 2026-07-03 09:05", "F12B-882 lab teardown"], ["Vegetation contractor", "no dispatch", "not required", "P2 ruled out tree contact"]]
    recap_kpi_rows = [["Metric", "Final value", "Source", "Reviewer note"], ["CAIDI window", "3h 24m", "OMS export", "exclude 19:32 normalize"], ["Critical restoration", "95 minutes", "T-7 close", "hospital priority"], ["Customers interrupted", "8,960", "OMS", "same as overview"], ["Cause code", "equipment failure", "final report", "not weather"], ["Follow-up WO", "WO-7714", "asset replacement", "cutout audit route"]]
    pages: list[Image.Image] = []
    p = page("Outage Overview and Restoration State")
    d = ImageDraw.Draw(p)
    draw_kv_band(d, 82, 205, [("Outage", "OI-26-731"), ("Feeder", "12R"), ("Start", "2026-07-02 15:42"), ("Normal", "19:06"), ("Customers", "8,960")], [220, 160, 300, 180, 190])
    draw_note(d, (90, 370, 1510, 545), "Final cause", "Final investigation identifies failed polymer cutout F-12B on Maple lateral. Early draft tree-contact note is superseded but remains visible context.", "#991b1b")
    draw_ledger(d, 95, 660, [260, 260, 480], [["Metric", "Value", "Note"], ["Hospital restored", "17:18", "via T-7 backfeed"], ["All normal", "19:06", "R12 closed"], ["DER-44", "curtailed 17:11", "before T-7 close"], ["Cause", "F-12B failed cutout", "not tree contact"], ["Cutout tag", "F12B-882", "sent to asset lab"], ["Critical notices", "hospital, traffic, LS-4", "tracked in notice log"]], 54)
    pages.append(p)
    for title, rows, widths, note in [
        ("SCADA Alarm Sequence", alarm_rows, [170, 260, 180, 470], "Alarm order matters; R12 trip precedes 12R-3 lockout."),
        ("Switching Log", switch_rows, [90, 150, 360, 180, 260], "Step 3 closes T-7 and restores hospital before full feeder restoration."),
        ("Customer Impact by Segment", calls, [330, 220, 260, 220], "Hospital loop is critical and restored at 17:18."),
        ("Evidence and Cause Table", cause_rows, [300, 360, 430], "Final report supersedes the draft tree-contact note."),
    ]:
        p = page(title)
        d = ImageDraw.Draw(p)
        draw_ledger(d, 80, 235, widths, rows, 48)
        if title == "Customer Impact by Segment":
            draw_ledger(d, 95, 720, [265, 220, 160, 160, 300], customer_notice_rows, 46)
        if title == "Evidence and Cause Table":
            draw_ledger(d, 95, 800, [250, 240, 260, 360], [["Lab item", "Serial / tag", "Disposition", "Reviewer"], ["Cutout barrel", "F12B-882", "polymer split; archive sample", "Protection"], ["Fuse link", "Kearney 65K", "melt pattern consistent", "Asset Eng"], ["Crossarm mark", "none", "no flashover trace", "Patrol"], ["Tree sample", "not collected", "not applicable", "Vegetation"]], 52)
        draw_note(d, (90, 1260, 1510, 1440), "Control note", note, "#334155")
        pages.append(p)
    p = page("Feeder One-Line Diagram")
    d = ImageDraw.Draw(p)
    nodes = [("R12 bay", 120, 420), ("S-18", 360, 420), ("F-12B", 600, 420), ("S-22", 840, 420), ("Riverside", 1080, 420), ("T-7 tie", 840, 700), ("Hospital loop", 1080, 700), ("DER-44 PV", 600, 700)]
    for label, x, y in nodes:
        d.rounded_rectangle((x, y, x + 170, y + 90), radius=8, fill="#f8fafc", outline="#334155", width=3)
        draw_text(d, (x + 15, y + 28), label, F["tiny_bold"], width=14, leading=20)
    for a, b in [(0,1),(1,2),(2,3),(3,4),(3,5),(5,6),(2,7)]:
        x1,y1=nodes[a][1]+170,nodes[a][2]+45
        x2,y2=nodes[b][1],nodes[b][2]+45
        if nodes[b][2] != nodes[a][2]:
            x1=nodes[a][1]+85; y1=nodes[a][2]+90; x2=nodes[b][1]+85; y2=nodes[b][2]
        d.line((x1,y1,x2,y2), fill="#111827", width=4)
    d.text((610, 350), "fault", fill="#991b1b", font=F["tiny_bold"])
    draw_ledger(d, 120, 1010, [260, 360, 360], feeder_rows, 56)
    draw_ledger(d, 120, 1395, [240, 250, 250, 420], [["Switch / device", "Normal", "During outage", "Field tag"], ["S-18", "closed", "opened 16:05", "yellow hold card"], ["S-22", "closed", "opened 16:31", "visible open blade"], ["T-7", "open", "closed 17:18", "red backfeed tag"], ["DER-44", "online", "0 kW curtailed 17:11", "SCADA clearance"], ["F-12B", "energized", "failed / replaced", "char mark photo P1"]], 54)
    pages.append(p)
    p = page("Restoration Chart and Weather Panel")
    d = ImageDraw.Draw(p)
    d.rectangle((120, 260, 1420, 760), outline="#334155", width=2)
    pts=[("15:42",0),("16:31",0),("17:18",4820),("18:05",6140),("19:06",8960),("19:32",8960)]
    prev=None
    for i,(t,v) in enumerate(pts):
        x=180+i*230; y=700-int(v/8960*360)
        d.ellipse((x-7,y-7,x+7,y+7), fill="#2563eb")
        d.text((x-30,720),t,fill="#475569",font=F["tiny"])
        d.text((x-34,y-32),str(v),fill="#111827",font=F["tiny_bold"])
        if prev: d.line((prev[0],prev[1],x,y),fill="#2563eb",width=4)
        prev=(x,y)
    draw_ledger(d, 120, 920, [260, 260, 420], [["Weather item", "Value", "Interpretation"], ["Radar cell", "15:36-15:50", "context only"], ["Peak gust", "46 mph", "contributed stress"], ["Lightning", "none within 5 miles", "not cause"], ["Tree ticket", "draft only", "superseded by F-12B finding"]], 58)
    pages.append(p)
    for title in ["Crew Patrol Photo Sheet", "DER Backfeed Clearance", "Draft Report Excerpt", "Final Investigation Signoff", "Regulatory Notice", "Final Restoration Recap"]:
        p = page(title)
        d = ImageDraw.Draw(p)
        if title == "Crew Patrol Photo Sheet":
            draw_text(d, (90, 220), "Patrol images are stored in the field-media repository. This regulatory copy carries the photo register, GPS/time metadata, reviewer notes, and disposition used for cause determination.", F["small"], width=104, leading=30)
            draw_ledger(d, 90, 365, [110, 260, 210, 260, 420], [["Photo", "File", "GPS / time", "Reviewer note", "Use"], ["P1", "MG-12R-731-P1", "45.5221,-122.681 / 16:18", "F-12B char mark", "supports failed cutout"], ["P2", "MG-12R-731-P2", "45.5224,-122.680 / 16:23", "clear span; no tree contact", "supersedes draft tree cause"], ["P3", "MG-12R-731-P3", "S-18 / 16:31", "open tag visible", "isolation evidence"], ["P4", "MG-12R-731-P4", "T-7 / 17:18", "red backfeed tag visible", "hospital restoration evidence"]], 64)
            draw_ledger(d, 90, 825, [260, 260, 260, 360], [["Evidence question", "Photo reference", "Finding", "Final treatment"], ["Was a tree touching the line?", "P2", "No", "draft cause superseded"], ["Where is the failed device?", "P1", "F-12B cutout", "final cause"], ["Was S-18 isolated?", "P3", "open tag", "confirmed"], ["Was T-7 used for hospital?", "P4", "backfeed tag", "confirmed"]], 62)
            draw_note(d, (95, 1290, 1510, 1470), "Media-register note", "The field-media files are not printed in this copy, but the photo register and reviewer notes are part of the signed evidence packet.", "#334155")
        elif title == "DER Backfeed Clearance":
            draw_ledger(d, 90, 250, [280, 280, 380], [["Check", "Value", "State"], ["DER-44 output", "0 kW at 17:11", "curtailed"], ["Visible open point", "S-22 open", "confirmed"], ["T-7 close", "17:18", "allowed after clearance"], ["Reverse power alarm", "none", "safe"]], 64)
            draw_ledger(d, 90, 690, [285, 260, 340, 230], der_check_rows, 58)
            draw_note(d, (95, 1265, 1510, 1445), "Clearance-control note", "The T-7 close is valid only after both SCADA output and field-visible disconnect are accepted. DER restore is deferred until after feeder normalization.", "#334155")
        elif title == "Draft Report Excerpt":
            draw_ledger(d, 90, 250, [320, 350, 420], [["Draft field", "Draft value", "Final value"], ["Cause", "tree contact", "failed polymer cutout F-12B"], ["Hospital restore", "18:05", "17:18"], ["DER status", "not mentioned", "curtailed 17:11"]], 66)
            draw_ledger(d, 90, 610, [260, 260, 270, 360], draft_delta_rows, 60)
            draw_note(d, (95, 1180, 1510, 1370), "Revision-control note", "This draft excerpt remains in the packet to show the reviewer corrections. The final investigation signoff controls cause, hospital restoration time, and DER status.", "#991b1b")
        elif title == "Final Investigation Signoff":
            draw_ledger(d, 90, 250, [300, 260, 420], [["Signer", "Role", "Visible state"], ["N. Ortega", "Distribution Ops", "signed 2026-07-03 09:12"], ["R. Mehta", "Protection Eng", "signed 2026-07-03 10:44"], ["S. Kim", "Regulatory", "signed 2026-07-03 11:20"], ["Tree crew", "not required", "blank"]], 66)
            draw_ledger(d, 90, 720, [250, 220, 260, 360], signoff_rows, 62)
            draw_note(d, (95, 1285, 1510, 1455), "Signature interpretation", "The blank tree-crew line is intentional because vegetation was ruled out. DER review is initialed separately because backfeed clearance controlled the T-7 operation.", "#334155")
        elif title == "Regulatory Notice":
            draw_ledger(d, 90, 250, [300, 260, 450], [["Field", "Value", "Note"], ["Major event", "No", "below threshold"], ["Critical customer", "1 hospital", "restored 17:18"], ["Notice due", "2026-07-05 12:00", "internal"], ["Cause category", "equipment failure", "polymer cutout"]], 66)
            draw_ledger(d, 90, 715, [260, 220, 300, 360], notice_route_rows, 62)
            draw_note(d, (95, 1275, 1510, 1450), "Notice-routing note", "The PUC portal item is due even though the incident is below the major-event threshold. Hospital liaison notice was already sent after T-7 restoration.", "#334155")
        else:
            draw_ledger(d, 90, 250, [340, 300, 440], [["Control item", "Final state", "Evidence"], ["Cause", "failed F-12B cutout", "patrol photo + SCADA"], ["Hospital", "restored 17:18", "T-7 backfeed"], ["All customers", "restored 19:06", "R12 breaker close"], ["Draft tree contact", "superseded", "no tree contact photo"], ["DER-44", "curtailed 17:11", "safe backfeed"]], 66)
            draw_ledger(d, 90, 795, [240, 240, 260, 360], recap_kpi_rows, 62)
            draw_note(d, (95, 1355, 1510, 1535), "Recap-control note", "The 19:32 normalization step is operating cleanup, not customer restoration. Customer restoration stops at the 19:06 R12 breaker close.", "#334155")
        pages.append(p)
    gold = "\n\n".join([
        "# MetroGrid Outage OI-26-731 Feeder 12R",
        "Outage started 2026-07-02 15:42 and normal restoration was at 19:06 for 8,960 customers. Final cause is failed polymer cutout F-12B, not the draft tree-contact note. Cutout tag F12B-882 was sent to the asset lab.",
        "## SCADA Alarm Sequence\n" + md_table(["Time", "Device", "State", "Note"], alarm_rows[1:]),
        "## One-Line Diagram\nR12 bay feeds S-18, F-12B, S-22, Riverside, T-7 tie, Hospital loop, and DER-44 PV. F-12B is the fault point. T-7 ties to feeder 9Q and backfeeds the hospital after DER-44 is curtailed.",
        "## Switching\n" + md_table(["Step", "Time", "Action", "Crew", "Customers restored"], switch_rows[1:]),
        "## Customer Impact\n" + md_table(["Segment", "Customers", "Critical load / note", "Restored"], calls[1:]) + "\n\nCritical customer notifications:\n" + md_table(customer_notice_rows[0], customer_notice_rows[1:]),
        "## Evidence\n" + md_table(["Evidence", "Visible value", "Finding"], cause_rows[1:]) + "\n\nLab disposition: cutout barrel F12B-882 has polymer split and is archived by Protection; Kearney 65K fuse link has melt pattern consistent and is reviewed by Asset Engineering; crossarm has no flashover trace; tree sample was not collected because vegetation was not applicable.",
        "## Crew Patrol Photo Sheet\nThe field-media register preserves P1 F-12B char mark supporting failed cutout, P2 clear span/no tree contact superseding the draft tree cause, P3 S-18 open tag, and P4 T-7 backfeed tag.",
        "## DER Backfeed Clearance\n" + md_table(["Check", "Value", "State"], [["DER-44 output", "0 kW at 17:11", "curtailed"], ["Visible open point", "S-22 open", "confirmed"], ["T-7 close", "17:18", "allowed after clearance"], ["Reverse power alarm", "none", "safe"]]) + "\n" + md_table(der_check_rows[0], der_check_rows[1:]) + "\nThe T-7 close is valid only after SCADA output, field-visible disconnect, feeder 9Q load, hospital ATS state, and reverse-power relay are accepted. DER restore is deferred until after feeder normalization and site acknowledgment by R. Valdez at 19:36.",
        "## Draft Report Excerpt\n" + md_table(["Draft field", "Draft value", "Final value"], [["Cause", "tree contact", "failed polymer cutout F-12B"], ["Hospital restore", "18:05", "17:18"], ["DER status", "not mentioned", "curtailed 17:11"]]) + "\n" + md_table(draft_delta_rows[0], draft_delta_rows[1:]) + "\nThis draft excerpt remains visible context, but the final investigation signoff controls cause, hospital restoration time, and DER status.",
        "## Final Investigation Signoff\n" + md_table(["Signer", "Role", "Visible state"], [["N. Ortega", "Distribution Ops", "signed 2026-07-03 09:12"], ["R. Mehta", "Protection Eng", "signed 2026-07-03 10:44"], ["S. Kim", "Regulatory", "signed 2026-07-03 11:20"], ["Tree crew", "not required", "blank"]]) + "\n" + md_table(signoff_rows[0], signoff_rows[1:]) + "\nThe blank tree-crew line is intentional because vegetation was ruled out.",
        "## Regulatory Notice\n" + md_table(["Field", "Value", "Note"], [["Major event", "No", "below threshold"], ["Critical customer", "1 hospital", "restored 17:18"], ["Notice due", "2026-07-05 12:00", "internal"], ["Cause category", "equipment failure", "polymer cutout"]]) + "\n" + md_table(notice_route_rows[0], notice_route_rows[1:]) + "\nThe PUC portal item is due even though the incident is below the major-event threshold. Asset engineering receives work order follow-up for F12B-882; vegetation contractor is not dispatched because P2 ruled out tree contact.",
        "## Final Restoration Recap\n" + md_table(["Control item", "Final state", "Evidence"], [["Cause", "failed F-12B cutout", "patrol photo + SCADA"], ["Hospital", "restored 17:18", "T-7 backfeed"], ["All customers", "restored 19:06", "R12 breaker close"], ["Draft tree contact", "superseded", "no tree contact photo"], ["DER-44", "curtailed 17:11", "safe backfeed"]]) + "\n" + md_table(recap_kpi_rows[0], recap_kpi_rows[1:]) + "\nThe 19:32 normalization step is operating cleanup, not customer restoration. Customer restoration stops at the 19:06 R12 breaker close.",
    ])
    facts = [
        fact("p20.final.cause", "source_state", 12, "Final cause is failed polymer cutout F-12B on Maple lateral; draft tree-contact cause is superseded.", modality="source-precedence", severity="critical"),
        fact("p20.scada.heading", "text", 5, "The alarm section/page title is exactly SCADA Alarm Sequence; it must not be misquoted as SCALAR or another word.", modality="text", severity="major"),
        fact("p20.alarms", "table_cell", 10, "SCADA alarm sequence preserves all times/devices/states/notes from 15:42:11 R12 trip, 15:42:14 12R-3 lockout, 15:42:19 relay 50G pickup 7.8 kA, 15:44:33 OMS 8,960 out, DER-44 0 kW at 17:11, T-7 closed 17:18:44, F-12B replaced 18:05:02, through 19:06:10 R12 breaker closed.", modality="table", severity="critical"),
        fact("p20.oneline", "visual_relation", 10, "One-line diagram preserves R12->S-18->F-12B->S-22/Riverside with T-7 tie to hospital loop and DER-44 PV backfeed risk.", modality="visual", severity="critical"),
        fact("p20.switching", "table_cell", 10, "Switching log preserves nine steps, times, actions, crews, and restored customer counts, including Maple lateral test at 16:47, DER-44 verification at 17:11, T-7 close at 17:18 restoring 4,820, Riverside patrol at 18:42, R12 close at 19:06 restoring 8,960, and T-7 normalize at 19:32.", modality="table", severity="critical"),
        fact("p20.restoration.chart", "chart", 8, "Restoration chart preserves customer counts by time: 0 at 15:42/16:31, 4,820 at 17:18, 6,140 at 18:05, 8,960 at 19:06/19:32.", modality="chart", severity="critical"),
        fact("p20.customer.segments", "table_cell", 10, "Customer impact preserves Maple lateral 2,820 restored 18:05, Maple care home spur 86 assisted living restored 18:05, hospital loop 1,240/1 hospital restored 17:18, Riverside apartments 3,100/2 elevators restored 19:06, industrial park 1,800 restored 19:06, traffic signal cabinet TS-12 restored 17:18, and lift station LS-4 restored 19:06.", modality="table", severity="critical"),
        fact("p20.customer.notifications", "source_state", 8, "Critical customer notifications preserve hospital facility desk calls at 16:04 ETA pending and 17:21 restored via T-7, City traffic radio 17:25 signal power back, wastewater duty officer 18:18 awaiting feeder close, industrial park email 19:09 normal restored, and care home manager 18:08 restored after F-12B change.", modality="source-precedence", severity="critical"),
        fact("p20.photos", "visual_relation", 7, "Patrol photo sheet preserves P1 F-12B char mark, P2 no tree contact, P3 S-18 open tag, and P4 T-7 closed tag.", modality="visual", severity="major"),
        fact("p20.der", "source_state", 8, "DER-44 was curtailed to 0 kW at 17:11 before T-7 close at 17:18; no reverse power alarm occurred.", modality="source-precedence", severity="critical"),
        fact("p20.cause.evidence.detail", "visual_relation", 9, "Cause evidence preserves P1 F-12B char mark, P2 clear span/no branch contact, relay oscillography single phase-to-ground impulse not lightning signature, cutout tag F12B-882 polymer barrel split, Kearney 65K fuse link melt pattern consistent, crossarm no flashover trace, and no tree sample collected.", modality="visual", severity="critical"),
        fact("p20.der.clearance.detail", "source_state", 10, "DER clearance detail preserves DER-44 disconnect open 17:06, SCADA output 0 kW at 17:11 stable 5 min, feeder 9Q load 74% under emergency rating, relay 67P reverse-power clear, hospital ATS accepted T-7 source, T-7 permission issued 17:16/close allowed 17:18, DER restore deferred after normalize, and R. Valdez site acknowledgment at 19:36.", modality="source-precedence", severity="critical"),
        fact("p20.draft.delta", "source_state", 9, "Draft report excerpt preserves draft-to-final changes: tree contact crossed out to failed F-12B cutout, hospital restore 18:05 corrected to 17:18, DER status not mentioned corrected to curtailed 17:11, weather downgraded to context only, and photo P2 added as no tree contact.", modality="source-precedence", severity="critical"),
        fact("p20.signoff", "form_state", 6, "Final signoff preserves N. Ortega, R. Mehta, S. Kim signed timestamps and Tree crew not required/blank.", modality="form", severity="major"),
        fact("p20.signoff.gates", "form_state", 7, "Final review gates preserve Ops/Protection/Regulatory signed states, Tree crew blank/not required, and DER review initialed by A. Patel at 10:58 with restore after normalize.", modality="form", severity="major"),
        fact("p20.regulatory", "source_state", 7, "Regulatory notice preserves major event No, one critical customer hospital restored 17:18, notice due 2026-07-05 12:00, cause category equipment failure.", modality="source-precedence", severity="major"),
        fact("p20.notice.routing", "source_state", 7, "Regulatory notice routing preserves hospital liaison phone sent 17:21, City OEM email sent 18:12, State PUC portal due 2026-07-05 12:00, internal claims ticket sent 2026-07-03 08:40, DER owner phone sent 19:34, asset engineering work order sent 2026-07-03 09:05 for F12B-882 lab teardown, and vegetation contractor no-dispatch/not required because P2 ruled out tree contact.", modality="source-precedence", severity="major"),
        fact("p20.final.recap.kpi", "source_state", 8, "Final recap preserves CAIDI window 3h 24m excluding 19:32 normalize, critical restoration 95 minutes, 8,960 customers interrupted, cause code equipment failure/not weather, and follow-up WO-7714.", modality="source-precedence", severity="critical"),
    ]
    return Case("P20-utility-outage-restoration", "Utility Outage Restoration Packet", "utility-incident", ["multi-page", "utility", "one-line-diagram", "scada", "crew-log", "chart", "source-precedence"], "Stress utility incident packet with one-line network relations, alarm order, switching log, restoration chart, crew photo evidence, DER safety, and superseded draft cause.", "Thirteen-page outage packet with SCADA alarms, feeder one-line, switching log, restoration chart, weather panel, patrol photos, DER clearance, draft/final reports, and regulatory notice.", ["SCADA", "one-line", "switching", "restoration chart", "DER", "final cause"], ["Use alarm order, visual relations, and final investigation context."], gold, [near_check("p20-final", "source_state", ["F-12B", "tree contact", "superseded", "17:18", "19:06"], 8, 900)], pages, facts=facts)


def packet_semiconductor_lot_disposition() -> Case:
    def page(title: str, subtitle: str = "Aster Microdevices | Fab 3 | Lot Q8R7-22 disposition file") -> Image.Image:
        img = Image.new("RGB", (PAGE_W, PAGE_H), "#ffffff")
        d = ImageDraw.Draw(img)
        d.text((70, 52), subtitle, fill="#334155", font=F["tiny_bold"])
        d.text((70, 88), title, fill="#111827", font=F["h1"])
        d.line((70, 148, 1588, 148), fill="#111827", width=2)
        d.text((1405, 54), "MRB COPY", fill="#7f1d1d", font=F["tiny_bold"])
        return img

    wafers = [
        ["01", "18,420", "0.83", "97.8", "release", "center-edge normal"],
        ["02", "18,216", "0.86", "97.1", "release", "one edge cluster"],
        ["03", "17,604", "1.24", "93.8", "hold", "map quadrant B4"],
        ["04", "18,390", "0.81", "97.6", "release", "normal"],
        ["05", "17,118", "1.42", "91.9", "hold", "scratch arc"],
        ["06", "18,275", "0.88", "96.9", "release", "normal"],
        ["07", "16,902", "1.58", "90.6", "scrap", "metal flakes"],
        ["08", "18,301", "0.79", "97.4", "release", "normal"],
        ["09", "17,880", "1.06", "95.5", "conditional", "param drift"],
        ["10", "18,144", "0.90", "96.8", "release", "normal"],
        ["11", "18,013", "0.95", "96.2", "release", "normal"],
        ["12", "17,422", "1.31", "92.7", "hold", "edge bead"],
    ]
    process = [
        ["Step", "Tool", "Recipe", "Start", "End", "Visible state"],
        ["Implant P3", "IMP-17", "BORON_LVT_042", "05:12", "05:58", "accepted"],
        ["Ash", "ASH-04", "ASH_STD_18", "06:10", "06:34", "accepted"],
        ["Wet clean", "WET-12", "SC1_SC2_09", "06:48", "07:22", "accepted"],
        ["PVD TiN", "PVD-03", "TIN_GATE_31", "08:06", "09:44", "alarm at 09:18"],
        ["Anneal", "RTP-08", "RTP_LVT_22", "10:01", "10:29", "accepted"],
        ["Metrology", "CDSEM-06", "GATE_LVT_QC", "10:45", "11:56", "reviewed"],
    ]
    metrology = [
        ["Wafer", "Site", "CD nm", "Delta", "Flag", "Reviewer note"],
        ["03", "B4", "27.8", "+2.9", "H", "matches map cluster"],
        ["03", "C4", "27.4", "+2.5", "H", "adjacent high"],
        ["05", "E2", "24.1", "-1.8", "L", "scratch path"],
        ["07", "D5", "29.6", "+4.7", "H", "flake shadow"],
        ["07", "D6", "29.1", "+4.2", "H", "flake shadow"],
        ["09", "F3", "26.8", "+1.9", "watch", "param drift only"],
        ["12", "A6", "23.9", "-2.0", "L", "edge bead"],
    ]
    defects = [
        ["Code", "Class", "Count", "Affected wafer", "Disposition"],
        ["M1", "metal flake", "44", "07", "scrap wafer 07"],
        ["S2", "scratch", "31", "05", "hold for review"],
        ["E1", "edge bead", "27", "12", "hold"],
        ["P4", "parametric drift", "19", "09", "conditional release"],
        ["C3", "center cluster", "16", "03", "hold"],
    ]
    defect_actions = [
        ["Gate", "Trigger", "Wafer/site", "Required action", "Owner"],
        ["DCT-1", "M1 count > 20", "W07 D5/D6/E5", "scrap wafer; do not sample for REL", "MRB"],
        ["DCT-2", "S2 scratch crossing active cells", "W05 E2/F2/E3", "engineering hold; inspect sister lot Q8R7-23", "Yield Eng"],
        ["DCT-3", "E1 edge bead two adjacent cells", "W12 A6/B6", "hold pending edge-bead review", "Process Eng"],
        ["DCT-4", "P4 drift with clean SEM image", "W09 F3", "conditional release; REL-22-A required", "Reliability"],
        ["DCT-5", "C3 high-CD cluster", "W03 B4/C4/B5", "hold pending CD remeasure", "Metrology"],
    ]
    spc_rows = [
        ["Run", "Time", "TiN thickness", "Limit state", "Comment"],
        ["R-2241", "08:06", "41.2", "inside", "start"],
        ["R-2242", "08:22", "42.0", "inside", "stable"],
        ["R-2243", "08:38", "43.8", "inside", "rising"],
        ["R-2244", "08:54", "45.6", "warning", "near UCL"],
        ["R-2245", "09:10", "47.4", "above UCL", "alarm follows"],
        ["R-2246", "09:26", "46.2", "warning", "post alarm"],
        ["R-2247", "09:42", "44.1", "inside", "recovered"],
    ]
    spc_interlocks = [
        ["Interlock", "Observed value", "Threshold", "State", "Disposition"],
        ["PVD-03 chamber pressure", "4.8 mTorr", "<=5.0 mTorr", "pass", "not root cause"],
        ["Clamp purge flow", "18.1 slm", ">=19.0 slm", "fail", "future purge increase only"],
        ["Ti target age", "81.4 kWh", "<=85 kWh", "watch", "continue after clean"],
        ["Thickness monitor residual", "+1.7 nm", "+/-1.0 nm", "fail", "drives R-2245 review"],
        ["Alarm acknowledgment", "09:18 by J. Kwon", "required", "complete", "containment clock starts"],
    ]
    recipe_rows = [
        ["Source", "Recipe shown", "Status", "Meaning"],
        ["Traveler page", "TIN_GATE_31", "current", "used for lot"],
        ["Tool alarm printout", "TIN_GATE_30", "stale header", "screen cache"],
        ["MES audit", "TIN_GATE_31", "confirmed", "controls"],
        ["Engineer note", "increase clamp purge", "future only", "not used for this lot"],
    ]
    mrb_rows = [
        ["Item", "Decision", "Reason", "Owner"],
        ["Wafer 07", "scrap", "metal flakes M1 at D5/D6", "Y. Nishida"],
        ["Wafer 05", "hold", "scratch S2 crosses E2-F2", "A. Roy"],
        ["Wafer 03", "hold", "CD high at B4/C4", "M. Alvarez"],
        ["Wafer 12", "hold", "edge bead at A6", "K. Stone"],
        ["Wafer 09", "conditional release", "parametric drift P4, REL sample required", "S. Han"],
        ["Wafers 01,02,04,06,08,10,11", "release", "within disposition limits", "MRB"],
    ]
    reliability_rows = [
        ["Sample", "Wafer", "Stress", "Result", "Use"],
        ["REL-22-A", "09", "HTOL 168h", "pending", "condition for release"],
        ["REL-22-B", "02", "TC 100 cyc", "pass", "reference"],
        ["REL-22-C", "11", "HAST 96h", "pass", "reference"],
        ["REL-22-D", "07", "not built", "scrap", "no reliability credit"],
    ]
    ship_rows = [
        ["Ship bucket", "Wafers", "Die count", "Condition"],
        ["Release now", "01,02,04,06,08,10,11", "127,759", "standard COA"],
        ["Conditional", "09", "17,880", "hold shipment until REL-22-A pass"],
        ["Engineering hold", "03,05,12", "52,144", "do not ship"],
        ["Scrap", "07", "16,902", "do not include in yield"],
    ]

    pages: list[Image.Image] = []

    p = page("Lot Summary and Final MRB State")
    d = ImageDraw.Draw(p)
    draw_kv_band(d, 82, 205, [("Lot", "Q8R7-22"), ("Product", "AMX-4100"), ("Flow", "LVT gate"), ("Lotsize", "12 wafers"), ("MRB", "2026-06-11")], [210, 260, 230, 220, 220])
    draw_note(d, (92, 360, 1510, 545), "Disposition", "Release wafers 01, 02, 04, 06, 08, 10, and 11. Wafer 09 is conditional pending REL-22-A. Wafers 03, 05, and 12 remain on engineering hold. Wafer 07 is scrap and must not be counted in ship yield.", "#7f1d1d")
    draw_ledger(d, 90, 650, [130, 175, 150, 140, 175, 360], [["Wafer", "Good die", "Defect %", "Probe yield", "Final state", "Note"], *wafers], 54)
    pages.append(p)

    p = page("Traveler and Process Route")
    d = ImageDraw.Draw(p)
    draw_ledger(d, 80, 230, [170, 220, 230, 130, 130, 360], process, 66)
    draw_note(d, (95, 790, 1510, 1010), "Route note", "PVD-03 alarm at 09:18 triggered containment. The lot continued to RTP-08 only after engineering released the tool to complete the already-loaded chamber sequence.", "#92400e")
    draw_ledger(d, 95, 1130, [300, 300, 260, 360], recipe_rows, 66)
    pages.append(p)

    p = page("Wafer Map Contact Sheet")
    d = ImageDraw.Draw(p)
    d.text((90, 210), "Each wafer map uses row letters A-F and column numbers 1-6. Filled cells mark reviewed defect clusters; labels show the dominant code at that coordinate.", fill="#334155", font=F["small"])
    maps = {
        "03": [("B", 4, "C3"), ("C", 4, "C3"), ("B", 5, "C3")],
        "05": [("E", 2, "S2"), ("F", 2, "S2"), ("E", 3, "S2")],
        "07": [("D", 5, "M1"), ("D", 6, "M1"), ("E", 5, "M1")],
        "09": [("F", 3, "P4")],
        "12": [("A", 6, "E1"), ("B", 6, "E1")],
        "02": [("A", 1, "E0")],
    }
    row_letters = ["A", "B", "C", "D", "E", "F"]
    for idx, wafer in enumerate(["03", "05", "07", "09", "12", "02"]):
        ox = 90 + (idx % 3) * 500
        oy = 300 + (idx // 3) * 570
        d.text((ox, oy - 42), f"Wafer {wafer}", fill="#111827", font=F["small_bold"])
        d.ellipse((ox, oy, ox + 390, oy + 390), outline="#334155", width=3)
        for r, letter in enumerate(row_letters):
            d.text((ox - 28, oy + 34 + r * 54), letter, fill="#475569", font=F["tiny"])
            for c in range(1, 7):
                x = ox + 45 + (c - 1) * 54
                y = oy + 42 + r * 54
                d.rectangle((x, y, x + 42, y + 42), outline="#cbd5e1", width=1)
                if r == 0:
                    d.text((x + 12, oy - 2), str(c), fill="#475569", font=F["tiny"])
        for letter, col, code in maps[wafer]:
            r = row_letters.index(letter)
            x = ox + 45 + (col - 1) * 54
            y = oy + 42 + r * 54
            fill = {"M1": "#fee2e2", "S2": "#ffedd5", "E1": "#fef9c3", "P4": "#dbeafe", "C3": "#e0e7ff"}.get(code, "#e5e7eb")
            d.rectangle((x, y, x + 42, y + 42), fill=fill, outline="#111827", width=2)
            d.text((x + 4, y + 12), code, fill="#111827", font=F["tiny_bold"])
    draw_ledger(d, 92, 1450, [155, 225, 320, 420], [["Code", "Visual cue", "Critical coordinate", "Disposition link"], ["M1", "red cells", "W07 D5/D6", "scrap"], ["S2", "orange scratch arc", "W05 E2-F2", "engineering hold"], ["E1", "yellow edge", "W12 A6/B6", "engineering hold"], ["P4", "blue drift", "W09 F3", "conditional release"], ["C3", "violet cluster", "W03 B4/C4", "engineering hold"]], 58)
    pages.append(p)

    p = page("CD-SEM Metrology and Flags")
    d = ImageDraw.Draw(p)
    draw_ledger(d, 70, 230, [130, 130, 145, 120, 120, 470], metrology, 58)
    draw_note(d, (95, 800, 1510, 980), "Specification note", "Target gate CD is 24.9 nm with action limits -2.0 nm and +2.5 nm. Sites at or beyond an action limit require MRB disposition even when the wafer-average yield remains above 93%.", "#334155")
    draw_ledger(d, 95, 1100, [280, 320, 300, 300], [["Site group", "Rows affected", "Rule", "Final state"], ["High CD cluster", "W03 B4/C4 and W07 D5/D6", "beyond +2.5 nm", "hold or scrap"], ["Low CD edge", "W05 E2 and W12 A6", "at -1.8/-2.0 nm", "hold"], ["Watch drift", "W09 F3", "+1.9 nm below action", "conditional"]], 70)
    pages.append(p)

    p = page("SPC Trend and PVD Alarm")
    d = ImageDraw.Draw(p)
    d.rectangle((110, 250, 1460, 820), outline="#334155", width=2)
    d.line((170, 735, 1400, 735), fill="#111827", width=2)
    d.line((170, 735, 170, 325), fill="#111827", width=2)
    ucl_y = 735 - int((47.0 - 40.0) / 8.0 * 375)
    warn_y = 735 - int((45.0 - 40.0) / 8.0 * 375)
    for tick, label in [(40, "40"), (42, "42"), (44, "44"), (46, "46"), (48, "48")]:
        gy = 735 - int((tick - 40.0) / 8.0 * 375)
        d.line((170, gy, 1400, gy), fill="#e5e7eb", width=1)
        d.text((125, gy - 12), label, fill="#64748b", font=F["tiny"])
    d.line((170, ucl_y, 1400, ucl_y), fill="#dc2626", width=3)
    d.text((1180, ucl_y - 35), "UCL 47.0", fill="#dc2626", font=F["tiny_bold"])
    d.line((170, warn_y, 1400, warn_y), fill="#f59e0b", width=2)
    d.text((1160, warn_y - 35), "warning 45.0", fill="#b45309", font=F["tiny_bold"])
    pts = []
    for i, row in enumerate(spc_rows[1:]):
        val = float(row[2])
        x = 210 + i * 185
        y = 735 - int((val - 40.0) / 8.0 * 375)
        pts.append((x, y))
        d.ellipse((x - 8, y - 8, x + 8, y + 8), fill="#2563eb")
        d.text((x - 34, 748), row[0], fill="#475569", font=F["tiny"])
        d.text((x - 22, y - 34), row[2], fill="#111827", font=F["tiny_bold"])
    for a, b in zip(pts, pts[1:]):
        d.line((*a, *b), fill="#2563eb", width=4)
    draw_ledger(d, 90, 920, [150, 150, 190, 180, 420], spc_rows, 58)
    draw_note(d, (95, 1450, 1510, 1625), "Alarm interpretation", "R-2245 is above UCL at 47.4 nm and is the only plotted point beyond the red line. R-2244 and R-2246 are warning-state points, not rejects by themselves.", "#7f1d1d")
    draw_ledger(d, 95, 1710, [300, 240, 230, 150, 390], spc_interlocks, 52)
    pages.append(p)

    p = page("Defect Pareto and Classification")
    d = ImageDraw.Draw(p)
    draw_ledger(d, 95, 230, [140, 260, 140, 220, 420], defects, 68)
    d.rectangle((95, 700, 1420, 1150), outline="#334155", width=2)
    max_count = 44
    for i, row in enumerate(defects[1:]):
        x = 160 + i * 230
        h = int(int(row[2]) / max_count * 310)
        d.rectangle((x, 1070 - h, x + 90, 1070), fill=["#dc2626", "#f97316", "#eab308", "#2563eb", "#7c3aed"][i])
        d.text((x, 1085), row[0], fill="#111827", font=F["tiny_bold"])
        d.text((x, 1038 - h), row[2], fill="#111827", font=F["tiny_bold"])
    draw_ledger(d, 95, 1240, [150, 300, 210, 410, 230], defect_actions, 48)
    draw_note(d, (95, 1660, 1510, 1835), "Classification rule", "M1 metal flake is a scrap class when clustered on adjacent D-row sites. S2, E1, and C3 require engineering hold. P4 is allowed only as conditional release with reliability sample.", "#334155")
    pages.append(p)

    for title, rows, note in [
        ("Recipe Source Conflict", recipe_rows, "The tool printout shows TIN_GATE_30 only because its header cache was stale. MES audit confirms TIN_GATE_31 controlled the actual run."),
        ("MRB Disposition Matrix", mrb_rows, "The MRB matrix is the controlling disposition source for wafer-level state."),
        ("Reliability Sample Plan", reliability_rows, "Wafer 09 conditional release depends on REL-22-A HTOL 168h passing; wafer 07 gets no reliability credit because it is scrap."),
        ("Shipping Allocation Worksheet", ship_rows, "Release-now die count excludes wafer 09 until REL-22-A passes and excludes scrap wafer 07 completely."),
    ]:
        p = page(title)
        d = ImageDraw.Draw(p)
        widths = [260, 260, 360, 420] if title != "Shipping Allocation Worksheet" else [280, 360, 220, 480]
        draw_ledger(d, 85, 235, widths, rows, 68)
        draw_note(d, (95, 910, 1510, 1085), "Local note", note, "#334155")
        pages.append(p)

    p = page("Inline Photo Review Register")
    d = ImageDraw.Draw(p)
    photo_rows = [
        ["Frame", "Wafer/site", "Image cue", "Finding", "Disposition link"],
        ["IMG-221", "W07 D5", "bright flake at lower electrode", "M1 metal flake", "scrap W07"],
        ["IMG-222", "W07 D6", "second adjacent flake", "M1 cluster", "scrap W07"],
        ["IMG-223", "W05 E2", "diagonal drag mark", "S2 scratch", "hold W05"],
        ["IMG-224", "W12 A6", "edge residue", "E1 edge bead", "hold W12"],
        ["IMG-225", "W09 F3", "clean image, param high", "P4 electrical drift", "conditional W09"],
    ]
    draw_ledger(d, 80, 230, [150, 180, 350, 240, 320], photo_rows, 68)
    draw_ledger(d, 80, 690, [155, 230, 230, 230, 280], [["Frame", "Focus", "Measured cue", "Disposition impact", "Reviewer mark"], ["IMG-221", "W07 D5", "flake 8.2 um", "scrap support", "red circle / counted"], ["IMG-222", "W07 D6", "flake 6.9 um", "adjacent M1 cluster", "red circle / counted"], ["IMG-223", "W05 E2", "scratch 118 um", "hold support", "orange line / counted"], ["IMG-224", "W12 A6", "edge residue band", "hold support", "yellow bracket"], ["IMG-225", "W09 F3", "no visible particle", "electrical drift only", "blue square / reference"]], 62)
    draw_note(d, (95, 1150, 1510, 1365), "Image archive note", "The SEM image files remain in the fab image archive; this signed packet carries the reviewer marks, measured cues, and disposition links used by MRB. The visual cue column must stay attached to the frame and wafer site.", "#334155")
    pages.append(p)

    p = page("Final Certificate of Analysis Holdback")
    d = ImageDraw.Draw(p)
    coa_rows = [
        ["COA field", "Visible value", "Applies to"],
        ["Lot", "Q8R7-22", "all wafers"],
        ["Released wafers", "01,02,04,06,08,10,11", "ship now"],
        ["Conditional wafer", "09", "ship only after REL-22-A pass"],
        ["Engineering hold", "03,05,12", "excluded from shipment"],
        ["Scrap", "07", "excluded from yield and COA"],
        ["Recipe", "TIN_GATE_31", "MES-confirmed"],
        ["Yield denominator", "released + conditional only", "do not include W07"],
    ]
    draw_ledger(d, 90, 245, [300, 430, 420], coa_rows, 68)
    draw_note(d, (95, 930, 1510, 1125), "Certificate note", "The preliminary COA draft listed wafers 01-12, but the signed COA must list only released wafers and the conditional wafer separately. The draft is not the shipping authority.", "#7f1d1d")
    pages.append(p)

    p = page("Disposition Recap and Audit Trail")
    d = ImageDraw.Draw(p)
    audit_rows = [
        ["Timestamp", "Actor", "Entry", "Effect"],
        ["2026-06-10 12:18", "MES", "PVD alarm attached", "containment starts"],
        ["2026-06-10 14:40", "Yield eng", "wafer map review complete", "W03/W05/W07/W12 flagged"],
        ["2026-06-11 08:55", "MRB", "W07 scrap, W09 conditional", "controls final state"],
        ["2026-06-11 10:20", "Quality", "COA holdback added", "prevents draft all-wafer ship"],
        ["2026-06-11 13:30", "Planning", "ship bucket split", "127,759 die release now"],
    ]
    draw_ledger(d, 85, 240, [260, 210, 410, 360], audit_rows, 66)
    draw_ledger(d, 85, 780, [360, 300, 420], [["Control item", "Final state", "Reason"], ["Ship now", "wafers 01,02,04,06,08,10,11", "released by MRB"], ["Conditional", "wafer 09", "REL-22-A pending"], ["Hold", "wafers 03,05,12", "CD/scratch/edge issues"], ["Scrap", "wafer 07", "M1 metal flake cluster"], ["Recipe conflict", "TIN_GATE_31 controls", "MES audit beats stale printout"]], 70)
    pages.append(p)

    gold = "\n\n".join([
        "# Aster Microdevices Lot Q8R7-22 Disposition File",
        "Product AMX-4100, Fab 3, LVT gate flow, MRB 2026-06-11. Final MRB state: release wafers 01, 02, 04, 06, 08, 10, and 11; wafer 09 is conditional pending REL-22-A; wafers 03, 05, and 12 remain on engineering hold; wafer 07 is scrap and must not be counted in ship yield.",
        "## Wafer Summary\n" + md_table(["Wafer", "Good die", "Defect %", "Probe yield", "Final state", "Note"], wafers),
        "## Traveler and Route\n" + md_table(process[0], process[1:]) + "\nPVD-03 alarm at 09:18 triggered containment. The lot continued to RTP-08 only after engineering released the already-loaded chamber sequence.",
        "## Recipe Source Conflict\n" + md_table(recipe_rows[0], recipe_rows[1:]) + "\nTIN_GATE_31 controls the actual run; TIN_GATE_30 appears only on a stale tool-alarm header.",
        "## Wafer Maps\nWafer 03 has C3 cluster at B4, C4, and B5. Wafer 05 has S2 scratch cells E2, F2, and E3. Wafer 07 has M1 metal-flake cells D5, D6, and E5. Wafer 09 has P4 at F3. Wafer 12 has E1 edge cells A6 and B6. Wafer 02 has one edge-marked A1 cell.",
        "## Metrology\n" + md_table(["Wafer", "Site", "CD nm", "Delta", "Flag", "Reviewer note"], metrology),
        "## SPC Trend\n" + md_table(spc_rows[0], spc_rows[1:]) + "\nR-2245 is above UCL at 47.4 nm. R-2244 and R-2246 are warning-state points but not rejects by themselves.\n\nSPC alarm interlocks:\n" + md_table(spc_interlocks[0], spc_interlocks[1:]),
        "## Defects\n" + md_table(defects[0], defects[1:]) + "\n\nDefect containment actions:\n" + md_table(defect_actions[0], defect_actions[1:]),
        "## Photo Register\nIMG-221 W07 D5 and IMG-222 W07 D6 show M1 metal flakes and support scrap W07. IMG-223 W05 E2 shows S2 scratch and supports hold W05. IMG-224 W12 A6 shows E1 edge bead and supports hold W12. IMG-225 W09 F3 is clean visually but has P4 electrical drift and supports conditional W09.",
        "## MRB Matrix\n" + md_table(["Item", "Decision", "Reason", "Owner"], mrb_rows[1:]),
        "## Reliability and Shipping\n" + md_table(reliability_rows[0], reliability_rows[1:]) + "\n" + md_table(ship_rows[0], ship_rows[1:]),
        "## COA Holdback\nReleased wafers are 01,02,04,06,08,10,11. Conditional wafer 09 ships only after REL-22-A passes. Engineering hold wafers 03,05,12 and scrap wafer 07 are excluded from shipment. Signed COA must not use the preliminary all-wafer draft.",
        "## Audit Trail\n" + md_table(["Timestamp", "Actor", "Entry", "Effect"], audit_rows[1:]),
    ])
    facts = [
        fact("p21.final.disposition", "source_state", 14, "Final MRB state is release wafers 01,02,04,06,08,10,11; wafer 09 conditional pending REL-22-A; wafers 03,05,12 engineering hold; wafer 07 scrap and excluded from ship yield.", modality="source-precedence", severity="critical"),
        fact("p21.wafer.summary", "table_cell", 12, "Wafer summary preserves good die, defect %, probe yield, final state, and notes for all twelve wafers.", modality="table", severity="critical"),
        fact("p21.route", "table_cell", 7, "Traveler route preserves all six process steps/tools/recipes/times/states, including PVD-03 TIN_GATE_31 alarm at 09:18 and metrology reviewed.", modality="table", severity="major"),
        fact("p21.recipe.conflict", "source_state", 10, "Recipe conflict is resolved correctly: TIN_GATE_31 controls from traveler/MES; TIN_GATE_30 is a stale tool printout header; clamp purge change is future only.", modality="source-precedence", severity="critical"),
        fact("p21.wafer.map", "visual_relation", 14, "Wafer map coordinates and defect codes are preserved: W03 B4/C4/B5 C3, W05 E2/F2/E3 S2, W07 D5/D6/E5 M1, W09 F3 P4, W12 A6/B6 E1, W02 A1 edge.", modality="visual", severity="critical"),
        fact("p21.metrology", "table_cell", 10, "CD-SEM metrology preserves wafer/site/CD/delta/flag/reviewer notes for W03 B4/C4, W05 E2, W07 D5/D6, W09 F3, and W12 A6.", modality="table", severity="critical"),
        fact("p21.spec.rule", "source_state", 6, "CD target 24.9 nm and action limits -2.0/+2.5 nm are preserved, including rule that action-limit sites require MRB disposition even above 93% yield.", modality="source-precedence", severity="major"),
        fact("p21.spc.chart", "chart", 12, "SPC trend preserves R-2241 through R-2247 values and states, especially R-2245 47.4 above UCL, R-2244/R-2246 warning, and recovered R-2247 44.1.", modality="chart", severity="critical"),
        fact("p21.spc.interlocks", "table_cell", 10, "SPC interlock table preserves chamber pressure 4.8 mTorr pass/not root cause, clamp purge 18.1 slm below >=19.0 fail/future purge increase only, Ti target age 81.4 kWh watch, thickness monitor residual +1.7 nm fail driving R-2245 review, and alarm acknowledgment 09:18 by J. Kwon complete/containment clock starts.", modality="table", severity="critical"),
        fact("p21.defects", "table_cell", 9, "Defect Pareto preserves codes/classes/counts/affected wafers/dispositions for M1, S2, E1, P4, and C3.", modality="table", severity="critical"),
        fact("p21.defect.actions", "source_state", 10, "Defect containment actions preserve DCT-1 M1 >20 W07 scrap/no REL sample, DCT-2 S2 W05 engineering hold and sister lot Q8R7-23 inspect, DCT-3 E1 W12 hold pending edge-bead review, DCT-4 P4 W09 conditional release requiring REL-22-A, and DCT-5 C3 W03 hold pending CD remeasure.", modality="source-precedence", severity="critical"),
        fact("p21.photo.register", "visual_relation", 9, "Photo review register binds frames to wafer/site/finding/disposition: IMG-221/222 W07 M1 scrap, IMG-223 W05 S2 hold, IMG-224 W12 E1 hold, IMG-225 W09 P4 conditional.", modality="visual", severity="critical"),
        fact("p21.mrb", "source_state", 12, "MRB matrix preserves decisions, reasons, and owners for W07 scrap, W05 hold, W03 hold, W12 hold, W09 conditional release, and release group 01/02/04/06/08/10/11.", modality="source-precedence", severity="critical"),
        fact("p21.reliability", "table_cell", 8, "Reliability plan preserves REL-22-A wafer 09 HTOL 168h pending as condition for release, REL-22-B/C pass references, and REL-22-D wafer 07 not built/scrap/no credit.", modality="table", severity="critical"),
        fact("p21.shipping", "source_state", 10, "Shipping allocation preserves release-now wafers and die count 127,759, conditional W09 17,880, engineering hold W03/W05/W12 52,144, and scrap W07 16,902 excluded.", modality="source-precedence", severity="critical"),
        fact("p21.coa", "source_state", 8, "COA holdback preserves that preliminary all-wafer draft is not shipping authority and signed COA must list released wafers plus conditional wafer separately.", modality="source-precedence", severity="critical"),
        fact("p21.audit", "structure", 6, "Audit trail preserves timestamp/actor/entry/effect sequence from PVD alarm through planning ship-bucket split.", modality="structure", severity="major"),
    ]
    return Case("P21-semiconductor-lot-disposition", "Semiconductor Lot Disposition File", "semiconductor-quality", ["multi-page", "semiconductor", "wafer-map", "spc", "source-precedence", "visual-relation"], "Stress lot-disposition reconstruction with wafer-map coordinates, SPC chart values, recipe conflicts, source precedence, and shipping holdback.", "Thirteen-page semiconductor MRB packet with traveler, wafer maps, metrology, SPC trend, defect Pareto, recipe conflict, photo register, MRB matrix, reliability plan, COA holdback, and audit trail.", ["wafer maps", "SPC chart", "metrology", "MRB matrix", "source precedence"], ["Bind wafer coordinates, chart values, and MRB source-state decisions."], gold, [near_check("p21-final", "source_state", ["wafer 09", "REL-22-A", "wafer 07", "scrap", "TIN_GATE_31"], 8, 900)], pages, facts=facts)


def packet_pharma_stability_release() -> Case:
    def page(title: str, subtitle: str = "Orion Generics | Product OG-217 tablets | Stability and release file") -> Image.Image:
        img = Image.new("RGB", (PAGE_W, PAGE_H), "#fffefc")
        d = ImageDraw.Draw(img)
        d.text((70, 52), subtitle, fill="#334155", font=F["tiny_bold"])
        d.text((70, 88), title, fill="#111827", font=F["h1"])
        d.line((70, 148, 1588, 148), fill="#111827", width=2)
        d.text((1385, 54), "QA RELEASE COPY", fill="#166534", font=F["tiny_bold"])
        return img

    batches = [
        ["Batch", "Strength", "Mfg date", "Pack", "Initial state", "QA decision"],
        ["G217-2401", "25 mg", "2026-01-14", "HDPE bottle", "commercial", "release"],
        ["G217-2402", "25 mg", "2026-01-16", "HDPE bottle", "commercial", "release"],
        ["G217-2403", "25 mg", "2026-01-19", "blister", "process validation", "hold for 6M"],
        ["G217-2404", "50 mg", "2026-01-22", "HDPE bottle", "scale-up", "conditional"],
    ]
    assay_rows = [
        ["Sample", "Assay %LC", "Imp A", "Imp B", "Total impurities", "State"],
        ["G217-2401 initial", "99.3", "0.08", "0.05", "0.21", "pass"],
        ["G217-2402 initial", "98.9", "0.07", "0.06", "0.24", "pass"],
        ["G217-2403 initial", "99.8", "0.09", "0.04", "0.23", "pass"],
        ["G217-2404 initial", "101.1", "0.10", "0.05", "0.26", "watch"],
        ["G217-2403 6M 40C/75", "95.8", "0.42", "0.31", "0.94", "hold"],
        ["G217-2404 3M 40C/75", "97.2", "0.21", "0.18", "0.58", "conditional"],
    ]
    dissolution = [
        ["Batch", "Stage", "10 min", "20 min", "30 min", "45 min", "Q state"],
        ["G217-2401", "initial", "52", "79", "91", "96", "pass S1"],
        ["G217-2402", "initial", "50", "77", "89", "95", "pass S1"],
        ["G217-2403", "initial", "48", "74", "86", "93", "pass S1"],
        ["G217-2403", "6M accel", "35", "58", "73", "81", "fail S1; hold"],
        ["G217-2404", "3M accel", "43", "69", "82", "90", "pass S2"],
    ]
    stability_a = [
        ["Batch", "Condition", "Time", "Assay", "Imp A", "Water", "Appearance"],
        ["G217-2401", "25C/60", "0M", "99.3", "0.08", "1.2", "white"],
        ["G217-2401", "25C/60", "3M", "99.0", "0.10", "1.3", "white"],
        ["G217-2401", "40C/75", "3M", "98.1", "0.18", "1.6", "white"],
        ["G217-2402", "25C/60", "0M", "98.9", "0.07", "1.1", "white"],
        ["G217-2402", "40C/75", "3M", "97.8", "0.17", "1.5", "white"],
        ["G217-2403", "25C/60", "0M", "99.8", "0.09", "1.3", "white"],
    ]
    stability_b = [
        ["Batch", "Condition", "Time", "Assay", "Imp A", "Water", "Appearance"],
        ["G217-2403", "40C/75", "3M", "97.4", "0.24", "1.9", "cream tint"],
        ["G217-2403", "40C/75", "6M", "95.8", "0.42", "2.4", "cream tint"],
        ["G217-2404", "25C/60", "0M", "101.1", "0.10", "1.4", "white"],
        ["G217-2404", "40C/75", "1M", "99.4", "0.15", "1.7", "white"],
        ["G217-2404", "40C/75", "3M", "97.2", "0.21", "2.0", "white"],
        ["G217-2404", "30C/65", "3M", "98.4", "0.16", "1.8", "white"],
    ]
    blend_rows = [
        ["Location", "G217-2401", "G217-2402", "G217-2403", "G217-2404"],
        ["Top left", "98.7", "99.1", "100.2", "101.8"],
        ["Top right", "99.0", "98.6", "99.6", "101.4"],
        ["Middle", "99.4", "99.0", "100.1", "101.2"],
        ["Bottom left", "98.8", "98.4", "99.3", "100.9"],
        ["Bottom right", "99.2", "98.8", "99.5", "101.5"],
        ["RSD %", "0.29", "0.28", "0.36", "0.32"],
    ]
    cu_rows = [
        ["Batch", "Mean", "Min", "Max", "AV", "State"],
        ["G217-2401", "99.1", "97.8", "100.6", "6.8", "pass"],
        ["G217-2402", "98.8", "97.2", "100.1", "7.4", "pass"],
        ["G217-2403", "99.6", "96.9", "102.8", "10.6", "pass"],
        ["G217-2404", "101.3", "98.2", "104.6", "14.9", "borderline; conditional"],
    ]
    packaging_rows = [
        ["Line item", "G217-2401", "G217-2402", "G217-2403", "G217-2404"],
        ["Start count", "90,240", "88,800", "92,400", "47,520"],
        ["Good bottles/cards", "89,760", "88,104", "91,944", "47,112"],
        ["Rejects", "214", "332", "288", "196"],
        ["Samples", "266", "364", "168", "212"],
        ["Reconciliation", "100.00%", "100.00%", "100.00%", "100.00%"],
    ]
    deviations = [
        ["Deviation", "Batch", "Description", "Initial impact", "Final state"],
        ["DV-217-11", "G217-2403", "6M accel dissolution S1 failure", "major", "batch hold"],
        ["DV-217-12", "G217-2404", "CU AV 14.9 near limit", "minor", "conditional release"],
        ["DV-217-13", "G217-2402", "label camera reject burst", "minor", "closed no product impact"],
        ["DV-217-14", "G217-2401", "HPLC vial reinjection", "minor", "accepted reinjection"],
    ]
    source_conflict = [
        ["Source", "Value shown", "Status", "Final treatment"],
        ["Draft batch release", "G217-2403 release", "superseded", "ignore for release"],
        ["Stability minutes", "G217-2403 hold", "current", "controls"],
        ["Packaging report", "G217-2403 reconciliation 100%", "context", "does not override stability hold"],
        ["QA disposition", "G217-2404 conditional", "current", "requires 9M accel review"],
    ]
    final_rows = [
        ["Batch", "Final state", "Reason", "Shipment"],
        ["G217-2401", "release", "all release tests pass", "allowed"],
        ["G217-2402", "release", "all release tests pass", "allowed"],
        ["G217-2403", "hold", "6M accelerated dissolution and impurity trend", "not allowed"],
        ["G217-2404", "conditional", "CU AV 14.9 and 3M accelerated trend", "only domestic stability reserve"],
    ]

    pages: list[Image.Image] = []
    p = page("Executive Release Summary")
    d = ImageDraw.Draw(p)
    draw_kv_band(d, 80, 205, [("Product", "OG-217 tablets"), ("Protocol", "STB-217-26A"), ("Review", "2026-07-01"), ("Batches", "4")], [330, 300, 250, 160])
    draw_note(d, (90, 365, 1510, 555), "QA disposition", "Release G217-2401 and G217-2402. Hold G217-2403 because accelerated 6M dissolution fails S1 and impurities trend high. G217-2404 is conditional and limited to domestic stability reserve pending 9M accelerated review.", "#7f1d1d")
    draw_ledger(d, 90, 665, [180, 170, 190, 220, 240, 250], batches, 62)
    draw_ledger(d, 90, 1125, [300, 260, 360, 320], final_rows, 66)
    pages.append(p)

    for title, rows, widths, note in [
        ("Batch Record and Packaging Configuration", batches, [190, 180, 190, 220, 240, 260], "G217-2403 is process validation blister stock; its packaging completion does not imply release."),
        ("Assay and Related Substances", assay_rows, [260, 160, 120, 120, 210, 220], "G217-2403 6M accelerated sample is the critical impurity trend row."),
        ("Blend Uniformity", blend_rows, [220, 180, 180, 180, 180], "All blend RSD values pass; this table does not clear later stability holds."),
        ("Content Uniformity", cu_rows, [230, 160, 160, 160, 160, 360], "G217-2404 AV 14.9 remains below the hard limit but triggers conditional release."),
        ("Packaging Reconciliation", packaging_rows, [260, 210, 210, 210, 210], "All reconciliations close at 100.00%; reject burst DV-217-13 has no product impact."),
        ("Deviation and CAPA Register", deviations, [220, 160, 420, 220, 300], "DV-217-11 is the release blocker; DV-217-14 uses accepted reinjection data."),
        ("Source Conflict Register", source_conflict, [300, 300, 220, 430], "Current stability minutes and QA disposition override the draft release page."),
    ]:
        p = page(title)
        d = ImageDraw.Draw(p)
        draw_ledger(d, 75, 230, widths, rows, 58)
        draw_note(d, (90, 900, 1510, 1080), "Review note", note, "#334155")
        pages.append(p)

    p = page("Dissolution Profiles")
    d = ImageDraw.Draw(p)
    d.rectangle((105, 245, 1460, 790), outline="#334155", width=2)
    d.line((170, 725, 1410, 725), fill="#111827", width=2)
    d.line((170, 725, 170, 320), fill="#111827", width=2)
    for yv in [50, 60, 70, 80, 90, 100]:
        gy = 725 - int((yv - 40) / 65 * 385)
        d.line((170, gy, 1410, gy), fill="#e5e7eb", width=1)
        d.text((125, gy - 10), str(yv), fill="#64748b", font=F["tiny"])
    d.line((170, 725 - int((80 - 40) / 65 * 385), 1410, 725 - int((80 - 40) / 65 * 385)), fill="#dc2626", width=3)
    d.text((1310, 470), "Q=80", fill="#dc2626", font=F["tiny_bold"])
    profiles = [
        ("G217-2401", [52, 79, 91, 96], "#2563eb"),
        ("G217-2402", [50, 77, 89, 95], "#0f766e"),
        ("G217-2403 6M", [35, 58, 73, 81], "#dc2626"),
        ("G217-2404 3M", [43, 69, 82, 90], "#7c3aed"),
    ]
    times = [10, 20, 30, 45]
    for label, vals, color in profiles:
        pts = []
        for t, v in zip(times, vals):
            x = 220 + int((t - 10) / 35 * 1080)
            y = 725 - int((v - 40) / 65 * 385)
            pts.append((x, y))
            d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color)
        for a, b in zip(pts, pts[1:]):
            d.line((*a, *b), fill=color, width=4)
    for i, (label, _vals, color) in enumerate(profiles):
        lx = 135 + i * 350
        ly = 815
        d.line((lx, ly + 11, lx + 34, ly + 11), fill=color, width=5)
        d.text((lx + 48, ly), label, fill=color, font=F["tiny_bold"])
    draw_ledger(d, 80, 910, [200, 160, 130, 130, 130, 130, 260], dissolution, 58)
    draw_note(d, (90, 1430, 1510, 1605), "Dissolution interpretation", "G217-2403 6M accelerated reaches 81% at 45 min but fails S1 because the 30 min value is 73% below Q=80. G217-2404 3M passes only after S2 review.", "#7f1d1d")
    pages.append(p)

    p = page("Stability Table Part 1")
    d = ImageDraw.Draw(p)
    draw_ledger(d, 70, 230, [190, 170, 120, 120, 120, 120, 260], stability_a, 58)
    draw_note(d, (90, 820, 1510, 990), "Continuation", "This is the first part of the stability matrix. The same headers continue on the next page; repeated headers are not additional data rows.", "#334155")
    pages.append(p)

    p = page("Stability Table Part 2")
    d = ImageDraw.Draw(p)
    draw_ledger(d, 70, 230, [190, 170, 120, 120, 120, 120, 260], stability_b, 58)
    draw_note(d, (90, 820, 1510, 1000), "Critical rows", "G217-2403 at 40C/75 6M has assay 95.8, Imp A 0.42, water 2.4, and cream tint. G217-2404 at 40C/75 3M remains conditional, not fully released.", "#7f1d1d")
    pages.append(p)

    p = page("Chromatogram Plate and Peak Purity")
    d = ImageDraw.Draw(p)
    panels = [
        ("A G217-2401 assay", "main peak 7.42 min; purity 0.998", "#2563eb"),
        ("B G217-2403 6M Imp A", "Imp A 3.18 min; 0.42%", "#dc2626"),
        ("C G217-2403 6M Imp B", "Imp B 5.66 min; 0.31%", "#ea580c"),
        ("D G217-2404 3M assay", "main peak 7.43 min; 97.2%", "#7c3aed"),
    ]
    for i, (label, note, color) in enumerate(panels):
        x = 90 + (i % 2) * 730
        y = 250 + (i // 2) * 420
        rng = random.Random(21700 + i)
        d.rectangle((x, y, x + 630, y + 315), outline="#cbd5e1", width=2)
        d.rectangle((x + 1, y + 1, x + 629, y + 314), outline="#f8fafc", width=1)
        d.text((x + 16, y + 16), label, fill="#111827", font=F["small_bold"])
        d.text((x + 420, y + 18), f"Seq {2417 + i} / 254 nm", fill="#64748b", font=F["tiny"])
        d.line((x + 55, y + 255, x + 590, y + 255), fill="#111827", width=2)
        d.line((x + 55, y + 255, x + 55, y + 70), fill="#111827", width=2)
        for tick, rt in enumerate(["0", "2", "4", "6", "8", "10"]):
            tx = x + 55 + tick * 107
            d.line((tx, y + 255, tx, y + 262), fill="#111827", width=1)
            d.text((tx - 8, y + 266), rt, fill="#64748b", font=F["tiny"])
        for tick, au in enumerate(["0", "25", "50", "75"]):
            ty = y + 255 - tick * 54
            d.line((x + 48, ty, x + 55, ty), fill="#111827", width=1)
            d.text((x + 18, ty - 10), au, fill="#64748b", font=F["tiny"])
        peak_x = [x + 448, x + 225, x + 358, x + 452][i]
        integration = (peak_x - (48 if i in [0, 3] else 30), peak_x + (58 if i in [0, 3] else 34))
        d.rectangle((integration[0], y + 80, integration[1], y + 255), outline="#94a3b8", width=1)
        d.text((integration[0] + 4, y + 86), "INT", fill="#64748b", font=F["tiny"])
        shoulder_x = peak_x - (72 if i in [0, 3] else -82)
        small_peak_x = peak_x + (86 if i in [0, 3] else 118)
        trace = []
        for step in range(0, 510, 6):
            xx = x + 65 + step
            main_width = 23 if i in [0, 3] else 16
            if xx > peak_x:
                main_width += 18 if i in [0, 3] else 9
            main_height = 156 if i in [0, 3] else 92
            dist = (xx - peak_x) / main_width
            shoulder_dist = (xx - shoulder_x) / (20 + i * 3)
            small_dist = (xx - small_peak_x) / (16 + i * 2)
            height = main_height * pow(2.71828, -(dist * dist) / 2)
            height += (18 + i * 3) * pow(2.71828, -(shoulder_dist * shoulder_dist) / 2)
            height += (9 + i * 2) * pow(2.71828, -(small_dist * small_dist) / 2)
            baseline = 4 * pow(2.71828, -((step - 120) / 180) ** 2) + (step / 510) * (3 if i % 2 else -2)
            noise = rng.uniform(-2.8, 2.8) + rng.uniform(-1.1, 1.1)
            yy = y + 235 - int(height + baseline + noise)
            trace.append((xx, yy))
        fill_trace = [(trace[0][0], y + 255), *trace, (trace[-1][0], y + 255)]
        d.polygon(fill_trace, fill=(*ImageColor.getrgb(color), 28))
        for a, b in zip(trace, trace[1:]):
            d.line((*a, *b), fill=color, width=2)
        for marker in [shoulder_x, peak_x, small_peak_x]:
            d.line((marker, y + 247, marker, y + 255), fill="#334155", width=1)
        d.text((x + 16, y + 284), note, fill="#334155", font=F["tiny_bold"])
        d.text((x + 494, y + 284), "min", fill="#64748b", font=F["tiny"])
    draw_ledger(d, 90, 1135, [260, 260, 250, 360], [["Panel", "Peak / RT", "Value", "Interpretation"], ["A", "main 7.42", "purity 0.998", "release batch clean"], ["B", "Imp A 3.18", "0.42%", "G217-2403 blocker"], ["C", "Imp B 5.66", "0.31%", "G217-2403 trend"], ["D", "main 7.43", "97.2%", "G217-2404 conditional"]], 62)
    pages.append(p)

    p = page("Particle and Appearance Register")
    d = ImageDraw.Draw(p)
    particle_rows = [
        ["Frame", "Batch", "Cue", "Reviewer mark", "Final treatment"],
        ["VIS-41", "G217-2401", "no specks", "green check", "release"],
        ["VIS-42", "G217-2402", "label scuff only", "blue note", "release"],
        ["VIS-43", "G217-2403", "cream tint at 6M", "amber box", "hold"],
        ["VIS-44", "G217-2404", "no particles", "green check", "conditional"],
        ["VIS-45", "G217-2403", "tablet edge chip", "red circle", "stability retain only"],
    ]
    draw_ledger(d, 85, 235, [160, 190, 320, 260, 350], particle_rows, 66)
    draw_ledger(d, 85, 760, [220, 270, 280, 380], [["Visual state", "Affected source", "Meaning", "Release impact"], ["cream tint", "G217-2403 6M", "matches impurity trend", "hold"], ["edge chip", "G217-2403 retain", "not commercial sample", "context only"], ["label scuff", "G217-2402 bottle", "secondary packaging only", "no impact"], ["green check", "G217-2401/G217-2404", "visual pass", "release/conditional"]], 66)
    pages.append(p)

    p = page("Stability Chamber Tray Map")
    d = ImageDraw.Draw(p)
    d.text((90, 215), "Chamber CH-40-75 shelf C, pull map reviewed 2026-06-28. Row letters and column numbers are printed on the tray rails.", fill="#334155", font=F["small"])
    cell_w, cell_h = 165, 130
    grid_x, grid_y = 220, 330
    cols = ["1", "2", "3", "4", "5", "6"]
    rows = ["A", "B", "C", "D"]
    for c, col in enumerate(cols):
        d.text((grid_x + c * cell_w + 70, grid_y - 45), col, fill="#475569", font=F["small_bold"])
    for r, row in enumerate(rows):
        d.text((grid_x - 55, grid_y + r * cell_h + 46), row, fill="#475569", font=F["small_bold"])
    tray = {
        ("A", "1"): ("G217-2401\n3M reserve\nR", "#dcfce7", "#166534"),
        ("A", "2"): ("G217-2402\n3M reserve\nR", "#dcfce7", "#166534"),
        ("B", "3"): ("G217-2403\n6M pulled\nH", "#fee2e2", "#991b1b"),
        ("B", "4"): ("G217-2403\n9M retain\nQ", "#fef3c7", "#92400e"),
        ("C", "2"): ("G217-2404\n3M pulled\nC", "#ede9fe", "#6d28d9"),
        ("C", "3"): ("G217-2404\n9M pending\nC", "#ede9fe", "#6d28d9"),
        ("D", "5"): ("empty clip\nbroken\nX", "#e5e7eb", "#475569"),
    }
    for r, row in enumerate(rows):
        for c, col in enumerate(cols):
            x = grid_x + c * cell_w
            y = grid_y + r * cell_h
            label, fill, outline = tray.get((row, col), ("", "#ffffff", "#cbd5e1"))
            d.rectangle((x, y, x + cell_w - 8, y + cell_h - 8), fill=fill, outline=outline, width=3 if label else 1)
            if label:
                draw_text(d, (x + 12, y + 18), label, F["tiny_bold"], fill=outline, width=14, leading=22)
    draw_ledger(d, 130, 930, [170, 360, 320, 420], [["Mark", "Meaning", "Tray cells", "Disposition effect"], ["R", "retained reserve", "A1, A2", "release support only"], ["H", "hold blocker", "B3", "G217-2403 remains held"], ["Q", "quarantined retain", "B4", "not a release sample"], ["C", "conditional stability", "C2, C3", "G217-2404 pending 9M"], ["X", "empty broken clip", "D5", "do not count as missing sample"]], 62)
    draw_note(d, (130, 1410, 1485, 1588), "Tray interpretation", "B3 is the pulled G217-2403 6M hold sample. B4 is a quarantined 9M retain and does not reverse the hold. C2 is the pulled G217-2404 3M conditional sample; C3 is the pending 9M sample.", "#7f1d1d")
    pages.append(p)

    p = page("Hardness Drift Mini-Trends")
    d = ImageDraw.Draw(p)
    d.text((90, 215), "Tablet hardness is plotted from retain pulls. Values are not repeated in the release tables because the chart is reviewed as visual trend evidence.", fill="#334155", font=F["small"])
    chart_specs = [
        ("G217-2401", [9.8, 9.7, 9.6, 9.6], "#2563eb"),
        ("G217-2402", [9.7, 9.6, 9.5, 9.4], "#0f766e"),
        ("G217-2403", [9.6, 9.1, 8.6, 8.1], "#dc2626"),
        ("G217-2404", [10.1, 9.8, 9.4, 9.0], "#7c3aed"),
    ]
    times = ["0M", "1M", "3M", "6M"]
    for i, (label, values, color) in enumerate(chart_specs):
        x0 = 100 + (i % 2) * 735
        y0 = 310 + (i // 2) * 460
        d.rectangle((x0, y0, x0 + 635, y0 + 330), outline="#334155", width=2)
        d.text((x0 + 18, y0 + 18), label, fill="#111827", font=F["small_bold"])
        d.line((x0 + 70, y0 + 270, x0 + 570, y0 + 270), fill="#111827", width=2)
        d.line((x0 + 70, y0 + 270, x0 + 70, y0 + 70), fill="#111827", width=2)
        for tick in [8.0, 8.5, 9.0, 9.5, 10.0]:
            gy = y0 + 270 - int((tick - 8.0) / 2.2 * 190)
            d.line((x0 + 70, gy, x0 + 570, gy), fill="#e5e7eb", width=1)
            d.text((x0 + 24, gy - 10), f"{tick:.1f}", fill="#64748b", font=F["tiny"])
        alert_y = y0 + 270 - int((8.5 - 8.0) / 2.2 * 190)
        d.line((x0 + 70, alert_y, x0 + 570, alert_y), fill="#dc2626", width=2)
        pts = []
        for j, val in enumerate(values):
            px = x0 + 95 + j * 150
            py = y0 + 270 - int((val - 8.0) / 2.2 * 190)
            pts.append((px, py))
            d.ellipse((px - 6, py - 6, px + 6, py + 6), fill=color)
            d.text((px - 15, y0 + 286), times[j], fill="#475569", font=F["tiny"])
        for a, b in zip(pts, pts[1:]):
            d.line((*a, *b), fill=color, width=4)
    draw_ledger(d, 120, 1265, [245, 250, 430, 340], [["Visual finding", "Batch", "Reviewer mark", "Release meaning"], ["Stable hardness", "G217-2401", "flat blue trace", "supports release"], ["Stable hardness", "G217-2402", "flat green trace", "supports release"], ["Alert crossing", "G217-2403", "red trace crosses alert at final pull", "supports hold"], ["Downward drift", "G217-2404", "purple trace stays above alert", "conditional monitoring"]], 64)
    pages.append(p)

    p = page("Regulatory Commitments")
    d = ImageDraw.Draw(p)
    reg_rows = [
        ["Commitment", "Applies to", "Due", "State"],
        ["Submit 6M accel update", "G217-2403", "2026-08-15", "required"],
        ["Complete REL-OG217-A", "G217-2404", "2026-09-30", "open"],
        ["Annual report note", "DV-217-11", "2027-01-31", "include"],
        ["Shelf-life claim", "24 months", "not changed", "no expansion"],
    ]
    draw_ledger(d, 90, 250, [360, 250, 220, 360], reg_rows, 68)
    draw_note(d, (95, 820, 1510, 1010), "Regulatory interpretation", "The file does not support expanding shelf life. G217-2403 data must be reported, and G217-2404 conditional release cannot be converted to unrestricted release until the reliability commitment closes.", "#334155")
    pages.append(p)

    p = page("Final QA Decision and Audit Trail")
    d = ImageDraw.Draw(p)
    audit_rows = [
        ["Time", "Actor", "Entry", "Effect"],
        ["2026-06-28 09:20", "QC", "G217-2403 6M result loaded", "stability hold opened"],
        ["2026-06-28 14:05", "QA", "draft release page voided", "source conflict resolved"],
        ["2026-06-29 11:30", "MSAT", "G217-2404 conditional proposed", "9M review required"],
        ["2026-07-01 10:10", "QA", "release G217-2401/G217-2402", "shipment allowed"],
        ["2026-07-01 10:18", "QA", "G217-2403 hold remains", "shipment blocked"],
    ]
    draw_ledger(d, 90, 230, [250, 180, 420, 360], audit_rows, 66)
    draw_ledger(d, 90, 760, [300, 280, 460], [["Control item", "Final state", "Evidence"], ["Release", "G217-2401 and G217-2402", "assay/dissolution/stability pass"], ["Hold", "G217-2403", "6M accel dissolution S1 failure + impurity trend"], ["Conditional", "G217-2404", "CU AV 14.9 + 3M trend"], ["Draft G217-2403 release", "voided", "stability minutes override"]], 72)
    pages.append(p)

    gold = "\n\n".join([
        "# Orion Generics OG-217 Stability and Release File",
        "QA disposition: release G217-2401 and G217-2402; hold G217-2403 because accelerated 6M dissolution fails S1 and impurities trend high; G217-2404 is conditional and limited to domestic stability reserve pending 9M accelerated review.",
        "## Batches\n" + md_table(batches[0], batches[1:]),
        "## Assay and Related Substances\n" + md_table(assay_rows[0], assay_rows[1:]),
        "## Dissolution\n" + md_table(dissolution[0], dissolution[1:]) + "\nG217-2403 6M accelerated reaches 81% at 45 min but fails S1 because the 30 min value is 73% below Q=80. G217-2404 3M passes only after S2 review.",
        "## Blend Uniformity\n" + md_table(blend_rows[0], blend_rows[1:]),
        "## Content Uniformity\n" + md_table(cu_rows[0], cu_rows[1:]),
        "## Stability Matrix\n" + md_table(stability_a[0], stability_a[1:] + stability_b[1:]),
        "## Chromatogram Plate\nPanels: A G217-2401 assay main peak 7.42 min purity 0.998; B G217-2403 6M Imp A at 3.18 min 0.42%; C G217-2403 6M Imp B at 5.66 min 0.31%; D G217-2404 3M assay main peak 7.43 min 97.2%.",
        "## Packaging Reconciliation\n" + md_table(packaging_rows[0], packaging_rows[1:]),
        "## Deviations and Source Conflict\n" + md_table(deviations[0], deviations[1:]) + "\n" + md_table(source_conflict[0], source_conflict[1:]),
        "## Particle and Appearance Register\nVIS-41 G217-2401 no specks release; VIS-42 G217-2402 label scuff only release; VIS-43 G217-2403 cream tint at 6M hold; VIS-44 G217-2404 no particles conditional; VIS-45 G217-2403 tablet edge chip is stability-retain context only.",
        "## Stability Chamber Tray Map\nChamber CH-40-75 shelf C has G217-2401 3M reserve R at A1, G217-2402 3M reserve R at A2, G217-2403 6M pulled H at B3, G217-2403 9M retain Q at B4, G217-2404 3M pulled C at C2, G217-2404 9M pending C at C3, and an empty broken clip X at D5. B3 controls the G217-2403 hold; B4 is quarantined retain context; C2 is the G217-2404 conditional sample; C3 is pending 9M.",
        "## Hardness Drift Mini-Trends\nVisual trend facts: G217-2401 remains stable from about 9.8 to 9.6; G217-2402 remains stable from about 9.7 to 9.4; G217-2403 drops from about 9.6 to 8.1 and crosses below the 8.5 alert line at 6M; G217-2404 drifts from about 10.1 to 9.0 and remains conditional monitoring.",
        "## Regulatory Commitments\nSubmit 6M accelerated update for G217-2403 by 2026-08-15. Complete REL-OG217-A for G217-2404 by 2026-09-30. Include DV-217-11 in the 2027-01-31 annual report. Shelf-life claim remains 24 months with no expansion.",
        "## Final QA Decision\n" + md_table(final_rows[0], final_rows[1:]) + "\nAudit trail: QC loaded G217-2403 6M at 2026-06-28 09:20; QA voided draft release at 2026-06-28 14:05; MSAT proposed G217-2404 conditional at 2026-06-29 11:30; QA released G217-2401/G217-2402 at 2026-07-01 10:10 and kept G217-2403 hold at 10:18.",
    ])
    facts = [
        fact("p22.final.disposition", "source_state", 14, "Final QA disposition is G217-2401 and G217-2402 release; G217-2403 hold due 6M accelerated dissolution S1 failure and impurity trend; G217-2404 conditional domestic stability reserve pending 9M accelerated review.", modality="source-precedence", severity="critical"),
        fact("p22.batch.config", "table_cell", 7, "Batch table preserves strength, manufacture date, pack, initial state, and QA decision for all four batches.", modality="table", severity="major"),
        fact("p22.assay.impurities", "table_cell", 10, "Assay table preserves all sample rows and values, especially G217-2403 6M 95.8 assay, Imp A 0.42, Imp B 0.31, total impurities 0.94 hold.", modality="table", severity="critical"),
        fact("p22.dissolution.table", "table_cell", 10, "Dissolution table preserves 10/20/30/45 min values and Q states for all five rows.", modality="table", severity="critical"),
        fact("p22.dissolution.chart", "chart", 10, "Dissolution profile interpretation preserves Q=80 line, G217-2403 6M at 35/58/73/81 and S1 failure at 30 min, and G217-2404 3M pass only after S2.", modality="chart", severity="critical"),
        fact("p22.blend", "table_cell", 7, "Blend uniformity preserves all location values and RSD rows for four batches.", modality="table", severity="major"),
        fact("p22.content.uniformity", "table_cell", 8, "Content uniformity preserves mean/min/max/AV/state for all batches, especially G217-2404 AV 14.9 borderline conditional.", modality="table", severity="critical"),
        fact("p22.stability.continuation", "structure", 10, "Stability matrix is preserved as a continuation table across two pages with repeated headers not treated as data.", modality="structure", severity="critical"),
        fact("p22.stability.critical", "table_cell", 12, "Stability critical rows preserve G217-2403 40C/75 6M assay 95.8, Imp A 0.42, water 2.4, cream tint; G217-2404 40C/75 3M assay 97.2, Imp A 0.21, water 2.0.", modality="table", severity="critical"),
        fact("p22.chromatograms", "visual_relation", 10, "Chromatogram panels preserve labels, retention times, and values for A-D, including Imp A 3.18 min 0.42% and Imp B 5.66 min 0.31% for G217-2403 6M.", modality="visual", severity="critical"),
        fact("p22.packaging", "table_cell", 8, "Packaging reconciliation preserves start counts, good bottles/cards, rejects, samples, and 100.00% reconciliation for all four batches.", modality="table", severity="major"),
        fact("p22.deviations", "source_state", 10, "Deviation register preserves DV-217-11 as major release blocker, DV-217-12 conditional, DV-217-13 closed no impact, and DV-217-14 accepted reinjection.", modality="source-precedence", severity="critical"),
        fact("p22.source.conflict", "source_state", 10, "Source conflict is resolved correctly: draft G217-2403 release is superseded; stability minutes and QA disposition control; packaging reconciliation does not override stability hold.", modality="source-precedence", severity="critical"),
        fact("p22.particle.visual", "visual_relation", 8, "Particle/appearance register preserves frame-to-batch cue and final treatment, especially VIS-43 cream tint hold and VIS-45 edge chip as stability-retain context only.", modality="visual", severity="critical"),
        fact("p22.chamber.map", "visual_relation", 12, "Stability chamber tray map preserves row/column cell bindings and marks: A1 G217-2401 3M reserve R, A2 G217-2402 3M reserve R, B3 G217-2403 6M pulled H, B4 G217-2403 9M retain Q, C2 G217-2404 3M pulled C, C3 G217-2404 9M pending C, D5 empty broken clip X.", modality="visual", severity="critical"),
        fact("p22.chamber.interpretation", "source_state", 8, "Tray interpretation preserves that B3 is the pulled G217-2403 6M hold sample, B4 is quarantined retain context and does not reverse the hold, C2 is the pulled G217-2404 3M conditional sample, and C3 is pending 9M.", modality="source-precedence", severity="critical"),
        fact("p22.hardness.trends", "chart", 12, "Hardness mini-trends are preserved: G217-2401 about 9.8 to 9.6 stable; G217-2402 about 9.7 to 9.4 stable; G217-2403 about 9.6 to 8.1 and below the 8.5 alert at 6M; G217-2404 about 10.1 to 9.0 downward drift/conditional monitoring.", modality="chart", severity="critical"),
        fact("p22.regulatory", "source_state", 8, "Regulatory commitments preserve G217-2403 6M update due 2026-08-15, REL-OG217-A due 2026-09-30 for G217-2404, annual report DV-217-11 due 2027-01-31, and no shelf-life expansion.", modality="source-precedence", severity="critical"),
        fact("p22.audit", "structure", 6, "Final audit trail preserves timestamp/actor/entry/effect sequence and final control item states.", modality="structure", severity="major"),
    ]
    return Case("P22-pharma-stability-release", "Pharmaceutical Stability Release File", "pharma-quality", ["multi-page", "pharma", "stability", "dissolution", "chromatograms", "source-precedence"], "Stress pharmaceutical release reconstruction with stability continuation, dissolution chart semantics, chromatogram panels, deviations, and source conflicts.", "Seventeen-page pharmaceutical stability and release packet with assay, dissolution, stability continuation, chromatograms, packaging reconciliation, tray map, hardness trends, deviations, regulatory commitments, and final QA disposition.", ["stability matrix", "dissolution chart", "chromatograms", "deviations", "source conflicts"], ["Bind release state to stability evidence, chart thresholds, and current QA source."], gold, [near_check("p22-final", "source_state", ["G217-2403", "hold", "6M", "G217-2404", "conditional"], 8, 900)], pages, facts=facts)


CASES = [
    packet_launch_readiness(),
    packet_pfas_validation(),
    packet_architecture_floorplan_diagrams(),
    packet_clinical_trial_site_binder(),
    packet_utility_outage_restoration(),
    packet_semiconductor_lot_disposition(),
    packet_pharma_stability_release(),
]


def write_pdf(case: Case, path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    if case.covered_text:
        c.setFont("Helvetica", 12)
        c.setFillColorRGB(0, 0, 0)
        y = 620
        for line in case.covered_text:
            c.drawString(72, y, line)
            y -= 18
    for i, page in enumerate(case.pages):
        page_size = (letter[1], letter[0]) if page.width > page.height else letter
        c.setPageSize(page_size)
        if case.extractable_text_pages and i < len(case.extractable_text_pages):
            c.setFont("Helvetica", 9)
            c.setFillColorRGB(0, 0, 0)
            for px, py, line in case.extractable_text_pages[i]:
                c.drawString(px / page.width * page_size[0], page_size[1] - py / page.height * page_size[1], line)
        buffer = BytesIO()
        page.save(buffer, format="PNG")
        buffer.seek(0)
        c.drawImage(ImageReader(buffer), 0, 0, width=page_size[0], height=page_size[1])
        c.showPage()
    if case.hidden_text:
        # Add invisible-looking white text on a fresh overlay page location before final save.
        # ReportLab extraction preserves it, while it is not visible on a white background.
        # It is intentionally placed after pages so raw extractors can still see stale values.
        # This uses a page-level white text object; rendered content remains unchanged.
        pass
    c.save()

    if case.hidden_text:
        # Reopen and overlay white text onto the first page without changing visible rendering.
        from pypdf import PdfReader, PdfWriter
        from reportlab.pdfgen import canvas as rl_canvas

        packet = BytesIO()
        overlay = rl_canvas.Canvas(packet, pagesize=letter, invariant=1)
        overlay.setFillColorRGB(1, 1, 1)
        overlay.setFont("Helvetica", 8)
        y = 40
        for line in case.hidden_text:
            overlay.drawString(42, y, line)
            y += 10
        overlay.save()
        packet.seek(0)
        base = PdfReader(str(path))
        over = PdfReader(packet)
        writer = PdfWriter()
        base.pages[0].merge_page(over.pages[0])
        for page in base.pages:
            writer.add_page(page)
        with path.open("wb") as f:
            writer.write(f)


def rasterize_source_pdf_to_pdf(source: Path, path: Path, dpi: int = 144) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        prefix = Path(tmp) / "page"
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(source), str(prefix)], check=True, capture_output=True)
        pages = sorted(Path(tmp).glob("page-*.png"))
        if not pages:
            raise RuntimeError(f"No pages rendered from {source}")
        c = canvas.Canvas(str(path), invariant=1)
        for page_path in pages:
            img = Image.open(page_path).convert("RGB")
            page_size = (img.width * 72 / dpi, img.height * 72 / dpi)
            c.setPageSize(page_size)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            c.drawImage(ImageReader(buffer), 0, 0, width=page_size[0], height=page_size[1])
            c.showPage()
        c.save()


def write_spec(case: Case) -> str:
    return "\n".join(
        [
            f"# {case.title}",
            "",
            f"Source modality: {case.modality}",
            "",
            f"Family: `{case.family}`",
            "",
            "Tags: " + ", ".join(f"`{tag}`" for tag in case.tags),
            "",
        ]
    )


def write_case(case: Case) -> dict:
    out = CASE_ROOT / case.slug
    out.mkdir(parents=True, exist_ok=True)
    if case.source_pdf:
        if case.rasterize_source_pdf:
            rasterize_source_pdf_to_pdf(case.source_pdf, out / "source.pdf", dpi=case.rasterize_dpi)
        else:
            shutil.copyfile(case.source_pdf, out / "source.pdf")
    else:
        write_pdf(case, out / "source.pdf")
    (out / "gold.md").write_text(case.gold, encoding="utf-8")
    (out / "spec.md").write_text(write_spec(case), encoding="utf-8")
    checks = {"id": case.id, "title": case.title, "family": case.family, "tags": case.tags, "checks": case.checks}
    (out / "checks.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    facts = {"id": case.id, "title": case.title, "family": case.family, "tags": case.tags, "facts": normalize_facts(case.facts) if case.facts else facts_from_checks(case)}
    (out / "facts.json").write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")
    return {
        "id": case.id,
        "title": case.title,
        "family": case.family,
        "tags": case.tags,
        "pages": case.page_count_override if case.page_count_override is not None else len(case.pages),
        "pdf": f"benchmark/cases/{case.slug}/source.pdf",
        "gold": f"benchmark/cases/{case.slug}/gold.md",
        "spec": f"benchmark/cases/{case.slug}/spec.md",
        "checks": f"benchmark/cases/{case.slug}/checks.json",
        "facts": f"benchmark/cases/{case.slug}/facts.json",
    }


def write_provider_capabilities() -> None:
    capabilities = {
        "schemaVersion": 1,
        "lastReviewed": "2026-07-07",
        "notes": [
            "This file records documented provider ingestion behavior for interpreting Doc2MD results. It is not a scoring file.",
            "Official Doc2MD runs send native PDFs to the provider. Capability gates diagnose provider/document handling separately from the official score.",
        ],
        "providers": {
            "openai": {
                "documents": {
                    "pdf": {
                        "supported": True,
                        "ingestionMode": "text_plus_page_images",
                        "officialDocs": ["https://developers.openai.com/api/docs/guides/file-inputs"],
                        "note": "OpenAI documents that PDFs provide both extracted text and page images to vision-capable models.",
                    },
                    "txt": {"supported": True, "ingestionMode": "native_text"},
                    "md": {"supported": True, "ingestionMode": "native_text"},
                    "csv": {"supported": True, "ingestionMode": "native_text_or_spreadsheet"},
                    "docx": {"supported": True, "ingestionMode": "document_parse"},
                    "pptx": {"supported": True, "ingestionMode": "document_parse"},
                    "xlsx": {"supported": True, "ingestionMode": "spreadsheet_parse"},
                    "images": {"supported": True, "ingestionMode": "vision_image"},
                }
            },
            "google-vertex": {
                "documents": {
                    "pdf": {
                        "supported": True,
                        "ingestionMode": "page_images",
                        "officialDocs": [
                            "https://ai.google.dev/gemini-api/docs/document-processing",
                            "https://firebase.google.com/docs/ai-logic/input-file-requirements",
                        ],
                        "note": "Google documents PDF support for text, images, diagrams, charts, and tables. Firebase AI Logic states PDF pages are tokenized like images.",
                    },
                    "txt": {"supported": True, "ingestionMode": "native_text"},
                    "md": {"supported": True, "ingestionMode": "native_text"},
                    "csv": {"supported": False, "ingestionMode": "unknown"},
                    "docx": {"supported": False, "ingestionMode": "unknown"},
                    "pptx": {"supported": False, "ingestionMode": "unknown"},
                    "xlsx": {"supported": False, "ingestionMode": "unknown"},
                    "images": {"supported": True, "ingestionMode": "vision_image"},
                }
            },
            "anthropic": {
                "documents": {
                    "pdf": {
                        "supported": True,
                        "ingestionMode": "text_plus_page_images",
                        "officialDocs": ["https://platform.claude.com/docs/en/build-with-claude/pdf-support"],
                        "note": "Anthropic documents visual PDF support as extracted text plus page images. Some hosted routes can fall back to text-only PDF handling.",
                    },
                    "txt": {"supported": True, "ingestionMode": "native_text"},
                    "md": {"supported": True, "ingestionMode": "native_text"},
                    "csv": {"supported": True, "ingestionMode": "native_text"},
                    "docx": {"supported": False, "ingestionMode": "convert_before_upload"},
                    "pptx": {"supported": False, "ingestionMode": "convert_before_upload"},
                    "xlsx": {"supported": False, "ingestionMode": "convert_before_upload"},
                    "images": {"supported": True, "ingestionMode": "vision_image"},
                }
            },
        },
    }
    (BENCHMARK_ROOT / "provider-capabilities.json").write_text(json.dumps(capabilities, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    if BENCHMARK_ROOT.exists():
        shutil.rmtree(BENCHMARK_ROOT)
    CASE_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "Doc2MD",
        "suite": "official",
        "scoreName": "Doc2MD Native PDF Score",
        "inputProtocol": "native_pdf",
        "providerFileModePolicy": "Send the native PDF file to the provider and record the provider's documented PDF ingestion mode separately. Do not convert official inputs to page images in the harness.",
        "version": "0.1.0",
        "description": "Benchmark for faithful document-to-Markdown reconstruction across realistic multi-page documents with dense layouts, charts, tables, forms, diagrams, annotations, and source-state conflicts.",
        "caseCount": len(CASES),
        "pageCount": sum(case.page_count_override if case.page_count_override is not None else len(case.pages) for case in CASES),
        "cases": [write_case(case) for case in CASES],
    }
    (BENCHMARK_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_provider_capabilities()
    print(f"Wrote {manifest['caseCount']} cases and {manifest['pageCount']} pages to {BENCHMARK_ROOT}")


if __name__ == "__main__":
    main()
