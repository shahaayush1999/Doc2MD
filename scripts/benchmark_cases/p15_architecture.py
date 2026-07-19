from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from reportlab.lib.colors import Color, HexColor

from .common import (
    AMBER,
    BLUE,
    GREEN,
    INK,
    LANDSCAPE,
    MUTED,
    RED,
    CaseBuilder,
    directed_edge_leaf,
    draw_arrow,
    draw_badge,
    draw_checkbox,
    draw_label,
    draw_paragraph,
    draw_table,
    form_state_leaf,
    image_reader,
    leaf,
    markdown_table,
    source_precedence_leaf,
    table_leaves,
    visual_leaf,
)
from .rasterize import ScanProfile, rasterize_pdf_pages


# The envelope is part of the case contract. Pages 2 and 8 are rasterized only
# after the native construction file is complete; mixed pages retain native
# schedules around embedded field-image or scanned-form regions.
NATIVE_PAGES = (1, 3, 4, 5, 6)
FULL_SCAN_PAGES = (2, 8)
MIXED_PAGES = (7, 9, 10)


def _box(c, x, y, width, height, title, subtitle="", *, fill="#F7F8F8", stroke=INK):
    c.setFillColor(HexColor(fill))
    c.setStrokeColor(stroke)
    c.setLineWidth(0.9)
    c.roundRect(x, y, width, height, 4, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont("DocSans-Bold", 7.2)
    c.drawCentredString(x + width / 2, y + height / 2 + (4 if subtitle else -2), title)
    if subtitle:
        c.setFillColor(MUTED)
        c.setFont("DocSans", 5.8)
        c.drawCentredString(x + width / 2, y + height / 2 - 8, subtitle)


def _bubble(c, x, y, text, *, color=RED):
    c.setFillColor(HexColor("#FFF9F5"))
    c.setStrokeColor(color)
    c.setLineWidth(1.1)
    c.circle(x, y, 10, fill=1, stroke=1)
    c.setFillColor(color)
    c.setFont("DocSans-Bold", 6.2)
    c.drawCentredString(x, y - 2, text)


def _door(c, hinge_x, wall_y, width, *, swing_up, color=INK, dashed=False):
    c.saveState()
    c.setStrokeColor(HexColor("#FCFCFA"))
    c.setLineWidth(5)
    c.line(hinge_x, wall_y, hinge_x + width, wall_y)
    c.setStrokeColor(color)
    c.setLineWidth(1.2)
    if dashed:
        c.setDash(4, 2)
    direction = 1 if swing_up else -1
    c.line(hinge_x, wall_y, hinge_x, wall_y + direction * width)
    if swing_up:
        c.arc(hinge_x - width, wall_y - width, hinge_x + width, wall_y + width, startAng=0, extent=90)
    else:
        c.arc(hinge_x - width, wall_y - width, hinge_x + width, wall_y + width, startAng=270, extent=90)
    c.restoreState()


def _dimension(c, x1, y1, x2, y2, label, *, color=MUTED):
    c.saveState()
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(0.55)
    c.line(x1, y1, x2, y2)
    if abs(x2 - x1) >= abs(y2 - y1):
        c.line(x1, y1 - 4, x1, y1 + 4)
        c.line(x2, y2 - 4, x2, y2 + 4)
        c.setFont("DocSans", 5.8)
        c.drawCentredString((x1 + x2) / 2, y1 + 4, label)
    else:
        c.line(x1 - 4, y1, x1 + 4, y1)
        c.line(x2 - 4, y2, x2 + 4, y2)
        c.setFont("DocSans", 5.8)
        c.drawString(x1 + 5, (y1 + y2) / 2, label)
    c.restoreState()


def _north_arrow(c, x, y):
    c.setFillColor(INK)
    c.setFont("DocSans-Bold", 7)
    c.drawCentredString(x, y + 28, "N")
    path = c.beginPath()
    path.moveTo(x, y + 24)
    path.lineTo(x - 6, y + 5)
    path.lineTo(x, y + 9)
    path.lineTo(x + 6, y + 5)
    path.close()
    c.drawPath(path, fill=1, stroke=0)


def _floor_plan(c, *, revision: str, overlay: bool = False):
    """Draw the shared plan geometry and return named anchor coordinates."""
    x0, y0 = 58.0, 143.0
    scale = 12.0
    lower_h = 10 * scale
    upper_h = 12 * scale
    clean_w = 18.5 * scale
    lab_w = 16 * scale
    freezer_w = 10.5 * scale
    wash_w = 12 * scale
    corridor_w = 22.5 * scale
    it_w = 10.5 * scale
    upper_y = y0 + lower_h
    clean_x = x0
    lab_x = clean_x + clean_w
    freezer_x = lab_x + lab_w
    corridor_x = x0 + wash_w
    it_x = corridor_x + corridor_w

    rooms = [
        (clean_x, upper_y, clean_w, upper_h, "214 CLEAN PREP", "18'-6\" x 12'-0\""),
        (lab_x, upper_y, lab_w, upper_h, "215 LAB B", "16'-0\" x 12'-0\""),
        (freezer_x, upper_y, freezer_w, upper_h, "216 FREEZER", "10'-6\" x 12'-0\""),
        (x0, y0, wash_w, lower_h, "217 WASH", "12'-0\" x 10'-0\""),
        (corridor_x, y0, corridor_w, lower_h, "C2 CORRIDOR", "WEST EGRESS"),
        (it_x, y0, it_w, lower_h, "218 IT", "10'-6\" x 10'-0\""),
    ]
    for x, y, width, height, name, dimensions in rooms:
        c.setStrokeColor(INK)
        c.setLineWidth(2.1)
        c.rect(x, y, width, height, fill=0, stroke=1)
        c.setFillColor(INK)
        c.setFont("DocSans-Bold", 6.5)
        c.drawCentredString(x + width / 2, y + height / 2 + 4, name)
        c.setFillColor(MUTED)
        c.setFont("DocSans", 5.6)
        c.drawCentredString(x + width / 2, y + height / 2 - 7, dimensions)

    # Grid bubbles and exterior glazing are intentionally conventional symbols.
    for index, gx in enumerate((x0, lab_x, freezer_x, freezer_x + freezer_w), start=1):
        c.setStrokeColor(HexColor("#B7BDC2"))
        c.setLineWidth(0.35)
        c.setDash(2, 3)
        c.line(gx, y0 - 13, gx, upper_y + upper_h + 16)
        c.setDash()
        c.circle(gx, y0 - 20, 7, fill=0, stroke=1)
        c.setFillColor(MUTED)
        c.setFont("DocSans", 5.5)
        c.drawCentredString(gx, y0 - 22, str(index))
    for room_x, room_w in ((clean_x, clean_w), (lab_x, lab_w), (freezer_x, freezer_w)):
        wx = room_x + room_w / 2 - 18
        c.setStrokeColor(BLUE)
        c.setLineWidth(0.7)
        c.line(wx, upper_y + upper_h - 2, wx + 36, upper_y + upper_h - 2)
        c.line(wx, upper_y + upper_h + 2, wx + 36, upper_y + upper_h + 2)

    old_hinge = lab_x + 102
    new_hinge = old_hinge - 54
    width = 36
    if revision == "B":
        _door(c, old_hinge, upper_y, width, swing_up=True)
        door_hinge = old_hinge
    else:
        _door(c, new_hinge, upper_y, width, swing_up=False, color=BLUE)
        door_hinge = new_hinge
        # Reader symbol is deliberately unlabeled except for the keyed bubble.
        c.setFillColor(HexColor("#FFF3EA"))
        c.setStrokeColor(RED)
        c.rect(new_hinge + width + 5, upper_y - 13, 6, 9, fill=1, stroke=1)
        if overlay:
            _door(c, old_hinge, upper_y, width, swing_up=True, color=RED, dashed=True)
            _dimension(c, new_hinge, upper_y + 56, old_hinge, upper_y + 56, "4'-6\"", color=RED)
            c.setFillColor(RED)
            c.setFont("DocSans-Italic", 5.8)
            c.drawString(old_hinge + 3, upper_y + 44, "REV B")

    # Egress arrows are visual evidence; no adjacent prose restates direction.
    draw_arrow(c, lab_x + 94, upper_y + 52, door_hinge + 18, upper_y - 12, color=GREEN, width=1.7)
    draw_arrow(c, door_hinge + 18, upper_y - 28, corridor_x + 18, y0 + 46, color=GREEN, width=1.7)

    callout6 = (new_hinge + width + 14 if revision == "C" else old_hinge + width + 14, upper_y - 20)
    callout9 = (it_x + 70, y0 + 55)
    callout11 = (freezer_x + 76, upper_y + 85)
    _bubble(c, *callout6, "6")
    _bubble(c, *callout9, "9")
    _bubble(c, *callout11, "11")
    c.setStrokeColor(RED)
    c.setLineWidth(0.7)
    c.line(callout6[0] - 10, callout6[1] + 3, door_hinge + width + 5, upper_y - 7)
    c.line(callout9[0] - 10, callout9[1], it_x + 38, y0 + 68)
    c.line(callout11[0] - 10, callout11[1], freezer_x + 38, upper_y + 66)
    c.setFillColor(RED)
    c.setFont("DocSans-Bold", 5.5)
    c.drawString(callout6[0] + 13, callout6[1] - 2, "D-214B / CR-6" if revision == "C" else "D-214A")
    c.drawString(callout9[0] + 13, callout9[1] - 2, "R2")
    c.drawString(callout11[0] + 13, callout11[1] - 2, "FZ-3")

    _dimension(c, x0, upper_y + upper_h + 20, freezer_x + freezer_w, upper_y + upper_h + 20, "45'-0\"")
    _dimension(c, x0 - 15, y0, x0 - 15, upper_y + upper_h, "22'-0\"")
    _north_arrow(c, 742, 502)
    c.setFillColor(MUTED)
    c.setFont("DocSans", 5.5)
    c.drawString(650, 151, "0     4     8 FT")
    c.setStrokeColor(INK)
    c.setLineWidth(1.1)
    c.line(650, 144, 710, 144)
    c.line(650, 140, 650, 148)
    c.line(680, 140, 680, 148)
    c.line(710, 140, 710, 148)
    return {
        "lab": (lab_x, upper_y, lab_w, upper_h),
        "corridor": (corridor_x, y0, corridor_w, lower_h),
        "freezer": (freezer_x, upper_y, freezer_w, upper_h),
        "it": (it_x, y0, it_w, lower_h),
        "old_hinge": old_hinge,
        "new_hinge": new_hinge,
        "wall_y": upper_y,
    }


def _pil_font(size: int, *, bold: bool = False):
    # Pillow's bundled default is deterministic and avoids host font drift.
    return ImageFont.load_default(size=size + (1 if bold else 0))


def _paper_image(width: int, height: int, seed: int) -> Image.Image:
    rng = random.Random(seed)
    image = Image.new("RGB", (width, height), (242, 240, 232))
    pixels = image.load()
    for _ in range(width * height // 48):
        x = rng.randrange(width)
        y = rng.randrange(height)
        shade = rng.randrange(222, 247)
        pixels[x, y] = (shade, shade, max(210, shade - 5))
    return image.filter(ImageFilter.GaussianBlur(0.18))


def _draw_scan_checkbox(draw, x, y, state, label, *, font):
    draw.rectangle((x, y, x + 26, y + 26), outline=(45, 45, 42), width=2)
    if state == "checked":
        draw.line((x + 3, y + 14, x + 10, y + 23, x + 24, y + 3), fill=(30, 61, 96), width=4, joint="curve")
    elif state == "crossed":
        draw.line((x + 3, y + 3, x + 23, y + 23), fill=(140, 40, 40), width=3)
        draw.line((x + 23, y + 3, x + 3, y + 23), fill=(140, 40, 40), width=3)
    draw.text((x + 38, y + 2), label, fill=(35, 35, 32), font=font)
    if state == "crossed":
        label_box = draw.textbbox((x + 38, y + 2), label, font=font)
        strike_y = y + 14
        draw.line((x + 35, strike_y, label_box[2] + 6, strike_y), fill=(140, 40, 40), width=3)
        draw.text((label_box[2] + 18, y + 2), "VOID", fill=(140, 40, 40), font=font)


def _commissioning_scan() -> Image.Image:
    image = _paper_image(1140, 720, 1507)
    draw = ImageDraw.Draw(image)
    title = _pil_font(28, bold=True)
    body = _pil_font(22)
    small = _pil_font(18)
    draw.text((54, 38), "LP-2 CONTROL POWER FIELD CHECK", fill=(25, 25, 23), font=title)
    draw.text((54, 82), "Record EC-214-19    Area 214-218    Walkdown 14 JUN 2026", fill=(50, 50, 46), font=small)
    draw.line((54, 116, 1080, 116), fill=(95, 92, 85), width=2)
    checks = [
        ("checked", "Torque witness marks complete"),
        ("checked", "L2-15 field tag installed"),
        ("checked", "L2-17 field tag installed"),
        ("checked", "L2-19 field tag installed"),
        ("unchecked", "L2-21 released for use"),
        ("checked", "Emergency transfer witnessed"),
        ("crossed", "Reader polarity exception open"),
    ]
    for index, (state, label) in enumerate(checks):
        _draw_scan_checkbox(draw, 74, 150 + index * 58, state, label, font=body)
    draw.line((54, 585, 1080, 585), fill=(115, 110, 100), width=1)
    draw.text((64, 610), "Technician: JH", fill=(34, 34, 31), font=body)
    draw.text((420, 610), "Witness: LS", fill=(34, 34, 31), font=body)
    draw.text((740, 610), "Panel energized 16:42", fill=(34, 34, 31), font=body)
    draw.text((850, 665), "FIELD COPY", fill=(132, 58, 45), font=small)
    return ImageEnhance.Contrast(image).enhance(1.05)


def _release_scan() -> Image.Image:
    image = _paper_image(1040, 620, 1510)
    draw = ImageDraw.Draw(image)
    title = _pil_font(27, bold=True)
    body = _pil_font(21)
    small = _pil_font(18)
    draw.rectangle((34, 30, 1006, 590), outline=(55, 55, 50), width=3)
    draw.text((58, 50), "FINAL ISSUE RELEASE / RECORD COPY", fill=(24, 24, 22), font=title)
    draw.text((58, 94), "Package ARC-214-C    Release 16 JUN 2026 17:20", fill=(50, 50, 46), font=small)
    draw.line((58, 125, 980, 125), fill=(100, 96, 88), width=2)
    checks = [
        ("checked", "IFC Revision C accepted"),
        ("unchecked", "Use archived Revision B background"),
        ("checked", "RFI-214-17 incorporated"),
        ("unchecked", "Open access-control punch items"),
    ]
    for index, (state, label) in enumerate(checks):
        _draw_scan_checkbox(draw, 78, 160 + index * 65, state, label, font=body)
    draw.text((72, 445), "Architect AV    Security TN    Electrical JH    Owner LS", fill=(32, 32, 29), font=body)
    draw.text((72, 493), "Release seal 214-C-0616", fill=(32, 32, 29), font=small)
    draw.ellipse((760, 430, 940, 565), outline=(145, 47, 42), width=5)
    draw.text((801, 465), "ISSUED", fill=(145, 47, 42), font=title)
    draw.text((791, 510), "16 JUN 2026", fill=(145, 47, 42), font=small)
    return ImageEnhance.Contrast(image).enhance(1.06)


def _field_photo(kind: str) -> Image.Image:
    width, height = 1180, 720
    seed = 151901 if kind == "door" else 151902
    rng = random.Random(seed)
    image = Image.new("RGB", (width, height), (183, 180, 170))
    draw = ImageDraw.Draw(image)
    # Mild luminance texture makes these read as field records rather than
    # flat diagrams while keeping every judged feature legible.
    for y in range(height):
        shade = int(202 - 55 * y / height)
        draw.line((0, y, width, y), fill=(shade, shade - 3, shade - 9))
    for _ in range(4200):
        x = rng.randrange(width)
        y = rng.randrange(height)
        d = rng.randrange(-12, 13)
        base = image.getpixel((x, y))
        image.putpixel((x, y), tuple(max(0, min(255, channel + d)) for channel in base))
    if kind == "door":
        # Corridor perspective, opening, frame, and reader at image-right jamb.
        draw.polygon([(0, 145), (1180, 35), (1180, 610), (0, 720)], fill=(193, 190, 180))
        draw.polygon([(320, 172), (825, 127), (825, 630), (320, 672)], fill=(66, 69, 70))
        draw.polygon([(350, 194), (794, 157), (794, 606), (350, 642)], fill=(39, 42, 43))
        draw.line((320, 172, 825, 127, 825, 630, 320, 672, 320, 172), fill=(232, 229, 217), width=18)
        draw.rectangle((851, 324, 887, 402), fill=(42, 47, 50), outline=(225, 226, 220), width=4)
        draw.ellipse((830, 294, 913, 430), outline=(197, 43, 42), width=7)
        draw.line((910, 305, 1040, 220), fill=(197, 43, 42), width=6)
        draw.ellipse((1030, 190, 1085, 245), fill=(252, 244, 235), outline=(197, 43, 42), width=5)
        draw.text((1048, 203), "A", fill=(197, 43, 42), font=_pil_font(27, bold=True), anchor="mm")
        draw.polygon([(620, 642), (750, 635), (1050, 720), (480, 720)], fill=(143, 137, 126))
    else:
        # IT closet: rack at right, tray approaches from left and drops at the
        # rack's west/top corner; the east service side remains visibly clear.
        draw.rectangle((0, 0, width, 720), fill=(186, 184, 175))
        draw.polygon([(0, 0), (1180, 0), (1080, 170), (90, 185)], fill=(215, 213, 203))
        draw.rectangle((610, 150, 970, 680), fill=(52, 56, 58), outline=(225, 224, 214), width=8)
        for row in range(14):
            yy = 180 + row * 32
            draw.rectangle((650, yy, 930, yy + 21), fill=(78 + row % 2 * 12, 82, 84), outline=(132, 138, 139), width=2)
        draw.polygon([(50, 110), (620, 98), (620, 150), (50, 165)], fill=(96, 100, 101), outline=(52, 55, 56))
        for x in range(85, 600, 58):
            draw.line((x, 122, x + 42, 121), fill=(34, 64, 83), width=5)
            draw.line((x, 137, x + 42, 136), fill=(167, 117, 38), width=4)
        # The metal tray makes a visible elbow and vertical drop into the
        # rack's image-left/west top corner. Keep the gray assembly distinct
        # from the red annotation so the physical direction is unambiguous.
        draw.polygon(
            [(585, 108), (635, 108), (635, 215), (605, 215), (605, 158), (585, 158)],
            fill=(96, 100, 101),
            outline=(52, 55, 56),
        )
        draw.line((603, 125, 618, 125, 618, 198), fill=(34, 64, 83), width=5)
        draw.line((590, 141, 608, 141, 608, 198), fill=(167, 117, 38), width=4)
        draw.ellipse((565, 86, 676, 242), outline=(195, 47, 43), width=7)
        draw.line((578, 78, 485, 36), fill=(195, 47, 43), width=6)
        draw.ellipse((435, 12, 495, 68), fill=(250, 243, 234), outline=(195, 47, 43), width=5)
        draw.text((465, 40), "B", fill=(195, 47, 43), font=_pil_font(27, bold=True), anchor="mm")
        draw.rectangle((990, 180, 1145, 680), fill=(199, 196, 185))
    return image.filter(ImageFilter.GaussianBlur(0.28))


def build(output_root: Path):
    case = CaseBuilder(
        output_root=output_root,
        case_id="P15-architecture-floorplan-diagrams",
        title="Suite 214 Laboratory Coordination Set",
        family="architectural and building systems",
        tags=[
            "mixed-pdf",
            "floorplan-overlay",
            "reflected-ceiling-plan",
            "rack-elevation",
            "directed-topology",
            "panel-schedule",
            "scanned-rfi",
            "field-photos",
            "source-precedence",
        ],
        page_count=10,
        purpose="Test long-range technical coordination across archived and controlling plans, spatial overlays, MEP geometry, rack and patch bindings, directed network paths, electrical form states, scanned redlines, field-image evidence, and final release authority.",
        source_modality="five born-digital technical sheets, two full-page image-only scans, and three mixed pages with native schedules plus scanned forms or field images",
        document_ref="ORION BIOLOGICS | ARC-214 | COORDINATION SET | REV C",
        metadata_date="D:20260616172000-04'00'",
    )
    case.set_page_modalities(
        native_pages=NATIVE_PAGES,
        full_raster_pages=FULL_SCAN_PAGES,
        mixed_pages=MIXED_PAGES,
    )

    # Page 1 - native transmittal, index, and authority chain.
    c = case.new_page(
        "Coordination transmittal and sheet index",
        subtitle="Orion Biologics | Suite 214 laboratory renovation | record package",
        section_code="ARC-214-C",
    )
    draw_badge(c, "record issue", 42, 684, BLUE)
    draw_badge(c, "revision C", 139, 684, GREEN)
    draw_paragraph(
        c,
        "This package assembles the architectural, technology, electrical, field-response, and closeout records issued for coordination. Retain each sheet identity, revision, and issue authority throughout coordination use.",
        42,
        654,
        520,
        size=8.5,
        leading=11.3,
    )
    index_headers = ["Sheet", "Record", "Rev", "Issued", "Class"]
    index_rows = [
        ["TX-01", "Transmittal / index", "C", "16 Jun", "Record"],
        ["A2.14-B", "Archived floor plan", "B", "07 Jun", "Archive"],
        ["A2.14", "Controlled floor plan", "C", "12 Jun", "Construction"],
        ["A6.24", "RCP / MEP coordination", "C", "12 Jun", "Coordination"],
        ["T4.08", "Rack R2 / patching", "C", "13 Jun", "Coordination"],
        ["N1.07", "Network / access topology", "C", "13 Jun", "Coordination"],
        ["E6.02", "LP-2 / field check", "C", "14 Jun", "Field check"],
        ["RFI-214-17", "Door field response", "A", "12 Jun", "Response"],
        ["PH-214", "Field photo record", "A", "15 Jun", "Photo record"],
        ["CL-214", "Final issue release", "C", "16 Jun", "Release"],
    ]
    draw_label(c, "Controlled sheet index", 42, 596)
    draw_table(c, 42, 582, [78, 226, 46, 76, 76], [index_headers, *index_rows], font_size=6.6, zebra=True)
    revision_headers = ["Event", "Date", "Authority", "Record effect"]
    revision_rows = [
        ["Rev B issue", "07 Jun", "MS", "Archived background"],
        ["RFI response", "12 Jun", "AV", "Incorporated by Rev C"],
        ["Rev C issue", "12 Jun", "AV", "Controls coordination"],
        ["Record release", "16 Jun", "LS", "Closes package"],
    ]
    draw_label(c, "Revision and authority register", 42, 286)
    draw_table(c, 42, 272, [110, 76, 82, 236], [revision_headers, *revision_rows], font_size=7.1, zebra=True)
    c.setFillColor(HexColor("#F4F0E7"))
    c.roundRect(42, 70, 520, 54, 4, fill=1, stroke=0)
    draw_paragraph(c, "Authority order: final release, Revision C sheets, answered RFI, archived Revision B record.", 55, 103, 490, font="DocSans-Bold", size=8.1, leading=10.5, color=RED)
    case.add_gold(
        "Coordination transmittal and sheet index",
        "Package ARC-214-C is the RECORD ISSUE for the Orion Biologics Suite 214 laboratory renovation. The controlled index lists ten records from TX-01 through CL-214.\n\n"
        + markdown_table(index_headers, index_rows)
        + "\n\n"
        + markdown_table(revision_headers, revision_rows)
        + "\n\nThe authority order is final release, Revision C sheets, answered RFI, then archived Revision B record. Revision B is retained only as the archived background; Revision C controls coordination; RFI-214-17 is incorporated; the 16 June release closes the package.",
    )
    index_scored = {
        ("A2.14-B", "Rev"), ("A2.14-B", "Class"),
        ("A2.14", "Rev"), ("A2.14", "Issued"),
        ("E6.02", "Class"), ("RFI-214-17", "Issued"),
        ("CL-214", "Rev"), ("CL-214", "Class"),
    }
    case.add_region(
        "p01.index",
        "Controlled sheet index",
        "table",
        table_leaves("p01.index", index_headers, index_rows, scored_bindings=index_scored),
        budget=1,
        closed_world=True,
    )
    revision_scored = {
        ("Rev B issue", "Record effect"), ("RFI response", "Authority"),
        ("RFI response", "Record effect"), ("Rev C issue", "Record effect"),
        ("Record release", "Date"), ("Record release", "Record effect"),
    }
    case.add_region(
        "p01.revisions",
        "Revision and authority register",
        "table",
        table_leaves("p01.revisions", revision_headers, revision_rows, consequential={("Rev C issue", "Record effect")}, scored_bindings=revision_scored),
        budget=1,
        closed_world=True,
        primary_axis="source_precedence",
        secondary_axes=["table_reconstruction"],
    )
    case.add_region(
        "p01.control",
        "Package authority order",
        "text",
        [
            source_precedence_leaf("p01.control.release", "The final release outranks all earlier package records.", [["final release"], ["Revision C"]]),
            source_precedence_leaf("p01.control.rev-c", "Revision C sheets control over the archived Revision B record.", [["Revision C", "Rev C"], ["Revision B", "Rev B"], ["archived"]]),
            source_precedence_leaf("p01.control.rfi", "The answered RFI is incorporated by Revision C rather than acting as a later standalone override.", [["RFI"], ["incorporated"], ["Revision C", "Rev C"]]),
        ],
        budget=2,
        primary_axis="source_precedence",
    )
    case.add_region(
        "p01.transmittal",
        "Transmittal identity",
        "structure",
        [
            leaf("p01.tx.package", "The package identifier is ARC-214-C.", evidence=["ARC-214-C"]),
            leaf("p01.tx.project", "The project is the Orion Biologics Suite 214 laboratory renovation.", evidence=["Orion Biologics", "Suite 214"]),
            leaf("p01.tx.issue", "The transmittal is a record issue.", evidence=[["record issue", "record package"]]),
            leaf("p01.tx.sheet-count", "The controlled index lists ten records from TX-01 through CL-214.", evidence=["TX-01", "CL-214", "ten"]),
        ],
    )

    # Page 2 - full-page raster of the archived Revision B plan.
    c = case.new_page(
        "A2.14-B - Archived floor plan",
        subtitle="Record background | not for current coordination",
        section_code="REV B / ARCHIVED",
        page_size=LANDSCAPE,
    )
    _floor_plan(c, revision="B")
    c.saveState()
    c.translate(408, 320)
    c.rotate(18)
    c.setStrokeColor(Color(0.62, 0.13, 0.13, alpha=0.42))
    c.setFillColor(Color(0.62, 0.13, 0.13, alpha=0.19))
    c.setLineWidth(4)
    c.rect(-145, -30, 290, 60, fill=0, stroke=1)
    c.setFont("DocSans-Bold", 31)
    c.drawCentredString(0, -10, "SUPERSEDED - REV B")
    c.restoreState()
    c.setFillColor(INK)
    c.setFont("DocSans-Bold", 6.2)
    c.drawString(58, 107, "ISSUED 07 JUN 2026     DRAWN MS     CHECKED AV")
    c.setFont("DocSans", 5.8)
    c.drawRightString(734, 107, "FIELD BACKGROUND 214-B-0707")
    case.add_gold(
        "A2.14-B - Archived floor plan",
        "Revision B is visibly stamped superseded and dated 7 June 2026; the archived field-background record is 214-B-0707. The overall footprint is 45 ft by 22 ft. Clean Prep 214 is 18 ft 6 in by 12 ft and is west of Lab B 215, which is 16 ft by 12 ft. Freezer 216 is east of Lab B; Lab B is directly north of corridor C2; Wash 217 is immediately west of corridor C2; IT Closet 218 is south of Freezer 216 and east of C2. The old Lab B opening is near the middle of its south wall, has a north swing into Lab B, and is keyed by callout 6. Callout 9 points to rack R2 in IT Closet 218; callout 11 points to FZ-3 in Freezer 216. The first egress segment runs from Lab B through the old opening and the second turns west along C2.",
    )
    case.add_region(
        "p02.base-rooms",
        "Archived-plan room geometry",
        "diagram",
        [
            visual_leaf("p02.room.clean-lab", "Clean Prep 214 is immediately west of Lab B 215.", [["Clean Prep 214"], ["Lab B 215"], ["west"]]),
            visual_leaf("p02.room.lab-freezer", "Freezer 216 is immediately east of Lab B 215.", [["Freezer 216"], ["Lab B 215"], ["east"]]),
            visual_leaf("p02.room.lab-corridor", "Lab B 215 directly adjoins corridor C2 along its south wall.", [["Lab B 215"], ["C2"], ["corridor"], ["south"]], harm=2),
            visual_leaf("p02.room.freezer-it", "IT Closet 218 is directly south of Freezer 216.", [["IT Closet 218"], ["Freezer 216"], ["south"]]),
            visual_leaf("p02.room.wash-corridor", "Wash 217 is immediately west of corridor C2.", [["Wash 217"], ["C2"], ["corridor"], ["west"]]),
            visual_leaf("p02.room.overall", "The archived plan shows an overall footprint of 45 ft by 22 ft.", [["45'-0\"", "45 ft"], ["22'-0\"", "22 ft"]]),
            visual_leaf("p02.room.lab-size", "Lab B is dimensioned 16 ft by 12 ft.", [["Lab B", "215"], ["16'-0\"", "16 ft"], ["12'-0\"", "12 ft"]]),
            visual_leaf("p02.room.clean-size", "Clean Prep is dimensioned 18 ft 6 in by 12 ft.", [["Clean Prep", "214"], ["18'-6\"", "18 ft 6"], ["12'-0\"", "12 ft"]]),
        ],
        budget=2,
        primary_axis="chart_diagram_spatial",
        unique_evidence=False,
        text_only_recoverable=False,
    )
    case.add_region(
        "p02.base-door",
        "Archived Lab B opening",
        "diagram",
        [
            visual_leaf("p02.door.wall", "The Revision B Lab B opening is in the wall shared with corridor C2.", [["Lab B"], ["C2"], ["corridor"], ["shared", "south wall"]], harm=2),
            visual_leaf("p02.door.position", "The Revision B opening is near the middle of the Lab B south wall.", [["Lab B", "215"], ["middle", "center"], ["south wall"]]),
            visual_leaf("p02.door.swing", "The Revision B door leaf swings north into Lab B.", [["Lab B", "215"], ["north"], ["swing"]], harm=2),
            visual_leaf("p02.door.callout", "Callout 6 keys the Revision B Lab B opening.", [["callout 6", "6"], ["Lab B", "215"], ["opening", "door"]]),
        ],
        budget=2,
        unique_evidence=False,
        text_only_recoverable=False,
    )
    case.add_region(
        "p02.base-egress-callouts",
        "Archived egress and equipment callouts",
        "diagram",
        [
            directed_edge_leaf("p02.egress.lab-door", "The first egress arrow runs from Lab B to the old corridor opening.", ["Lab B"], ["old corridor opening", "old opening"], relation=["egress"]),
            directed_edge_leaf("p02.egress.door-west", "The second egress arrow runs from the archived Revision B opening west along corridor C2.", ["archived opening", "Revision B opening", "old opening", "old corridor opening"], ["west along corridor C2", "west along C2", "west through C2", "C2 west"], relation=["egress", "west"]),
            visual_leaf("p02.callout.9", "Callout 9 points to rack R2 in IT Closet 218.", [["callout 9", "9"], ["rack R2", "R2"], ["IT Closet 218"]]),
            visual_leaf("p02.callout.11", "Callout 11 points to freezer FZ-3 in room 216.", [["callout 11", "11"], ["FZ-3"], ["216"]]),
        ],
        budget=2,
        unique_evidence=False,
        text_only_recoverable=False,
    )
    case.add_region(
        "p02.base-titleblock",
        "Archived-plan title-block state",
        "form",
        [
            source_precedence_leaf("p02.state.superseded", "The Revision B plan is visibly stamped superseded.", [["Revision B", "Rev B"], ["SUPERSEDED", "superseded"]], harm=2),
            leaf("p02.state.date", "The archived plan issue date is 2026-06-07.", evidence=[["07 JUN 2026", "7 June 2026"]]),
            leaf("p02.state.record", "The archived field-background record is 214-B-0707.", evidence=["214-B-0707"]),
        ],
        budget=1,
        text_only_recoverable=False,
    )

    # Page 3 - native controlling plan with old/new overlay.
    c = case.new_page(
        "A2.14 - Controlled floor plan and overlay",
        subtitle="Coordinated issue | current geometry shown solid blue; archived opening shown dashed red",
        section_code="REV C / IFC",
        page_size=LANDSCAPE,
    )
    _floor_plan(c, revision="C", overlay=True)
    c.setFillColor(INK)
    c.setFont("DocSans-Bold", 6.2)
    c.drawString(58, 107, "ISSUED 12 JUN 2026     DRAWN MS     CHECKED AV")
    c.setFont("DocSans", 5.8)
    c.drawRightString(734, 107, "COORDINATION RECORD A2.14-C")
    case.add_gold(
        "A2.14 - Controlled floor plan and overlay",
        "Revision C retains the 45 ft by 22 ft overall footprint but moves the Lab B opening 4 ft 6 in west of the dashed Revision B position. The dimension between the old and new opening hinge points is 4 ft 6 in. The current door is D-214B, is in the Lab B/C2 shared wall, and swings south into corridor C2. Reader CR-6 is on the corridor side at the east jamb. Callout 6 keys that reader and opening; callout 9 keys rack R2 in IT Closet 218; callout 11 keys FZ-3 in Freezer 216. Egress runs from Lab B through D-214B and then west along C2. The north arrow points toward the top of the sheet. The solid blue opening is Revision C's controlling current geometry; the dashed red opening is archived Revision B geometry.",
    )
    case.add_region(
        "p03.current-rooms",
        "Controlled-plan room geometry",
        "diagram",
        [
            visual_leaf("p03.room.clean-lab", "Clean Prep 214 remains immediately west of Lab B 215.", [["Clean Prep 214"], ["Lab B 215"], ["west"]]),
            visual_leaf("p03.room.lab-freezer", "Freezer 216 remains immediately east of Lab B 215.", [["Freezer 216"], ["Lab B 215"], ["east"]]),
            visual_leaf("p03.room.lab-corridor", "The south wall of Lab B 215 directly adjoins corridor C2.", [["Lab B 215"], ["C2"], ["corridor"], ["south"]], harm=2),
            visual_leaf("p03.room.freezer-it", "IT Closet 218 remains directly south of Freezer 216.", [["IT Closet 218"], ["Freezer 216"], ["south"]]),
            visual_leaf("p03.room.overall", "The controlled plan preserves the 45 ft by 22 ft overall footprint.", [["45'-0\"", "45 ft"], ["22'-0\"", "22 ft"]]),
            visual_leaf("p03.room.north", "The north arrow points toward the top of the sheet.", [["north", "N"], ["top", "up"]]),
        ],
        budget=2,
        unique_evidence=False,
        text_only_recoverable=False,
    )
    case.add_region(
        "p03.current-door",
        "Revision C door and reader geometry",
        "diagram",
        [
            visual_leaf("p03.door.wall", "D-214B is set in the wall shared by Lab B 215 and corridor C2.", [["D-214B"], ["Lab B 215"], ["C2"], ["corridor"]], harm=2),
            visual_leaf("p03.door.shift", "The solid Revision C opening is 4 ft 6 in west of the dashed Revision B opening.", [["Revision C", "Rev C"], ["Revision B", "Rev B"], ["4'-6\"", "4 ft 6"], ["west"]], harm=2),
            visual_leaf("p03.door.swing", "D-214B swings south into corridor C2.", [["D-214B"], ["south"], ["C2", "corridor"]], harm=2),
            visual_leaf(
                "p03.door.reader-side",
                "Reader CR-6 is on the corridor side of D-214B.",
                [["CR-6"], ["corridor side", "C2"], ["D-214B"]],
                local_bindings=[[["CR-6"], ["corridor side", "C2"], ["D-214B"]]],
                harm=2,
            ),
            visual_leaf("p03.door.reader-jamb", "Reader CR-6 is at the east jamb of D-214B.", [["CR-6"], ["east jamb", "east"], ["D-214B"]], harm=2),
            visual_leaf(
                "p03.door.old-style",
                "The archived door is dashed red while the current door is solid blue or teal-blue.",
                [["archived"], ["dashed red"], ["current"], ["solid blue", "solid teal", "teal/blue", "teal-blue", "blue/teal"], ["door", "opening"]],
                local_bindings=[
                    [["archived"], ["dashed red"], ["door", "opening"]],
                    [["current"], ["solid blue", "solid teal", "teal/blue", "teal-blue", "blue/teal"], ["door", "opening"]],
                ],
            ),
            visual_leaf("p03.door.callout", "Callout 6 keys the reader and door opening.", [["callout 6", "6"], ["reader", "CR-6"], ["door", "opening"]]),
        ],
        budget=3,
        unique_evidence=False,
        text_only_recoverable=False,
    )
    case.add_region(
        "p03.current-egress-callouts",
        "Controlled egress and equipment callouts",
        "diagram",
        [
            directed_edge_leaf(
                "p03.egress.lab-door",
                "The first egress segment runs from Lab B through D-214B.",
                ["Lab B"],
                ["D-214B"],
                relation=["egress", "through"],
            ),
            directed_edge_leaf(
                "p03.egress.door-west",
                "The second egress segment continues west along corridor C2.",
                ["D-214B", "current opening"],
                ["west along corridor C2", "west along C2", "west through C2", "C2 west"],
                relation=["egress"],
            ),
            visual_leaf("p03.callout.9", "Callout 9 keys rack R2 inside IT Closet 218.", [["callout 9", "9"], ["R2"], ["IT Closet 218"]]),
            visual_leaf("p03.callout.11", "Callout 11 keys FZ-3 inside Freezer 216.", [["callout 11", "11"], ["FZ-3"], ["Freezer 216"]]),
        ],
        budget=2,
        unique_evidence=False,
        text_only_recoverable=False,
    )
    case.add_region(
        "p03.overlay",
        "Revision overlay interpretation",
        "diagram",
        [
            source_precedence_leaf(
                "p03.overlay.current",
                "The solid blue or teal-blue opening is the controlling Revision C geometry.",
                [["solid blue", "solid teal", "teal/blue", "teal-blue", "blue/teal"], ["Revision C", "Rev C"], ["controlling", "current"]],
            ),
            source_precedence_leaf("p03.overlay.old", "The dashed red opening is retained as archived Revision B geometry.", [["dashed red", "dashed"], ["Revision B", "Rev B"], ["archived"]]),
            visual_leaf(
                "p03.overlay.same-wall",
                "Both old and new openings lie on the shared wall between Lab B and C2.",
                [["old", "Revision B"], ["new", "Revision C"], ["Lab B"], ["C2"], ["shared wall"]],
                local_bindings=[[["old", "Revision B"], ["new", "Revision C"], ["Lab B"], ["C2"], ["shared wall"]]],
            ),
            visual_leaf("p03.overlay.delta", "The overlay dimension between the opening hinge points is 4 ft 6 in.", [["4'-6\"", "4 ft 6"], ["hinge", "opening"], ["dimension"]]),
        ],
        budget=2,
        primary_axis="source_precedence",
        secondary_axes=["chart_diagram_spatial"],
        text_only_recoverable=False,
    )

    # Page 4 - native reflected ceiling and MEP coordination diagram.
    c = case.new_page(
        "A6.24 - Reflected ceiling and MEP coordination",
        subtitle="Suite 214 ceiling zones | device geometry and conflict resolution",
        section_code="REV C",
        page_size=LANDSCAPE,
    )
    px, py, pw, ph = 75, 150, 590, 330
    c.setStrokeColor(INK)
    c.setLineWidth(1.4)
    c.rect(px, py, pw, ph, fill=0, stroke=1)
    # Two-foot ceiling grid.
    c.setStrokeColor(HexColor("#CCD1D4"))
    c.setLineWidth(0.35)
    for x in range(int(px + 30), int(px + pw), 30):
        c.line(x, py, x, py + ph)
    for y in range(int(py + 30), int(py + ph), 30):
        c.line(px, y, px + pw, y)
    c.setStrokeColor(INK)
    c.setLineWidth(1)
    c.line(px + 250, py, px + 250, py + ph)
    c.setFont("DocSans-Bold", 7)
    c.setFillColor(INK)
    c.drawString(px + 10, py + ph - 18, "ZONE 214 / CLEAN PREP")
    c.drawString(px + 270, py + ph - 18, "ZONE 215 / LAB B")
    # Fixtures: lights, diffusers, sprinkler, sensor, panel, VAV branch.
    fixtures = {
        "L-4": (205, 386),
        "L-5": (440, 386),
        "SD-4": (362, 421),
        "RG-2": (565, 278),
        "SP-7": (482, 425),
        "OS-2": (520, 218),
        "CP-4": (382, 253),
        "B-2": (420, 182),
    }
    for name, (x, y) in fixtures.items():
        if name.startswith("L"):
            c.setStrokeColor(BLUE)
            c.rect(x - 28, y - 8, 56, 16, fill=0, stroke=1)
        elif name.startswith("S") and name != "SP-7":
            c.setStrokeColor(GREEN)
            c.circle(x, y, 12, fill=0, stroke=1)
            c.line(x - 8, y - 8, x + 8, y + 8)
            c.line(x - 8, y + 8, x + 8, y - 8)
        elif name == "RG-2":
            c.setStrokeColor(GREEN)
            c.rect(x - 13, y - 13, 26, 26, fill=0, stroke=1)
            for offset in (-7, 0, 7):
                c.line(x - 11, y + offset, x + 11, y + offset)
        elif name == "SP-7":
            c.setStrokeColor(RED)
            c.circle(x, y, 5, fill=0, stroke=1)
            c.line(x - 8, y, x + 8, y)
            c.line(x, y - 8, x, y + 8)
        elif name == "OS-2":
            c.setStrokeColor(AMBER)
            c.circle(x, y, 9, fill=0, stroke=1)
        elif name == "CP-4":
            c.setStrokeColor(INK)
            c.rect(x - 18, y - 13, 36, 26, fill=0, stroke=1)
        else:
            c.setStrokeColor(MUTED)
            c.rect(x - 55, y - 10, 110, 20, fill=0, stroke=1)
        c.setFillColor(INK)
        c.setFont("DocSans-Bold", 5.8)
        c.drawString(x + 14, y + 7, name)
    # Supply route and data/sensor control are arrowed visual relations.
    draw_arrow(c, 708, 420, fixtures["SD-4"][0] + 12, fixtures["SD-4"][1], color=GREEN, width=1.5)
    c.setFillColor(MUTED)
    c.setFont("DocSans", 5.6)
    c.drawString(670, 432, "VAV-214")
    draw_arrow(c, fixtures["OS-2"][0], fixtures["OS-2"][1] - 10, fixtures["CP-4"][0] + 18, fixtures["CP-4"][1], color=AMBER, dashed=True)
    draw_arrow(c, fixtures["CP-4"][0] - 18, fixtures["CP-4"][1], 710, 244, color=BLUE, dashed=True)
    c.setFillColor(MUTED)
    c.setFont("DocSans", 5.6)
    c.drawString(666, 250, "BAS-214")
    # Conflict cloud: old diffuser location overlaps the sprinkler clearance.
    old_sd = (468, 412)
    c.saveState()
    c.setStrokeColor(RED)
    c.setDash(4, 2)
    c.circle(old_sd[0], old_sd[1], 14, fill=0, stroke=1)
    c.circle(fixtures["SP-7"][0], fixtures["SP-7"][1], 24, fill=0, stroke=1)
    c.restoreState()
    draw_arrow(c, old_sd[0] - 12, old_sd[1], fixtures["SD-4"][0] + 14, fixtures["SD-4"][1], color=RED, dashed=True)
    _dimension(c, fixtures["SD-4"][0], 454, fixtures["SP-7"][0], 454, "8'-0\"", color=RED)
    _bubble(c, 496, 451, "C1")
    draw_label(c, "Symbol key", 75, 118)
    c.setFont("DocSans", 5.9)
    c.setFillColor(MUTED)
    c.drawString(130, 118, "solid green: supply   dashed amber: sensor control   dashed blue: BAS data   dashed red: relocated")
    case.add_gold(
        "A6.24 - Reflected ceiling and MEP coordination",
        "The ceiling plan places SD-4 north-west of bench B-2 and west of sprinkler SP-7. SP-7 is north-east of ceiling panel CP-4. Occupancy sensor OS-2 is south-east of CP-4. Light L-5 is north of CP-4. Return grille RG-2 is east of CP-4. The solid green VAV-214 supply arrow runs to SD-4. A dashed amber control arrow runs from OS-2 to CP-4; a dashed blue BAS link runs from CP-4 to BAS-214. The dashed old diffuser location is near SP-7; the red relocation arrow moves it west to the solid current SD-4 position, producing an 8 ft separation. The solid SD-4 symbol is current and the dashed old symbol is superseded. Conflict bubble C1 keys that resolved move.",
    )
    case.add_region(
        "p04.ceiling-geometry",
        "Ceiling device geometry",
        "diagram",
        [
            visual_leaf("p04.geo.sd-bench", "SD-4 is north-west of bench B-2.", [["SD-4"], ["B-2"], ["north-west", "northwest"]]),
            visual_leaf("p04.geo.sd-sp", "SD-4 is west of sprinkler SP-7.", [["SD-4"], ["SP-7"], ["west"]], harm=2),
            visual_leaf("p04.geo.sp-cp", "SP-7 is north-east of ceiling panel CP-4.", [["SP-7"], ["CP-4"], ["north-east", "northeast"]]),
            visual_leaf("p04.geo.os-cp", "OS-2 is south-east of CP-4.", [["OS-2"], ["CP-4"], ["south-east", "southeast"]]),
            visual_leaf("p04.geo.light-cp", "Light L-5 is north of CP-4.", [["L-5"], ["CP-4"], ["north"]]),
            visual_leaf("p04.geo.rg-cp", "Return grille RG-2 is east of CP-4.", [["RG-2"], ["CP-4"], ["east"]]),
        ],
        budget=2,
        text_only_recoverable=False,
    )
    case.add_region(
        "p04.mep-paths",
        "Directed MEP and controls paths",
        "diagram",
        [
            directed_edge_leaf("p04.edge.vav-sd", "A solid supply path runs from VAV-214 to SD-4.", ["VAV-214"], ["SD-4"], relation=["supply", "solid"]),
            directed_edge_leaf("p04.edge.os-cp", "A dashed control path runs from OS-2 to CP-4.", ["OS-2"], ["CP-4"], relation=["control", "dashed"]),
            directed_edge_leaf("p04.edge.cp-bas", "A dashed data path runs from CP-4 to BAS-214.", ["CP-4"], ["BAS-214"], relation=["data", "BAS", "dashed"]),
            visual_leaf("p04.edge.supply-style", "The VAV supply route is solid green.", [["VAV"], ["supply"], ["solid"], ["green"]]),
            visual_leaf("p04.edge.control-style", "The sensor-control route is dashed amber and the BAS route is dashed blue.", [["sensor", "control"], ["dashed amber", "amber"], ["BAS"], ["dashed blue", "blue"]]),
        ],
        budget=2,
        text_only_recoverable=False,
    )
    case.add_region(
        "p04.conflict",
        "Resolved ceiling conflict",
        "diagram",
        [
            visual_leaf("p04.conflict.old", "The dashed red relocation graphic marks the old diffuser area near sprinkler SP-7 and conflict bubble C1.", [["dashed red", "dashed"], ["relocation", "old diffuser"], ["SP-7"], ["C1", "conflict"]]),
            directed_edge_leaf(
                "p04.conflict.move",
                "The red relocation arrow runs from the old diffuser position west to SD-4.",
                ["old diffuser", "old position", "SP-7", "C1 conflict area", "SP-7/C1 conflict area"],
                ["SD-4"],
                relation=["relocation", "west"],
            ),
            visual_leaf("p04.conflict.clearance", "The revised SD-4 position is dimensioned 8 ft from SP-7.", [["SD-4"], ["SP-7"], ["8'-0\"", "8 ft"]], harm=2),
            visual_leaf("p04.conflict.key", "Conflict bubble C1 keys the diffuser relocation.", [["C1"], ["diffuser", "SD-4"], ["relocation", "move"]]),
        ],
        budget=3,
        primary_axis="chart_diagram_spatial",
        secondary_axes=["source_precedence"],
        text_only_recoverable=False,
    )

    # Page 5 - native rack elevation and curated patch bindings.
    c = case.new_page(
        "T4.08 - Rack R2 elevation and patching",
        subtitle="IT Closet 218 | front elevation | coordinated ports only",
        section_code="REV C",
    )
    rack_x, rack_y, rack_w, rack_h = 55, 132, 172, 520
    c.setStrokeColor(INK)
    c.setLineWidth(1.5)
    c.rect(rack_x, rack_y, rack_w, rack_h, fill=0, stroke=1)
    unit_h = rack_h / 44
    devices = [
        (42, 2, "CS-2", "core switch", "#DCE8F4"),
        (36, 2, "PP-7", "patch panel", "#F0F1F1"),
        (31, 2, "AC-6", "door controller", "#F2DADA"),
        (26, 3, "UPS-A", "2.2 kVA", "#F4E8C8"),
        (19, 1, "GW-3", "freezer gateway", "#DCEBDF"),
        (14, 2, "NVR-B", "event bridge", "#E7DFF0"),
        (8, 1, "PDU-2", "metered", "#DFE7EA"),
    ]
    for top_u, units, name, note, color in devices:
        y = rack_y + (top_u - 1) * unit_h
        c.setFillColor(HexColor(color))
        c.setStrokeColor(INK)
        c.rect(rack_x + 34, y, rack_w - 46, units * unit_h, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("DocSans-Bold", 5.8)
        c.drawString(rack_x + 40, y + units * unit_h / 2 + 1, name)
        c.setFont("DocSans", 5.5)
        c.drawRightString(rack_x + rack_w - 16, y + units * unit_h / 2 + 1, note)
        c.setFont("DocSans", 5.5)
        unit_label = f"U{top_u}-{top_u + units - 1}" if units > 1 else f"U{top_u}"
        c.drawRightString(rack_x + 29, y + 2, unit_label)
    # Elevation callout indicates the west/top tray entry without a prose recap.
    c.setStrokeColor(MUTED)
    c.setLineWidth(2)
    c.line(12, 638, rack_x + 34, 638)
    c.line(12, 646, rack_x + 34, 646)
    draw_arrow(c, 38, 650, rack_x + 34, 650, color=RED, width=1.5)
    _bubble(c, 28, 650, "B")
    patch_headers = ["Port", "Drop", "Endpoint", "Location", "VLAN", "Medium"]
    patch_rows = [
        ["CS-2/01", "D214-01", "Tablet dock", "214-W", "210", "Cat6A"],
        ["CS-2/07", "D215-03", "CR-6", "215-S", "230", "Cat6A"],
        ["CS-2/08", "D215-04", "DC-6", "R2/U31", "230", "Cat6A"],
        ["CS-2/12", "D216-02", "FZ-3", "216-E", "240", "Cat6A"],
        ["CS-2/13", "D216-03", "GW-3", "R2/U19", "240", "Cat6A"],
        ["CS-2/19", "D218-01", "FW-02 mgmt", "218-R2", "99", "Cat6A"],
        ["PP-7/21", "D214-11", "BAS-214", "214-N", "120", "OM4"],
        ["PP-7/22", "D215-12", "CP-4", "215-CLG", "120", "OM4"],
    ]
    draw_label(c, "Patch and endpoint schedule", 245, 655)
    draw_table(c, 245, 640, [50, 50, 70, 55, 40, 50], [patch_headers, *patch_rows], font_size=6.0, zebra=True)
    draw_label(c, "Internal patch paths", 245, 297)
    internal_paths = [
        ("PP-7/07", "CS-2/07", "D215-03"),
        ("PP-7/12", "CS-2/12", "D216-02"),
        ("PP-7/22", "OM4-2", "D215-12"),
    ]
    for row_index, (source, middle, destination) in enumerate(internal_paths):
        y = 236 - row_index * 58
        _box(c, 245, y, 72, 30, source, fill="#F5F7F7")
        _box(c, 359, y, 72, 30, middle, fill="#EEF3F7")
        _box(c, 473, y, 72, 30, destination, fill="#F5F7F7")
        draw_arrow(c, 317, y + 15, 359, y + 15, color=BLUE, width=1.2)
        draw_arrow(c, 431, y + 15, 473, y + 15, color=BLUE, width=1.2)
    case.add_gold(
        "T4.08 - Rack R2 elevation and patching",
        "Rack R2 placements are CS-2 at U42-U43, PP-7 at U36-U37, AC-6 at U31-U32, UPS-A at U26-U28, GW-3 at U19, NVR-B at U14-U15, and PDU-2 at U8. Callout B identifies the tray entry on the west/top side of the rack.\n\n"
        + markdown_table(patch_headers, patch_rows)
        + "\n\nInternal patch paths are PP-7/07 -> CS-2/07 -> D215-03; PP-7/12 -> CS-2/12 -> D216-02; and PP-7/22 -> OM4-2 -> D215-12.",
    )
    case.add_region(
        "p05.rack",
        "Rack-unit elevation",
        "diagram",
        [
            visual_leaf("p05.rack.cs2", "Core switch CS-2 occupies U42-U43.", [["CS-2"], ["U42-U43"]], local_bindings=[["CS-2", "U42-U43"]]),
            visual_leaf("p05.rack.pp7", "Patch panel PP-7 occupies U36-U37.", [["PP-7"], ["U36-U37"]], local_bindings=[["PP-7", "U36-U37"]]),
            visual_leaf("p05.rack.ac6", "Door controller AC-6 occupies U31-U32.", [["AC-6"], ["U31-U32"]], local_bindings=[["AC-6", "U31-U32"]], harm=2),
            visual_leaf("p05.rack.ups", "UPS-A occupies U26-U28.", [["UPS-A", "UPS A"], ["U26-U28"]], local_bindings=[["UPS-A", "U26-U28"]]),
            visual_leaf("p05.rack.gw3", "Freezer gateway GW-3 occupies U19.", [["GW-3"], ["U19"]], local_bindings=[["GW-3", "U19"]]),
            visual_leaf("p05.rack.nvr", "NVR-B occupies U14-U15.", [["NVR-B"], ["U14-U15"]], local_bindings=[["NVR-B", "U14-U15"]]),
            visual_leaf("p05.rack.entry", "Callout B identifies a tray entry at the rack's west/top side.", [["callout B", "B"], ["tray entry"], ["west", "top"]]),
        ],
        budget=2,
        text_only_recoverable=False,
    )
    patch_scored = {
        ("CS-2/01", "Endpoint"), ("CS-2/01", "VLAN"),
        ("CS-2/07", "Endpoint"), ("CS-2/07", "Location"), ("CS-2/07", "VLAN"),
        ("CS-2/08", "Endpoint"), ("CS-2/08", "Location"),
        ("CS-2/12", "Endpoint"), ("CS-2/12", "Location"), ("CS-2/12", "VLAN"),
        ("CS-2/13", "Endpoint"), ("CS-2/13", "Location"),
        ("PP-7/21", "Endpoint"), ("PP-7/22", "Endpoint"),
    }
    case.add_region(
        "p05.patch",
        "Patch and endpoint schedule",
        "table",
        table_leaves("p05.patch", patch_headers, patch_rows, consequential={("CS-2/07", "Endpoint"), ("CS-2/12", "VLAN")}, scored_bindings=patch_scored),
        budget=2,
        closed_world=True,
    )
    case.add_region(
        "p05.internal-paths",
        "Internal patch paths",
        "diagram",
        [
            directed_edge_leaf("p05.path.07-a", "The first path runs from PP-7/07 to CS-2/07.", ["PP-7/07"], ["CS-2/07"], relation=["patch"]),
            directed_edge_leaf("p05.path.07-b", "The first path continues from CS-2/07 to D215-03.", ["CS-2/07"], ["D215-03"], relation=["patch"]),
            directed_edge_leaf("p05.path.12-a", "The second path runs from PP-7/12 to CS-2/12.", ["PP-7/12"], ["CS-2/12"], relation=["patch"]),
            directed_edge_leaf("p05.path.12-b", "The second path continues from CS-2/12 to D216-02.", ["CS-2/12"], ["D216-02"], relation=["patch"]),
            directed_edge_leaf("p05.path.22-a", "The third path runs from PP-7/22 to OM4-2.", ["PP-7/22"], ["OM4-2"], relation=["patch"]),
            directed_edge_leaf("p05.path.22-b", "The third path continues from OM4-2 to D215-12.", ["OM4-2"], ["D215-12"], relation=["patch"]),
        ],
        budget=2,
        primary_axis="chart_diagram_spatial",
        text_only_recoverable=False,
    )

    # Page 6 - native directed topology; labels alone do not expose direction.
    c = case.new_page(
        "N1.07 - Network and access-control topology",
        subtitle="Directed service paths | solid operational edges | dashed conditional edge",
        section_code="REV C",
        page_size=LANDSCAPE,
    )
    nodes = {
        "FW-02": (52, 360),
        "CS-2": (195, 360),
        "CR-6": (365, 455),
        "DC-6": (365, 330),
        "FZ-3": (365, 205),
        "NVR-B": (560, 455),
        "ACS-CORE": (560, 330),
        "QA-210": (560, 205),
        "BAS-214": (680, 270),
    }
    for name, (x, y) in nodes.items():
        _box(c, x, y, 88, 34, name, fill="#F5F7F7")
    edges = [
        ("FW-02", "CS-2", "TAG 99/210/230/240", False, BLUE),
        ("CS-2", "CR-6", "V230 / events", False, BLUE),
        ("CR-6", "DC-6", "Wiegand", False, AMBER),
        ("DC-6", "ACS-CORE", "V230 / auth", False, BLUE),
        ("CS-2", "FZ-3", "V240 / telemetry", False, BLUE),
        ("FZ-3", "QA-210", "alarm / one-way", False, GREEN),
        ("CR-6", "NVR-B", "event mirror", False, GREEN),
        ("FZ-3", "BAS-214", "optional trend", True, AMBER),
    ]
    for source, destination, label, dashed, color in edges:
        sx, sy = nodes[source]
        dx, dy = nodes[destination]
        start = (sx + 88, sy + 17)
        end = (dx, dy + 17)
        if source == "CR-6" and destination == "DC-6":
            start = (sx + 44, sy)
            end = (dx + 44, dy + 34)
        elif source == "FZ-3" and destination == "BAS-214":
            start = (sx + 88, sy + 8)
            end = (dx, dy + 8)
        draw_arrow(c, *start, *end, color=color, dashed=dashed, width=1.4)
        c.setFillColor(MUTED)
        c.setFont("DocSans", 5.6)
        label_x = (start[0] + end[0]) / 2
        label_y = (start[1] + end[1]) / 2 + 8
        if source == "FW-02" and destination == "CS-2":
            c.drawCentredString(label_x, label_y + 24, "TAGGED TRUNK")
            c.drawCentredString(label_x, label_y + 15, "99/210/230/240")
        else:
            if label.startswith("alarm"):
                label_y -= 16
            elif label.startswith("optional"):
                label_y += 6
            c.drawCentredString(label_x, label_y, label)
    policy_headers = ["Path key", "Transport", "Mode", "Policy"]
    policy_rows = [
        ["ACL-230-A", "V230", "Auth", "Permit one-way"],
        ["MIR-230-B", "V230", "Event", "Permit one-way"],
        ["TEL-240-Q", "V240", "Alarm", "Permit one-way"],
        ["OPT-240-B", "V240", "Trend", "Conditional"],
    ]
    draw_table(c, 110, 158, [130, 120, 110, 220], [policy_headers, *policy_rows], font_size=6.6, zebra=True)
    case.add_gold(
        "N1.07 - Network and access-control topology",
        "Directed edges are FW-02 to CS-2 (tagged trunk 99/210/230/240); CS-2 to CR-6 (VLAN 230 events); CR-6 to DC-6 (Wiegand); DC-6 to ACS-CORE (VLAN 230 authorization); CS-2 to FZ-3 (VLAN 240 telemetry); FZ-3 to QA-210 (one-way alarm); CR-6 to NVR-B (event mirror); and a dashed conditional FZ-3 to BAS-214 trend edge. The CR-6 event mirror branches to NVR-B before the DC-6 authorization target. No reverse authorization, mirror, or alarm edges are drawn.\n\n"
        + markdown_table(policy_headers, policy_rows),
    )
    case.add_region(
        "p06.network-edges",
        "Directed network service edges",
        "diagram",
        [
            directed_edge_leaf("p06.edge.fw-cs", "A tagged trunk runs from FW-02 to CS-2.", ["FW-02"], ["CS-2"], relation=["tagged trunk", "99/210/230/240"], harm=2),
            directed_edge_leaf("p06.edge.cs-cr", "A VLAN 230 event path runs from CS-2 to CR-6.", ["CS-2"], ["CR-6"], relation=["VLAN 230 event", "VLAN 230 events", "VLAN 230 / events"], harm=2),
            directed_edge_leaf("p06.edge.cs-fz", "A VLAN 240 telemetry path runs from CS-2 to FZ-3.", ["CS-2"], ["FZ-3"], relation=["VLAN 240 telemetry", "VLAN 240 / telemetry"], harm=2),
            directed_edge_leaf("p06.edge.fz-qa", "A one-way alarm path runs from FZ-3 to QA-210.", ["FZ-3"], ["QA-210"], relation=["one-way", "alarm"]),
            directed_edge_leaf("p06.edge.cr-nvr", "An event-mirror path runs from CR-6 to NVR-B.", ["CR-6"], ["NVR-B"], relation=["event mirror", "mirror"]),
            directed_edge_leaf("p06.edge.fz-bas", "A dashed conditional trend path runs from FZ-3 to BAS-214.", ["FZ-3"], ["BAS-214"], relation=["dashed", "conditional", "trend"]),
            visual_leaf("p06.edge.conditional", "The FZ-3 to BAS-214 edge is dashed and conditional.", [["FZ-3"], ["BAS-214"], ["dashed"], ["conditional"]]),
        ],
        budget=3,
        text_only_recoverable=False,
    )
    case.add_region(
        "p06.access-edges",
        "Directed access-control chain",
        "diagram",
        [
            directed_edge_leaf("p06.access.cs-cr", "The access chain enters CR-6 from CS-2.", ["CS-2"], ["CR-6"], relation=["access", "VLAN 230"]),
            directed_edge_leaf("p06.access.cr-dc", "Reader data runs from CR-6 to DC-6 by Wiegand.", ["CR-6"], ["DC-6"], relation=["Wiegand"]),
            directed_edge_leaf("p06.access.dc-core", "Authorization traffic runs from DC-6 to ACS-CORE.", ["DC-6"], ["ACS-CORE"], relation=["authorization", "auth"]),
            visual_leaf("p06.access.branch", "The CR-6 event mirror branches to NVR-B before the DC-6 authorization target.", [["CR-6"], ["NVR-B"], ["DC-6"], ["branch", "mirror"], ["before", "prior to"]]),
        ],
        budget=3,
        text_only_recoverable=False,
    )
    policy_scored = {
        ("ACL-230-A", "Transport"), ("ACL-230-A", "Policy"),
        ("MIR-230-B", "Mode"), ("MIR-230-B", "Policy"),
        ("TEL-240-Q", "Mode"), ("TEL-240-Q", "Policy"),
        ("OPT-240-B", "Mode"), ("OPT-240-B", "Policy"),
    }
    case.add_region(
        "p06.policy",
        "Directed path policy register",
        "table",
        table_leaves("p06.policy", policy_headers, policy_rows, consequential={("ACL-230-A", "Policy"), ("OPT-240-B", "Policy")}, scored_bindings=policy_scored),
        budget=2,
        closed_world=True,
        primary_axis="table_reconstruction",
    )

    # Page 7 - mixed electrical schedule and embedded scanned field checklist.
    c = case.new_page(
        "E6.02 - Panel LP-2 and field check",
        subtitle="LP-2 branch schedule with field walkdown record",
        section_code="REV C / FIELD",
    )
    panel_headers = ["Circuit", "Load", "Breaker", "Branch", "Room", "Record"]
    panel_rows = [
        ["L2-11", "Bench outlets B", "20A/1P", "Normal", "215", "B-2"],
        ["L2-13", "Autoclave AC-1", "30A/2P", "Normal", "217", "AC-1"],
        ["L2-15", "Door controller", "20A/1P", "Emergency", "215", "DC-6"],
        ["L2-17", "Freezer", "20A/1P", "Emergency", "216", "FZ-3"],
        ["L2-19", "Rack UPS", "20A/1P", "Emergency", "218", "UPS-A"],
        ["L2-21", "Spare", "20A/1P", "Normal", "-", "Future"],
    ]
    draw_table(c, 42, 662, [65, 132, 70, 88, 52, 90], [panel_headers, *panel_rows], font_size=6.8, zebra=True)
    draw_label(c, "Embedded field walkdown record", 42, 404)
    checklist = _commissioning_scan()
    c.drawImage(image_reader(checklist), 42, 92, width=520, height=288, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(HexColor("#94989A"))
    c.rect(42, 92, 520, 288, fill=0, stroke=1)
    case.add_gold(
        "E6.02 - Panel LP-2 and field check",
        markdown_table(panel_headers, panel_rows)
        + "\n\nThe embedded field-check record is EC-214-19, dated 14 June 2026. Its explicit states are:\n"
        + "- Torque witness marks complete: checked.\n"
        + "- L2-15 field tag installed: checked.\n"
        + "- L2-17 field tag installed: checked.\n"
        + "- L2-19 field tag installed: checked.\n"
        + "- L2-21 released for use: unchecked.\n"
        + "- Emergency transfer witnessed: checked.\n"
        + "- Reader polarity exception open: crossed out.\n\n"
        + "Technician JH and witness LS recorded that panel LP-2 was energized at 16:42 on 14 June 2026.",
    )
    panel_scored = {
        ("L2-15", "Load"), ("L2-15", "Branch"), ("L2-15", "Record"),
        ("L2-17", "Load"), ("L2-17", "Branch"), ("L2-17", "Record"),
        ("L2-19", "Load"), ("L2-19", "Branch"), ("L2-19", "Record"),
        ("L2-21", "Load"), ("L2-21", "Branch"), ("L2-21", "Record"),
    }
    case.add_region(
        "p07.panel",
        "Panel LP-2 branch schedule",
        "table",
        table_leaves("p07.panel", panel_headers, panel_rows, consequential={("L2-15", "Record"), ("L2-17", "Branch")}, scored_bindings=panel_scored),
        budget=2,
        closed_world=True,
    )
    checklist_leaves = [
        form_state_leaf("p07.check.torque", "Torque witness marks complete is checked.", "Torque witness marks complete", "checked"),
        form_state_leaf("p07.check.l215", "L2-15 field tag installed is checked.", "L2-15 field tag installed", "checked", harm=2),
        form_state_leaf("p07.check.l217", "L2-17 field tag installed is checked.", "L2-17 field tag installed", "checked"),
        form_state_leaf("p07.check.l219", "L2-19 field tag installed is checked.", "L2-19 field tag installed", "checked"),
        form_state_leaf("p07.check.l221", "L2-21 released for use is unchecked.", "L2-21 released for use", "unchecked", harm=2),
        form_state_leaf("p07.check.transfer", "Emergency transfer witnessed is checked.", "Emergency transfer witnessed", "checked", harm=2),
        form_state_leaf("p07.check.polarity", "Reader polarity exception open is crossed out.", "Reader polarity exception open", "crossed", harm=2),
    ]
    case.add_region(
        "p07.walkdown",
        "Scanned electrical walkdown states",
        "form",
        checklist_leaves,
        budget=3,
        closed_world=True,
        text_only_recoverable=False,
    )
    case.add_region(
        "p07.walkdown-identity",
        "Scanned field-record identity",
        "form",
        [
            leaf("p07.identity.record", "The field-check record is EC-214-19.", evidence=["EC-214-19"]),
            leaf("p07.identity.date", "The walkdown date is 2026-06-14.", evidence=[["14 JUN 2026", "14 June 2026"]]),
            leaf("p07.identity.tech", "The technician initials are JH.", evidence=["JH", "Technician"]),
            leaf("p07.identity.witness", "The witness initials are LS.", evidence=["LS", "Witness"]),
            leaf("p07.identity.time", "Panel energization was recorded at 16:42.", evidence=["16:42", "energized"]),
        ],
        budget=1,
        text_only_recoverable=False,
    )

    # Page 8 - full-page scan of field RFI and redline; no native recovery.
    c = case.new_page(
        "RFI-214-17 - Lab B corridor opening",
        subtitle="Field response and marked plan excerpt",
        section_code="ANSWERED / REV A",
    )
    c.setFillColor(HexColor("#F7F4EB"))
    c.setStrokeColor(HexColor("#8D8A82"))
    c.roundRect(42, 424, 520, 228, 3, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont("DocSans-Bold", 8.5)
    c.drawString(58, 625, "FIELD QUERY / RECEIVED 09 JUN 2026")
    draw_paragraph(c, "Revision B opening conflicts with the installed security rough-in. Confirm governing opening, swing, reader jamb, controller branch, and whether the old field background may be used for set-out.", 58, 600, 470, size=8, leading=11)
    draw_checkbox(c, 60, 500, "unchecked", "Maintain D-214A at Revision B position")
    draw_checkbox(c, 60, 474, "checked", "Issue architect response for construction")
    c.setFillColor(HexColor("#FFF8F5"))
    c.setStrokeColor(RED)
    c.roundRect(42, 154, 300, 238, 3, fill=1, stroke=1)
    c.setFillColor(RED)
    c.setFont("DocSans-Bold", 8.5)
    c.drawString(58, 366, "ARCHITECT RESPONSE / AV / 12 JUN")
    response_lines = [
        "VOID D-214A SET-OUT.",
        "Shift opening 4'-6\" west.",
        "Use D-214B; swing south into C2.",
        "Set CR-6 on corridor-side east jamb.",
        "DC-6 branch is LP-2 / L2-15.",
        "Revision C governs construction.",
    ]
    y = 335
    for line in response_lines:
        c.setFont("DocSans-Italic", 8.2)
        c.drawString(62, y, line)
        y -= 26
    # Redline sketch intentionally contains geometry not captured by the text
    # alone: old/new relative positions and the keyed reader side.
    sx, sy = 370, 176
    c.setStrokeColor(INK)
    c.setLineWidth(2)
    c.rect(sx, sy, 170, 180, fill=0, stroke=1)
    c.setFont("DocSans-Bold", 6)
    c.setFillColor(INK)
    c.drawCentredString(sx + 85, sy + 136, "215 LAB B")
    c.drawCentredString(sx + 85, sy + 38, "C2 CORRIDOR")
    _door(c, sx + 104, sy + 90, 28, swing_up=True, color=RED, dashed=True)
    _door(c, sx + 50, sy + 90, 28, swing_up=False, color=BLUE)
    c.setFillColor(HexColor("#FFF3EA"))
    c.setStrokeColor(RED)
    c.rect(sx + 82, sy + 76, 6, 9, fill=1, stroke=1)
    _dimension(c, sx + 50, sy + 116, sx + 104, sy + 116, "4'-6\"", color=RED)
    _bubble(c, sx + 94, sy + 70, "6")
    c.setStrokeColor(RED)
    c.setLineWidth(3)
    c.line(57, 510, 310, 505)
    c.setFont("DocSans-Bold", 11)
    c.drawString(300, 515, "VOID")
    c.setFont("DocSans", 6.2)
    c.setFillColor(MUTED)
    c.drawString(42, 105, "Architect AV signed 12 JUN 2026     Security TN reviewed     Contractor RK acknowledged 13 JUN 2026")
    case.add_gold(
        "RFI-214-17 - Lab B corridor opening",
        "The field query was received on 2026-06-09. Maintain D-214A at Revision B position is unchecked, crossed by a red strike, and marked VOID. Issue architect response for construction is checked. The answered RFI voids D-214A and makes D-214B the controlling identifier. Architect AV directs a new opening 4 ft 6 in west of the old opening, a south swing into C2, CR-6 on the corridor-side east jamb, and DC-6 on LP-2 circuit L2-15. Revision C governs construction. The redline sketch places Lab B above corridor C2 with the door wall between them, shows the dashed old and solid new positions, dimensions the new opening 4 ft 6 in west of the old opening, and keys reader callout 6 on the east jamb. AV signed 2026-06-12; TN reviewed; contractor RK acknowledged 2026-06-13.",
    )
    case.add_region(
        "p08.query-states",
        "Field-query option states",
        "form",
        [
            form_state_leaf("p08.query.maintain", "Maintain D-214A at Revision B position is unchecked.", "Maintain D-214A at Revision B position", "unchecked", harm=2),
            form_state_leaf("p08.query.response", "Issue architect response for construction is checked.", "Issue architect response for construction", "checked", harm=2),
            visual_leaf("p08.query.void", "The maintain-D-214A option is crossed by a red strike and marked VOID.", [["maintain D-214A"], ["strike", "crossed"], ["VOID"]], harm=2),
            leaf("p08.query.received", "The field query was received on 2026-06-09.", evidence=[["09 JUN 2026", "9 June 2026", "2026-06-09"]]),
        ],
        budget=2,
        closed_world=True,
        text_only_recoverable=False,
    )
    case.add_region(
        "p08.redline",
        "Door redline geometry",
        "diagram",
        [
            visual_leaf("p08.redline.old-new", "The redline shows a dashed old opening east of a solid new opening.", [["dashed", "old"], ["solid", "new"], ["east", "west"]], harm=2),
            visual_leaf("p08.redline.shift", "The new opening is dimensioned 4 ft 6 in west of the old opening.", [["4'-6\"", "4 ft 6"], ["new opening"], ["old opening"], ["west"]], harm=2),
            visual_leaf("p08.redline.swing", "The new door swings south into corridor C2.", [["new door", "D-214B"], ["south"], ["C2", "corridor"]], harm=2),
            visual_leaf("p08.redline.reader-position", "The reader is at the east jamb of the new opening.", [["reader", "CR-6"], ["east jamb"], ["new opening"]]),
            visual_leaf("p08.redline.reader-callout", "Callout 6 keys the reader.", [["callout 6", "6"], ["reader", "CR-6"]]),
            visual_leaf("p08.redline.wall", "The redline sketch places Lab B above corridor C2, separated by the door wall.", [["Lab B"], ["C2"], ["corridor"], ["above"], ["door wall"]]),
        ],
        budget=3,
        text_only_recoverable=False,
    )
    case.add_region(
        "p08.response",
        "Answered RFI authority and directives",
        "form",
        [
            source_precedence_leaf("p08.response.door", "The answered RFI voids D-214A and makes D-214B the controlling identifier.", [["answered RFI"], ["void", "voids"], ["D-214A"], ["D-214B"], ["controlling"]]),
            source_precedence_leaf("p08.response.shift", "The answered RFI controls a 4 ft 6 in westward shift.", [["answered RFI"], ["4'-6\"", "4 ft 6"], ["west"]]),
            source_precedence_leaf("p08.response.reader", "The answered RFI controls CR-6 on the corridor-side east jamb.", [["answered RFI"], ["CR-6"], ["corridor-side", "corridor side"], ["east jamb"]]),
            source_precedence_leaf("p08.response.circuit", "The answered RFI binds DC-6 to LP-2 circuit L2-15.", [["answered RFI"], ["DC-6"], ["LP-2"], ["L2-15"]]),
            source_precedence_leaf("p08.response.rev", "The architect response states that Revision C governs construction.", [["Revision C", "Rev C"], ["governs", "governing"], ["construction"]]),
            leaf("p08.response.signoff", "AV signed 2026-06-12; TN reviewed; RK acknowledged 2026-06-13.", evidence=["AV", "signed", ["12 JUN 2026", "2026-06-12"], "TN", "RK", ["13 JUN 2026", "2026-06-13"]]),
        ],
        budget=3,
        primary_axis="source_precedence",
        secondary_axes=["form_state", "low_quality_scan"],
        text_only_recoverable=False,
    )

    # Page 9 - mixed native framing with two embedded annotated field photos.
    c = case.new_page(
        "PH-214 - Field photo and punch evidence",
        subtitle="Photographs retained at inspection resolution | annotation keys only",
        section_code="15 JUN / FIELD",
        page_size=LANDSCAPE,
    )
    door_photo = _field_photo("door")
    rack_photo = _field_photo("rack")
    c.drawImage(image_reader(door_photo), 45, 230, width=340, height=275, preserveAspectRatio=True, mask="auto")
    c.drawImage(image_reader(rack_photo), 407, 230, width=340, height=275, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(HexColor("#7D8285"))
    c.rect(45, 230, 340, 275, fill=0, stroke=1)
    c.rect(407, 230, 340, 275, fill=0, stroke=1)
    c.setFillColor(INK)
    c.setFont("DocSans-Bold", 6.5)
    c.drawString(45, 212, "PHOTO 06 | CORRIDOR C2 | KEY A")
    c.drawString(407, 212, "PHOTO 09 | ROOM 218 | KEY B")
    photo_headers = ["Image", "Captured", "View", "Custodian", "Checksum"]
    photo_rows = [
        ["PHOTO 06", "15 Jun 09:16", "C2 south", "TN", "8F4C-06A2"],
        ["PHOTO 09", "15 Jun 09:42", "218 west", "TN", "1B77-09D5"],
    ]
    draw_table(c, 115, 170, [92, 110, 105, 86, 120], [photo_headers, *photo_rows], font_size=6.5, zebra=True)
    case.add_gold(
        "PH-214 - Field photo and punch evidence",
        "Photo 06 is a corridor-side view of D-214B. The reader is mounted on the image-right/east jamb, outside the Lab B opening; annotation A circles the reader rather than the opening. Photo 09 shows rack R2 in room 218. The overhead tray approaches from image-left/west and drops at the rack's west/top corner; annotation B circles that entry.\n\n"
        + markdown_table(photo_headers, photo_rows),
    )
    case.add_region(
        "p09.photo-door",
        "Door field-photo evidence",
        "image",
        [
            visual_leaf("p09.door.reader", "Photo 06 shows the reader on the image-right jamb of the doorway.", [["Photo 06"], ["reader"], ["image-right", "right jamb"]], harm=2),
            visual_leaf("p09.door.annotation", "Annotation A circles the reader rather than the opening.", [["annotation A", "A"], ["circles"], ["reader"], ["not", "rather than"]]),
        ],
        budget=3,
        text_only_recoverable=False,
    )
    case.add_region(
        "p09.photo-rack",
        "Rack field-photo evidence",
        "image",
        [
            visual_leaf("p09.rack.tray", "Photo 09 shows the overhead tray approaching rack R2 from image-left.", [["Photo 09"], ["tray"], ["rack", "R2"], ["image-left", "left"]], harm=2),
            visual_leaf(
                "p09.rack.drop",
                "The tray drops at the rack's west/top corner.",
                [["tray"], ["drop", "drops", "transition", "downward", "vertical"], ["image-upper-left", "image upper left", "upper-left", "upper left", "west/top", "west-top", "west", "top corner"]],
            ),
            visual_leaf("p09.rack.annotation", "Annotation B circles the tray-to-rack entry.", [["annotation B", "B"], ["tray"], ["rack"], ["entry"]]),
        ],
        budget=3,
        text_only_recoverable=False,
    )
    case.add_region(
        "p09.photo-index",
        "Field-photo chain of custody",
        "table",
        table_leaves(
            "p09.photo-index",
            photo_headers,
            photo_rows,
            consequential={("PHOTO 06", "Checksum")},
            scored_bindings={("PHOTO 06", "View"), ("PHOTO 06", "Checksum"), ("PHOTO 09", "View"), ("PHOTO 09", "Checksum")},
        ),
        budget=1,
        closed_world=True,
    )

    # Page 10 - mixed issue register plus embedded controlling release form.
    c = case.new_page(
        "CL-214 - Final issue and signoff record",
        subtitle="Distribution manifest with embedded release authority",
        section_code="RECORD CLOSEOUT",
    )
    issue_headers = ["Artifact", "Revision", "Digest", "Recipient", "Time"]
    issue_rows = [
        ["A2.14", "C", "2E11-A214", "Field / RK", "17:22"],
        ["A6.24", "C", "9A40-A624", "MEP / JH", "17:22"],
        ["T4.08", "C", "B817-T408", "Security / TN", "17:23"],
        ["N1.07", "C", "0C31-N107", "IT / SM", "17:23"],
        ["E6.02", "C", "7D14-E602", "Electrical / JH", "17:24"],
        ["RFI-214-17", "A", "6F82-R214", "Record / LS", "17:24"],
    ]
    draw_table(c, 42, 660, [102, 62, 106, 150, 70], [issue_headers, *issue_rows], font_size=6.7, zebra=True)
    draw_label(c, "Embedded final release", 42, 388)
    release = _release_scan()
    c.drawImage(image_reader(release), 42, 72, width=520, height=296, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(HexColor("#94989A"))
    c.rect(42, 72, 520, 296, fill=0, stroke=1)
    case.add_gold(
        "CL-214 - Final issue and signoff record",
        markdown_table(issue_headers, issue_rows)
        + "\n\nThe release package is ARC-214-C. The embedded release form has IFC Revision C accepted checked, use archived Revision B background unchecked, RFI-214-17 incorporated checked, and open access-control punch items unchecked. Architect AV, Security TN, Electrical JH, and Owner LS sign the release. The release seal is 214-C-0616 and is dated 16 June 2026. Therefore Revision C controls, the archived plan cannot be used for set-out, the RFI directives are incorporated, and no access-control punch item remains open.",
    )
    issue_scored = {
        ("A2.14", "Revision"), ("A2.14", "Digest"),
        ("N1.07", "Revision"), ("E6.02", "Digest"),
    }
    case.add_region(
        "p10.issue",
        "Final distribution manifest",
        "table",
        table_leaves("p10.issue", issue_headers, issue_rows, scored_bindings=issue_scored),
        budget=1,
        closed_world=True,
    )
    case.add_region(
        "p10.release-states",
        "Embedded final-release states",
        "form",
        [
            form_state_leaf("p10.release.rev-c", "IFC Revision C accepted is checked.", "IFC Revision C accepted", "checked", harm=2),
            form_state_leaf("p10.release.rev-b", "Use archived Revision B background is unchecked.", "Use archived Revision B background", "unchecked", harm=2),
            form_state_leaf("p10.release.rfi", "RFI-214-17 incorporated is checked.", "RFI-214-17 incorporated", "checked", harm=2),
            form_state_leaf("p10.release.punch", "Open access-control punch items is unchecked.", "Open access-control punch items", "unchecked", harm=2),
        ],
        budget=3,
        closed_world=True,
        text_only_recoverable=False,
    )
    case.add_region(
        "p10.release-identity",
        "Final-release identity and signatories",
        "form",
        [
            leaf("p10.identity.package", "The release package is ARC-214-C.", evidence=["ARC-214-C"]),
            leaf("p10.identity.date", "The release date is 16 June 2026 (2026-06-16).", evidence=[["16 JUN 2026", "16 June 2026"]]),
            leaf("p10.identity.seal", "The release seal is 214-C-0616.", evidence=["214-C-0616"]),
            leaf("p10.identity.signers", "The release names AV, TN, JH, and LS as signatories.", evidence=["AV", "TN", "JH", "LS"]),
        ],
        budget=1,
        text_only_recoverable=False,
    )
    record = case.finish()
    rasterize_pdf_pages(
        case.pdf_path,
        case.pdf_path,
        {
            2: ScanProfile(seed=1502, color_mode="grayscale", dpi=144, skew_degrees=-0.14, noise_level=1.15, blur_radius=0.18, jpeg_quality=90, contrast=1.04),
            8: ScanProfile(seed=1508, color_mode="color", dpi=138, skew_degrees=0.22, noise_level=1.85, blur_radius=0.25, jpeg_quality=86, contrast=1.05),
        },
        metadata={
            "Creator": "Orion Biologics document control imaging",
            "Producer": "Enterprise Document Services",
        },
    )
    return record
