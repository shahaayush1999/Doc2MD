from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = ROOT / "benchmark"
CASE_ROOT = BENCHMARK_ROOT / "cases"

PAGE_W, PAGE_H = 1700, 2200


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


def fact(id_: str, category: str, weight: float, expectation: str, guidance: str = "") -> dict:
    return {
        "id": id_,
        "category": category,
        "weight": weight,
        "expectation": expectation,
        "guidance": guidance,
    }


def facts_from_checks(case: Case) -> list[dict]:
    return [
        fact(
            check["id"],
            check.get("category", "accuracy"),
            check.get("weight", 1),
            check.get("description", check["id"]),
            "Derived from the deterministic audit checklist. Mark correct when the candidate faithfully preserves this obligation, even if wording or Markdown syntax differs.",
        )
        for check in case.checks
    ]


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
    d.text((100, 1350), "Footer: Board packet GTM-09. Lane ownership, month span, owner, and dependency drive staffing plan.", fill="#475569", font=F["small"])
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
    draw_text(d, (left_x, y + 45), "The parser emits candidate blocks, then applies a patch reranker only to regions marked table-like or figure-like.", F["small"], width=34, leading=29)
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
        "# Sparse Retrieval With Patch Reranking\n\nAbstract: We evaluate a patch reranker that improves table-region recall without changing OCR. The main result is a 6.3 point F1 gain on scanned appendices.\n\n## 1. Method\n\nThe parser emits candidate blocks, then applies a patch reranker only to regions marked table-like or figure-like.\n\nEquation 1: score = 0.62*T + 0.28*V + 0.10*R.\n\nTable 1. Ablation: base recall 71.4 and F1 68.2; +patch recall 80.1 and F1 74.5; +caption recall 82.0 and F1 75.1.\n\n## 2. Results\n\nThe caption-aware variant is strongest, but most of the gain comes from patch reranking. Failure cases cluster around equation/table boundaries.\n\nFigure 2 retrieval path: PDF page -> patch grid -> reranker -> Markdown blocks. Caption: patch grid feeds the reranker before Markdown block assembly.\n\n## 3. Limitations\n\nThe model still confuses marginal notes with captions when the note touches a figure border. Rotated labels were excluded from the pilot.\n\nReviewer note: Do not read this box before the Results section; it comments on Figure 2.\n\nFootnote 1: F1 is macro-averaged over pages, not documents.\n",
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
    d.text((100, 150), "Page is shown in portrait, but the matrix is a landscape insert.", fill="#7f1d1d", font=F["small"])
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
    draw_text(d, (740, 915), "Operations note: red slash cells are reviewed from the matrix itself, not from row totals. Export Friday must be read directly from its cell.", F["small"], width=58, leading=29)
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
        "# Landscape Heatmap Escalation Plan\n\nPage is shown in portrait, but the matrix is a landscape insert.\n\n## Escalation heatmap: color + letter both matter\n\n| Team | Mon | Tue | Wed | Thu | Fri | Sat |\n| --- | --- | --- | --- | --- | --- | --- |\n| API | G | Y | Y | R with slash | R | Y |\n| Data | G | G | Y | Y | R with slash | R |\n| Export | Y | Y | R with slash | R | Y | G |\n| Billing | G | Y | G | Y | Y | R with slash |\n\nLegend: G green normal; Y yellow watch; R red escalation. A diagonal slash means the owner must page the incident lead.\n\nReviewer instruction: derive the red slash cells from the matrix itself. Do not infer severity from row totals. Export Friday must be read directly from its cell.\n\nCritical red slash cells: API Thu, Data Fri, Export Wed, and Billing Sat. Export Fri is yellow, not red. Weekend columns are part of the table and must not be dropped.\n",
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


def packet_ops_board() -> Case:
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
    d.text((100, 150), "Some chart values are visual only. Warning banner must be derived from the panels.", fill="#7f1d1d", font=F["small"])
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
    draw_table(d, 105, 900, [260, 240, 240, 240], [["Priority", "Breached", "At risk", "OK"], ["Critical", "3", "2", "7"], ["High", "5", "4", "18"], ["Normal", "2", "6", "31"]], 70)
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


def packet_scientific_supplement() -> Case:
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


def packet_noc_handover() -> Case:
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
    arrows = [("POS", "EdgeGW"), ("Handheld", "EdgeGW"), ("EdgeGW", "Switch"), ("Switch", "Acquirer"), ("Switch", "Risk"), ("Risk", "Fraud"), ("Switch", "Ledger")]
    for a, b in arrows:
        ax, ay, _ = nodes[a]
        bx, by, _ = nodes[b]
        d.line((ax + 205, ay + 41, bx, by + 41), fill="#111827", width=4)
        d.polygon([(bx, by + 41), (bx - 14, by + 31), (bx - 14, by + 51)], fill="#111827")
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
    d.text((100, 150), "Color, letter, and slash all carry status. Dot means external partner is required.", fill="#7f1d1d", font=F["small"])
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
    colors = {"G": "#dcfce7", "Y": "#fef3c7", "R": "#fee2e2"}
    x0, y0 = 285, 330
    for c, stream in enumerate(streams):
        d.text((x0 + c * 205 + 12, y0 - 52), stream, fill="#111827", font=F["small"])
    for r, store in enumerate(stores):
        y = y0 + r * 115
        d.text((95, y + 32), store, fill="#111827", font=F["small"])
        for c, stream in enumerate(streams):
            value = matrix[r][c]
            x = x0 + c * 205
            d.rectangle((x, y, x + 145, y + 82), fill=colors[value], outline="#111827", width=3)
            d.text((x + 58, y + 26), value, fill="#111827", font=F["small"])
            if (store, stream) in slash:
                d.line((x + 10, y + 8, x + 135, y + 74), fill="#991b1b", width=4)
            if (store, stream) in dot:
                d.ellipse((x + 112, y + 12, x + 128, y + 28), fill="#111827")
    d.rounded_rectangle((90, 1130, 650, 1375), radius=14, fill="#f8fafc", outline="#334155", width=3)
    draw_text(d, (120, 1165), "Legend: G green clear; Y yellow watch; R red blocked. Slash means executive escalation. Dot means external partner required.", F["small"], width=39, leading=30)
    d.rounded_rectangle((770, 1130, 1540, 1375), radius=14, fill="#fff7ed", outline="#c2410c", width=3)
    draw_text(d, (800, 1165), "Matrix readout: marked red cells require owner escalation. Dots indicate partner follow-up. Read the row and column labels directly before updating the launch log.", F["small"], fill="#9a3412", width=55, leading=30)
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
    draw_text(d, (905, 865), "Stamp nuance: PARTIAL PAID applies only to FieldBridge, not to the whole ledger. Signage reprint is not reserve eligible.", F["small"], fill="#991b1b", width=43, leading=30)
    d.line((980, 1020, 1410, 870), fill="#991b1b", width=8)
    d.text((1115, 920), "PARTIAL PAID", fill="#991b1b", font=F["stamp"])
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

Matrix reconstruction: BND-01 has red Gateway, red POS with slash, and red Partner with slash and dot. PDX-05 Gateway is yellow with slash, not red.

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
    pts = [(1080, 1190), (1220, 1110), (1360, 1030)]
    labels = ["1.9", "1.5", "1.2"]
    d.line((1070, 1210, 1420, 1210), fill="#111827", width=3)
    d.line((1070, 1210, 1070, 980), fill="#111827", width=3)
    for a, b in zip(pts, pts[1:]):
        d.line((*a, *b), fill="#2563eb", width=5)
    for p, label in zip(pts, labels):
        d.ellipse((p[0] - 7, p[1] - 7, p[0] + 7, p[1] + 7), fill="#2563eb")
        d.text((p[0] - 18, p[1] - 35), label, fill="#111827", font=F["tiny"])
    d.rounded_rectangle((80, 870, 930, 1280), radius=14, fill="#fff7ed", outline="#c2410c", width=3)
    draw_text(d, (110, 905), "Footnotes: 08-12 potassium is hemolyzed and excluded. 08-12 INR was canceled and should not be carried forward. Hemoglobin remains low at discharge.", F["small"], fill="#9a3412", width=58, leading=30)
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
    draw_text(d, (860, 840), "Pharmacist note: ED list showed lisinopril 20 mg daily and ibuprofen PRN, but both are inactive at discharge. Do not copy ED list into final medication section.", F["small"], fill="#991b1b", width=48, leading=30)
    d.line((1035, 855, 1165, 855), fill="#991b1b", width=4)
    d.text((1038, 820), "20 mg daily", fill="#991b1b", font=F["tiny"])
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
    d.text((725, 1062), "94 threshold", fill="#dc2626", font=F["tiny"])
    for a, b in zip(pts, pts[1:]):
        d.line((*a, *b), fill="#2563eb", width=5)
    for p, val in zip(pts, vals):
        d.ellipse((p[0] - 7, p[1] - 7, p[0] + 7, p[1] + 7), fill="#2563eb")
        d.text((p[0] - 12, p[1] - 33), val, fill="#111827", font=F["tiny"])
    d.rounded_rectangle((905, 800, 1535, 1280), radius=14, fill="#f8fafc", outline="#334155", width=3)
    d.text((935, 835), "Blood pressure", fill="#111827", font=F["h2"])
    bp_rows = [["Time", "BP", "Pulse"], ["06:00", "132/84", "88"], ["12:00", "118/72", "82"], ["18:00", "126/78", "80"], ["22:00", "124/76", "78"]]
    draw_table(d, 935, 895, [150, 190, 130], bp_rows, 56)
    pages.append(p4)

    p5 = base_page("Referral Sheet and Draft Footer")
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
    pages.append(p5)

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

## Referral Sheet and Draft Footer

| Appointment | Date/time | Location | Status | Instruction |
| --- | --- | --- | --- | --- |
| Home health nurse | 2026-08-15 09:00 | home | authorized | med check and vitals |
| BMP lab draw | 2026-08-17 08:00 | LMC Lab | scheduled | bring lab slip |
| Primary care | 2026-08-19 10:30 | Clinic A | scheduled | review antibiotics |
| Cardiology | 2026-08-25 09:00 | Heart Center | scheduled | 11 days after discharge |

Authorization stamp: home health visit approved once for 2026-08-15. Additional visits require PCP order.

Draft footer from 08:15 said cardiology in 2 weeks and resume home blood pressure pill. It is superseded by final medication reconciliation and signed referral schedule.
"""

    return Case(
        "P08-hospital-discharge-medrec",
        "Hospital Discharge Medication Reconciliation",
        "medical",
        ["multi-page", "labs", "med-rec", "forms", "timeline", "source-precedence", "chart"],
        "Stress a realistic discharge packet with lab units/flags, final-vs-draft medication state, selected actions, held/administered MAR states, visual vitals, and follow-up conflicts.",
        "Five-page medical discharge packet with mixed memo text, tables, checkboxes, chart, and draft/source-state conflict.",
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
            fact("p08.creatinine.sparkline", "visual_relation", 4, "Creatinine sparkline values are 1.9, 1.5, and 1.2, showing improvement."),
            fact("p08.med.table", "table_cell", 8, "Medication table preserves Metformin 500 mg continue, Lisinopril HOLD/stop/do not restart, Azithromycin 250 mg daily x3 days/new, Insulin glargine 14 units/change, Ibuprofen STOP/stop."),
            fact("p08.med.checkboxes", "form_state", 6, "Checked actions are continue Metformin, change Insulin glargine, stop Lisinopril, new Azithromycin; restart lisinopril today is unchecked."),
            fact("p08.med.superseded", "source_state", 6, "ED list showed lisinopril 20 mg daily and ibuprofen PRN, but both are inactive at discharge and must not be treated as active discharge medications."),
            fact("p08.mar.grid", "table_cell", 7, "MAR grid preserves Azithromycin administered at 12:00, Insulin lispro administered 06:00 and 18:00 but held at 12:00, Acetaminophen refused 12:00 and administered 22:00, Lisinopril held all day, Metformin administered 06:00 and 18:00."),
            fact("p08.vitals", "visual_relation", 5, "Oxygen saturation chart values are 91, 93, 95, 96, 96 with threshold 94; BP table preserves 132/84 pulse 88, 118/72 pulse 82, 126/78 pulse 80, 124/76 pulse 78."),
            fact("p08.referrals", "table_cell", 5, "Referral sheet preserves home health 2026-08-15 09:00 authorized once, BMP 2026-08-17 08:00, primary care 2026-08-19 10:30, cardiology 2026-08-25 09:00."),
            fact("p08.draft.footer", "source_state", 6, "Draft footer said cardiology in 2 weeks and resume home blood pressure pill, but it is superseded by the signed referral schedule and final medication reconciliation."),
            fact("p08.page_order", "structure", 4, "Output preserves packet order: discharge summary, lab trends, final medication reconciliation, nursing MAR/vitals, referral sheet/draft footer."),
        ],
        extractable_text_pages=[
            overlays(["Lakeview Medical Center - Discharge Packet", "Patient: Ana Rivera", "MRN: LMC-482913"], 100, 100),
            [],
            [],
            [],
            overlays(["Draft footer from 08:15 is superseded by final medication reconciliation and signed referral schedule."], 880, 730),
        ],
    )


CASES = [packet_ops_board(), packet_scientific_supplement(), packet_noc_handover(), packet_launch_readiness(), packet_hospital_discharge()]


def write_pdf(case: Case, path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    if case.covered_text:
        c.setFont("Helvetica", 12)
        c.setFillColorRGB(0, 0, 0)
        y = 620
        for line in case.covered_text:
            c.drawString(72, y, line)
            y -= 18
    for i, page in enumerate(case.pages):
        if case.extractable_text_pages and i < len(case.extractable_text_pages):
            c.setFont("Helvetica", 9)
            c.setFillColorRGB(0, 0, 0)
            for px, py, line in case.extractable_text_pages[i]:
                c.drawString(px / PAGE_W * letter[0], letter[1] - py / PAGE_H * letter[1], line)
        buffer = BytesIO()
        page.save(buffer, format="PNG")
        buffer.seek(0)
        c.drawImage(ImageReader(buffer), 0, 0, width=letter[0], height=letter[1])
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
        overlay = rl_canvas.Canvas(packet, pagesize=letter)
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


def write_spec(case: Case) -> str:
    return "\n".join(
        [
            f"# {case.title}",
            "",
            f"Purpose: {case.purpose}",
            "",
            f"Source modality: {case.modality}",
            "",
            "Expected gold objects:",
            *[f"- {item}" for item in case.expected],
            "",
            "Scoring checklist:",
            *[f"- {item}" for item in case.scoring],
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
    write_pdf(case, out / "source.pdf")
    (out / "gold.md").write_text(case.gold, encoding="utf-8")
    (out / "spec.md").write_text(write_spec(case), encoding="utf-8")
    checks = {"id": case.id, "title": case.title, "family": case.family, "tags": case.tags, "checks": case.checks}
    (out / "checks.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    facts = {"id": case.id, "title": case.title, "family": case.family, "tags": case.tags, "facts": case.facts or facts_from_checks(case)}
    (out / "facts.json").write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")
    return {
        "id": case.id,
        "title": case.title,
        "family": case.family,
        "tags": case.tags,
        "pages": len(case.pages),
        "pdf": f"benchmark/cases/{case.slug}/source.pdf",
        "gold": f"benchmark/cases/{case.slug}/gold.md",
        "spec": f"benchmark/cases/{case.slug}/spec.md",
        "checks": f"benchmark/cases/{case.slug}/checks.json",
        "facts": f"benchmark/cases/{case.slug}/facts.json",
    }


def main() -> None:
    if BENCHMARK_ROOT.exists():
        shutil.rmtree(BENCHMARK_ROOT)
    CASE_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "Doc2MD-LongPackets-5",
        "version": "0.6.0-experimental",
        "description": "Experimental multi-page realistic packet benchmark focused on charts, dense visual matrices, spatial timelines, continuations, borderless layouts, and cross-page conflicts.",
        "caseCount": len(CASES),
        "pageCount": sum(len(case.pages) for case in CASES),
        "cases": [write_case(case) for case in CASES],
    }
    (BENCHMARK_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {manifest['caseCount']} cases and {manifest['pageCount']} pages to {BENCHMARK_ROOT}")


if __name__ == "__main__":
    main()
