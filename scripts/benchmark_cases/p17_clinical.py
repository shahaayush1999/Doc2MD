from __future__ import annotations

import random

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from reportlab.lib.colors import HexColor

from .common import (
    AMBER,
    BLUE,
    GREEN,
    INK,
    MUTED,
    RED,
    CaseBuilder,
    draw_badge,
    draw_checkbox,
    draw_label,
    draw_paragraph,
    draw_table,
    image_reader,
    leaf,
    markdown_table,
    table_leaves,
)


def _paper(width: int, height: int, seed: int) -> tuple[Image.Image, ImageDraw.ImageDraw, ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    rng = random.Random(seed)
    image = Image.new("L", (width, height), 246)
    pixels = image.load()
    for _ in range(width * height // 42):
        pixels[rng.randrange(width), rng.randrange(height)] = rng.randrange(225, 250)
    image = image.filter(ImageFilter.GaussianBlur(0.22))
    draw = ImageDraw.Draw(image)
    regular = ImageFont.load_default(size=18)
    bold = ImageFont.load_default(size=21)
    return image, draw, regular, bold


def _box(draw: ImageDraw.ImageDraw, x: int, y: int, state: str) -> None:
    draw.rectangle((x, y, x + 24, y + 24), outline=45, width=2)
    if state == "checked":
        draw.line((x + 3, y + 13, x + 10, y + 21), fill=30, width=4)
        draw.line((x + 10, y + 21, x + 23, y + 2), fill=30, width=4)
    elif state == "crossed":
        draw.line((x + 2, y + 2, x + 22, y + 22), fill=35, width=3)
        draw.line((x + 22, y + 2, x + 2, y + 22), fill=35, width=3)


def _ecrf_scan() -> Image.Image:
    image, draw, regular, bold = _paper(1400, 900, 1707)
    draw.text((48, 34), "HTX-204 ELECTROCARDIOGRAM eCRF / SITE 014", font=bold, fill=25)
    draw.line((48, 75, 1350, 75), fill=80, width=2)
    draw.text((55, 104), "Subject: 014-003       Visit: W2       Date: 21 Apr 2026", font=regular, fill=35)
    draw.text((55, 157), "ECG performed", font=bold, fill=25)
    _box(draw, 295, 151, "crossed")
    draw.text((330, 157), "Yes - original entry 21 Apr 09:02", font=regular, fill=45)
    _box(draw, 295, 201, "checked")
    draw.text((330, 207), "No - corrected entry 22 Apr 14:18", font=regular, fill=25)
    draw.text((55, 268), "Reason not performed: ECG machine unavailable; replacement due 23 Apr.", font=regular, fill=35)
    draw.text((55, 318), "Associated deviation: DEV-014-03 (major)", font=regular, fill=35)
    draw.text((55, 358), "Data query: Q-77 OPEN / PI response pending", font=bold, fill=25)
    draw.rectangle((50, 415, 1340, 610), outline=95, width=2)
    draw.text((70, 435), "CORRECTION CERTIFICATION", font=bold, fill=30)
    draw.text((70, 482), "Original checked-Yes entry was transcribed from the visit worksheet in error.", font=regular, fill=35)
    draw.text((70, 522), "Source note confirms no tracing was acquired. Final source value is NO.", font=regular, fill=35)
    draw.text((70, 570), "Coordinator: MK / 22 Apr 14:18     Monitor verified: LS / 08 May", font=regular, fill=35)
    draw.text((55, 680), "PI review of DEV-014-03", font=regular, fill=35)
    _box(draw, 375, 674, "")
    draw.text((414, 680), "Not yet completed", font=regular, fill=35)
    draw.text((55, 760), "No erasure used. Both the original and corrected states remain visible.", font=regular, fill=45)
    return ImageEnhance.Contrast(image).enhance(1.08).convert("RGB")


def _temperature_scan() -> Image.Image:
    image, draw, regular, bold = _paper(1400, 820, 1708)
    draw.text((48, 34), "INVESTIGATIONAL PRODUCT TEMPERATURE EXCURSION", font=bold, fill=25)
    draw.line((48, 75, 1350, 75), fill=80, width=2)
    draw.text((55, 105), "Kit K-204-153 / Subject 014-007 / Refrigerator RX-2", font=regular, fill=35)
    rows = [
        ("18 Apr 09:10", "8.4 C", "Alarm acknowledged"),
        ("18 Apr 10:10", "9.1 C", "Kit quarantined"),
        ("18 Apr 11:10", "8.8 C", "Unblinded pharmacist notified"),
        ("18 Apr 12:10", "7.8 C", "Above range"),
        ("18 Apr 13:05", "5.2 C", "Returned to range"),
        ("18 Apr 13:40", "4.7 C", "Stable; quarantine retained"),
    ]
    y = 165
    for time, value, action in rows:
        draw.text((65, y), time, font=regular, fill=35)
        draw.text((300, y), value, font=regular, fill=35)
        draw.text((430, y), action, font=regular, fill=35)
        draw.line((55, y + 28, 1330, y + 28), fill=180, width=1)
        y += 55
    draw.text((55, 515), "DISPOSITION", font=bold, fill=25)
    _box(draw, 55, 560, "")
    draw.text((92, 566), "Return to stock", font=regular, fill=35)
    _box(draw, 330, 560, "checked")
    draw.text((367, 566), "Do not dose", font=bold, fill=25)
    _box(draw, 610, 560, "")
    draw.text((647, 566), "Destroy", font=regular, fill=35)
    draw.text((55, 628), "Dispensed quantity: 0     Final inventory state: QUARANTINED", font=bold, fill=25)
    draw.text((55, 692), "Pharmacist RP / 18 Apr 14:02     Monitor LS / 08 May 11:20", font=regular, fill=35)
    return ImageEnhance.Contrast(image).enhance(1.08).convert("RGB")


def build(output_root):
    case = CaseBuilder(
        output_root=output_root,
        case_id="P17-clinical-trial-site-monitoring",
        title="HTX-204 Site 014 Monitoring File",
        family="clinical trial site operations",
        tags=["native-pdf", "longitudinal-records", "labs", "deviations", "corrected-ecrf", "accountability-form", "source-state"],
        page_count=9,
        purpose="Test longitudinal subject continuity, clinical table bindings, visible correction history, checkbox state, investigational-product accountability, and final site readiness.",
        source_modality="born-digital native monitoring file with embedded scanned eCRF and accountability-form regions",
        document_ref="HTX-204 · SITE 014 · MONITORING VISIT 03",
        metadata_date="D:20260629172100-05'00'",
    )

    # Page 1 - visit cover and source inventory.
    c = case.new_page(
        "Site 014 interim monitoring visit",
        subtitle="Helio Therapeutics | Protocol HTX-204 | Monitor L. Sen",
        section_code="VISIT 08 MAY 2026",
    )
    draw_badge(c, "Interim visit", 42, 684, BLUE)
    visit_headers = ["Field", "Value"]
    visit_rows = [
        ["Site", "014 / Harbor Endocrine"],
        ["Visit date", "8 May 2026"],
        ["Data cut", "6 May 2026"],
        ["Monitor", "L. Sen"],
        ["Principal investigator", "Dr. Neha Rao"],
        ["Subjects reviewed", "014-001 through 014-016"],
    ]
    draw_label(c, "Visit record", 42, 650)
    draw_table(c, 42, 635, [150, 355], [visit_headers, *visit_rows], font_size=8, zebra=True)
    inventory_headers = ["Source set", "Date range", "Custodian", "State"]
    inventory_rows = [
        ["Enrollment and visits", "2026-04-03–2026-05-06", "Coordinator", "Complete to cut"],
        ["Central laboratory", "2026-04-05–2026-05-06", "Lab portal", "Three follow-ups"],
        ["AE and deviation logs", "2026-04-10–2026-05-06", "PI / coordinator", "Open items noted"],
        ["IP accountability", "2026-04-05–2026-05-04", "Pharmacy", "One quarantine"],
        ["eCRF corrections", "2026-04-21–2026-05-08", "Data management", "Q-77 open"],
    ]
    draw_label(c, "Source inventory", 42, 405)
    draw_table(c, 42, 390, [145, 112, 110, 150], [inventory_headers, *inventory_rows], font_size=7.3, zebra=True)
    draw_paragraph(c, "The signed site-readiness determination appears on the final page after source review and correction verification.", 42, 175, 510, size=8.5, leading=12, color=MUTED)
    case.add_gold("Visit cover and source inventory", markdown_table(visit_headers, visit_rows) + "\n\n" + markdown_table(inventory_headers, inventory_rows))
    case.add_region("p01.visit", "Visit record", "table", table_leaves("p01.visit", visit_headers, visit_rows), closed_world=True)
    case.add_region("p01.inventory", "Source inventory", "table", table_leaves("p01.inventory", inventory_headers, inventory_rows), closed_world=True)

    # Page 2 - enrollment and disposition.
    c = case.new_page(
        "Enrollment and subject disposition",
        subtitle="Dates are enrollment dates; disposition is current at the 6 May data cut",
        section_code="SUBJECT LOG",
    )
    enroll_headers = ["Subject", "Enrollment", "Status", "Arm / reason", "Current disposition"]
    enroll_rows = [
        ["014-001", "03 Apr", "Screen fail", "HbA1c 9.1%", "Not randomized"],
        ["014-002", "05 Apr", "Randomized", "Arm B", "Completed W4"],
        ["014-003", "07 Apr", "Randomized", "Arm A", "W2 ECG unresolved"],
        ["014-004", "10 Apr", "Randomized", "Arm B", "Withdrew 24 Apr / dizziness"],
        ["014-005", "12 Apr", "Randomized", "Arm A", "Completed W4"],
        ["014-006", "15 Apr", "Screen fail", "eGFR 42", "Not randomized"],
        ["014-007", "18 Apr", "Randomized", "Arm B", "Kit quarantine"],
        ["014-008", "20 Apr", "Randomized", "Arm A", "Central lab pending"],
        ["014-009", "19 Apr", "Randomized", "Arm B", "W2 06 May outside window"],
        ["014-010", "23 Apr", "Screen fail", "QTc 486 ms", "Not randomized"],
        ["014-011", "26 Apr", "Randomized", "Arm A", "Repeat lab pending"],
        ["014-012", "28 Apr", "Randomized", "Arm B / waiver W-14", "Active"],
        ["014-013", "29 Apr", "Randomized", "Arm A", "Lost to follow-up 05 May"],
        ["014-014", "01 May", "Randomized", "Arm A", "ePRO retraining"],
        ["014-015", "02 May", "Screen fail", "BP 168/98", "Not randomized"],
        ["014-016", "04 May", "Randomized", "Arm B", "Masking review open"],
    ]
    draw_table(c, 42, 665, [62, 66, 77, 130, 190], [enroll_headers, *enroll_rows], font_size=6.25, zebra=True)
    case.add_gold("Enrollment and subject disposition", markdown_table(enroll_headers, enroll_rows))
    case.add_region("p02.enrollment", "Enrollment and subject disposition", "table", table_leaves("p02.enrollment", enroll_headers, enroll_rows, consequential={("014-003", "Current disposition"), ("014-004", "Current disposition"), ("014-007", "Current disposition")}), budget=2, closed_world=True)

    # Page 3 - longitudinal visit records.
    c = case.new_page(
        "Longitudinal visit record",
        subtitle="Selected subject visits with kits and visit-state evidence",
        section_code="VISIT GRID",
    )
    visit_grid_headers = ["Subject", "Visit", "Date", "State", "Kit", "Source note"]
    visit_grid_rows = [
        ["014-002", "V1", "05 Apr", "Done", "K-204-118", "ECG normal"],
        ["014-002", "W2", "19 Apr", "Done", "K-204-142", "Diary returned"],
        ["014-002", "W4", "03 May", "Done", "K-204-166", "Dose reduced"],
        ["014-003", "V1", "07 Apr", "Done", "K-204-121", "Baseline ECG filed"],
        ["014-003", "W2", "21 Apr", "Partial", "K-204-146", "ECG not performed"],
        ["014-004", "V1", "10 Apr", "Done", "K-204-128", "Dizziness began 11 Apr"],
        ["014-004", "Early term", "24 Apr", "Withdrawn", "-", "Related dizziness"],
        ["014-007", "V1", "18 Apr", "Hold", "K-204-153", "Temperature excursion"],
        ["014-007", "W2", "02 May", "Partial", "-", "Repeat potassium normal"],
        ["014-008", "V1", "20 Apr", "Done", "K-204-158", "Central lab pending"],
        ["014-009", "W2", "06 May", "Late", "K-204-181", "Day +17; +2 max"],
        ["014-011", "V1", "26 Apr", "Done", "K-204-171", "Repeat creatinine ordered"],
        ["014-014", "V1", "01 May", "Done", "K-204-184", "ePRO not activated"],
        ["014-016", "V1", "04 May", "Done", "K-204-190", "Masking note sealed"],
    ]
    draw_table(c, 42, 665, [63, 62, 60, 70, 88, 182], [visit_grid_headers, *visit_grid_rows], font_size=6.35, zebra=True)
    case.add_gold("Longitudinal visit record", markdown_table(visit_grid_headers, visit_grid_rows))
    case.add_region("p03.visits", "Longitudinal visit record", "table", table_leaves("p03.visits", visit_grid_headers, visit_grid_rows, key_column=2, consequential={("21 Apr", "Source note"), ("18 Apr", "State")}), budget=2, closed_world=True)

    # Page 4 - laboratory and adverse-event records.
    c = case.new_page(
        "Laboratory and adverse-event review",
        subtitle="Central laboratory flags and adverse-event follow-up at data cut",
        section_code="SAFETY REVIEW",
    )
    lab_headers = ["Subject / test", "Result", "Flag", "Reference", "Unit"]
    lab_rows = [
        ["014-002 / ALT", "38", "-", "0-45", "U/L"],
        ["014-003 / ALT", "67", "H", "0-45", "U/L"],
        ["014-003 / eGFR", "58", "L", ">=60", "mL/min"],
        ["014-004 / Hemoglobin", "10.8", "L", "12.0-16.0", "g/dL"],
        ["014-007 / Potassium", "5.6", "H", "3.5-5.1", "mmol/L"],
        ["014-009 / ALT", "49", "H", "0-45", "U/L"],
        ["014-011 / Creatinine", "1.34", "H", "0.60-1.30", "mg/dL"],
        ["014-016 / Glucose", "62", "L", "70-110", "mg/dL"],
    ]
    draw_label(c, "Central laboratory", 42, 665)
    draw_table(c, 42, 650, [170, 70, 50, 115, 90], [lab_headers, *lab_rows], font_size=7, zebra=True)
    ae_headers = ["AE", "Subject", "Term", "Severity", "Relatedness", "Outcome"]
    ae_rows = [
        ["AE-014-01", "014-004", "Dizziness", "Moderate", "Related", "Withdrew 24 Apr"],
        ["AE-014-02", "014-002", "Nausea", "Mild", "Possible", "Dose reduced W4"],
        ["AE-014-03", "014-007", "Hyperkalemia", "Moderate", "Unrelated", "Repeat normal"],
        ["AE-014-04", "014-011", "Creatinine increased", "Mild", "Possible", "Repeat pending"],
        ["AE-014-05", "014-016", "Hypoglycemia", "Moderate", "Related", "Safety call done"],
    ]
    draw_label(c, "Adverse events", 42, 360)
    draw_table(c, 42, 345, [82, 58, 105, 72, 78, 120], [ae_headers, *ae_rows], font_size=6.65, zebra=True)
    case.add_gold("Laboratory and adverse-event review", markdown_table(lab_headers, lab_rows) + "\n\n" + markdown_table(ae_headers, ae_rows))
    case.add_region("p04.labs", "Central laboratory table", "table", table_leaves("p04.labs", lab_headers, lab_rows, consequential={("014-003 / ALT", "Flag"), ("014-007 / Potassium", "Flag")}), budget=2, closed_world=True)
    case.add_region("p04.aes", "Adverse-event table", "table", table_leaves("p04.aes", ae_headers, ae_rows, consequential={("AE-014-01", "Outcome")}), budget=2, closed_world=True)

    # Page 5 - deviations and query state.
    c = case.new_page(
        "Protocol deviations and data queries",
        subtitle="Open and answered states at the monitoring data cut",
        section_code="ACTION LOG",
    )
    deviation_headers = ["Deviation", "Subject", "Description", "Class", "Current action"]
    deviation_rows = [
        ["DEV-014-03", "014-003", "W2 ECG not performed", "Major", "Q-77 open"],
        ["DEV-014-07", "014-007", "Kit at 9.1 C for 3 h", "Major", "Do not dose K-204-153"],
        ["DEV-014-02", "014-002", "Diary page late", "Minor", "Resolved"],
        ["DEV-014-08", "014-009", "W2 06 May; +2 max 05 May", "Minor", "Q-86 open"],
        ["DEV-014-09", "014-011", "Repeat central lab not filed", "Major", "Q-88 open"],
        ["DEV-014-10", "014-014", "ePRO not activated", "Minor", "Retraining done"],
        ["DEV-014-11", "014-016", "Unblinded pharmacy note", "Major", "Q-93 open"],
    ]
    draw_table(c, 42, 665, [88, 66, 195, 62, 130], [deviation_headers, *deviation_rows], font_size=6.7, zebra=True)
    query_headers = ["Query", "Subject", "Issue", "State"]
    query_rows = [
        ["Q-74", "014-004", "AE stop date", "Answered 26 Apr"],
        ["Q-77", "014-003", "W2 ECG correction", "Open / PI response"],
        ["Q-81", "014-007", "Excursion dosing", "Answered: do not dose"],
        ["Q-84", "014-008", "Central lab receipt", "Open"],
        ["Q-86", "014-009", "06 May; window ended 05 May", "Open"],
        ["Q-88", "014-011", "Repeat report missing", "Open"],
        ["Q-91", "014-014", "ePRO activation", "Answered: retrained"],
        ["Q-93", "014-016", "Masking note", "Open"],
    ]
    draw_label(c, "Data query log", 42, 385)
    draw_table(c, 42, 370, [72, 72, 205, 175], [query_headers, *query_rows], font_size=6.8, zebra=True)
    case.add_gold("Protocol deviations and data queries", markdown_table(deviation_headers, deviation_rows) + "\n\n" + markdown_table(query_headers, query_rows))
    case.add_region("p05.deviations", "Protocol deviation log", "table", table_leaves("p05.deviations", deviation_headers, deviation_rows, consequential={("DEV-014-03", "Current action"), ("DEV-014-07", "Current action")}), budget=2, closed_world=True)
    case.add_region("p05.queries", "Data query log", "table", table_leaves("p05.queries", query_headers, query_rows, consequential={("Q-77", "State"), ("Q-93", "State")}), budget=2, closed_world=True)

    # Page 6 - investigational-product accountability.
    c = case.new_page(
        "Investigational-product accountability",
        subtitle="Dispensing, returns, temperature state, and reconciliation",
        section_code="PHARMACY",
    )
    ip_headers = ["Kit", "Subject", "Dispensed", "Returned", "Temperature", "Final inventory state"]
    ip_rows = [
        ["K-204-118", "014-002", "30", "4", "In range", "Accounted"],
        ["K-204-142", "014-002", "30", "6", "In range", "Accounted"],
        ["K-204-166", "014-002", "15", "2", "In range", "Dose reduced"],
        ["K-204-121", "014-003", "30", "5", "In range", "Accounted"],
        ["K-204-146", "014-003", "30", "Not returned", "In range", "Open reconciliation"],
        ["K-204-153", "014-007", "0", "N/A — never dispensed", "9.1 C / 3 h", "Quarantined"],
        ["K-204-158", "014-008", "30", "Pending", "In range", "Await lab receipt"],
        ["K-204-160", "014-009", "30", "3", "In range", "Visit-window query"],
        ["K-204-171", "014-011", "30", "Pending", "In range", "Hold repeat lab"],
        ["K-204-184", "014-014", "30", "0", "In range", "ePRO retrained"],
        ["K-204-190", "014-016", "30", "2", "In range", "Masking review"],
    ]
    draw_table(c, 42, 665, [76, 60, 65, 82, 105, 150], [ip_headers, *ip_rows], font_size=6.5, zebra=True)
    draw_paragraph(c, "K-204-153 remained in pharmacy inventory and was never dispensed. Its zero dispense count is consistent with the checked Do not dose disposition on the excursion form.", 42, 255, 500, font="DocSans-Bold", size=8.2, leading=11.5, color=RED)
    accountability_note = "K-204-153 remained in pharmacy inventory, was never dispensed, and is quarantined under the Do not dose disposition."
    case.add_gold("Investigational-product accountability", markdown_table(ip_headers, ip_rows) + "\n\n" + accountability_note)
    case.add_region("p06.accountability", "Investigational-product accountability", "table", table_leaves("p06.accountability", ip_headers, ip_rows, consequential={("K-204-153", "Dispensed"), ("K-204-153", "Final inventory state")}), budget=2, closed_world=True)
    case.add_region(
        "p06.accountability-note",
        "K-204-153 inventory and disposition note",
        "text",
        [
            leaf("p06.accountability-note.inventory", "K-204-153 remained in pharmacy inventory and was never dispensed."),
            leaf("p06.accountability-note.disposition", "K-204-153 is quarantined under a Do not dose disposition.", harm=2),
        ],
        budget=1,
    )

    # Page 7 - actual corrected eCRF scan.
    c = case.new_page(
        "Corrected ECG eCRF / Subject 014-003",
        subtitle="Source correction audit trail | original entry retained",
        section_code="Q-77",
    )
    scan = _ecrf_scan()
    c.drawImage(image_reader(scan), 42, 215, width=528, height=405, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(HexColor("#969CA2"))
    c.rect(42, 215, 528, 405, fill=0, stroke=1)
    draw_paragraph(c, "MONITOR NOTE · L. SEN · 08 MAY 2026 — Final source state: ECG not performed. The original Yes box remains visible but crossed; the corrected No box is checked. Q-77 remains open pending PI response.", 42, 177, 520, font="DocSans-Bold", size=8.5, leading=12, color=RED)
    case.add_gold("Corrected ECG eCRF", "Subject 014-003, W2 on 2026-04-21. The original ECG performed = Yes box is crossed out. ECG performed = No is checked as the corrected source value on 2026-04-22 at 14:18. Reason: machine unavailable. DEV-014-03 is major. Q-77 is open pending PI response. Coordinator MK made the correction; monitor LS verified it on 2026-05-08. PI review is not completed.")
    case.add_region(
        "p07.ecrf",
        "Corrected ECG eCRF scan",
        "form",
        [
            leaf("p07.ecrf.subject", "The corrected eCRF belongs to subject 014-003 at W2 on 2026-04-21."),
            leaf("p07.ecrf.original", "The original ECG performed = Yes box is crossed out."),
            leaf("p07.ecrf.corrected", "The final ECG performed = No box is checked.", harm=2),
            leaf("p07.ecrf.reason", "The ECG was not performed because the machine was unavailable."),
            leaf("p07.ecrf.query", "Q-77 remains open pending PI response.", harm=2),
            leaf("p07.ecrf.audit.correction", "Coordinator MK corrected the form on 2026-04-22 at 14:18."),
            leaf("p07.ecrf.audit.verification", "Monitor LS verified the form on 2026-05-08."),
            leaf("p07.ecrf.pi", "PI review of DEV-014-03 is not completed."),
        ],
        budget=2,
    )

    # Page 8 - temperature form and shipment manifest.
    c = case.new_page(
        "Temperature excursion and sample shipments",
        subtitle="Pharmacy source form with laboratory chain-of-custody status",
        section_code="DEV-014-07",
    )
    temp_scan = _temperature_scan()
    c.drawImage(image_reader(temp_scan), 42, 365, width=528, height=310, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(HexColor("#969CA2"))
    c.rect(42, 365, 528, 310, fill=0, stroke=1)
    shipment_headers = ["Shipment", "Subject", "Tube", "Drawn", "Received", "State"]
    shipment_rows = [
        ["SH-204-44", "014-002", "PK-2", "19 Apr 08:12", "20 Apr 09:02", "Accepted"],
        ["SH-204-45", "014-003", "PK-2", "21 Apr 08:44", "23 Apr 16:40", "Accepted / late temp"],
        ["SH-204-46", "014-008", "Central lab", "20 Apr 09:15", "Pending", "Not reviewed"],
        ["SH-204-47", "014-009", "PK-2", "06 May 09:04", "06 May 11:20", "Accepted / 1 d late"],
        ["SH-204-48", "014-011", "Chemistry", "26 Apr 08:52", "27 Apr 10:05", "Repeat requested"],
        ["SH-204-49", "014-016", "Glucose", "04 May 07:58", "05 May 09:44", "Safety call done"],
    ]
    draw_label(c, "Sample shipment manifest", 42, 335)
    draw_table(c, 42, 320, [77, 58, 73, 92, 92, 125], [shipment_headers, *shipment_rows], font_size=6.35, zebra=True)
    case.add_gold(
        "Temperature excursion and sample shipments",
        "Kit K-204-153 / subject 014-007 on 2026-04-18: 8.4 C at 09:10; 9.1 C and quarantined at 10:10; "
        "8.8 C pharmacist notified at 11:10; 7.8 C at 12:10; 5.2 C at 13:05; 4.7 C stable at 13:40. "
        "Do not dose is checked; Return to stock and Destroy are unchecked. Dispensed quantity is 0 and final inventory state is quarantined.\n\n"
        + markdown_table(shipment_headers, shipment_rows),
    )
    case.add_region(
        "p08.excursion",
        "Temperature excursion form",
        "form",
        [
            leaf("p08.excursion.kit", "The excursion form is for kit K-204-153 and subject 014-007."),
            leaf("p08.excursion.peak", "Peak recorded temperature is 9.1 C at 10:10 on 2026-04-18.", harm=2),
            leaf("p08.excursion.final-reading", "The final reading is 4.7 C at 13:40."),
            leaf("p08.excursion.quarantine", "Quarantine remains in force after the final reading."),
            leaf("p08.excursion.disposition.do-not-dose", "Do not dose is checked.", harm=2),
            leaf("p08.excursion.disposition.return-to-stock", "Return to stock is unchecked."),
            leaf("p08.excursion.disposition.destroy", "Destroy is unchecked."),
            leaf("p08.excursion.dispensed", "Dispensed quantity is 0.", harm=2),
            leaf("p08.excursion.inventory-state", "Final inventory state is quarantined.", harm=2),
        ],
        budget=2,
    )
    case.add_region("p08.shipments", "Sample shipment manifest", "table", table_leaves("p08.shipments", shipment_headers, shipment_rows, consequential={("SH-204-45", "State"), ("SH-204-46", "State")}), budget=2, closed_world=True)

    # Page 9 - final readiness and PI signoff.
    c = case.new_page(
        "Site readiness determination",
        subtitle="Signed monitor assessment after source review",
        section_code="FINAL 08 MAY",
    )
    readiness_headers = ["Domain", "Open items", "Controlling evidence", "State"]
    readiness_rows = [
        ["Enrollment", "0", "Disposition log current", "Ready"],
        ["ECG", "1", "Q-77 / 014-003", "Open"],
        ["IP accountability", "1", "K-204-153 quarantine", "Open"],
        ["Central laboratory", "3", "014-008, 014-011, 014-016", "Open"],
        ["AE follow-up", "1", "AE-014-04 repeat lab", "Open"],
        ["Visit windows", "1", "Q-86 / 014-009", "Open"],
        ["Masking", "1", "Q-93 / 014-016", "Open"],
    ]
    draw_table(c, 42, 660, [120, 72, 230, 82], [readiness_headers, *readiness_rows], font_size=7.2, zebra=True)
    draw_label(c, "Principal-investigator review", 42, 380)
    draw_checkbox(c, 44, 348, "checked", "AE-014-01 reviewed")
    draw_checkbox(c, 44, 322, "unchecked", "DEV-014-03 reviewed")
    draw_checkbox(c, 44, 296, "checked", "DEV-014-07 reviewed")
    draw_checkbox(c, 44, 270, "unchecked", "DEV-014-09 reviewed")
    draw_checkbox(c, 44, 244, "unchecked", "DEV-014-11 reviewed")
    draw_checkbox(c, 44, 207, "unchecked", "Site clean-ready attestation")
    c.setFillColor(INK)
    c.setFont("DocSans", 8)
    c.drawString(325, 348, "PI: Dr. Neha Rao")
    c.drawString(325, 324, "Signed: 08 May 2026")
    draw_badge(c, "Not clean-ready", 325, 277, RED)
    draw_paragraph(c, "Final monitor determination: Site 014 is not clean-ready while ECG correction, drug accountability, central-lab follow-up, visit-window, and masking items remain open.", 325, 235, 235, font="DocSans-Bold", size=8.2, leading=11.5, color=RED)
    case.add_gold("Site readiness determination", markdown_table(readiness_headers, readiness_rows) + "\n\nPI review states: AE-014-01 checked; DEV-014-03 unchecked; DEV-014-07 checked; DEV-014-09 unchecked; DEV-014-11 unchecked; Site clean-ready attestation unchecked. Dr. Neha Rao signed on 2026-05-08. Final monitor determination: Site 014 is not clean-ready.")
    case.add_region("p09.readiness", "Data-cleaning readiness", "table", table_leaves("p09.readiness", readiness_headers, readiness_rows, consequential={("ECG", "State"), ("IP accountability", "State"), ("Masking", "State")}), budget=2, closed_world=True)
    case.add_region(
        "p09.signoff",
        "PI signoff and clean-ready state",
        "form",
        [
            leaf("p09.signoff.ae", "PI reviewed AE-014-01 is checked."),
            leaf("p09.signoff.dev03", "PI reviewed DEV-014-03 is unchecked."),
            leaf("p09.signoff.dev07", "PI reviewed DEV-014-07 is checked."),
            leaf("p09.signoff.dev09", "PI reviewed DEV-014-09 is unchecked."),
            leaf("p09.signoff.dev11", "PI reviewed DEV-014-11 is unchecked."),
            leaf("p09.signoff.clean.attestation", "Site clean-ready attestation is unchecked."),
            leaf("p09.signoff.clean.determination", "The final monitor state is not clean-ready.", harm=2),
            leaf("p09.signoff.pi", "Dr. Neha Rao signed on 2026-05-08."),
        ],
        budget=2,
    )

    return case.finish()
