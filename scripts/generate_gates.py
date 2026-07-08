from __future__ import annotations

import json
import shutil
import subprocess
from io import BytesIO
from pathlib import Path
from textwrap import wrap
from typing import Callable

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import black, white
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = ROOT / "benchmark"
CASE_ROOT = BENCHMARK_ROOT / "cases"
GATE_ROOT = BENCHMARK_ROOT / "gates"
PAGE_W, PAGE_H = letter


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates += [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        ]
    candidates += [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


F_TITLE = font(34, True)
F_H2 = font(24, True)
F_BODY = font(20)
F_SMALL = font(16)


def draw_text_page(lines: list[str], *, title: str | None = None, width: int = 1600, height: int = 2100) -> Image.Image:
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


def draw_wrapped(d: ImageDraw.ImageDraw, x: int, y: int, text: str, *, width: int, leading: int = 28, fill: str = "#111827", font_obj=F_SMALL) -> int:
    for line in wrap(text, width=width):
        d.text((x, y), line, fill=fill, font=font_obj)
        y += leading
    return y


def add_png_page(c: canvas.Canvas, img: Image.Image) -> None:
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    c.drawImage(ImageReader(buffer), 0, 0, width=PAGE_W, height=PAGE_H)
    c.showPage()


def write_native_text_layer_gate(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    c.setFillColor(white)
    c.setFont("Helvetica", 12)
    c.drawString(72, 720, "TEXT_LAYER_PROBE_7F3A: The shipment hold code is QX-914.")
    c.drawString(72, 700, "Facility: Delta Cold Chain, Door 12.")
    c.drawString(72, 680, "Release instruction: keep pallet P-882 on hold until QA signs FORM-19.")
    img = Image.new("RGB", (1600, 2100), "white")
    d = ImageDraw.Draw(img)
    d.text((145, 150), "Delta Cold Chain - Exported Hold Notice", fill="#2f343b", font=F_TITLE)
    d.rectangle((140, 245, 1460, 760), fill="#e5e7eb")
    rows = [
        ("Shipment hold code", "QX-914"),
        ("Facility", "Delta Cold Chain"),
        ("Door", "12"),
        ("Pallet", "P-882"),
        ("Release condition", "QA signs FORM-19"),
    ]
    y = 305
    for label, value in rows:
        d.rectangle((180, y - 8, 1160, y + 34), outline="#9ca3af", width=1)
        d.text((200, y), label, fill="#30343a", font=F_SMALL)
        d.text((560, y + 9), value, fill="#30343a", font=F_SMALL)
        d.rectangle((520, y - 4, 1120, y + 16), fill="#d1d5db")
        y += 70
    d.text((145, 850), "The original export rendered with collapsed glyphs; operations kept this copy for recovery.", fill="#475569", font=F_BODY)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    c.drawImage(ImageReader(buffer), 0, 0, width=PAGE_W, height=PAGE_H)
    c.showPage()
    c.save()


def write_raster_visual_ocr_gate(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    add_png_page(
        c,
        draw_text_page(
            [
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
            ],
            title="Scanned Receiving Note",
        ),
    )
    c.save()


def write_layout_reconstruction_gate(path: Path) -> None:
    img = Image.new("RGB", (1600, 2100), "#ffffff")
    d = ImageDraw.Draw(img)
    d.text((95, 82), "Fremont Packaging Transfer - Ops Memo", fill="#111827", font=F_TITLE)
    d.text((95, 142), "Quarterly review extract | prepared 2026-07-06 | owner: Mira Chen", fill="#4b5563", font=F_BODY)
    d.line((95, 196, 1505, 196), fill="#9ca3af", width=2)
    d.text((95, 245), "Executive summary", fill="#111827", font=F_H2)
    left_lines = [
        "Line validation is complete for the foil pouch cell, but carton artwork remains under purchasing review.",
        "Retail pilot demand was higher than forecast in week 2. The Fremont team will keep amber cartons limited to the pilot channel until reject-rate data is final.",
        "The cutover window remains conditional because the Line 4 FAT retest must close before release engineering signs the weekend move order.",
    ]
    right_lines = [
        "The table below is the controlling risk register for the Wednesday review. Sidebar notes capture context from the import log and should remain near the transfer summary.",
        "A prior slide export shifted some timeline labels, but the operating plan itself is unchanged: validation, artwork lock, retail pilot, then cutover.",
        "Purchasing asked that supplier slips and reject-rate issues stay visible in the same memo excerpt as the decision rows.",
    ]
    y_left = 305
    for line in left_lines:
        y_left = draw_wrapped(d, 95, y_left, line, width=58)
        y_left += 26
    y_right = 305
    for line in right_lines:
        y_right = draw_wrapped(d, 835, y_right, line, width=55)
        y_right += 26
    d.rectangle((1040, 700, 1480, 930), outline="#9a3412", width=3)
    d.text((1062, 725), "Sidebar: import log", fill="#9a3412", font=F_H2)
    d.text((1062, 775), "Q3 pilot label shifted during", fill="#111827", font=F_SMALL)
    d.text((1062, 807), "Google Slides import.", fill="#111827", font=F_SMALL)
    d.text((1062, 850), "Actual timeline has four", fill="#111827", font=F_SMALL)
    d.text((1062, 882), "milestone bars, not six.", fill="#111827", font=F_SMALL)
    d.text((95, 710), "Transfer timeline", fill="#111827", font=F_H2)
    d.line((140, 805, 960, 805), fill="#374151", width=4)
    for label, x in [("Q1", 180), ("Q2", 380), ("Q3", 580), ("Q4", 780)]:
        d.line((x, 780, x, 830), fill="#374151", width=2)
        d.text((x - 16, 748), label, fill="#111827", font=F_SMALL)
    for label, x1, x2, y, color in [
        ("Line validation", 155, 365, 875, "#2563eb"),
        ("Carton artwork lock", 340, 548, 946, "#0f766e"),
        ("Retail pilot", 520, 742, 1017, "#d97706"),
        ("Cutover window", 715, 940, 1088, "#b91c1c"),
    ]:
        d.rounded_rectangle((x1, y, x2, y + 50), radius=12, fill=color)
        d.text((x1 + 14, y + 13), label, fill="white", font=F_SMALL)
    d.text((95, 1225), "Risks and decisions", fill="#111827", font=F_H2)
    rows = [
        ("ID", "Issue", "Decision", "Owner"),
        ("R-12", "Foil pouch supplier slips by 2 weeks", "Escalate to dual-source plan", "Iris"),
        ("R-18", "Line 4 reject rate above 1.5%", "Hold cutover until FAT retest", "Mateo"),
        ("D-07", "Use amber cartons for pilot only", "Approved by Mira on 2026-07-02", "Mira"),
    ]
    y = 1290
    widths = [105, 520, 520, 150]
    for idx, row in enumerate(rows):
        x = 95
        for cell, w in zip(row, widths):
            d.text((x, y), cell, fill="#111827", font=F_SMALL)
            x += w
        if idx == 0:
            d.line((95, y + 28, 1390, y + 28), fill="#111827", width=2)
        y += 48
    d.text((95, 1540), "Review closeout", fill="#111827", font=F_H2)
    d.text((95, 1595), "Final cutover remains gated by FAT retest for Line 4.", fill="#111827", font=F_BODY)
    d.text((95, 1632), "Purchasing must confirm dual-source pricing before amber carton pilot expansion.", fill="#111827", font=F_BODY)
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    add_png_page(c, img)
    c.save()


def write_visual_semantics_gate(path: Path) -> None:
    img = Image.new("RGB", (1600, 2100), "white")
    d = ImageDraw.Draw(img)
    d.text((100, 90), "Access Request Form", fill="#111827", font=F_TITLE)
    d.text((100, 160), "Request ID: AR-6021", fill="#111827", font=F_BODY)
    d.text((100, 198), "User: Daniel Kim", fill="#111827", font=F_BODY)
    y = 280
    for label, checked in [("Production database", True), ("Billing export bucket", False), ("Break-glass admin", False)]:
        d.rectangle((110, y, 142, y + 32), outline="#111827", width=3)
        if checked:
            d.line((116, y + 17, 126, y + 28, 138, y + 6), fill="#0f766e", width=5)
        d.text((162, y - 2), label, fill="#111827", font=F_BODY)
        y += 58
    d.line((165, 338, 405, 338), fill="#b91c1c", width=4)
    d.text((430, 324), "removed by approver", fill="#b91c1c", font=F_SMALL)
    d.text((100, 500), "Duration", fill="#111827", font=F_H2)
    y = 560
    for label, checked in [("24 hours", False), ("7 days", True), ("Permanent", False)]:
        d.ellipse((112, y, 142, y + 30), outline="#111827", width=3)
        if checked:
            d.ellipse((120, y + 8, 134, y + 22), fill="#111827")
        d.text((162, y - 2), label, fill="#111827", font=F_BODY)
        y += 52
    d.text((100, 760), "Approver note: remove billing bucket; production database only.", fill="#111827", font=F_BODY)
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    add_png_page(c, img)
    c.save()


def write_source_state_precedence_gate(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    c.setFillColor(white)
    c.setFont("Helvetica", 10)
    c.drawString(72, 730, "STALE_TEXT_LAYER: Release status APPROVED. Owner: Hana Park. Ship date: 2026-08-04.")
    add_png_page(
        c,
        draw_text_page(
            [
                "Release: RL-884",
                "Product: EU tenant reporting connector",
                "Prepared by: Release Operations",
                "Visible status: BLOCKED",
                "Owner: Nisha Vora",
                "Ship date: 2026-08-11",
                "Reason: EU tenant security signoff missing.",
                "Visible stamp: HOLD UNTIL SIGNOFF",
                "",
                "Current review notes:",
                "1. Security review SR-19 remains open.",
                "2. Documentation package is otherwise complete.",
                "3. Hana Park transferred ownership to Nisha Vora on 2026-08-07.",
                "4. Release may proceed only after signoff is attached to the ticket.",
            ],
            title="Final Release Exception Card",
        ),
    )
    c.save()


def write_multi_page_continuity_gate(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    for title, lines in [
        (
            "Draft Change Order",
            [
                "CO-1184",
                "Status: DRAFT",
                "Window: 2026-08-12 01:00-03:00",
                "Rollback owner: Alex Meyer",
                "Risk: medium",
                "",
                "Affected services:",
                "API gateway: drain standby pool first",
                "Billing worker: pause batch queue",
                "Notification service: monitor delayed retries",
                "",
                "Open items:",
                "CAB review pending",
                "Storage snapshot estimate still preliminary",
                "Customer notice not yet approved",
            ],
        ),
        (
            "Signed Change Order",
            [
                "CO-1184",
                "Status: APPROVED",
                "Window: 2026-08-13 02:00-04:00",
                "Rollback owner: Sana Rao",
                "Risk: high",
                "Signature: M. Chen, 2026-08-07",
                "",
                "Approved execution checklist:",
                "01:40 freeze deploy queue",
                "02:00 start API gateway drain",
                "02:35 pause billing worker",
                "03:10 verify retry lag under 90 seconds",
                "03:50 rollback checkpoint review",
            ],
        ),
        (
            "Post-Approval Correction",
            [
                "CO-1184",
                "Correction: maintenance window remains 2026-08-13 02:00-04:00.",
                "Correction: rollback owner changed to Omar Nadir.",
                "Final status: APPROVED WITH OWNER CORRECTION",
                "",
                "Correction log:",
                "Sana Rao is out for incident coverage.",
                "Omar Nadir accepted rollback ownership at 2026-08-08 09:15.",
                "No change to customer notice, risk rating, or window.",
                "Attach this correction page after the signed change order.",
            ],
        ),
    ]:
        add_png_page(c, draw_text_page(lines, title=title))
    c.save()


NATIVE_RECOVERY_PAGES = [
    [
        "# Ops Review Export Recovery",
        "",
        "Document: OR-7712",
        "Department: West Region Logistics",
        "Prepared: 2026-07-05",
        "Owner: Lena Ortiz",
        "",
        "## Executive Memo",
        "The July export from the presentation system rendered with missing glyphs and collapsed text boxes, but the archived copy retains the intended memo content.",
        "Final recommendation: hold the Reno outbound consolidation until the dock staffing exception closes.",
        "Exception owner: Ravi Mehta.",
        "Review deadline: 2026-07-12 16:00 PT.",
        "",
        "## Decision Register",
        "| ID | Topic | Decision | Owner | Due |",
        "| D-17 | Reno consolidation | Hold pending dock staffing exception | Ravi Mehta | 2026-07-12 16:00 PT |",
        "| D-18 | Boise overflow | Approve temporary cross-dock slot B7 | Lena Ortiz | 2026-07-09 |",
        "| D-19 | Tacoma weekend linehaul | Keep existing carrier allocation | Mira Chen | 2026-07-11 |",
    ],
    [
        "# Operations Table Continuation",
        "",
        "## Lane Risk Register",
        "| Lane | Volume | Constraint | Status | Action |",
        "| Reno -> SFO | 41 pallets | Dock crew short by 3 | Blocked | Wait for staffing exception close |",
        "| Boise -> SEA | 18 pallets | Overflow slot needed | Approved | Use temporary cross-dock slot B7 |",
        "| Tacoma -> PDX | 27 pallets | Carrier capacity tight | Watch | Keep current allocation and monitor tender rejects |",
        "| Spokane -> SEA | 12 pallets | None | Clear | No action |",
        "",
        "The blocked Reno lane is the controlling constraint. The Boise overflow action does not release the Reno hold.",
    ],
    [
        "# Final Reconciliation",
        "",
        "## Cost Reserve",
        "| Item | Amount | Reserve treatment |",
        "| Temporary slot B7 | $2,400 | Eligible |",
        "| Reno labor standby | $3,850 | Eligible if hold extends past 2026-07-12 |",
        "| Tacoma weekend premium | $1,175 | Not eligible |",
        "",
        "Eligible reserve if Reno hold extends: $6,250.",
        "Eligible reserve if Reno hold closes on time: $2,400.",
        "Final controlling statement: Reno outbound consolidation remains ON HOLD until Ravi Mehta closes the dock staffing exception.",
    ],
]


def write_native_text_recovery_depth(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    for index, lines in enumerate(NATIVE_RECOVERY_PAGES, start=1):
        c.setFillColor(white)
        c.setFont("Helvetica", 8)
        y = 720
        for line in lines:
            c.drawString(36, y, line)
            y -= 11
            if y < 42:
                break
        img = Image.new("RGB", (1600, 2100), "white")
        d = ImageDraw.Draw(img)
        d.rectangle((140, 225, 1460, 1880), fill="#e5e7eb")
        d.text((190, 180), f"West Region Logistics - Export Page {index}", fill="#2f343b", font=F_TITLE)
        fragments = [visible_fragment(line) for line in lines if line and not line.startswith("| ---")]
        for i, line in enumerate(fragments[:16]):
            y_img = 300 + i * 58
            x_img = 165 + (i % 4) * 34
            visible = line.replace("|", "  ")[:78]
            d.text((x_img, y_img), visible, fill="#30343a", font=F_SMALL)
            if i % 4 == 2:
                d.rectangle((x_img + 180, y_img - 3, min(1430, x_img + 880), y_img + 24), fill="#d1d5db")
            if i % 7 == 0:
                d.line((160, y_img + 28, 1380, y_img + 18), fill="#9ca3af", width=2)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        c.drawImage(ImageReader(buffer), 0, 0, width=PAGE_W, height=PAGE_H)
        c.showPage()
    c.save()


def visible_fragment(line: str) -> str:
    text = line.strip().lstrip("#").strip()
    if text.startswith("|") and text.endswith("|"):
        cells = [cell.strip() for cell in text.strip("|").split("|")]
        return " / ".join(cell for cell in cells if cell)
    return text


def pdftotext(path: Path) -> str:
    try:
        result = subprocess.run(["pdftotext", "-layout", str(path), "-"], check=True, capture_output=True, text=True)
        return result.stdout.replace("\f", "").strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def fact(id_: str, category: str, weight: float, expectation: str, *, severity: str = "critical", modality: str | None = None) -> dict:
    item = {
        "id": id_,
        "category": category,
        "weight": weight,
        "severity": severity,
        "expectation": expectation,
    }
    if modality:
        item["modality"] = modality
    return item


GateWriter = Callable[[Path], None]


GATES: list[dict] = [
    {
        "id": "G01-native-pdf-text-layer",
        "title": "Native PDF Text Layer Gate",
        "gateId": "native_pdf_text_layer",
        "description": "Recover legitimate extractable PDF text when the rendered page image carries no visible text.",
        "writer": write_native_text_layer_gate,
        "pages": 1,
        "gold": "# Native PDF Text Layer Gate\n\nTEXT_LAYER_PROBE_7F3A: The shipment hold code is QX-914.\n\nFacility: Delta Cold Chain, Door 12.\n\nRelease instruction: keep pallet P-882 on hold until QA signs FORM-19.\n",
        "facts": [
            fact("g01.probe", "native_text_layer", 8, "The output preserves TEXT_LAYER_PROBE_7F3A and shipment hold code QX-914.", modality="native_pdf_text_layer"),
            fact("g01.release_instruction", "native_text_layer", 6, "The output preserves Delta Cold Chain Door 12 and the instruction to keep pallet P-882 on hold until QA signs FORM-19.", modality="native_pdf_text_layer"),
        ],
    },
    {
        "id": "G02-raster-visual-ocr",
        "title": "Raster Visual OCR Gate",
        "gateId": "raster_visual_ocr",
        "description": "Read document text that exists only as visible raster content inside the PDF.",
        "writer": write_raster_visual_ocr_gate,
        "pages": 1,
        "gold": "# Raster Visual OCR Gate\n\nScanned Receiving Note RN-4481. Dock: North 3. Carrier: Velox Freight. Seal: VX-39022.\n\n| Line | Item | Qty | Condition |\n| --- | --- | ---: | --- |\n| 1 | Sterile wraps | 24 | accepted |\n| 2 | Nitrile gloves | 18 | one carton crushed |\n| 3 | Label rolls | 9 | accepted |\n\nHandwritten note: hold line 2 for supervisor review.\n",
        "facts": [
            fact("g02.header", "visual_ocr", 5, "The output reads RN-4481, Dock North 3, Velox Freight, and seal VX-39022.", modality="raster_visual_ocr"),
            fact("g02.rows", "table_cell", 8, "The raster line items are preserved: sterile wraps 24 accepted; nitrile gloves 18 one carton crushed; label rolls 9 accepted.", modality="raster_visual_ocr"),
            fact("g02.note", "visual_ocr", 5, "The note says to hold line 2 for supervisor review.", modality="raster_visual_ocr"),
        ],
    },
    {
        "id": "G03-layout-reconstruction",
        "title": "Layout Reconstruction Gate",
        "gateId": "layout_reconstruction",
        "description": "Recover reading order and grouping from a realistically drifted slide export.",
        "writer": write_layout_reconstruction_gate,
        "pages": 1,
        "gold": "# Layout Reconstruction Gate\n\nFremont Packaging Transfer - Ops Memo. Quarterly review extract prepared 2026-07-06. Owner: Mira Chen.\n\n## Executive Summary\n\nLine validation is complete for the foil pouch cell, but carton artwork remains under purchasing review. Retail pilot demand was higher than forecast in week 2. Amber cartons remain limited to the pilot channel until reject-rate data is final. The cutover window is conditional because the Line 4 FAT retest must close before release engineering signs the weekend move order.\n\nThe table is the controlling risk register for the Wednesday review. Sidebar notes capture context from the import log and should remain near the transfer summary. A prior slide export shifted some timeline labels, but the operating plan remains validation, artwork lock, retail pilot, then cutover. Purchasing asked that supplier slips and reject-rate issues stay visible in the memo excerpt.\n\n## Sidebar: import log\n\nQ3 pilot label shifted during Google Slides import. Actual timeline has four milestone bars, not six.\n\n## Transfer Timeline\n\nTimeline has four milestone bars: Line validation in Q1-Q2, Carton artwork lock in Q2-Q3, Retail pilot in Q3-Q4, and Cutover window in Q4. Colors indicate blue = validation, green = approval, orange = retail pilot, red = cutover.\n\n## Risks and Decisions\n\n| ID | Issue | Decision | Owner |\n| --- | --- | --- | --- |\n| R-12 | Foil pouch supplier slips by 2 weeks | Escalate to dual-source plan | Iris |\n| R-18 | Line 4 reject rate above 1.5% | Hold cutover until FAT retest | Mateo |\n| D-07 | Use amber cartons for pilot only | Approved by Mira on 2026-07-02 | Mira |\n\n## Review Closeout\n\nFinal cutover remains gated by FAT retest for Line 4. Purchasing must confirm dual-source pricing before amber carton pilot expansion.\n",
        "facts": [
            fact("g03.timeline", "layout", 8, "The timeline is reconstructed as four actual bars in order: Line validation, Carton artwork lock, Retail pilot, and Cutover window.", modality="layout_reconstruction"),
            fact("g03.risk_table", "table_cell", 8, "The risk/decision rows preserve R-12 dual-source plan/Iris, R-18 hold cutover until FAT retest/Mateo, and D-07 amber cartons approved by Mira on 2026-07-02/Mira.", modality="layout_reconstruction"),
            fact("g03.sidebar_closeout", "layout", 5, "The sidebar/import-log and review closeout content are preserved near the memo: Q3 pilot label shifted, four milestone bars not six, final cutover gated by FAT retest, and purchasing must confirm dual-source pricing.", severity="major", modality="layout_reconstruction"),
        ],
    },
    {
        "id": "G04-visual-semantics",
        "title": "Visual Semantics Gate",
        "gateId": "visual_semantic",
        "description": "Extract meaning from checkboxes, radio buttons, strike-through corrections, and local notes.",
        "writer": write_visual_semantics_gate,
        "pages": 1,
        "gold": "# Visual Semantics Gate\n\nAccess Request Form. Request ID: AR-6021. User: Daniel Kim.\n\nCheckbox states: Production database is checked. Billing export bucket is unchecked and removed by approver. Break-glass admin is unchecked.\n\nDuration radio state: 7 days is selected; 24 hours and Permanent are not selected.\n\nApprover note: remove billing bucket; production database only.\n",
        "facts": [
            fact("g04.checkboxes", "form_state", 8, "Production database is checked; billing export bucket is removed by approver; break-glass admin is unchecked.", modality="visual_semantic"),
            fact("g04.radio", "form_state", 6, "The 7 days radio option is selected; 24 hours and Permanent are not selected.", modality="visual_semantic"),
            fact("g04.note", "form_state", 5, "The approver note says remove billing bucket and production database only.", modality="visual_semantic"),
        ],
    },
    {
        "id": "G05-source-state-precedence",
        "title": "Source State Precedence Gate",
        "gateId": "source_state_precedence",
        "description": "Prefer visible current document state over stale hidden PDF text when they conflict.",
        "writer": write_source_state_precedence_gate,
        "pages": 1,
        "gold": "# Source State Precedence Gate\n\nFinal Release Exception Card.\n\nRelease: RL-884\n\nProduct: EU tenant reporting connector\n\nPrepared by: Release Operations\n\nVisible status: BLOCKED\n\nOwner: Nisha Vora\n\nShip date: 2026-08-11\n\nReason: EU tenant security signoff missing.\n\nVisible stamp: HOLD UNTIL SIGNOFF\n\n## Current Review Notes\n\n1. Security review SR-19 remains open.\n2. Documentation package is otherwise complete.\n3. Hana Park transferred ownership to Nisha Vora on 2026-08-07.\n4. Release may proceed only after signoff is attached to the ticket.\n\nThe stale hidden values APPROVED, Hana Park as current owner, and 2026-08-04 are not current visible release values.\n",
        "facts": [
            fact("g05.visible_final", "source_state", 10, "The visible final exception card is preserved: RL-884 product EU tenant reporting connector is BLOCKED, owner Nisha Vora, ship date 2026-08-11, reason EU tenant security signoff missing, stamp HOLD UNTIL SIGNOFF.", modality="source_state_precedence"),
            fact("g05.review_notes", "source_state", 5, "The current review notes are preserved: SR-19 remains open, docs are otherwise complete, Hana Park transferred ownership to Nisha Vora on 2026-08-07, and release needs signoff attached.", severity="major", modality="source_state_precedence"),
            fact("g05.hidden_stale_not_current", "forbidden_text", 8, "The hidden stale layer is not presented as current visible content: APPROVED, Hana Park, and 2026-08-04 are wrong for the visible document.", modality="source_state_precedence"),
        ],
    },
    {
        "id": "G06-multi-page-continuity",
        "title": "Multi Page Continuity Gate",
        "gateId": "multi_page_continuity",
        "description": "Preserve packet order and final state across multiple related pages.",
        "writer": write_multi_page_continuity_gate,
        "pages": 3,
        "gold": "# Multi Page Continuity Gate\n\n## Draft Change Order\n\nCO-1184. Status: DRAFT. Window: 2026-08-12 01:00-03:00. Rollback owner: Alex Meyer. Risk: medium.\n\nAffected services: API gateway drain standby pool first; billing worker pause batch queue; notification service monitor delayed retries.\n\nOpen items: CAB review pending; storage snapshot estimate preliminary; customer notice not yet approved.\n\n## Signed Change Order\n\nCO-1184. Status: APPROVED. Window: 2026-08-13 02:00-04:00. Rollback owner: Sana Rao. Risk: high. Signature: M. Chen, 2026-08-07.\n\nApproved execution checklist: 01:40 freeze deploy queue; 02:00 start API gateway drain; 02:35 pause billing worker; 03:10 verify retry lag under 90 seconds; 03:50 rollback checkpoint review.\n\n## Post-Approval Correction\n\nCO-1184. Correction: maintenance window remains 2026-08-13 02:00-04:00. Correction: rollback owner changed to Omar Nadir. Final status: APPROVED WITH OWNER CORRECTION.\n\nCorrection log: Sana Rao is out for incident coverage. Omar Nadir accepted rollback ownership at 2026-08-08 09:15. No change to customer notice, risk rating, or window. Attach this correction page after the signed change order.\n",
        "facts": [
            fact("g06.packet_order", "document_state", 7, "The output preserves draft, signed, and post-approval correction pages as distinct states for CO-1184.", modality="multi_page_continuity"),
            fact("g06.final_state", "document_state", 10, "The final state is approved with owner correction, final window 2026-08-13 02:00-04:00, and final rollback owner Omar Nadir.", modality="multi_page_continuity"),
            fact("g06.supporting_details", "document_state", 5, "Supporting details are preserved: affected services on draft page, approved execution checklist on signed page, and correction log showing Omar accepted ownership at 2026-08-08 09:15.", severity="major", modality="multi_page_continuity"),
        ],
    },
]


NATIVE_TEXT_DEPTH_CASE = {
    "id": "P23-native-text-layer-recovery",
    "title": "Bad Export Native Text Recovery Packet",
    "family": "native-text-recovery",
    "role": "depth",
    "requiredGates": ["native_pdf_text_layer"],
    "tags": ["multi-page", "native-text-layer", "bad-export", "tables", "source-recovery"],
    "pages": 3,
    "writer": write_native_text_recovery_depth,
    "gold": "\n\n".join("\n".join(page) for page in NATIVE_RECOVERY_PAGES) + "\n",
    "facts": [
        fact("p23.memo", "native_text_layer", 8, "The memo preserves OR-7712, West Region Logistics, prepared 2026-07-05, owner Lena Ortiz, final recommendation to hold Reno outbound consolidation, exception owner Ravi Mehta, and review deadline 2026-07-12 16:00 PT.", modality="native_pdf_text_layer"),
        fact("p23.decisions", "table_cell", 10, "Decision register preserves D-17 Reno consolidation hold pending dock staffing exception/Ravi/2026-07-12 16:00 PT, D-18 Boise overflow approve temporary cross-dock slot B7/Lena/2026-07-09, and D-19 Tacoma weekend linehaul keep existing carrier allocation/Mira/2026-07-11.", modality="native_pdf_text_layer"),
        fact("p23.lanes", "table_cell", 10, "Lane risk register preserves Reno -> SFO 41 pallets blocked dock crew short by 3, Boise -> SEA 18 pallets approved overflow slot B7, Tacoma -> PDX 27 pallets watch carrier capacity tight, and Spokane -> SEA 12 pallets clear.", modality="native_pdf_text_layer"),
        fact("p23.reserve", "table_cell", 8, "Cost reserve preserves temporary slot B7 $2,400 eligible, Reno labor standby $3,850 eligible if hold extends, Tacoma weekend premium $1,175 not eligible, reserve $6,250 if hold extends and $2,400 if closes on time.", modality="native_pdf_text_layer"),
        fact("p23.final", "source_state", 8, "Final controlling statement is that Reno outbound consolidation remains ON HOLD until Ravi Mehta closes the dock staffing exception.", modality="native_pdf_text_layer"),
    ],
}


CAPABILITY_GATES = [
    {
        "id": gate["gateId"],
        "title": gate["title"],
        "caseId": gate["id"],
        "description": gate["description"],
        "passThreshold": 80,
    }
    for gate in GATES
]


DEPTH_REQUIRED_GATES = {
    "P07-launch-readiness-dossier": [
        "raster_visual_ocr",
        "layout_reconstruction",
        "visual_semantic",
        "source_state_precedence",
        "multi_page_continuity",
    ],
    "P12-pfas-method-validation": [
        "raster_visual_ocr",
        "layout_reconstruction",
        "visual_semantic",
        "multi_page_continuity",
    ],
    "P15-architecture-floorplan-diagrams": [
        "raster_visual_ocr",
        "layout_reconstruction",
        "visual_semantic",
        "source_state_precedence",
        "multi_page_continuity",
    ],
    "P17-clinical-trial-site-monitoring": [
        "raster_visual_ocr",
        "layout_reconstruction",
        "visual_semantic",
        "source_state_precedence",
        "multi_page_continuity",
    ],
    "P20-utility-outage-restoration": [
        "raster_visual_ocr",
        "layout_reconstruction",
        "visual_semantic",
        "source_state_precedence",
        "multi_page_continuity",
    ],
    "P21-semiconductor-lot-disposition": [
        "raster_visual_ocr",
        "layout_reconstruction",
        "visual_semantic",
        "source_state_precedence",
        "multi_page_continuity",
    ],
    "P22-pharma-stability-release": [
        "raster_visual_ocr",
        "layout_reconstruction",
        "visual_semantic",
        "source_state_precedence",
        "multi_page_continuity",
    ],
}


def write_native_text_depth_case() -> dict:
    case = NATIVE_TEXT_DEPTH_CASE
    case_dir = CASE_ROOT / case["id"]
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True)
    writer: GateWriter = case["writer"]
    writer(case_dir / "source.pdf")
    (case_dir / "gold.md").write_text(case["gold"], encoding="utf-8")
    (case_dir / "spec.md").write_text(f"# {case['title']}\n\n{case['family']}\n", encoding="utf-8")
    (case_dir / "checks.json").write_text(
        json.dumps({"id": case["id"], "title": case["title"], "family": case["family"], "tags": case["tags"], "checks": []}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    (case_dir / "facts.json").write_text(
        json.dumps({"id": case["id"], "title": case["title"], "family": case["family"], "tags": case["tags"], "facts": case["facts"]}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return {
        "id": case["id"],
        "title": case["title"],
        "family": case["family"],
        "role": "depth",
        "requiredGates": case["requiredGates"],
        "tags": case["tags"],
        "pages": case["pages"],
        "pdf": f"benchmark/cases/{case['id']}/source.pdf",
        "gold": f"benchmark/cases/{case['id']}/gold.md",
        "spec": f"benchmark/cases/{case['id']}/spec.md",
        "checks": f"benchmark/cases/{case['id']}/checks.json",
        "facts": f"benchmark/cases/{case['id']}/facts.json",
    }


def deterministic_checks(gate: dict) -> list[dict]:
    checks = []
    for item in gate["facts"]:
        checks.append(
            {
                "id": item["id"],
                "category": item["category"],
                "weight": min(3, item["weight"]),
                "description": item["expectation"],
            }
        )
    return checks


def write_gate_case(gate: dict) -> dict:
    case_dir = CASE_ROOT / gate["id"]
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True)
    pdf_path = case_dir / "source.pdf"
    writer: GateWriter = gate["writer"]
    writer(pdf_path)

    diagnostic_dir = GATE_ROOT / gate["id"]
    diagnostic_dir.mkdir(parents=True, exist_ok=True)
    extracted = pdftotext(pdf_path)
    (diagnostic_dir / "pdftotext.txt").write_text(extracted + ("\n" if extracted else ""), encoding="utf-8")
    (diagnostic_dir / "probe.json").write_text(
        json.dumps(
            {
                "id": gate["id"],
                "gateId": gate["gateId"],
                "title": gate["title"],
                "description": gate["description"],
                "observedPdftotext": extracted,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    tags = ["capability-gate", gate["gateId"]]
    (case_dir / "gold.md").write_text(gate["gold"], encoding="utf-8")
    (case_dir / "spec.md").write_text(
        f"# {gate['title']}\n\n{gate['description']}\n",
        encoding="utf-8",
    )
    (case_dir / "checks.json").write_text(
        json.dumps({"id": gate["id"], "title": gate["title"], "family": "capability-gate", "tags": tags, "checks": deterministic_checks(gate)}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    (case_dir / "facts.json").write_text(
        json.dumps({"id": gate["id"], "title": gate["title"], "family": "capability-gate", "tags": tags, "facts": gate["facts"]}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return {
        "id": gate["id"],
        "title": gate["title"],
        "family": "capability-gate",
        "role": "gate",
        "gateId": gate["gateId"],
        "tags": tags,
        "pages": gate["pages"],
        "pdf": f"benchmark/cases/{gate['id']}/source.pdf",
        "gold": f"benchmark/cases/{gate['id']}/gold.md",
        "spec": f"benchmark/cases/{gate['id']}/spec.md",
        "checks": f"benchmark/cases/{gate['id']}/checks.json",
        "facts": f"benchmark/cases/{gate['id']}/facts.json",
        "probe": f"benchmark/gates/{gate['id']}/probe.json",
        "pdftotext": f"benchmark/gates/{gate['id']}/pdftotext.txt",
    }


def main() -> None:
    manifest_path = BENCHMARK_ROOT / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("benchmark/manifest.json does not exist. Run scripts/generate_benchmark.py first.")

    GATE_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    depth_cases = [
        case
        for case in manifest.get("cases", [])
        if case.get("role") != "gate" and not str(case.get("id", "")).startswith("G") and case.get("id") != NATIVE_TEXT_DEPTH_CASE["id"]
    ]
    gate_cases = [write_gate_case(gate) for gate in GATES]
    native_depth_case = write_native_text_depth_case()

    for case in depth_cases:
        case["role"] = "depth"
        case["requiredGates"] = DEPTH_REQUIRED_GATES.get(case["id"], [])

    all_cases = gate_cases + [native_depth_case] + depth_cases
    updated = {
        **manifest,
        "suite": "official",
        "scoreName": "Doc2MD Gated Native PDF Score",
        "capabilityGates": CAPABILITY_GATES,
        "gatePolicy": {
            "officialScoreUses": "depth_cases_after_gate_zeroing",
            "gateScoreContribution": "reported_not_in_official_denominator",
            "failedGateBehavior": "dependent depth cases receive finalScore 0 while rawScore is still reported",
        },
        "gateCount": len(gate_cases),
        "depthCaseCount": len(depth_cases) + 1,
        "caseCount": len(all_cases),
        "pageCount": sum(int(case.get("pages", 1)) for case in all_cases),
        "cases": all_cases,
    }
    manifest_path.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(gate_cases)} capability gates and {len(depth_cases) + 1} depth cases to {manifest_path}")


if __name__ == "__main__":
    main()
