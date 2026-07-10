from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter

from .common import (
    REPO_ROOT,
    finalize_fact_regions,
    leaf,
    markdown_table,
    source_precedence_leaf,
    table_leaves,
    visual_leaf,
)


CASE_ID = "P23-native-text-layer-recovery"
TITLE = "Northstar Cold Chain Supplier Cutover Authorization"
FAMILY = "office export recovery"
TAGS = [
    "native-pdf",
    "libreoffice-export",
    "malformed-layout",
    "native-text-recovery",
    "mixed-modality",
    "tables",
    "source-precedence",
    "reading-order",
]


CONTROL_HEADERS = ["Field", "Controlled value", "Field", "Controlled value"]
CONTROL_ROWS = [
    ["File", "SV-2048", "Revision", "D"],
    ["Prepared", "08 Jul 2026", "Effective", "10 Jul 2026 09:30 MST"],
    ["Sites", "Phoenix and Tucson", "Coordinator", "Avery Kim"],
]

AUTHORITY_HEADERS = ["Priority", "Record", "Controls", "Does not control"]
AUTHORITY_ROWS = [
    ["1", "Page 5 final authorization", "GO/HOLD state and release conditions", "Individual rate details"],
    ["2", "Page 4 exception register", "Exception scope, owner, and closure evidence", "Commercial ceiling"],
    ["3", "Page 3 finance validation", "Authorized cost ceiling and invoice route", "Operational release"],
    ["4", "Page 2 cutover workplan", "Task sequence, windows, and task gates", "Final authorization"],
    ["Reference", "Email and meeting notes", "Context only when cited by a controlled row", "Any approval or closure"],
]

WORKPLAN_HEADERS = ["ID", "Site / asset", "Activity", "Owner", "Planned window", "Gate / evidence", "State"]
WORKPLAN_ROWS = [
    [
        "T-01",
        "Phoenix / Dock 4",
        "Reserve the temperature-controlled bay; retain Kestrel access until EX-07 is signed.",
        "Avery Kim",
        "14 Jul 22:00-23:00 MST",
        "Facilities call FC-119 and access list AC-44",
        "READY",
    ],
    [
        "T-02",
        "Phoenix / Sensor P-14",
        "Move telemetry from Kestrel gateway KG-2 to Boreal gateway BG-5; preserve 15-minute data.",
        "Lin Chen",
        "14 Jul 23:00-23:40 MST",
        "Parallel-read delta <=0.3 C for 30 minutes",
        "CONDITIONAL",
    ],
    [
        "T-03",
        "Tucson / Cage C",
        "Seal returned Kestrel inventory and complete a dual count before carrier release.",
        "Mateo Soto",
        "15 Jul 00:15-01:00 MST",
        "Dual count sheet IC-882",
        "READY",
    ],
    [
        "T-04",
        "Phoenix / Lot PX-771",
        "Transfer 48 pallets only after the T-02 telemetry gate passes.",
        "Rina Singh",
        "15 Jul 00:30-02:10 MST",
        "Scan batch SC-77; zero orphan pallets",
        "BLOCKED BY T-02",
    ],
    [
        "T-05",
        "Tucson / Lot TZ-219",
        "Transfer 26 pallets and exclude six quarantined cases held under QA-61.",
        "Jordan Cole",
        "15 Jul 01:20-02:20 MST",
        "QA release QR-203 for eligible stock",
        "READY",
    ],
    [
        "T-06",
        "Both sites / credentials",
        "Close Kestrel credentials after inventory reconciliation and legal waiver confirmation.",
        "Avery Kim",
        "15 Jul 04:30 MST",
        "REC-2048 has zero unresolved items and EX-07 is signed",
        "PENDING",
    ],
]

HANDOFF_HEADERS = ["Trigger", "Notify", "Channel", "Required content"]
HANDOFF_ROWS = [
    ["T-02 passes", "Phoenix floor lead", "Bridge BR-2048", "P-14 delta and validation end time"],
    ["T-04 completes", "Inventory control", "Queue IC-WEST", "PX-771 pallet count and orphan count"],
    ["Any temperature breach", "Quality on-call", "QA hotline", "Sensor, duration, peak delta, and lot"],
    ["Rollback invoked", "Both site leads", "Bridge BR-2048", "Last completed task and custody location"],
]

COST_HEADERS = ["Line", "Basis", "Amount", "Approval condition"]
COST_ROWS = [
    ["Boreal implementation", "Quote Q-884 revision C", "$18,600", "Fixed fee"],
    ["Kestrel overlap", "Two nights at $2,160", "$4,320", "Maximum two nights"],
    ["Sensor validation", "Work order TV-19", "$2,150", "P-14 parallel read"],
    ["Contingency", "Legal-delay allowance", "$3,000", "Available only if EX-07 extends"],
]

INVOICE_HEADERS = ["Vendor", "PO", "Cost center", "Reviewer", "Route"]
INVOICE_ROWS = [
    ["Boreal Storage", "44018-3", "CC-7420", "Jonah Mercer", "AP-West / transition"],
    ["Kestrel Logistics", "44007-9", "CC-7420", "Jonah Mercer", "AP-West / overlap"],
    ["ThermoVision", "43991-2", "CC-7314", "Nadia Brooks", "AP-Quality / validation"],
]

EXCEPTION_HEADERS = [
    "Exception",
    "Affected obligation",
    "Current finding",
    "Owner",
    "Due",
    "Accepted closure evidence",
    "State",
]
EXCEPTION_ROWS = [
    [
        "E-05",
        "T-02 telemetry gate",
        "Parallel baseline differs by 0.2 C after probe alignment.",
        "Lin Chen",
        "09 Jul 15:00 MST",
        "Signed TV-19 trace with 30-minute comparison",
        "CLOSED",
    ],
    [
        "EX-07",
        "T-06 credential closure",
        "Kestrel access waiver is with counsel; physical cutover may proceed while access is retained.",
        "Isha Patel",
        "14 Jul 18:00 MST",
        "Countersigned waiver WA-771",
        "OPEN",
    ],
    [
        "E-08",
        "T-05 Tucson inventory",
        "Six QA-61 cases remain quarantined and are outside the eligible transfer quantity.",
        "Dara Nwosu",
        "15 Jul 01:00 MST",
        "QR-203 release or segregated custody receipt",
        "OPEN - EXCLUDE",
    ],
    [
        "E-09",
        "Boreal invoice route",
        "Draft purchase order omitted the transition suffix.",
        "Jonah Mercer",
        "09 Jul 12:00 MST",
        "Issued PO 44018-3",
        "CLOSED",
    ],
    [
        "E-11",
        "T-03 carrier release",
        "Carrier arrival is forecast at 01:10, ten minutes after the planned count window.",
        "Mateo Soto",
        "15 Jul 00:30 MST",
        "Dispatch update in BR-2048 and revised custody time",
        "WATCH",
    ],
    [
        "E-12",
        "Tucson backup power",
        "Backup power transfer test passed in 46 seconds against the 60 second limit.",
        "Jordan Cole",
        "09 Jul 17:00 MST",
        "Facilities test certificate FT-662",
        "CLOSED",
    ],
]

CONDITION_HEADERS = ["Condition", "Required state before action", "Action governed", "Failure response"]
CONDITION_ROWS = [
    ["C-1", "P-14 parallel-read delta <=0.3 C for 30 minutes", "Start T-04", "Hold PX-771 at Phoenix"],
    ["C-2", "Six QA-61 cases remain segregated unless QR-203 releases them", "Start T-05", "Move eligible stock only"],
    ["C-3", "EX-07 signed and REC-2048 has zero unresolved items", "Close Kestrel credentials", "Retain access and escalate"],
    ["C-4", "No temperature deviation >1.0 C for 10 continuous minutes", "Continue physical transfer", "Invoke rollback RB-12"],
]

SIGNOFF_HEADERS = ["Role", "Name", "Decision", "Recorded"]
SIGNOFF_ROWS = [
    ["Executive sponsor", "Mara Velez", "Approved", "10 Jul 2026 09:12 MST"],
    ["Cutover lead", "Avery Kim", "Accepted", "10 Jul 2026 09:18 MST"],
    ["Quality", "Dara Nwosu", "Approved with QA-61 exclusion", "10 Jul 2026 09:26 MST"],
    ["Legal exception owner", "Isha Patel", "EX-07 remains open; not a release signature", "Review due 14 Jul 18:00 MST"],
]


def _set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def _set_cell_margins(cell, *, top: int = 50, start: int = 60, bottom: int = 45, end: int = 60) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def _set_repeat_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    tr_pr.append(repeat)


def _set_table_fixed(table) -> None:
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    layout = tbl_pr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tbl_pr.append(layout)
    layout.set(qn("w:type"), "fixed")
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = OxmlElement(f"w:{edge}")
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), "3")
        node.set(qn("w:color"), "B8C0C7")
        borders.append(node)


def _write_cell(cell, value: str, *, header: bool = False, compact: bool = False) -> None:
    cell.text = ""
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    _set_cell_margins(cell, top=28 if compact else 45, bottom=24 if compact else 40)
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = Pt(7.8 if compact else 9.3)
    run = paragraph.add_run(str(value))
    run.bold = header
    run.font.name = "Arial"
    run.font.size = Pt(6.7 if compact else 7.5)
    run.font.color.rgb = RGBColor(25, 35, 43)


def _add_table(
    document: Document,
    headers: list[str],
    rows: list[list[str]],
    widths: list[float],
    *,
    exact_rows: bool = False,
    row_height: float = 0.31,
    compact: bool = False,
):
    table = document.add_table(rows=1, cols=len(headers))
    _set_table_fixed(table)
    for grid_col, width in zip(table._tbl.tblGrid.gridCol_lst, widths, strict=True):
        grid_col.set(qn("w:w"), str(int(width * 1440)))
    header = table.rows[0]
    header.height = Inches(0.29 if compact else 0.32)
    header.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    _set_repeat_header(header)
    for cell, text, width in zip(header.cells, headers, widths, strict=True):
        cell.width = Inches(width)
        _set_cell_shading(cell, "D9E2E8")
        _write_cell(cell, text, header=True, compact=compact)
    for row_index, values in enumerate(rows):
        row = table.add_row()
        if exact_rows:
            row.height = Inches(row_height)
            row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
        for cell, value, width in zip(row.cells, values, widths, strict=True):
            cell.width = Inches(width)
            if row_index % 2:
                _set_cell_shading(cell, "F2F5F6")
            _write_cell(cell, value, compact=compact)
    return table


def _keep_with_next(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    keep = p_pr.find(qn("w:keepNext"))
    if keep is None:
        keep = OxmlElement("w:keepNext")
        p_pr.append(keep)


def _label(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(2.5)
    _keep_with_next(paragraph)
    run = paragraph.add_run(text.upper())
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(6.4)
    run.font.color.rgb = RGBColor(68, 82, 93)


def _paragraph(document: Document, text: str, *, size: float = 8.4, bold: bool = False) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(4)
    paragraph.paragraph_format.line_spacing = Pt(size + 2.1)
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.name = "Arial"
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor(25, 35, 43)


def _page_title(document: Document, page: int, title: str, status: str) -> None:
    banner = document.add_table(rows=1, cols=2)
    banner.autofit = False
    banner.alignment = WD_TABLE_ALIGNMENT.LEFT
    banner.columns[0].width = Inches(6.15 if page != 4 else 8.7)
    banner.columns[1].width = Inches(1.25)
    for cell in banner.rows[0].cells:
        _set_cell_margins(cell, top=5, bottom=5, start=0, end=0)
    left = banner.cell(0, 0).paragraphs[0]
    left.paragraph_format.space_after = Pt(0)
    run = left.add_run("NORTHSTAR COLD CHAIN  |  SUPPLIER TRANSITION SV-2048")
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(6.4)
    run.font.color.rgb = RGBColor(60, 76, 87)
    right = banner.cell(0, 1).paragraphs[0]
    right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    right.paragraph_format.space_after = Pt(0)
    run = right.add_run(f"{status}  |  {page}/5")
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(6.4)
    run.font.color.rgb = RGBColor(124, 55, 42)
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(5)
    paragraph.paragraph_format.space_after = Pt(3)
    run = paragraph.add_run(title)
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(16.5)
    run.font.color.rgb = RGBColor(19, 38, 52)
    rule = document.add_paragraph()
    rule.paragraph_format.space_after = Pt(2)
    run = rule.add_run("_" * (96 if page == 4 else 72))
    run.font.name = "Arial"
    run.font.size = Pt(5.6)
    run.font.color.rgb = RGBColor(170, 181, 188)


def _configure_section(section, *, landscape: bool = False) -> None:
    if landscape:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = Inches(11)
        section.page_height = Inches(8.5)
        section.top_margin = Inches(0.38)
        section.bottom_margin = Inches(0.35)
        section.left_margin = Inches(0.42)
        section.right_margin = Inches(0.42)
    else:
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width = Inches(8.5)
        section.page_height = Inches(11)
        section.top_margin = Inches(0.42)
        section.bottom_margin = Inches(0.42)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)
    section.header_distance = Inches(0.15)
    section.footer_distance = Inches(0.15)


def _add_reviewer_sidebar(document: Document) -> None:
    """Add an ordinary floating review table anchored to its body position.

    Word reserves a right-side wrap area for the page-anchored review note.
    Writer shifts the note and the fixed-height table during DOCX import, leaving
    compressed rows and altered reading order. Both layers remain native.
    """
    table = document.add_table(rows=2, cols=1)
    table.autofit = False
    table.columns[0].width = Inches(2.05)
    _set_table_fixed(table)
    tbl_pr = table._tbl.tblPr
    position = OxmlElement("w:tblpPr")
    position.set(qn("w:leftFromText"), "180")
    position.set(qn("w:rightFromText"), "180")
    position.set(qn("w:topFromText"), "120")
    position.set(qn("w:bottomFromText"), "120")
    position.set(qn("w:vertAnchor"), "page")
    position.set(qn("w:horzAnchor"), "page")
    position.set(qn("w:tblpX"), "8200")
    position.set(qn("w:tblpY"), "2760")
    tbl_pr.append(position)
    overlap = OxmlElement("w:tblOverlap")
    overlap.set(qn("w:val"), "never")
    tbl_pr.append(overlap)
    header, note = table.rows
    header.height = Inches(0.28)
    header.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    _set_cell_shading(header.cells[0], "C9D6DE")
    _write_cell(header.cells[0], "APPROVER SIDEBAR - 08 JUL", header=True)
    note.height = Inches(0.82)
    note.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
    _set_cell_shading(note.cells[0], "EEF3F5")
    _write_cell(
        note.cells[0],
        "A. Kim: keep Kestrel Dock 4 access active until counsel signs EX-07. This margin note is advisory; page 5 controls release.",
    )


def _font(size: int, *, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Verdana Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Verdana.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default(size=size)


def _finance_stamp(path: Path) -> None:
    image = Image.new("RGBA", (920, 300), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    green = (36, 104, 76, 238)
    draw.rounded_rectangle((15, 15, 905, 285), radius=24, outline=green, width=9)
    draw.line((42, 96, 878, 96), fill=green, width=4)
    draw.text((46, 36), "FINANCE VALIDATED", font=_font(42, bold=True), fill=green)
    draw.text((46, 120), "JONAH MERCER  |  09 JUL 2026 16:42 MST", font=_font(28), fill=green)
    draw.text((46, 171), "CEILING $28,070  |  CONTROL VC-2048", font=_font(28, bold=True), fill=green)
    draw.text((46, 222), "COST VALIDATION IS NOT OPERATIONAL RELEASE", font=_font(24), fill=green)
    image.save(path, format="PNG", optimize=True)


def _configure_document(document: Document) -> None:
    _configure_section(document.sections[0])
    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(8.2)
    normal.paragraph_format.space_after = Pt(0)
    properties = document.core_properties
    properties.title = TITLE
    properties.subject = "Controlled supplier transition file SV-2048"
    properties.author = "Northstar Cold Chain, Regional Operations"
    properties.keywords = "SV-2048, supplier transition, cold storage, cutover"
    properties.created = datetime(2026, 7, 8, 16, 20, tzinfo=timezone.utc)
    properties.modified = datetime(2026, 7, 10, 16, 30, tzinfo=timezone.utc)


def _build_docx(path: Path, stamp_path: Path) -> None:
    document = Document()
    _configure_document(document)

    _page_title(document, 1, "Regional cold-storage cutover approval", "REV D")
    _label(document, "Document control")
    _add_table(document, CONTROL_HEADERS, CONTROL_ROWS, [1.05, 2.55, 1.05, 2.85])
    _label(document, "Change request")
    _paragraph(
        document,
        "Northstar will transfer eligible Phoenix and Tucson inventory from Kestrel Logistics to Boreal Storage during the 14-15 July maintenance window. The change includes telemetry migration, physical custody transfer, invoice routing, and eventual closure of Kestrel credentials. Quarantined inventory remains under Northstar quality control.",
    )
    _label(document, "Record authority and precedence")
    _add_table(document, AUTHORITY_HEADERS, AUTHORITY_ROWS, [0.65, 2.0, 2.5, 2.35], compact=True)
    _label(document, "Review workflow")
    workflow_headers = ["Step", "Owner", "Required review", "Exit record"]
    workflow_rows = [
        ["1", "Cutover lead", "Sequence and operational gates", "Page 2 workplan"],
        ["2", "Finance", "Ceiling, PO, and invoice routing", "Page 3 validation"],
        ["3", "Functional owners", "Exception scope and evidence", "Page 4 register"],
        ["4", "Sponsor and quality", "Selective GO/HOLD authorization", "Page 5 final record"],
    ]
    _add_table(document, workflow_headers, workflow_rows, [0.6, 1.5, 3.1, 2.3])
    _paragraph(
        document,
        "A lower-priority record may supply detail but cannot reverse a higher-priority state. Closure applies only to the obligation named in the exception row.",
        bold=True,
    )
    document.add_page_break()

    _page_title(document, 2, "Cutover workplan and handoff sequence", "CONTROLLED")
    _paragraph(
        document,
        "All times are Mountain Standard Time. Start windows are targets; each task gate remains mandatory even if the prior task finishes early.",
    )
    _label(document, "Workplan")
    _add_table(
        document,
        WORKPLAN_HEADERS,
        WORKPLAN_ROWS,
        [0.45, 1.05, 2.15, 0.9, 1.15, 1.35, 0.95],
        exact_rows=True,
        row_height=0.19,
        compact=True,
    )
    _add_reviewer_sidebar(document)
    _label(document, "Dependency interpretation")
    _paragraph(
        document,
        "T-02 gates the PX-771 transfer in T-04. EX-07 does not block physical transfer; it blocks T-06 credential closure. T-05 may move only eligible Tucson stock while the six QA-61 cases remain segregated.",
    )
    _label(document, "Handoff matrix")
    _add_table(document, HANDOFF_HEADERS, HANDOFF_ROWS, [1.4, 1.45, 1.65, 3.0], exact_rows=True, row_height=0.25, compact=True)
    _label(document, "Rollback trigger")
    _paragraph(
        document,
        "Invoke RB-12 if a temperature deviation exceeds 1.0 C for 10 continuous minutes. Stop the active transfer, preserve custody at the last confirmed location, and report the last completed task on bridge BR-2048.",
    )
    document.add_page_break()

    _page_title(document, 3, "Commercial validation and invoice routing", "FINANCE")
    _label(document, "Authorized cost build")
    _add_table(document, COST_HEADERS, COST_ROWS, [1.55, 2.15, 1.05, 2.75], exact_rows=True, row_height=0.38)
    total_headers = ["Control", "Value", "Interpretation"]
    total_rows = [
        ["Base committed cost", "$25,070", "Implementation, overlap, and sensor validation"],
        ["Conditional contingency", "$3,000", "Usable only while EX-07 extends the overlap"],
        ["Not-to-exceed ceiling", "$28,070", "Requires finance reapproval if exceeded"],
    ]
    _add_table(document, total_headers, total_rows, [1.65, 1.25, 4.6])
    _label(document, "Invoice route")
    _add_table(document, INVOICE_HEADERS, INVOICE_ROWS, [1.45, 1.0, 1.0, 1.45, 2.6])
    _label(document, "Finance scope")
    _paragraph(
        document,
        "Finance validates the ceiling and invoice route. It does not declare an exception closed, satisfy a task gate, or authorize physical release. Unused contingency is not committed spend.",
    )
    document.add_picture(str(stamp_path), width=Inches(4.25))
    document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.RIGHT

    landscape_section = document.add_section(WD_SECTION.NEW_PAGE)
    _configure_section(landscape_section, landscape=True)
    _page_title(document, 4, "Exception and closure-evidence register", "REV D")
    _paragraph(
        document,
        "Read each state against its affected obligation. A closed row does not close another row, and a watch item does not become a hold unless the final authorization says so.",
    )
    _label(document, "Controlled register")
    _add_table(
        document,
        EXCEPTION_HEADERS,
        EXCEPTION_ROWS,
        [0.75, 1.35, 2.7, 1.0, 1.25, 2.35, 1.0],
        exact_rows=True,
        row_height=0.23,
        compact=True,
    )
    _label(document, "Register notes")
    note_headers = ["Marker", "Meaning", "Operational consequence"]
    note_rows = [
        ["CLOSED", "Listed evidence was accepted for that row", "No effect on unrelated exceptions"],
        ["OPEN - EXCLUDE", "Affected inventory stays out of the authorized quantity", "Eligible inventory may proceed"],
        ["WATCH", "Monitor and update the stated evidence channel", "Continue unless a final condition fails"],
    ]
    _add_table(document, note_headers, note_rows, [1.2, 4.3, 4.9], compact=True)
    footnote = document.add_paragraph()
    footnote.paragraph_format.space_before = Pt(5)
    footnote.paragraph_format.space_after = Pt(0)
    footnote.paragraph_format.left_indent = Inches(0.15)
    footnote.paragraph_format.right_indent = Inches(0.15)
    footnote.paragraph_format.line_spacing = Pt(8.1)
    run = footnote.add_run(
        "Record note: Email acknowledgment is context only unless the relevant row cites it as accepted evidence. The signed page 5 authorization controls GO/HOLD state; the finance validation controls cost only."
    )
    run.italic = True
    run.font.name = "Arial"
    run.font.size = Pt(6.8)
    run.font.color.rgb = RGBColor(61, 73, 81)

    final_section = document.add_section(WD_SECTION.NEW_PAGE)
    _configure_section(final_section)
    _page_title(document, 5, "Final implementation authorization", "EFFECTIVE")
    _label(document, "Controlling decision")
    decision = document.add_table(rows=1, cols=2)
    _set_table_fixed(decision)
    decision.columns[0].width = Inches(1.2)
    decision.columns[1].width = Inches(6.25)
    _set_cell_shading(decision.cell(0, 0), "D6E7DD")
    _set_cell_shading(decision.cell(0, 1), "EEF6F1")
    _write_cell(decision.cell(0, 0), "PHYSICAL CUTOVER\nGO", header=True)
    _write_cell(
        decision.cell(0, 1),
        "Begin at 14 Jul 2026 22:00 MST for eligible inventory only. Kestrel credential decommission remains HOLD until C-3 is satisfied.",
        header=True,
    )
    _label(document, "Release conditions")
    _add_table(document, CONDITION_HEADERS, CONDITION_ROWS, [0.75, 2.85, 1.7, 2.2], exact_rows=True, row_height=0.45, compact=True)
    _label(document, "Authorization interpretation")
    _paragraph(
        document,
        "The GO decision permits the physical cutover; it does not close EX-07, release the six QA-61 cases, or waive telemetry and rollback gates. The finance stamp validates cost only. Page 4 remains the source for exception ownership and evidence.",
    )
    _label(document, "Recorded approvals")
    _add_table(document, SIGNOFF_HEADERS, SIGNOFF_ROWS, [1.45, 1.45, 2.85, 1.75], exact_rows=True, row_height=0.4, compact=True)
    _label(document, "Document control")
    _paragraph(
        document,
        "Revision D supersedes Draft C. This authorization became effective at 10 Jul 2026 09:30 MST. The next control event is the first failed condition, completed rollback, or closure of C-3, whichever occurs first.",
    )

    document.save(path)


def _export_with_libreoffice(docx_path: Path, pdf_path: Path, work_dir: Path) -> None:
    soffice = shutil.which("soffice") or "/opt/homebrew/bin/soffice"
    if not Path(soffice).exists():
        raise RuntimeError("LibreOffice soffice is required to generate P23")
    export_dir = work_dir / "export"
    profile_dir = work_dir / "lo-profile"
    export_dir.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({"LC_ALL": "C", "LANG": "C", "TZ": "UTC", "SOURCE_DATE_EPOCH": "1783696200"})
    result = subprocess.run(
        [
            soffice,
            f"-env:UserInstallation={profile_dir.as_uri()}",
            "--headless",
            "--nologo",
            "--nodefault",
            "--nofirststartwizard",
            "--convert-to",
            "pdf:writer_pdf_Export",
            "--outdir",
            str(export_dir),
            str(docx_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
        env=env,
    )
    converted = export_dir / f"{docx_path.stem}.pdf"
    if result.returncode != 0 or not converted.exists():
        raise RuntimeError(
            "LibreOffice PDF export failed: "
            + (result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}")
        )

    normalized = work_dir / "metadata-normalized.pdf"
    reader = PdfReader(str(converted))
    if len(reader.pages) != 5:
        raise ValueError(f"{CASE_ID}: LibreOffice generated {len(reader.pages)} pages; expected 5")
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata(
        {
            "/Title": TITLE,
            "/Author": "Northstar Cold Chain, Regional Operations",
            "/Subject": "Controlled supplier transition file SV-2048",
            "/Creator": "LibreOffice Writer",
            "/Producer": "LibreOffice PDF export",
        }
    )
    with normalized.open("wb") as stream:
        writer.write(stream)

    qpdf = shutil.which("qpdf")
    if not qpdf:
        raise RuntimeError("qpdf is required to normalize P23 deterministically")
    subprocess.run(
        [qpdf, "--deterministic-id", "--object-streams=generate", str(normalized), str(pdf_path)],
        check=True,
        capture_output=True,
        text=True,
    )


GOLD_SECTIONS = {
    1: "1. Regional cold-storage cutover approval",
    2: "2. Cutover workplan and handoff sequence",
    3: "3. Commercial validation and invoice routing",
    4: "4. Exception and closure-evidence register",
    5: "5. Final implementation authorization",
}


def _source_anchor(page: int, label: str, layer: str) -> dict:
    return {
        "page": page,
        "layer": layer,
        "sectionPath": [TITLE, GOLD_SECTIONS[page], label],
    }


def _closed_table(keys: list[str]) -> dict:
    return {"scope": "table_rows", "keys": keys}


def _region(
    region_id: str,
    label: str,
    kind: str,
    leaves: list[dict],
    *,
    primary_axis: str,
    page: int | None = None,
    layer: str = "native_text",
    modality: str | None = None,
    secondary_axes: tuple[str, ...] = (),
    text_only_recoverable: bool = True,
    budget: int = 1,
    unique_evidence: bool = True,
    closed_world: dict | None = None,
    source_anchors: list[dict] | None = None,
    gold_section: str | None = None,
) -> dict:
    if source_anchors is None:
        if page is None:
            raise ValueError(f"{region_id}: page or source_anchors is required")
        source_anchors = [_source_anchor(page, label, layer)]
    primary_page = int(source_anchors[0]["page"])
    region = {
        "id": region_id,
        "label": label,
        "sourceAnchors": source_anchors,
        "goldSection": gold_section or GOLD_SECTIONS[primary_page],
        "kind": kind,
        "modality": modality or layer,
        "uniqueEvidence": unique_evidence,
        "primaryAxis": primary_axis,
        "secondaryAxes": list(secondary_axes),
        "textOnlyRecoverable": text_only_recoverable,
        "budget": budget,
        "leaves": leaves,
    }
    if closed_world is not None:
        region["closedWorld"] = closed_world
    return region


def _regions() -> list[dict]:
    workflow_headers = ["Step", "Owner", "Required review", "Exit record"]
    workflow_rows = [
        ["1", "Cutover lead", "Sequence and operational gates", "Page 2 workplan"],
        ["2", "Finance", "Ceiling, PO, and invoice routing", "Page 3 validation"],
        ["3", "Functional owners", "Exception scope and evidence", "Page 4 register"],
        ["4", "Sponsor and quality", "Selective GO/HOLD authorization", "Page 5 final record"],
    ]
    total_headers = ["Control", "Value", "Interpretation"]
    total_rows = [
        ["Base committed cost", "$25,070", "Implementation, overlap, and sensor validation"],
        ["Conditional contingency", "$3,000", "Usable only while EX-07 extends the overlap"],
        ["Not-to-exceed ceiling", "$28,070", "Requires finance reapproval if exceeded"],
    ]
    note_headers = ["Marker", "Meaning", "Operational consequence"]
    note_rows = [
        ["CLOSED", "Listed evidence was accepted for that row", "No effect on unrelated exceptions"],
        ["OPEN - EXCLUDE", "Affected inventory stays out of the authorized quantity", "Eligible inventory may proceed"],
        ["WATCH", "Monitor and update the stated evidence channel", "Continue unless a final condition fails"],
    ]
    workplan_bindings = {
        ("T-01", "Activity"),
        ("T-02", "Activity"),
        ("T-02", "Gate / evidence"),
        ("T-04", "Activity"),
        ("T-04", "State"),
        ("T-05", "Activity"),
        ("T-05", "Gate / evidence"),
        ("T-06", "Activity"),
        ("T-06", "Gate / evidence"),
        ("T-06", "State"),
    }
    handoff_bindings = {(row[0], "Required content") for row in HANDOFF_ROWS}
    cost_bindings = {(row[0], "Amount") for row in COST_ROWS} | {
        ("Kestrel overlap", "Approval condition"),
        ("Contingency", "Approval condition"),
    }
    total_bindings = {(row[0], "Value") for row in total_rows} | {
        ("Conditional contingency", "Interpretation"),
    }
    invoice_bindings = {(row[0], "PO") for row in INVOICE_ROWS} | {
        ("Boreal Storage", "Route"),
        ("ThermoVision", "Route"),
    }
    exception_bindings = {(row[0], "State") for row in EXCEPTION_ROWS} | {
        ("EX-07", "Affected obligation"),
        ("EX-07", "Accepted closure evidence"),
        ("E-08", "Current finding"),
        ("E-08", "Accepted closure evidence"),
        ("E-11", "Current finding"),
    }
    condition_bindings = {
        (row[0], field)
        for row in CONDITION_ROWS
        for field in ("Required state before action", "Action governed", "Failure response")
    }
    signoff_bindings = {(row[0], "Decision") for row in SIGNOFF_ROWS} | {
        ("Executive sponsor", "Recorded"),
        ("Quality", "Recorded"),
    }
    return [
        _region(
            "p01.control",
            "Document control",
            "table",
            [
                leaf("p01.control.identity", "The controlled file is SV-2048 at Revision D.", evidence=["SV-2048", "Revision", "D"]),
                leaf("p01.control.dates", "SV-2048 was prepared 08 Jul 2026 and became effective 10 Jul 2026 at 09:30 MST.", evidence=["SV-2048", "08 Jul 2026", "10 Jul 2026", "09:30 MST"]),
                leaf("p01.control.scope", "The controlled sites are Phoenix and Tucson, coordinated by Avery Kim.", evidence=["Phoenix", "Tucson", "Avery Kim"]),
            ],
            page=1,
            primary_axis="precise_recall",
            secondary_axes=("table_reconstruction",),
        ),
        _region(
            "p01.request",
            "Change request and scope",
            "text",
            [
                leaf("p01.request.sites", "The transfer covers eligible Phoenix and Tucson inventory."),
                leaf("p01.request.functions", "The change covers telemetry migration, physical custody, invoice routing, and later credential closure."),
                leaf("p01.request.quarantine", "Quarantined inventory remains under Northstar quality control.", harm=2),
            ],
            page=1,
            primary_axis="precise_recall",
        ),
        _region(
            "p01.authority",
            "Record authority and precedence",
            "table",
            [
                source_precedence_leaf(
                    "p01.authority.order",
                    "Source priority is page 5 final authorization, page 4 exception register, page 3 finance validation, page 2 workplan, then reference notes.",
                    ["page 5 final authorization", "page 4", "page 3", "page 2", "reference"],
                ),
                leaf("p01.authority.final", "Page 5 controls GO/HOLD state and release conditions but not individual rate details.", harm=2, evidence=["Page 5", "GO/HOLD", "release conditions", ["but not", "not"], "rate details"]),
                leaf("p01.authority.exceptions", "Page 4 controls exception scope, owner, and closure evidence but not the commercial ceiling.", harm=2, evidence=["Page 4", "exception scope", "closure evidence", ["but not", "not"], "commercial ceiling"]),
                leaf("p01.authority.finance", "Page 3 controls the authorized cost ceiling and invoice route but not operational release.", harm=2, evidence=["Page 3", "cost ceiling", "invoice route", ["but not", "not"], "Operational release"]),
                leaf("p01.authority.workplan", "Page 2 controls task sequence, windows, and task gates but not final authorization.", harm=2, evidence=["Page 2", "Task sequence", "task gates", ["but not", "not"], "Final authorization"]),
                leaf("p01.authority.reference", "Email and meeting notes provide context only when cited and cannot approve or close an item.", evidence=["Email and meeting notes", "Context only", "approval", "closure"]),
                leaf("p01.authority.scope", "A lower-priority record may supply detail but cannot reverse a higher-priority state; closure applies only to the obligation named in an exception row.", harm=2, evidence=["lower-priority", "cannot reverse", "higher-priority", ["only", "solely"], "obligation named"]),
            ],
            page=1,
            primary_axis="source_precedence",
            secondary_axes=("table_reconstruction", "reading_order"),
            budget=3,
            closed_world={"scope": "record_set", "keys": [row[1] for row in AUTHORITY_ROWS]},
        ),
        _region(
            "p01.workflow",
            "Review workflow",
            "structure",
            [
                leaf(
                    "p01.workflow.order",
                    "Review proceeds from cutover lead to finance to functional owners to sponsor and quality.",
                    claim_type="ordered_record",
                    evidence_policy={"type": "ordered_tokens", "tokens": [["Cutover lead"], ["Finance"], ["Functional owners"], ["Sponsor and quality"]]},
                ),
                leaf(
                    "p01.workflow.records",
                    "The workflow exits through page 2 workplan, page 3 validation, page 4 register, then page 5 final record.",
                    claim_type="ordered_record",
                    evidence_policy={"type": "ordered_tokens", "tokens": [["Page 2 workplan"], ["Page 3 validation"], ["Page 4 register"], ["Page 5 final record"]]},
                ),
            ],
            page=1,
            primary_axis="reading_order",
            secondary_axes=("structure_reconstruction",),
        ),
        _region(
            "p02.workplan",
            "Clipped native-layer workplan",
            "table",
            table_leaves(
                "p02.workplan",
                WORKPLAN_HEADERS,
                WORKPLAN_ROWS,
                consequential={("T-02", "Gate / evidence"), ("T-04", "State"), ("T-05", "Activity"), ("T-06", "Gate / evidence"), ("T-06", "State")},
                scored_bindings=workplan_bindings,
            ),
            page=2,
            layer="native_layer_recovery",
            modality="native_layer_recovery",
            primary_axis="native_layer_recovery",
            secondary_axes=("table_reconstruction", "precise_recall", "reading_order"),
            text_only_recoverable=False,
            budget=4,
            closed_world=_closed_table([row[0] for row in WORKPLAN_ROWS]),
        ),
        _region(
            "p02.sidebar",
            "Floating approver sidebar",
            "text",
            [
                leaf("p02.sidebar.access", "Avery Kim's 08 Jul sidebar says to keep Kestrel Dock 4 access active until counsel signs EX-07."),
                leaf("p02.sidebar.advisory", "The sidebar is advisory and says page 5 controls release.", harm=2),
            ],
            page=2,
            primary_axis="precise_recall",
            secondary_axes=("source_precedence",),
        ),
        _region(
            "p02.dependencies",
            "Cross-record dependency interpretation",
            "text",
            [
                leaf("p02.dependencies.t02", "T-02 gates the T-04 transfer of PX-771.", harm=2),
                leaf("p02.dependencies.ex07", "EX-07 blocks T-06 credential closure but does not block physical transfer.", harm=2),
                leaf("p02.dependencies.qa61", "T-05 may move only eligible Tucson stock while six QA-61 cases stay segregated.", harm=2),
            ],
            page=2,
            primary_axis="source_precedence",
            secondary_axes=("cross_page_join",),
            budget=3,
        ),
        _region(
            "p02.reading-order",
            "Recovered page-two reading order",
            "structure",
            [
                leaf(
                    "p02.reading-order.sections",
                    "Reconstruct the logical order: workplan table, approver sidebar, dependency interpretation, handoff matrix, then rollback trigger.",
                    harm=2,
                    claim_type="ordered_record",
                    evidence_policy={"type": "ordered_tokens", "tokens": [["T-01"], ["Approver sidebar"], ["T-02 gates"], ["Handoff matrix"], ["RB-12"]]},
                )
            ],
            page=2,
            layer="native_layer_recovery",
            modality="native_layer_recovery",
            primary_axis="reading_order",
            secondary_axes=("native_layer_recovery", "structure_reconstruction"),
            text_only_recoverable=False,
            budget=2,
        ),
        _region(
            "p02.handoff",
            "Handoff matrix",
            "table",
            table_leaves(
                "p02.handoff",
                HANDOFF_HEADERS,
                HANDOFF_ROWS,
                consequential={("Any temperature breach", "Required content"), ("Rollback invoked", "Required content")},
                scored_bindings=handoff_bindings,
            ),
            page=2,
            primary_axis="table_reconstruction",
            secondary_axes=("precise_recall",),
            closed_world=_closed_table([row[0] for row in HANDOFF_ROWS]),
        ),
        _region(
            "p02.rollback",
            "Rollback trigger",
            "text",
            [
                leaf("p02.rollback.threshold", "RB-12 is invoked for a temperature deviation above 1.0 C lasting 10 continuous minutes.", harm=2),
                leaf("p02.rollback.actions", "Rollback stops the active transfer and preserves custody at the last confirmed location.", harm=2),
                leaf("p02.rollback.report", "The last completed task must be reported on bridge BR-2048."),
            ],
            page=2,
            primary_axis="precise_recall",
            secondary_axes=("long_context_coherence",),
            budget=2,
        ),
        _region(
            "p03.cost",
            "Authorized cost build",
            "table",
            table_leaves(
                "p03.cost",
                COST_HEADERS,
                COST_ROWS,
                consequential={("Contingency", "Approval condition")},
                scored_bindings=cost_bindings,
            ),
            page=3,
            primary_axis="table_reconstruction",
            secondary_axes=("precise_recall",),
            budget=2,
            closed_world=_closed_table([row[0] for row in COST_ROWS]),
        ),
        _region(
            "p03.total",
            "Cost controls",
            "table",
            table_leaves(
                "p03.total",
                total_headers,
                total_rows,
                consequential={("Conditional contingency", "Interpretation"), ("Not-to-exceed ceiling", "Value")},
                scored_bindings=total_bindings,
            ),
            page=3,
            primary_axis="precise_recall",
            secondary_axes=("table_reconstruction",),
            budget=2,
            closed_world=_closed_table([row[0] for row in total_rows]),
        ),
        _region(
            "p03.invoice",
            "Invoice route",
            "table",
            table_leaves("p03.invoice", INVOICE_HEADERS, INVOICE_ROWS, scored_bindings=invoice_bindings),
            page=3,
            primary_axis="table_reconstruction",
            secondary_axes=("precise_recall",),
            closed_world=_closed_table([row[0] for row in INVOICE_ROWS]),
        ),
        _region(
            "p03.scope",
            "Finance scope",
            "text",
            [
                leaf("p03.scope.validation", "Finance validates the cost ceiling and invoice route."),
                leaf("p03.scope.no-release", "Finance does not close exceptions, satisfy task gates, or authorize physical release.", harm=2),
                leaf("p03.scope.contingency", "Unused contingency is not committed spend."),
            ],
            page=3,
            primary_axis="source_precedence",
            secondary_axes=("precise_recall",),
            budget=2,
        ),
        _region(
            "p03.stamp",
            "Raster finance validation stamp",
            "image",
            [
                visual_leaf("p03.stamp.signer-time", "The finance-validation stamp records Jonah Mercer on 09 Jul 2026 at 16:42 MST.", ["Jonah Mercer", "09 Jul 2026", "16:42 MST"]),
                visual_leaf("p03.stamp.control", "The finance-validation stamp names control VC-2048.", ["VC-2048"]),
                visual_leaf("p03.stamp.scope", "The finance-validation stamp says cost validation is not operational release.", ["COST VALIDATION", "NOT OPERATIONAL RELEASE"], harm=2),
            ],
            page=3,
            layer="raster",
            modality="raster",
            primary_axis="image_description",
            secondary_axes=("mixed_modality_fusion", "precise_recall"),
            text_only_recoverable=False,
            budget=2,
        ),
        _region(
            "p04.exceptions",
            "Landscape exception register",
            "table",
            table_leaves(
                "p04.exceptions",
                EXCEPTION_HEADERS,
                EXCEPTION_ROWS,
                consequential={("EX-07", "Affected obligation"), ("EX-07", "Accepted closure evidence"), ("EX-07", "State"), ("E-08", "Current finding"), ("E-08", "State")},
                scored_bindings=exception_bindings,
            ),
            page=4,
            primary_axis="source_precedence",
            secondary_axes=("table_reconstruction", "precise_recall"),
            budget=4,
            closed_world=_closed_table([row[0] for row in EXCEPTION_ROWS]),
        ),
        _region(
            "p04.notes",
            "Register state semantics",
            "table",
            [
                leaf("p04.notes.closed", "CLOSED means listed evidence was accepted for that row and has no effect on unrelated exceptions.", evidence=["CLOSED", "accepted", "No effect", "unrelated exceptions"]),
                leaf("p04.notes.exclude", "OPEN - EXCLUDE keeps affected inventory out while eligible inventory may proceed.", harm=2, evidence=["OPEN - EXCLUDE", "Affected inventory", "Eligible inventory may proceed"]),
                leaf("p04.notes.watch", "WATCH requires monitoring the evidence channel and continues unless a final condition fails.", evidence=["WATCH", "evidence channel", "Continue", "final condition fails"]),
            ],
            page=4,
            primary_axis="source_precedence",
            secondary_axes=("table_reconstruction",),
            closed_world={"scope": "record_set", "keys": [row[0] for row in note_rows]},
        ),
        _region(
            "p04.scope",
            "Exception scope and authority note",
            "text",
            [
                leaf("p04.scope.closed", "A closed row has no effect on unrelated exceptions.", harm=2),
                leaf("p04.scope.email", "Email acknowledgment is context unless the relevant row cites it as accepted evidence."),
                leaf("p04.scope.sources", "Page 5 controls GO/HOLD state while page 3 finance validation controls cost only.", harm=2),
            ],
            page=4,
            primary_axis="source_precedence",
            secondary_axes=("cross_page_join",),
            budget=2,
        ),
        _region(
            "p05.decision",
            "Final selective authorization",
            "text",
            [
                leaf("p05.decision.go", "Physical cutover is GO beginning 14 Jul 2026 at 22:00 MST for eligible inventory only.", harm=2),
                leaf("p05.decision.hold", "Kestrel credential decommission remains HOLD until condition C-3 is satisfied.", harm=2),
            ],
            page=5,
            primary_axis="source_precedence",
            secondary_axes=("precise_recall", "summarization_coverage"),
            budget=4,
        ),
        _region(
            "p05.conditions",
            "Release conditions",
            "table",
            table_leaves(
                "p05.conditions",
                CONDITION_HEADERS,
                CONDITION_ROWS,
                consequential={("C-1", "Required state before action"), ("C-3", "Required state before action"), ("C-4", "Failure response")},
                scored_bindings=condition_bindings,
            ),
            page=5,
            primary_axis="table_reconstruction",
            secondary_axes=("source_precedence", "precise_recall"),
            budget=4,
            closed_world=_closed_table([row[0] for row in CONDITION_ROWS]),
        ),
        _region(
            "p05.interpretation",
            "Authorization interpretation",
            "text",
            [
                leaf("p05.interpretation.ex07", "The GO decision does not close EX-07.", harm=2),
                leaf("p05.interpretation.qa61", "The GO decision does not release the six QA-61 cases.", harm=2),
                leaf("p05.interpretation.gates", "The GO decision does not waive telemetry or rollback gates.", harm=2),
                leaf("p05.interpretation.sources", "Page 4 remains the source for exception ownership and closure evidence."),
            ],
            page=5,
            primary_axis="source_precedence",
            secondary_axes=("summarization_coverage",),
            budget=2,
        ),
        _region(
            "p05.signoff",
            "Recorded approvals",
            "table",
            table_leaves(
                "p05.signoff",
                SIGNOFF_HEADERS,
                SIGNOFF_ROWS,
                consequential={("Legal exception owner", "Decision"), ("Quality", "Decision")},
                scored_bindings=signoff_bindings,
            ),
            page=5,
            primary_axis="precise_recall",
            secondary_axes=("table_reconstruction", "source_precedence"),
            budget=2,
            closed_world=_closed_table([row[0] for row in SIGNOFF_ROWS]),
        ),
        _region(
            "p05.control",
            "Final document control",
            "text",
            [
                leaf("p05.control.revision", "Revision D supersedes Draft C."),
                leaf("p05.control.effective", "The authorization became effective at 10 Jul 2026 09:30 MST."),
                leaf("p05.control.event", "The next control event is the first failed condition, completed rollback, or closure of C-3."),
            ],
            page=5,
            primary_axis="precise_recall",
            secondary_axes=("long_context_coherence",),
        ),
        _region(
            "x01.selective-release",
            "Cross-page selective-release synthesis",
            "mixed",
            [
                leaf(
                    "x01.selective-release.physical",
                    "Physical cutover is GO only for eligible inventory and still requires the T-02 and T-04 telemetry gate and the T-05 QA-61 exclusion.",
                    harm=2,
                    claim_type="cross_page_join",
                    evidence=["Physical cutover", "GO", ["only", "solely"], "eligible inventory", "T-02", "T-04", "T-05", "QA-61"],
                ),
                leaf(
                    "x01.selective-release.credentials",
                    "Kestrel credential closure remains HOLD because T-06 and C-3 require both signed EX-07 and zero unresolved REC-2048 items.",
                    harm=2,
                    claim_type="cross_page_join",
                    evidence=["Kestrel", "HOLD", "T-06", "C-3", "signed EX-07", "REC-2048", "zero unresolved"],
                ),
                leaf(
                    "x01.selective-release.finance",
                    "Finance validation and its stamp authorize cost only; they cannot close an exception, satisfy a task gate, or override the final release state.",
                    harm=2,
                    claim_type="cross_page_join",
                    evidence=["finance validation", "stamp", "cost", ["only", "solely"], "cannot", "exception", "task gate", "final release"],
                ),
            ],
            primary_axis="long_context_coherence",
            secondary_axes=("cross_page_join", "source_precedence", "mixed_modality_fusion"),
            modality="mixed",
            text_only_recoverable=False,
            budget=4,
            unique_evidence=False,
            source_anchors=[
                _source_anchor(1, "Record authority and precedence", "native_text"),
                _source_anchor(2, "Clipped native-layer workplan", "native_layer_recovery"),
                _source_anchor(3, "Finance scope", "native_text"),
                _source_anchor(3, "Raster finance validation stamp", "raster"),
                _source_anchor(4, "Landscape exception register", "native_text"),
                _source_anchor(5, "Final selective authorization", "native_text"),
            ],
            gold_section=GOLD_SECTIONS[5],
        ),
    ]


def _gold() -> str:
    workflow_headers = ["Step", "Owner", "Required review", "Exit record"]
    workflow_rows = [
        ["1", "Cutover lead", "Sequence and operational gates", "Page 2 workplan"],
        ["2", "Finance", "Ceiling, PO, and invoice routing", "Page 3 validation"],
        ["3", "Functional owners", "Exception scope and evidence", "Page 4 register"],
        ["4", "Sponsor and quality", "Selective GO/HOLD authorization", "Page 5 final record"],
    ]
    total_headers = ["Control", "Value", "Interpretation"]
    total_rows = [
        ["Base committed cost", "$25,070", "Implementation, overlap, and sensor validation"],
        ["Conditional contingency", "$3,000", "Usable only while EX-07 extends the overlap"],
        ["Not-to-exceed ceiling", "$28,070", "Requires finance reapproval if exceeded"],
    ]
    note_headers = ["Marker", "Meaning", "Operational consequence"]
    note_rows = [
        ["CLOSED", "Listed evidence was accepted for that row", "No effect on unrelated exceptions"],
        ["OPEN - EXCLUDE", "Affected inventory stays out of the authorized quantity", "Eligible inventory may proceed"],
        ["WATCH", "Monitor and update the stated evidence channel", "Continue unless a final condition fails"],
    ]
    return (
        f"# {TITLE}\n\n"
        "## 1. Regional cold-storage cutover approval\n\n"
        + markdown_table(CONTROL_HEADERS, CONTROL_ROWS)
        + "\n\nNorthstar will transfer eligible Phoenix and Tucson inventory from Kestrel Logistics to Boreal Storage during the 14-15 July maintenance window. The change includes telemetry migration, physical custody transfer, invoice routing, and eventual closure of Kestrel credentials. Quarantined inventory remains under Northstar quality control.\n\n"
        + markdown_table(AUTHORITY_HEADERS, AUTHORITY_ROWS)
        + "\n\nA lower-priority record may supply detail but cannot reverse a higher-priority state. Closure applies only to the obligation named in the exception row. SV-2048 was prepared 08 Jul 2026 and became effective 10 Jul 2026 at 09:30 MST.\n\n"
        + markdown_table(workflow_headers, workflow_rows)
        + "\n\n## 2. Cutover workplan and handoff sequence\n\n"
        + markdown_table(WORKPLAN_HEADERS, WORKPLAN_ROWS)
        + "\n\nApprover sidebar, 08 Jul - Avery Kim: keep Kestrel Dock 4 access active until counsel signs EX-07. This margin note is advisory; page 5 controls release.\n\n"
        "T-02 gates the PX-771 transfer in T-04. EX-07 does not block physical transfer; it blocks T-06 credential closure. T-05 may move only eligible Tucson stock while the six QA-61 cases remain segregated.\n\n"
        "**Handoff matrix**\n\n"
        + markdown_table(HANDOFF_HEADERS, HANDOFF_ROWS)
        + "\n\nInvoke RB-12 if a temperature deviation exceeds 1.0 C for 10 continuous minutes. Stop the active transfer, preserve custody at the last confirmed location, and report the last completed task on bridge BR-2048.\n\n"
        "## 3. Commercial validation and invoice routing\n\n"
        + markdown_table(COST_HEADERS, COST_ROWS)
        + "\n\n"
        + markdown_table(total_headers, total_rows)
        + "\n\n"
        + markdown_table(INVOICE_HEADERS, INVOICE_ROWS)
        + "\n\nFinance validates the ceiling and invoice route. It does not declare an exception closed, satisfy a task gate, or authorize physical release. Unused contingency is not committed spend.\n\n"
        "Raster finance stamp: Jonah Mercer; 09 Jul 2026 16:42 MST; ceiling $28,070; control VC-2048; cost validation is not operational release.\n\n"
        "## 4. Exception and closure-evidence register\n\n"
        + markdown_table(EXCEPTION_HEADERS, EXCEPTION_ROWS)
        + "\n\n"
        + markdown_table(note_headers, note_rows)
        + "\n\nEmail acknowledgment is context only unless the relevant row cites it as accepted evidence. The signed page 5 authorization controls GO/HOLD state; the finance validation controls cost only.\n\n"
        "## 5. Final implementation authorization\n\n"
        "**PHYSICAL CUTOVER: GO.** Begin at 14 Jul 2026 22:00 MST for eligible inventory only. **KESTREL CREDENTIAL DECOMMISSION: HOLD** until C-3 is satisfied.\n\n"
        + markdown_table(CONDITION_HEADERS, CONDITION_ROWS)
        + "\n\nThe GO decision permits the physical cutover; it does not close EX-07, release the six QA-61 cases, or waive telemetry and rollback gates. Kestrel credential closure remains HOLD because T-06 and C-3 require both signed EX-07 and zero unresolved REC-2048 items. Finance validation and its stamp authorize cost only; they cannot close an exception, satisfy a task gate, or override the final release state. Page 4 remains the source for exception ownership and evidence.\n\n"
        + markdown_table(SIGNOFF_HEADERS, SIGNOFF_ROWS)
        + "\n\nRevision D supersedes Draft C. This authorization became effective at 10 Jul 2026 09:30 MST. The next control event is the first failed condition, completed rollback, or closure of C-3, whichever occurs first.\n"
    )


def build(output_root):
    output_root = Path(output_root).resolve()
    case_dir = output_root / "cases" / CASE_ID
    case_dir.mkdir(parents=True, exist_ok=True)
    source_pdf = case_dir / "source.pdf"
    with tempfile.TemporaryDirectory(prefix="p23-office-export-") as temp_name:
        work_dir = Path(temp_name)
        docx_path = work_dir / "northstar-supplier-transition-sv-2048.docx"
        stamp_path = work_dir / "finance-validation.png"
        _finance_stamp(stamp_path)
        _build_docx(docx_path, stamp_path)
        _export_with_libreoffice(docx_path, source_pdf, work_dir)

    regions = _regions()
    gold = _gold()
    finalize_fact_regions(regions, gold)
    (case_dir / "gold.md").write_text(gold, encoding="utf-8")
    (case_dir / "facts.json").write_text(
        json.dumps(
            {
                "schemaVersion": 3,
                "id": CASE_ID,
                "title": TITLE,
                "family": FAMILY,
                "tags": TAGS,
                "regions": regions,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (case_dir / "spec.md").write_text(
        f"# {TITLE}\n\n"
        "Source modality: five-page DOCX exported through LibreOffice to a native PDF. Four pages contain native text only; the finance page also contains one raster validation stamp.\n\n"
        f"Family: `{FAMILY}`\n\n"
        "Purpose: recover a realistic office workflow when fixed-height table rows, a wrapped floating reviewer sidebar, and portrait/landscape section conversion leave legitimate native text clipped and displaced in the visible export.\n\n"
        "The source PDF contains the office export's own text and image objects. Container normalization changes metadata and serialization only; it does not add, hide, or replace page content.\n\n"
        "Tags: "
        + ", ".join(f"`{tag}`" for tag in TAGS)
        + "\n",
        encoding="utf-8",
    )

    prefix = output_root.relative_to(REPO_ROOT).as_posix()
    base = f"{prefix}/cases/{CASE_ID}"
    return {
        "id": CASE_ID,
        "title": TITLE,
        "family": FAMILY,
        "tags": TAGS,
        "pages": 5,
        "pdf": f"{base}/source.pdf",
        "gold": f"{base}/gold.md",
        "spec": f"{base}/spec.md",
        "facts": f"{base}/facts.json",
    }
