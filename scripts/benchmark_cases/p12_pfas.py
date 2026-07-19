from __future__ import annotations

import math
import random
from collections.abc import Sequence

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from reportlab.lib.colors import HexColor

from .common import (
    AMBER,
    BLUE,
    GREEN,
    INK,
    MUTED,
    RED,
    CaseBuilder,
    directed_edge_leaf,
    draw_arrow,
    draw_badge,
    draw_label,
    draw_paragraph,
    draw_table,
    image_reader,
    leaf,
    markdown_table,
    source_precedence_leaf,
    table_binding_leaf,
    table_leaves,
)
from .rasterize import ScanProfile, rasterize_pdf_pages


# The generator creates one deterministic 12-page logical packet. The selected
# scan pages are rasterized after generation by the corpus assembly step. These
# constants are deliberately public so the assembly step cannot silently drift
# from the case's intended modality envelope.
PAGE_PACKET_CONTROL = 1
PAGE_CALIBRATION_MODEL = 2
PAGE_CALIBRATION_CURVES = 3
PAGE_PRECISION_PART_1 = 4
PAGE_PRECISION_PART_2 = 5
PAGE_PREPARATION_SCAN = 6
PAGE_SEQUENCE_SCAN = 7
PAGE_INTEGRATION_REVIEW = 8
PAGE_QC_REVIEW = 9
PAGE_MAINTENANCE_SCAN = 10
PAGE_QA_CORRECTION = 11
PAGE_FINAL_DETERMINATION = 12

NATIVE_ONLY_PAGES = (
    PAGE_PACKET_CONTROL,
    PAGE_CALIBRATION_MODEL,
    PAGE_PRECISION_PART_1,
    PAGE_PRECISION_PART_2,
    PAGE_QC_REVIEW,
    PAGE_FINAL_DETERMINATION,
)
FULL_PAGE_SCAN_PAGES = (
    PAGE_PREPARATION_SCAN,
    PAGE_SEQUENCE_SCAN,
    PAGE_MAINTENANCE_SCAN,
)
MIXED_PAGES = (
    PAGE_CALIBRATION_CURVES,
    PAGE_INTEGRATION_REVIEW,
    PAGE_QA_CORRECTION,
)


def _clean_scan(image: Image.Image, *, seed: int, blur: float = 0.22) -> Image.Image:
    """Apply restrained deterministic copier texture to a raster insert."""
    rng = random.Random(seed)
    result = image.convert("L")
    pixels = result.load()
    for _ in range(result.width * result.height // 42):
        x = rng.randrange(result.width)
        y = rng.randrange(result.height)
        pixels[x, y] = rng.randrange(220, 252)
    result = result.filter(ImageFilter.GaussianBlur(blur))
    return ImageEnhance.Contrast(result).enhance(1.08).convert("RGB")


def _chart_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Pillow's bundled default is deterministic and avoids host font drift.
    return ImageFont.load_default(size=size)


def _calibration_plate(panels: Sequence[dict[str, object]]) -> Image.Image:
    """Dense raster-only calibration review plate with no native answer recap."""
    image = Image.new("RGB", (1800, 1160), "#f7f7f3")
    draw = ImageDraw.Draw(image)
    heading = _chart_font(27, bold=True)
    title_font = _chart_font(24, bold=True)
    body = _chart_font(19)
    small = _chart_font(17)
    tiny = _chart_font(15)

    draw.text((28, 18), "CALIBRATION REVIEW PLATE - WEIGHTED 1/x^2", font=heading, fill="#17202a")
    draw.text(
        (770, 24),
        "filled circle = included  |  open diamond = excluded  |  inset bars = back-calculated residual %",
        font=small,
        fill="#4e5963",
    )

    panel_width, panel_height = 566, 520
    for index, panel in enumerate(panels):
        column, row = index % 3, index // 3
        left = 28 + column * 590
        top = 66 + row * 540
        right = left + panel_width
        bottom = top + panel_height
        name = str(panel["name"])
        levels = [float(value) for value in panel["levels"]]  # type: ignore[index]
        responses = [float(value) for value in panel["responses"]]  # type: ignore[index]
        residuals = [float(value) for value in panel["residuals"]]  # type: ignore[index]
        color = str(panel["color"])
        excluded_index = panel.get("excluded_index")

        draw.rectangle((left, top, right, bottom), fill="#fbfbf8", outline="#7f8991", width=2)
        draw.text((left + 14, top + 11), f"{index + 1}. {name}", font=title_font, fill="#17202a")
        draw.text(
            (left + 14, top + 43),
            f"{panel['equation']}  |  R2 {panel['r2']}  |  {panel['range']}",
            font=body,
            fill="#3f4952",
        )

        x0, y0 = left + 54, top + 332
        x1, y1 = left + 382, top + 102
        draw.line((x0, y0, x1, y0), fill="#17202a", width=2)
        draw.line((x0, y0, x0, y1), fill="#17202a", width=2)
        for fraction in (0.25, 0.5, 0.75):
            y = int(y0 - fraction * (y0 - y1))
            draw.line((x0, y, x1, y), fill="#d8dcdf", width=1)
        log_low = math.log10(min(levels))
        log_span = math.log10(max(levels)) - log_low
        response_max = max(responses) * 1.08
        points: list[tuple[int, int]] = []
        for point_index, (level, response) in enumerate(zip(levels, responses)):
            x = int(x0 + 12 + (math.log10(level) - log_low) / log_span * (x1 - x0 - 24))
            y = int(y0 - 10 - response / response_max * (y0 - y1 - 20))
            points.append((x, y))
            if excluded_index == point_index:
                draw.polygon([(x, y - 8), (x + 8, y), (x, y + 8), (x - 8, y)], outline=color, fill="#fbfbf8")
            else:
                draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color, outline=color)
        included_points = [point for point_index, point in enumerate(points) if excluded_index != point_index]
        for first, second in zip(included_points, included_points[1:]):
            draw.line((*first, *second), fill=color, width=3)
        draw.text((left + 125, top + 338), "concentration ng/L (log)", font=small, fill="#303840")
        draw.text((left + 9, top + 185), "response\nratio", font=small, fill="#303840")

        # Residual inset is a separate visual encoding. The zero line and +/-20
        # bounds make an excluded or retained edge standard auditable by sight.
        rx0, ry0 = left + 418, top + 119
        rx1, ry1 = right - 14, top + 331
        zero_y = int((ry0 + ry1) / 2)
        draw.rectangle((rx0, ry0, rx1, ry1), outline="#a2a8ad", width=1)
        draw.line((rx0 + 6, zero_y, rx1 - 6, zero_y), fill="#5d666d", width=1)
        draw.line((rx0 + 6, ry0 + 12, rx1 - 6, ry0 + 12), fill="#b94942", width=1)
        draw.line((rx0 + 6, ry1 - 12, rx1 - 6, ry1 - 12), fill="#b94942", width=1)
        bar_width = max(5, int((rx1 - rx0 - 18) / len(residuals)) - 4)
        for residual_index, residual in enumerate(residuals):
            x = rx0 + 9 + residual_index * (bar_width + 4)
            height = int(abs(residual) / 20.0 * (ry1 - ry0 - 30) / 2)
            bar_color = "#b94942" if excluded_index == residual_index else color
            if residual >= 0:
                draw.rectangle((x, zero_y - height, x + bar_width, zero_y), fill=bar_color)
            else:
                draw.rectangle((x, zero_y, x + bar_width, zero_y + height), fill=bar_color)
        draw.text((rx0 + 7, top + 94), "residual %", font=tiny, fill="#4e5963")

        level_text = " / ".join(f"{value:g}" for value in levels)
        response_text = " / ".join(f"{value:.3f}" for value in responses)
        draw.text((left + 14, top + 376), f"LEVEL ng/L  {level_text}", font=tiny, fill="#303840")
        draw.text((left + 14, top + 401), f"RESPONSE    {response_text}", font=tiny, fill="#303840")
        draw.rectangle((left + 13, top + 435, right - 13, bottom - 13), fill="#eef1f1", outline="#c5cacc")
        draw.text((left + 24, top + 446), str(panel["review"]), font=body, fill="#17202a")
        draw.text((left + 24, top + 478), str(panel["disposition"]), font=small, fill=color)
    return image


def _chromatogram_plate() -> Image.Image:
    """Eight crowded raster-only panels from one routine integration review."""
    image = Image.new("RGB", (1800, 1120), "#f7f7f4")
    draw = ImageDraw.Draw(image)
    title_font = _chart_font(22, bold=True)
    note_font = _chart_font(17)
    tick_font = _chart_font(14)
    panels = [
        {
            "title": "A  LRB-240410-01 / PFOS Q1",
            "rt": 5.64,
            "peak": 0,
            "color": "#59636e",
            "state": "NO PEAK / BLANK ACCEPTED",
            "notes": ["noise 38-44 cps", "file 240410_10.wiff", "integration: none"],
        },
        {
            "title": "B  DW-240408-03 / PFOA Q1",
            "rt": 4.41,
            "peak": 205,
            "color": "#2d6a4f",
            "state": "ACCEPTED / FINAL BATCH RESULT",
            "notes": ["area 25,621", "Q1/Q2 ratio 0.31", "file 240410_14.wiff"],
        },
        {
            "title": "C  DW-240409-04 / 13C8-PFOA IS",
            "rt": 4.39,
            "peak": 82,
            "color": "#9e2a2b",
            "state": "SEQ 18 HOLD / ORIGINAL REJECTED",
            "notes": ["IS recovery 38%", "IR-18A", "file 240410_18.wiff"],
        },
        {
            "title": "D  DW-240409-04-RI / 13C8-PFOA IS",
            "rt": 4.40,
            "peak": 196,
            "color": "#1d4e89",
            "state": "SEQ 19 ACCEPTED / CONTROLLING",
            "notes": ["IS recovery 91%", "IR-19B", "file 240410_19.wiff"],
        },
        {
            "title": "E  DW-240409-04 / PFOA Q1",
            "rt": 4.42,
            "peak": 124,
            "color": "#9e2a2b",
            "state": "SEQ 18 NOT REPORTABLE",
            "notes": ["area 11,180", "Q1/Q2 ratio 0.27", "IR-18A linked"],
        },
        {
            "title": "F  DW-240409-04-RI / PFOA Q1",
            "rt": 4.41,
            "peak": 96,
            "color": "#1d4e89",
            "state": "SEQ 19 ACCEPTED / 1.06 ng/L J",
            "notes": ["area 8,420", "Q1/Q2 ratio 0.30", "IR-19B linked"],
        },
        {
            "title": "G  CCV-10-CLOSE / PFOA Q1",
            "rt": 4.41,
            "peak": 218,
            "color": "#2d6a4f",
            "state": "ACCEPTED / 103.1% RECOVERY",
            "notes": ["back-calc 10.31 ng/L", "area 80,755", "file 240410_21.wiff"],
        },
        {
            "title": "H  DW-240409-05 / 6:2 FTS Q2",
            "rt": 5.18,
            "peak": 142,
            "color": "#7a4f9a",
            "state": "REVIEWED / QUALIFIER CONFIRMED",
            "notes": ["area 13,290", "Q1/Q2 ratio 0.22", "file 240410_20.wiff"],
        },
    ]
    for index, panel in enumerate(panels):
        ox = 24 + (index % 4) * 444
        oy = 24 + (index // 4) * 548
        draw.rectangle((ox, oy, ox + 424, oy + 524), outline="#8b9298", width=2)
        draw.text((ox + 13, oy + 12), str(panel["title"]), font=title_font, fill="#17202a")
        x0, y0 = ox + 58, oy + 324
        x1, y1 = ox + 402, oy + 78
        draw.line((x0, y0, x1, y0), fill="#17202a", width=2)
        draw.line((x0, y0, x0, y1), fill="#17202a", width=2)
        for tick in range(0, 9, 2):
            x = x0 + int(tick / 8 * (x1 - x0))
            draw.line((x, y0, x, y0 + 8), fill="#17202a", width=1)
            draw.text((x - 5, y0 + 11), str(tick), font=tick_font, fill="#59636e")
        draw.text((ox + 175, oy + 351), "time (min)", font=note_font, fill="#303840")
        draw.text((ox + 6, oy + 185), "cps", font=note_font, fill="#303840")
        peak_x = x0 + int(float(panel["rt"]) / 8 * (x1 - x0))
        rng = random.Random(12_800 + index)
        trace: list[tuple[int, int]] = []
        for step in range(0, x1 - x0, 4):
            x = x0 + step
            base = rng.randint(-4, 4)
            distance = (x - peak_x) / 18
            height = int(int(panel["peak"]) * math.exp(-(distance * distance) / 2))
            trace.append((x, y0 - 13 - height + base))
        for first, second in zip(trace, trace[1:]):
            draw.line((*first, *second), fill=str(panel["color"]), width=2)
        draw.line((peak_x, y1, peak_x, y0), fill="#b9bec3", width=1)
        draw.text((peak_x - 33, y1 - 22), f"{float(panel['rt']):.2f} min", font=note_font, fill=str(panel["color"]))
        draw.rectangle((ox + 12, oy + 386, ox + 412, oy + 423), fill="#e9eded")
        draw.text((ox + 22, oy + 396), str(panel["state"]), font=note_font, fill=str(panel["color"]))
        for note_index, note in enumerate(panel["notes"]):
            draw.text((ox + 18, oy + 437 + note_index * 25), str(note), font=note_font, fill="#303840")
    return image


def _signed_correction_scan() -> Image.Image:
    """Visual-only QA amendment; the native LIMS table above it is stale."""
    image = Image.new("RGB", (1450, 610), "#f1efe8")
    draw = ImageDraw.Draw(image)
    title = _chart_font(27, bold=True)
    body = _chart_font(20)
    small = _chart_font(17)
    draw.rectangle((24, 22, 1424, 584), outline="#52575b", width=3)
    draw.text((55, 48), "QUALITY CORRECTION RECORD CR-24-044", font=title, fill="#24282b")
    draw.text((1030, 51), "CONTROLLED / SIGNED", font=small, fill="#9e2a2b")
    draw.line((55, 92, 1395, 92), fill="#73787c", width=2)
    lines = [
        "Scope: DW-240409-04 only. Other batch results are unchanged.",
        "Superseded source: PRELIM-LIMS-0419 entries derived from sequence 18 / IR-18A.",
        "Controlling source: accepted reinjection sequence 19 with integration IR-19B.",
        "Correct PFOA from 1.84 ng/L J to 1.06 ng/L J.",
        "PFOS remains <0.50 ng/L U; no qualifier change is authorized.",
        "Reason: sequence 18 internal-standard recovery was below the 50-150% criterion.",
        "Effective after technical and QA signatures below; do not overwrite the audit trail.",
    ]
    y = 126
    for line in lines:
        draw.text((65, y), line, font=body, fill="#24282b")
        y += 53
    draw.line((60, 510, 640, 510), fill="#777", width=1)
    draw.line((775, 510, 1360, 510), fill="#777", width=1)
    draw.text((72, 523), "Technical: L. Chen / 22 Apr 2024 09:40", font=small, fill="#24282b")
    draw.text((788, 523), "QA: R. Patel / 22 Apr 2024 16:10", font=small, fill="#24282b")
    draw.text((72, 554), "Linked records: SEQ-240410, IR-18A, IR-19B, MX-24-041", font=small, fill="#59636e")
    return _clean_scan(image, seed=12_110, blur=0.16)


def _schema_order_leaves(prefix: str, headers: Sequence[str], keys: Sequence[str]) -> list[dict]:
    return [
        leaf(
            f"{prefix}.schema",
            "The field schema is preserved in order: " + ", ".join(headers) + ".",
            claim_type="structure",
            evidence_policy={"type": "ordered_tokens", "tokens": [[header] for header in headers]},
        ),
        leaf(
            f"{prefix}.row-order",
            "The row order is preserved as: " + " -> ".join(keys) + ".",
            claim_type="ordered_record",
            evidence_policy={"type": "ordered_tokens", "tokens": [[key] for key in keys]},
        ),
    ]


def _table_gold(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    return markdown_table(headers, rows)


def build(output_root):
    calibration_panels: list[dict[str, object]] = [
        {
            "name": "PFOA",
            "levels": [0.25, 0.5, 1.0, 5.0, 20.0, 50.0, 80.0],
            "responses": [0.021, 0.040, 0.077, 0.406, 1.393, 3.731, 5.986],
            "residuals": [11.8, -6.1, 3.4, -2.8, 1.9, -4.2, 5.1],
            "color": "#1d4e89",
            "equation": "y = 0.0748x + 0.0021",
            "r2": "0.9986",
            "range": "0.25-80 ng/L",
            "review": "Max residual +11.8% at 0.25 ng/L (L1)",
            "disposition": "L1 retained - within the +/-20% lowest-level allowance",
        },
        {
            "name": "PFNA",
            "levels": [0.25, 0.5, 1.0, 5.0, 20.0, 50.0, 80.0],
            "responses": [0.018, 0.034, 0.070, 0.352, 1.411, 3.510, 5.621],
            "residuals": [-18.7, 9.2, -5.5, 3.1, -2.4, 4.8, -3.0],
            "color": "#6a4c93",
            "equation": "y = 0.0702x + 0.0008",
            "r2": "0.9964",
            "range": "0.25-80 ng/L",
            "review": "Max residual -18.7% at 0.25 ng/L (L1)",
            "disposition": "L1 retained - within the +/-20% lowest-level allowance",
        },
        {
            "name": "PFOS",
            "levels": [0.5, 1.0, 2.0, 10.0, 25.0, 50.0, 100.0],
            "responses": [0.042, 0.089, 0.184, 0.958, 2.392, 4.753, 8.177],
            "residuals": [-9.4, 4.1, -3.8, 2.5, -6.2, 7.9, 14.6],
            "color": "#2d6a4f",
            "equation": "y = 0.0831x + 0.0184",
            "r2": "0.9978",
            "range": "0.50-100 ng/L",
            "review": "Max residual +14.6% at 100 ng/L (L7)",
            "disposition": "Upper point retained - within the +/-15% criterion",
        },
        {
            "name": "PFHxS",
            "levels": [0.5, 1.0, 2.0, 10.0, 25.0, 50.0, 100.0],
            "responses": [0.038, 0.080, 0.162, 0.821, 2.049, 4.086, 8.169],
            "residuals": [7.2, -5.1, 3.7, -2.9, 2.1, -8.4, 4.6],
            "color": "#bc6c25",
            "equation": "y = 0.0817x + 0.0019",
            "r2": "0.9991",
            "range": "0.50-100 ng/L",
            "review": "Max residual -8.4% at 50 ng/L (L6)",
            "disposition": "All seven levels retained - no residual flag",
        },
        {
            "name": "6:2 FTS",
            "levels": [1.0, 2.0, 5.0, 10.0, 25.0, 50.0, 100.0],
            "responses": [0.052, 0.141, 0.269, 0.548, 1.361, 2.716, 5.433],
            "residuals": [-4.8, 23.6, 6.2, -3.1, 2.8, -5.9, 4.4],
            "color": "#9e2a2b",
            "equation": "y = 0.0544x + 0.0007",
            "r2": "0.9981 after L2 exclusion",
            "range": "1.00-100 ng/L",
            "excluded_index": 1,
            "review": "L2 residual +23.6% at 2.0 ng/L; vial bubble CAL-EX-06",
            "disposition": "L2 excluded; six-level refit accepted under signed exception",
        },
        {
            "name": "HFPO-DA",
            "levels": [0.5, 1.0, 2.0, 10.0, 20.0, 50.0, 80.0],
            "responses": [0.044, 0.086, 0.175, 0.790, 1.664, 4.400, 6.632],
            "residuals": [9.7, -6.8, 3.5, -4.2, 2.9, 6.1, -5.0],
            "color": "#007f8b",
            "equation": "y = 0.0830x + 0.0041",
            "r2": "0.9989",
            "range": "0.50-80 ng/L",
            "review": "Max residual +9.7% at 0.50 ng/L (L1)",
            "disposition": "All seven levels retained - no curvature flag",
        },
    ]
    case = CaseBuilder(
        output_root=output_root,
        case_id="P12-pfas-method-validation",
        title="PFAS Method Validation and Batch Release Packet",
        family="environmental analytical laboratory",
        tags=[
            "mixed-modality",
            "scientific",
            "calibration",
            "continued-table",
            "full-page-scans",
            "chromatograms",
            "source-precedence",
        ],
        page_count=12,
        purpose=(
            "Test exact scientific reconstruction across native tables, visual-only plots, full-page bench scans, "
            "continued tables, QC calculations, and a signed correction chain that changes one final result."
        ),
        source_modality=(
            "six native-only pages, three full-page raster scans, and three mixed pages with raster evidence; "
            "page images and native text are both necessary"
        ),
        document_ref="NORTHSTAR ANALYTICAL | MVS-PFAS-26-04 | controlled copy",
        metadata_date="D:20260618143000-07'00'",
    )
    case.set_page_modalities(
        native_pages=NATIVE_ONLY_PAGES,
        full_raster_pages=FULL_PAGE_SCAN_PAGES,
        mixed_pages=MIXED_PAGES,
    )

    # Page 1 - packet control, method record, source hierarchy, and a concise manifest.
    c = case.new_page(
        "Validation packet control and method scope",
        subtitle="North River drinking-water study | EPA 533 modified | Revision B",
        section_code="CONTROL 01",
    )
    draw_badge(c, "controlled copy", 42, 681, BLUE)
    control_headers = ["Field", "Controlled value"]
    control_rows = [
        ["Study", "MV-PFAS-24-017"],
        ["Instrument", "SCIEX 6500+ QTRAP; ESI negative"],
        ["Column", "BEH C18, 2.1 x 50 mm, 1.7 um"],
        ["Injection", "5 uL"],
        ["Study interval", "08-22 Apr 2024"],
        ["Reporting basis", "ng/L in original sample; U95 where quantified"],
    ]
    draw_label(c, "Controlled method record", 42, 654)
    draw_table(c, 42, 640, [130, 398], [control_headers, *control_rows], font_size=7.4, zebra=True)
    draw_label(c, "Source precedence", 42, 486)
    precedence = [
        ("Signed QA correction", "controls amended fields"),
        ("Accepted integration", "controls raw response"),
        ("LIMS export", "provisional until release"),
    ]
    for index, (name, note) in enumerate(precedence):
        x = 42 + index * 177
        c.setFillColor(HexColor("#F3F4F4"))
        c.setStrokeColor(HexColor("#9AA0A6"))
        c.roundRect(x, 425, 155, 42, 4, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("DocSans-Bold", 7)
        c.drawString(x + 8, 450, f"{index + 1}. {name}")
        c.setFont("DocSans", 6.3)
        c.setFillColor(MUTED)
        c.drawString(x + 8, 435, note)
        if index < len(precedence) - 1:
            draw_arrow(c, x + 155, 446, x + 173, 446, color=BLUE, width=0.9)
    manifest_headers = ["Sample ID", "Matrix", "Collected", "Received", "Preserved", "Release path"]
    manifest_rows = [
        ["FB-240408-01", "Field blank", "08 Apr 09:10", "08 Apr 15:42", "Trizma", "Routine"],
        ["DW-240408-02", "Finished water", "08 Apr 09:25", "08 Apr 15:42", "Trizma", "Routine"],
        ["DW-240408-03", "Finished water", "08 Apr 09:40", "08 Apr 15:42", "Trizma", "MS/MSD"],
        ["DW-240409-04", "Finished water", "09 Apr 10:05", "09 Apr 16:20", "Trizma", "Corrected"],
        ["DW-240409-05", "Finished water", "09 Apr 10:20", "09 Apr 16:20", "Trizma", "Routine"],
    ]
    draw_label(c, "Bottle manifest", 42, 386)
    draw_table(c, 42, 372, [93, 94, 82, 82, 69, 108], [manifest_headers, *manifest_rows], font_size=6.25, zebra=True)
    draw_paragraph(
        c,
        "Packet order is controlled; supporting bench records and field-level amendments remain part of the audit trail.",
        42,
        228,
        520,
        font="DocSans-Italic",
        size=7.6,
        leading=10.5,
        color=MUTED,
    )
    case.add_gold(
        "Page 1 - Validation packet control and method scope",
        _table_gold(control_headers, control_rows)
        + "\n\nSource precedence: signed QA correction > accepted integration > provisional LIMS export. "
        "A signed QA correction controls only the fields it amends.\n\n"
        + _table_gold(manifest_headers, manifest_rows),
    )
    case.add_region(
        "p01.control",
        "Controlled method record",
        "table",
        _schema_order_leaves("p01.control", control_headers, [row[0] for row in control_rows])
        + [
            leaf("p01.control.study", "The controlled study identifier is MV-PFAS-24-017."),
            leaf("p01.control.instrument", "The instrument is a SCIEX 6500+ QTRAP operated in ESI negative mode."),
            leaf("p01.control.reporting", "Results are reported in ng/L in the original sample, with U95 where quantified.", harm=2),
        ],
        budget=2,
    )
    case.add_region(
        "p01.precedence",
        "Source precedence diagram",
        "diagram",
        [
            source_precedence_leaf(
                "p01.precedence.order",
                "The precedence order is signed QA correction, then accepted integration, then provisional LIMS export.",
                ["signed QA correction", "accepted integration", "provisional LIMS export"],
                harm=2,
            ),
            leaf("p01.precedence.scope", "A signed QA correction controls only the fields it amends."),
        ],
        budget=2,
        modality="vector_geometry",
        primary_axis="source_precedence",
        secondary_axes=["chart_diagram_spatial"],
        text_only_recoverable=False,
    )
    case.add_region(
        "p01.manifest",
        "Bottle manifest",
        "table",
        _schema_order_leaves("p01.manifest", manifest_headers, [row[0] for row in manifest_rows])
        + [
            leaf("p01.manifest.d3", "DW-240408-03 follows the MS/MSD release path."),
            leaf("p01.manifest.d4", "DW-240409-04 follows the corrected release path.", harm=2),
        ],
    )

    # Page 2 - equations plus a nested transition/limit table.
    c = case.new_page(
        "Calibration model, transitions, and limits",
        subtitle="Quantifier and qualifier transitions; reporting limits apply to the original sample",
        section_code="CAL 02",
    )
    equations = [
        ("Response ratio", "R = A_native / A_IS"),
        ("Concentration", "C_sample = ((R - b) / m) x DF"),
        ("Spike recovery", "Recovery % = ((C_spiked - C_native) / C_added) x 100"),
        ("Expanded uncertainty", "U95 = 2 x sqrt(u_cal^2 + u_rep^2 + u_vol^2 + u_rec^2)"),
    ]
    for index, (label, formula) in enumerate(equations):
        x = 42 + (index % 2) * 266
        y = 646 - (index // 2) * 59
        draw_label(c, label, x, y + 24)
        c.setFillColor(HexColor("#F4F5F5"))
        c.roundRect(x, y - 2, 246, 34, 4, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("DocSans", 7.6)
        c.drawString(x + 9, y + 10, formula)
    cal_headers = ["Analyte", "Internal standard", "Quantifier", "Qualifier", "RT min", "Range ng/L", "LOD / LOQ ng/L"]
    cal_rows = [
        ["PFBA", "13C4-PFBA", "213>169", "213>119", "2.18", "0.50-80", "0.16 / 0.50"],
        ["PFPeA", "13C5-PFPeA", "263>219", "263>169", "2.74", "0.50-80", "0.13 / 0.50"],
        ["PFHxA", "13C5-PFHxA", "313>269", "313>119", "3.32", "0.50-80", "0.18 / 0.50"],
        ["PFHpA", "13C4-PFHpA", "363>319", "363>169", "3.86", "0.50-80", "0.15 / 0.50"],
        ["PFOA", "13C8-PFOA", "413>369", "413>169", "4.41", "0.25-80", "0.08 / 0.25"],
        ["PFNA", "13C9-PFNA", "463>419", "463>169", "4.95", "0.25-80", "0.09 / 0.25"],
        ["PFDA", "13C6-PFDA", "513>469", "513>219", "5.48", "0.25-80", "0.10 / 0.25"],
        ["PFBS", "18O2-PFBS", "299>80", "299>99", "3.05", "0.50-100", "0.17 / 0.50"],
        ["PFHxS", "18O2-PFHxS", "399>80", "399>99", "4.63", "0.50-100", "0.20 / 0.50"],
        ["PFOS", "13C8-PFOS", "499>80", "499>99", "5.64", "0.50-100", "0.22 / 0.50"],
        ["6:2 FTS", "13C2-6:2FTS", "427>407", "427>81", "5.19", "1.00-100", "0.31 / 1.00"],
        ["HFPO-DA", "13C3-HFPO-DA", "329>285", "329>169", "3.71", "0.50-80", "0.14 / 0.50"],
    ]
    group_row = ["Identity", "", "Transitions", "", "Retention", "Validated range", "Limits"]
    draw_label(c, "Transition and reporting-limit table", 42, 521)
    draw_table(c, 42, 507, [52, 89, 69, 68, 48, 86, 116], [group_row, cal_headers, *cal_rows], font_size=5.8, header_rows=2, group_header_rows=1, zebra=True)
    qualifier_headers = ["Symbol", "Meaning", "Rendering rule"]
    qualifier_rows = [
        ["U", "Not detected at the LOQ", "Preserve the leading < sign and LOQ"],
        ["J", "Estimated concentration", "Preserve the numeric value and J"],
        ["-", "No qualifier", "Do not invent a textual qualifier"],
    ]
    draw_label(c, "Qualifier contract", 42, 178)
    draw_table(c, 42, 165, [55, 185, 288], [qualifier_headers, *qualifier_rows], font_size=6.8, zebra=True)
    case.add_gold(
        "Page 2 - Calibration model, transitions, and limits",
        "Equations:\n"
        + "\n".join(f"- **{label}:** `{formula}`" for label, formula in equations)
        + "\n\nThe calibration table uses grouped headers for identity, transitions, retention, validated range, and limits.\n\n"
        + _table_gold(cal_headers, cal_rows)
        + "\n\n"
        + _table_gold(qualifier_headers, qualifier_rows),
    )
    case.add_region(
        "p02.equations",
        "Calibration and recovery equations",
        "text",
        [leaf(f"p02.eq.{index:02d}", f"{label} is written as {formula}.", harm=2 if label in {"Concentration", "Spike recovery"} else 1) for index, (label, formula) in enumerate(equations, start=1)],
        budget=2,
    )
    case.add_region(
        "p02.transitions",
        "Nested transition and limit table",
        "table",
        _schema_order_leaves("p02.transitions", cal_headers, [row[0] for row in cal_rows])
        + [
            table_binding_leaf("p02.pfoa.transitions", "For PFOA, Quantifier is 413>369.", "PFOA", "Quantifier", "413>369"),
            table_binding_leaf("p02.pfoa.transitions.qualifier", "For PFOA, Qualifier is 413>169.", "PFOA", "Qualifier", "413>169"),
            table_binding_leaf("p02.pfoa.binding", "For PFOA, Internal standard is 13C8-PFOA.", "PFOA", "Internal standard", "13C8-PFOA"),
            table_binding_leaf("p02.pfoa.binding.rt", "For PFOA, RT min is 4.41.", "PFOA", "RT min", "4.41"),
            table_binding_leaf("p02.pfoa.binding.range", "For PFOA, Range ng/L is 0.25-80.", "PFOA", "Range ng/L", "0.25-80"),
            table_binding_leaf("p02.pfoa.binding.lod-loq", "For PFOA, LOD / LOQ ng/L is 0.08 / 0.25.", "PFOA", "LOD / LOQ ng/L", "0.08 / 0.25", harm=2),
            table_binding_leaf("p02.pfos.binding", "For PFOS, Internal standard is 13C8-PFOS.", "PFOS", "Internal standard", "13C8-PFOS"),
            table_binding_leaf("p02.pfos.binding.rt", "For PFOS, RT min is 5.64.", "PFOS", "RT min", "5.64"),
            table_binding_leaf("p02.pfos.binding.range", "For PFOS, Range ng/L is 0.50-100.", "PFOS", "Range ng/L", "0.50-100"),
            table_binding_leaf("p02.pfos.binding.lod-loq", "For PFOS, LOD / LOQ ng/L is 0.22 / 0.50.", "PFOS", "LOD / LOQ ng/L", "0.22 / 0.50", harm=2),
            table_binding_leaf("p02.hfpo.binding", "For HFPO-DA, Internal standard is 13C3-HFPO-DA.", "HFPO-DA", "Internal standard", "13C3-HFPO-DA"),
            table_binding_leaf("p02.hfpo.binding.quantifier", "For HFPO-DA, Quantifier is 329>285.", "HFPO-DA", "Quantifier", "329>285"),
            table_binding_leaf("p02.hfpo.binding.qualifier", "For HFPO-DA, Qualifier is 329>169.", "HFPO-DA", "Qualifier", "329>169"),
            table_binding_leaf("p02.hfpo.binding.rt", "For HFPO-DA, RT min is 3.71.", "HFPO-DA", "RT min", "3.71"),
            table_binding_leaf("p02.fts.limit", "For 6:2 FTS, LOD / LOQ ng/L is 0.31 / 1.00.", "6:2 FTS", "LOD / LOQ ng/L", "0.31 / 1.00"),
        ],
        budget=2,
    )
    case.add_region(
        "p02.qualifiers",
        "Qualifier contract",
        "table",
        [
            leaf("p02.qual.u", "U means not detected at the LOQ; preserve the leading < sign and the LOQ.", harm=2),
            leaf("p02.qual.j", "J means estimated concentration; preserve both the numeric value and J.", harm=2),
            leaf(
                "p02.qual.none",
                "A dash means no qualifier and must not be expanded into an invented qualifier.",
                evidence_policy={"type": "lexical", "allOf": [["-", "dash"], ["no qualifier"], ["do not invent", "must not invent", "not expanded"]]},
            ),
        ],
    )

    # Page 3 - one crowded calibration review plate. The per-analyte equations,
    # residuals, excluded-standard state, and point bindings exist only inside
    # the raster plate; native text supplies the general acceptance rule only.
    c = case.new_page(
        "Calibration curves and residual disposition",
        subtitle="Six-analyte weighted review | fit, residual, and exclusion disposition",
        section_code="FIGURE 03",
    )
    plate = _calibration_plate(calibration_panels)
    c.drawImage(image_reader(plate), 42, 280, width=528, height=340, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(HexColor("#9AA0A6"))
    c.rect(42, 280, 528, 340, fill=0, stroke=1)
    draw_label(c, "Method acceptance rule", 42, 246)
    draw_paragraph(
        c,
        "Use weighted 1/x^2. Accept R2 >= 0.995 and each included back-calculated standard within +/-15%; the lowest included level may be within +/-20%. A standard may be excluded only under a signed, source-visible exception.",
        42,
        230,
        520,
        size=7.8,
        leading=10.7,
    )
    draw_paragraph(
        c,
        "Panel-specific fit, exclusion, and residual disposition are recorded in Figure 03; the signed calibration exception log controls exclusions.",
        42,
        174,
        520,
        font="DocSans-Italic",
        size=7.5,
        leading=10.4,
        color=MUTED,
    )

    panel_gold: list[str] = []
    for panel in calibration_panels:
        levels = [float(value) for value in panel["levels"]]  # type: ignore[index]
        responses = [float(value) for value in panel["responses"]]  # type: ignore[index]
        residuals = [float(value) for value in panel["residuals"]]  # type: ignore[index]
        panel_gold.append(
            f"- **{panel['name']}** - {panel['equation']}; R2 {panel['r2']}; range {panel['range']}. "
            f"Levels: {', '.join(f'{value:g}' for value in levels)} ng/L. "
            f"Responses: {', '.join(f'{value:.3f}' for value in responses)}. "
            f"Residuals: {', '.join(f'{value:+.1f}%' for value in residuals)}. "
            f"Review: {panel['review']}. Disposition: {panel['disposition']}."
        )
    case.add_gold(
        "Page 3 - Calibration curves and residual disposition",
        "Figure 03 is a 2x3 raster calibration-review plate in this panel order: PFOA, PFNA, PFOS, PFHxS, 6:2 FTS, HFPO-DA. Filled circles are included standards, an open diamond is an excluded standard, and inset bars are back-calculated residual percentages. The horizontal axis is log concentration in ng/L and the vertical axis is response ratio.\n\n"
        + "\n".join(panel_gold)
        + "\n\nThe general method rule is weighted 1/x^2, R2 >= 0.995, included standards within +/-15%, and the lowest included standard within +/-20%. Only the 6:2 FTS 2.0 ng/L L2 standard is excluded, under the source-visible CAL-EX-06 vial-bubble exception; the six-level refit is accepted.",
    )

    calibration_leaves: list[dict] = [
        leaf(
            "p03.chart.axes",
            "Figure 03 uses log concentration in ng/L on the horizontal axis and response ratio on the vertical axis.",
            harm=2,
            claim_type="structure",
        ),
        leaf(
            "p03.chart.encoding",
            "Filled circles are included standards, an open diamond is an excluded standard, and inset bars encode back-calculated residual percent.",
            harm=2,
            claim_type="structure",
        ),
        leaf(
            "p03.chart.panel-order",
            "The panel order is PFOA -> PFNA -> PFOS -> PFHxS -> 6:2 FTS -> HFPO-DA.",
            claim_type="ordered_record",
            evidence_policy={
                "type": "ordered_tokens",
                "tokens": [["PFOA"], ["PFNA"], ["PFOS"], ["PFHxS"], ["6:2 FTS"], ["HFPO-DA"]],
            },
        ),
        leaf(
            "p03.chart.rule",
            "The review uses weighted 1/x^2, requires R2 >= 0.995, requires included standards within +/-15%, and permits the lowest included standard within +/-20%.",
            harm=2,
        ),
    ]
    residual_leaves: list[dict] = []
    for panel in calibration_panels:
        name = str(panel["name"])
        slug = name.lower().replace(":", "").replace(" ", "-")
        levels = [float(value) for value in panel["levels"]]  # type: ignore[index]
        responses = [float(value) for value in panel["responses"]]  # type: ignore[index]
        calibration_leaves.extend(
            [
                leaf(
                    f"p03.fit.{slug}",
                    f"{name} uses {panel['equation']} with R2 {panel['r2']} over {panel['range']}.",
                    harm=2 if name == "6:2 FTS" else 1,
                ),
                leaf(
                    f"p03.curve.{slug}.low",
                    f"{name} binds its low standard {levels[0]:g} ng/L to response ratio {responses[0]:.3f}.",
                ),
                leaf(
                    f"p03.curve.{slug}.mid",
                    f"{name} binds its middle standard {levels[3]:g} ng/L to response ratio {responses[3]:.3f}.",
                ),
                leaf(
                    f"p03.curve.{slug}.high",
                    f"{name} binds its high standard {levels[-1]:g} ng/L to response ratio {responses[-1]:.3f}.",
                ),
            ]
        )
        residual_leaves.append(
            leaf(
                f"p03.residual.{slug}",
                f"For {name}, {panel['review']}; {panel['disposition']}.",
                harm=2 if name in {"PFNA", "6:2 FTS"} else 1,
            )
        )
    case.add_region(
        "p03.calibration-panels",
        "Six-panel calibration curves and point bindings",
        "chart",
        calibration_leaves,
        budget=3,
        modality="mixed",
        primary_axis="chart_diagram_spatial",
        text_only_recoverable=False,
    )
    case.add_region(
        "p03.residual-review",
        "Per-analyte residual and excluded-standard state",
        "chart",
        residual_leaves,
        budget=2,
        modality="mixed",
        primary_axis="chart_diagram_spatial",
        secondary_axes=["source_precedence"],
        text_only_recoverable=False,
    )

    # Pages 4-5 - one continued validation table, intentionally split at PFNA/PFDA.
    precision_headers = ["Analyte", "Low rec / RSD %", "Mid rec / RSD %", "High rec / RSD %", "n", "State"]
    precision_rows = [
        ["PFBA", "96.0 / 8.4", "101.0 / 4.6", "99.0 / 3.8", "7", "Pass"],
        ["PFPeA", "93.0 / 9.1", "98.0 / 5.2", "101.0 / 4.1", "7", "Pass"],
        ["PFHxA", "91.0 / 10.3", "97.0 / 5.8", "100.0 / 4.3", "7", "Pass"],
        ["PFHpA", "95.0 / 7.9", "99.0 / 4.9", "102.0 / 4.0", "7", "Pass"],
        ["PFOA", "98.0 / 6.8", "103.0 / 3.7", "101.0 / 3.2", "7", "Pass"],
        ["PFNA", "97.0 / 7.2", "102.0 / 4.1", "100.0 / 3.6", "7", "Pass"],
        ["PFDA", "92.0 / 11.5", "96.0 / 6.3", "99.0 / 4.9", "7", "Pass"],
        ["PFBS", "104.0 / 9.7", "99.0 / 4.8", "98.0 / 4.0", "7", "Pass"],
        ["PFHxS", "101.0 / 8.9", "100.0 / 4.4", "97.0 / 3.9", "7", "Pass"],
        ["PFOS", "89.0 / 12.6", "95.0 / 6.7", "96.0 / 5.1", "7", "Pass"],
        ["6:2 FTS", "86.0 / 14.8", "92.0 / 7.4", "94.0 / 6.3", "7", "Pass"],
        ["HFPO-DA", "99.0 / 7.5", "104.0 / 4.2", "103.0 / 3.5", "7", "Pass"],
    ]
    c = case.new_page(
        "Table V4 - Accuracy and precision",
        subtitle="Part 1 of 2 | fortified reagent water | recovery / RSD in percent",
        section_code="TABLE 04",
    )
    draw_table(c, 42, 665, [74, 112, 112, 112, 38, 80], [precision_headers, *precision_rows[:6]], font_size=6.8, zebra=True)
    draw_label(c, "Study design and acceptance", 42, 420)
    design_headers = ["Level", "Nominal basis", "Replicates", "Recovery", "RSD"]
    design_rows = [
        ["Low", "LOQ or 2 x LOQ", "7 on 7 days", "70-130%", "<=20%"],
        ["Mid", "10 ng/L", "7 on 7 days", "70-130%", "<=20%"],
        ["High", "80 ng/L", "7 on 7 days", "70-130%", "<=20%"],
    ]
    draw_table(c, 42, 406, [70, 130, 108, 105, 115], [design_headers, *design_rows], font_size=7.1, zebra=True)
    draw_paragraph(c, "Continuation boundary: PFDA through HFPO-DA appear on page 5 under repeated column headers.", 42, 272, 520, font="DocSans-Italic", size=8, leading=11, color=MUTED)
    case.add_gold(
        "Page 4 - Table V4 accuracy and precision, part 1",
        _table_gold(precision_headers, precision_rows[:6])
        + "\n\n"
        + _table_gold(design_headers, design_rows)
        + "\n\nTable V4 continues on page 5 with PFDA through HFPO-DA and repeated headers.",
    )
    case.add_region(
        "p04.precision",
        "Table V4 rows PFBA through PFNA",
        "table",
        _schema_order_leaves("p04.precision", precision_headers, [row[0] for row in precision_rows[:6]])
        + [
            leaf("p04.precision.pfoa", "PFOA low/mid/high recovery and RSD pairs are 98.0/6.8, 103.0/3.7, and 101.0/3.2%, with n=7 and state Pass.", harm=2),
            leaf("p04.precision.pfhxa", "PFHxA low recovery/RSD is 91.0/10.3%, with n=7 and state Pass."),
        ],
        budget=2,
    )
    case.add_region(
        "p04.design",
        "Validation study design",
        "table",
        [
            leaf("p04.design.low", "The low level is LOQ or 2 x LOQ, with 7 replicates on 7 days."),
            leaf("p04.design.acceptance", "All levels require 70-130% recovery and RSD <=20%.", harm=2),
            leaf("p04.design.continues", "Table V4 continues on page 5 with PFDA through HFPO-DA under repeated headers.", harm=2),
        ],
    )

    c = case.new_page(
        "Table V4 - Accuracy and precision (continued)",
        subtitle="Part 2 of 2 | repeated headers are structural, not data rows",
        section_code="TABLE 05",
    )
    draw_table(c, 42, 665, [74, 112, 112, 112, 38, 80], [precision_headers, *precision_rows[6:]], font_size=6.8, zebra=True)
    exception_headers = ["Record", "Affected result", "Observation", "Disposition"]
    exception_rows = [
        ["EX-24-011", "6:2 FTS low-level day 2", "61% recovery", "Excluded: fortification omitted"],
        ["EX-24-014", "PFOS low-level day 6", "89% recovery; 12.6% RSD", "Retained: within criteria"],
        ["EX-24-017", "HFPO-DA mid day 4", "104% recovery", "Retained: within criteria"],
    ]
    draw_label(c, "Exception register linked to Table V4", 42, 414)
    draw_table(c, 42, 400, [82, 133, 149, 164], [exception_headers, *exception_rows], font_size=6.65, zebra=True)
    draw_paragraph(c, "EX-24-011 is not part of n=7. The valid replacement replicate is included in the 86.0% low-level mean.", 42, 270, 520, font="DocSans-Bold", size=7.8, leading=11, color=RED)
    case.add_gold(
        "Page 5 - Table V4 accuracy and precision, part 2",
        "This page continues Table V4 from page 4; the repeated headers are not data rows.\n\n"
        + _table_gold(precision_headers, precision_rows[6:])
        + "\n\n"
        + _table_gold(exception_headers, exception_rows)
        + "\n\nEX-24-011 is excluded from n=7; its valid replacement contributes to the 86.0% 6:2 FTS low-level mean.",
    )
    case.add_region(
        "p05.precision",
        "Continued Table V4 rows PFDA through HFPO-DA",
        "table",
        _schema_order_leaves("p05.precision", precision_headers, [row[0] for row in precision_rows[6:]])[1:]
        + [
            leaf("p05.precision.pfos", "PFOS low/mid/high recovery and RSD pairs are 89.0/12.6, 95.0/6.7, and 96.0/5.1%, with n=7 and state Pass.", harm=2),
            leaf("p05.precision.fts", "6:2 FTS low/mid/high recovery and RSD pairs are 86.0/14.8, 92.0/7.4, and 94.0/6.3%, with n=7 and state Pass.", harm=2),
            leaf("p05.precision.continuation", "This is the continuation of page 4 Table V4; repeated headers are not data rows.", harm=2),
        ],
        budget=2,
    )
    case.add_region(
        "p05.exceptions",
        "Validation exception register",
        "table",
        [
            leaf("p05.exception.ex11", "EX-24-011 is the omitted-fortification 6:2 FTS low-level day-2 result at 61% recovery."),
            leaf("p05.exception.ex11.disposition", "EX-24-011 is excluded from n=7 and replaced by a valid replicate included in the 86.0% mean.", harm=2),
            leaf("p05.exception.ex14", "EX-24-014 retains the PFOS low-level day-6 result because 89% recovery and 12.6% RSD are within criteria."),
        ],
        budget=2,
    )

    # Page 6 - preparation and dilution bench record. The assembly step turns
    # this complete page into an image-only scan; no separate native summary is
    # drawn elsewhere in the packet.
    c = case.new_page(
        "Extraction, fortification, and dilution bench record",
        subtitle="Working bench copy | handwritten checks transcribed at review",
        section_code="BENCH 06",
    )
    draw_badge(c, "bench original", 42, 681, AMBER)
    prep_headers = ["Prep ID", "Material / sample", "Initial", "Aliquot", "Final", "Recorded target / DF"]
    prep_rows = [
        ["SPK-01", "LCS mixed native spike", "1.000 ng/uL", "10.00 uL", "1.000 L", "10.00 ng/L"],
        ["SPK-02", "MS/MSD mixed native spike", "1.000 ng/uL", "10.00 uL", "1.000 L", "10.00 ng/L"],
        ["DIL-03", "DW-240408-03 extract", "1.000 mL", "0.500 mL", "5.000 mL", "DF 10.00"],
        ["DIL-04", "DW-240409-04 original extract", "1.000 mL", "1.000 mL", "1.000 mL", "DF 1.00"],
        ["DIL-05", "DW-240409-04 reinjection vial", "0.800 mL", "0.400 mL", "0.800 mL", "DF 2.00"],
    ]
    draw_label(c, "Preparation ledger", 42, 648)
    draw_table(c, 42, 634, [63, 150, 76, 68, 68, 103], [prep_headers, *prep_rows], font_size=6.5, zebra=True, vertical_rules=True)
    bottle_headers = ["Sample", "Bottle mL", "Extract mL", "SPE lot", "Surrogate added", "Analyst check"]
    bottle_rows = [
        ["LRB-240410-01", "250.0", "1.000", "SPE-24-118", "50.0 uL", "MI 10 Apr 08:04"],
        ["LCS-240410-01", "250.0", "1.000", "SPE-24-118", "50.0 uL", "MI 10 Apr 08:08"],
        ["DW-240408-03", "249.0", "1.000", "SPE-24-118", "50.0 uL", "MI 10 Apr 08:17"],
        ["DW-240409-04", "250.0", "1.000", "SPE-24-118", "50.0 uL", "MI 10 Apr 08:23"],
    ]
    draw_label(c, "Extraction ledger", 42, 440)
    draw_table(c, 42, 426, [102, 74, 72, 87, 92, 101], [bottle_headers, *bottle_rows], font_size=6.45, zebra=True, vertical_rules=True)
    draw_label(c, "Bench annotations", 42, 284)
    notes = [
        "SPK-01 and SPK-02 verified against CRM certificate PFAS-MIX-2319, expiry 30 Sep 2024.",
        "DIL-05 prepared only after reinjection authorization MX-24-041; keep DIL-04 vial in audit storage.",
        "Balance check 10.0002 g against 10.0000 g; pipette P100 verification 99.6 uL at 20.1 C.",
    ]
    y = 262
    for note in notes:
        draw_paragraph(c, f"[x] {note}", 52, y, 500, size=7.5, leading=10.4)
        y -= 38
    c.setStrokeColor(HexColor("#777777"))
    c.line(52, 111, 265, 111)
    c.line(326, 111, 548, 111)
    c.setFillColor(INK)
    c.setFont("DocSans-Italic", 8)
    c.drawString(58, 94, "M. Iyer / analyst / 10 Apr 2024 08:42")
    c.drawString(332, 94, "L. Chen / witness / 10 Apr 2024 08:51")
    case.add_gold(
        "Page 6 - Scanned extraction, fortification, and dilution record",
        _table_gold(prep_headers, prep_rows)
        + "\n\n"
        + _table_gold(bottle_headers, bottle_rows)
        + "\n\n"
        + "\n".join(f"- {note}" for note in notes)
        + "\n\nAnalyst M. Iyer signed 10 Apr 2024 08:42; witness L. Chen signed 10 Apr 2024 08:51.",
    )
    case.add_region(
        "p06.preparation",
        "Scanned preparation ledger",
        "form",
        _schema_order_leaves("p06.prep", prep_headers, [row[0] for row in prep_rows])
        + [
            leaf("p06.prep.spk01", "SPK-01 uses 1.000 ng/uL stock, 10.00 uL aliquot, and 1.000 L final volume for a 10.00 ng/L LCS target.", harm=2),
        ]
        + table_leaves(
            "p06.prep",
            prep_headers,
            prep_rows,
            scored_bindings={
                ("DIL-03", "Final"),
                ("DIL-03", "Recorded target / DF"),
                ("DIL-05", "Final"),
                ("DIL-05", "Recorded target / DF"),
            },
            consequential={
                ("DIL-05", "Final"),
                ("DIL-05", "Recorded target / DF"),
            },
        )[2:],
        budget=2,
    )
    case.add_region(
        "p06.extraction",
        "Scanned extraction ledger and signatures",
        "form",
        [
            leaf("p06.extraction.d3", "DW-240408-03 uses 249.0 mL bottle volume, 1.000 mL extract, SPE lot SPE-24-118, and 50.0 uL surrogate."),
            leaf("p06.extraction.crm", "SPK-01 and SPK-02 are verified against CRM certificate PFAS-MIX-2319 expiring 30 Sep 2024."),
            leaf("p06.extraction.storage", "DIL-05 was prepared after MX-24-041; the DIL-04 vial remains in audit storage.", harm=2),
            leaf("p06.extraction.signatures", "M. Iyer signed at 08:42 and L. Chen witnessed at 08:51 on 10 Apr 2024."),
        ],
        budget=2,
    )

    # Page 7 - signed sequence scan. Sequence 18/19 meaning exists only here and
    # in later source-control artifacts; there is no native explanatory caption.
    c = case.new_page(
        "LC-MS/MS sequence and technical review",
        subtitle="Batch 240410 | signed sequence sheet",
        section_code="SEQUENCE 07",
    )
    sequence_headers = ["Seq", "Type", "Vial", "Sample / control", "Start", "IS rec", "Carryover", "State"]
    sequence_rows = [
        ["09", "Cal", "A09", "CAL-80", "09:54", "103%", "Clear", "Accepted"],
        ["10", "Blank", "B01", "LRB-240410-01", "10:07", "97%", "Clear", "Accepted"],
        ["11", "LCS", "B02", "LCS-240410-01", "10:20", "94%", "Clear", "Accepted"],
        ["12", "Sample", "B03", "FB-240408-01", "10:33", "96%", "Clear", "Accepted"],
        ["13", "Sample", "B04", "DW-240408-02", "10:46", "92%", "Clear", "Accepted"],
        ["14", "Sample", "B05", "DW-240408-03", "10:59", "89%", "Clear", "Accepted"],
        ["15", "MS", "B06", "DW-240408-03-MS", "11:12", "93%", "Clear", "Accepted"],
        ["16", "MSD", "B07", "DW-240408-03-MSD", "11:25", "90%", "Clear", "Accepted"],
        ["17", "CCV", "B08", "CCV-10", "11:38", "95%", "Clear", "Accepted"],
        ["18", "Sample", "B09", "DW-240409-04", "11:51", "38%", "Clear", "HOLD MX-24-041"],
        ["19", "Sample", "C01", "DW-240409-04-RI", "12:18", "91%", "Clear", "Accepted"],
        ["20", "Sample", "C02", "DW-240409-05", "12:31", "88%", "Clear", "Accepted"],
        ["21", "CCV", "C03", "CCV-10-CLOSE", "12:44", "93%", "Clear", "Accepted"],
    ]
    draw_table(c, 42, 674, [38, 49, 39, 138, 48, 52, 72, 92], [sequence_headers, *sequence_rows], font_size=6.1, zebra=True, vertical_rules=True)
    incident_headers = ["Linked item", "Entry"]
    incident_rows = [
        ["MX-24-041", "Opened 11:58 after sequence 18 IS recovery fell below 50%"],
        ["Authorization", "One reinjection after blank and needle-seat flush"],
        ["Control rule", "If reinjection IS is 50-150%, retain original only in audit trail"],
        ["Review mark", "Sequence 19 circled; sequence 18 struck once, still legible"],
    ]
    draw_label(c, "Technical review annotations", 42, 326)
    draw_table(c, 42, 312, [100, 428], [incident_headers, *incident_rows], font_size=6.7, zebra=True)
    c.setStrokeColor(HexColor("#777777"))
    c.line(52, 133, 263, 133)
    c.line(326, 133, 548, 133)
    c.setFillColor(INK)
    c.setFont("DocSans-Italic", 8)
    c.drawString(58, 115, "M. Iyer / analyst / 19 Apr 2024 14:05")
    c.drawString(332, 115, "L. Chen / technical / 22 Apr 2024 09:40")
    case.add_gold(
        "Page 7 - Scanned LC-MS/MS sequence and technical review",
        _table_gold(sequence_headers, sequence_rows)
        + "\n\n"
        + _table_gold(incident_headers, incident_rows)
        + "\n\nSequence 18 is held under MX-24-041 at 38% IS recovery. Sequence 19 is the accepted reinjection at 91% IS recovery. Analyst M. Iyer signed 19 Apr 2024 14:05 and technical reviewer L. Chen signed 22 Apr 2024 09:40.",
    )
    case.add_region(
        "p07.sequence",
        "Scanned instrument sequence",
        "form",
        _schema_order_leaves("p07.sequence", sequence_headers, [row[0] for row in sequence_rows])
        + [
            leaf("p07.sequence.17", "Sequence 17 is CCV-10 at 11:38 with 95% IS recovery and Accepted state."),
            leaf("p07.sequence.21", "Sequence 21 is closing CCV-10-CLOSE at 12:44 with 93% IS recovery and Accepted state."),
        ],
        budget=2,
    )
    case.add_region(
        "p07.review",
        "Scanned sequence review annotations",
        "form",
        [
            leaf("p07.review.trigger", "MX-24-041 opened at 11:58 because sequence 18 IS recovery was below 50%."),
            leaf("p07.review.authorization", "The authorization permits one reinjection after a blank and needle-seat flush."),
            leaf("p07.review.rule", "If reinjection IS is 50-150%, the original remains only in the audit trail.", harm=2),
            leaf("p07.review.signatures", "M. Iyer signed 19 Apr 2024 14:05; L. Chen signed technical review 22 Apr 2024 09:40."),
        ],
        budget=2,
    )

    # Page 8 - a crowded integration contact sheet. The native register maps
    # panel IDs to injection/channel only; visual annotations carry all trace
    # measurements, review state, and accepted-versus-rejected meaning.
    c = case.new_page(
        "Raw integration and chromatogram review",
        subtitle="Eight-panel quantifier, qualifier, and internal-standard review",
        section_code="INTEGRATION 08",
    )
    chrom = _chromatogram_plate()
    c.drawImage(image_reader(chrom), 42, 330, width=528, height=329, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(HexColor("#9AA0A6"))
    c.rect(42, 330, 528, 329, fill=0, stroke=1)
    routing_headers = ["Panel", "Injection", "Trace channel", "Review role"]
    routing_rows = [
        ["A", "Seq 10", "PFOS Q1", "Reagent blank"],
        ["B", "Seq 14", "PFOA Q1", "Batch sample"],
        ["C", "Seq 18", "13C8-PFOA IS", "Original internal standard"],
        ["D", "Seq 19", "13C8-PFOA IS", "Reinjection internal standard"],
        ["E", "Seq 18", "PFOA Q1", "Original quantifier"],
        ["F", "Seq 19", "PFOA Q1", "Reinjection quantifier"],
        ["G", "Seq 21", "PFOA Q1", "Closing CCV"],
        ["H", "Seq 20", "6:2 FTS Q2", "Qualifier review"],
    ]
    draw_label(c, "Integration cross-reference index", 42, 298)
    draw_table(c, 42, 284, [48, 82, 154, 244], [routing_headers, *routing_rows], font_size=6.2, zebra=True)
    draw_paragraph(c, "The index cross-references injection and trace channel. Signed instrument annotations are the controlled source for retention time, area, ratio, recovery, file, and review state.", 42, 88, 520, font="DocSans-Italic", size=7.1, leading=9.8, color=MUTED)
    case.add_gold(
        "Page 8 - Raw integration and chromatogram review",
        "Instrument panel evidence:\n"
        "- Panel A, LRB-240410-01 / PFOS Q1: 5.64 min, noise 38-44 cps, file 240410_10.wiff, no integration, NO PEAK / BLANK ACCEPTED.\n"
        "- Panel B, DW-240408-03 / PFOA Q1: 4.41 min, area 25,621, Q1/Q2 ratio 0.31, file 240410_14.wiff, ACCEPTED / FINAL BATCH RESULT.\n"
        "- Panel C, DW-240409-04 / 13C8-PFOA IS: 4.39 min, IS recovery 38%, IR-18A, file 240410_18.wiff, SEQ 18 HOLD / ORIGINAL REJECTED.\n"
        "- Panel D, DW-240409-04-RI / 13C8-PFOA IS: 4.40 min, IS recovery 91%, IR-19B, file 240410_19.wiff, SEQ 19 ACCEPTED / CONTROLLING.\n"
        "- Panel E, DW-240409-04 / PFOA Q1: 4.42 min, area 11,180, Q1/Q2 ratio 0.27, IR-18A linked, SEQ 18 NOT REPORTABLE.\n"
        "- Panel F, DW-240409-04-RI / PFOA Q1: 4.41 min, area 8,420, Q1/Q2 ratio 0.30, IR-19B linked, SEQ 19 ACCEPTED / 1.06 ng/L J.\n"
        "- Panel G, CCV-10-CLOSE / PFOA Q1: 4.41 min, back-calculated 10.31 ng/L, area 80,755, file 240410_21.wiff, ACCEPTED / 103.1% RECOVERY.\n"
        "- Panel H, DW-240409-05 / 6:2 FTS Q2: 5.18 min, area 13,290, Q1/Q2 ratio 0.22, file 240410_20.wiff, REVIEWED / QUALIFIER CONFIRMED.\n\n"
        + _table_gold(routing_headers, routing_rows)
        + "\n\nThe native index supplies injection and channel identity only; the visual plate controls trace measurements and review state.",
    )
    chromatogram_claims = [
        ("a", "Panel A is LRB-240410-01 / PFOS Q1.", "5.64", "noise is 38-44 cps", "there is no integration and the file is 240410_10.wiff", "NO PEAK / BLANK ACCEPTED"),
        ("b", "Panel B is DW-240408-03 / PFOA Q1.", "4.41", "area is 25,621", "Q1/Q2 ratio is 0.31 and the file is 240410_14.wiff", "ACCEPTED / FINAL BATCH RESULT"),
        ("c", "Panel C is DW-240409-04 / 13C8-PFOA IS.", "4.39", "IS recovery is 38%", "IR-18A is linked to file 240410_18.wiff", "SEQ 18 HOLD / ORIGINAL REJECTED"),
        ("d", "Panel D is DW-240409-04-RI / 13C8-PFOA IS.", "4.40", "IS recovery is 91%", "IR-19B is linked to file 240410_19.wiff", "SEQ 19 ACCEPTED / CONTROLLING"),
        ("e", "Panel E is DW-240409-04 / PFOA Q1.", "4.42", "area is 11,180", "Q1/Q2 ratio is 0.27 and IR-18A is linked", "SEQ 18 NOT REPORTABLE"),
        ("f", "Panel F is DW-240409-04-RI / PFOA Q1.", "4.41", "area is 8,420", "Q1/Q2 ratio is 0.30 and IR-19B is linked", "SEQ 19 ACCEPTED / 1.06 ng/L J"),
        ("g", "Panel G is CCV-10-CLOSE / PFOA Q1.", "4.41", "back-calculated concentration is 10.31 ng/L", "area is 80,755 and the file is 240410_21.wiff", "ACCEPTED / 103.1% RECOVERY"),
        ("h", "Panel H is DW-240409-05 / 6:2 FTS Q2.", "5.18", "area is 13,290", "Q1/Q2 ratio is 0.22 and the file is 240410_20.wiff", "REVIEWED / QUALIFIER CONFIRMED"),
    ]
    chromatogram_leaves: list[dict] = []
    for slug, binding, rt, measure_a, measure_b, state in chromatogram_claims:
        panel_name = slug.upper()
        chromatogram_leaves.extend(
            [
                leaf(f"p08.chrom.{slug}.binding", binding),
                leaf(f"p08.chrom.{slug}.rt", f"Panel {panel_name} marks retention time {rt} min."),
                leaf(f"p08.chrom.{slug}.measure-a", f"For Panel {panel_name}, {measure_a}."),
                leaf(f"p08.chrom.{slug}.measure-b", f"For Panel {panel_name}, {measure_b}."),
                leaf(
                    f"p08.chrom.{slug}.state",
                    f"Panel {panel_name} is marked {state}.",
                    harm=2 if slug in {"c", "d", "e", "f"} else 1,
                ),
            ]
        )
    case.add_region(
        "p08.chromatograms",
        "Eight-panel chromatogram and integration contact sheet",
        "image",
        chromatogram_leaves,
        budget=4,
        modality="raster",
        primary_axis="image_description",
        secondary_axes=["source_precedence", "mixed_modality_fusion"],
        text_only_recoverable=False,
    )
    case.add_region(
        "p08.routing",
        "Native panel-to-injection index",
        "table",
        _schema_order_leaves("p08.routing", routing_headers, [row[0] for row in routing_rows])
        + [
            table_binding_leaf(f"p08.routing.{panel.lower()}.injection", f"For Panel {panel}, Injection is {injection}.", panel, "Injection", injection)
            for panel, injection, _, _ in routing_rows
        ]
        + [
            table_binding_leaf(f"p08.routing.{panel.lower()}.channel", f"For Panel {panel}, Trace channel is {channel}.", panel, "Trace channel", channel)
            for panel, _, channel, _ in routing_rows
            if panel in {"C", "D", "E", "F", "G", "H"}
        ]
        + [
            leaf("p08.routing.boundary", "The native index supplies injection and channel identity only; visual annotations control trace measurements and review state."),
        ],
    )

    # Page 9 - native QC evidence. Recovery must be computed by joining the
    # 10.00 ng/L targets on page 6 with these measured values.
    c = case.new_page(
        "Blank, recovery, and continuing-calibration review",
        subtitle="Measured values shown here; fortification targets are controlled by the page 6 bench record",
        section_code="QC 09",
    )
    qc_headers = ["Control", "Analyte", "Measured", "Review criterion", "Review state"]
    qc_rows = [
        ["LRB-240410-01", "PFOA", "<0.25 ng/L U", "<0.25 ng/L", "Meets"],
        ["LRB-240410-01", "PFOS", "<0.50 ng/L U", "<0.50 ng/L", "Meets"],
        ["LCS-240410-01", "PFOA", "9.62 ng/L", "70-130% recovery", "Calculate from SPK-01"],
        ["LCS-240410-01", "PFOS", "9.14 ng/L", "70-130% recovery", "Calculate from SPK-01"],
        ["DW-240408-03-MS", "PFOA", "13.02 ng/L", "70-130% recovery", "Subtract native 3.42"],
        ["DW-240408-03-MSD", "PFOA", "13.22 ng/L", "RPD <=30%", "Compare with MS"],
        ["DW-240408-03-MSD", "6:2 FTS", "8.40 ng/L", "70-130% recovery", "Native <1.00 U"],
        ["CCV-10", "PFOA", "9.48 ng/L", "85-115% of 10.00", "Meets"],
        ["CCV-10-CLOSE", "PFOA", "10.31 ng/L", "85-115% of 10.00", "Meets"],
    ]
    draw_table(c, 42, 668, [120, 62, 90, 134, 122], [qc_headers, *qc_rows], font_size=6.25, zebra=True)
    source_headers = ["Computation", "Required source join", "Reviewer action"]
    source_rows = [
        ["LCS PFOA recovery", "p6 SPK-01 target + p9 measured", "Calculate; compare to 70-130%"],
        ["LCS PFOS recovery", "p6 SPK-01 target + p9 measured", "Calculate; compare to 70-130%"],
        ["MS PFOA recovery", "p6 SPK-02 + native + p9 spiked", "Subtract native; calculate"],
        ["MSD PFOA recovery", "p6 SPK-02 + native + p9 spiked", "Subtract native; calculate"],
        ["MS/MSD PFOA RPD", "two calculated spike recoveries", "Calculate; compare to <=30%"],
        ["MSD 6:2 FTS recovery", "p6 SPK-02 + p9 measured; native U", "Treat native as zero; calculate"],
    ]
    draw_label(c, "Reviewer calculation index", 42, 390)
    draw_table(c, 42, 376, [140, 245, 143], [source_headers, *source_rows], font_size=6.55, zebra=True)
    draw_paragraph(c, "The calculation index gives routing and review actions; the signed preparation record remains the only target source.", 42, 175, 520, font="DocSans-Italic", size=7.5, leading=10.5, color=MUTED)
    case.add_gold(
        "Page 9 - Blank, recovery, and continuing-calibration review",
        _table_gold(qc_headers, qc_rows)
        + "\n\n"
        + _table_gold(source_headers, source_rows)
        + "\n\nThe 10.00 ng/L SPK-01/SPK-02 targets come from page 6. The LCS recoveries are 96.2% PFOA and 91.4% PFOS; MS/MSD PFOA recoveries are 96.0% and 98.0% with 2.1% RPD; 6:2 FTS MSD recovery is 84.0%.",
    )
    case.add_region(
        "p09.qc",
        "QC measured values",
        "table",
        _schema_order_leaves("p09.qc", qc_headers, [row[0] for row in qc_rows])[:1]
        + [
            leaf(
                "p09.qc.row-order",
                "The source row order preserves each Control/Analyte pair from the two LRB rows through the CCV-10-CLOSE row for PFOA.",
                claim_type="ordered_record",
                evidence_policy={
                    "type": "ordered_tokens",
                    "tokens": [[value] for row in qc_rows for value in row[:2]],
                },
            )
        ]
        + [
            leaf("p09.qc.blanks", "LRB PFOA is <0.25 ng/L U and PFOS is <0.50 ng/L U; both meet their blank criteria.", harm=2),
            leaf("p09.qc.lcs", "LCS measured concentrations are 9.62 ng/L PFOA and 9.14 ng/L PFOS."),
            leaf("p09.qc.ms", "DW-240408-03-MS PFOA is 13.02 ng/L; native PFOA is 3.42 ng/L."),
            leaf("p09.qc.msd", "DW-240408-03-MSD PFOA is 13.22 ng/L and 6:2 FTS is 8.40 ng/L with native <1.00 U."),
            leaf("p09.qc.ccv", "Opening CCV-10 PFOA is 9.48 ng/L and closing CCV-10-CLOSE PFOA is 10.31 ng/L; both meet 85-115% of 10.00."),
        ],
        budget=2,
    )
    # Page 10 - full-page maintenance/authorization scan.
    c = case.new_page(
        "Instrument maintenance and reinjection authorization",
        subtitle="Maintenance exception MX-24-041 | service bench record",
        section_code="MAINT 10",
    )
    draw_badge(c, "original signed record", 42, 681, RED)
    incident_headers = ["Time", "Observation / action", "Measured check", "Initials"]
    incident_rows = [
        ["11:55", "Sequence 18 flagged by IS rule", "13C8-PFOA recovery 38%", "MI"],
        ["12:00", "Pressure and source check", "6,820 psi; spray stable", "MI"],
        ["12:04", "Needle-seat inspection", "Visible salt film", "LC"],
        ["12:08", "Needle seat flushed 3 x 500 uL", "50:50 MeOH:water", "LC"],
        ["12:12", "System blank injected", "PFOS carryover <0.08 ng/L", "MI"],
        ["12:16", "IS check solution", "13C8-PFOA recovery 96%", "MI"],
        ["12:17", "One reinjection authorized", "Use retained DIL-05 vial", "LC"],
    ]
    draw_table(c, 42, 657, [55, 230, 173, 70], [incident_headers, *incident_rows], font_size=6.5, zebra=True, vertical_rules=True)
    decision_headers = ["Decision field", "Signed entry"]
    decision_rows = [
        ["Permitted scope", "DW-240409-04 only; one reinjection"],
        ["Acceptance gate", "IS recovery 50-150%; blank carryover below LOQ"],
        ["If gate passes", "Send both integrations to QA; do not select final concentration here"],
        ["If gate fails", "Invalidate sample result and request re-extraction"],
        ["Audit preservation", "Retain sequence 18, IR-18A, and original vial DIL-04"],
    ]
    draw_label(c, "Authorization and boundary", 42, 390)
    draw_table(c, 42, 376, [125, 403], [decision_headers, *decision_rows], font_size=6.7, zebra=True)
    draw_label(c, "Handwritten service note", 42, 224)
    draw_paragraph(c, "Salt residue was confined to the needle seat. No source cleaning, recalibration, or re-extraction was authorized.", 52, 202, 492, font="DocSans-Italic", size=8.2, leading=11.2)
    c.setStrokeColor(HexColor("#777777"))
    c.line(52, 118, 263, 118)
    c.line(326, 118, 548, 118)
    c.setFillColor(INK)
    c.setFont("DocSans-Italic", 8)
    c.drawString(58, 100, "M. Iyer / operator / 19 Apr 2024 12:22")
    c.drawString(332, 100, "L. Chen / authorization / 19 Apr 2024 12:24")
    case.add_gold(
        "Page 10 - Scanned maintenance and reinjection authorization",
        _table_gold(incident_headers, incident_rows)
        + "\n\n"
        + _table_gold(decision_headers, decision_rows)
        + "\n\nSalt residue was confined to the needle seat. No source cleaning, recalibration, or re-extraction was authorized. M. Iyer signed 19 Apr 2024 12:22 and L. Chen authorized at 12:24.",
    )
    case.add_region(
        "p10.maintenance",
        "Scanned maintenance incident chronology",
        "form",
        _schema_order_leaves("p10.maintenance", incident_headers, [row[0] for row in incident_rows])
        + [
            leaf("p10.maintenance.trigger", "Sequence 18 was flagged at 11:55 for 13C8-PFOA recovery of 38%.", harm=2),
            leaf("p10.maintenance.cause", "Needle-seat inspection found visible salt film at 12:04."),
            leaf("p10.maintenance.action", "The needle seat was flushed three times with 500 uL of 50:50 methanol:water."),
            leaf("p10.maintenance.check", "The system blank had PFOS carryover <0.08 ng/L and the IS check recovered 96%."),
        ],
        budget=2,
        primary_axis="low_quality_scan",
        secondary_axes=["form_state"],
    )
    case.add_region(
        "p10.authorization",
        "Scanned reinjection authorization",
        "form",
        [
            leaf("p10.auth.scope", "Only DW-240409-04 may be reinjected, exactly once, using retained vial DIL-05.", harm=2),
            leaf("p10.auth.gate", "Acceptance requires IS recovery of 50-150% and blank carryover below LOQ.", harm=2),
            leaf("p10.auth.boundary", "If the gate passes, both integrations go to QA; this maintenance record does not select a final concentration.", harm=2),
            leaf("p10.auth.preserve", "Sequence 18, IR-18A, and original vial DIL-04 must remain in the audit trail."),
            leaf("p10.auth.signatures", "M. Iyer signed at 12:22 and L. Chen authorized at 12:24 on 19 Apr 2024."),
        ],
        budget=2,
    )

    # Page 11 - provisional export followed by the signed correction record.
    c = case.new_page(
        "LIMS export and signed QA correction",
        subtitle="Provisional export snapshot with a separately signed correction record",
        section_code="CORRECTION 11",
    )
    preliminary_headers = ["Export row", "Sample", "Analyte", "Result", "Qual.", "Source", "Status"]
    preliminary_rows = [
        ["E-104", "DW-240409-04", "PFOA", "1.84 ng/L", "J", "Seq 18 / IR-18A", "Provisional"],
        ["E-105", "DW-240409-04", "PFOS", "<0.50 ng/L", "U", "Seq 18 / IR-18A", "Provisional"],
        ["E-106", "DW-240409-05", "PFOA", "4.87 ng/L", "-", "Seq 20 / IR-20A", "Ready"],
    ]
    draw_label(c, "PRELIM-LIMS-0419 provisional export", 42, 672)
    draw_table(c, 42, 658, [48, 101, 54, 73, 43, 133, 76], [preliminary_headers, *preliminary_rows], font_size=5.95, zebra=True)
    draw_label(c, "Signed correction record", 42, 518)
    correction = _signed_correction_scan()
    c.drawImage(image_reader(correction), 42, 244, width=528, height=222, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(HexColor("#8B8175"))
    c.rect(42, 244, 528, 222, fill=0, stroke=1)
    case.add_gold(
        "Page 11 - LIMS export and signed QA correction",
        "The page first contains provisional export PRELIM-LIMS-0419:\n\n"
        + _table_gold(preliminary_headers, preliminary_rows)
        + "\n\nSigned correction CR-24-044 applies only to DW-240409-04. It supersedes PRELIM-LIMS-0419 fields derived from sequence 18/IR-18A and makes accepted sequence 19/IR-19B controlling. PFOA changes from 1.84 ng/L J to 1.06 ng/L J. PFOS remains <0.50 ng/L U with no qualifier change. Other batch results are unchanged. The reason is sequence 18 IS recovery below the 50-150% criterion. L. Chen signed 22 Apr 2024 09:40 and R. Patel signed 22 Apr 2024 16:10. The audit trail must not be overwritten. Controlled record order is provisional PRELIM-LIMS-0419 first, followed by signed CR-24-044.",
    )
    case.add_region(
        "p11.preliminary",
        "Provisional LIMS export",
        "table",
        _schema_order_leaves("p11.prelim", preliminary_headers, [row[0] for row in preliminary_rows])
        + [
            table_binding_leaf("p11.prelim.e104", "For E-104, Result is 1.84 ng/L.", "E-104", "Result", "1.84 ng/L"),
            table_binding_leaf("p11.prelim.e104.sample", "For E-104, Sample is DW-240409-04.", "E-104", "Sample", "DW-240409-04"),
            table_binding_leaf("p11.prelim.e104.analyte", "For E-104, Analyte is PFOA.", "E-104", "Analyte", "PFOA"),
            table_binding_leaf("p11.prelim.e104.qualifier", "For E-104, Qual. is J.", "E-104", "Qual.", "J"),
            table_binding_leaf("p11.prelim.e104.source", "For E-104, Source is Seq 18 / IR-18A.", "E-104", "Source", "Seq 18 / IR-18A"),
            table_binding_leaf("p11.prelim.e104.status", "For E-104, Status is Provisional.", "E-104", "Status", "Provisional"),
            table_binding_leaf("p11.prelim.e105", "For E-105, Result is <0.50 ng/L.", "E-105", "Result", "<0.50 ng/L"),
            table_binding_leaf("p11.prelim.e105.sample", "For E-105, Sample is DW-240409-04.", "E-105", "Sample", "DW-240409-04"),
            table_binding_leaf("p11.prelim.e105.analyte", "For E-105, Analyte is PFOS.", "E-105", "Analyte", "PFOS"),
            table_binding_leaf("p11.prelim.e105.qualifier", "For E-105, Qual. is U.", "E-105", "Qual.", "U"),
            table_binding_leaf("p11.prelim.e105.source", "For E-105, Source is Seq 18 / IR-18A.", "E-105", "Source", "Seq 18 / IR-18A"),
            table_binding_leaf("p11.prelim.e105.status", "For E-105, Status is Provisional.", "E-105", "Status", "Provisional"),
            table_binding_leaf("p11.prelim.e106", "For E-106, Result is 4.87 ng/L.", "E-106", "Result", "4.87 ng/L"),
            table_binding_leaf("p11.prelim.e106.sample", "For E-106, Sample is DW-240409-05.", "E-106", "Sample", "DW-240409-05"),
            table_binding_leaf("p11.prelim.e106.analyte", "For E-106, Analyte is PFOA.", "E-106", "Analyte", "PFOA"),
            table_binding_leaf("p11.prelim.e106.qualifier", "For E-106, Qual. is a dash.", "E-106", "Qual.", ["-", "dash", "no qualifier"]),
            table_binding_leaf("p11.prelim.e106.source", "For E-106, Source is Seq 20 / IR-20A.", "E-106", "Source", "Seq 20 / IR-20A"),
            table_binding_leaf("p11.prelim.e106.status", "For E-106, Status is Ready.", "E-106", "Status", "Ready"),
        ],
    )
    case.add_region(
        "p11.correction",
        "Signed QA correction CR-24-044",
        "image",
        [
            leaf("p11.correction.scope", "CR-24-044 applies only to DW-240409-04; other batch results are unchanged.", harm=2),
            leaf("p11.correction.pfos", "DW-240409-04 PFOS remains <0.50 ng/L U with no qualifier change.", harm=2),
            leaf("p11.correction.reason", "The correction reason is sequence 18 internal-standard recovery below the 50-150% criterion."),
            leaf("p11.correction.signatures", "L. Chen signed 22 Apr 2024 09:40 and R. Patel signed 22 Apr 2024 16:10."),
        ],
        budget=2,
    )
    case.add_region(
        "p11.reading-order",
        "Preliminary-to-correction reading order",
        "structure",
        [
            source_precedence_leaf(
                "p11.order",
                "Preserve the controlled record order: provisional PRELIM-LIMS-0419 first, signed CR-24-044 second.",
                ["PRELIM-LIMS-0419", "signed CR-24-044"],
                harm=2,
            )
        ],
        modality="mixed",
        primary_axis="reading_order",
        secondary_axes=["source_precedence", "mixed_modality_fusion"],
        text_only_recoverable=False,
    )

    # Page 12 - concise final determination. It reports released concentrations
    # and qualifiers, but does not repeat chromatogram RTs, areas, ratios, noise,
    # IS recoveries, maintenance values, or every validation table cell.
    c = case.new_page(
        "Final signed validation and batch determination",
        subtitle="Release values after source-precedence review | 22 Apr 2024",
        section_code="RELEASE 12",
    )
    result_headers = ["Result ID", "Sample", "Analyte", "Released result", "Qual.", "U95", "Authority"]
    result_rows = [
        ["R-01", "FB-240408-01", "PFOA", "<0.25 ng/L", "U", "-", "Routine"],
        ["R-02", "DW-240408-02", "PFOA", "2.18 ng/L", "-", "0.42 ng/L", "Routine"],
        ["R-03", "DW-240408-02", "PFOS", "0.62 ng/L", "J", "0.18 ng/L", "Routine"],
        ["R-04", "DW-240408-03", "PFOA", "3.42 ng/L", "-", "0.55 ng/L", "Routine"],
        ["R-05", "DW-240408-03", "PFOS", "0.74 ng/L", "J", "0.19 ng/L", "Routine"],
        ["R-06", "DW-240409-04", "PFOA", "1.06 ng/L", "J", "0.25 ng/L", "CR-24-044"],
        ["R-07", "DW-240409-04", "PFOS", "<0.50 ng/L", "U", "-", "CR-24-044"],
        ["R-08", "DW-240409-05", "PFOA", "4.87 ng/L", "-", "0.72 ng/L", "Routine"],
    ]
    draw_table(c, 42, 668, [47, 103, 56, 86, 43, 77, 116], [result_headers, *result_rows], font_size=6.05, zebra=True)
    determination_headers = ["Release check", "Determination", "Basis"]
    determination_rows = [
        ["Calibration", "Accepted", "Weighted fits and residual review"],
        ["Blanks and CCVs", "Accepted", "Opening and closing controls within criteria"],
        ["Recovery / precision", "Accepted", "Valid n=7; documented EX-24-011 replacement"],
        ["DW-240409-04", "Accepted as corrected", "Sequence 19 / IR-19B / CR-24-044"],
        ["Batch release", "RELEASED", "J and U qualifiers retained exactly"],
    ]
    draw_label(c, "Determination", 42, 390)
    draw_table(c, 42, 376, [126, 132, 270], [determination_headers, *determination_rows], font_size=6.8, zebra=True)
    draw_paragraph(c, "Release boundary: the signed determination does not erase provisional exports, rejected integrations, or maintenance records.", 42, 209, 520, font="DocSans-Bold", size=7.7, leading=10.8, color=RED)
    c.setStrokeColor(HexColor("#777777"))
    c.line(52, 132, 263, 132)
    c.line(326, 132, 548, 132)
    c.setFillColor(INK)
    c.setFont("DocSans-Italic", 8)
    c.drawString(58, 114, "L. Chen / technical / 22 Apr 2024 09:40")
    c.drawString(332, 114, "R. Patel / QA release / 22 Apr 2024 16:10")
    case.add_gold(
        "Page 12 - Final signed validation and batch determination",
        _table_gold(result_headers, result_rows)
        + "\n\n"
        + _table_gold(determination_headers, determination_rows)
        + "\n\nThe batch is released with J and U qualifiers preserved. DW-240409-04's record lifecycle begins with held sequence 18 at 38% IS recovery and rejected original integration IR-18A, then continues through accepted DW-240409-04-RI sequence 19 at 91% IS recovery and controlling reinjection IR-19B. Panels E and F preserve the original not-reportable PFOA Q1 trace and the accepted reinjection trace. Signed CR-24-044 changes provisional PFOA 1.84 ng/L J to released R-06 at 1.06 ng/L J with U95 0.25 ng/L, while PFOS remains <0.50 ng/L U. The final determination does not erase provisional exports, rejected integrations, or maintenance records. L. Chen signed 22 Apr 2024 09:40 and R. Patel released 22 Apr 2024 16:10.",
    )
    case.add_region(
        "p12.results",
        "Released result table",
        "table",
        _schema_order_leaves("p12.results", result_headers, [row[0] for row in result_rows])
        + [
            leaf(
                "p12.result.r02",
                "For R-02, Released result is 2.18 ng/L.",
                claim_type="table_binding",
                evidence_policy={"type": "table_binding", "row": ["R-02"], "column": ["Released result"], "value": ["2.18 ng/L"]},
            ),
            leaf(
                "p12.result.r02.qualifier",
                "For R-02, Qual. is -.",
                claim_type="table_binding",
                evidence_policy={"type": "table_binding", "row": ["R-02"], "column": ["Qual."], "value": ["-"]},
            ),
            leaf(
                "p12.result.r02.u95",
                "For R-02, U95 is 0.42 ng/L.",
                claim_type="table_binding",
                evidence_policy={"type": "table_binding", "row": ["R-02"], "column": ["U95"], "value": ["0.42 ng/L"]},
            ),
            leaf("p12.result.r03", "R-03 releases DW-240408-02 PFOS at 0.62 ng/L J with U95 0.18 ng/L."),
            leaf(
                "p12.result.r04",
                "For R-04, Released result is 3.42 ng/L.",
                claim_type="table_binding",
                evidence_policy={"type": "table_binding", "row": ["R-04"], "column": ["Released result"], "value": ["3.42 ng/L"]},
            ),
            leaf(
                "p12.result.r04.qualifier",
                "For R-04, Qual. is -.",
                claim_type="table_binding",
                evidence_policy={"type": "table_binding", "row": ["R-04"], "column": ["Qual."], "value": ["-"]},
            ),
            leaf(
                "p12.result.r04.u95",
                "For R-04, U95 is 0.55 ng/L.",
                claim_type="table_binding",
                evidence_policy={"type": "table_binding", "row": ["R-04"], "column": ["U95"], "value": ["0.55 ng/L"]},
            ),
            leaf("p12.result.r07", "R-07 releases DW-240409-04 PFOS as <0.50 ng/L U under CR-24-044.", harm=2),
            leaf(
                "p12.result.r08",
                "For R-08, Released result is 4.87 ng/L.",
                claim_type="table_binding",
                evidence_policy={"type": "table_binding", "row": ["R-08"], "column": ["Released result"], "value": ["4.87 ng/L"]},
            ),
            leaf(
                "p12.result.r08.qualifier",
                "For R-08, Qual. is -.",
                claim_type="table_binding",
                evidence_policy={"type": "table_binding", "row": ["R-08"], "column": ["Qual."], "value": ["-"]},
            ),
            leaf(
                "p12.result.r08.u95",
                "For R-08, U95 is 0.72 ng/L.",
                claim_type="table_binding",
                evidence_policy={"type": "table_binding", "row": ["R-08"], "column": ["U95"], "value": ["0.72 ng/L"]},
            ),
        ],
        budget=2,
    )
    case.add_region(
        "p12.determination",
        "Final determination and signatures",
        "table",
        [
            leaf("p12.det.calibration", "Calibration is accepted based on weighted fits and residual review."),
            leaf("p12.det.recovery", "Recovery and precision are accepted with valid n=7 and documented EX-24-011 replacement."),
            leaf("p12.det.release", "The batch is RELEASED with J and U qualifiers retained exactly.", harm=2),
            leaf("p12.det.signatures", "L. Chen signed technical review at 09:40 and R. Patel released at 16:10 on 22 Apr 2024."),
        ],
        budget=1,
        primary_axis="source_precedence",
        secondary_axes=["summarization_coverage"],
    )
    case.add_region(
        "join.dw24040904-release",
        "DW-240409-04 rejected-integration-to-release lifecycle",
        "mixed",
        [
            leaf(
                "join.dw24040904.original",
                "DW-240409-04 sequence 18 is held at 38% IS recovery with original integration IR-18A rejected and its PFOA Q1 trace not reportable.",
                harm=2,
            ),
            leaf(
                "join.dw24040904.reinjection",
                "DW-240409-04-RI sequence 19 is accepted at 91% IS recovery with reinjection IR-19B controlling.",
                harm=2,
            ),
            directed_edge_leaf(
                "join.dw24040904.correction",
                "Signed CR-24-044 changes DW-240409-04 PFOA from provisional 1.84 ng/L J to 1.06 ng/L J.",
                ["provisional 1.84 ng/L J", "1.84 ng/L J"],
                ["1.06 ng/L J"],
                relation=["Signed CR-24-044 changes DW-240409-04 PFOA", "Signed CR-24-044 corrects DW-240409-04 PFOA"],
                harm=2,
            ),
            leaf(
                "join.dw24040904.release",
                "Released result R-06 is DW-240409-04 PFOA at 1.06 ng/L J with U95 0.25 ng/L under CR-24-044.",
                harm=2,
            ),
            leaf(
                "join.dw24040904.pfos",
                "Across the correction and release, DW-240409-04 PFOS remains <0.50 ng/L U.",
                harm=2,
            ),
            leaf(
                "join.dw24040904.audit",
                "The accepted reinjection controls release without erasing the provisional export or rejected original integration.",
                harm=2,
            ),
        ],
        pages=[7, 8, 11, 12],
        budget=2,
        modality="mixed",
        primary_axis="source_precedence",
        secondary_axes=["long_context_coherence", "mixed_modality_fusion"],
        text_only_recoverable=False,
        gold_section="Page 12 - Final signed validation and batch determination",
    )
    record = case.finish()
    rasterize_pdf_pages(
        case.pdf_path,
        case.pdf_path,
        {
            6: ScanProfile(seed=1206, dpi=168, skew_degrees=0.12, noise_level=1.25, blur_radius=0.16, jpeg_quality=90, contrast=1.04),
            7: ScanProfile(seed=1207, dpi=180, skew_degrees=-0.16, noise_level=1.45, blur_radius=0.18, jpeg_quality=89, contrast=1.05),
            10: ScanProfile(seed=1210, dpi=156, skew_degrees=0.20, noise_level=1.65, blur_radius=0.20, jpeg_quality=88, contrast=1.03),
        },
        metadata={
            "Creator": "Northstar controlled laboratory imaging",
            "Producer": "Enterprise Document Services",
        },
    )
    return record
