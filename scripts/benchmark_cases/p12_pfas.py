from __future__ import annotations

import math
import random

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
    make_scan,
    markdown_table,
    table_leaves,
)


def _chromatogram_plate() -> Image.Image:
    image = Image.new("RGB", (1320, 620), "#f7f7f4")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=17)
    small = ImageFont.load_default(size=12)
    bold = ImageFont.load_default(size=20)
    panels = [
        ("A  LRB / PFOS", 5.64, "no reportable peak; noise 41 cps", "#59636e", 0),
        ("B  CAL-0.5 / PFOS", 5.64, "area 4,572; S/N 12", "#1d4e89", 118),
        ("C  DW-240408-03 / PFOA", 4.41, "area 25,621; 3.42 ng/L", "#2d6a4f", 168),
        ("D  DW-240409-04 / IS overlay", 4.63, "original 38%; reinjection 91%", "#9e2a2b", 150),
    ]
    for index, (title, rt, note, color, amplitude) in enumerate(panels):
        ox = 28 + (index % 2) * 650
        oy = 26 + (index // 2) * 292
        draw.rectangle((ox, oy, ox + 615, oy + 260), outline="#8b9298", width=2)
        draw.text((ox + 16, oy + 12), title, font=bold, fill="#17202a")
        draw.line((ox + 58, oy + 205, ox + 575, oy + 205), fill="#17202a", width=2)
        draw.line((ox + 58, oy + 205, ox + 58, oy + 62), fill="#17202a", width=2)
        for tick in range(0, 9, 2):
            tick_x = ox + 58 + int(tick / 8.0 * 500)
            draw.line((tick_x, oy + 205, tick_x, oy + 210), fill="#17202a", width=1)
            draw.text((tick_x - 4, oy + 210), str(tick), font=small, fill="#59636e")
        axis_label = "Time (min)"
        axis_width = draw.textbbox((0, 0), axis_label, font=small)[2]
        draw.text((ox + 316 - axis_width / 2, oy + 224), axis_label, font=small, fill="#303840")
        draw.text((ox + 7, oy + 102), "Intensity\n(cps)", font=small, fill="#303840")
        rng = random.Random(1200 + index)
        trace: list[tuple[int, int]] = []
        peak_x = ox + 58 + int(rt / 8.0 * 500)
        for step in range(0, 500, 5):
            x = ox + 58 + step
            base = rng.randint(-3, 3)
            distance = (x - peak_x) / (16 if index != 3 else 22)
            height = amplitude * math.exp(-(distance * distance) / 2)
            if index == 3:
                second_distance = (x - peak_x - 38) / 24
                height += 92 * math.exp(-(second_distance * second_distance) / 2)
            trace.append((x, oy + 198 - int(height) + base))
        for first, second in zip(trace, trace[1:]):
            draw.line((*first, *second), fill=color, width=2)
        draw.line((peak_x, oy + 62, peak_x, oy + 205), fill="#b9bec3", width=1)
        draw.text((peak_x - 25, oy + 42), f"{rt:.2f} min", font=font, fill=color)
        draw.text((ox + 16, oy + 238), note, font=font, fill="#303840")
    return image


def _weighted_calibration_metrics(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Return slope, weighted R2, and maximum back-calculated residual for a 1/x2 fit."""
    weights = [1.0 / (level * level) for level in xs]
    sum_w = sum(weights)
    sum_wx = sum(weight * level for weight, level in zip(weights, xs))
    sum_wy = sum(weight * response for weight, response in zip(weights, ys))
    sum_wxx = sum(weight * level * level for weight, level in zip(weights, xs))
    sum_wxy = sum(weight * level * response for weight, level, response in zip(weights, xs, ys))
    determinant = sum_w * sum_wxx - sum_wx * sum_wx
    intercept = (sum_wy * sum_wxx - sum_wx * sum_wxy) / determinant
    slope = (sum_w * sum_wxy - sum_wx * sum_wy) / determinant
    weighted_mean = sum_wy / sum_w
    fitted = [intercept + slope * level for level in xs]
    weighted_sse = sum(weight * (response - predicted) ** 2 for weight, response, predicted in zip(weights, ys, fitted))
    weighted_sst = sum(weight * (response - weighted_mean) ** 2 for weight, response in zip(weights, ys))
    r_squared = 1.0 - weighted_sse / weighted_sst
    residuals = [((response - intercept) / (slope * level) - 1.0) * 100.0 for level, response in zip(xs, ys)]
    return slope, r_squared, max(abs(residual) for residual in residuals)


def build(output_root):
    calibration_curves = [
        ("PFOA", [0.25, 1, 5, 20, 80], [0.021, 0.077, 0.406, 1.393, 5.986], BLUE),
        ("PFOS", [0.5, 2, 10, 50, 100], [0.042, 0.184, 0.958, 4.753, 8.177], GREEN),
        ("HFPO-DA", [0.5, 2, 10, 50, 80], [0.044, 0.175, 0.790, 4.400, 6.632], AMBER),
    ]
    calibration_metrics = {
        name: _weighted_calibration_metrics(xs, ys) for name, xs, ys, _ in calibration_curves
    }
    case = CaseBuilder(
        output_root=output_root,
        case_id="P12-pfas-method-validation",
        title="PFAS Method Validation Supplement",
        family="environmental analytical laboratory",
        tags=["native-pdf", "scientific", "equations", "nested-table", "continuation", "scan", "chromatograms"],
        page_count=7,
        purpose="Test scientific notation, nested calibration fields, a continued precision table, a scanned sequence sheet, and analytical visual panels.",
        source_modality="born-digital native PDF with an embedded chromatogram plate and one scanned sequence sheet",
        document_ref="NORTHSTAR ANALYTICAL · MVS-PFAS-26-04 · controlled copy",
        metadata_date="D:20260618143000-07'00'",
    )

    # Page 1 - method conditions and sample manifest.
    c = case.new_page(
        "MV-PFAS-24-017 / Method conditions",
        subtitle="North River Environmental Laboratory | EPA 533 modified | Revision A",
        section_code="SUPPLEMENT S1",
    )
    draw_badge(c, "QA reviewed", 42, 684, GREEN)
    method_headers = ["Field", "Recorded value"]
    method_rows = [
        ["Instrument", "SCIEX 6500+ QTRAP; ESI negative"],
        ["Column", "Acquity BEH C18, 2.1 x 50 mm, 1.7 um"],
        ["Injection", "5 uL"],
        ["Mobile phase A", "5 mM ammonium acetate in water"],
        ["Mobile phase B", "Methanol"],
        ["Study dates", "8-19 April 2024"],
    ]
    draw_label(c, "Method record", 42, 650)
    draw_table(c, 42, 635, [122, 390], [method_headers, *method_rows], font_size=7.7, zebra=True)
    workflow = ["Receipt", "Preservation", "SPE extraction", "Dry-down", "Reconstitution", "LC-MS/MS", "Review"]
    draw_label(c, "Analytical workflow", 42, 463)
    for index, step in enumerate(workflow):
        x = 42 + index * 75
        c.setFillColor(HexColor("#F3F4F4"))
        c.setStrokeColor(HexColor("#9AA0A6"))
        c.roundRect(x, 420, 62, 27, 3, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("DocSans-Bold", 5.8)
        c.drawCentredString(x + 31, 430, step)
        if index < len(workflow) - 1:
            draw_arrow(c, x + 62, 433, x + 73, 433, color=BLUE, width=0.9)
    manifest_headers = ["Sample ID", "Matrix", "Collected", "Received", "pH", "Cl mg/L", "mL", "State"]
    manifest_rows = [
        ["FB-240408-01", "Field blank", "08 Apr 09:10", "08 Apr 15:42", "6.8", "<0.02", "252", "OK"],
        ["DW-240408-02", "Finished water", "08 Apr 09:25", "08 Apr 15:42", "7.2", "<0.02", "251", "OK"],
        ["DW-240408-03", "Finished water", "08 Apr 09:40", "08 Apr 15:42", "7.1", "<0.02", "249", "OK"],
        ["DW-240409-04", "Finished water", "09 Apr 10:05", "09 Apr 16:20", "7.4", "<0.02", "250", "OK"],
        ["DW-240409-05", "Finished water", "09 Apr 10:20", "09 Apr 16:20", "7.3", "<0.02", "250", "OK"],
        ["LRB-240410-01", "Reagent blank", "10 Apr 07:30", "10 Apr 07:30", "6.9", "<0.02", "250", "Prepared"],
        ["LCS-240410-01", "Control sample", "10 Apr 07:35", "10 Apr 07:35", "7.0", "<0.02", "250", "Prepared"],
        ["MSD-240410-03", "Matrix spike dup.", "10 Apr 07:40", "10 Apr 07:40", "7.1", "<0.02", "250", "Prepared"],
    ]
    draw_label(c, "Bottle and QC manifest", 42, 386)
    draw_table(c, 42, 372, [78, 82, 69, 69, 29, 43, 31, 62], [manifest_headers, *manifest_rows], font_size=5.65, zebra=True)
    case.add_gold(
        "Method conditions and sample manifest",
        markdown_table(method_headers, method_rows)
        + "\n\nWorkflow: "
        + " -> ".join(workflow)
        + ".\n\n"
        + markdown_table(manifest_headers, manifest_rows),
    )
    case.add_region("p01.method", "Method record", "table", table_leaves("p01.method", method_headers, method_rows), closed_world=True)
    case.add_region(
        "p01.workflow",
        "Analytical workflow",
        "diagram",
        [leaf(f"p01.workflow.{index:02d}", f"Workflow step {index} is {step}.") for index, step in enumerate(workflow, start=1)],
    )
    case.add_region("p01.manifest", "Bottle and QC manifest", "table", table_leaves("p01.manifest", manifest_headers, manifest_rows), budget=2, closed_world=True)

    # Page 2 - equations and nested calibration headers.
    c = case.new_page(
        "Calibration model and transitions",
        subtitle="Quantifier/qualifier transitions, regression fields, and reporting limits",
        section_code="CALIBRATION",
    )
    equations = [
        ("Response ratio", "R = A_native / A_IS"),
        ("Sample concentration", "C_sample = ((R - b) / m) x DF"),
        ("Detection limit", "LOD = t_(n-1,0.99) x SD_low"),
        ("Expanded uncertainty", "U95 = 2 x sqrt(u_cal^2 + u_rep^2 + u_vol^2 + u_rec^2)"),
    ]
    for index, (label, formula) in enumerate(equations):
        x = 42 + (index % 2) * 266
        y = 650 - (index // 2) * 65
        draw_label(c, label, x, y + 24)
        c.setFillColor(HexColor("#F4F5F5"))
        c.roundRect(x, y - 4, 246, 36, 4, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("DocSans", 8.2)
        c.drawString(x + 10, y + 10, formula)
    cal_headers = ["Analyte", "Internal standard", "Quant.", "Qual.", "RT", "m", "R2", "LOD / LOQ"]
    cal_rows = [
        ["PFBA", "13C4-PFBA", "213>169", "213>119", "2.18", "0.0921", "0.9987", "0.16 / 0.50"],
        ["PFPeA", "13C5-PFPeA", "263>219", "263>169", "2.74", "0.0875", "0.9991", "0.13 / 0.50"],
        ["PFHxA", "13C5-PFHxA", "313>269", "313>119", "3.32", "0.0814", "0.9985", "0.18 / 0.50"],
        ["PFHpA", "13C4-PFHpA", "363>319", "363>169", "3.86", "0.0778", "0.9990", "0.15 / 0.50"],
        ["PFOA", "13C8-PFOA", "413>369", "413>169", "4.41", f"{calibration_metrics['PFOA'][0]:.4f}", f"{calibration_metrics['PFOA'][1]:.4f}", "0.08 / 0.25"],
        ["PFNA", "13C9-PFNA", "463>419", "463>169", "4.95", "0.0712", "0.9989", "0.09 / 0.25"],
        ["PFDA", "13C6-PFDA", "513>469", "513>219", "5.48", "0.0686", "0.9986", "0.10 / 0.25"],
        ["PFBS", "18O2-PFBS", "299>80", "299>99", "3.05", "0.1033", "0.9992", "0.17 / 0.50"],
        ["PFHxS", "18O2-PFHxS", "399>80", "399>99", "4.63", "0.0968", "0.9988", "0.20 / 0.50"],
        ["PFOS", "13C8-PFOS", "499>80", "499>99", "5.64", f"{calibration_metrics['PFOS'][0]:.4f}", f"{calibration_metrics['PFOS'][1]:.4f}", "0.22 / 0.50"],
        ["6:2 FTS", "13C2-6:2FTS", "427>407", "427>81", "5.19", "0.0642", "0.9979", "0.31 / 1.00"],
        ["HFPO-DA", "13C3-HFPO-DA", "329>285", "329>169", "3.71", f"{calibration_metrics['HFPO-DA'][0]:.4f}", f"{calibration_metrics['HFPO-DA'][1]:.4f}", "0.14 / 0.50"],
    ]
    group_row = ["Identity", "", "Transitions", "", "Retention", "Regression", "Fit", "Limits ng/L"]
    draw_label(c, "Transition and calibration table", 42, 516)
    draw_table(c, 42, 501, [50, 88, 57, 57, 48, 54, 47, 88], [group_row, cal_headers, *cal_rows], font_size=6.2, header_rows=2, group_header_rows=1, zebra=True)
    case.add_gold(
        "Calibration model and transitions",
        "Equations:\n"
        + "\n".join(f"- **{label}:** `{formula}`" for label, formula in equations)
        + "\n\nThe table has grouped identity, transition, retention, regression, fit, and reporting-limit headers.\n\n"
        + markdown_table(cal_headers, cal_rows),
    )
    case.add_region(
        "p02.equations",
        "Calibration equations",
        "text",
        [leaf(f"p02.equations.{index:02d}", f"{label} is written as {formula}.", harm=2 if index in {1, 3} else 1) for index, (label, formula) in enumerate(equations)],
        budget=2,
    )
    case.add_region("p02.calibration", "Nested calibration table", "table", table_leaves("p02.calibration", cal_headers, cal_rows, consequential={("PFOA", "LOD / LOQ"), ("PFOS", "LOD / LOQ")}), budget=2, closed_world=True)

    # Page 3 - labeled calibration curves and residual review.
    c = case.new_page(
        "Calibration curves and residual review",
        subtitle="Five labeled levels per panel; weighted 1/x2 regression",
        section_code="FIGURE S3",
    )
    curves = calibration_curves
    for panel, (name, xs, ys, color) in enumerate(curves):
        ox = 42 + panel * 179
        oy = 405
        c.setStrokeColor(HexColor("#9DA3A8"))
        c.rect(ox, oy, 164, 255, fill=0, stroke=1)
        draw_label(c, name, ox + 10, oy + 235)
        c.setStrokeColor(INK)
        c.line(ox + 28, oy + 38, ox + 150, oy + 38)
        c.line(ox + 28, oy + 38, ox + 28, oy + 212)
        points = []
        label_offsets = [8, 20, 34, 14, 8]
        log_low = math.log10(min(xs))
        log_span = math.log10(max(xs)) - log_low
        for point_index, (level, response) in enumerate(zip(xs, ys)):
            px = ox + 33 + (math.log10(level) - log_low) / log_span * 112
            py = oy + 43 + response / max(ys) * 158
            points.append((px, py))
            c.setFillColor(color)
            c.circle(px, py, 2.2, fill=1, stroke=0)
            label_y = py + label_offsets[point_index]
            c.setStrokeColor(HexColor("#B7BDC3"))
            c.setLineWidth(0.35)
            c.line(px, py + 3, px, label_y - 2)
            c.setFillColor(INK)
            c.setFont("DocSans", 5.6)
            c.drawCentredString(px, label_y, f"{level:g}/{response:.3f}")
        c.setStrokeColor(color)
        c.setLineWidth(1.2)
        for first, second in zip(points, points[1:]):
            c.line(first[0], first[1], second[0], second[1])
        c.setFillColor(MUTED)
        c.setFont("DocSans", 5.5)
        c.drawCentredString(ox + 88, oy + 17, "log level ng/L / response ratio")
    residual_headers = ["Analyte", "Max abs residual", "Failing points", "Review decision"]
    residual_rows = [
        ["PFOA", f"{calibration_metrics['PFOA'][2]:.1f}%", "0", "1/x2 retained"],
        ["PFOS", f"{calibration_metrics['PFOS'][2]:.1f}%", "0", "High calibrator inside +/-15%"],
        ["HFPO-DA", f"{calibration_metrics['HFPO-DA'][2]:.1f}%", "0", "No curvature"],
    ]
    draw_label(c, "Residual disposition", 42, 360)
    draw_table(c, 42, 345, [80, 105, 85, 240], [residual_headers, *residual_rows], font_size=7.4, zebra=True)
    case.add_gold(
        "Calibration curves and residual review",
        "Curve labels are level ng/L / response ratio.\n\n"
        + "\n".join(f"- {name}: " + ", ".join(f"{x:g}/{y:.3f}" for x, y in zip(xs, ys)) for name, xs, ys, _ in curves)
        + "\n\n"
        + markdown_table(residual_headers, residual_rows),
    )
    for name, xs, ys, _ in curves:
        case.add_region(
            f"p03.curve.{name.lower().replace(':', '').replace(' ', '-')}",
            f"{name} calibration curve",
            "chart",
            [leaf(f"p03.curve.{name.lower().replace(':', '').replace(' ', '-')}.{index:02d}", f"{name} has response ratio {response:.3f} at {level:g} ng/L.") for index, (level, response) in enumerate(zip(xs, ys), start=1)],
        )
    case.add_region("p03.residuals", "Residual disposition", "table", table_leaves("p03.residuals", residual_headers, residual_rows), closed_world=True)

    # Pages 4-5 - one continued accuracy and precision table.
    s4_headers = ["Analyte", "Low rec / RSD", "Mid rec / RSD", "High rec / RSD", "n", "State"]
    s4_rows = [
        ["PFBA", "96 / 8.4", "101 / 4.6", "99 / 3.8", "7", "Pass"],
        ["PFPeA", "93 / 9.1", "98 / 5.2", "101 / 4.1", "7", "Pass"],
        ["PFHxA", "91 / 10.3", "97 / 5.8", "100 / 4.3", "7", "Pass"],
        ["PFHpA", "95 / 7.9", "99 / 4.9", "102 / 4.0", "7", "Pass"],
        ["PFOA", "98 / 6.8", "103 / 3.7", "101 / 3.2", "7", "Pass"],
        ["PFNA", "97 / 7.2", "102 / 4.1", "100 / 3.6", "7", "Pass"],
        ["PFDA", "92 / 11.5", "96 / 6.3", "99 / 4.9", "7", "Pass"],
        ["PFBS", "104 / 9.7", "99 / 4.8", "98 / 4.0", "7", "Pass"],
        ["PFHxS", "101 / 8.9", "100 / 4.4", "97 / 3.9", "7", "Pass"],
        ["PFOS", "89 / 12.6", "95 / 6.7", "96 / 5.1", "7", "Pass"],
        ["6:2 FTS", "86 / 14.8", "92 / 7.4", "94 / 6.3", "7", "Pass"],
        ["HFPO-DA", "99 / 7.5", "104 / 4.2", "103 / 3.5", "7", "Pass"],
    ]
    c = case.new_page(
        "Table S4 - Accuracy and precision",
        subtitle="Part 1 of 2 | fortified reagent water | recovery % / RSD %",
        section_code="TABLE S4",
    )
    draw_table(c, 42, 660, [68, 105, 105, 105, 38, 65], [s4_headers, *s4_rows[:6]], font_size=7.3, zebra=True)
    draw_label(c, "Acceptance criteria", 42, 405)
    draw_paragraph(c, "Recovery 70-130%; RSD <= 20%. Low level equals 2x LOQ for PFOA, PFNA, and PFDA and equals LOQ for the remaining analytes.", 42, 387, 500, size=8.4, leading=11.5)
    c.setFillColor(MUTED)
    c.setFont("DocSans-Italic", 8)
    c.drawString(42, 330, "Table S4 continued — PFDA through HFPO-DA appear on page 5.")
    case.add_gold(
        "Table S4 - Accuracy and precision, part 1",
        markdown_table(s4_headers, s4_rows[:6])
        + "\n\nAcceptance: recovery 70-130%; RSD <= 20%. "
        + "Table S4 continues on the next page with PFDA through HFPO-DA under repeated headers.",
    )
    case.add_region("p04.s4", "Table S4 rows PFBA-PFNA", "table", table_leaves("p04.s4", s4_headers, s4_rows[:6]), budget=2, closed_world=True)
    case.add_region(
        "p04.continuation",
        "Continuation notice",
        "structure",
        [
            leaf("p04.continuation.rows", "Table S4 continues on the next page with PFDA through HFPO-DA."),
            leaf("p04.continuation.headers", "The continued Table S4 uses repeated column headers."),
        ],
    )

    c = case.new_page(
        "Table S4 - Accuracy and precision (continued)",
        subtitle="Part 2 of 2 | fortified reagent water | recovery % / RSD %",
        section_code="TABLE S4 CONT.",
    )
    draw_table(c, 42, 660, [68, 105, 105, 105, 38, 65], [s4_headers, *s4_rows[6:]], font_size=7.3, zebra=True)
    spike_headers = ["Analyte", "Native", "Spike", "MS rec", "MSD rec", "RPD", "Qualifier"]
    spike_rows = [
        ["PFOA", "3.42", "10.00", "96", "98", "2.1", "None"],
        ["PFOS", "0.74", "10.00", "91", "88", "3.4", "J: native <2x LOQ"],
        ["PFHxS", "1.16", "10.00", "102", "99", "3.0", "None"],
        ["HFPO-DA", "<0.50", "10.00", "105", "106", "1.0", "U native"],
        ["6:2 FTS", "<1.00", "10.00", "84", "87", "3.5", "Low bias monitored"],
    ]
    draw_label(c, "DW-240408-03 matrix spike duplicate", 42, 395)
    draw_table(c, 42, 380, [61, 56, 52, 55, 62, 45, 170], [spike_headers, *spike_rows], font_size=6.6, zebra=True)
    case.add_gold(
        "Table S4 - Accuracy and precision, part 2",
        "This page continues Table S4 from the prior page; repeated headers are not data rows.\n\n"
        + markdown_table(s4_headers, s4_rows[6:])
        + "\n\n"
        + markdown_table(spike_headers, spike_rows),
    )
    case.add_region("p05.s4", "Table S4 rows PFDA-HFPO-DA", "table", table_leaves("p05.s4", s4_headers, s4_rows[6:]), budget=2, closed_world=True)
    case.add_region(
        "p05.continuation",
        "Continuation identity",
        "structure",
        [
            leaf("p05.continuation.same-table", "This page continues Table S4 from the prior page."),
            leaf("p05.continuation.headers-not-data", "The repeated Table S4 headers are not data rows."),
        ],
    )
    case.add_region("p05.spike", "Matrix spike duplicate", "table", table_leaves("p05.spike", spike_headers, spike_rows, consequential={("PFOS", "Qualifier")}), budget=2, closed_world=True)

    # Page 6 - raster laboratory sequence sheet.
    c = case.new_page(
        "Instrument sequence and reinjection review",
        subtitle="Signed bench copy scanned after technical review",
        section_code="BATCH 240410",
    )
    seq_headers = ["Seq", "Type", "Vial", "Sample ID", "Time", "IS", "Carry", "State"]
    seq_rows = [
        ["01", "Blank", "A01", "SBLK-01", "08:10", "Y", "Clear", "Accepted"],
        ["02", "Cal", "A02", "CAL-0.5", "08:23", "Y", "Clear", "Accepted"],
        ["03", "Cal", "A03", "CAL-1", "08:36", "Y", "Clear", "Accepted"],
        ["04", "Cal", "A04", "CAL-2", "08:49", "Y", "Clear", "Accepted"],
        ["05", "Cal", "A05", "CAL-5", "09:02", "Y", "Clear", "Accepted"],
        ["06", "Cal", "A06", "CAL-10", "09:15", "Y", "Clear", "Accepted"],
        ["07", "Cal", "A07", "CAL-20", "09:28", "Y", "Clear", "Accepted"],
        ["08", "Cal", "A08", "CAL-50", "09:41", "Y", "Clear", "Accepted"],
        ["09", "Cal", "A09", "CAL-80", "09:54", "Y", "Clear", "Accepted"],
        ["10", "Blank", "B01", "LRB-240410-01", "10:07", "Y", "Clear", "Accepted"],
        ["11", "LCS", "B02", "LCS-240410-01", "10:20", "Y", "Clear", "Accepted"],
        ["12", "Sample", "B03", "FB-240408-01", "10:33", "Y", "Clear", "Accepted"],
        ["13", "Sample", "B04", "DW-240408-02", "10:46", "Y", "Clear", "Accepted"],
        ["14", "Sample", "B05", "DW-240408-03", "10:59", "Y", "Clear", "Accepted"],
        ["15", "MS", "B06", "DW-240408-03-MS", "11:12", "Y", "Clear", "Accepted"],
        ["16", "MSD", "B07", "DW-240408-03-MSD", "11:25", "Y", "Clear", "Accepted"],
        ["17", "CCV", "B08", "CCV-10", "11:38", "Y", "Clear", "Accepted"],
        ["18", "Sample", "B09", "DW-240409-04", "11:51", "N", "Clear", "Reinject"],
        ["19", "Sample", "C01", "DW-240409-04-RI", "12:18", "Y", "Clear", "Accepted"],
        ["20", "Sample", "C02", "DW-240409-05", "12:31", "Y", "Clear", "Accepted"],
    ]
    scan_lines = [" ".join(f"{header:<12}" for header in seq_headers)] + [
        f"{row[0]:<4} {row[1]:<7} {row[2]:<4} {row[3]:<19} {row[4]:<6} {row[5]:<2} {row[6]:<6} {row[7]}" for row in seq_rows
    ]
    scan_lines += ["", "Analyst M. Iyer 19 Apr 14:05   Technical L. Chen 22 Apr 09:40", "QA R. Patel 22 Apr 16:10   Seq 19 controls DW-240409-04 results"]
    scan = make_scan("LC-MS/MS BATCH SEQUENCE / MV-PFAS-24-017", scan_lines, width=1500, height=980, seed=1206, marks=[(1160, 846, "check")])
    c.drawImage(image_reader(scan), 42, 205, width=528, height=430, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(HexColor("#9AA0A6"))
    c.rect(42, 205, 528, 430, fill=0, stroke=1)
    draw_paragraph(c, "Sequence 18 failed internal-standard recovery. Sequence 19 is the accepted reinjection and supplies the final DW-240409-04 result.", 42, 174, 520, font="DocSans-Bold", size=8.6, leading=12, color=RED)
    case.add_gold("Instrument sequence and reinjection review", markdown_table(seq_headers, seq_rows) + "\n\nSequence 18 failed internal-standard recovery. Sequence 19 is the accepted reinjection used for final DW-240409-04 results. Analyst M. Iyer signed 2024-04-19 14:05; technical reviewer L. Chen signed 2024-04-22 09:40; QA reviewer R. Patel signed 2024-04-22 16:10.")
    case.add_region("p06.sequence", "Scanned instrument sequence", "form", table_leaves("p06.sequence", seq_headers, seq_rows, consequential={("18", "State"), ("19", "State")}), budget=2, closed_world=True)
    case.add_region(
        "p06.signoff",
        "Sequence review signoff",
        "form",
        [
            leaf("p06.signoff.analyst", "M. Iyer signed analyst review on 2024-04-19 at 14:05."),
            leaf("p06.signoff.technical", "L. Chen signed technical review on 2024-04-22 at 09:40."),
            leaf("p06.signoff.qa", "R. Patel signed QA review on 2024-04-22 at 16:10."),
            leaf("p06.signoff.control", "Sequence 19, not Sequence 18, controls final DW-240409-04 results.", harm=2),
        ],
        budget=2,
    )

    # Page 7 - raster chromatograms, final results, and uncertainty.
    c = case.new_page(
        "Chromatograms, final results, and uncertainty",
        subtitle="Plate S7; references distinguish direct traces from contextual QC evidence",
        section_code="FINAL DATA",
    )
    plate = _chromatogram_plate()
    c.drawImage(image_reader(plate), 42, 410, width=528, height=248, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(HexColor("#9AA0A6"))
    c.rect(42, 410, 528, 248, fill=0, stroke=1)
    result_headers = ["Result ID", "Sample", "Analyte", "Result", "Qual.", "U95", "Reference"]
    result_rows = [
        ["R-01", "FB-240408-01", "PFOA", "<0.25", "U", "-", "p2 limit / context"],
        ["R-02", "DW-240408-02", "PFOA", "2.18", "-", "0.42", "S7C / other sample"],
        ["R-03", "DW-240408-02", "PFOS", "0.62", "J", "0.18", "S7B / cal context"],
        ["R-04", "DW-240408-03", "PFOA", "3.42", "-", "0.55", "S7C / direct"],
        ["R-05", "DW-240408-03", "PFOS", "0.74", "J", "0.19", "S7A / blank context"],
        ["R-06", "DW-240409-04", "PFOA", "1.06", "J", "0.25", "S7D IS / Seq 19"],
        ["R-07", "DW-240409-04", "PFOS", "<0.50", "U", "-", "S7D IS / Seq 19"],
        ["R-08", "DW-240409-05", "PFOA", "4.87", "-", "0.72", "No S7 panel"],
    ]
    draw_table(c, 42, 385, [43, 101, 56, 50, 38, 46, 74], [result_headers, *result_rows], font_size=6.1, zebra=True)
    uncertainty_headers = ["Analyte", "u cal", "u rep", "u vol", "u rec", "U95"]
    uncertainty_rows = [
        ["PFOA", "5.2%", "4.1%", "1.5%", "3.6%", "15.4%"],
        ["PFOS", "7.4%", "6.9%", "1.5%", "5.1%", "22.8%"],
        ["HFPO-DA", "4.8%", "3.7%", "1.5%", "3.2%", "13.8%"],
    ]
    draw_label(c, "Expanded uncertainty", 42, 205)
    draw_table(c, 42, 192, [70, 52, 52, 52, 52, 66], [uncertainty_headers, *uncertainty_rows], font_size=5.9, zebra=True)
    case.add_gold(
        "Chromatograms, final results, and uncertainty",
        "Chromatogram axes are time (min) and intensity (cps). Panels: A LRB/PFOS has no reportable peak and noise 41 cps; B CAL-0.5/PFOS is 5.64 min, area 4,572, S/N 12; C DW-240408-03/PFOA is 4.41 min, area 25,621, 3.42 ng/L; D DW-240409-04 internal-standard overlay is 38% original and 91% on reinjection.\n\n"
        + markdown_table(result_headers, result_rows)
        + "\n\n"
        + markdown_table(uncertainty_headers, uncertainty_rows),
    )
    case.add_region(
        "p07.chromatograms",
        "Chromatogram plate S7",
        "image",
        [
            leaf("p07.chrom.axes.time", "The chromatogram x-axis is Time (min)."),
            leaf("p07.chrom.axes.intensity", "The chromatogram y-axis is Intensity (cps)."),
            leaf("p07.chrom.a.binding", "Panel A is LRB/PFOS."),
            leaf("p07.chrom.a.peak", "Panel A has no reportable peak."),
            leaf("p07.chrom.a.noise", "Panel A noise is 41 cps."),
            leaf("p07.chrom.b.binding", "Panel B is CAL-0.5/PFOS."),
            leaf("p07.chrom.b.rt", "Panel B retention time is 5.64 min."),
            leaf("p07.chrom.b.area", "Panel B area is 4,572."),
            leaf("p07.chrom.b.sn", "Panel B S/N is 12."),
            leaf("p07.chrom.c.binding", "Panel C is DW-240408-03/PFOA."),
            leaf("p07.chrom.c.rt", "Panel C retention time is 4.41 min."),
            leaf("p07.chrom.c.area", "Panel C area is 25,621."),
            leaf("p07.chrom.c.concentration", "Panel C concentration is 3.42 ng/L.", harm=2),
            leaf("p07.chrom.d.original", "Panel D shows original internal-standard recovery of 38% for DW-240409-04."),
            leaf("p07.chrom.d.reinject", "Panel D shows reinjection internal-standard recovery of 91% for DW-240409-04.", harm=2),
        ],
        budget=2,
    )
    case.add_region("p07.results", "Final result table", "table", table_leaves("p07.results", result_headers, result_rows, consequential={("R-06", "Reference"), ("R-07", "Reference")}), budget=2, closed_world=True)
    case.add_region("p07.uncertainty", "Expanded uncertainty table", "table", table_leaves("p07.uncertainty", uncertainty_headers, uncertainty_rows), closed_world=True)

    return case.finish()
