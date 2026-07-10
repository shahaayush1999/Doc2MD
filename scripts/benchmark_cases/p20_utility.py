from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
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
    draw_checkbox,
    draw_label,
    draw_paragraph,
    draw_table,
    image_reader,
    leaf,
    make_scan,
    markdown_table,
    table_leaves,
)


ASSET_DIR = Path(__file__).with_name("assets")


def _field_photo(kind: str, seed: int) -> Image.Image:
    del seed  # Kept in the call signature to make the source-record IDs explicit.
    asset_names = {
        "cutout": "p20-field-cutout.png",
        "clear": "p20-field-clear-span.png",
        "switch": "p20-field-open-switch.png",
    }
    source = Image.open(ASSET_DIR / asset_names[kind]).convert("RGB")
    image = ImageOps.fit(source, (920, 560), method=Image.Resampling.LANCZOS)
    annotation = ImageDraw.Draw(image)
    if kind == "cutout":
        annotation.ellipse((410, 150, 515, 330), outline="#9f1f1f", width=7)
        annotation.line((505, 165, 690, 78), fill="#9f1f1f", width=4)
        annotation.rectangle((680, 50, 870, 112), fill="#f4eee4", outline="#9f1f1f", width=3)
        annotation.text((698, 68), "split / char", font=ImageFont.load_default(size=21), fill="#7b1818")
    elif kind == "clear":
        annotation.rectangle((350, 250, 555, 310), fill="#d4e0e4", outline="#33506a", width=3)
        annotation.text((375, 267), "clear span", font=ImageFont.load_default(size=24), fill="#24475f")
    else:
        annotation.rectangle((545, 335, 655, 430), fill="#f2d64b", outline="#6d5d00", width=4)
        annotation.text((562, 363), "S-18", font=ImageFont.load_default(size=20), fill="#4e4300")
        annotation.text((560, 389), "OPEN", font=ImageFont.load_default(size=20), fill="#4e4300")
    return image


def build(output_root):
    case = CaseBuilder(
        output_root=output_root,
        case_id="P20-utility-outage-restoration",
        title="Feeder 12R Outage Investigation",
        family="electric utility incident operations",
        tags=["native-pdf", "scada", "switching-log", "one-line", "restoration-chart", "field-photos", "redline", "source-precedence"],
        page_count=8,
        purpose="Test event chronology, switching dependencies, directed feeder topology, quantitative restoration, real image regions, redlined cause revision, and signed final state.",
        source_modality="born-digital native incident packet with embedded field-photo and scanned working-copy regions",
        document_ref="METROGRID · OI-26-731 · CONTROLLED INCIDENT FILE",
        metadata_date="D:20260703112100-05'00'",
    )

    # Page 1 - incident record without premature cause conclusion.
    c = case.new_page(
        "OI-26-731 / Feeder 12R incident record",
        subtitle="MetroGrid Electric | Portland North district | Event 2 July 2026",
        section_code="OPERATIONS COPY",
    )
    draw_badge(c, "Closed", 42, 684, GREEN)
    summary_headers = ["Field", "Recorded value"]
    summary_rows = [
        ["Outage start", "2 Jul 2026 15:42"],
        ["Customers interrupted", "8,960"],
        ["Critical customers", "Hospital loop; traffic signal TS-12; lift station LS-4"],
        ["Hospital restoration", "17:18 via tie T-7"],
        ["All-customer restoration", "19:06 via R12 breaker close"],
        ["Network normalized", "19:32 after T-7 opened"],
    ]
    draw_label(c, "Event record", 42, 650)
    draw_table(c, 42, 635, [160, 350], [summary_headers, *summary_rows], font_size=8, zebra=True)
    source_headers = ["Record", "Clock basis", "Custodian", "State"]
    source_rows = [
        ["SCADA alarm export", "Sub-second", "System control", "Frozen 20:00"],
        ["Switching order 12R-731", "24-hour local", "Control room", "Signed"],
        ["OMS restoration series", "5-minute bins", "Outage management", "Final"],
        ["Patrol media P1-P3", "GPS device time", "Crew A", "Uploaded"],
        ["Investigation report", "Revision 2", "Protection engineering", "Signed 3 Jul"],
    ]
    draw_label(c, "Incident source register", 42, 390)
    draw_table(c, 42, 375, [150, 108, 120, 115], [source_headers, *source_rows], font_size=7.3, zebra=True)
    case.add_gold("Incident record", markdown_table(summary_headers, summary_rows) + "\n\n" + markdown_table(source_headers, source_rows))
    case.add_region("p01.summary", "Incident event record", "table", table_leaves("p01.summary", summary_headers, summary_rows, consequential={("Hospital restoration", "Recorded value"), ("All-customer restoration", "Recorded value")}), budget=2, closed_world=True)
    case.add_region("p01.sources", "Incident source register", "table", table_leaves("p01.sources", source_headers, source_rows), closed_world=True)

    # Page 2 - SCADA sequence.
    c = case.new_page(
        "SCADA alarm sequence",
        subtitle="Sequence exported from control historian at 20:00 local",
        section_code="SCADA-12R",
    )
    alarm_headers = ["Time", "Device", "State", "System note"]
    alarm_rows = [
        ["15:42:11", "R12 breaker", "Trip", "Phase B ground"],
        ["15:42:14", "Recloser 12R-3", "Lockout", "Third shot"],
        ["15:42:19", "Relay 50G", "Pickup", "7.8 kA momentary"],
        ["15:43:02", "Cap bank CB-4", "Offline", "Voltage sag"],
        ["15:44:33", "OMS", "8,960 out", "Nested outage created"],
        ["16:05:20", "Switch S-18", "Opened", "Crew isolation"],
        ["16:31:05", "Switch S-22", "Opened", "Riverside isolated"],
        ["17:11:00", "DER-44", "0 kW", "Curtailment verified"],
        ["17:18:44", "Tie T-7", "Closed", "Hospital backfeed"],
        ["18:05:02", "F-12B", "Replaced", "Maple test passed"],
        ["18:55:18", "Switch S-18", "Closed", "Upstream path staged"],
        ["19:00:41", "Switch S-22", "Closed", "Riverside path staged"],
        ["19:06:10", "R12 breaker", "Closed", "Normal source restored"],
    ]
    draw_table(c, 42, 665, [88, 135, 105, 190], [alarm_headers, *alarm_rows], font_size=7.2, zebra=True)
    c.setFillColor(MUTED)
    c.setFont("DocSans-Italic", 7.5)
    c.drawString(42, 245, "Timestamps are historian event times; switching-order times on the following page are minute-level operator entries.")
    case.add_gold("SCADA alarm sequence", markdown_table(alarm_headers, alarm_rows))
    case.add_region("p02.alarms", "SCADA alarm sequence", "table", table_leaves("p02.alarms", alarm_headers, alarm_rows, consequential={("15:42:11", "State"), ("17:18:44", "State"), ("19:06:10", "State")}), budget=2, closed_world=True)

    # Page 3 - switching log.
    c = case.new_page(
        "Switching order 12R-731",
        subtitle="Operator entries and cumulative customers restored",
        section_code="SIGNED ORDER",
    )
    switch_headers = ["Step", "Time", "Action", "Authority", "Cumulative restored"]
    switch_rows = [
        ["1", "16:05", "Open S-18", "Crew A / Control", "0"],
        ["2", "16:31", "Open S-22", "Crew B / Control", "0"],
        ["3", "16:47", "Test Maple lateral", "Crew A", "0"],
        ["4", "17:11", "Verify DER-44 at 0 kW", "System control", "0"],
        ["5", "17:18", "Close tie T-7", "Crew C / Control", "4,820"],
        ["6", "18:05", "Replace and test F-12B", "Crew A", "6,140"],
        ["7", "18:42", "Patrol Riverside taps", "Crew B", "6,140"],
        ["8", "18:55", "Close S-18", "Crew A / Control", "6,140"],
        ["9", "19:00", "Close S-22", "Crew B / Control", "6,140"],
        ["10", "19:06", "Close R12 breaker", "System control", "8,960"],
        ["11", "19:32", "Open T-7 / normalize", "Crew C / Control", "8,960 stable"],
    ]
    draw_table(c, 42, 665, [45, 58, 205, 135, 115], [switch_headers, *switch_rows], font_size=7.1, zebra=True)
    sign_headers = ["Role", "Name", "Signed"]
    sign_rows = [
        ["Switching authority", "N. Ortega", "2 Jul 19:40"],
        ["Field lead", "R. Mehta", "2 Jul 19:44"],
        ["Control desk", "A. Patel", "2 Jul 19:45"],
    ]
    draw_label(c, "Order signoff", 42, 300)
    draw_table(c, 42, 285, [165, 170, 145], [sign_headers, *sign_rows], font_size=7.7, zebra=True)
    case.add_gold("Switching order", markdown_table(switch_headers, switch_rows) + "\n\n" + markdown_table(sign_headers, sign_rows))
    case.add_region("p03.switching", "Switching order", "table", table_leaves("p03.switching", switch_headers, switch_rows, consequential={("5", "Action"), ("8", "Action"), ("9", "Action"), ("10", "Cumulative restored")}), budget=2, closed_world=True)
    case.add_region("p03.signoff", "Switching-order signoff", "table", table_leaves("p03.signoff", sign_headers, sign_rows), closed_world=True)

    # Page 4 - feeder one-line and DER clearance.
    c = case.new_page(
        "Feeder one-line and DER clearance",
        subtitle="Normal feeder path, outage isolation, and temporary hospital backfeed",
        section_code="12R / 9Q",
    )
    nodes = {
        "R12 bay": (50, 540),
        "S-18": (150, 540),
        "F-12B": (250, 540),
        "S-22": (350, 540),
        "Riverside": (465, 540),
        "T-7": (350, 430),
        "Hospital": (465, 430),
        "DER-44": (250, 430),
        "Feeder 9Q": (350, 335),
    }
    for label, (x, y) in nodes.items():
        c.setFillColor(HexColor("#F4F5F5"))
        c.setStrokeColor(INK)
        c.roundRect(x, y, 78, 30, 3, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("DocSans-Bold", 6)
        c.drawCentredString(x + 39, y + 11, label)
    edges = [
        ("R12 bay", "S-18", "normal feed"),
        ("S-18", "F-12B", "Maple lateral"),
        ("F-12B", "S-22", "12R trunk"),
        ("S-22", "Riverside", "12R load"),
        ("S-22", "T-7", "tie branch"),
        ("T-7", "Hospital", "temporary backfeed"),
        ("Feeder 9Q", "T-7", "9Q source"),
        ("DER-44", "F-12B", "PV backfeed risk"),
    ]
    label_positions = {
        ("R12 bay", "S-18"): (130, 563),
        ("S-18", "F-12B"): (223, 563),
        ("F-12B", "S-22"): (326, 563),
        ("S-22", "Riverside"): (438, 563),
        ("S-22", "T-7"): (397, 493),
        ("T-7", "Hospital"): (430, 453),
        ("Feeder 9Q", "T-7"): (397, 395),
        ("DER-44", "F-12B"): (285, 493),
    }
    for source, destination, edge_label in edges:
        sx, sy = nodes[source]
        dx, dy = nodes[destination]
        if sy == dy:
            draw_arrow(c, sx + 78, sy + 15, dx, dy + 15, color=BLUE, width=1.2)
        elif sy > dy:
            draw_arrow(c, sx + 39, sy, dx + 39, dy + 30, color=BLUE, width=1.2)
        else:
            draw_arrow(c, sx + 39, sy + 30, dx + 39, dy, color=BLUE, width=1.2)
        lx, ly = label_positions[(source, destination)]
        c.setFillColor(MUTED)
        c.setFont("DocSans", 5.8)
        c.drawCentredString(lx, ly, edge_label)
    c.setFillColor(RED)
    c.setFont("DocSans-Bold", 7)
    c.drawString(252, 580, "fault / replaced")
    clearance_headers = ["Clearance item", "Operator entry", "Field confirmation", "State"]
    clearance_rows = [
        ["DER-44 disconnect", "Open 17:06", "Visible at POI", "Accepted"],
        ["SCADA output", "0 kW 17:11", "Stable 5 min", "Accepted"],
        ["Feeder 9Q load", "74% after transfer", "Below emergency rating", "Accepted"],
        ["Reverse power", "None", "Relay 67P clear", "Accepted"],
        ["Hospital ATS", "Normal source lost", "T-7 source accepted", "Accepted"],
        ["T-7 permission", "Issued 17:16", "Close at 17:18", "Accepted"],
        ["DER restore", "After normalize", "Site call 19:34", "Deferred"],
    ]
    draw_label(c, "DER and transfer clearance", 42, 300)
    draw_table(c, 42, 285, [128, 130, 180, 90], [clearance_headers, *clearance_rows], font_size=6.65, zebra=True)
    case.add_gold("Feeder one-line and DER clearance", "Directed feeder relations: " + "; ".join(f"{source} -> {destination} ({label})" for source, destination, label in edges) + ".\n\n" + markdown_table(clearance_headers, clearance_rows))
    case.add_region("p04.oneline", "Feeder one-line", "diagram", [leaf(f"p04.edge.{index:02d}", f"A directed relation runs from {source} to {destination} for {label}.", harm=2 if destination in {"T-7", "Hospital"} else 1) for index, (source, destination, label) in enumerate(edges, start=1)], budget=2)
    case.add_region("p04.clearance", "DER and transfer clearance", "table", table_leaves("p04.clearance", clearance_headers, clearance_rows, consequential={("SCADA output", "State"), ("T-7 permission", "State")}), budget=2, closed_world=True)

    # Page 5 - restoration chart and customer impact.
    c = case.new_page(
        "Restoration progression and customer impact",
        subtitle="OMS final series; customer restoration ends at 19:06",
        section_code="OMS FINAL",
    )
    series = [("15:42", 0), ("16:31", 0), ("17:18", 4820), ("18:05", 6140), ("19:06", 8960), ("19:32", 8960)]
    ox, oy, width, height = 70, 485, 470, 165
    c.setStrokeColor(INK)
    c.line(ox, oy, ox + width, oy)
    c.line(ox, oy, ox, oy + height)
    points = []
    for index, (time, value) in enumerate(series):
        x = ox + 18 + index * 86
        y = oy + 10 + value / 8960 * 140
        points.append((x, y))
        c.setFillColor(BLUE)
        c.circle(x, y, 3, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("DocSans-Bold", 6.3)
        c.drawCentredString(x, y + 9, f"{value:,}")
        c.setFont("DocSans", 6.2)
        c.drawCentredString(x, oy - 14, time)
    c.setStrokeColor(BLUE)
    c.setLineWidth(1.6)
    for first, second in zip(points, points[1:]):
        c.line(first[0], first[1], second[0], second[1])
    impact_headers = ["Segment", "Customers", "Critical load", "Restored"]
    impact_rows = [
        ["9Q transfer block", "4,820", "Includes hospital + TS-12", "17:18"],
        ["Hospital loop", "1,240", "Hospital", "17:18"],
        ["TS-12", "1 service", "Traffic signal", "17:18"],
        ["Maple tested block", "1,320", "Includes care home spur", "18:05"],
        ["Care home spur", "86", "Assisted living", "18:05"],
        ["Riverside / industrial block", "2,820", "Includes LS-4", "19:06"],
        ["LS-4", "1 service", "Lift station", "19:06"],
    ]
    draw_label(c, "Customer impact", 42, 430)
    draw_table(c, 42, 415, [160, 90, 145, 82], [impact_headers, *impact_rows], font_size=7.2, zebra=True)
    c.setFillColor(MUTED)
    c.setFont("DocSans-Italic", 6.7)
    c.drawString(42, 245, "Parent blocks reconcile to 8,960; critical-service rows are nested callouts and are not added again.")
    case.add_gold("Restoration progression and customer impact", "OMS cumulative restoration: " + ", ".join(f"{time} = {value:,}" for time, value in series) + ". The parent-block increments are 4,820 at 17:18, 1,320 at 18:05, and 2,820 at 19:06, totaling 8,960. The 19:32 value is normalization, not a new customer restoration. Critical-service rows are nested callouts and must not be added again.\n\n" + markdown_table(impact_headers, impact_rows))
    case.add_region("p05.restoration", "OMS restoration chart", "chart", [leaf(f"p05.restoration.{time.replace(':', '')}", f"Cumulative customers restored at {time} are {value:,}.", harm=2 if time in {"17:18", "19:06"} else 1) for time, value in series], budget=2)
    impact_leaves = table_leaves("p05.impact", impact_headers, impact_rows, consequential={("Hospital loop", "Restored")})
    impact_leaves.extend(
        [
            leaf("p05.impact.reconciliation", "The three parent blocks reconcile to 8,960 customers.", harm=2),
            leaf("p05.impact.nesting", "Critical-service rows are nested callouts and are not added again.", harm=2),
        ]
    )
    case.add_region("p05.impact", "Customer impact table", "table", impact_leaves, budget=2, closed_world=True)

    # Page 6 - actual field photo regions.
    c = case.new_page(
        "Patrol field media",
        subtitle="Crew A uploads with GPS device time; original files retained in incident archive",
        section_code="P1-P3",
    )
    photos = [
        ("P1", "F-12B / 16:18", _field_photo("cutout", 2001)),
        ("P2", "Maple span / 16:23", _field_photo("clear", 2002)),
        ("P3", "S-18 / 16:31", _field_photo("switch", 2003)),
    ]
    for index, (photo_id, caption, photo) in enumerate(photos):
        y = 510 - index * 185
        c.drawImage(image_reader(photo), 42, y, width=230, height=140, preserveAspectRatio=True, mask="auto")
        c.setStrokeColor(HexColor("#969CA2"))
        c.rect(42, y, 230, 140, fill=0, stroke=1)
        c.setFillColor(INK)
        c.setFont("DocSans-Bold", 8)
        c.drawString(292, y + 115, f"{photo_id}  {caption}")
        if photo_id == "P1":
            draw_paragraph(c, "Blackened split polymer barrel is visible below the phase-B conductor. The red review circle is on the damaged cutout.", 292, y + 92, 260, size=8, leading=11)
        elif photo_id == "P2":
            draw_paragraph(c, "The span between the two poles is clear. Vegetation is set back and no branch touches either conductor.", 292, y + 92, 260, size=8, leading=11)
        else:
            draw_paragraph(c, "The switch blade is visibly open and the yellow S-18 OPEN hold tag is attached below the blade.", 292, y + 92, 260, size=8, leading=11)
    case.add_gold("Patrol field media", "P1 F-12B at 16:18 shows a blackened split polymer cutout barrel under the phase-B conductor. P2 Maple span at 16:23 shows a clear span with vegetation set back and no branch contact. P3 S-18 at 16:31 shows the switch blade open with a yellow S-18 OPEN hold tag.")
    case.add_region(
        "p06.photo.p1",
        "P1 damaged cutout photograph",
        "image",
        [
            leaf("p06.p1.device", "P1 is bound to F-12B at 16:18."),
            leaf(
                "p06.p1.damage",
                "P1 visibly shows a blackened split polymer cutout barrel below the phase-B conductor.",
                harm=2,
                allow_partial=True,
            ),
        ],
    )
    case.add_region("p06.photo.p2", "P2 clear-span photograph", "image", [leaf("p06.p2.location", "P2 is the Maple span at 16:23."), leaf("p06.p2.clear", "P2 visibly shows a clear span with no branch touching the conductors.", harm=2)])
    case.add_region(
        "p06.photo.p3",
        "P3 open-switch photograph",
        "image",
        [
            leaf("p06.p3.device", "P3 is S-18 at 16:31."),
            leaf("p06.p3.blade", "P3 visibly shows an open switch blade.", harm=2),
            leaf("p06.p3.tag", "P3 visibly shows a yellow S-18 OPEN hold tag."),
        ],
    )

    # Page 7 - scanned redlined draft and supporting evidence.
    c = case.new_page(
        "Draft investigation report / reviewer markup",
        subtitle="Revision 1 retained in the incident file; signed Revision 2 follows",
        section_code="DRAFT / REDLINE",
    )
    scan_lines = [
        "METROGRID OUTAGE INVESTIGATION / REVISION 1",
        "Event OI-26-731 / Feeder 12R / prepared 02 Jul 21:10",
        "",
        "Preliminary cause: TREE CONTACT on Maple lateral.",
        "Hospital loop restored: 18:05.",
        "DER-44 status: not recorded.",
        "Weather: 46 mph gust; primary cause pending review.",
        "",
        "PROTECTION REVIEW / 03 JUL 08:35",
        "Cause revised to failed polymer cutout F-12B.",
        "Hospital restored 17:18 via T-7; 18:05 is Maple lateral.",
        "DER-44 curtailed to 0 kW at 17:11 before tie close.",
        "Weather retained as context; P2 rules out tree contact.",
    ]
    scan = make_scan("OUTAGE REPORT - WORKING COPY", scan_lines, width=1350, height=770, seed=2007, marks=[(55, 198, "strike"), (55, 231, "strike"), (980, 190, "F-12B"), (980, 226, "17:18")])
    c.drawImage(image_reader(scan), 42, 340, width=528, height=300, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(HexColor("#969CA2"))
    c.rect(42, 340, 528, 300, fill=0, stroke=1)
    evidence_headers = ["Evidence", "Observed state", "Use in Revision 2"]
    evidence_rows = [
        ["Photo P1", "Split / char at F-12B", "Supports equipment failure"],
        ["Photo P2", "Clear span / no contact", "Rejects tree-contact draft"],
        ["Relay 50G", "Single phase-ground impulse", "Matches failed cutout"],
        ["Cutout tag F12B-882", "Polymer barrel split", "Asset-lab teardown"],
        ["Lightning log", "None within 5 miles", "Not causal"],
    ]
    draw_label(c, "Reviewer evidence matrix", 42, 305)
    draw_table(c, 42, 290, [130, 180, 190], [evidence_headers, *evidence_rows], font_size=7.1, zebra=True)
    case.add_gold("Draft report and reviewer markup", "Revision 1 preliminary cause TREE CONTACT is struck out and revised to failed polymer cutout F-12B. Hospital restoration 18:05 is struck and corrected to 17:18 via T-7. DER-44 status is corrected to curtailed at 17:11. Weather is context; P2 rules out tree contact.\n\n" + markdown_table(evidence_headers, evidence_rows))
    case.add_region("p07.redline", "Scanned redlined draft report", "form", [leaf("p07.redline.cause-old", "TREE CONTACT is visibly struck as the Revision 1 preliminary cause."), leaf("p07.redline.cause-new", "The cause correction is failed polymer cutout F-12B.", harm=2), leaf("p07.redline.hospital", "Hospital restoration is corrected from 18:05 to 17:18 via T-7.", harm=2), leaf("p07.redline.der", "DER-44 status is corrected to curtailed at 17:11."), leaf("p07.redline.weather", "Weather is retained as context rather than the final cause.")], budget=2)
    case.add_region("p07.evidence", "Reviewer evidence matrix", "table", table_leaves("p07.evidence", evidence_headers, evidence_rows, consequential={("Photo P2", "Use in Revision 2")}), budget=2, closed_world=True)

    # Page 8 - signed final investigation and regulatory routing.
    c = case.new_page(
        "Revision 2 final investigation and notice",
        subtitle="Signed 3 July 2026 | controlling incident determination",
        section_code="FINAL / REV 2",
    )
    draw_badge(c, "Equipment failure", 42, 684, RED)
    final_headers = ["Control field", "Final value", "Basis"]
    final_rows = [
        ["Cause", "Failed polymer cutout F-12B", "P1 + relay + tag F12B-882"],
        ["Hospital restoration", "17:18", "T-7 switching step 5"],
        ["All customers restored", "19:06", "R12 close / OMS"],
        ["DER-44", "Curtailed 17:11", "0 kW before T-7 close"],
        ["Major-event threshold", "No", "8,960 customers / 3 h 24 m"],
        ["Follow-up", "WO-7714", "Replace peer cutouts / lab teardown"],
    ]
    draw_label(c, "Final determination", 42, 650)
    draw_table(c, 42, 635, [155, 165, 220], [final_headers, *final_rows], font_size=7.4, zebra=True)
    notice_headers = ["Recipient", "Channel", "Due / sent", "Payload"]
    notice_rows = [
        ["Hospital liaison", "Phone", "Sent 17:21", "Backfeed restored"],
        ["City OEM", "Email", "Sent 18:12", "Critical-load update"],
        ["State PUC log", "Portal", "Due 05 Jul 12:00", "Below major threshold"],
        ["DER owner", "Phone", "Sent 19:34", "Normalization complete"],
        ["Asset engineering", "Work order", "Sent 03 Jul 09:05", "F12B-882 teardown"],
        ["Vegetation contractor", "No dispatch", "Not required", "P2 rules out tree contact"],
    ]
    draw_label(c, "Notice routing", 42, 370)
    draw_table(c, 42, 355, [135, 90, 130, 180], [notice_headers, *notice_rows], font_size=6.9, zebra=True)
    draw_label(c, "Final signoff", 42, 125)
    draw_checkbox(c, 44, 91, "checked", "Operations sequence / N. Ortega 09:12")
    draw_checkbox(c, 280, 91, "checked", "Protection / R. Mehta 10:44")
    draw_checkbox(c, 44, 64, "checked", "Regulatory / S. Kim 11:20")
    draw_checkbox(c, 280, 64, "disabled", "Vegetation / not required")
    case.add_gold("Revision 2 final investigation and notice", markdown_table(final_headers, final_rows) + "\n\n" + markdown_table(notice_headers, notice_rows) + "\n\nFinal signoff: Operations/N. Ortega checked at 09:12; Protection/R. Mehta checked at 10:44; Regulatory/S. Kim checked at 11:20; Vegetation is disabled/not required.")
    case.add_region("p08.final", "Final incident determination", "table", table_leaves("p08.final", final_headers, final_rows, consequential={("Cause", "Final value"), ("Hospital restoration", "Final value")}), budget=2, closed_world=True)
    case.add_region("p08.notices", "Regulatory and stakeholder routing", "table", table_leaves("p08.notices", notice_headers, notice_rows), closed_world=True)
    case.add_region(
        "p08.signoff",
        "Final investigation signoff",
        "form",
        [
            leaf(
                "p08.signoff.ops",
                "Operations sequence is checked and signed by N. Ortega at 09:12.",
                allow_partial=True,
            ),
            leaf(
                "p08.signoff.protection",
                "Protection review is checked and signed by R. Mehta at 10:44.",
                allow_partial=True,
            ),
            leaf(
                "p08.signoff.regulatory",
                "Regulatory review is checked and signed by S. Kim at 11:20.",
                allow_partial=True,
            ),
            leaf("p08.signoff.vegetation", "Vegetation review is disabled and marked not required."),
        ],
    )

    return case.finish()
