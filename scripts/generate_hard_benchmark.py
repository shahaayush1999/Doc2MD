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
    img = base_page("Three-Column Launch Poster")
    d = ImageDraw.Draw(img)
    cols = [(90, 250, 500), (600, 250, 1010), (1110, 250, 1520)]
    headings = ["Signal", "Evidence", "Decision"]
    colors = ["#eef2ff", "#ecfeff", "#f0fdf4"]
    for (x1, y1, x2), heading, color in zip(cols, headings, colors):
        d.rounded_rectangle((x1, y1, x2, 1260), radius=18, fill=color, outline="#334155", width=3)
        d.text((x1 + 22, y1 + 24), heading, fill="#111827", font=F["h2"])

    draw_text(d, (115, 330), "North funnel shows high visits but weak activation. Do not combine with partner leads.", F["small"], width=27, leading=29)
    d.text((115, 540), "Mini table", fill="#111827", font=F["small"])
    draw_table(d, 115, 580, [130, 130, 130], [["Region", "Visits", "Act."], ["North", "18k", "4.1%"], ["West", "9k", "7.8%"], ["Partner", "3k", "11.2%"]], 54)
    d.rounded_rectangle((165, 970, 460, 1115), radius=14, fill="#fee2e2", outline="#991b1b", width=3)
    d.text((190, 1018), "Risk: North volume", fill="#991b1b", font=F["small"])

    draw_text(d, (625, 330), "Figure A traces the evidence chain. Website visits feed trial starts, but partner leads bypass trials.", F["small"], width=28, leading=29)
    flow = [("Website", 650, 590), ("Trial", 800, 740), ("Paid", 650, 890)]
    for label, x, y in flow:
        d.ellipse((x, y, x + 130, y + 75), fill="#dbeafe", outline="#1d4ed8", width=3)
        d.text((x + 24, y + 24), label, fill="#111827", font=F["tiny"])
    d.line((760, 645, 820, 740), fill="#111827", width=4)
    d.line((800, 815, 735, 890), fill="#111827", width=4)
    d.rounded_rectangle((890, 560, 1000, 650), radius=12, fill="#fef3c7", outline="#92400e", width=3)
    d.text((908, 595), "Partner", fill="#92400e", font=F["tiny"])
    d.line((940, 650, 755, 910), fill="#92400e", width=4)

    draw_text(d, (1135, 330), "Decision: launch West first, hold North until activation improves, and track Partner separately.", F["small"], width=28, leading=29)
    d.rounded_rectangle((1140, 560, 1490, 720), radius=14, fill="#dcfce7", outline="#15803d", width=3)
    d.text((1170, 612), "APPROVE WEST", fill="#15803d", font=F["stamp"])
    d.rounded_rectangle((1140, 810, 1490, 995), radius=14, fill="#fff7ed", outline="#c2410c", width=3)
    draw_text(d, (1170, 850), "Margin note: Partner leads are not part of North.", F["small"], fill="#9a3412", width=24, leading=28)
    d.text((100, 1370), "Poster footer: GTM-27 draft 4. Reading order is Signal -> Evidence -> Decision.", fill="#475569", font=F["small"])
    return Case(
        "H14-three-column-poster",
        "Three-Column Launch Poster",
        "layout",
        ["raster-only", "three-column", "poster", "diagram", "table", "callout"],
        "Recover a three-column poster with an embedded table, flow diagram, stamp, and margin note.",
        "Raster-only poster page with three visual columns.",
        ["column reading order", "mini table", "flow diagram", "decision stamp", "margin note", "footer"],
        ["Read Signal before Evidence before Decision.", "Keep Partner separate from North.", "Preserve approve/hold decision."],
        "# Three-Column Launch Poster\n\nSignal: North funnel shows high visits but weak activation. Do not combine North with partner leads. Mini table: North 18k visits and 4.1% activation; West 9k visits and 7.8% activation; Partner 3k visits and 11.2% activation. Risk: North volume.\n\nEvidence: Figure A traces Website -> Trial -> Paid, while Partner bypasses Trial and points to Paid.\n\nDecision: launch West first, hold North until activation improves, and track Partner separately. Stamp: APPROVE WEST. Margin note: Partner leads are not part of North.\n\nPoster footer: GTM-27 draft 4. Reading order is Signal -> Evidence -> Decision.\n",
        [
            ordered_check("poster-reading-order", "layout", ["Signal", "North", "Evidence", "Website", "Decision", "APPROVE WEST", "GTM-27"], 3),
            near_check("north-row", "tables", ["North", "18k", "4.1%"], 2, 180),
            near_check("west-row", "tables", ["West", "9k", "7.8%"], 2, 180),
            ordered_check("flow-main", "visual", ["Website", "Trial", "Paid"], 2),
            near_check("partner-separate", "binding", ["Partner", "bypass", "Trial", "Paid"], 2.5, 360),
            all_check("decision", "text", ["launch West", "hold North", "track Partner separately"], 2),
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
    draw_text(d, (740, 915), "Reviewer instruction: derive the red slash cells from the matrix itself. Do not infer severity from row totals. Export Friday must be read directly from its cell.", F["small"], width=58, leading=29)
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
        "# Landscape Heatmap Escalation Plan\n\nLegend: G green normal; Y yellow watch; R red escalation. A diagonal slash means the owner must page the incident lead.\n\nCritical red slash cells: API Thu, Data Fri, Export Wed, and Billing Sat. Export Fri is yellow, not red. Weekend columns are part of the table and must not be dropped.\n",
        [
            all_check("legend", "text", ["green normal", "yellow watch", "red escalation", "slash"], 2),
            near_check("api-thu", "tables", ["API", "Thu", "red", "slash"], 2.5, 420),
            near_check("data-fri", "tables", ["Data", "Fri", "red", "slash"], 2.5, 420),
            near_check("billing-sat", "tables", ["Billing", "Sat", "red", "slash"], 2.5, 420),
            near_check("export-fri-yellow", "binding", ["Export", "Fri", "yellow", "not red"], 2.5, 420),
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
        "# Multi-Panel Metrics Report\n\nPanel A Queue depth rises every day and ends at 47 on Friday.\n\nPanel B Defect mix: red means severe and blue means minor. Visual has the most severe defects, with 19 severe defects.\n\nPanel C Owner matrix: Noor has 14 open and 6 aged with SLA risk; Mira has 9 open and 1 aged with SLA ok; Ken has 24 open and 11 aged with SLA risk.\n\nCross-panel warning: Ken has the highest aged count at 11. The defect mix warning is severe Visual defects, not total Tables defects.\n",
        [
            near_check("queue-friday", "visual", ["Queue depth", "Friday", "47"], 2.5, 260),
            near_check("visual-severe", "visual", ["Visual", "severe", "19"], 2.5, 260),
            near_check("ken-aged", "tables", ["Ken", "24", "11", "risk"], 2.5, 260),
            near_check("noor-row", "tables", ["Noor", "14", "6", "risk"], 2, 260),
            none_check("no-wrong-severe", ["Tables has the most severe", "Tables.*most severe"], 2),
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
        "# Redlined Data Processing Addendum\n\nSection 4. Data return: Processor must return Customer Data within 10 business days after termination. Deleted old text: within 30 calendar days. Comment A: Legal asks whether 10 business days is acceptable for regulated customers.\n\nSection 5. Audit logs: Processor must retain audit logs for 400 days and provide export within 48 hours of written request. Deleted phrase: commercially reasonable efforts. Comment B: Security accepts 400 days and says not to restore the deleted efforts language.\n\nSignature block remains unchanged: NovaCloud / Atlas Retail.\n",
        [
            near_check("current-return", "text", ["Data return", "10 business days", "termination"], 2.5, 260),
            near_check("deleted-30", "structure", ["Deleted", "30 calendar days"], 2, 220),
            near_check("audit-current", "text", ["Audit logs", "400 days", "48 hours"], 2.5, 320),
            near_check("comment-a", "layout", ["Comment A", "Legal", "regulated customers"], 2, 260),
            near_check("comment-b", "layout", ["Comment B", "Security", "400 days", "deleted efforts"], 2, 360),
            none_check("no-current-30", ["must return Customer Data within 30 calendar days", "current.*30 calendar days"], 3),
            none_check("no-inserted-efforts", ["Inserted.*commercially reasonable efforts", "current.*commercially reasonable efforts"], 2),
        ],
        [img],
    )


CASES = [h01(), h02(), h03(), h07(), h11(), h12(), h13(), h14(), h15(), h16(), h17()]


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
        "name": "Doc2MD-Hard-11",
        "version": "0.3.0",
        "description": "Compact hard Doc2MD candidate suite focused on complex raster layouts, visual-to-structure reconstruction, table/figure binding, redlines, and visibility semantics.",
        "caseCount": len(CASES),
        "pageCount": sum(len(case.pages) for case in CASES),
        "cases": [write_case(case) for case in CASES],
    }
    (BENCHMARK_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {manifest['caseCount']} cases and {manifest['pageCount']} pages to {BENCHMARK_ROOT}")


if __name__ == "__main__":
    main()
