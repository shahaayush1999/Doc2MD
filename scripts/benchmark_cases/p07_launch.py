from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import HexColor

from .common import (
    AMBER,
    BLUE,
    GREEN,
    INK,
    MUTED,
    RED,
    CaseBuilder,
    draw_arrow,
    draw_badge,
    draw_label,
    draw_paragraph,
    draw_table,
    image_reader,
    leaf,
    markdown_table,
    table_leaves,
)


def build(output_root):
    case = CaseBuilder(
        output_root=output_root,
        case_id="P07-launch-readiness-dossier",
        title="Northwest Pilot Readiness Review",
        family="retail operations",
        tags=["native-pdf", "dashboard", "dependency-map", "heatmap", "source-precedence"],
        page_count=7,
        purpose="Test a realistic born-digital operating packet with embedded visual regions and a superseded appendix.",
        source_modality="born-digital native PDF with one embedded raster escalation matrix",
        document_ref="OPS-NW-26-08 · controlled copy",
        metadata_date="D:20260810091500-07'00'",
    )

    # Page 1 - executive memo and decision register.
    c = case.new_page(
        "Northwest Pilot Readiness Review",
        subtitle="Meridian Retail Network | Steering packet | 10 August 2026",
        section_code="OPS-NW-26-08",
    )
    draw_badge(c, "Conditional go", 42, 684, AMBER)
    draw_label(c, "Decision requested", 42, 655)
    decision_request = (
        "Authorize the six-store pilot for the 14 August 2026 launch window, subject to closure of the Bend gateway exception "
        "and recovery of Tier 2 service-desk backlog to the approved limit."
    )
    draw_paragraph(
        c,
        decision_request,
        42,
        638,
        520,
        font="DocSans-Bold",
        size=10.3,
        leading=14,
    )
    draw_label(c, "Operating context", 42, 575)
    memo_left = (
        "The launch covers six stores, two fulfillment nodes, and three payment partners. Friday's activation target is 4,850 devices. "
        "Spokane North completed training after the scheduled cutover rehearsal; Bend still has one open POS-to-gateway exception."
    )
    memo_right = (
        "Finance approved reserve use for gateway freight and temporary floor support only. The Portland service desk remains above its Tier 2 launch threshold after the weekend migration. Signage reprint is deferred and is not reserve eligible."
    )
    draw_paragraph(c, memo_left, 42, 557, 250, size=8.8, leading=12)
    draw_paragraph(c, memo_right, 312, 557, 250, size=8.8, leading=12)
    decision_headers = ["Item", "Owner", "Due", "State", "Condition"]
    decision_rows = [
        ["Gateway freight reserve", "Iris Wu", "11 Aug", "Approved", "$18.4k cap"],
        ["Bend POS exception", "Mateo Ruiz", "12 Aug 17:00", "Open", "close before go"],
        ["Service desk staffing", "Priya Nair", "13 Aug 09:00", "Conditional", "Tier 2 <= 22"],
        ["Signage reprint", "Noah Klein", "Deferred", "Not funded", "outside reserve"],
    ]
    draw_label(c, "Decision register", 42, 425)
    draw_table(c, 42, 410, [128, 74, 78, 72, 130], [decision_headers, *decision_rows], font_size=7.3)
    c.setFillColor(HexColor("#F3F0E8"))
    c.roundRect(42, 95, 520, 82, 5, fill=1, stroke=0)
    draw_label(c, "Hold conditions", 56, 156, color=RED)
    draw_paragraph(
        c,
        "Hold if Bend remains open after 12 Aug 17:00, payment-switch errors exceed 1.2%, or Tier 2 backlog exceeds 22 at launch review.",
        56,
        139,
        485,
        size=8.5,
        leading=11.5,
        color=RED,
    )
    case.add_gold(
        "Executive memo and decision register",
        memo_left
        + "\n\n"
        + memo_right
        + "\n\n"
        + decision_request
        + "\n\nDecision: **CONDITIONAL GO**. Hold conditions are Bend open after 2026-08-12 17:00, payment-switch errors above 1.2%, or Tier 2 backlog above 22.\n\n"
        + markdown_table(decision_headers, decision_rows),
    )
    case.add_region(
        "p01.memo",
        "Executive memo",
        "text",
        [
            leaf(
                "p01.memo.scope",
                "Launch scope is six stores, two fulfillment nodes, and three payment partners.",
                allow_partial=True,
            ),
            leaf("p01.memo.target", "Friday activation target is 4,850 devices."),
            leaf("p01.memo.window", "The requested pilot launch window is 14 August 2026.", harm=2),
            leaf("p01.memo.spokane", "Spokane North completed training after the scheduled rehearsal."),
            leaf("p01.memo.bend", "Bend has one open POS-to-gateway exception.", harm=2),
            leaf("p01.memo.reserve", "Reserve is approved only for gateway freight and temporary floor support."),
            leaf("p01.memo.portland", "The Portland service desk remains above its Tier 2 launch threshold after the weekend migration.", harm=2),
            leaf("p01.memo.signage", "Signage reprint is deferred and not reserve eligible."),
            leaf("p01.memo.decision", "The current steering decision is CONDITIONAL GO.", harm=2),
            leaf("p01.memo.hold.bend", "Bend remaining open after 2026-08-12 17:00 is a hold condition.", harm=2),
            leaf("p01.memo.hold.errors", "Payment-switch error rate above 1.2% is a hold condition.", harm=2),
            leaf("p01.memo.hold.backlog", "Tier 2 backlog above 22 is a hold condition.", harm=2),
        ],
        budget=2,
    )
    case.add_region(
        "p01.decisions",
        "Decision register",
        "table",
        table_leaves("p01.decisions", decision_headers, decision_rows, consequential={("Bend POS exception", "State")}),
        closed_world=True,
    )

    # Page 2 - native vector dashboard.
    c = case.new_page(
        "Launch metrics",
        subtitle="Cutover snapshot | data through Friday 16:00 PT",
        section_code="DASHBOARD",
    )
    activations = [("Mon", 920), ("Tue", 1280), ("Wed", 1740), ("Thu", 2510), ("Fri", 3220)]
    c.setStrokeColor(INK)
    c.setLineWidth(0.7)
    c.line(64, 505, 330, 505)
    c.line(64, 505, 64, 650)
    points = []
    for index, (day, value) in enumerate(activations):
        x = 78 + index * 57
        y = 515 + value / 3220 * 120
        points.append((x, y))
        c.setFillColor(BLUE)
        c.circle(x, y, 3.2, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("DocSans-Bold", 6.6)
        c.drawCentredString(x, y + 9, str(value))
        c.setFont("DocSans", 6.5)
        c.drawCentredString(x, 493, day)
    c.setStrokeColor(BLUE)
    c.setLineWidth(1.8)
    for first, second in zip(points, points[1:]):
        c.line(first[0], first[1], second[0], second[1])
    draw_label(c, "Device activations", 64, 672)
    backlog = [("Tier 1", 31, 12), ("Tier 2", 27, 8), ("Partner", 9, 4), ("Fraud", 6, 2)]
    draw_label(c, "Open / blocked backlog", 356, 672)
    for index, (queue, open_count, blocked) in enumerate(backlog):
        y = 637 - index * 34
        c.setFont("DocSans", 7)
        c.setFillColor(INK)
        c.drawString(356, y + 3, queue)
        bar_width = open_count * 3.1
        blocked_width = blocked * 3.1
        c.setFillColor(HexColor("#AFC6DD"))
        c.rect(408, y, bar_width, 10, fill=1, stroke=0)
        c.setFillColor(RED)
        c.rect(408 + bar_width - blocked_width, y, blocked_width, 10, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("DocSans-Bold", 6.5)
        c.drawString(520, y + 2, f"{open_count} / {blocked}")
    guard_headers = ["Guardrail", "Current", "Limit", "State"]
    guard_rows = [
        ["Payment-switch errors", "0.9%", "<= 1.2%", "Inside"],
        ["Tier 2 backlog", "27", "<= 22", "Outside"],
        ["Gateway spare units", "126", ">= 140", "Outside"],
        ["Training completion", "92%", ">= 95%", "Outside"],
    ]
    draw_label(c, "Launch guardrails", 42, 445)
    draw_table(c, 42, 430, [180, 92, 92, 100], [guard_headers, *guard_rows], font_size=8.2, zebra=True)
    draw_label(c, "Traffic-light convention", 42, 252)
    draw_badge(c, "Inside", 42, 225, GREEN)
    draw_badge(c, "Watch", 119, 225, AMBER)
    draw_badge(c, "Outside", 196, 225, RED)
    c.setFillColor(MUTED)
    c.setFont("DocSans", 7.5)
    c.drawString(42, 195, "Inside = limit met; Watch = caution; Outside = limit missed.")
    c.drawString(42, 179, "Blocked counts are a subset of open backlog, not an additional queue total.")
    case.add_gold(
        "Launch metrics",
        "Device activations: "
        + ", ".join(f"{day} {value}" for day, value in activations)
        + ".\n\nBacklog values are open / blocked: "
        + ", ".join(f"{queue} {open_count} / {blocked}" for queue, open_count, blocked in backlog)
        + ". Blocked counts are subsets of open backlog, not additional queue totals. The traffic-light convention is Inside = limit met, Watch = caution, and Outside = limit missed. Snapshot is through Friday 16:00 PT.\n\n"
        + markdown_table(guard_headers, guard_rows),
    )
    case.add_region(
        "p02.activations",
        "Activation line chart",
        "chart",
        [leaf(f"p02.activations.{day.lower()}", f"{day} device activations are {value}.") for day, value in activations]
        + [leaf("p02.activations.snapshot", "The dashboard snapshot is through Friday 16:00 PT.")],
    )
    case.add_region(
        "p02.backlog",
        "Backlog bars",
        "chart",
        [
            item
            for queue, open_count, blocked in backlog
            for item in (
                leaf(f"p02.backlog.{queue.lower().replace(' ', '')}.open", f"{queue} open backlog is {open_count}."),
                leaf(f"p02.backlog.{queue.lower().replace(' ', '')}.blocked", f"{queue} blocked backlog is {blocked}."),
            )
        ]
        + [leaf("p02.backlog.relationship", "Blocked counts are subsets of open backlog rather than additional queue totals.")],
    )
    case.add_region(
        "p02.legend",
        "Traffic-light convention",
        "structure",
        [
            leaf("p02.legend.inside", "Inside means the limit is met."),
            leaf("p02.legend.watch", "Watch means caution."),
            leaf("p02.legend.outside", "Outside means the limit is missed.", harm=2),
        ],
    )
    case.add_region(
        "p02.guardrails",
        "Guardrail table",
        "table",
        table_leaves(
            "p02.guardrails",
            guard_headers,
            guard_rows,
            consequential={("Tier 2 backlog", "State"), ("Gateway spare units", "State")},
        ),
        closed_world=True,
        budget=2,
    )

    # Page 3 - dependency topology.
    c = case.new_page(
        "Payment and device dependencies",
        subtitle="Launch path and monitored fallback",
        section_code="ARCH-04",
    )
    nodes = {
        "POS terminals": (64, 575),
        "Handheld scanners": (64, 455),
        "Edge gateway": (236, 515),
        "Payment switch": (370, 515),
        "Acquirer A": (500, 610),
        "Risk rules": (500, 500),
        "Settlement ledger": (370, 350),
        "Fraud desk": (500, 390),
    }
    for label, (x, y) in nodes.items():
        c.setFillColor(HexColor("#F7F8F8"))
        c.setStrokeColor(INK)
        c.roundRect(x, y, 96, 34, 4, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("DocSans-Bold", 7)
        c.drawCentredString(x + 48, y + 13, label)
    edges = [
        ("POS terminals", "Edge gateway", False),
        ("Handheld scanners", "Edge gateway", False),
        ("Edge gateway", "Payment switch", False),
        ("Payment switch", "Acquirer A", False),
        ("Payment switch", "Risk rules", False),
        ("Payment switch", "Settlement ledger", False),
        ("Risk rules", "Fraud desk", False),
        ("Handheld scanners", "Settlement ledger", True),
    ]
    for source, destination, dashed in edges:
        sx, sy = nodes[source]
        dx, dy = nodes[destination]
        if (source, destination) in {("Payment switch", "Settlement ledger"), ("Risk rules", "Fraud desk")}:
            draw_arrow(c, sx + 48, sy, dx + 48, dy + 34, color=BLUE)
        else:
            draw_arrow(c, sx + 96, sy + 17, dx, dy + 17, color=AMBER if dashed else BLUE, dashed=dashed)
    c.setFillColor(RED)
    c.setFont("DocSans-Bold", 7.5)
    c.drawString(115, 628, "Bend exception EX-214")
    c.setStrokeColor(RED)
    c.setLineWidth(1.2)
    c.line(190, 620, 211, 552)
    draw_label(c, "Path notes", 42, 245)
    notes = [
        ["Solid", "Authorization or control path", "Required"],
        ["Dashed", "Scanner event copy to settlement", "Monitoring only"],
        ["EX-214", "Bend POS-to-gateway handshake", "Open"],
    ]
    draw_table(c, 42, 230, [80, 250, 150], [["Mark", "Meaning", "State"], *notes], font_size=8.2)
    case.add_gold(
        "Payment and device dependencies",
        "Required directed edges are POS terminals -> Edge gateway; Handheld scanners -> Edge gateway; Edge gateway -> Payment switch; Payment switch -> Acquirer A, Risk rules, and Settlement ledger; and Risk rules -> Fraud desk. A dashed monitoring-only event-copy path runs from Handheld scanners -> Settlement ledger. EX-214 is the open Bend POS-to-gateway handshake exception.\n\n"
        + markdown_table(["Mark", "Meaning", "State"], notes),
    )
    edge_leaves = [
        leaf(
            f"p03.edges.{index:02d}",
            f"A {'dashed monitoring-only' if dashed else 'required solid'} directed edge runs from {source} to {destination}.",
            harm=2 if not dashed else 1,
        )
        for index, (source, destination, dashed) in enumerate(edges, start=1)
    ]
    case.add_region("p03.topology", "Dependency topology", "diagram", edge_leaves, budget=2)
    case.add_region(
        "p03.exception",
        "Bend exception callout",
        "diagram",
        [
            leaf("p03.exception.state", "EX-214 is open."),
            leaf(
                "p03.exception.binding",
                "EX-214 is bound to the Bend POS terminals -> Edge gateway relation.",
                harm=2,
            ),
        ],
    )

    # Page 4 - borderless readiness table.
    c = case.new_page(
        "Store readiness",
        subtitle="Owner review at 10 August 15:30 PT",
        section_code="STORE REGISTER",
    )
    ready_headers = ["Store", "Owner", "Training", "Gateways", "Signage", "POS", "Staffing", "Open item"]
    ready_rows = [
        ["PDX-02 Pearl", "Lena", "OK", "144", "OK", "OK", "OK", "partner token"],
        ["PDX-05 East", "Owen", "Watch", "148", "OK", "OK", "OK", "coach shift"],
        ["SEA-04 Ballard", "Nia", "OK", "151", "OK", "OK", "Watch", "late coverage"],
        ["SPK-03 North", "Eli", "Watch", "146", "OK", "OK", "OK", "retest logged"],
        ["BND-01 Bend", "Mateo", "OK", "126", "OK", "Blocked", "OK", "EX-214 gateway"],
        ["EUG-02 River", "Sara", "OK", "143", "Watch", "OK", "OK", "signage ETA"],
    ]
    draw_table(c, 42, 650, [80, 48, 54, 54, 50, 52, 52, 92], [ready_headers, *ready_rows], font_size=6.7, zebra=True)
    draw_label(c, "Owner notes", 42, 395)
    owner_notes = [
        "PDX-05 coach shift is scheduled before the Thursday close rehearsal.",
        "SPK-03 training retest is logged; the dashboard still shows the packet-time Watch state.",
        "BND-01 replacement gateway is staged at the Redmond depot; courier release remains pending EX-214 closure.",
        "EUG-02 signage ETA does not use gateway reserve funds.",
    ]
    y = 375
    for index, note in enumerate(owner_notes, start=1):
        c.setFillColor(MUTED)
        c.setFont("DocSans-Bold", 7)
        c.drawString(44, y, f"{index:02d}")
        y = draw_paragraph(c, note, 68, y, 480, size=8.2, leading=11) - 7
    review_basis = (
        "Owners reconvene 13 August at 09:00 PT. Store states are frozen to the 10 August 15:30 PT packet cut; "
        "later field updates require an annotated change record."
    )
    draw_label(c, "Next review and packet cut", 42, 255)
    draw_paragraph(c, review_basis, 42, 237, 510, size=8.4, leading=11.5)
    case.add_gold(
        "Store readiness",
        markdown_table(ready_headers, ready_rows)
        + "\n\n"
        + "\n".join(f"- {note}" for note in owner_notes)
        + "\n\n"
        + review_basis,
    )
    case.add_region(
        "p04.readiness",
        "Store readiness table",
        "table",
        table_leaves(
            "p04.readiness",
            ready_headers,
            ready_rows,
            consequential={("BND-01 Bend", "POS"), ("BND-01 Bend", "Open item")},
        ),
        budget=2,
        closed_world=True,
    )
    case.add_region(
        "p04.notes",
        "Owner notes",
        "text",
        [
            leaf("p04.notes.pdx05", "PDX-05 coach shift is scheduled before the Thursday close rehearsal."),
            leaf("p04.notes.spk03.retest", "SPK-03 training retest is logged."),
            leaf("p04.notes.spk03.packet-state", "The packet-time SPK-03 training state remains Watch.", harm=2),
            leaf("p04.notes.bnd01.staged", "The BND-01 replacement gateway is staged at the Redmond depot."),
            leaf("p04.notes.bnd01.release", "Courier release for the BND-01 replacement gateway remains pending EX-214 closure.", harm=2),
            leaf("p04.notes.eug02", "EUG-02 signage does not use gateway reserve funds."),
            leaf("p04.notes.review", "Owners reconvene on 13 August at 09:00 PT."),
            leaf("p04.notes.packet-cut.timestamp", "Store states are frozen to the 10 August 15:30 PT packet cut.", harm=2),
            leaf("p04.notes.packet-cut.change-record", "Later store-state updates require an annotated change record."),
        ],
    )

    # Page 5 - embedded raster escalation matrix.
    c = case.new_page(
        "Escalation matrix",
        subtitle="Functional owner status by store",
        section_code="RISK MATRIX",
    )
    stores = ["PDX-02", "PDX-05", "SEA-04", "SPK-03", "BND-01", "EUG-02"]
    functions = ["Gateway", "POS", "Staffing", "Partner"]
    matrix = {
        "PDX-02": ["G", "G", "G", "Y."],
        "PDX-05": ["Y/", "G", "G", "G"],
        "SEA-04": ["G", "G", "Y", "G"],
        "SPK-03": ["G", "Y", "G", "G"],
        "BND-01": ["R", "R/", "Y", "R/."],
        "EUG-02": ["G", "G", "G", "Y"],
    }
    image = Image.new("RGB", (1280, 720), "#f8f7f3")
    d = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=24)
    bold = ImageFont.load_default(size=27)
    x0, y0, cw, ch = 250, 110, 220, 78
    d.text((35, 28), "FUNCTIONAL ESCALATION MATRIX", font=bold, fill="#17202a")
    for col, function in enumerate(functions):
        d.text((x0 + col * cw + 50, y0 - 48), function, font=bold, fill="#17202a")
    colors = {"G": "#dbe9df", "Y": "#f5e7bc", "R": "#edd0d0"}
    for row, store in enumerate(stores):
        y = y0 + row * ch
        d.text((38, y + 24), store, font=bold, fill="#17202a")
        for col, state in enumerate(matrix[store]):
            x = x0 + col * cw
            d.rounded_rectangle((x, y, x + cw - 18, y + ch - 14), radius=10, fill=colors[state[0]], outline="#858b91", width=2)
            d.text((x + 72, y + 17), state[0], font=bold, fill="#17202a")
            if "/" in state:
                d.line((x + 126, y + 15, x + 160, y + 48), fill="#9e2a2b", width=5)
            if "." in state:
                d.ellipse((x + 170, y + 18, x + 188, y + 36), fill="#1d4e89")
    d.text((35, 630), "G clear   Y watch   R blocked   / executive escalation   dot external partner", font=font, fill="#303840")
    c.drawImage(image_reader(image), 42, 238, width=520, height=292, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(HexColor("#A8ADB2"))
    c.rect(42, 238, 520, 292, fill=0, stroke=1)
    draw_label(c, "Escalation convention", 42, 198)
    draw_paragraph(c, "A slash marks required executive escalation. A dot marks external-partner action. Symbols may appear together in one cell.", 42, 180, 510, size=8.2, leading=11)
    matrix_rows = [[store, *matrix[store]] for store in stores]
    case.add_gold(
        "Escalation matrix",
        "Legend: G = clear; Y = watch; R = blocked; slash = executive escalation; dot = external-partner action.\n\n"
        + markdown_table(["Store", *functions], matrix_rows),
    )
    matrix_leaves = [
        leaf("p05.legend.g", "Matrix legend maps G to clear."),
        leaf("p05.legend.y", "Matrix legend maps Y to watch."),
        leaf("p05.legend.r", "Matrix legend maps R to blocked."),
        leaf("p05.legend.slash", "Matrix slash means executive escalation.", harm=2),
        leaf("p05.legend.dot", "Matrix dot means external-partner action."),
    ]
    for store in stores:
        for function, state in zip(functions, matrix[store]):
            cell_id = f"p05.matrix.{store.lower()}.{function.lower()}"
            consequential = store == "BND-01" and function in {"POS", "Partner"}
            matrix_leaves.append(
                leaf(
                    f"{cell_id}.state",
                    f"The {store} {function} cell base state is {state[0]}.",
                    harm=2 if consequential else 1,
                )
            )
            if "/" in state:
                matrix_leaves.append(
                    leaf(
                        f"{cell_id}.executive-escalation",
                        f"The {store} {function} cell carries the executive-escalation slash.",
                        harm=2 if consequential else 1,
                    )
                )
            if "." in state:
                matrix_leaves.append(
                    leaf(
                        f"{cell_id}.external-partner",
                        f"The {store} {function} cell carries the external-partner dot.",
                        harm=2 if consequential else 1,
                    )
                )
    case.add_region("p05.matrix", "Raster escalation matrix", "diagram", matrix_leaves, budget=2, closed_world=True)

    # Page 6 - procurement ledger.
    c = case.new_page(
        "Launch reserve ledger",
        subtitle="Approved categories and current exposure",
        section_code="FIN-RESERVE",
    )
    ledger_headers = ["Vendor", "Purpose", "Invoice", "Eligibility", "Paid", "Exposure"]
    ledger_rows = [
        ["LumenWorks", "gateway freight", "$12,640", "Eligible", "$0", "$12,640"],
        ["FieldBridge", "floor support", "$5,760", "Eligible", "$2,000", "$3,760"],
        ["SignPro", "signage reprint", "$3,480", "Not eligible", "$0", "$0"],
        ["SwitchOps", "monitoring cover", "$2,900", "Not eligible", "$0", "$0"],
        ["Northstar Print", "counter cards", "$740", "Not eligible", "$740", "$0"],
    ]
    draw_table(c, 42, 650, [82, 115, 69, 76, 60, 70], [ledger_headers, *ledger_rows], font_size=7.1, zebra=True)
    totals = [
        ["Eligible invoices before payments", "$18,400"],
        ["FieldBridge payment applied", "-$2,000"],
        ["Remaining eligible exposure", "$16,400"],
    ]
    draw_label(c, "Reconciliation", 330, 400)
    draw_table(c, 330, 385, [150, 82], [["Line", "Amount"], *totals], font_size=8)
    draw_label(c, "Finance note", 42, 400)
    draw_paragraph(c, "Partial payment applies only to FieldBridge. Non-eligible invoices remain in the packet but do not consume launch reserve.", 42, 382, 250, size=8.3, leading=11.5)
    approval_trail = (
        "Finance controller Iris Wu approved the $18,400 eligible invoice base on 9 August. "
        "The $2,000 FieldBridge payment posted on 10 August at 12:40 PT; the reconciliation above is after that posting."
    )
    draw_label(c, "Approval trail", 42, 245)
    draw_paragraph(c, approval_trail, 42, 227, 510, size=8.4, leading=11.5)
    case.add_gold(
        "Launch reserve ledger",
        markdown_table(ledger_headers, ledger_rows)
        + "\n\n"
        + markdown_table(["Line", "Amount"], totals)
        + "\n\nPartial payment applies only to FieldBridge. Non-eligible invoices do not consume launch reserve.\n\n"
        + approval_trail,
    )
    case.add_region(
        "p06.ledger",
        "Reserve ledger",
        "table",
        table_leaves("p06.ledger", ledger_headers, ledger_rows),
        closed_world=True,
    )
    case.add_region(
        "p06.finance-note",
        "Finance note",
        "text",
        [
            leaf("p06.finance-note.partial", "Partial payment applies only to FieldBridge."),
            leaf("p06.finance-note.ineligible", "Non-eligible invoices do not consume launch reserve."),
            leaf("p06.finance-note.approval", "Iris Wu approved the $18,400 eligible invoice base on 9 August."),
            leaf("p06.finance-note.posting-time", "The $2,000 FieldBridge payment posted on 10 August at 12:40 PT."),
            leaf("p06.finance-note.reconciliation-state", "The displayed reconciliation is after the FieldBridge payment posting."),
        ],
    )
    case.add_region(
        "p06.reconciliation",
        "Reserve reconciliation",
        "table",
        table_leaves(
            "p06.reconciliation",
            ["Line", "Amount"],
            totals,
            consequential={("Remaining eligible exposure", "Amount")},
        ),
        budget=2,
        closed_world=True,
    )

    # Page 7 - visibly superseded appendix.
    c = case.new_page(
        "Appendix C - 7 August working snapshot",
        subtitle="Version 0.7 | Superseded by steering packet issued 10 August 2026",
        section_code="HISTORICAL",
    )
    c.saveState()
    c.setFillColor(HexColor("#E6E2DA"))
    c.setFont("DocSans-Bold", 48)
    c.translate(135, 315)
    c.rotate(34)
    c.drawString(0, 0, "SUPERSEDED")
    c.restoreState()
    draft_headers = ["Field", "Working value", "Status on 7 Aug"]
    draft_rows = [
        ["Steering decision", "GO", "draft"],
        ["Tier 2 backlog", "18", "draft"],
        ["Gateway spare units", "158", "draft"],
        ["Bend POS", "OK", "draft"],
        ["Reserve exposure", "$17,300", "draft"],
    ]
    draw_table(c, 72, 580, [175, 150, 150], [draft_headers, *draft_rows], font_size=8.4)
    c.setFillColor(RED)
    c.setFont("DocSans-Bold", 9)
    c.drawString(72, 300, "Supersession record")
    draw_paragraph(c, "Version 0.7 was replaced in full by OPS-NW-26-08 on 10 August at 09:15 PT. No value on this page is current.", 72, 280, 455, size=9, leading=12, color=RED)
    case.add_gold(
        "Superseded appendix",
        "Appendix C version 0.7 was superseded in full by OPS-NW-26-08 on 2026-08-10 at 09:15 PT. Its values remain historical and are not current.\n\n"
        + markdown_table(draft_headers, draft_rows),
    )
    case.add_region(
        "p07.supersession",
        "Supersession record",
        "text",
        [
            leaf("p07.supersession.version", "Appendix C is version 0.7 dated 7 August."),
            leaf("p07.supersession.control", "OPS-NW-26-08 superseded the appendix in full on 2026-08-10 at 09:15 PT.", harm=2),
            leaf("p07.supersession.state", "No working value in the appendix is current.", harm=2),
        ],
        budget=2,
    )
    case.add_region(
        "p07.draft",
        "Historical working values",
        "table",
        table_leaves("p07.draft", draft_headers, draft_rows),
        closed_world=True,
    )

    return case.finish()
