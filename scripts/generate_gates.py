from __future__ import annotations

import json
import shutil
import subprocess
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import black, white
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = ROOT / "benchmark"
CASE_ROOT = BENCHMARK_ROOT / "cases"
GATE_ROOT = ROOT / "benchmark" / "gates"
PAGE_W, PAGE_H = letter


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = []
    if bold:
        names += [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
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


F_TITLE = font(34, True)
F_H2 = font(24, True)
F_BODY = font(20)
F_SMALL = font(16)


def draw_image_text(lines: list[str], *, title: str | None = None, width: int = 1600, height: int = 2100) -> Image.Image:
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    y = 95
    if title:
        d.text((110, y), title, fill="#111827", font=F_TITLE)
        d.line((110, y + 52, width - 110, y + 52), fill="#9ca3af", width=2)
        y += 95
    for line in lines:
        if line.startswith("## "):
            y += 18
            d.text((110, y), line[3:], fill="#111827", font=F_H2)
            y += 46
        elif line == "":
            y += 24
        else:
            d.text((110, y), line, fill="#111827", font=F_BODY)
            y += 34
    return img


def draw_office_collision_image() -> Image.Image:
    img = Image.new("RGB", (1600, 2100), "#ffffff")
    d = ImageDraw.Draw(img)
    d.text((95, 88), "Quarterly Packaging Transfer - Slide Export", fill="#111827", font=F_TITLE)
    d.text((95, 150), "Prepared for the Fremont ops review", fill="#4b5563", font=F_BODY)
    d.line((95, 200, 1505, 200), fill="#9ca3af", width=2)

    d.text((95, 245), "Timeline", fill="#111827", font=F_H2)
    d.line((150, 360, 1410, 360), fill="#374151", width=4)
    quarters = [("Q1", 210), ("Q2", 510), ("Q3", 810), ("Q4", 1110)]
    for label, x in quarters:
        d.line((x, 330, x, 390), fill="#374151", width=2)
        d.text((x - 22, 300), label, fill="#111827", font=F_SMALL)

    items = [
        ("Line validation", 170, 510, 430, "#2563eb"),
        ("Carton artwork lock", 430, 760, 515, "#0f766e"),
        ("Retail pilot", 700, 1040, 600, "#d97706"),
        ("Cutover window", 1000, 1350, 685, "#b91c1c"),
    ]
    for label, x1, x2, y, color in items:
        d.rounded_rectangle((x1, y, x2, y + 56), radius=15, fill=color)
        d.text((x1 + 18, y + 14), label, fill="white", font=F_SMALL)

    # Intentional realistic export defects: duplicate labels, shifted text boxes,
    # and a legend that drifted into the plot area. These are visible, not hidden.
    d.text((745, 514), "Carton artwork lock", fill="#064e3b", font=F_SMALL)
    d.text((1045, 606), "Retail pilot", fill="#92400e", font=F_SMALL)
    d.rectangle((1115, 250, 1505, 342), outline="#d1d5db", width=2)
    d.text((1135, 268), "Legend: blue=validation", fill="#111827", font=F_SMALL)
    d.text((1135, 296), "green=approval; red=cutover", fill="#111827", font=F_SMALL)

    d.text((95, 790), "Risks and decisions", fill="#111827", font=F_H2)
    rows = [
        ("R-12", "Foil pouch supplier slips by 2 weeks", "Escalate to dual-source plan"),
        ("R-18", "Line 4 reject rate above 1.5%", "Hold cutover until FAT retest"),
        ("D-07", "Use amber cartons for pilot only", "Approved by Mira on 2026-07-02"),
    ]
    y = 855
    widths = [130, 560, 620]
    headers = ["ID", "Issue", "Decision"]
    x = 95
    for h, w in zip(headers, widths):
        d.text((x, y), h, fill="#111827", font=F_SMALL)
        x += w
    d.line((95, y + 28, 1405, y + 28), fill="#111827", width=2)
    y += 48
    for row in rows:
        x = 95
        for cell, w in zip(row, widths):
            d.text((x, y), cell, fill="#111827", font=F_SMALL)
            x += w
        y += 46

    d.text((95, 1098), "Reviewer notes", fill="#111827", font=F_H2)
    d.text((95, 1155), "The Q3 pilot label was shifted during Google Slides import.", fill="#111827", font=F_BODY)
    d.text((95, 1192), "Do not treat the duplicate floating label as a separate milestone.", fill="#111827", font=F_BODY)
    d.text((95, 1229), "Final cutover remains gated by FAT retest for Line 4.", fill="#111827", font=F_BODY)
    return img


def add_png_page(c: canvas.Canvas, img: Image.Image) -> None:
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    c.drawImage(ImageReader(buffer), 0, 0, width=PAGE_W, height=PAGE_H)
    c.showPage()


def write_text_pdf(path: Path, lines: list[str]) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    y = 720
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, y, lines[0])
    y -= 36
    c.setFont("Helvetica", 11)
    for line in lines[1:]:
        if line == "":
            y -= 14
        else:
            c.drawString(72, y, line)
            y -= 17
    c.save()


def write_blank_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    c.showPage()
    c.save()


def write_hidden_text_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    c.setFillColor(white)
    c.setFont("Helvetica", 12)
    c.drawString(72, 720, "TEXT_LAYER_PROBE_7F3A: The shipment hold code is QX-914.")
    c.drawString(72, 700, "The visible page is intentionally blank.")
    c.showPage()
    c.save()


def write_raster_text_pdf(path: Path) -> None:
    lines = [
        "Scanned Receiving Note",
        "Document: RN-4481",
        "Dock: North 3",
        "Carrier: Velox Freight",
        "Seal: VX-39022",
        "",
        "Line  Item              Qty  Condition",
        "1     Sterile wraps     24   accepted",
        "2     Nitrile gloves    18   one carton crushed",
        "3     Label rolls       9    accepted",
        "",
        "Handwritten note: hold line 2 for supervisor review.",
    ]
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    add_png_page(c, draw_image_text(lines))
    c.save()


def write_mixed_conflict_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    c.setFillColor(white)
    c.setFont("Helvetica", 10)
    c.drawString(72, 730, "STALE_TEXT_LAYER: Release status APPROVED. Owner: Hana Park. Ship date: 2026-08-04.")
    img = draw_image_text(
        [
            "Final Release Exception Card",
            "Release: RL-884",
            "Visible status: BLOCKED",
            "Owner: Nisha Vora",
            "Ship date: 2026-08-11",
            "Reason: EU tenant security signoff missing.",
            "Visible stamp: HOLD UNTIL SIGNOFF",
        ]
    )
    add_png_page(c, img)
    c.save()


def write_covered_text_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    c.setFillColor(black)
    c.setFont("Helvetica", 12)
    c.drawString(72, 710, "Old value: Batch B-771 potency 98.6%, disposition RELEASE.")
    c.setFillColor(white)
    c.rect(50, 650, 520, 110, stroke=0, fill=1)
    img = draw_image_text(
        [
            "Visible Correction Notice",
            "Batch: B-771",
            "Corrected potency: 92.4%",
            "Disposition: HOLD",
            "Reason: second assay failed precision check.",
        ],
        width=1200,
        height=500,
    )
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    c.drawImage(ImageReader(buffer), 62, 560, width=488, height=203)
    c.showPage()
    c.save()


def write_office_collision_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    add_png_page(c, draw_office_collision_image())
    c.save()


def write_rotated_skewed_scan_pdf(path: Path) -> None:
    img = draw_image_text(
        [
            "Field Calibration Sheet",
            "Meter: FM-204",
            "Technician: Jules Park",
            "Temperature: 21.8 C",
            "Reading A: 4.98 mA",
            "Reading B: 12.06 mA",
            "Reading C: 19.94 mA",
            "Result: pass, no trim required",
        ],
        width=1400,
        height=1900,
    )
    img = img.rotate(-7, expand=True, fillcolor="white")
    canvas_img = Image.new("RGB", (1600, 2100), "white")
    canvas_img.paste(img, (35, 140))
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    add_png_page(c, canvas_img)
    c.save()


def write_bad_text_order_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    # Draw visible page in normal reading order as an image.
    img = draw_image_text(
        [
            "Clinic Referral Summary",
            "Patient: Mira Patel",
            "Referral ID: REF-7721",
            "",
            "## Assessment",
            "Primary concern: recurrent dizziness after medication change.",
            "Urgency: routine within 14 days.",
            "",
            "## Plan",
            "1. Schedule vestibular evaluation.",
            "2. Send current medication list.",
            "3. Call patient if symptoms worsen.",
        ]
    )
    add_png_page(c, img)
    c.save()

    # Overlay extractable text in intentionally bad order while preserving render.
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas as rl_canvas

    packet = BytesIO()
    overlay = rl_canvas.Canvas(packet, pagesize=letter, invariant=1)
    overlay.setFillColor(white)
    overlay.setFont("Helvetica", 9)
    for y, line in [
        (720, "3. Call patient if symptoms worsen."),
        (704, "Plan"),
        (688, "Patient: Mira Patel"),
        (672, "1. Schedule vestibular evaluation."),
        (656, "Clinic Referral Summary"),
        (640, "Urgency: routine within 14 days."),
        (624, "Referral ID: REF-7721"),
        (608, "Primary concern: recurrent dizziness after medication change."),
        (592, "2. Send current medication list."),
        (576, "Assessment"),
    ]:
        overlay.drawString(72, y, line)
    overlay.save()
    packet.seek(0)
    reader = PdfReader(str(path))
    overlay_reader = PdfReader(packet)
    page = reader.pages[0]
    page.merge_page(overlay_reader.pages[0])
    writer = PdfWriter()
    writer.add_page(page)
    with path.open("wb") as f:
        writer.write(f)


def write_font_encoding_corruption_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    c.setFillColor(white)
    c.setFont("Helvetica", 10)
    c.drawString(72, 735, "Copy paste corruption layer: Order 8l5O-OO1 amount S12,B4O status CI0SED")
    img = draw_image_text(
        [
            "Remittance Advice",
            "Order: 8150-001",
            "Amount: $12,840.00",
            "Status: CLOSED",
            "Bank reference: ACH-7742",
            "Note: zeros and letter O are visually distinct in the rendered document.",
        ]
    )
    add_png_page(c, img)
    c.save()


def write_form_state_pdf(path: Path) -> None:
    img = Image.new("RGB", (1600, 2100), "white")
    d = ImageDraw.Draw(img)
    d.text((100, 90), "Access Request Form", fill="#111827", font=F_TITLE)
    d.text((100, 160), "Request ID: AR-6021", fill="#111827", font=F_BODY)
    d.text((100, 198), "User: Daniel Kim", fill="#111827", font=F_BODY)
    states = [
        ("Production database", True),
        ("Billing export bucket", False),
        ("Break-glass admin", False),
    ]
    y = 280
    for label, checked in states:
        d.rectangle((110, y, 142, y + 32), outline="#111827", width=3)
        if checked:
            d.line((116, y + 17, 126, y + 28, 138, y + 6), fill="#0f766e", width=5)
        d.text((162, y - 2), label, fill="#111827", font=F_BODY)
        y += 58
    d.text((100, 500), "Duration", fill="#111827", font=F_H2)
    radios = [("24 hours", False), ("7 days", True), ("Permanent", False)]
    y = 560
    for label, checked in radios:
        d.ellipse((112, y, 142, y + 30), outline="#111827", width=3)
        if checked:
            d.ellipse((120, y + 8, 134, y + 22), fill="#111827")
        d.text((162, y - 2), label, fill="#111827", font=F_BODY)
        y += 52
    d.text((100, 760), "Approver note: remove billing bucket; production database only.", fill="#111827", font=F_BODY)
    d.line((165, 338, 405, 338), fill="#b91c1c", width=4)
    d.text((430, 324), "crossed out by approver", fill="#b91c1c", font=F_SMALL)
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    add_png_page(c, img)
    c.save()


def write_annotation_layer_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 720, "Contract Review Excerpt")
    c.setFont("Helvetica", 11)
    c.drawString(72, 680, "Section 4.2: Provider must notify Customer within 72 hours of a Security Incident.")
    c.drawString(72, 655, "Section 4.3: Audit requests require ten business days' notice.")
    c.setFillColorRGB(1, 0.95, 0.55)
    c.rect(360, 635, 170, 34, stroke=0, fill=1)
    c.setFillColor(black)
    c.drawString(368, 646, "Comment C1 here")
    try:
        c.textAnnotation("C1 Priya: change 72 hours to 48 hours before sending.", Rect=(360, 635, 540, 700))
    except Exception:
        pass
    c.showPage()
    c.save()


def write_crop_offcanvas_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 720, "Cropped Packing Slip")
    c.setFont("Helvetica", 11)
    c.drawString(72, 680, "Visible shipment: PK-5109")
    c.drawString(72, 660, "Visible destination: Reno DC")
    c.drawString(72, 640, "Visible cartons: 14")
    c.drawString(900, 640, "OFF-CANVAS TEXT: destination Phoenix DC, cartons 22")
    c.showPage()
    c.save()


def write_multiversion_packet_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    page1 = draw_image_text(
        [
            "Draft Change Order",
            "CO-1184",
            "Status: DRAFT",
            "Window: 2026-08-12 01:00-03:00",
            "Rollback owner: Alex Meyer",
            "Risk: medium",
        ]
    )
    page2 = draw_image_text(
        [
            "Signed Change Order",
            "CO-1184",
            "Status: APPROVED",
            "Window: 2026-08-13 02:00-04:00",
            "Rollback owner: Sana Rao",
            "Risk: high",
            "Signature: M. Chen, 2026-08-07",
        ]
    )
    page3 = draw_image_text(
        [
            "Post-Approval Correction",
            "CO-1184",
            "Correction: maintenance window remains 2026-08-13 02:00-04:00.",
            "Correction: rollback owner changed to Omar Nadir.",
            "Final status: APPROVED WITH OWNER CORRECTION",
        ]
    )
    for page in [page1, page2, page3]:
        add_png_page(c, page)
    c.save()


def write_spreadsheet_screenshot_pdf(path: Path) -> None:
    img = Image.new("RGB", (1600, 2100), "white")
    d = ImageDraw.Draw(img)
    d.text((90, 80), "Exported Spreadsheet Screenshot", fill="#111827", font=F_TITLE)
    d.text((90, 135), "Inventory Reconciliation - Week 31", fill="#4b5563", font=F_BODY)
    x0, y0 = 90, 230
    col_w = [120, 320, 150, 150, 180, 220]
    rows = [
        ["SKU", "Item", "On hand", "Counted", "Variance", "Action"],
        ["A-104", "Sterile pouch", "1240", "1236", "-4", "investigate"],
        ["B-220", "Nitrile glove", "890", "910", "+20", "adjust"],
        ["C-018", "Label roll", "412", "412", "0", "none"],
        ["D-771", "Foil carton", "78", "65", "-13", "hold pick"],
    ]
    y = y0
    for r, row in enumerate(rows):
        x = x0
        for cidx, cell in enumerate(row):
            if r == 0:
                d.rectangle((x, y, x + col_w[cidx], y + 42), fill="#e5e7eb", outline="#cbd5e1")
                fnt = F_SMALL
            else:
                if cidx == 4 and cell.startswith("-"):
                    d.rectangle((x, y, x + col_w[cidx], y + 42), fill="#fee2e2", outline="#e5e7eb")
                elif cidx == 4 and cell.startswith("+"):
                    d.rectangle((x, y, x + col_w[cidx], y + 42), fill="#dcfce7", outline="#e5e7eb")
                else:
                    d.rectangle((x, y, x + col_w[cidx], y + 42), fill="white", outline="#e5e7eb")
                fnt = F_SMALL
            d.text((x + 8, y + 10), cell, fill="#111827", font=fnt)
            x += col_w[cidx]
        y += 42
    d.text((90, 520), "Filter shown: variance != 0, but row C-018 remains visible from frozen subtotal band.", fill="#111827", font=F_SMALL)
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    add_png_page(c, img)
    c.save()


GATES = [
    {
        "id": "G01-blank-page",
        "title": "Blank Page Control",
        "capability": "input-control",
        "purpose": "A visually blank PDF with no text layer. The visible-document output should be empty or state that the page is blank.",
        "writer": write_blank_pdf,
        "expectedVisibleMarkdown": "",
        "expectedExtractedText": "",
    },
    {
        "id": "G02-hidden-text-layer",
        "title": "Hidden Text Layer Access",
        "capability": "pdf-text-layer",
        "purpose": "A visually blank PDF with white extractable text. It isolates provider/model access to non-visible PDF text.",
        "writer": write_hidden_text_pdf,
        "expectedVisibleMarkdown": "",
        "expectedExtractedText": "TEXT_LAYER_PROBE_7F3A: The shipment hold code is QX-914.",
    },
    {
        "id": "G03-born-digital-visible-text",
        "title": "Born-Digital Visible Text",
        "capability": "extractable-visible-text",
        "purpose": "A normal selectable-text PDF. It isolates basic born-digital reconstruction without raster OCR.",
        "writer": lambda path: write_text_pdf(
            path,
            [
                "Acme Service Bulletin SB-204",
                "Applies to units S4-20P and S4-40P shipped after 2026-06-01.",
                "Action: replace bracket B-7 only if vibration exceeds 2.1 mm/s.",
                "",
                "Unit | Reading | Action",
                "S4-20P | 1.8 mm/s | no action",
                "S4-40P | 2.4 mm/s | replace bracket B-7",
            ],
        ),
        "expectedVisibleMarkdown": "Acme Service Bulletin SB-204 with the unit/action table.",
        "expectedExtractedText": "Acme Service Bulletin SB-204",
    },
    {
        "id": "G04-raster-text-only",
        "title": "Raster Text Only",
        "capability": "visual-ocr",
        "purpose": "A scanned/image-only receiving note. It isolates whether the model can read visible raster text from the PDF.",
        "writer": write_raster_text_pdf,
        "expectedVisibleMarkdown": "Scanned Receiving Note RN-4481 with Dock North 3, carrier Velox Freight, seal VX-39022, and three line items.",
        "expectedExtractedText": "",
    },
    {
        "id": "G05-mixed-visible-vs-hidden-conflict",
        "title": "Mixed Visible Versus Hidden Conflict",
        "capability": "visible-state-precedence",
        "purpose": "A PDF with hidden stale text and visible raster final values. It separates text-layer access from visible-state discipline.",
        "writer": write_mixed_conflict_pdf,
        "expectedVisibleMarkdown": "Release RL-884 is BLOCKED, owner Nisha Vora, ship date 2026-08-11, hold until signoff.",
        "expectedExtractedText": "STALE_TEXT_LAYER: Release status APPROVED.",
    },
    {
        "id": "G06-covered-stale-text",
        "title": "Covered Stale Text",
        "capability": "covered-text-precedence",
        "purpose": "A visible correction card covers old extractable text. It tests whether rendered visible content wins.",
        "writer": write_covered_text_pdf,
        "expectedVisibleMarkdown": "Batch B-771 corrected potency 92.4%, disposition HOLD, second assay failed precision check.",
        "expectedExtractedText": "Old value: Batch B-771 potency 98.6%, disposition RELEASE.",
    },
    {
        "id": "G07-office-conversion-layout-drift",
        "title": "Office Conversion Layout Drift",
        "capability": "layout-salvage",
        "purpose": "A realistic image-only slide export with shifted duplicate labels and sparse table rules. It probes layout cleanup without hidden text.",
        "writer": write_office_collision_pdf,
        "expectedVisibleMarkdown": "Quarterly Packaging Transfer slide with four timeline bars, three risk/decision rows, and reviewer notes that duplicate floating labels are not separate milestones.",
        "expectedExtractedText": "",
    },
    {
        "id": "G11-rotated-skewed-scan",
        "title": "Rotated Skewed Scan",
        "capability": "scan-orientation-ocr",
        "purpose": "A slightly rotated scanned calibration sheet. It tests whether the model can recover visible raster text despite scan skew.",
        "writer": write_rotated_skewed_scan_pdf,
        "expectedVisibleMarkdown": "Field Calibration Sheet for meter FM-204, technician Jules Park, temperature 21.8 C, readings 4.98 mA, 12.06 mA, 19.94 mA, result pass no trim required.",
        "expectedExtractedText": "",
    },
    {
        "id": "G12-bad-text-layer-order",
        "title": "Bad Text Layer Order",
        "capability": "visual-reading-order-over-text-layer",
        "purpose": "The visible page reads normally, but the hidden extractable text layer is intentionally out of order. The model should follow visible reading order.",
        "writer": write_bad_text_order_pdf,
        "expectedVisibleMarkdown": "Clinic Referral Summary for Mira Patel, REF-7721, assessment before plan, with the three plan steps in order.",
        "expectedExtractedText": "Extractable text layer is present but intentionally scrambled.",
    },
    {
        "id": "G13-font-encoding-corruption",
        "title": "Font Encoding Copy Paste Corruption",
        "capability": "visual-text-over-corrupt-text-layer",
        "purpose": "The visible PDF text is correct but the hidden text layer contains copy-paste-like character corruption. The model should preserve visible rendered values.",
        "writer": write_font_encoding_corruption_pdf,
        "expectedVisibleMarkdown": "Remittance Advice with order 8150-001, amount $12,840.00, status CLOSED, bank reference ACH-7742.",
        "expectedExtractedText": "Copy paste corruption layer: Order 8l5O-OO1 amount S12,B4O status CI0SED",
    },
    {
        "id": "G14-form-state-only",
        "title": "Form State Only",
        "capability": "form-state",
        "purpose": "A raster access request form isolating checked, unchecked, radio, and crossed-out states.",
        "writer": write_form_state_pdf,
        "expectedVisibleMarkdown": "Access Request Form AR-6021 for Daniel Kim: production database checked, billing export bucket crossed out/removed, break-glass admin unchecked, duration 7 days selected, approver note production database only.",
        "expectedExtractedText": "",
    },
    {
        "id": "G15-annotation-comment-layer",
        "title": "Annotation Comment Layer",
        "capability": "pdf-annotation-handling",
        "purpose": "A contract excerpt with a visible comment marker and a PDF text annotation. It tests whether annotations/comments are preserved when available.",
        "writer": write_annotation_layer_pdf,
        "expectedVisibleMarkdown": "Contract Review Excerpt with Section 4.2 notification within 72 hours, Section 4.3 ten business days notice, visible Comment C1 marker, and annotation C1 Priya requesting 72 hours change to 48 hours.",
        "expectedExtractedText": "PDF annotation may not appear in pdftotext.",
    },
    {
        "id": "G16-crop-offcanvas-text",
        "title": "Crop And Off Canvas Text",
        "capability": "visible-crop-precedence",
        "purpose": "A PDF contains visible packing-slip text and off-canvas extractable text outside the visible page area. The model should reconstruct only visible content.",
        "writer": write_crop_offcanvas_pdf,
        "expectedVisibleMarkdown": "Cropped Packing Slip with visible shipment PK-5109, destination Reno DC, cartons 14. Off-canvas Phoenix DC/cartons 22 must not be treated as visible content.",
        "expectedExtractedText": "OFF-CANVAS TEXT: destination Phoenix DC, cartons 22",
    },
    {
        "id": "G17-multiversion-packet",
        "title": "Multi Version Packet",
        "capability": "document-state-across-pages",
        "purpose": "A three-page packet with draft, signed, and post-approval correction states. It tests document-state preservation and final-value binding.",
        "writer": write_multiversion_packet_pdf,
        "expectedVisibleMarkdown": "CO-1184 packet preserving draft, signed, and correction pages; final status approved with owner correction, final window 2026-08-13 02:00-04:00, final rollback owner Omar Nadir.",
        "expectedExtractedText": "",
    },
    {
        "id": "G18-spreadsheet-screenshot",
        "title": "Spreadsheet Screenshot Table",
        "capability": "spreadsheet-screenshot-table",
        "purpose": "A spreadsheet screenshot with table cells, sign/color semantics, and a filter note. It isolates raster spreadsheet table extraction.",
        "writer": write_spreadsheet_screenshot_pdf,
        "expectedVisibleMarkdown": "Inventory Reconciliation Week 31 table with A-104 -4 investigate, B-220 +20 adjust, C-018 0 none, D-771 -13 hold pick, and filter note that C-018 remains visible from frozen subtotal band.",
        "expectedExtractedText": "",
    },
]


def visible_facts(gate: dict) -> list[dict]:
    gate_id = gate["id"].lower()
    capability = gate["capability"]
    if gate["id"] == "G01-blank-page":
        return [
            {
                "id": f"{gate_id}.blank",
                "category": "blank_control",
                "weight": 3,
                "severity": "critical",
                "modality": capability,
                "expectation": "The PDF page has no visible content and no extractable text. A faithful visible-document reconstruction should be empty or state that the page is blank, without inventing document facts.",
            }
        ]
    if gate["id"] == "G02-hidden-text-layer":
        return [
            {
                "id": f"{gate_id}.visible_blank",
                "category": "visible_state",
                "weight": 4,
                "severity": "critical",
                "modality": capability,
                "expectation": "The page is visually blank. For visible-document reconstruction, the hidden white text-layer probe must not be treated as visible document content.",
            },
            {
                "id": f"{gate_id}.forbidden_probe",
                "category": "forbidden_text",
                "weight": 4,
                "severity": "critical",
                "modality": capability,
                "expectation": "The output must not include TEXT_LAYER_PROBE_7F3A, QX-914, or the hidden statement that the visible page is intentionally blank.",
            },
        ]
    if gate["id"] == "G03-born-digital-visible-text":
        return [
            {
                "id": f"{gate_id}.bulletin",
                "category": "extractable_text",
                "weight": 3,
                "severity": "major",
                "modality": capability,
                "expectation": "The output preserves Acme Service Bulletin SB-204, the applicable units S4-20P and S4-40P, the 2026-06-01 shipment condition, and the 2.1 mm/s threshold.",
            },
            {
                "id": f"{gate_id}.unit_table",
                "category": "table_cell",
                "weight": 4,
                "severity": "critical",
                "modality": capability,
                "expectation": "The unit/action table preserves S4-20P as 1.8 mm/s with no action and S4-40P as 2.4 mm/s with replace bracket B-7.",
            },
        ]
    if gate["id"] == "G04-raster-text-only":
        return [
            {
                "id": f"{gate_id}.header",
                "category": "visual_ocr",
                "weight": 3,
                "severity": "major",
                "modality": capability,
                "expectation": "The output reads the raster-only receiving note: RN-4481, Dock North 3, Velox Freight, and seal VX-39022.",
            },
            {
                "id": f"{gate_id}.lines",
                "category": "table_cell",
                "weight": 5,
                "severity": "critical",
                "modality": capability,
                "expectation": "The raster line items are preserved: sterile wraps 24 accepted; nitrile gloves 18 one carton crushed; label rolls 9 accepted.",
            },
            {
                "id": f"{gate_id}.hold_note",
                "category": "visual_ocr",
                "weight": 3,
                "severity": "major",
                "modality": capability,
                "expectation": "The handwritten-style visible note says to hold line 2 for supervisor review.",
            },
        ]
    if gate["id"] == "G05-mixed-visible-vs-hidden-conflict":
        return [
            {
                "id": f"{gate_id}.visible_final",
                "category": "source_state",
                "weight": 6,
                "severity": "critical",
                "modality": capability,
                "expectation": "The visible final exception card is preserved: RL-884 is BLOCKED, owner Nisha Vora, ship date 2026-08-11, reason EU tenant security signoff missing, stamp HOLD UNTIL SIGNOFF.",
            },
            {
                "id": f"{gate_id}.forbidden_stale",
                "category": "forbidden_text",
                "weight": 6,
                "severity": "critical",
                "modality": capability,
                "expectation": "The hidden stale layer must not be presented as current visible content: APPROVED, Hana Park, and 2026-08-04 are wrong for the visible document.",
            },
        ]
    if gate["id"] == "G06-covered-stale-text":
        return [
            {
                "id": f"{gate_id}.visible_correction",
                "category": "source_state",
                "weight": 6,
                "severity": "critical",
                "modality": capability,
                "expectation": "The visible correction card is preserved: batch B-771 corrected potency 92.4%, disposition HOLD, reason second assay failed precision check.",
            },
            {
                "id": f"{gate_id}.forbidden_covered",
                "category": "forbidden_text",
                "weight": 6,
                "severity": "critical",
                "modality": capability,
                "expectation": "The covered stale text must not be presented as current visible content: potency 98.6% and disposition RELEASE are wrong for the visible document.",
            },
        ]
    if gate["id"] == "G11-rotated-skewed-scan":
        return [
            {
                "id": f"{gate_id}.calibration_fields",
                "category": "visual_ocr",
                "weight": 7,
                "severity": "critical",
                "modality": capability,
                "expectation": "The skewed scanned sheet is read correctly: Field Calibration Sheet, meter FM-204, technician Jules Park, temperature 21.8 C, readings 4.98 mA, 12.06 mA, and 19.94 mA.",
            },
            {
                "id": f"{gate_id}.result",
                "category": "visual_ocr",
                "weight": 3,
                "severity": "major",
                "modality": capability,
                "expectation": "The result is preserved as pass, no trim required.",
            },
        ]
    if gate["id"] == "G12-bad-text-layer-order":
        return [
            {
                "id": f"{gate_id}.visible_order",
                "category": "reading_order",
                "weight": 6,
                "severity": "critical",
                "modality": capability,
                "expectation": "The output follows visible reading order: Clinic Referral Summary, patient Mira Patel, REF-7721, Assessment section, then Plan section.",
            },
            {
                "id": f"{gate_id}.plan_steps",
                "category": "reading_order",
                "weight": 4,
                "severity": "critical",
                "modality": capability,
                "expectation": "The plan steps are preserved in order: schedule vestibular evaluation; send current medication list; call patient if symptoms worsen.",
            },
        ]
    if gate["id"] == "G13-font-encoding-corruption":
        return [
            {
                "id": f"{gate_id}.visible_values",
                "category": "source_state",
                "weight": 7,
                "severity": "critical",
                "modality": capability,
                "expectation": "The visible rendered values are preserved: order 8150-001, amount $12,840.00, status CLOSED, bank reference ACH-7742.",
            },
            {
                "id": f"{gate_id}.corrupt_layer_not_used",
                "category": "forbidden_text",
                "weight": 4,
                "severity": "critical",
                "modality": capability,
                "expectation": "The corrupt hidden/copy-paste text-layer variants are not used as final values: 8l5O-OO1, S12,B4O, and CI0SED are wrong.",
            },
        ]
    if gate["id"] == "G14-form-state-only":
        return [
            {
                "id": f"{gate_id}.checkboxes",
                "category": "form_state",
                "weight": 6,
                "severity": "critical",
                "modality": capability,
                "expectation": "The checkbox states are preserved: production database checked; billing export bucket is crossed out/removed by approver; break-glass admin unchecked.",
            },
            {
                "id": f"{gate_id}.radio_and_note",
                "category": "form_state",
                "weight": 5,
                "severity": "critical",
                "modality": capability,
                "expectation": "The radio duration state and approver note are preserved: 7 days selected; approver note says remove billing bucket and production database only.",
            },
        ]
    if gate["id"] == "G15-annotation-comment-layer":
        return [
            {
                "id": f"{gate_id}.contract_text",
                "category": "annotation",
                "weight": 4,
                "severity": "major",
                "modality": capability,
                "expectation": "The visible contract excerpt is preserved: Section 4.2 notification within 72 hours and Section 4.3 audit requests require ten business days notice.",
            },
            {
                "id": f"{gate_id}.comment",
                "category": "annotation",
                "weight": 6,
                "severity": "critical",
                "modality": capability,
                "expectation": "The visible Comment C1 marker and available PDF annotation are preserved: Priya requests changing 72 hours to 48 hours before sending.",
            },
        ]
    if gate["id"] == "G16-crop-offcanvas-text":
        return [
            {
                "id": f"{gate_id}.visible_slip",
                "category": "visible_crop",
                "weight": 6,
                "severity": "critical",
                "modality": capability,
                "expectation": "The visible packing slip values are preserved: PK-5109, destination Reno DC, cartons 14.",
            },
            {
                "id": f"{gate_id}.offcanvas_ignored",
                "category": "forbidden_text",
                "weight": 5,
                "severity": "critical",
                "modality": capability,
                "expectation": "The off-canvas text outside the visible page area is not treated as visible content: Phoenix DC and cartons 22 are wrong for visible reconstruction.",
            },
        ]
    if gate["id"] == "G17-multiversion-packet":
        return [
            {
                "id": f"{gate_id}.all_versions",
                "category": "document_state",
                "weight": 5,
                "severity": "critical",
                "modality": capability,
                "expectation": "The output preserves the draft page, signed page, and post-approval correction page as distinct document states for CO-1184.",
            },
            {
                "id": f"{gate_id}.final_state",
                "category": "document_state",
                "weight": 7,
                "severity": "critical",
                "modality": capability,
                "expectation": "The final state is correctly bound: approved with owner correction, window 2026-08-13 02:00-04:00, final rollback owner Omar Nadir.",
            },
        ]
    if gate["id"] == "G18-spreadsheet-screenshot":
        return [
            {
                "id": f"{gate_id}.spreadsheet_rows",
                "category": "table_cell",
                "weight": 8,
                "severity": "critical",
                "modality": capability,
                "expectation": "The spreadsheet screenshot table preserves rows and actions: A-104 sterile pouch 1240/1236 variance -4 investigate; B-220 nitrile glove 890/910 +20 adjust; C-018 label roll 412/412 0 none; D-771 foil carton 78/65 -13 hold pick.",
            },
            {
                "id": f"{gate_id}.filter_note",
                "category": "table_cell",
                "weight": 3,
                "severity": "major",
                "modality": capability,
                "expectation": "The filter note is preserved: variance != 0 is shown, but C-018 remains visible from frozen subtotal band.",
            },
        ]
    return [
        {
            "id": f"{gate_id}.timeline",
            "category": "layout_salvage",
            "weight": 5,
            "severity": "critical",
            "modality": capability,
            "expectation": "The timeline is reconstructed with four actual bars: Line validation, Carton artwork lock, Retail pilot, and Cutover window. Duplicate shifted labels are not extra milestones.",
        },
        {
            "id": f"{gate_id}.risk_table",
            "category": "table_cell",
            "weight": 5,
            "severity": "critical",
            "modality": capability,
            "expectation": "The risks and decisions table preserves R-12 foil pouch supplier slip escalated to dual-source plan, R-18 Line 4 reject rate above 1.5% held until FAT retest, and D-07 amber cartons for pilot approved by Mira on 2026-07-02.",
        },
        {
            "id": f"{gate_id}.reviewer_notes",
            "category": "layout_salvage",
            "weight": 3,
            "severity": "major",
            "modality": capability,
            "expectation": "The reviewer notes are preserved: the Q3 pilot label shifted during Google Slides import; the duplicate floating label is not a separate milestone; final cutover remains gated by FAT retest for Line 4.",
        },
    ]


def deterministic_checks(gate: dict) -> list[dict]:
    if gate["id"] == "G01-blank-page":
        return [
            {
                "id": "g01-no-invention",
                "category": "blank_control",
                "weight": 1,
                "description": "No substantive invented content appears for a blank page.",
                "none": ["shipment", "release", "invoice", "table", "QX-914", "TEXT_LAYER_PROBE"],
            }
        ]
    if gate["id"] == "G02-hidden-text-layer":
        return [
            {
                "id": "g02-no-hidden-probe",
                "category": "visible_state",
                "weight": 2,
                "description": "Hidden white text-layer probe is not emitted as visible content.",
                "none": ["TEXT_LAYER_PROBE_7F3A", "QX-914", "intentionally blank"],
            }
        ]
    if gate["id"] == "G05-mixed-visible-vs-hidden-conflict":
        return [
            {
                "id": "g05-visible-values",
                "category": "source_state",
                "weight": 2,
                "description": "Visible final release values are present.",
                "all": ["RL-884", "BLOCKED", "Nisha Vora", "2026-08-11"],
            },
            {
                "id": "g05-no-stale-values",
                "category": "source_state",
                "weight": 3,
                "description": "Hidden stale release values are not treated as current.",
                "none": ["APPROVED", "Hana Park", "2026-08-04"],
            },
        ]
    if gate["id"] == "G06-covered-stale-text":
        return [
            {
                "id": "g06-visible-correction",
                "category": "source_state",
                "weight": 2,
                "description": "Visible correction values are present.",
                "all": ["B-771", "92.4", "HOLD"],
            },
            {
                "id": "g06-no-covered-values",
                "category": "source_state",
                "weight": 3,
                "description": "Covered stale values are not treated as current.",
                "none": ["98.6", "RELEASE"],
            },
        ]
    return []


def pdftotext(path: Path) -> str:
    try:
        result = subprocess.run(["pdftotext", "-layout", str(path), "-"], check=True, capture_output=True, text=True)
        return result.stdout.replace("\f", "").strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def main() -> None:
    if GATE_ROOT.exists():
        shutil.rmtree(GATE_ROOT)
    GATE_ROOT.mkdir(parents=True)

    manifest_cases = []
    main_manifest_path = BENCHMARK_ROOT / "manifest.json"
    main_manifest = json.loads(main_manifest_path.read_text(encoding="utf-8")) if main_manifest_path.exists() else {"cases": []}
    existing_non_gate_cases = [case for case in main_manifest.get("cases", []) if not str(case.get("id", "")).startswith("G")]

    for gate in GATES:
        case_dir = GATE_ROOT / gate["id"]
        case_dir.mkdir(parents=True)
        pdf_path = case_dir / "source.pdf"
        gate["writer"](pdf_path)
        extracted = pdftotext(pdf_path)
        (case_dir / "pdftotext.txt").write_text(extracted + ("\n" if extracted else ""), encoding="utf-8")
        (case_dir / "expected.md").write_text(
            f"# {gate['title']}\n\n"
            f"Capability: {gate['capability']}\n\n"
            f"Visible-document expectation: {gate['expectedVisibleMarkdown'] or '(blank visible page)'}\n\n"
            f"Text-layer probe expectation: {gate['expectedExtractedText'] or '(no extractable text expected)'}\n",
            encoding="utf-8",
        )
        (case_dir / "probe.json").write_text(
            json.dumps(
                {
                    "id": gate["id"],
                    "title": gate["title"],
                    "capability": gate["capability"],
                    "purpose": gate["purpose"],
                    "expectedVisibleMarkdown": gate["expectedVisibleMarkdown"],
                    "expectedExtractedText": gate["expectedExtractedText"],
                    "observedPdftotext": extracted,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        scored_dir = CASE_ROOT / gate["id"]
        if scored_dir.exists():
            shutil.rmtree(scored_dir)
        scored_dir.mkdir(parents=True)
        shutil.copyfile(pdf_path, scored_dir / "source.pdf")

        facts = visible_facts(gate)
        checks = deterministic_checks(gate)
        tags = ["capability-gate", gate["capability"]]
        gold = (
            f"# {gate['title']}\n\n"
            f"Capability: {gate['capability']}\n\n"
            f"{gate['expectedVisibleMarkdown'] or 'The visible page is blank.'}\n"
        )
        spec = (
            f"# {gate['title']}\n\n"
            f"Purpose: {gate['purpose']}\n\n"
            f"Capability: {gate['capability']}\n\n"
            f"Visible-document expectation: {gate['expectedVisibleMarkdown'] or '(blank visible page)'}\n\n"
            f"Text-layer diagnostic expectation: {gate['expectedExtractedText'] or '(no extractable text expected)'}\n"
        )
        (scored_dir / "gold.md").write_text(gold, encoding="utf-8")
        (scored_dir / "spec.md").write_text(spec, encoding="utf-8")
        (scored_dir / "checks.json").write_text(
            json.dumps({"id": gate["id"], "title": gate["title"], "family": "capability-gate", "tags": tags, "checks": checks}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        (scored_dir / "facts.json").write_text(
            json.dumps({"id": gate["id"], "title": gate["title"], "family": "capability-gate", "tags": tags, "facts": facts}, indent=2)
            + "\n",
            encoding="utf-8",
        )

        manifest_cases.append(
            {
                "id": gate["id"],
                "title": gate["title"],
                "family": "capability-gate",
                "tags": tags,
                "pages": 1,
                "pdf": f"benchmark/cases/{gate['id']}/source.pdf",
                "gold": f"benchmark/cases/{gate['id']}/gold.md",
                "spec": f"benchmark/cases/{gate['id']}/spec.md",
                "checks": f"benchmark/cases/{gate['id']}/checks.json",
                "facts": f"benchmark/cases/{gate['id']}/facts.json",
                "capability": gate["capability"],
                "probe": f"benchmark/gates/{gate['id']}/probe.json",
                "expected": f"benchmark/gates/{gate['id']}/expected.md",
                "pdftotext": f"benchmark/gates/{gate['id']}/pdftotext.txt",
            }
        )

    manifest = {
        "name": "Doc2MD Capability Gates",
        "suite": "gates",
        "scoreName": "Doc2MD Capability Gate Diagnostics",
        "inputProtocol": "native_pdf",
        "scoredOfficially": False,
        "description": "Minimal PDF probes for isolating provider/model ingestion capabilities. These are diagnostics and are not part of the official Doc2MD score.",
        "caseCount": len(manifest_cases),
        "pageCount": len(manifest_cases),
        "cases": manifest_cases,
    }
    (GATE_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    updated_manifest = {
        **main_manifest,
        "caseCount": len(existing_non_gate_cases),
        "pageCount": sum(int(case.get("pages", 1)) for case in existing_non_gate_cases),
        "cases": existing_non_gate_cases,
    }
    main_manifest_path.write_text(json.dumps(updated_manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(manifest_cases)} gate probes to {GATE_ROOT}; official benchmark manifest remains depth-only")


if __name__ == "__main__":
    main()
