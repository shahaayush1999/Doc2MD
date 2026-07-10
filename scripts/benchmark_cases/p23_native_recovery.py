from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter

from .common import REPO_ROOT, leaf, markdown_table, table_leaves


CASE_ID = "P23-native-text-layer-recovery"
TITLE = "West Region Logistics Exception Control Packet"
FAMILY = "office export recovery"
TAGS = [
    "native-pdf",
    "libreoffice-export",
    "malformed-layout",
    "native-text-recovery",
    "tables",
    "source-precedence",
]


DECISION_HEADERS = ["ID", "Scope", "Disposition", "Owner", "Due"]
DECISION_ROWS = [
    ["D-17", "Reno consolidation", "HOLD — dock crew exception", "Ravi Mehta", "12 Jul 16:00 PT"],
    ["D-18", "Boise overflow", "APPROVE — cross-dock slot B7", "Lena Ortiz", "09 Jul"],
    ["D-19", "Tacoma weekend linehaul", "RETAIN — current carrier allocation", "Mira Chen", "11 Jul"],
]

LANE_HEADERS = ["Lane", "Pallets", "Constraint", "State", "Control / next gate"]
LANE_ROWS = [
    ["Reno → SFO", "41", "Dock crew short by 3", "BLOCKED", "Ravi closes D-17"],
    ["Boise → SEA", "18", "Overflow slot B7", "RELEASED", "Cutoff 09 Jul 18:00"],
    ["Tacoma → PDX", "27", "Carrier capacity tight", "WATCH", "Confirm 11 Jul 10:00"],
    ["Spokane → SEA", "12", "None", "CLEAR", "No action"],
]

RESERVE_HEADERS = ["Reserve line", "Amount", "Eligibility", "Control basis"]
RESERVE_ROWS = [
    ["Temporary slot B7", "$2,400", "Eligible", "Approval LO-551"],
    ["Reno labor standby", "$3,850", "Conditional", "Only if D-17 extends past 12 Jul 16:00 PT"],
    ["Tacoma weekend premium", "$1,175", "Not eligible", "Existing carrier allocation retained"],
]

SIGNOFF_HEADERS = ["Role", "Name", "State", "Timestamp"]
SIGNOFF_ROWS = [
    ["Operations", "Lena Ortiz", "Approved", "10 Jul 15:05 PT"],
    ["Finance", "M. Okafor", "Concurred", "10 Jul 14:18 PT"],
    ["Exception owner", "Ravi Mehta", "Open — not signed", "Next review 12 Jul 16:00 PT"],
    ["Document control", "S. Bell", "Revision 3 effective", "10 Jul 15:10 PT"],
]


def _set_repeat_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    tr_pr.append(repeat)


def _set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def _set_cell_margins(cell, *, top: int = 45, start: int = 55, bottom: int = 45, end: int = 55) -> None:
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


def _set_table_fixed(table) -> None:
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
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
    for edge in ("top", "left", "bottom", "right", "insideH"):
        node = OxmlElement(f"w:{edge}")
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), "3")
        node.set(qn("w:color"), "B7BDC3")
        borders.append(node)
    inside_v = OxmlElement("w:insideV")
    inside_v.set(qn("w:val"), "nil")
    borders.append(inside_v)


def _write_cell(cell, value: str, *, header: bool, compressed: bool) -> None:
    cell.text = ""
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    _set_cell_margins(cell, top=28 if compressed else 48, bottom=24 if compressed else 48)
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = Pt(5.7 if compressed else 9.7)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    lines = str(value).split("\n")
    for index, line in enumerate(lines):
        if index:
            run = paragraph.add_run()
            run.add_break()
        run = paragraph.add_run(line)
        run.bold = header
        run.font.name = "Verdana"
        run.font.size = Pt(7.4 if compressed else 7.8)
        run.font.color.rgb = RGBColor(25, 31, 36)


def _add_table(document: Document, headers, rows, widths, *, compressed: bool = False):
    table = document.add_table(rows=1, cols=len(headers))
    _set_table_fixed(table)
    header = table.rows[0]
    header.height = Inches(0.27)
    header.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    _set_repeat_header(header)
    for index, (cell, text, width) in enumerate(zip(header.cells, headers, widths, strict=True)):
        cell.width = Inches(width)
        _set_cell_shading(cell, "DDE3E8")
        _write_cell(cell, str(text), header=True, compressed=False)
    for row_index, values in enumerate(rows):
        row = table.add_row()
        row.height = Inches(0.24 if compressed else 0.38)
        row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
        for cell, value, width in zip(row.cells, values, widths, strict=True):
            cell.width = Inches(width)
            if row_index % 2:
                _set_cell_shading(cell, "F3F4F4")
            _write_cell(cell, str(value), header=False, compressed=compressed)
    return table


def _set_keep_with_next(paragraph, value: bool = True) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    keep = p_pr.find(qn("w:keepNext"))
    if value and keep is None:
        keep = OxmlElement("w:keepNext")
        p_pr.append(keep)
    elif not value and keep is not None:
        p_pr.remove(keep)


def _label(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(7)
    paragraph.paragraph_format.space_after = Pt(3)
    _set_keep_with_next(paragraph)
    run = paragraph.add_run(text.upper())
    run.bold = True
    run.font.name = "Verdana"
    run.font.size = Pt(6.6)
    run.font.color.rgb = RGBColor(75, 86, 96)


def _paragraph(document: Document, text: str, *, size: float = 8.6, bold: bool = False) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(4)
    paragraph.paragraph_format.line_spacing = Pt(size + 2.4)
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.name = "Verdana"
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor(25, 31, 36)


def _page_title(document: Document, page: int, title: str, status: str) -> None:
    banner = document.add_table(rows=1, cols=2)
    banner.alignment = WD_TABLE_ALIGNMENT.LEFT
    banner.autofit = False
    banner.columns[0].width = Inches(5.9)
    banner.columns[1].width = Inches(1.65)
    for cell in banner.rows[0].cells:
        _set_cell_margins(cell, top=15, bottom=15, start=0, end=0)
    left = banner.cell(0, 0).paragraphs[0]
    left.paragraph_format.space_after = Pt(0)
    run = left.add_run("WEST REGION LOGISTICS / OR-7712")
    run.bold = True
    run.font.name = "Verdana"
    run.font.size = Pt(6.5)
    run.font.color.rgb = RGBColor(69, 80, 90)
    right = banner.cell(0, 1).paragraphs[0]
    right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    right.paragraph_format.space_after = Pt(0)
    run = right.add_run(f"{status}  ·  {page} / 4")
    run.bold = True
    run.font.name = "Verdana"
    run.font.size = Pt(6.5)
    run.font.color.rgb = RGBColor(105, 46, 43)
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(5)
    paragraph.paragraph_format.space_after = Pt(4)
    run = paragraph.add_run(title)
    run.bold = True
    run.font.name = "Verdana"
    run.font.size = Pt(17)
    run.font.color.rgb = RGBColor(23, 32, 42)
    rule = document.add_paragraph()
    rule.paragraph_format.space_after = Pt(3)
    run = rule.add_run("━" * 74)
    run.font.name = "Verdana"
    run.font.size = Pt(5.6)
    run.font.color.rgb = RGBColor(176, 184, 191)


def _add_control_rail(document: Document, lines: list[str]) -> None:
    """Add a floating control rail that LibreOffice displaces over body content.

    Word's table-positioning properties and exact-height body rows interact poorly
    in Writer's PDF filter. The resulting overlap is the intended, genuine office
    conversion failure; all affected strings remain ordinary document text.
    """
    table = document.add_table(rows=len(lines), cols=1)
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.RIGHT
    table.columns[0].width = Inches(1.38)
    tbl_pr = table._tbl.tblPr
    position = OxmlElement("w:tblpPr")
    position.set(qn("w:leftFromText"), "80")
    position.set(qn("w:rightFromText"), "80")
    position.set(qn("w:topFromText"), "80")
    position.set(qn("w:bottomFromText"), "80")
    position.set(qn("w:vertAnchor"), "page")
    position.set(qn("w:horzAnchor"), "page")
    position.set(qn("w:tblpX"), "9100")
    position.set(qn("w:tblpY"), "2450")
    position.set(qn("w:tblpXSpec"), "center")
    tbl_pr.append(position)
    for index, (row, text) in enumerate(zip(table.rows, lines, strict=True)):
        row.height = Inches(0.28)
        row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
        cell = row.cells[0]
        _set_cell_shading(cell, "E2E5E7" if index else "BFC7CE")
        _write_cell(cell, text, header=index == 0, compressed=True)


def _approval_stamp(path: Path) -> None:
    image = Image.new("RGBA", (760, 250), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    color = (46, 100, 74, 235)
    draw.rounded_rectangle((15, 15, 745, 235), radius=22, outline=color, width=8)
    draw.line((35, 82, 725, 82), fill=color, width=4)
    font = ImageFont.load_default(size=34)
    small = ImageFont.load_default(size=25)
    draw.text((42, 34), "FINANCE CONCURRENCE", font=font, fill=color)
    draw.text((42, 102), "M. OKAFOR / 10 JUL 2026 / 14:18 PT", font=small, fill=color)
    draw.text((42, 153), "RESERVE CONTROL LO-551", font=small, fill=color)
    image.save(path, format="PNG", optimize=True)


def _configure_document(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.38)
    section.bottom_margin = Inches(0.38)
    section.left_margin = Inches(0.46)
    section.right_margin = Inches(0.46)
    section.header_distance = Inches(0.15)
    section.footer_distance = Inches(0.15)
    normal = document.styles["Normal"]
    normal.font.name = "Verdana"
    normal.font.size = Pt(8.4)
    normal.paragraph_format.space_after = Pt(0)
    document.core_properties.title = TITLE
    document.core_properties.subject = "Operating exception control packet OR-7712"
    document.core_properties.author = "West Region Logistics Document Control"
    document.core_properties.keywords = "OR-7712, logistics, exception control"
    document.core_properties.created = datetime(2026, 7, 10, 15, 10, tzinfo=timezone.utc)
    document.core_properties.modified = datetime(2026, 7, 10, 15, 10, tzinfo=timezone.utc)


def _build_docx(path: Path, stamp_path: Path) -> None:
    document = Document()
    _configure_document(document)

    _page_title(document, 1, "Operating exception memo", "REV 03")
    _label(document, "Control fields")
    control_headers = ["Memo field", "Memo value", "Linked field", "Linked value"]
    control_rows = [
        ["Prepared", "10 Jul 2026", "Coordinator", "Lena Ortiz"],
        ["Review window", "Through 12 Jul 16:00 PT", "Region", "West"],
        ["Scope", "Cross-dock and linehaul exceptions", "Record", "OR-7712"],
    ]
    _add_table(document, control_headers, control_rows, [0.9, 2.15, 1.15, 3.25])
    _label(document, "Operating note")
    _paragraph(document, "Network planning opened OR-7712 after Reno dock staffing fell three crew positions below the consolidation plan. Boise overflow capacity and Tacoma weekend allocation are controlled separately; no blanket regional stop was issued.")
    _label(document, "Decision register")
    broken_decisions = [
        [row[0], row[1], row[2].replace(" — ", "\n"), row[3], row[4]] for row in DECISION_ROWS
    ]
    _add_table(document, DECISION_HEADERS, broken_decisions, [0.55, 1.55, 2.25, 1.35, 1.65], compressed=True)
    _add_control_rail(document, ["CONTROL", "REV 03", "WEST", "OR-7712"])
    _label(document, "Routing")
    _paragraph(document, "Distribute to network planning, Reno operations, transportation, and finance. D-17 is the only open blocking decision.")
    document.add_page_break()

    _page_title(document, 2, "Lane risk register", "CONTROLLED")
    _label(document, "Lane state at 10 Jul 15:00 PT")
    broken_lanes = [
        [row[0], row[1], row[2].replace(" by ", "\nby "), row[3], row[4].replace(" ", "\n", 1)]
        for row in LANE_ROWS
    ]
    _add_table(document, LANE_HEADERS, broken_lanes, [1.15, 0.7, 2.0, 1.0, 2.5], compressed=True)
    _add_control_rail(document, ["LANE GRID", "10 JUL", "15:00 PT", "REV 03"])
    _label(document, "Local controls")
    local_headers = ["Location", "Release authority", "Evidence", "Limit"]
    local_rows = [
        ["Reno", "Ravi Mehta", "Crew roster RC-118", "No outbound consolidation"],
        ["Boise", "Lena Ortiz", "Slot approval LO-551", "18 pallets / B7 only"],
        ["Tacoma", "Mira Chen", "Carrier note TC-49", "Existing allocation"],
        ["Spokane", "Dispatch desk", "Daily plan SP-210", "Standard cutoff"],
    ]
    _add_table(document, local_headers, local_rows, [1.2, 1.55, 2.1, 2.5])
    _label(document, "Sequence note")
    _paragraph(document, "Boise may release independently. Tacoma remains on watch without reserve eligibility. Spokane remains clear. Reno may not consolidate until the D-17 exception owner records closure.")
    document.add_page_break()

    _page_title(document, 3, "Cost reserve authorization", "FINANCE")
    _label(document, "Reserve ledger")
    broken_reserves = [
        [row[0], row[1], row[2], row[3].replace(" ", "\n", 2)] for row in RESERVE_ROWS
    ]
    _add_table(document, RESERVE_HEADERS, broken_reserves, [2.0, 1.0, 1.35, 3.0], compressed=True)
    _add_control_rail(document, ["RESERVE", "LO-551", "FINANCE", "REV 03"])
    _label(document, "Authorized reserve scenarios")
    scenario_headers = ["Scenario", "Eligible reserve", "Included lines"]
    scenario_rows = [
        ["D-17 closes by 12 Jul 16:00 PT", "$2,400", "Temporary slot B7"],
        ["D-17 remains open after 12 Jul 16:00 PT", "$6,250", "Slot B7 + Reno labor standby"],
    ]
    _add_table(document, scenario_headers, scenario_rows, [3.15, 1.35, 2.85])
    _label(document, "Finance annotation")
    _paragraph(document, "Tacoma weekend premium is excluded because D-19 retains the existing carrier allocation. Labor standby becomes eligible only after the D-17 deadline passes while the hold remains open.")
    document.add_picture(str(stamp_path), width=Inches(3.65))
    document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    document.add_page_break()

    _page_title(document, 4, "Controlling disposition and signoff", "FINAL")
    _label(document, "Controlling statement")
    statement = "Reno outbound consolidation remains ON HOLD until Ravi Mehta closes the D-17 dock staffing exception."
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(3)
    paragraph.paragraph_format.space_after = Pt(9)
    paragraph.paragraph_format.left_indent = Inches(0.18)
    paragraph.paragraph_format.right_indent = Inches(0.18)
    paragraph.paragraph_format.line_spacing = Pt(17)
    run = paragraph.add_run(statement)
    run.bold = True
    run.font.name = "Verdana"
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(120, 39, 36)
    _label(document, "Signoff register")
    _add_table(document, SIGNOFF_HEADERS, SIGNOFF_ROWS, [1.45, 1.55, 2.1, 2.25])
    _add_control_rail(document, ["FINAL", "REV 03", "EFFECTIVE", "15:10 PT"])
    _label(document, "State interpretation")
    _paragraph(document, "Finance concurrence authorizes the reserve; it does not release Reno. Operations approval establishes the packet. Ravi Mehta's row remains open and unsigned, so the controlling statement remains in force.")
    _label(document, "Document control")
    _paragraph(document, "Revision 3 supersedes Revision 2 at 10 Jul 2026 15:10 PT. Next review: 12 Jul 2026 16:00 PT. Retention class: operations exception / seven years.")

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
    env.update(
        {
            "LC_ALL": "C",
            "LANG": "C",
            "TZ": "UTC",
            "SOURCE_DATE_EPOCH": "1783696200",
        }
    )
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

    normalized = work_dir / "normalized.pdf"
    reader = PdfReader(str(converted))
    if len(reader.pages) != 4:
        raise ValueError(f"{CASE_ID}: LibreOffice generated {len(reader.pages)} pages; expected 4")
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata(
        {
            "/Title": TITLE,
            "/Author": "West Region Logistics Document Control",
            "/Subject": "Operating exception control packet OR-7712",
            "/Creator": "LibreOffice Writer office export",
            "/Producer": "LibreOffice PDF filter; normalized by Doc2MD generator",
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


def _regions() -> list[dict]:
    def region(region_id, page, label, kind, leaves, *, budget=1, closed_world=False):
        return {
            "id": region_id,
            "page": page,
            "label": label,
            "kind": kind,
            "budget": budget,
            "closedWorld": closed_world,
            "leaves": leaves,
        }

    control_headers = ["Memo field", "Memo value", "Linked field", "Linked value"]
    control_rows = [
        ["Prepared", "10 Jul 2026", "Coordinator", "Lena Ortiz"],
        ["Review window", "Through 12 Jul 16:00 PT", "Region", "West"],
        ["Scope", "Cross-dock and linehaul exceptions", "Record", "OR-7712"],
    ]
    local_headers = ["Location", "Release authority", "Evidence", "Limit"]
    local_rows = [
        ["Reno", "Ravi Mehta", "Crew roster RC-118", "No outbound consolidation"],
        ["Boise", "Lena Ortiz", "Slot approval LO-551", "18 pallets / B7 only"],
        ["Tacoma", "Mira Chen", "Carrier note TC-49", "Existing allocation"],
        ["Spokane", "Dispatch desk", "Daily plan SP-210", "Standard cutoff"],
    ]
    scenario_headers = ["Scenario", "Eligible reserve", "Included lines"]
    scenario_rows = [
        ["D-17 closes by 12 Jul 16:00 PT", "$2,400", "Temporary slot B7"],
        ["D-17 remains open after 12 Jul 16:00 PT", "$6,250", "Slot B7 + Reno labor standby"],
    ]
    return [
        region("p01.control", 1, "Memo control fields", "table", table_leaves("p01.control", control_headers, control_rows), closed_world=True),
        region("p01.note", 1, "Operating note", "text", [
            leaf("p01.note.trigger", "OR-7712 opened because Reno dock staffing was three crew positions below plan."),
            leaf(
                "p01.note.scope.local-controls",
                "Boise overflow capacity and Tacoma weekend allocation are separately controlled.",
            ),
            leaf("p01.note.scope.regional-stop", "No blanket regional stop was issued."),
        ]),
        region("p01.decisions", 1, "Decision register", "table", table_leaves("p01.decisions", DECISION_HEADERS, DECISION_ROWS, consequential={("D-17", "Disposition"), ("D-17", "Owner")}), budget=2, closed_world=True),
        region("p01.routing", 1, "Memo routing", "text", [
            leaf(
                "p01.routing.audience",
                "The memo routes to network planning, Reno operations, transportation, and finance.",
                allow_partial=True,
            ),
            leaf("p01.routing.blocker", "D-17 is the only open blocking decision.", harm=2),
        ]),
        region("p02.lanes", 2, "Lane risk register", "table", table_leaves("p02.lanes", LANE_HEADERS, LANE_ROWS, consequential={("Reno → SFO", "State"), ("Reno → SFO", "Control / next gate")}), budget=2, closed_world=True),
        region("p02.controls", 2, "Local release controls", "table", table_leaves("p02.controls", local_headers, local_rows, consequential={("Reno", "Limit")}), budget=2, closed_world=True),
        region("p02.sequence", 2, "Independent lane sequence", "text", [
            leaf("p02.sequence.boise", "Boise may release independently."),
            leaf("p02.sequence.tacoma", "Tacoma remains on watch without reserve eligibility."),
            leaf("p02.sequence.spokane", "Spokane remains clear."),
            leaf("p02.sequence.reno", "Reno may not consolidate until Ravi Mehta records D-17 closure.", harm=2),
        ], budget=2),
        region("p03.reserve", 3, "Reserve ledger", "table", table_leaves("p03.reserve", RESERVE_HEADERS, RESERVE_ROWS, consequential={("Reno labor standby", "Eligibility"), ("Tacoma weekend premium", "Eligibility")}), budget=2, closed_world=True),
        region("p03.scenarios", 3, "Reserve scenarios", "table", table_leaves("p03.scenarios", scenario_headers, scenario_rows, consequential={("D-17 remains open after 12 Jul 16:00 PT", "Eligible reserve")}), budget=2, closed_world=True),
        region("p03.annotation", 3, "Finance annotation", "text", [
            leaf("p03.annotation.tacoma", "The Tacoma premium is excluded because D-19 retains the existing carrier allocation."),
            leaf("p03.annotation.reno", "Reno labor standby becomes eligible only after the D-17 deadline passes while the hold remains open.", harm=2),
        ]),
        region("p03.stamp", 3, "Raster finance concurrence stamp", "image", [
            leaf("p03.stamp.approver", "The stamp records finance concurrence by M. Okafor."),
            leaf("p03.stamp.time", "The concurrence stamp is dated 10 Jul 2026 at 14:18 PT."),
            leaf("p03.stamp.control", "The stamp names reserve control LO-551."),
        ]),
        region("p04.statement", 4, "Final controlling disposition", "text", [
            leaf("p04.statement.hold", "Reno outbound consolidation remains ON HOLD.", harm=2),
            leaf("p04.statement.release", "Release requires Ravi Mehta to close the D-17 dock staffing exception.", harm=2),
        ], budget=2),
        region("p04.signoff", 4, "Signoff register", "table", table_leaves("p04.signoff", SIGNOFF_HEADERS, SIGNOFF_ROWS, consequential={("Exception owner", "State")}), budget=2, closed_world=True),
        region("p04.interpretation", 4, "Signoff state interpretation", "text", [
            leaf("p04.interpretation.finance", "Finance concurrence authorizes the reserve but does not release Reno."),
            leaf("p04.interpretation.owner-state", "Ravi Mehta remains open and unsigned."),
            leaf(
                "p04.interpretation.effect",
                "Ravi Mehta's open, unsigned row keeps the controlling statement in force.",
                harm=2,
            ),
        ], budget=2),
        region("p04.control", 4, "Document control", "text", [
            leaf("p04.control.supersession", "Revision 3 supersedes Revision 2 at 10 Jul 2026 15:10 PT."),
            leaf("p04.control.review", "The next review is 12 Jul 2026 at 16:00 PT."),
            leaf("p04.control.retention", "The retention class is operations exception / seven years."),
        ]),
    ]


def _gold() -> str:
    control_headers = ["Memo field", "Memo value", "Linked field", "Linked value"]
    control_rows = [
        ["Prepared", "10 Jul 2026", "Coordinator", "Lena Ortiz"],
        ["Review window", "Through 12 Jul 16:00 PT", "Region", "West"],
        ["Scope", "Cross-dock and linehaul exceptions", "Record", "OR-7712"],
    ]
    local_headers = ["Location", "Release authority", "Evidence", "Limit"]
    local_rows = [
        ["Reno", "Ravi Mehta", "Crew roster RC-118", "No outbound consolidation"],
        ["Boise", "Lena Ortiz", "Slot approval LO-551", "18 pallets / B7 only"],
        ["Tacoma", "Mira Chen", "Carrier note TC-49", "Existing allocation"],
        ["Spokane", "Dispatch desk", "Daily plan SP-210", "Standard cutoff"],
    ]
    scenario_headers = ["Scenario", "Eligible reserve", "Included lines"]
    scenario_rows = [
        ["D-17 closes by 12 Jul 16:00 PT", "$2,400", "Temporary slot B7"],
        ["D-17 remains open after 12 Jul 16:00 PT", "$6,250", "Slot B7 + Reno labor standby"],
    ]
    return (
        f"# {TITLE}\n\n"
        "## Operating exception memo\n\n"
        + markdown_table(control_headers, control_rows)
        + "\n\nNetwork planning opened OR-7712 after Reno dock staffing fell three crew positions below the consolidation plan. Boise overflow capacity and Tacoma weekend allocation are controlled separately; no blanket regional stop was issued.\n\n"
        + markdown_table(DECISION_HEADERS, DECISION_ROWS)
        + "\n\nDistribute to network planning, Reno operations, transportation, and finance. D-17 is the only open blocking decision.\n\n"
        "## Lane risk register\n\n"
        + markdown_table(LANE_HEADERS, LANE_ROWS)
        + "\n\n"
        + markdown_table(local_headers, local_rows)
        + "\n\nBoise may release independently. Tacoma remains on watch without reserve eligibility. Spokane remains clear. Reno may not consolidate until the D-17 exception owner records closure.\n\n"
        "## Cost reserve authorization\n\n"
        + markdown_table(RESERVE_HEADERS, RESERVE_ROWS)
        + "\n\n"
        + markdown_table(scenario_headers, scenario_rows)
        + "\n\nTacoma weekend premium is excluded because D-19 retains the existing carrier allocation. Labor standby becomes eligible only after the D-17 deadline passes while the hold remains open.\n\n"
        "Finance concurrence stamp: M. Okafor; 10 Jul 2026 14:18 PT; reserve control LO-551.\n\n"
        "## Controlling disposition and signoff\n\n"
        "Reno outbound consolidation remains **ON HOLD** until Ravi Mehta closes the D-17 dock staffing exception.\n\n"
        + markdown_table(SIGNOFF_HEADERS, SIGNOFF_ROWS)
        + "\n\nFinance concurrence authorizes the reserve; it does not release Reno. Operations approval establishes the packet. Ravi Mehta's row remains open and unsigned, so the controlling statement remains in force.\n\n"
        "Revision 3 supersedes Revision 2 at 10 Jul 2026 15:10 PT. Next review: 12 Jul 2026 16:00 PT. Retention class: operations exception / seven years.\n"
    )


def build(output_root):
    output_root = Path(output_root).resolve()
    case_dir = output_root / "cases" / CASE_ID
    case_dir.mkdir(parents=True, exist_ok=True)
    source_pdf = case_dir / "source.pdf"
    with tempfile.TemporaryDirectory(prefix="p23-office-export-") as temp_name:
        work_dir = Path(temp_name)
        docx_path = work_dir / "west-region-logistics-or-7712.docx"
        stamp_path = work_dir / "finance-stamp.png"
        _approval_stamp(stamp_path)
        _build_docx(docx_path, stamp_path)
        _export_with_libreoffice(docx_path, source_pdf, work_dir)

    regions = _regions()
    (case_dir / "gold.md").write_text(_gold(), encoding="utf-8")
    (case_dir / "facts.json").write_text(
        json.dumps(
            {
                "schemaVersion": 2,
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
        "Source modality: born-digital DOCX exported through LibreOffice to native PDF, with a raster approval stamp and a genuinely malformed fixed-row/floating-table layout.\n\n"
        f"Family: `{FAMILY}`\n\n"
        "Purpose: Recover structured office-document content from legitimate native PDF objects when LibreOffice's handling of incompatible DOCX layout constraints produces clipping and overlap.\n\n"
        "The source PDF is the unmodified office-export result apart from deterministic container normalization. It has no hidden answer layer or post-export content overlay.\n\n"
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
        "pages": 4,
        "pdf": f"{base}/source.pdf",
        "gold": f"{base}/gold.md",
        "spec": f"{base}/spec.md",
        "facts": f"{base}/facts.json",
    }
