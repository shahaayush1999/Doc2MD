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
    draw_badge,
    draw_label,
    draw_paragraph,
    draw_table,
    image_reader,
    leaf,
    markdown_table,
    table_leaves,
)


ASSET_DIR = Path(__file__).with_name("assets")


def _sem_image(kind: str, seed: int) -> Image.Image:
    del seed  # Stable source-image selection replaces procedural randomness.
    asset_names = {
        "flake": "p21-sem-flake.png",
        "scratch": "p21-sem-scratch.png",
        "edge": "p21-sem-edge.png",
        "clean": "p21-sem-clean.png",
    }
    source = Image.open(ASSET_DIR / asset_names[kind]).convert("L")
    image = ImageOps.fit(source, (900, 560), method=Image.Resampling.LANCZOS)
    image = ImageOps.autocontrast(image, cutoff=0.4)
    draw = ImageDraw.Draw(image)
    draw.rectangle((48, 492, 264, 520), fill=20)
    draw.rectangle((58, 500, 252, 509), fill=242)
    draw.text((58, 524), "20 um", font=ImageFont.load_default(size=20), fill=238)
    return image.convert("RGB")


def _wafer_map(c, ox, oy, wafer, cells, color):
    c.setFillColor(INK)
    c.setFont("DocSans-Bold", 7)
    c.drawString(ox, oy + 145, f"WAFER {wafer}")
    c.setStrokeColor(MUTED)
    c.circle(ox + 67, oy + 67, 63, fill=0, stroke=1)
    letters = ["A", "B", "C", "D", "E", "F"]
    for row, letter in enumerate(letters):
        c.setFillColor(MUTED)
        c.setFont("DocSans", 5.6)
        c.drawString(ox - 4, oy + 112 - row * 18, letter)
        for column in range(1, 7):
            x = ox + 18 + (column - 1) * 18
            y = oy + 102 - row * 18
            c.setStrokeColor(HexColor("#D5D8DA"))
            c.rect(x, y, 14, 14, fill=0, stroke=1)
            if row == 0:
                c.setFillColor(MUTED)
                c.setFont("DocSans", 5.6)
                c.drawCentredString(x + 7, oy + 124, str(column))
    for coordinate, code in cells:
        row = letters.index(coordinate[0])
        column = int(coordinate[1])
        x = ox + 18 + (column - 1) * 18
        y = oy + 102 - row * 18
        c.setFillColor(HexColor(color))
        c.rect(x, y, 14, 14, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("DocSans-Bold", 5.7)
        c.drawCentredString(x + 7, y + 4.2, code)


def build(output_root):
    case = CaseBuilder(
        output_root=output_root,
        case_id="P21-semiconductor-lot-disposition",
        title="Lot Q8R7-22 Material Review File",
        family="semiconductor manufacturing quality",
        tags=["native-pdf", "wafer-maps", "metrology", "spc", "sem-images", "mrb", "source-precedence"],
        page_count=8,
        purpose="Test wafer-coordinate bindings, process-source conflicts, metrology and SPC state, real SEM-like image regions, MRB decisions, and shipment authority.",
        source_modality="born-digital native manufacturing file with embedded wafer and SEM-like inspection imagery",
        document_ref="FAB 8 · LOT Q8R7-22 · MRB-26-071",
        metadata_date="D:20260707164500-07'00'",
    )

    # Page 1 - traveler and recipe source state.
    c = case.new_page(
        "Lot traveler and process source",
        subtitle="Aster Microdevices | Fab 8 | AMX-4100 LVT gate flow",
        section_code="LOT Q8R7-22",
    )
    draw_badge(c, "MRB hold", 42, 684, AMBER)
    route_headers = ["Step", "Tool", "Recipe", "Start", "End", "Recorded state"]
    route_rows = [
        ["Implant P3", "IMP-17", "BORON_LVT_042", "05:12", "05:58", "Accepted"],
        ["Ash", "ASH-04", "ASH_STD_18", "06:10", "06:34", "Accepted"],
        ["Wet clean", "WET-12", "SC1_SC2_09", "06:48", "07:22", "Accepted"],
        ["PVD TiN", "PVD-03", "TIN_GATE_31", "08:06", "09:44", "Alarm 09:18"],
        ["Anneal", "RTP-08", "RTP_LVT_22", "10:01", "10:29", "Accepted"],
        ["Metrology", "CDSEM-06", "GATE_LVT_QC", "10:45", "11:56", "Reviewed"],
    ]
    draw_label(c, "Process traveler", 42, 650)
    draw_table(c, 42, 635, [92, 75, 120, 62, 62, 110], [route_headers, *route_rows], font_size=6.9, zebra=True)
    recipe_headers = ["Source", "Recipe shown", "State", "Use for this lot"]
    recipe_rows = [
        ["Traveler page", "TIN_GATE_31", "Current", "Yes"],
        ["PVD alarm printout", "TIN_GATE_30", "Stale cached header", "No"],
        ["MES audit event", "TIN_GATE_31", "Confirmed", "Yes / controls"],
        ["Engineer note", "Increase clamp purge", "Future revision", "Not used"],
    ]
    draw_label(c, "Recipe source reconciliation", 42, 370)
    draw_table(c, 42, 355, [150, 120, 130, 120], [recipe_headers, *recipe_rows], font_size=7.3, zebra=True)
    draw_paragraph(c, "MES event 88419 confirms TIN_GATE_31 executed on PVD-03. The TIN_GATE_30 string is confined to a stale alarm-printout header.", 42, 175, 500, font="DocSans-Bold", size=8.4, leading=11.5, color=RED)
    case.add_gold("Lot traveler and process source", markdown_table(route_headers, route_rows) + "\n\n" + markdown_table(recipe_headers, recipe_rows) + "\n\nTIN_GATE_31 controls the actual lot run; TIN_GATE_30 is a stale alarm-printout header and the clamp-purge change is future only.")
    case.add_region("p01.route", "Process traveler", "table", table_leaves("p01.route", route_headers, route_rows, consequential={("PVD TiN", "Recipe"), ("PVD TiN", "Recorded state")}), budget=2, closed_world=True)
    case.add_region("p01.recipe", "Recipe source reconciliation", "table", table_leaves("p01.recipe", recipe_headers, recipe_rows, consequential={("MES audit event", "Recipe shown"), ("PVD alarm printout", "Use for this lot")}), budget=2, closed_world=True)

    # Page 2 - wafer maps.
    c = case.new_page(
        "Wafer-map review",
        subtitle="Grid A-F × 1-6 | reviewed defect codes shown in-map",
        section_code="MAP SET 11 JUN",
    )
    maps = [
        ("03", [("B4", "C3"), ("C4", "C3"), ("B5", "C3")], "#D9D7EE"),
        ("05", [("E2", "S2"), ("F2", "S2"), ("E3", "S2")], "#F2DFC4"),
        ("07", [("D5", "M1"), ("D6", "M1"), ("E5", "M1")], "#E8CACA"),
        ("09", [("F3", "P4")], "#CEDDF0"),
        ("12", [("A6", "E1"), ("B6", "E1")], "#F2E9C2"),
        ("02", [("A1", "E0")], "#DDE3E6"),
    ]
    for index, (wafer, cells, color) in enumerate(maps):
        ox = 52 + (index % 3) * 180
        oy = 420 - (index // 3) * 220
        _wafer_map(c, ox, oy, wafer, cells, color)
    legend_headers = ["Code", "Class", "Map color", "Disposition gate"]
    legend_rows = [
        ["M1", "Metal flake", "Red", "Scrap cluster"],
        ["S2", "Scratch", "Orange", "Engineering hold"],
        ["E1", "Edge bead", "Yellow", "Engineering hold"],
        ["P4", "Parametric drift", "Blue", "Reliability condition"],
        ["C3", "Center CD cluster", "Violet", "Remeasure / MRB"],
        ["E0", "Edge mark", "Gray", "Reference only"],
    ]
    draw_table(c, 42, 180, [70, 140, 90, 200], [legend_headers, *legend_rows], font_size=6.8, zebra=True)
    case.add_gold("Wafer-map review", "Wafer 03 C3 cells: B4, C4, B5. Wafer 05 S2 cells: E2, F2, E3. Wafer 07 M1 cells: D5, D6, E5. Wafer 09 P4 cell: F3. Wafer 12 E1 cells: A6, B6. Wafer 02 E0 reference cell: A1.\n\n" + markdown_table(legend_headers, legend_rows))
    map_leaves = []
    for wafer, cells, _color in maps:
        for coordinate, code in cells:
            map_leaves.append(leaf(f"p02.map.w{wafer}.{coordinate.lower()}", f"Wafer {wafer} cell {coordinate} is marked {code}.", harm=2 if wafer in {"07", "09"} else 1))
    case.add_region("p02.maps", "Wafer-map contact sheet", "diagram", map_leaves, budget=2, closed_world=True)
    case.add_region("p02.legend", "Wafer-map legend", "table", table_leaves("p02.legend", legend_headers, legend_rows), closed_world=True)

    # Page 3 - metrology.
    c = case.new_page(
        "CD-SEM metrology review",
        subtitle="Target 24.9 nm | action limits -2.0 / +2.5 nm",
        section_code="CDSEM-06",
    )
    met_headers = ["Wafer / site", "CD nm", "Delta nm", "Flag", "Image ref", "Reviewer note"]
    met_rows = [
        ["03 / B4", "27.8", "+2.9", "H", "IMG-221", "Matches C3 map"],
        ["03 / C4", "27.4", "+2.5", "H", "IMG-222", "Adjacent high"],
        ["05 / E2", "24.1", "-0.8", "L-map", "IMG-223", "Scratch path"],
        ["07 / D5", "29.6", "+4.7", "H", "IMG-224", "Flake shadow"],
        ["07 / D6", "29.1", "+4.2", "H", "IMG-225", "Adjacent flake"],
        ["09 / F3", "26.8", "+1.9", "Watch", "IMG-226", "Parametric only"],
        ["12 / A6", "22.9", "-2.0", "L", "IMG-227", "Edge bead"],
    ]
    draw_table(c, 42, 665, [92, 60, 68, 63, 75, 160], [met_headers, *met_rows], font_size=7, zebra=True)
    rule_headers = ["Rule", "Condition", "Required action"]
    rule_rows = [
        ["CD-H", "Delta >= +2.5 nm", "MRB disposition"],
        ["CD-L", "Delta <= -2.0 nm", "MRB disposition"],
        ["Map correlation", "Defect code at measured site", "Review image and map together"],
        ["Yield exception", "Wafer yield >93%", "Does not waive action-limit review"],
    ]
    draw_label(c, "Disposition rules", 42, 350)
    draw_table(c, 42, 335, [105, 170, 230], [rule_headers, *rule_rows], font_size=7.4, zebra=True)
    case.add_gold("CD-SEM metrology review", markdown_table(met_headers, met_rows) + "\n\n" + markdown_table(rule_headers, rule_rows))
    case.add_region("p03.metrology", "CD-SEM metrology", "table", table_leaves("p03.metrology", met_headers, met_rows, consequential={("07 / D5", "CD nm"), ("12 / A6", "Flag")}), budget=2, closed_world=True)
    case.add_region("p03.rules", "Metrology disposition rules", "table", table_leaves("p03.rules", rule_headers, rule_rows), closed_world=True)

    # Page 4 - SPC chart and interlocks.
    c = case.new_page(
        "PVD thickness SPC and alarm interlocks",
        subtitle="PVD-03 sequence R-2241 through R-2247",
        section_code="SPC 11 JUN",
    )
    series = [
        ("R-2241", 41.2, "Inside"),
        ("R-2242", 42.0, "Inside"),
        ("R-2243", 43.8, "Inside"),
        ("R-2244", 45.6, "Warning"),
        ("R-2245", 47.4, "Above UCL"),
        ("R-2246", 46.2, "Warning"),
        ("R-2247", 44.1, "Recovered"),
    ]
    ox, oy = 75, 430
    c.setStrokeColor(INK)
    c.line(ox, oy, 540, oy)
    c.line(ox, oy, ox, 650)
    for value, color, label in [(45.0, AMBER, "warning 45.0"), (47.0, RED, "UCL 47.0")]:
        y = oy + (value - 40) / 8 * 200
        c.setStrokeColor(color)
        c.setDash(4, 3)
        c.line(ox, y, 540, y)
        c.setDash()
        c.setFillColor(color)
        c.setFont("DocSans-Bold", 6)
        c.drawRightString(540, y + 4, label)
    points = []
    for index, (run, value, _state) in enumerate(series):
        x = ox + 28 + index * 66
        y = oy + (value - 40) / 8 * 200
        points.append((x, y))
        c.setFillColor(RED if value > 47 else BLUE)
        c.circle(x, y, 3, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("DocSans-Bold", 6)
        c.drawCentredString(x, y + 9, f"{value:.1f}")
        c.setFont("DocSans", 5.5)
        c.drawCentredString(x, oy - 15, run)
    c.setStrokeColor(BLUE)
    c.setLineWidth(1.5)
    for first, second in zip(points, points[1:]):
        c.line(first[0], first[1], second[0], second[1])
    interlock_headers = ["Interlock", "Observed", "Threshold", "State", "Disposition"]
    interlock_rows = [
        ["Chamber pressure", "4.8 mTorr", "<=5.0", "Pass", "Not root cause"],
        ["Clamp purge", "18.1 slm", ">=19.0", "Fail", "Future increase only"],
        ["Ti target age", "81.4 kWh", "<=85", "Watch", "Clean then continue"],
        ["Monitor residual", "+1.7 nm", "+/-1.0", "Fail", "R-2245 review"],
        ["Alarm ack", "09:18 / J. Kwon", "Required", "Complete", "Containment starts"],
    ]
    draw_label(c, "Alarm interlocks", 42, 365)
    draw_table(c, 42, 350, [120, 100, 82, 65, 150], [interlock_headers, *interlock_rows], font_size=6.9, zebra=True)
    case.add_gold("PVD thickness SPC and alarm interlocks", "SPC points: " + ", ".join(f"{run} {value:.1f} nm ({state})" for run, value, state in series) + ". Warning is 45.0 nm and UCL is 47.0 nm.\n\n" + markdown_table(interlock_headers, interlock_rows))
    case.add_region("p04.spc", "PVD thickness SPC chart", "chart", [leaf(f"p04.spc.{run.lower()}", f"{run} is {value:.1f} nm with state {state}.", harm=2 if run == "R-2245" else 1) for run, value, state in series], budget=2)
    case.add_region("p04.interlocks", "PVD alarm interlocks", "table", table_leaves("p04.interlocks", interlock_headers, interlock_rows, consequential={("Clamp purge", "State"), ("Monitor residual", "State")}), budget=2, closed_world=True)

    # Page 5 - actual SEM-like image regions.
    c = case.new_page(
        "SEM review contact sheet",
        subtitle="Representative reviewed frames; 20 um scale bars",
        section_code="IMG-224/223/227/226",
    )
    panels = [
        ("IMG-224", "W07 D5", "flake", _sem_image("flake", 2101)),
        ("IMG-223", "W05 E2", "scratch", _sem_image("scratch", 2102)),
        ("IMG-227", "W12 A6", "edge", _sem_image("edge", 2103)),
        ("IMG-226", "W09 F3", "clean", _sem_image("clean", 2104)),
    ]
    for index, (image_id, site, _kind, image) in enumerate(panels):
        x = 42 + (index % 2) * 270
        y = 390 - (index // 2) * 270
        c.drawImage(image_reader(image), x, y, width=250, height=155, preserveAspectRatio=True, mask="auto")
        c.setStrokeColor(HexColor("#969CA2"))
        c.rect(x, y, 250, 155, fill=0, stroke=1)
        c.setFillColor(INK)
        c.setFont("DocSans-Bold", 7)
        c.drawString(x, y - 14, f"{image_id} / {site}")
    case.add_gold("SEM review contact sheet", "IMG-224 / W07 D5 shows two bright irregular metal flakes, including an adjacent smaller flake. IMG-223 / W05 E2 shows a long diagonal scratch crossing the field. IMG-227 / W12 A6 shows a bright edge-residue band with small bead deposits. IMG-226 / W09 F3 is visually clean apart from low-level background specks; its P4 issue is parametric rather than a visible particle.")
    case.add_region(
        "p05.image.224",
        "IMG-224 metal-flake SEM",
        "image",
        [
            leaf("p05.img224.binding", "IMG-224 is bound to wafer 07 site D5."),
            leaf(
                "p05.img224.finding",
                "IMG-224 visibly shows two bright irregular metal flakes, one smaller and adjacent.",
                harm=2,
                allow_partial=True,
            ),
        ],
    )
    case.add_region("p05.image.223", "IMG-223 scratch SEM", "image", [leaf("p05.img223.binding", "IMG-223 is bound to wafer 05 site E2."), leaf("p05.img223.finding", "IMG-223 visibly shows a long diagonal scratch crossing the field.", harm=2)])
    case.add_region(
        "p05.image.227",
        "IMG-227 edge-bead SEM",
        "image",
        [
            leaf("p05.img227.binding", "IMG-227 is bound to wafer 12 site A6."),
            leaf(
                "p05.img227.finding",
                "IMG-227 visibly shows a bright edge-residue band with bead deposits.",
                allow_partial=True,
            ),
        ],
    )
    case.add_region(
        "p05.image.226",
        "IMG-226 clean SEM",
        "image",
        [
            leaf("p05.img226.binding", "IMG-226 is bound to wafer 09 site F3."),
            leaf("p05.img226.finding", "IMG-226 is visually clean apart from low-level background specks."),
            leaf("p05.img226.parametric", "The P4 issue for IMG-226 is parametric rather than a visible particle."),
        ],
    )

    # Page 6 - defect gates and MRB decisions.
    c = case.new_page(
        "Defect classification and MRB decisions",
        subtitle="Map, metrology, and image evidence reconciled at 11 June meeting",
        section_code="MRB 08:55",
    )
    defect_headers = ["Code", "Class", "Count", "Wafer", "Gate"]
    defect_rows = [
        ["M1", "Metal flake", "44", "07", "Scrap"],
        ["S2", "Scratch", "31", "05", "Engineering hold"],
        ["E1", "Edge bead", "27", "12", "Engineering hold"],
        ["P4", "Parametric drift", "19", "09", "Conditional"],
        ["C3", "Center CD cluster", "16", "03", "Remeasure / hold"],
    ]
    draw_table(c, 42, 665, [70, 135, 65, 65, 150], [defect_headers, *defect_rows], font_size=7.4, zebra=True)
    mrb_headers = ["Item", "Decision", "Reason", "Owner"]
    mrb_rows = [
        ["Wafer 07", "Scrap", "M1 at D5/D6/E5", "Y. Nishida"],
        ["Wafer 05", "Hold", "S2 crosses E2/F2/E3", "A. Roy"],
        ["Wafer 03", "Hold", "C3 high CD B4/C4/B5", "M. Alvarez"],
        ["Wafer 12", "Hold", "E1 at A6/B6", "K. Stone"],
        ["Wafer 09", "Conditional", "P4; REL-22-A required", "S. Han"],
        ["01,02,04,06,08,10,11", "Release", "Inside disposition limits", "MRB"],
    ]
    draw_label(c, "Material review board", 42, 410)
    draw_table(c, 42, 395, [145, 90, 220, 105], [mrb_headers, *mrb_rows], font_size=6.9, zebra=True)
    case.add_gold("Defect classification and MRB decisions", markdown_table(defect_headers, defect_rows) + "\n\n" + markdown_table(mrb_headers, mrb_rows))
    case.add_region("p06.defects", "Defect classification", "table", table_leaves("p06.defects", defect_headers, defect_rows), closed_world=True)
    case.add_region("p06.mrb", "MRB decisions", "table", table_leaves("p06.mrb", mrb_headers, mrb_rows, consequential={("Wafer 07", "Decision"), ("Wafer 09", "Decision")}), budget=2, closed_world=True)

    # Page 7 - reliability and shipping allocation.
    c = case.new_page(
        "Reliability conditions and shipping allocation",
        subtitle="Shipment authority remains conditional for wafer 09",
        section_code="HOLD / RELEASE",
    )
    rel_headers = ["Sample", "Wafer", "Stress", "Result", "Disposition use"]
    rel_rows = [
        ["REL-22-A", "09", "HTOL 168 h", "Pending", "Condition for shipment"],
        ["REL-22-B", "02", "TC 100 cycles", "Pass", "Reference"],
        ["REL-22-C", "11", "HAST 96 h", "Pass", "Reference"],
        ["REL-22-D", "07", "Not built", "Scrap", "No reliability credit"],
    ]
    draw_table(c, 42, 665, [90, 65, 120, 80, 180], [rel_headers, *rel_rows], font_size=7.4, zebra=True)
    ship_headers = ["Bucket", "Wafers", "Good die", "Shipment condition"]
    ship_rows = [
        ["Release now", "01,02,04,06,08,10,11", "127,759", "Standard COA"],
        ["Conditional", "09", "17,880", "Wait for REL-22-A pass"],
        ["Engineering hold", "03,05,12", "52,144", "Do not ship"],
        ["Scrap", "07", "16,902", "Exclude from yield and COA"],
    ]
    draw_label(c, "Shipping allocation", 42, 430)
    draw_table(c, 42, 415, [120, 165, 85, 170], [ship_headers, *ship_rows], font_size=7.3, zebra=True)
    case.add_gold("Reliability conditions and shipping allocation", markdown_table(rel_headers, rel_rows) + "\n\n" + markdown_table(ship_headers, ship_rows))
    case.add_region("p07.reliability", "Reliability sample plan", "table", table_leaves("p07.reliability", rel_headers, rel_rows, consequential={("REL-22-A", "Result")}), budget=2, closed_world=True)
    case.add_region("p07.shipping", "Shipping allocation", "table", table_leaves("p07.shipping", ship_headers, ship_rows, consequential={("Conditional", "Shipment condition"), ("Scrap", "Shipment condition")}), budget=2, closed_world=True)

    # Page 8 - signed COA holdback and audit trail.
    c = case.new_page(
        "Certificate holdback and final audit trail",
        subtitle="Signed quality record controls shipment eligibility",
        section_code="FINAL 11 JUN",
    )
    draw_badge(c, "Partial release", 42, 684, AMBER)
    coa_headers = ["COA field", "Signed value", "Application"]
    coa_rows = [
        ["Lot", "Q8R7-22", "All wafers"],
        ["Released wafers", "01,02,04,06,08,10,11", "Ship now"],
        ["Conditional wafer", "09", "After REL-22-A pass"],
        ["Engineering hold", "03,05,12", "Excluded"],
        ["Scrap", "07", "Excluded from yield and COA"],
        ["Executed recipe", "TIN_GATE_31", "MES confirmed"],
    ]
    draw_table(c, 42, 650, [145, 205, 180], [coa_headers, *coa_rows], font_size=7.4, zebra=True)
    audit_headers = ["Time", "Actor", "Entry", "Effect"]
    audit_rows = [
        ["10 Jun 12:18", "MES", "PVD alarm attached", "Containment starts"],
        ["10 Jun 14:40", "Yield engineering", "Map review complete", "03/05/07/12 flagged"],
        ["11 Jun 08:55", "MRB", "07 scrap; 09 conditional", "Disposition controls"],
        ["11 Jun 10:20", "Quality", "COA holdback signed", "Draft all-wafer COA void"],
        ["11 Jun 13:30", "Planning", "Ship buckets created", "127,759 die release"],
    ]
    draw_label(c, "Audit trail", 42, 395)
    draw_table(c, 42, 380, [100, 115, 185, 130], [audit_headers, *audit_rows], font_size=6.9, zebra=True)
    draw_paragraph(c, "The preliminary all-wafer COA is void. Only the signed values above authorize shipment.", 42, 155, 500, font="DocSans-Bold", size=8.6, leading=12, color=RED)
    case.add_gold("Certificate holdback and final audit trail", markdown_table(coa_headers, coa_rows) + "\n\n" + markdown_table(audit_headers, audit_rows) + "\n\nThe preliminary all-wafer COA is void; only the signed COA values authorize shipment.")
    case.add_region("p08.coa", "Signed COA holdback", "table", table_leaves("p08.coa", coa_headers, coa_rows, consequential={("Released wafers", "Signed value"), ("Conditional wafer", "Application"), ("Scrap", "Application")}), budget=2, closed_world=True)
    case.add_region("p08.audit", "Lot-disposition audit trail", "table", table_leaves("p08.audit", audit_headers, audit_rows), closed_world=True)
    case.add_region("p08.authority", "Shipment-authority statement", "text", [leaf("p08.authority.void", "The preliminary all-wafer COA is void."), leaf("p08.authority.signed", "Only the signed COA values on page 8 authorize shipment.", harm=2)])

    return case.finish()
