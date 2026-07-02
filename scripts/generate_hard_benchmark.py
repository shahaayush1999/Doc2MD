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
    "tiny": font(18),
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
    hidden_text: list[str] | None = None
    covered_text: list[str] | None = None

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
    d.rounded_rectangle(box, radius=24, fill=fill, outline=outline, width=4)
    x1, y1, _, _ = box
    d.text((x1 + 32, y1 + 24), title, fill="#111827", font=F["h2"])
    y = y1 + 78
    for line in lines:
        d.text((x1 + 32, y), line, fill="#111827", font=F["body"])
        y += 42


def draw_table(d: ImageDraw.ImageDraw, x: int, y: int, widths: list[int], rows: list[list[str]], row_h: int = 66) -> int:
    for r, row in enumerate(rows):
        fill = "#e5e7eb" if r == 0 else "#ffffff"
        cx = x
        for c, w in enumerate(widths):
            d.rectangle((cx, y, cx + w, y + row_h), fill=fill, outline="#111827", width=3)
            text = row[c] if c < len(row) else ""
            fnt = F["small"] if r else F["small"]
            d.multiline_text((cx + 12, y + 14), text, fill="#111827", font=fnt, spacing=4)
            cx += w
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
        "# Release Approval Card\n\nStatus: BLOCKED\nOwner: Nisha Vora\nBudget cap: $14,900\nReason: Security signoff missing for EU tenant\nStamp: HOLD UNTIL 2026-08-17\n",
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
        "# Shipping Exception Overlay\n\nShipment XQ-17 is DELAYED at Osaka with ETA 2026-08-14. Owner: Ren Ito.\nReason: customs inspection hold.\n",
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
    d.text((90, 960), "Gold must normalize each bar into task, owner, start, end, and label rows.", fill="#7f1d1d", font=F["small"])
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
    img = base_page("Broken Pitch Slide Export")
    d = ImageDraw.Draw(img)
    draw_card(d, (90, 260, 540, 820), "Phase 1", ["Collect source PDFs", "Inspect gold object list"], "#eef2ff", "#4338ca")
    draw_card(d, (470, 480, 1010, 1040), "Phase 2", ["Run cheap models", "Harden cases where", "scores saturate"], "#ecfeff", "#0f766e")
    draw_card(d, (980, 300, 1530, 870), "Phase 3", ["Publish calibration", "after leakage and", "ambiguity review"], "#f0fdf4", "#15803d")
    d.rounded_rectangle((255, 1040, 930, 1230), radius=16, fill="#fef3c7", outline="#92400e", width=4)
    d.text((285, 1092), "Sticky note:", fill="#92400e", font=F["h2"])
    d.text((285, 1145), "Do NOT call this a leaderboard yet", fill="#92400e", font=F["body"])
    d.text((110, 1340), "Decision requested: approve hard-suite pilot, not public launch.", fill="#111827", font=F["h2"])
    return Case(
        "H07-broken-pitch-slide",
        "Broken Pitch Slide Export",
        "layout",
        ["raster-only", "slide", "overlap"],
        "Untangle a mildly broken Office-export style slide without losing grouped callouts.",
        "Raster-only slide with overlapping phase cards and a sticky note.",
        ["phase order", "grouped phase text", "sticky note", "decision line"],
        ["Recover reading order despite overlap.", "Bind Phase 2 to cheap models and hardening.", "Preserve sticky warning."],
        "# Broken Pitch Slide Export\n\nPhase 1: Collect source PDFs and inspect the gold object list.\nPhase 2: Run cheap models, then harden cases where scores saturate.\nPhase 3: Publish calibration cases after leakage and ambiguity review.\nSticky note: Do NOT call this a leaderboard yet.\nDecision requested: approve hard-suite pilot, not public launch.\n",
        [
            ordered_check("phase-order", "layout", ["Phase 1", "Phase 2", "Phase 3", "Sticky note", "Decision requested"], 2.5),
            near_check("phase2", "layout", ["Phase 2", "cheap models", "harden", "saturate"], 2.5, 320),
            all_check("sticky", "visual", ["Do NOT call this a leaderboard yet"], 2),
            all_check("decision", "text", ["hard-suite pilot", "not public launch"], 1),
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
            none_check("no-positive-elim", ["Intercompany 72", "Intercompany.* 72 .* 81"], 2),
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
            near_check("checkboxes", "forms", ["Cliente informado", "Customer informed", "Pieza pendiente", "Part pending"], 1.5, 420),
            none_check("no-pending-selected", ["Pieza pendiente selected", "Part pending selected", "Pieza pendiente checked", "Part pending checked"], 2),
        ],
        [img],
    )


CASES = [h01(), h02(), h03(), h04(), h05(), h06(), h07(), h08(), h09(), h10(), h11(), h12()]


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
        image_to_pdf_page(c, page)
        if i < len(case.pages) - 1 and case.covered_text:
            # Covered text applies only to the first page before its image.
            pass
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
    }


def main() -> None:
    if BENCHMARK_ROOT.exists():
        shutil.rmtree(BENCHMARK_ROOT)
    CASE_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "Doc2MD-Hard-12",
        "version": "0.2.0",
        "description": "Compact hard Doc2MD candidate suite focused on visibility semantics, raster spatial normalization, table semantics, forms, dashboards, and layout binding.",
        "caseCount": len(CASES),
        "pageCount": sum(len(case.pages) for case in CASES),
        "cases": [write_case(case) for case in CASES],
    }
    (BENCHMARK_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {manifest['caseCount']} cases and {manifest['pageCount']} pages to {BENCHMARK_ROOT}")


if __name__ == "__main__":
    main()
