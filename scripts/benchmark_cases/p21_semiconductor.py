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
    form_state_leaf,
    image_reader,
    leaf,
    make_scan,
    markdown_table,
    source_precedence_leaf,
    table_leaves,
    visual_leaf,
)
from .rasterize import ScanProfile, rasterize_pdf_pages


ASSET_DIR = Path(__file__).with_name("assets")

# Deliberate page-level modality envelope. Full-scan pages are converted only
# after the native source has been laid out, so the selected pages contain one
# page-sized raster and no recoverable native text.
NATIVE_PAGES = (1, 3, 6, 9)
FULL_SCAN_PAGES = (2, 4)
MIXED_PAGES = (5, 7, 8)


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
        page_count=9,
        purpose="Test wafer-coordinate bindings, process-source conflicts, metrology and SPC state, real SEM-like image regions, MRB decisions, and shipment authority.",
        source_modality="mixed manufacturing file with native records, two full-page scanned reviews, SEM imagery, and scanned inspection forms",
        document_ref="FAB 8 · LOT Q8R7-22 · MRB-26-071",
        metadata_date="D:20260707164500-07'00'",
    )
    case.set_page_modalities(
        native_pages=NATIVE_PAGES,
        full_raster_pages=FULL_SCAN_PAGES,
        mixed_pages=MIXED_PAGES,
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
    route_bindings = {
        ("PVD TiN", "Tool"), ("PVD TiN", "Recipe"), ("PVD TiN", "Start"), ("PVD TiN", "Recorded state"),
        ("Metrology", "Tool"), ("Metrology", "Recorded state"),
    }
    recipe_bindings = {
        ("Traveler page", "Recipe shown"), ("Traveler page", "Use for this lot"),
        ("PVD alarm printout", "Recipe shown"), ("PVD alarm printout", "State"), ("PVD alarm printout", "Use for this lot"),
        ("MES audit event", "Recipe shown"), ("MES audit event", "State"), ("MES audit event", "Use for this lot"),
        ("Engineer note", "State"), ("Engineer note", "Use for this lot"),
    }
    case.add_region("p01.route", "Process traveler", "table", table_leaves("p01.route", route_headers, route_rows, consequential={("PVD TiN", "Recipe"), ("PVD TiN", "Recorded state")}, scored_bindings=route_bindings), budget=1, closed_world=True)
    case.add_region("p01.recipe", "Recipe source reconciliation", "table", table_leaves("p01.recipe", recipe_headers, recipe_rows, consequential={("MES audit event", "Recipe shown"), ("PVD alarm printout", "Use for this lot")}, scored_bindings=recipe_bindings), budget=2, closed_world=True, primary_axis="source_precedence", secondary_axes=["table_reconstruction"])

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
    map_leaves = [
        leaf("p02.map.w03.pattern", "Wafer 03 marks a three-cell C3 cluster at B4, C4, and B5.", evidence=[["Wafer"], ["03", "3"], ["marks"], ["three-cell", "three cell", "3-cell"], ["C3"], ["B4"], ["C4"], ["B5"]]),
        leaf("p02.map.w05.pattern", "Wafer 05 marks an S2 path at E2, F2, and E3.", evidence=[["Wafer"], ["05", "5"], ["marks"], ["S2"], ["path"], ["E2"], ["F2"], ["E3"]]),
        leaf(
            "p02.map.w07.pattern",
            "Wafer 07 marks an adjacent M1 cluster at D5, D6, and E5.",
            harm=2,
            evidence_policy={
                "type": "ordered_tokens",
                "tokens": [["Wafer 07", "WAFER 07", "W07"], ["M1"], ["D5"], ["D6"], ["E5"]],
            },
        ),
        leaf("p02.map.w09.pattern", "Wafer 09 marks only F3 as P4.", evidence=[["Wafer"], ["09", "9"], ["marks"], ["only", "solely"], ["F3"], ["P4"]]),
        leaf("p02.map.w12.pattern", "Wafer 12 marks the A6 and B6 edge cells as E1.", harm=2, evidence=[["Wafer"], ["12"], ["marks"], ["A6"], ["B6"], ["edge cells", "edge"], ["E1"]]),
        leaf("p02.map.w02.reference", "Wafer 02 marks only A1 as the gray E0 reference cell.", evidence=[["Wafer"], ["02", "2"], ["marks"], ["only", "solely"], ["A1"], ["gray", "grey"], ["E0"], ["reference"]]),
    ]
    case.add_region("p02.maps", "Wafer-map contact sheet", "diagram", map_leaves, budget=2, closed_world=True)
    legend_bindings = {(code, field) for code in {"M1", "S2", "E1", "P4", "C3"} for field in {"Class", "Disposition gate"}}
    case.add_region("p02.legend", "Wafer-map legend", "table", table_leaves("p02.legend", legend_headers, legend_rows, scored_bindings=legend_bindings), closed_world=True)

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
    met_bindings = {
        ("03 / B4", "CD nm"), ("03 / B4", "Delta nm"), ("03 / C4", "CD nm"),
        ("05 / E2", "Flag"), ("07 / D5", "CD nm"), ("07 / D5", "Delta nm"),
        ("07 / D6", "CD nm"), ("09 / F3", "Delta nm"), ("09 / F3", "Flag"),
        ("12 / A6", "CD nm"), ("12 / A6", "Delta nm"), ("12 / A6", "Flag"),
    }
    rule_bindings = {(row[0], field) for row in rule_rows for field in {"Condition", "Required action"}}
    case.add_region("p03.metrology", "CD-SEM metrology", "table", table_leaves("p03.metrology", met_headers, met_rows, consequential={("07 / D5", "CD nm"), ("12 / A6", "Flag")}, scored_bindings=met_bindings), budget=2, closed_world=True)
    case.add_region("p03.rules", "Metrology disposition rules", "table", table_leaves("p03.rules", rule_headers, rule_rows, scored_bindings=rule_bindings), closed_world=True)

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
    chart_height = 180
    draw_label(c, "Chart legend", ox, 670)
    c.setStrokeColor(BLUE)
    c.setLineWidth(1.5)
    c.line(145, 672, 178, 672)
    c.setFillColor(BLUE)
    c.circle(161, 672, 3, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("DocSans", 5.8)
    c.drawString(184, 669, "PVD-03 measured TiN thickness")
    c.setStrokeColor(AMBER)
    c.setDash(4, 3)
    c.line(345, 672, 378, 672)
    c.setDash()
    c.setFillColor(INK)
    c.drawString(384, 669, "warning 45.0 nm")
    c.setStrokeColor(RED)
    c.setDash(4, 3)
    c.line(474, 672, 507, 672)
    c.setDash()
    c.setFillColor(INK)
    c.drawString(513, 669, "UCL 47.0 nm")
    for x, color, label in [
        (145, BLUE, "inside / recovered"),
        (285, AMBER, "warning"),
        (380, RED, "above UCL"),
    ]:
        c.setFillColor(color)
        c.circle(x, 650, 3.2, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("DocSans", 5.8)
        c.drawString(x + 8, 647, label)
    c.setStrokeColor(INK)
    c.line(ox, oy, 540, oy)
    c.line(ox, oy, ox, oy + chart_height)
    c.setFillColor(INK)
    c.setFont("DocSans", 5.8)
    for tick in range(40, 49, 2):
        y = oy + (tick - 40) / 8 * chart_height
        c.line(ox - 4, y, ox, y)
        c.drawRightString(ox - 8, y - 2, str(tick))
    c.saveState()
    c.translate(44, oy + chart_height / 2)
    c.rotate(90)
    c.setFont("DocSans-Bold", 6.2)
    c.drawCentredString(0, 0, "TiN thickness (nm)")
    c.restoreState()
    c.setFont("DocSans-Bold", 6.2)
    c.drawCentredString((ox + 540) / 2, oy - 34, "Run sequence")
    for value, color, label in [(45.0, AMBER, "warning 45.0"), (47.0, RED, "UCL 47.0")]:
        y = oy + (value - 40) / 8 * chart_height
        c.setStrokeColor(color)
        c.setDash(4, 3)
        c.line(ox, y, 540, y)
        c.setDash()
        c.setFillColor(color)
        c.setFont("DocSans-Bold", 6)
        c.drawRightString(540, y + 4, label)
    points = []
    for index, (run, value, state) in enumerate(series):
        x = ox + 28 + index * 66
        y = oy + (value - 40) / 8 * chart_height
        points.append((x, y))
        point_color = RED if state == "Above UCL" else AMBER if state == "Warning" else BLUE
        c.setFillColor(point_color)
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
    case.add_gold(
        "PVD thickness SPC and alarm interlocks",
        "SPC points: "
        + ", ".join(f"{run} {value:.1f} nm ({state})" for run, value, state in series)
        + ". Warning is 45.0 nm and UCL is 47.0 nm.\n\n"
        + "Chart reconstruction: the horizontal x-axis is run sequence and the vertical y-axis is TiN thickness in nm. The blue solid line is the PVD-03 measured TiN-thickness series. Blue points mean inside or recovered below the warning threshold; amber points mean warning at or above 45.0 nm but below 47.0 nm; a red point means above the 47.0 nm UCL. The amber dashed line is the 45.0 nm warning threshold and the red dashed line is the 47.0 nm UCL. The series rises from R-2241 through a 47.4 nm peak at R-2245, then falls through R-2246 to a recovered 44.1 nm at R-2247.\n\n"
        + markdown_table(interlock_headers, interlock_rows),
    )
    spc_point_leaves = [
        leaf(
            f"p04.spc.{run.lower()}",
            f"{run} is {value:.1f} nm with state {state}.",
            harm=2 if run == "R-2245" else 1,
            evidence_policy={
                "type": "lexical",
                "allOf": [[run], [f"{value:.1f}"], ["nm"], [state]],
            },
        )
        for run, value, state in series
    ]
    case.add_region("p04.spc", "PVD thickness SPC chart points", "chart", spc_point_leaves, budget=2)
    case.add_region(
        "p04.spc-contract",
        "SPC chart axes, legend, thresholds, and trend",
        "chart",
        [
            leaf(
                "p04.spc.axes",
                "The chart uses run sequence on the horizontal x-axis and TiN thickness in nm on the vertical y-axis.",
                harm=2,
                claim_type="structure",
                evidence_policy={
                    "type": "lexical",
                    "allOf": [
                        ["horizontal x-axis", "x-axis", "horizontal axis"],
                        ["run sequence"],
                        ["vertical y-axis", "y-axis", "vertical axis"],
                        ["TiN thickness"],
                        ["nm"],
                    ],
                },
            ),
            leaf(
                "p04.spc.series",
                "The blue solid line is the PVD-03 measured TiN-thickness series.",
                harm=2,
                evidence_policy={"type": "lexical", "allOf": [["blue"], ["solid line"], ["PVD-03"], ["measured"], ["TiN thickness", "TiN-thickness"]]},
            ),
            leaf(
                "p04.spc.threshold.warning",
                "The amber dashed line is the 45.0 nm warning threshold.",
                harm=2,
                evidence_policy={"type": "lexical", "allOf": [["amber"], ["dashed line"], ["45.0 nm"], ["warning threshold"]]},
            ),
            leaf(
                "p04.spc.threshold.ucl",
                "The red dashed line is the 47.0 nm UCL.",
                harm=2,
                evidence_policy={"type": "lexical", "allOf": [["red"], ["dashed line"], ["47.0 nm"], ["UCL"]]},
            ),
            leaf(
                "p04.spc.color.blue",
                "Blue points mean Inside or Recovered below the 45.0 nm warning threshold.",
                evidence_policy={"type": "lexical", "allOf": [["blue points", "blue"], ["Inside"], ["Recovered"], ["below"], ["45.0 nm"]]},
            ),
            leaf(
                "p04.spc.color.amber",
                "Amber points mean Warning at or above 45.0 nm but below 47.0 nm.",
                evidence_policy={"type": "lexical", "allOf": [["amber points", "amber"], ["Warning"], ["above"], ["45.0 nm"], ["below"], ["47.0 nm"]]},
            ),
            leaf(
                "p04.spc.color.red",
                "A red point means Above UCL at more than 47.0 nm.",
                evidence_policy={"type": "lexical", "allOf": [["red point", "red"], ["Above UCL"], ["more than", "above"], ["47.0 nm"]]},
            ),
            leaf(
                "p04.spc.trend",
                "The series rises from R-2241 through a 47.4 nm peak at R-2245, then falls through R-2246 to a recovered 44.1 nm at R-2247.",
                harm=2,
                evidence_policy={
                    "type": "lexical",
                    "allOf": [["rises"], ["R-2241"], ["47.4 nm"], ["peak"], ["R-2245"], ["falls"], ["R-2246"], ["44.1 nm"], ["R-2247"], ["recovered"]],
                },
            ),
        ],
        budget=2,
    )
    interlock_bindings = {(row[0], field) for row in interlock_rows for field in {"Observed", "State", "Disposition"}}
    case.add_region("p04.interlocks", "PVD alarm interlocks", "table", table_leaves("p04.interlocks", interlock_headers, interlock_rows, consequential={("Clamp purge", "State"), ("Monitor residual", "State")}, scored_bindings=interlock_bindings), budget=1, closed_world=True)

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
    case.add_gold("SEM review contact sheet", "The page labels only the archive frame and inspected site; the morphology must be recovered from each image. IMG-224 / W07 D5 shows two bright irregular metal flakes, including an adjacent smaller flake. IMG-223 / W05 E2 shows a long diagonal scratch crossing the field. IMG-227 / W12 A6 shows a bright edge-residue band with small bead deposits. IMG-226 / W09 F3 is visually clean apart from low-level background specks.")
    case.add_region(
        "p05.image.224",
        "IMG-224 metal-flake SEM",
        "image",
        [
            visual_leaf(
                "p05.img224.finding",
                "IMG-224 visibly shows two bright irregular metal flakes, one smaller and adjacent.",
                [["IMG-224"], ["two", "2"], ["bright", "high contrast"], ["irregular", "flake"], ["adjacent", "beside"]],
                harm=2,
            ),
        ],
        budget=2,
    )
    case.add_region("p05.image.223", "IMG-223 scratch SEM", "image", [visual_leaf("p05.img223.finding", "IMG-223 visibly shows a long diagonal scratch crossing the field.", [["IMG-223"], ["diagonal"], ["scratch"], ["crossing", "across"]], harm=2)], budget=2)
    case.add_region(
        "p05.image.227",
        "IMG-227 edge-bead SEM",
        "image",
        [
            visual_leaf(
                "p05.img227.finding",
                "IMG-227 visibly shows a bright edge-residue band with bead deposits.",
                [["IMG-227"], ["edge", "boundary"], ["band", "line"], ["bead", "deposits", "droplets", "bumps"]],
            ),
        ],
        budget=2,
    )
    case.add_region(
        "p05.image.226",
        "IMG-226 clean SEM",
        "image",
        [
            visual_leaf("p05.img226.finding", "IMG-226 is visually clean apart from low-level background specks.", [["IMG-226"], ["clean"], ["background", "field"], ["specks", "noise"]]),
        ],
        budget=2,
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
        ["Wafer 07", "Scrap", "Map W07-M1 plus IMG-224/225", "Y. Nishida"],
        ["Wafer 05", "Hold", "Map W05-S2 plus IMG-223", "A. Roy"],
        ["Wafer 03", "Hold", "Map W03-C3 plus metrology", "M. Alvarez"],
        ["Wafer 12", "Hold", "Map W12-E1 plus IMG-227", "K. Stone"],
        ["Wafer 09", "Conditional", "P4 parametric; REL-22-A required", "S. Han"],
        ["01,02,04,06,08,10,11", "Release", "Inside disposition limits", "MRB"],
    ]
    draw_label(c, "Material review board", 42, 410)
    draw_table(c, 42, 395, [145, 90, 220, 105], [mrb_headers, *mrb_rows], font_size=6.9, zebra=True)
    case.add_gold("Defect classification and MRB decisions", markdown_table(defect_headers, defect_rows) + "\n\n" + markdown_table(mrb_headers, mrb_rows))
    defect_bindings = {(row[0], field) for row in defect_rows for field in {"Count", "Wafer", "Gate"}}
    mrb_bindings = {(row[0], field) for row in mrb_rows for field in {"Decision", "Reason"}}
    case.add_region("p06.defects", "Defect classification", "table", table_leaves("p06.defects", defect_headers, defect_rows, scored_bindings=defect_bindings), closed_world=True)
    case.add_region("p06.mrb", "MRB decisions", "table", table_leaves("p06.mrb", mrb_headers, mrb_rows, consequential={("Wafer 07", "Decision"), ("Wafer 09", "Decision")}, scored_bindings=mrb_bindings), budget=2, closed_world=True)

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
    reliability_scan = make_scan(
        "HTOL CHAMBER LOAD / CONTROLLED WORK TICKET",
        [
            "Sample REL-22-A   Wafer 09   Stress HTOL 168 h",
            "Chamber H-17   Tray position C4   Loaded 11 Jun 14:22",
            "Door seal witness KT   Humidity logger HL-88 attached",
            "Interim 24 h observation: no electrical reject",
            "Final 168 h result: PENDING - wafer 09 remains segregated",
            "Custody: S Han 11 Jun 14:22 / Quality M Alvarez 11 Jun 14:31",
        ],
        width=1500,
        height=520,
        seed=2107,
        marks=[(1240, 267, "check")],
    )
    c.drawImage(image_reader(reliability_scan), 42, 70, width=528, height=182, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(HexColor("#969CA2"))
    c.rect(42, 70, 528, 182, fill=0, stroke=1)
    case.add_gold(
        "Reliability conditions and shipping allocation",
        markdown_table(rel_headers, rel_rows)
        + "\n\n"
        + markdown_table(ship_headers, ship_rows)
        + "\n\nThe scanned HTOL load ticket binds REL-22-A / wafer 09 to chamber H-17 and tray C4, loaded 2026-06-11 14:22. KT witnessed the door seal; humidity logger HL-88 is attached. The 24 h observation reports no electrical reject, but the final 168 h result remains pending and wafer 09 remains segregated. S. Han and M. Alvarez signed custody at 14:22 and 14:31.",
    )
    rel_bindings = {(row[0], field) for row in rel_rows for field in {"Stress", "Result", "Disposition use"}}
    ship_bindings = {(row[0], field) for row in ship_rows for field in {"Wafers", "Good die", "Shipment condition"}}
    case.add_region("p07.reliability", "Reliability sample plan", "table", table_leaves("p07.reliability", rel_headers, rel_rows, consequential={("REL-22-A", "Result")}, scored_bindings=rel_bindings), budget=1, closed_world=True)
    case.add_region("p07.shipping", "Shipping allocation", "table", table_leaves("p07.shipping", ship_headers, ship_rows, consequential={("Conditional", "Shipment condition"), ("Scrap", "Shipment condition")}, scored_bindings=ship_bindings), budget=2, closed_world=True)
    case.add_region(
        "p07.htol-ticket",
        "Scanned REL-22-A HTOL load ticket",
        "form",
        [
            leaf("p07.htol.chamber", "REL-22-A / wafer 09 is loaded in chamber H-17 at tray C4."),
            leaf("p07.htol.loaded", "The HTOL load time is 2026-06-11 at 14:22."),
            leaf("p07.htol.seal", "KT witnessed the chamber door seal."),
            leaf("p07.htol.logger", "Humidity logger HL-88 is attached."),
            leaf("p07.htol.interim", "The 24 h observation reports no electrical reject."),
            leaf("p07.htol.final", "The final 168 h result is pending and wafer 09 remains segregated.", harm=2),
        ],
        budget=2,
    )

    # Page 8 - scanned inspection worksheet plus native archive routing.
    c = case.new_page(
        "Defect-image verification worksheet",
        subtitle="Inspector marks retained with the image archive routing record",
        section_code="IQC-071 / 11 JUN",
    )
    worksheet = make_scan(
        "ASTER MICRODEVICES / DEFECT IMAGE VERIFICATION",
        [
            "Lot Q8R7-22   Worksheet IQC-071   Review set IMG-223/224/226/227",
            "[X] Wafer map compared with image archive",
            "[X] Neighboring-die review completed for W07 cluster",
            "[ ] Independent morphology confirmation completed",
            "[ ] Preliminary all-wafer COA released",
            "[N/A] Reticle excursion review (disabled for PVD-origin event)",
            "IMG-224 initial count: 1 flake",
            "Corrected count: 2 reportable objects; see controlled image archive",
            "Correction basis: second object resolved at archive magnification",
            "Inspector R Kim 11 Jun 09:42   Reviewer A Roy 11 Jun 11:06",
        ],
        width=1500,
        height=900,
        seed=2108,
        marks=[(55, 296, "strike")],
    )
    c.drawImage(image_reader(worksheet), 42, 260, width=528, height=355, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(HexColor("#969CA2"))
    c.rect(42, 260, 528, 355, fill=0, stroke=1)
    routing_headers = ["Archive object", "Custodian", "Checksum state", "Packet role"]
    routing_rows = [
        ["IQC-071", "Incoming quality", "Signed", "Inspection worksheet"],
        ["IMG set 223/224/226/227", "Fab image archive", "Matched", "Visual evidence"],
        ["MAP-11JUN", "Yield engineering", "Matched", "Coordinate source"],
        ["COA-DRAFT-02", "Quality systems", "Void", "Not shipment authority"],
    ]
    draw_label(c, "Archive routing", 42, 225)
    draw_table(c, 42, 210, [120, 130, 105, 165], [routing_headers, *routing_rows], font_size=6.8, zebra=True)
    case.add_gold(
        "Defect-image verification worksheet",
        "The scanned IQC-071 worksheet covers lot Q8R7-22 and image set IMG-223/224/226/227. Wafer-map comparison and neighboring-die review are checked. Independent morphology confirmation is unchecked. Preliminary all-wafer COA release is unchecked. Reticle excursion review is disabled as not applicable to the PVD-origin event. IMG-224's initial count of one is struck and corrected to two reportable objects; the worksheet defers morphology to the controlled image archive. R. Kim signed 2026-06-11 09:42 and A. Roy reviewed at 11:06.\n\n"
        + markdown_table(routing_headers, routing_rows),
    )
    case.add_region(
        "p08.worksheet",
        "Scanned defect-image verification worksheet",
        "form",
        [
            form_state_leaf("p08.check.map", "Wafer-map comparison is checked.", ["Wafer map compared with image archive", "Wafer-map comparison"], "checked"),
            form_state_leaf("p08.check.neighbor", "Neighboring-die review for the W07 cluster is checked.", ["Neighboring-die review", "neighboring die review"], "checked"),
            form_state_leaf("p08.check.morphology", "Independent morphology confirmation is unchecked.", ["Independent morphology confirmation", "morphology confirmation"], "unchecked", harm=2),
            form_state_leaf("p08.check.coa", "Preliminary all-wafer COA release is unchecked.", ["Preliminary all-wafer COA released", "all-wafer COA release"], "unchecked", harm=2),
            form_state_leaf("p08.check.reticle", "Reticle excursion review is disabled.", ["Reticle excursion review", "reticle review"], "disabled"),
            leaf("p08.check.reticle.reason", "Reticle excursion review is marked not applicable to the PVD-origin event.", evidence=["Reticle excursion review", ["not applicable", "N/A"], "PVD"]),
            leaf("p08.correction.old", "The initial IMG-224 count of one object is struck out."),
            leaf("p08.correction.final", "IMG-224 is corrected to two reportable objects and the worksheet defers morphology to the controlled image archive.", harm=2),
            leaf("p08.signoff", "R. Kim signed at 2026-06-11 09:42 and A. Roy reviewed at 11:06."),
        ],
        budget=2,
    )
    routing_bindings = {(row[0], field) for row in routing_rows for field in {"Checksum state", "Packet role"}}
    case.add_region("p08.routing", "Inspection archive routing", "table", table_leaves("p08.routing", routing_headers, routing_rows, consequential={("COA-DRAFT-02", "Checksum state")}, scored_bindings=routing_bindings), closed_world=True)

    # Page 9 - signed COA holdback and audit trail.
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
    case.add_gold(
        "Certificate holdback and final audit trail",
        markdown_table(coa_headers, coa_rows)
        + "\n\n"
        + markdown_table(audit_headers, audit_rows)
        + "\n\nThe preliminary all-wafer COA is void; only the signed COA values authorize shipment. Cross-source joins remain explicit: wafer 07's M1 map cluster and IMG-224/225 evidence support scrap; wafer 09's visually clean IMG-226 does not negate its P4 parametric condition and REL-22-A shipment gate; the W12 E1 edge map and IMG-227 support engineering hold.",
    )
    coa_bindings = {(row[0], field) for row in coa_rows for field in {"Signed value", "Application"}}
    audit_bindings = {(row[0], field) for row in audit_rows for field in {"Entry", "Effect"}}
    case.add_region("p09.coa", "Signed COA holdback", "table", table_leaves("p09.coa", coa_headers, coa_rows, consequential={("Released wafers", "Signed value"), ("Conditional wafer", "Application"), ("Scrap", "Application")}, scored_bindings=coa_bindings), budget=2, closed_world=True)
    case.add_region("p09.audit", "Lot-disposition audit trail", "table", table_leaves("p09.audit", audit_headers, audit_rows, scored_bindings=audit_bindings), closed_world=True)
    case.add_region(
        "p09.authority",
        "Shipment-authority statement",
        "text",
        [
            source_precedence_leaf(
                "p09.authority.control",
                "The preliminary all-wafer COA is void; only the signed COA values authorize shipment.",
                [["preliminary", "draft"], ["void"], ["only"], ["signed COA"], ["authorize", "authority"]],
            )
        ],
        budget=2,
        primary_axis="source_precedence",
    )
    case.add_region(
        "p09.cross-source",
        "Cross-source wafer disposition joins",
        "mixed",
        [
            leaf(
                "p09.join.w07",
                "Wafer 07's M1 map cluster and IMG-224 and IMG-225 evidence are explicitly linked to the scrap decision.",
                harm=2,
                claim_type="cross_page_join",
                evidence=[["Wafer 07", "W07"], ["M1"], ["IMG-224"], ["IMG-225"], ["scrap"]],
            ),
            leaf(
                "p09.join.w09",
                "Wafer 09's visually clean IMG-226 does not negate the P4 parametric condition or the REL-22-A shipment gate.",
                harm=2,
                claim_type="cross_page_join",
                evidence=[["Wafer 09", "W09"], ["IMG-226"], ["clean"], ["does not", "not"], ["P4"], ["REL-22-A"]],
            ),
            leaf(
                "p09.join.w12",
                "The W12 E1 edge map and IMG-227 evidence are explicitly linked to engineering hold.",
                claim_type="cross_page_join",
                evidence=[["W12"], ["E1"], ["IMG-227"], ["hold"]],
            ),
        ],
        budget=3,
        modality="mixed",
        primary_axis="mixed_modality_fusion",
        secondary_axes=["cross_page_join", "summarization_coverage"],
        text_only_recoverable=False,
        gold_section="Certificate holdback and final audit trail",
        source_anchors=[
            {"page": 2, "layer": "raster", "sectionPath": [case.title, "Wafer-map review"]},
            {"page": 5, "layer": "raster", "sectionPath": [case.title, "SEM review contact sheet"]},
            {"page": 6, "layer": "native_text", "sectionPath": [case.title, "Defect classification and MRB decisions"]},
            {"page": 7, "layer": "mixed", "sectionPath": [case.title, "Reliability conditions and shipping allocation"]},
            {"page": 9, "layer": "native_text", "sectionPath": [case.title, "Certificate holdback and final audit trail"]},
        ],
    )

    case.add_gold_conclusions_for_leaves(
        [
            "p02.map.w03.pattern",
            "p02.map.w05.pattern",
            "p02.map.w07.pattern",
            "p02.map.w09.pattern",
            "p02.map.w12.pattern",
            "p02.map.w02.reference",
            "p09.join.w07",
        ]
    )
    record = case.finish()
    rasterize_pdf_pages(
        case.pdf_path,
        case.pdf_path,
        {
            2: ScanProfile(seed=2102, dpi=132, skew_degrees=-0.24, noise_level=2.7, blur_radius=0.34, jpeg_quality=78),
            4: ScanProfile(seed=2104, color_mode="color", dpi=132, skew_degrees=0.31, noise_level=2.3, blur_radius=0.30, jpeg_quality=80),
        },
        metadata={
            "Creator": "Fab document imaging station 08",
            "Producer": "Enterprise Document Services",
        },
    )
    return record
