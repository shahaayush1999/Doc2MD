from __future__ import annotations

"""Generate the long-form HTX-204 Site 014 monitoring packet.

The page-modality constants are part of the source contract. Full-page scan
pages are deterministically rasterized after composition; mixed pages retain
native text plus embedded scanned source regions.
"""

import random
import re
from collections.abc import Sequence

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from reportlab.lib.colors import HexColor

from .common import (
    AMBER,
    BLUE,
    INK,
    MUTED,
    CaseBuilder,
    draw_badge,
    draw_label,
    draw_paragraph,
    draw_table,
    extract_evidence_signals,
    image_reader,
    leaf,
    markdown_table,
    form_state_leaf,
    table_leaves,
)
from .rasterize import ScanProfile, rasterize_pdf_pages


INTENDED_NATIVE_ONLY_PAGES = (
    1, 2, 3, 4, 6, 7, 9, 10, 13, 14, 17, 19, 24, 26,
    29, 31, 33, 34, 35, 37, 39, 40, 41, 43, 44, 45, 47, 48,
)
INTENDED_FULL_PAGE_SCAN_PAGES = (5, 8, 11, 12, 16, 20, 22, 25, 30, 38, 42, 46)
INTENDED_MIXED_PAGES = (15, 18, 21, 23, 27, 28, 32, 36)
INTENDED_PAGE_MODALITY = {
    **{page: "native-only" for page in INTENDED_NATIVE_ONLY_PAGES},
    **{page: "full-page-scan" for page in INTENDED_FULL_PAGE_SCAN_PAGES},
    **{page: "mixed" for page in INTENDED_MIXED_PAGES},
}

# These joins intentionally span ten or more pages.  They are documented here
# so a future corpus audit can verify that shortening or rearranging the packet
# has not silently removed its long-context challenge.
ENTITY_DISTANCE_JOINS = {
    "subject-014-003": (2, 7, 11, 13, 16, 17, 20, 26, 29, 39, 47, 48),
    "subject-014-007": (2, 3, 6, 12, 13, 14, 17, 25, 28, 32, 37, 44, 45, 48),
    "kit-K-204-153": (5, 12, 14, 17, 25, 28, 32, 37, 44, 45, 48),
    "query-Q-77": (7, 11, 13, 16, 17, 26, 39, 47, 48),
    "shipment-SH-204-45": (4, 15, 20, 26, 39, 41, 47),
    "deviation-DEV-014-09": (7, 10, 13, 15, 22, 39, 47),
    "subject-014-016": (2, 6, 10, 21, 22, 25, 28, 30, 40, 46, 47, 48),
    "subject-014-014": (2, 3, 6, 7, 18, 26, 36, 39, 45, 47),
    "waiver-W-14": (2, 3, 8, 33, 42, 43, 47),
}


def _pil_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    """Return a deterministic bundled font without depending on host fonts."""
    return ImageFont.load_default(size=size)


def _paper(width: int, height: int, seed: int) -> Image.Image:
    rng = random.Random(seed)
    image = Image.new("L", (width, height), 247)
    pixels = image.load()
    for _ in range(width * height // 48):
        pixels[rng.randrange(width), rng.randrange(height)] = rng.randrange(222, 251)
    return image.filter(ImageFilter.GaussianBlur(0.20))


def _wrap_scan(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        proposed = word if not current else f"{current} {word}"
        if draw.textlength(proposed, font=font) <= width:
            current = proposed
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _scan_checkbox(draw: ImageDraw.ImageDraw, x: int, y: int, state: str, label: str, font: ImageFont.ImageFont) -> None:
    edge = 30
    ink = 38 if state != "disabled" else 145
    draw.rectangle((x, y, x + edge, y + edge), outline=ink, width=3)
    if state == "checked":
        draw.line((x + 4, y + 15, x + 12, y + 25), fill=25, width=5)
        draw.line((x + 12, y + 25, x + 28, y + 3), fill=25, width=5)
    elif state == "crossed":
        draw.line((x + 3, y + 3, x + 27, y + 27), fill=30, width=4)
        draw.line((x + 27, y + 3, x + 3, y + 27), fill=30, width=4)
    elif state == "disabled":
        draw.rectangle((x + 3, y + 3, x + 27, y + 27), fill=205)
        draw.line((x + 4, y + 26, x + 26, y + 4), fill=145, width=3)
    draw.text((x + 44, y + 1), label, font=font, fill=ink)


def _scan_document(
    title: str,
    subtitle: str,
    sections: Sequence[tuple[str, Sequence[str]]],
    *,
    controls: Sequence[tuple[str, str]] = (),
    corrections: Sequence[tuple[str, str, str]] = (),
    signatures: Sequence[str] = (),
    seed: int,
    width: int = 1600,
    height: int = 1950,
    form_code: str = "CONTROLLED SOURCE",
) -> Image.Image:
    """Create a readable deterministic source scan with visible state marks."""
    image = _paper(width, height, seed)
    draw = ImageDraw.Draw(image)
    small = _pil_font(22)
    regular = _pil_font(25)
    bold = _pil_font(29, bold=True)
    heading = _pil_font(36, bold=True)

    draw.rectangle((34, 28, width - 34, height - 28), outline=95, width=2)
    draw.rectangle((35, 29, width - 35, 128), fill=231)
    draw.text((65, 48), title, font=heading, fill=24)
    draw.text((width - 65, 53), form_code, font=small, fill=55, anchor="ra")
    draw.text((68, 145), subtitle, font=regular, fill=45)
    draw.line((65, 190, width - 65, 190), fill=95, width=2)

    y = 220
    for section_index, (section_title, paragraphs) in enumerate(sections):
        if y > height - 300:
            raise ValueError(f"Scanned source content exceeds page before section {section_title!r}")
        fill = 232 if section_index % 2 == 0 else 238
        draw.rectangle((64, y, width - 64, y + 43), fill=fill)
        draw.text((78, y + 6), section_title.upper(), font=bold, fill=35)
        y += 58
        for paragraph in paragraphs:
            for line in _wrap_scan(draw, paragraph, regular, width - 170):
                draw.text((82, y), line, font=regular, fill=38)
                y += 34
            y += 8
        draw.line((68, y, width - 68, y), fill=185, width=1)
        y += 18

    if corrections:
        draw.rectangle((64, y, width - 64, y + 43), fill=232)
        draw.text((78, y + 6), "CORRECTION HISTORY - ORIGINAL ENTRY REMAINS VISIBLE", font=bold, fill=35)
        y += 61
        for original, replacement, initials in corrections:
            original_lines = _wrap_scan(draw, original, regular, 1260)
            for original_line in original_lines:
                draw.text((82, y), original_line, font=regular, fill=70)
                length = min(1260, int(draw.textlength(original_line, font=regular)))
                draw.line((80, y + 17, 80 + length, y + 13), fill=45, width=4)
                y += 34
            draw.text((105, y), f"Corrected: {replacement} [{initials}]", font=regular, fill=28)
            y += 48
        draw.line((68, y, width - 68, y), fill=185, width=1)
        y += 18

    if controls:
        draw.rectangle((64, y, width - 64, y + 43), fill=232)
        draw.text((78, y + 6), "RECORDED STATES", font=bold, fill=35)
        y += 60
        columns = 2 if len(controls) > 4 else 1
        column_width = 720
        for index, (label, state) in enumerate(controls):
            col = index % columns
            row = index // columns
            _scan_checkbox(draw, 85 + col * column_width, y + row * 49, state, label, regular)
        y += ((len(controls) + columns - 1) // columns) * 49 + 18

    if signatures:
        draw.line((68, y, width - 68, y), fill=120, width=1)
        y += 18
        for signature in signatures:
            for line in _wrap_scan(draw, signature, small, width - 170):
                draw.text((82, y), line, font=small, fill=48)
                y += 30
            y += 3

    if y > height - 55:
        raise ValueError(f"Scanned source content ends below footer: y={y}, height={height}")
    draw.text((68, height - 58), "Controlled copy - alterations must retain the prior entry and attribution", font=small, fill=88)
    draw.text((width - 68, height - 58), f"scan ref {seed:04d}", font=small, fill=88, anchor="ra")
    return ImageEnhance.Contrast(image).enhance(1.08).convert("RGB")


def _place_full_scan(canvas, scan: Image.Image) -> None:
    canvas.drawImage(image_reader(scan), 42, 48, width=528, height=642, preserveAspectRatio=True, mask="auto")
    canvas.setStrokeColor(HexColor("#969CA2"))
    canvas.rect(42, 48, 528, 642, fill=0, stroke=1)


def _place_mixed_scan(canvas, scan: Image.Image, *, y: float = 390, height: float = 280) -> None:
    canvas.drawImage(image_reader(scan), 42, y, width=528, height=height, preserveAspectRatio=True, mask="auto")
    canvas.setStrokeColor(HexColor("#969CA2"))
    canvas.rect(42, y, 528, height, fill=0, stroke=1)


def _facts(
    case: CaseBuilder,
    suffix: str,
    label: str,
    kind: str,
    expectations: Sequence[tuple],
    *,
    budget: int = 1,
    closed_world: bool = False,
    primary_axis: str | None = None,
    secondary_axes: Sequence[str] = (),
) -> None:
    prefix = f"p{case.page_number:02d}.{suffix}"
    leaves = []
    for item in expectations:
        leaf_suffix, expectation = item[0], item[1]
        harm = item[2] if len(item) == 3 else 1
        if len(item) >= 4:
            harm = item[2]
            policy_spec = item[3]
            if isinstance(policy_spec, dict):
                leaves.append(
                    leaf(
                        f"{prefix}.{leaf_suffix}",
                        expectation,
                        harm=harm,
                        evidence=policy_spec["evidence"],
                    )
                )
            else:
                label_text, state = policy_spec
                leaves.append(
                    form_state_leaf(
                        f"{prefix}.{leaf_suffix}",
                        expectation,
                        label_text,
                        state,
                        harm=harm,
                    )
                )
        else:
            leaves.append(leaf(f"{prefix}.{leaf_suffix}", expectation, harm=harm))
    case.add_region(
        prefix,
        label,
        kind,
        leaves,
        budget=budget,
        closed_world=closed_world,
        primary_axis=primary_axis,
        secondary_axes=secondary_axes,
    )


def _expand_protocol_dates(value: object) -> str:
    """Preserve the source's packet-local date representation verbatim."""
    return str(value)


def _gold_table(case: CaseBuilder, heading: str, headers: Sequence[str], rows: Sequence[Sequence[str]], intro: str = "") -> None:
    # Faithful reconstruction preserves visible packet-local shorthand such as
    # ``08 May`` instead of inserting a year that is not printed in the row.
    gold_rows = [[_expand_protocol_dates(value) for value in row] for row in rows]
    expanded_intro = _expand_protocol_dates(intro.strip())
    body = (expanded_intro + "\n\n" if expanded_intro else "") + markdown_table(headers, gold_rows)
    case.add_gold(f"Page {case.page_number:02d} - {heading}", body)


def _gold_scan(case: CaseBuilder, heading: str, body: str) -> None:
    case.add_gold(f"Page {case.page_number:02d} - {heading}", body)


def _selected_table_region(
    case: CaseBuilder,
    suffix: str,
    label: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    bindings: Sequence[tuple[str, str]],
    *,
    budget: int = 2,
    consequential: Sequence[tuple[str, str]] = (),
    primary_axis: str = "table_reconstruction",
    secondary_axes: Sequence[str] = ("precise_recall",),
) -> None:
    """Add a bounded table region with explicit row/column/value policies."""
    prefix = f"p{case.page_number:02d}.{suffix}"
    fact_rows = [[_expand_protocol_dates(value) for value in row] for row in rows]
    raw_value_aliases = {
        (str(fact_row[0]), str(headers[column_index])): [str(source_row[column_index])]
        for source_row, fact_row in zip(rows, fact_rows, strict=True)
        for column_index in range(1, len(headers))
        if str(source_row[column_index]) != str(fact_row[column_index])
    }
    case.add_region(
        prefix,
        label,
        "table",
        table_leaves(
            prefix,
            headers,
            fact_rows,
            scored_bindings=set(bindings),
            consequential=set(consequential),
            value_aliases=raw_value_aliases,
        ),
        budget=budget,
        closed_world=True,
        primary_axis=primary_axis,
        secondary_axes=secondary_axes,
    )


def _complete_evidence(
    expectation: str,
    evidence: Sequence[str | Sequence[str]],
) -> list[str | Sequence[str]]:
    """Keep curated semantic anchors while making every literal mandatory.

    Facts v3 treats identifiers, dates, quantities, units, and finite-state
    words as independently falsifiable.  Adding each signal's formatting
    alternatives as its own all-of group prevents an otherwise strong binding
    from accepting a claim that omits or swaps one of those literals.
    """
    completed: list[str | Sequence[str]] = list(evidence)
    for signal in extract_evidence_signals(expectation):
        completed.append(list(signal.alternatives or (signal.value,)))
    return completed


def _source_anchor(case: CaseBuilder, page: int, layer: str) -> dict[str, object]:
    return {
        "page": page,
        "layer": layer,
        "sectionPath": [case.title, case.page_titles[page]],
    }


def build(output_root):
    case = CaseBuilder(
        output_root=output_root,
        case_id="P17-clinical-trial-site-monitoring",
        title="HTX-204 Site 014 Monitoring Source Packet",
        family="regulated clinical site monitoring",
        tags=[
            "long-context",
            "mixed-modality",
            "full-page-scans",
            "continued-tables",
            "source-precedence",
            "corrected-entries",
            "checkbox-state",
            "longitudinal-entities",
            "tail-obligations",
        ],
        page_count=48,
        purpose=(
            "Test faithful reconstruction of a realistically long regulated source packet whose controlling facts emerge through "
            "continued logs, scanned forms, visible corrections, cumulative state, delayed follow-up evidence, and tail obligations "
            "distributed across more than forty pages without a synthetic answer map."
        ),
        source_modality=(
            "48-page mixed packet: 28 intended native-only pages, 12 intended full-page scans, and 8 mixed pages "
            "with embedded scanned source regions"
        ),
        document_ref="HTX-204 | SITE 014 | MONITORING VISIT 03",
        metadata_date="D:20260509183000-05'00'",
    )
    case.set_page_modalities(
        native_pages=INTENDED_NATIVE_ONLY_PAGES,
        full_raster_pages=INTENDED_FULL_PAGE_SCAN_PAGES,
        mixed_pages=INTENDED_MIXED_PAGES,
    )

    # 1 - controlled visit authorization; intentionally neither a findings
    # summary nor a page-level answer map.
    c = case.new_page(
        "Monitoring visit authorization and source inventory",
        subtitle="Controlled working packet | Review window 08-09 May 2026",
        section_code="MV-03 / CONTROL",
    )
    draw_badge(c, "Source review authorized", 42, 684, BLUE)
    auth_headers = ["Control field", "Recorded value"]
    auth_rows = [
        ["Protocol", "HTX-204 / Amendment 6 dated 18 Mar 2026"],
        ["Site", "014 - Harbor Endocrine Research Center"],
        ["Principal investigator", "Dr. Neha Rao (NR)"],
        ["Clinical research associate", "Lina Sen (LS)"],
        ["On-site window", "08 May 2026 08:30 through 09 May 2026 16:30"],
        ["Data cut", "06 May 2026 at 18:00 local"],
        ["Review scope", "Consent, visits, safety, laboratory, pharmacy, ePRO, deviations, queries"],
    ]
    draw_label(c, "Authorization", 42, 651)
    y = draw_table(c, 42, 636, [150, 360], [auth_headers, *auth_rows], font_size=7.4, zebra=True)
    source_headers = ["Binder / system", "Custodian", "Controlled retrieval key", "Cutoff basis"]
    source_rows = [
        ["Subject source binder", "M. Kapoor", "SSR-014 / subject tabs", "Signed entries through review"],
        ["Central laboratory portal", "Lab interface", "NCL-S014 / accession key", "Amendments through 09 May"],
        ["Safety database export", "Site safety", "SAF-014-0605", "Exported 06 May"],
        ["Data-query console", "Data management", "DQC-HTX204-014", "State at each timestamp"],
        ["Pharmacy binder", "R. Patel", "IP-014 / restricted vault", "Physical count 08 May"],
        ["Monitoring workpapers", "L. Sen", "MV03-WP / signed index", "Contemporaneous review records"],
    ]
    draw_label(c, "Source map", 42, y - 24)
    draw_table(c, 42, y - 39, [145, 92, 120, 153], [source_headers, *source_rows], font_size=6.55, zebra=True)
    draw_paragraph(
        c,
        "This authorization identifies what may be reviewed and how the controlled repository locates it. It deliberately does not map source classes to packet pages or determine whether any item is resolved. Signed source records control their own fields according to the hierarchy on page 9.",
        42,
        145,
        510,
        size=8.2,
        leading=11.4,
        color=MUTED,
    )
    case.add_gold(
        "Page 01 - Monitoring visit authorization and source inventory",
        markdown_table(auth_headers, auth_rows) + "\n\n" + markdown_table(source_headers, source_rows),
    )
    _facts(
        case,
        "control",
        "Monitoring authorization and source inventory",
        "table",
        [
            ("site", "The packet is for Site 014 at Harbor Endocrine Research Center."),
            ("window", "The on-site review window runs from 2026-05-08 08:30 through 2026-05-09 16:30."),
            ("cut", "The ordinary data cut is 2026-05-06 at 18:00 local."),
            ("pharmacy-key", "The pharmacy binder is retrieved under IP-014 / restricted vault."),
            ("query-key", "The data-query console is retrieved under DQC-HTX204-014."),
        ],
        budget=2,
    )

    # 2 - enrollment roster.
    c = case.new_page(
        "Screening, randomization, and current disposition",
        subtitle="Roster at the 06 May data cut; disposition does not replace later source corrections",
        section_code="SUBJECT LOG / A",
    )
    roster_headers = ["Subject", "Consent", "Randomized", "Arm", "Current roster disposition", "Key locator"]
    roster_rows = [
        ["014-001", "03 Apr", "No", "-", "Screen failure / HbA1c 9.1%", "SF-01"],
        ["014-002", "05 Apr", "Yes", "B", "Completed W4", "V-002"],
        ["014-003", "07 Apr", "Yes", "A", "Active / W2 source correction", "V-003"],
        ["014-004", "10 Apr", "Yes", "B", "Withdrawn 24 Apr", "ET-004"],
        ["014-005", "12 Apr", "Yes", "A", "Completed W4", "V-005"],
        ["014-006", "15 Apr", "No", "-", "Screen failure / eGFR 42", "SF-06"],
        ["014-007", "18 Apr", "Yes", "B", "Active / pharmacy restriction", "V-007"],
        ["014-008", "20 Apr", "Yes", "A", "Active / lab receipt pending", "V-008"],
        ["014-009", "19 Apr", "Yes", "B", "Active / visit-window review", "V-009"],
        ["014-010", "23 Apr", "No", "-", "Screen failure / QTc 486 ms", "SF-10"],
        ["014-011", "26 Apr", "Yes", "A", "Active / amended lab report", "V-011"],
        ["014-012", "28 Apr", "Yes", "B", "Active / waiver W-14", "V-012"],
        ["014-013", "29 Apr", "Yes", "A", "Lost to follow-up 05 May", "FU-013"],
        ["014-014", "01 May", "Yes", "A", "Active / ePRO retraining", "V-014"],
        ["014-015", "02 May", "No", "-", "Screen failure / BP 168/98", "SF-15"],
        ["014-016", "04 May", "Yes", "B", "Active / masking review", "V-016"],
    ]
    draw_table(c, 36, 675, [57, 52, 63, 32, 198, 74], [roster_headers, *roster_rows], font_size=5.95, zebra=True)
    draw_paragraph(c, "Subject identifiers remain stable across visit, safety, laboratory, pharmacy, query, and action records. A roster label is an index state, not a substitute for the signed field-level source.", 42, 105, 510, size=8, leading=11, color=MUTED)
    _gold_table(case, "Screening, randomization, and current disposition", roster_headers, roster_rows)
    _facts(
        case,
        "roster",
        "Subject disposition roster",
        "table",
        [
            ("014003", "Subject 014-003 is randomized to Arm A and indexed as active with a W2 source correction.", 2),
            ("014004", "Subject 014-004 withdrew on 2026-04-24."),
            ("014007", "Subject 014-007 is randomized to Arm B and indexed with a pharmacy restriction.", 2),
            ("014009", "Subject 014-009 is indexed for visit-window review."),
            ("014011", "Subject 014-011 is indexed with an amended laboratory report."),
            ("014016", "Subject 014-016 is indexed for masking review."),
        ],
        budget=2,
    )

    # 3 - visit schedule, continued on page 10.
    c = case.new_page(
        "Visit chronology - enrollment through week 2",
        subtitle="Part 1 of 2 | Dates reflect source worksheets, not query-console normalization",
        section_code="VISIT LOG / PART 1",
    )
    visit_headers = ["Subject", "Visit", "Planned day", "Actual date/time", "Kit / device", "Worksheet state", "Continuation"]
    visit_rows = [
        ["014-002", "V1", "Day 1", "05 Apr 08:05", "K-204-118", "Complete", "W2 p10"],
        ["014-002", "W2", "Day 15", "19 Apr 08:12", "K-204-142", "Complete", "W4 p10"],
        ["014-003", "V1", "Day 1", "07 Apr 09:10", "K-204-121", "Complete", "W2 below"],
        ["014-003", "W2", "Day 15", "21 Apr 08:44", "K-204-146", "Partial; source correction", "DCF p16"],
        ["014-004", "V1", "Day 1", "10 Apr 10:20", "K-204-128", "Complete", "ET p10"],
        ["014-005", "V1", "Day 1", "12 Apr 09:32", "K-204-132", "Complete", "W2 p10"],
        ["014-007", "V1", "Day 1", "18 Apr 09:10", "K-204-153", "Pharmacy source required", "Form p12"],
        ["014-008", "V1", "Day 1", "20 Apr 09:15", "K-204-158", "Lab receipt pending", "Lab p15"],
        ["014-009", "V1", "Day 1", "19 Apr 10:04", "K-204-160", "Complete", "W2 p10"],
        ["014-011", "V1", "Day 1", "26 Apr 08:52", "K-204-171", "Repeat chemistry ordered", "Lab p15"],
        ["014-012", "V1", "Day 1", "28 Apr 11:06", "K-204-176", "Waiver W-14 filed", "Consent p8"],
        ["014-014", "V1", "Day 1", "01 May 09:40", "K-204-184", "ePRO setup incomplete", "Training p18"],
        ["014-016", "V1", "Day 1", "04 May 07:58", "K-204-190", "Masking review", "Dose p21"],
    ]
    draw_table(c, 32, 675, [55, 45, 58, 88, 80, 147, 73], [visit_headers, *visit_rows], font_size=5.9, zebra=True)
    draw_badge(c, "Continued on page 10", 42, 126, AMBER)
    draw_paragraph(c, "The continuation carries later visits and termination records. Do not infer a later visit from an enrollment row when the continuation is absent.", 42, 96, 500, size=8, leading=11, color=MUTED)
    _gold_table(case, "Visit chronology - enrollment through week 2", visit_headers, visit_rows)
    _facts(
        case,
        "visits-a",
        "Visit chronology part 1",
        "table",
        [
            ("014003-w2", "Subject 014-003 had a partial W2 visit on 2026-04-21 at 08:44 and its source correction continues to DCF page 16.", 2),
            ("014007-v1", "Subject 014-007 V1 on 2026-04-18 points to the pharmacy form on page 12.", 2),
            ("014009-v1", "Subject 014-009 V1 occurred on 2026-04-19 at 10:04."),
            ("014011-v1", "Subject 014-011 V1 on 2026-04-26 ordered repeat chemistry."),
            ("continuation", "The visit log explicitly continues on page 10."),
        ],
        budget=2,
    )

    # 4 - accession log.
    c = case.new_page(
        "Central laboratory accession and custody register",
        subtitle="Interface snapshot plus courier custody; amended analytical values appear later",
        section_code="LAB / ACCESSION",
    )
    lab_headers = ["Shipment", "Subject", "Specimen", "Collected", "Courier pickup", "Lab receipt", "Accession state"]
    lab_rows = [
        ["SH-204-41", "014-002", "PK-W2", "19 Apr 08:12", "19 Apr 16:00", "20 Apr 09:02", "Accepted"],
        ["SH-204-45", "014-003", "PK-W2", "21 Apr 08:44", "21 Apr 17:35", "23 Apr 16:40", "Accepted; receipt note"],
        ["SH-204-46", "014-008", "Chemistry", "20 Apr 09:15", "20 Apr 15:55", "Not posted", "Interface pending"],
        ["SH-204-47", "014-009", "PK-W2", "06 May 09:04", "06 May 10:15", "06 May 11:20", "Accepted"],
        ["SH-204-48", "014-011", "Chemistry", "26 Apr 08:52", "26 Apr 16:20", "27 Apr 10:05", "Repeat requested"],
        ["SH-204-52", "014-011", "Chemistry repeat", "08 May 07:46", "08 May 12:05", "08 May 15:31", "Amended report p15"],
        ["SH-204-49", "014-016", "Glucose", "04 May 07:58", "04 May 16:40", "05 May 09:44", "Safety call linked"],
        ["SH-204-50", "014-014", "PK-V1", "01 May 09:40", "01 May 15:20", "02 May 08:55", "Accepted"],
        ["SH-204-53", "014-007", "Potassium repeat", "02 May 09:22", "02 May 14:10", "03 May 08:40", "Final"],
        ["SH-204-54", "014-004", "ET chemistry", "24 Apr 10:11", "24 Apr 15:48", "25 Apr 09:26", "Accepted"],
    ]
    draw_table(c, 32, 675, [71, 55, 78, 82, 88, 86, 111], [lab_headers, *lab_rows], font_size=5.85, zebra=True)
    draw_paragraph(c, "A receipt timestamp proves custody, not the analytical result. For SH-204-45 use the signed receipt on page 20 for the corrected seal and temperature fields; for SH-204-52 use the amended report image on page 15.", 42, 128, 510, size=8, leading=11, color=MUTED)
    _gold_table(
        case,
        "Central laboratory accession and custody register",
        lab_headers,
        lab_rows,
        "A receipt timestamp proves custody, not the analytical result. SH-204-45's signed receipt on page 20 controls corrected seal and temperature fields; SH-204-52's amended report on page 15 controls amended analytical values.",
    )
    _facts(
        case,
        "accession",
        "Central laboratory accession register",
        "table",
        [
            ("sh20445", "Shipment SH-204-45 belongs to subject 014-003, was collected 2026-04-21 at 08:44, and was received 2026-04-23 at 16:40.", 2),
            ("sh20446", "Shipment SH-204-46 for subject 014-008 has no posted lab receipt and is interface pending."),
            ("sh20452", "Shipment SH-204-52 is the 2026-05-08 repeat chemistry for subject 014-011 and points to the amended report on page 15.", 2),
            ("sh20453", "Shipment SH-204-53 is the final potassium repeat for subject 014-007."),
            ("custody-limit", "A receipt timestamp proves custody, not an analytical result."),
        ],
        budget=2,
    )

    # 5 - intended full-page scan: pharmacy receipt ledger.
    c = case.new_page(
        "Pharmacy receipt ledger - shipment PS-778",
        subtitle="Scanned controlled source | Original corrections retained",
        section_code="PHARMACY / RECEIPT",
    )
    scan = _scan_document(
        "INVESTIGATIONAL PRODUCT RECEIPT LEDGER",
        "Protocol HTX-204 | Site 014 | Shipment PS-778 | Received 06 Apr 2026 14:26",
        [
            (
                "Courier and packaging",
                [
                    "Courier airway bill 77190433; outer carton dry and undamaged. Logger TL-884 stopped at 14:29 by pharmacist R. Patel.",
                    "Carton C-19 contained kits K-204-118 through K-204-152. Carton C-22 contained kits K-204-153 through K-204-177.",
                ],
            ),
            (
                "Receipt lines",
                [
                    "K-204-118 lot H24A expiry 31 Dec 2026 quantity 30 tablets; shelf RX-2/A1; count witnessed by JD.",
                    "K-204-121 lot H24A expiry 31 Dec 2026 quantity 30 tablets; shelf RX-2/A1; count witnessed by JD.",
                    "K-204-142 lot H24B expiry 31 Jan 2027 quantity 30 tablets; shelf RX-2/A2; count witnessed by JD.",
                    "K-204-146 lot H24B expiry 31 Jan 2027 quantity 30 tablets; shelf RX-2/A2; count witnessed by JD.",
                    "K-204-153 lot H24C expiry 31 Jan 2027 quantity 30 tablets; locator corrected below; count witnessed by MK.",
                    "K-204-158 lot H24C expiry 31 Jan 2027 quantity 30 tablets; shelf RX-2/B1; count witnessed by MK.",
                    "K-204-171 lot H24D expiry 28 Feb 2027 quantity 30 tablets; shelf RX-2/B2; count witnessed by MK.",
                    "K-204-176 lot H24D expiry 28 Feb 2027 quantity 30 tablets; shelf RX-2/B2; count witnessed by MK.",
                ],
            ),
            (
                "Receipt note",
                [
                    "Logger review covered 05 Apr 22:11 through 06 Apr 14:26. No excursion appears in the delivery trace. This receipt does not determine later storage disposition.",
                ],
            ),
        ],
        controls=[
            ("C-19 tamper seal intact", "checked"),
            ("C-22 tamper seal intact", "crossed"),
            ("C-22 seal discrepancy photographed", "checked"),
            ("Shipment placed in released stock", "unchecked"),
        ],
        corrections=[
            ("K-204-153 locator RX-2/A2", "K-204-153 locator RX-2/B1", "RP 06 Apr 14:41"),
            ("C-22 seal intact - yes", "C-22 outer seal split on arrival; inner pouch intact", "RP/JD"),
        ],
        signatures=[
            "Received and counted by R. Patel (RP), pharmacist, 06 Apr 2026 14:46.",
            "Independent witness J. Das (JD), 06 Apr 2026 14:51. Coordinator notification M. Kapoor, 06 Apr 15:03.",
        ],
        seed=1705,
        form_code="PH-REC-04 / REV 3",
    )
    _place_full_scan(c, scan)
    _gold_scan(
        case,
        "Pharmacy receipt ledger",
        "Shipment PS-778 was received 2026-04-06 at 14:26. Carton C-19 held kits K-204-118 through K-204-152; carton C-22 held K-204-153 through K-204-177. K-204-153 is lot H24C, expiry 2027-01-31, quantity 30, with its original RX-2/A2 locator struck and corrected to RX-2/B1 by RP at 14:41. C-19 tamper seal intact is checked. C-22 tamper seal intact is crossed out, while C-22 seal discrepancy photographed is checked. Shipment placed in released stock is unchecked. The correction states that C-22's outer seal was split but its inner pouch was intact. R. Patel received the shipment; J. Das witnessed the count.",
    )
    _facts(
        case,
        "receipt",
        "Scanned pharmacy receipt ledger",
        "form",
        [
            ("shipment", "Pharmacy shipment PS-778 was received on 2026-04-06 at 14:26."),
            ("kit", "K-204-153 is lot H24C, expires 2027-01-31, and had receipt quantity 30."),
            ("locator", "K-204-153's RX-2/A2 locator is struck and corrected to RX-2/B1 by RP at 14:41.", 2),
            ("c19", "C-19 tamper seal intact is checked."),
            ("c22-intact", "C-22 tamper seal intact is crossed.", 2, ("C-22 tamper seal intact", "crossed")),
            ("c22-photo", "C-22 seal discrepancy photographed is checked.", 2, ("C-22 seal discrepancy photographed", "checked")),
            ("release", "Shipment placed in released stock is unchecked.", 2),
            ("correction", "The corrected C-22 note says the outer seal was split while the inner pouch was intact."),
        ],
        budget=2,
        primary_axis="low_quality_scan",
        secondary_axes=("form_state",),
    )

    # 6 - safety listing.
    c = case.new_page(
        "Adverse-event line listing and follow-up state",
        subtitle="Safety database export 06 May 18:00 | Follow-up evidence may post after the cut",
        section_code="SAFETY / AE LOG",
    )
    ae_headers = ["AE", "Subject", "Onset", "Term", "Grade", "Relatedness", "Action", "Status at cut"]
    ae_rows = [
        ["AE-014-01", "014-004", "11 Apr", "Dizziness", "2", "Related", "Drug withdrawn", "Resolved 27 Apr"],
        ["AE-014-02", "014-002", "20 Apr", "Nausea", "1", "Possible", "Dose reduced", "Resolved 03 May"],
        ["AE-014-03", "014-007", "18 Apr", "Potassium increased", "2", "Unrelated", "Repeat test", "Resolved 03 May"],
        ["AE-014-04", "014-011", "26 Apr", "Creatinine increased", "1", "Possible", "Repeat ordered", "Ongoing"],
        ["AE-014-05", "014-016", "04 May", "Hypoglycemia", "2", "Related", "Safety call", "Ongoing"],
        ["AE-014-06", "014-003", "22 Apr", "Headache", "1", "Unlikely", "None", "Resolved 22 Apr"],
        ["AE-014-07", "014-009", "02 May", "Injection-site pain", "1", "Related", "None", "Resolved 04 May"],
        ["AE-014-08", "014-014", "03 May", "Missed diary entries", "N/A", "Device issue", "Retraining", "Open"],
    ]
    draw_table(c, 28, 675, [69, 54, 55, 109, 40, 75, 92, 90], [ae_headers, *ae_rows], font_size=5.75, zebra=True)
    follow_headers = ["Record", "Required evidence", "Owner", "Due", "Linked page"]
    follow_rows = [
        ["AE-014-04", "Repeat chemistry report", "MK", "09 May", "p15"],
        ["AE-014-05", "Dose worksheet and masking review", "NR", "10 May", "p21 / p28"],
        ["AE-014-08", "Training competency source", "MK", "08 May", "p18"],
    ]
    draw_label(c, "Follow-up routing", 42, 326)
    draw_table(c, 42, 311, [92, 196, 55, 72, 95], [follow_headers, *follow_rows], font_size=6.7, zebra=True)
    _gold_table(case, "Adverse-event line listing", ae_headers, ae_rows, markdown_table(follow_headers, follow_rows))
    _facts(
        case,
        "ae",
        "Adverse-event and follow-up listing",
        "table",
        [
            ("ae01", "AE-014-01 is related grade 2 dizziness for subject 014-004; drug was withdrawn and the event resolved on 2026-04-27."),
            ("ae03", "AE-014-03 for subject 014-007 is potassium increased, classified unrelated, with repeat testing and resolution on 2026-05-03."),
            ("ae04", "AE-014-04 for subject 014-011 is possible-related creatinine increased and was ongoing at the cut.", 2),
            ("ae05", "AE-014-05 for subject 014-016 is related grade 2 hypoglycemia and was ongoing at the cut.", 2),
            ("ae08", "AE-014-08 is a device issue for subject 014-014 and routes to training evidence on page 18."),
        ],
        budget=2,
    )

    # 7 - provisional query export.
    c = case.new_page(
        "Data-query console export - pre-monitor state",
        subtitle="Snapshot 06 May 18:04 | Provisional responses are not signed source",
        section_code="QUERY LOG / SNAPSHOT",
    )
    query_headers = ["Query", "Subject", "Opened", "Field / issue", "Console state", "Provisional response", "Next source"]
    query_rows = [
        ["Q-74", "014-004", "25 Apr", "AE stop date", "Answered", "Site entered 24 Apr", "Safety review"],
        ["Q-77", "014-003", "22 Apr", "W2 ECG performed", "Open", "Draft says Yes; tracing requested", "DCF p16"],
        ["Q-81", "014-007", "19 Apr", "Excursion dosing", "Answered", "Pharmacy form pending", "Form p12"],
        ["Q-84", "014-008", "23 Apr", "Central lab receipt", "Open", "Courier ticket filed", "Receipt interface"],
        ["Q-86", "014-009", "07 May", "W2 visit window", "Open", "Calendar note drafted", "Adjudication p27"],
        ["Q-88", "014-011", "28 Apr", "Repeat chemistry", "Open", "Specimen booked", "Report p15"],
        ["Q-91", "014-014", "04 May", "ePRO activation", "Answered", "Retraining scheduled", "Roster p18"],
        ["Q-93", "014-016", "05 May", "Masking note", "Open", "PI review requested", "Action p28"],
    ]
    draw_table(c, 26, 675, [57, 52, 54, 118, 67, 169, 69], [query_headers, *query_rows], font_size=5.7, zebra=True)
    draw_paragraph(c, "Console responses describe what had been typed by the snapshot time. A later signed clarification can retain, correct, or reject that response. When states conflict, retain both timestamps and bind the final field to the controlling source.", 42, 260, 510, size=8.4, leading=11.5, color=MUTED)
    draw_badge(c, "Snapshot - not final source", 42, 185, AMBER)
    _gold_table(case, "Data-query console export - pre-monitor state", query_headers, query_rows, "At the 06 May 2026 snapshot, console responses are provisional and are not signed source.")
    _facts(
        case,
        "queries",
        "Provisional query-console snapshot",
        "table",
        [
            ("q77", "At the 2026-05-06 snapshot, Q-77 is open and its provisional response says Yes with tracing requested; it points to DCF page 16.", 2),
            ("q81", "Q-81 is answered in the console but explicitly points to the pending pharmacy form on page 12."),
            ("q86", "Q-86 is open for subject 014-009's W2 visit window and continues to page 27.", 2),
            ("q88", "Q-88 is open for subject 014-011 repeat chemistry and points to page 15."),
            ("q93", "Q-93 is open for subject 014-016's masking note and continues to page 28."),
            ("provisional", "The page labels console responses as provisional and not signed source.", 2),
        ],
        budget=2,
    )

    # 8 - intended full-page scan: consent and delegation source.
    c = case.new_page(
        "Delegation and consent verification worksheet",
        subtitle="Scanned monitoring worksheet | Signatures and applicability states",
        section_code="REGULATORY / CONSENT",
    )
    scan = _scan_document(
        "DELEGATION AND INFORMED CONSENT VERIFICATION",
        "HTX-204 | Site 014 | Reviewed by LS on 08 May 2026 10:18",
        [
            (
                "Delegation log review",
                [
                    "Dr. Neha Rao: principal investigator; delegated consent, eligibility, dose decisions, AE causality, and deviation review from 18 Mar 2026.",
                    "Maya Kapoor: lead coordinator; delegated consent discussion, visit procedures, source entry, ePRO training, and query response preparation from 21 Mar 2026.",
                    "Ravi Patel: unblinded pharmacist; delegated receipt, temperature review, accountability, quarantine, and destruction from 22 Mar 2026.",
                    "Jaya Das: pharmacy witness; delegated independent count and seal verification only. No delegation for disposition decisions.",
                ],
            ),
            (
                "Subject 014-012 consent trail",
                [
                    "Main ICF version 6.0 dated 18 Mar 2026 signed by subject and Maya Kapoor on 28 Apr 2026 at 10:14, before screening procedures at 10:42.",
                    "Optional genetic biobank page signed at 10:17. The subject selected decline; no biobank sample identifier was assigned.",
                    "Re-consent is not required at this review because version 6.0 is current. Waiver W-14 addresses a translated diary, not the main consent process.",
                ],
            ),
            (
                "Monitor annotation",
                [
                    "The applicability marks below are source states. A gray barred box means the workflow was disabled, not that the activity was missing or refused.",
                ],
            ),
        ],
        controls=[
            ("Main ICF signed before procedures", "checked"),
            ("Optional genetic biobank accepted", "unchecked"),
            ("Optional genetic biobank declined", "checked"),
            ("Pregnancy testing workflow", "disabled"),
            ("Translated main ICF required", "unchecked"),
            ("Delegation exception raised", "unchecked"),
        ],
        signatures=[
            "Monitor verification: Lina Sen (LS), 08 May 2026 10:18.",
            "PI acknowledgment: Neha Rao (NR), 08 May 2026 12:06. No correction to consent timestamps requested.",
        ],
        seed=1708,
        form_code="REG-MON-11 / REV 2",
    )
    _place_full_scan(c, scan)
    _gold_scan(
        case,
        "Delegation and consent verification worksheet",
        "Dr. Neha Rao is delegated consent, eligibility, dose decisions, AE causality, and deviation review. Maya Kapoor is delegated consent discussion, visit procedures, source entry, ePRO training, and query-response preparation. Ravi Patel is delegated pharmacy receipt, temperature review, accountability, quarantine, and destruction. Jaya Das is delegated independent count and seal verification only, with no delegation for disposition decisions. Subject 014-012 signed main ICF v6.0 on 2026-04-28 at 10:14 before procedures at 10:42. Main ICF signed before procedures is checked. Optional genetic biobank accepted is unchecked. Optional genetic biobank declined is checked. Pregnancy testing workflow is disabled. Translated main ICF required and delegation exception raised are unchecked.",
    )
    _facts(
        case,
        "consent",
        "Scanned delegation and consent worksheet",
        "form",
        [
            ("timing", "Subject 014-012 signed main ICF v6.0 at 10:14 before screening procedures at 10:42 on 2026-04-28.", 2),
            ("biobank-accepted", "Optional genetic biobank accepted is unchecked.", 2, ("Optional genetic biobank accepted", "unchecked")),
            ("biobank-declined", "Optional genetic biobank declined is checked.", 2, ("Optional genetic biobank declined", "checked")),
            ("pregnancy", "Pregnancy testing workflow is disabled rather than missing.", 1, ("Pregnancy testing workflow", "disabled")),
            ("translation", "Translated main ICF required is unchecked."),
            (
                "pharmacist",
                "Ravi Patel is delegated pharmacy receipt, temperature review, accountability, quarantine, and destruction; Jaya Das has no delegation for disposition decisions.",
                1,
                {
                    "evidence": [
                        "Ravi Patel",
                        "delegated pharmacy receipt",
                        "quarantine",
                        "destruction",
                        "Jaya Das",
                        "no delegation for disposition decisions",
                    ]
                },
            ),
            ("exception", "Delegation exception raised is unchecked."),
        ],
        budget=2,
    )

    # 9 - explicit source precedence rules without disclosing later outcomes.
    c = case.new_page(
        "Source hierarchy and correction handling",
        subtitle="Monitoring work instruction WI-CLIN-17 | Applied field by field",
        section_code="WORK INSTRUCTION",
    )
    hierarchy_headers = ["Priority", "Source class", "Controls when", "Does not erase"]
    hierarchy_rows = [
        ["1", "Signed source correction / signed DCF", "Identifies field, date, author, reason, and final entry", "Original visible entry"],
        ["2", "Signed contemporaneous source form", "No later signed correction exists for that field", "Separate systems and later events"],
        ["3", "Verified external final report", "Report identity and amendment state are established", "Earlier report version"],
        ["4", "System audit trail", "Timestamped state is reported as of its snapshot", "Later signed source"],
        ["5", "Monitoring note", "Describes review, lineage, or unresolved evidence", "Underlying clinical source"],
        ["6", "Draft email or working tracker", "Reported only as draft context", "Any signed or verified record"],
    ]
    draw_table(c, 42, 665, [52, 150, 228, 90], [hierarchy_headers, *hierarchy_rows], font_size=6.65, zebra=True)
    draw_label(c, "Application rules", 42, 405)
    rules = [
        "Report the original and corrected values when both are visible; label which value controls and preserve authorship and time.",
        "A checkbox state carries meaning only with its exact label. Checked, unchecked, crossed, and disabled are distinct states.",
        "A query-console snapshot remains valid evidence of its own timestamp even when a later signed clarification changes the field value.",
        "A laboratory amendment supersedes the analytical value it identifies; custody timestamps remain independent facts.",
        "An action due date in a signed CAPA controls over a working-tracker date, while the draft date remains part of the audit trail.",
        "When no source controls a field, retain the unresolved state instead of choosing the most plausible value.",
    ]
    y = 378
    for index, rule in enumerate(rules, start=1):
        draw_badge(c, str(index), 42, y + 2, BLUE)
        y = draw_paragraph(c, rule, 72, y, 480, size=8.1, leading=11.2, color=INK) - 13
    case.add_gold(
        "Page 09 - Source hierarchy and correction handling",
        markdown_table(hierarchy_headers, hierarchy_rows) + "\n\n" + "\n".join(f"{i}. {rule}" for i, rule in enumerate(rules, start=1)),
    )
    _facts(
        case,
        "precedence",
        "Source hierarchy and correction rules",
        "text",
        [
            ("signed", "A signed source correction or signed DCF has the highest field-level priority when it identifies the field, author, date, reason, and final entry.", 2),
            ("original", "A correction does not erase the original visible entry."),
            ("checkbox", "Checked, unchecked, crossed, and disabled states must remain distinct and bound to their exact labels.", 2),
            ("snapshot", "A system snapshot remains evidence of its own timestamp even if a later signed clarification changes the field value."),
            ("lab", "A laboratory amendment supersedes the analytical value it identifies but not independent custody timestamps.", 2),
            ("capa", "A signed CAPA due date controls over a working-tracker due date while both remain in the audit trail.", 2),
        ],
        budget=2,
    )

    # 10 - visit chronology continuation.
    c = case.new_page(
        "Visit chronology - week 2 through termination",
        subtitle="Part 2 of 2 | Continuation of page 3",
        section_code="VISIT LOG / PART 2",
    )
    visit2_headers = ["Subject", "Visit", "Target / window", "Actual", "Elapsed from V1", "State", "Linked record"]
    visit2_rows = [
        ["014-002", "W4", "03 May +/-2 d", "03 May 08:20", "Day 29", "Complete", "Dose reduced / AE-02"],
        ["014-003", "W4", "05 May +/-2 d", "05 May 09:05", "Day 29", "Complete", "Q-77 still open"],
        ["014-004", "Early termination", "As needed", "24 Apr 10:11", "Day 15", "Withdrawn", "AE-014-01"],
        ["014-005", "W2", "26 Apr +/-2 d", "26 Apr 09:22", "Day 15", "Complete", "Diary complete"],
        ["014-005", "W4", "10 May +/-2 d", "Scheduled", "-", "Not yet due", "Calendar"],
        ["014-007", "W2", "02 May +/-2 d", "02 May 09:22", "Day 15", "Partial", "Repeat K final"],
        ["014-008", "W2", "04 May +/-2 d", "04 May 08:48", "Day 15", "Complete", "Receipt unresolved"],
        ["014-009", "W2", "03 May +/-2 d", "06 May 09:04", "Day 18", "Outside listed window", "Q-86 / p27"],
        ["014-011", "Unscheduled", "Repeat chemistry", "08 May 07:46", "Day 13", "Source obtained", "SH-204-52"],
        ["014-012", "W2", "12 May +/-2 d", "Scheduled", "-", "Not yet due", "Waiver W-14"],
        ["014-013", "Follow-up", "After missed contact", "05 May 17:20", "Day 7", "No contact", "FU-013"],
        ["014-014", "Unscheduled", "ePRO training", "08 May 13:30", "Day 8", "Source on p18", "Q-91"],
        ["014-016", "Safety call", "Within 24 h", "04 May 18:16", "Day 1", "Completed", "AE-014-05"],
    ]
    draw_table(c, 28, 675, [56, 79, 95, 85, 74, 93, 102], [visit2_headers, *visit2_rows], font_size=5.75, zebra=True)
    draw_paragraph(c, "For subject 014-009, the table records the operational window and actual attendance. The signed classification of that discrepancy appears on page 27; this log does not assign the deviation class.", 42, 112, 510, size=8.2, leading=11.2, color=MUTED)
    _gold_table(case, "Visit chronology - week 2 through termination", visit2_headers, visit2_rows, "This is part 2 of the visit log begun on page 3. Subject 014-009's signed discrepancy classification is deferred to page 27.")
    _facts(
        case,
        "visits-b",
        "Visit chronology continuation",
        "table",
        [
            ("continuation", "This page is explicitly part 2 of the visit log begun on page 3."),
            ("014003-w4", "Subject 014-003 completed W4 on 2026-05-05 while Q-77 remained open."),
            ("014007-w2", "Subject 014-007 had a partial W2 visit on 2026-05-02 and the repeat potassium was final."),
            ("014009", "Subject 014-009 attended W2 on 2026-05-06, day 18, outside the listed 2026-05-03 +/-2 day window.", 2),
            ("014011", "Subject 014-011 had an unscheduled repeat-chemistry visit on 2026-05-08 at 07:46 linked to SH-204-52."),
            ("classification", "The page defers subject 014-009's signed discrepancy classification to page 27."),
        ],
        budget=2,
    )

    # 11 - intended full-page scan: corrected ECG eCRF.
    c = case.new_page(
        "Subject 014-003 W2 electrocardiogram eCRF",
        subtitle="Scanned source correction | Original and corrected states visible",
        section_code="eCRF / ECG",
    )
    scan = _scan_document(
        "ELECTROCARDIOGRAM eCRF - WEEK 2",
        "Protocol HTX-204 | Site 014 | Subject 014-003 | Visit date 21 Apr 2026",
        [
            (
                "Visit context",
                [
                    "Visit worksheet started by coordinator Maya Kapoor at 08:44. Vital signs and blood collection were completed before 09:00.",
                    "ECG machine asset ECG-2 displayed service code E17. No tracing identifier was generated and no paper tracing is filed for this visit.",
                ],
            ),
            (
                "Field correction rationale",
                [
                    "The original performed entry was copied from the visit template before the coordinator confirmed the device failure. Review on 22 Apr found no tracing in source or device memory.",
                    "Correction made without erasure. The reason recorded is equipment unavailable; replacement unit was scheduled for delivery on 23 Apr.",
                    "Deviation DEV-014-03 was opened as major. Data query Q-77 was opened for reconciliation with the electronic field.",
                ],
            ),
            (
                "Audit trail",
                [
                    "Original entry by MK on 21 Apr 2026 at 09:02. Correction by MK on 22 Apr 2026 at 14:18. Monitor verification by LS on 08 May 2026 at 11:26.",
                ],
            ),
        ],
        controls=[
            ("ECG performed - Yes (original)", "crossed"),
            ("ECG performed - No (corrected)", "checked"),
            ("Tracing attached", "unchecked"),
            ("Equipment unavailable", "checked"),
            ("Subject refused", "unchecked"),
            ("PI deviation review completed", "unchecked"),
        ],
        corrections=[
            ("ECG performed: YES", "ECG performed: NO - no tracing acquired", "MK 22 Apr 14:18"),
        ],
        signatures=[
            "Coordinator correction certified by Maya Kapoor (MK), 22 Apr 2026 14:18.",
            "Monitor source verification Lina Sen (LS), 08 May 2026 11:26. PI deviation review remains unsigned on this form.",
        ],
        seed=1711,
        form_code="eCRF-ECG-W2 / AUDIT COPY",
    )
    _place_full_scan(c, scan)
    _gold_scan(
        case,
        "Corrected W2 ECG eCRF",
        "For subject 014-003 at W2 on 2026-04-21, ECG performed - Yes (original) is crossed out and ECG performed - No (corrected) is checked. Tracing attached is unchecked. Equipment unavailable is checked and subject refused is unchecked. The source says asset ECG-2 showed service code E17, no tracing identifier was generated, and no tracing is filed. MK made the original entry at 09:02 and corrected it on 2026-04-22 at 14:18. DEV-014-03 is major and Q-77 was opened. LS verified the source on 2026-05-08 at 11:26. PI deviation review completed is unchecked.",
    )
    _facts(
        case,
        "ecg",
        "Corrected ECG eCRF scan",
        "form",
        [
            ("identity", "The eCRF is for subject 014-003 at W2 on 2026-04-21."),
            ("original", "ECG performed - Yes (original) is crossed.", 2, ("ECG performed - Yes (original)", "crossed")),
            ("final", "ECG performed - No (corrected) is checked.", 2, ("ECG performed - No (corrected)", "checked")),
            ("final-value", "The final ECG performed field value is No.", 2, {"evidence": ["final", "ECG performed", "No"]}),
            ("tracing-state", "Tracing attached is unchecked.", 2, ("Tracing attached", "unchecked")),
            ("tracing-id", "No tracing identifier was generated.", 2),
            ("reason-equipment", "Equipment unavailable is checked.", 1, ("Equipment unavailable", "checked")),
            ("reason-refused", "Subject refused is unchecked.", 1, ("Subject refused", "unchecked")),
            ("audit", "MK corrected the field on 2026-04-22 at 14:18 and LS verified it on 2026-05-08 at 11:26."),
            ("deviation", "DEV-014-03 is major and Q-77 was opened."),
            ("pi", "PI deviation review completed is unchecked."),
        ],
        budget=2,
    )

    # 12 - intended full-page scan: temperature excursion source.
    c = case.new_page(
        "Investigational-product temperature excursion",
        subtitle="Scanned pharmacy source | Signed disposition controls over working notes",
        section_code="PHARMACY / DEV-014-07",
    )
    scan = _scan_document(
        "TEMPERATURE EXCURSION AND KIT DISPOSITION",
        "HTX-204 | Site 014 | Refrigerator RX-2 | Kit K-204-153 | 18 Apr 2026",
        [
            (
                "Logger sequence",
                [
                    "09:10 - 8.4 C; audible alarm acknowledged by RP. Kit remained in RX-2 while a quarantine bag was prepared.",
                    "10:10 - 9.1 C; K-204-153 placed in red quarantine bag QG-19 and segregated on shelf Q1.",
                    "11:10 - 8.8 C; unblinded pharmacist notified sponsor supply contact and retained the kit.",
                    "12:10 - 7.8 C; chamber returned within nominal range but product quarantine remained active.",
                    "13:05 - 5.2 C; second in-range reading. 13:40 - 4.7 C; stable after service reset.",
                ],
            ),
            (
                "Product and accountability context",
                [
                    "Kit K-204-153 is lot H24C, expiry 31 Jan 2027. Subject assignment 014-007 had been entered in the randomization system, but the kit had not left pharmacy custody.",
                    "Pharmacy physical count after segregation was 30 tablets. Sponsor stability response SR-204-19 was received at 13:52 and filed behind this form.",
                ],
            ),
            (
                "Disposition authorization",
                [
                    "Ravi Patel is the authorized unblinded pharmacist. Jaya Das witnessed the segregation and count but did not select the product disposition.",
                    "The four states below are mutually exclusive for final disposition. A gray barred state was disabled by the sponsor response.",
                ],
            ),
        ],
        controls=[
            ("Return to usable stock", "crossed"),
            ("Do not dose", "checked"),
            ("Destroy at site", "unchecked"),
            ("Release pending later review", "disabled"),
            ("Kit dispensed to subject", "unchecked"),
            ("Quarantine label QG-19 attached", "checked"),
        ],
        corrections=[
            ("Return kit to usable stock after two in-range readings", "Do not dose; retain quarantined pending sponsor return instruction", "RP 18 Apr 14:02"),
        ],
        signatures=[
            "Disposition selected and signed by Ravi Patel (RP), 18 Apr 2026 14:02, after sponsor response SR-204-19.",
            "Segregation and count witnessed by Jaya Das (JD), 18 Apr 2026 14:06. Monitor verification LS, 08 May 2026 14:20.",
        ],
        seed=1712,
        form_code="IP-TEMP-09 / REV 5",
    )
    _place_full_scan(c, scan)
    _gold_scan(
        case,
        "Temperature excursion and disposition",
        "For kit K-204-153 assigned to subject 014-007 in refrigerator RX-2, the readings on 2026-04-18 were 8.4 C at 09:10, 9.1 C at 10:10, 8.8 C at 11:10, 7.8 C at 12:10, 5.2 C at 13:05, and the final recorded reading was 4.7 C at 13:40. At 10:10 the kit entered quarantine bag QG-19. Return to usable stock is crossed. Do not dose is checked. Destroy at site and kit dispensed to subject are unchecked. Release pending later review is disabled. Quarantine label QG-19 attached is checked. Physical count was 30 tablets. RP signed the corrected disposition on 2026-04-18 at 14:02; JD witnessed segregation and count at 14:06.",
    )
    _facts(
        case,
        "excursion",
        "Temperature excursion and disposition scan",
        "form",
        [
            ("identity", "The form concerns kit K-204-153 assigned to subject 014-007 in refrigerator RX-2."),
            ("peak", "The peak recorded reading is 9.1 C at 10:10 on 2026-04-18.", 2),
            ("final-reading", "The final recorded reading is 4.7 C at 13:40."),
            ("return", "Return to usable stock is crossed.", 1, ("Return to usable stock", "crossed")),
            ("do-not-dose", "Do not dose is checked and controls the kit disposition.", 2, ("Do not dose", "checked")),
            ("destroy", "Destroy at site is unchecked.", 1, ("Destroy at site", "unchecked")),
            ("dispensed", "Kit dispensed to subject is unchecked.", 1, ("Kit dispensed to subject", "unchecked")),
            ("release", "Release pending later review is disabled.", 2, ("Release pending later review", "disabled")),
            ("quarantine", "Quarantine label QG-19 attached is checked.", 1, ("Quarantine label QG-19 attached", "checked")),
            ("quarantine-count", "Physical count is 30."),
            ("authorization", "RP signed the corrected disposition at 14:02 and JD witnessed segregation and count at 14:06."),
        ],
        budget=2,
    )

    # 13 - deviation chronology.
    c = case.new_page(
        "Protocol deviation chronology and evidence routing",
        subtitle="Chronological register | Classification follows signed review where present",
        section_code="DEVIATION LOG",
    )
    dev_headers = ["Deviation", "Subject", "Event date", "Detected", "Issue", "Provisional class", "Controlling source"]
    dev_rows = [
        ["DEV-014-02", "014-002", "19 Apr", "20 Apr", "Diary page returned late", "Minor", "Resolved note"],
        ["DEV-014-03", "014-003", "21 Apr", "22 Apr", "W2 ECG source discrepancy", "Major", "eCRF p11 / DCF p16"],
        ["DEV-014-04", "014-004", "24 Apr", "25 Apr", "ET lab outside processing target", "Minor", "Lab receipt"],
        ["DEV-014-07", "014-007", "18 Apr", "18 Apr", "IP storage excursion", "Major", "Pharmacy form p12"],
        ["DEV-014-08", "014-009", "06 May", "07 May", "W2 attendance outside listed window", "Pending signed class", "Adjudication p27"],
        ["DEV-014-09", "014-011", "27 Apr", "28 Apr", "Repeat chemistry evidence absent", "Major", "Amended report p15"],
        ["DEV-014-10", "014-014", "01 May", "04 May", "ePRO activation incomplete", "Minor", "Training p18"],
        ["DEV-014-11", "014-016", "04 May", "05 May", "Unblinded detail in site note", "Major", "PI review p22 / p28"],
    ]
    draw_table(c, 28, 675, [78, 55, 59, 58, 142, 103, 89], [dev_headers, *dev_rows], font_size=5.75, zebra=True)
    draw_label(c, "Chronology rule", 42, 340)
    draw_paragraph(c, "Event date, detection date, and signed classification are separate fields. DEV-014-08 remains pending here because page 27 carries the signed classification. DEV-014-03 and DEV-014-07 retain their original source corrections even after downstream review.", 42, 318, 510, size=8.3, leading=11.4)
    draw_paragraph(c, "The register links evidence without copying the checkbox or corrected field states from those source forms. Review the referenced page for the exact marked state.", 42, 238, 510, size=8.3, leading=11.4, color=MUTED)
    _gold_table(
        case,
        "Protocol deviation chronology",
        dev_headers,
        dev_rows,
        "Event date, detection date, and signed classification are separate fields. The register links evidence but does not replace exact marked states on the referenced source forms.",
    )
    _facts(
        case,
        "deviations",
        "Protocol deviation chronology",
        "table",
        [
            ("dev03", "DEV-014-03 concerns subject 014-003's 2026-04-21 W2 ECG discrepancy and routes to pages 11 and 16.", 2),
            ("dev07", "DEV-014-07 concerns subject 014-007's 2026-04-18 IP storage excursion and routes to page 12.", 2),
            ("dev08", "DEV-014-08 for subject 014-009 has a pending signed class here and routes to page 27.", 2),
            ("dev09", "DEV-014-09 concerns absent repeat chemistry evidence for subject 014-011 and routes to page 15."),
            ("dev11", "DEV-014-11 concerns unblinded detail in subject 014-016's site note and routes to pages 22 and 28."),
            ("dates", "The page treats event date, detection date, and signed classification as separate fields."),
        ],
        budget=2,
    )

    # 14 - pharmacy inventory reconciliation.  It links to, but does not repeat,
    # the visually encoded disposition on page 12.
    c = case.new_page(
        "Investigational-product inventory reconciliation",
        subtitle="Physical count 08 May 14:35 | Status labels defer to signed disposition forms",
        section_code="PHARMACY / COUNT",
    )
    ip_headers = ["Kit", "Subject", "Receipt qty", "Dispensed qty", "Returned qty", "Physical balance", "Inventory locator / status"]
    ip_rows = [
        ["K-204-118", "014-002", "30", "30", "4", "4", "RX-2/A1 / reconciled"],
        ["K-204-142", "014-002", "30", "30", "6", "6", "RX-2/A2 / reconciled"],
        ["K-204-166", "014-002", "15", "15", "2", "2", "RX-2/B2 / dose-reduction return"],
        ["K-204-121", "014-003", "30", "30", "5", "5", "RX-2/A1 / reconciled"],
        ["K-204-146", "014-003", "30", "30", "Not returned", "0", "Subject return outstanding"],
        ["K-204-153", "014-007", "30", "See source", "N/A", "30", "Q1 / signed form p12 controls"],
        ["K-204-158", "014-008", "30", "30", "Pending", "0", "Subject custody"],
        ["K-204-160", "014-009", "30", "30", "3", "3", "RX-2/B1 / window query"],
        ["K-204-171", "014-011", "30", "30", "Pending", "0", "Subject custody / lab follow-up"],
        ["K-204-176", "014-012", "30", "30", "Pending", "0", "Subject custody"],
        ["K-204-184", "014-014", "30", "30", "0", "0", "Subject custody / ePRO"],
        ["K-204-190", "014-016", "30", "30", "2", "2", "RX-2/B2 / masking review"],
    ]
    draw_table(c, 26, 675, [74, 51, 61, 69, 69, 78, 171], [ip_headers, *ip_rows], font_size=5.7, zebra=True)
    draw_paragraph(c, "For K-204-153, the count sheet deliberately records 'See source' for dispensed quantity. The signed marked state on page 12, not this reconciliation row, determines whether dosing occurred and which disposition controls.", 42, 160, 510, size=8.2, leading=11.3, color=MUTED)
    _gold_table(case, "Investigational-product inventory reconciliation", ip_headers, ip_rows)
    _facts(
        case,
        "inventory",
        "Investigational-product reconciliation",
        "table",
        [
            ("k146", "Kit K-204-146 for subject 014-003 has a subject return outstanding and physical site balance 0.", 2),
            ("k153-count", "Kit K-204-153 has receipt quantity 30, physical balance 30, and locator Q1."),
            ("k153-source", "The K-204-153 row defers dispensed quantity and status to the signed form on page 12 rather than restating them.", 2),
            ("k160", "Kit K-204-160 for subject 014-009 has returned quantity and physical balance 3."),
            ("k190", "Kit K-204-190 for subject 014-016 has returned quantity and physical balance 2 and remains linked to masking review."),
        ],
        budget=2,
    )

    # 15 - mixed: amended laboratory fax image plus native custody table.
    c = case.new_page(
        "Amended laboratory report and custody continuation",
        subtitle="Mixed source: verified report image above, native custody reconciliation below",
        section_code="LAB / AMENDMENT",
    )
    lab_scan = _scan_document(
        "CENTRAL LABORATORY - AMENDED CHEMISTRY REPORT",
        "Accession AC-77152 | Subject 014-011 | Specimen SH-204-52 | Final amendment 09 May 2026 07:18",
        [
            (
                "Analytical result",
                [
                    "Creatinine: 1.47 mg/dL; flag H; reference interval 0.60-1.30 mg/dL. Collected 08 May 2026 07:46; received 08 May 15:31.",
                    "eGFR calculated result: 54 mL/min/1.73 m2; flag L; interpretive threshold greater than or equal to 60.",
                ],
            ),
            (
                "Amendment reason",
                [
                    "The preliminary creatinine transcription was corrected after instrument-interface reconciliation. Analytical run and specimen identity were unchanged.",
                ],
            ),
        ],
        corrections=[("Preliminary creatinine 1.74 mg/dL", "Final amended creatinine 1.47 mg/dL", "CL 09 May 07:18")],
        signatures=["Electronically verified by C. Liu, laboratory director, 09 May 2026 07:18. Report status FINAL AMENDED."],
        seed=1715,
        width=1900,
        height=970,
        form_code="NCL-CHM / FINAL AMENDED",
    )
    _place_mixed_scan(c, lab_scan, y=398, height=275)
    custody_headers = ["Checkpoint", "Time", "Actor / system", "Recorded state"]
    custody_rows = [
        ["Collection", "08 May 07:46", "MK", "Tube CH-551 sealed"],
        ["Courier handoff", "08 May 12:05", "Apex courier", "Seal CH-551 intact"],
        ["Lab receipt", "08 May 15:31", "NCL accession", "Accepted / AC-77152"],
        ["Preliminary interface", "08 May 21:42", "Lab portal", "Version 1 posted"],
        ["Amended interface", "09 May 07:22", "Lab portal", "Version 2 posted"],
        ["Site acknowledgement", "09 May 08:06", "NR", "Amendment reviewed"],
    ]
    draw_label(c, "Native custody continuation", 42, 365)
    draw_table(c, 42, 350, [115, 105, 130, 160], [custody_headers, *custody_rows], font_size=6.8, zebra=True)
    case.add_gold(
        "Page 15 - Amended laboratory report and custody continuation",
        "The scanned final amended report for accession AC-77152 / subject 014-011 / specimen SH-204-52 gives creatinine 1.47 mg/dL, flag H, reference 0.60-1.30; the preliminary 1.74 mg/dL is struck. eGFR is 54 mL/min/1.73 m2, flag L. The specimen was collected 2026-05-08 at 07:46 and received at 15:31. C. Liu verified the final amendment on 2026-05-09 at 07:18.\n\n" + markdown_table(custody_headers, custody_rows),
    )
    _facts(
        case,
        "lab-report",
        "Scanned amended laboratory report",
        "form",
        [
            ("identity", "The amended report is accession AC-77152 for subject 014-011 and specimen SH-204-52."),
            ("original", "Preliminary creatinine 1.74 mg/dL is struck."),
            ("final", "Final amended creatinine is 1.47 mg/dL, high against reference 0.60-1.30 mg/dL.", 2),
            ("egfr", "The amended eGFR is 54 mL/min/1.73 m2 and is flagged low."),
            ("verification", "C. Liu verified the final amendment on 2026-05-09 at 07:18."),
        ],
        budget=2,
    )
    _facts(
        case,
        "custody",
        "Native custody continuation",
        "table",
        [
            ("collection", "Tube CH-551 was collected on 2026-05-08 at 07:46 and sealed."),
            ("receipt", "The laboratory accepted the specimen as accession AC-77152 at 15:31."),
            ("versions", "Portal version 1 posted at 21:42 on 2026-05-08 and version 2 posted at 07:22 on 2026-05-09."),
            ("ack", "Dr. Neha Rao reviewed the amendment at 08:06 on 2026-05-09."),
        ],
        budget=1,
    )

    # 16 - intended full-page scan: signed DCF superseding provisional query text.
    c = case.new_page(
        "Signed data clarification form Q-77",
        subtitle="Scanned controlling clarification | Draft response retained and struck",
        section_code="DCF / Q-77",
    )
    scan = _scan_document(
        "DATA CLARIFICATION FORM Q-77 - SIGNED RESPONSE",
        "HTX-204 | Site 014 | Subject 014-003 | Field: W2 ECG performed",
        [
            (
                "Query issued by data management",
                [
                    "The 21 Apr eCRF export reported ECG performed while no tracing identifier was transmitted. Confirm the source value and provide the reason for any correction.",
                    "Query opened 22 Apr 2026 16:05 by data manager AT. Console snapshot on 06 May still displayed the preparer's draft response.",
                ],
            ),
            (
                "Principal investigator response",
                [
                    "Source review confirms no ECG was obtained at W2 because the site ECG machine was unavailable. Record the field as not performed. No tracing exists to upload.",
                    "The original source selection remains visible on the eCRF. DEV-014-03 remains subject to separate deviation-review completion.",
                ],
            ),
            (
                "Data-management disposition",
                [
                    "Response accepted for field correction on 09 May at 09:14. Query closure awaits upload of this signed DCF to the production eCRF repository.",
                ],
            ),
        ],
        controls=[
            ("PI response signed", "checked"),
            ("Site response accepted", "checked"),
            ("Request missing tracing", "crossed"),
            ("Production field updated", "unchecked"),
            ("Query closed", "unchecked"),
            ("Deviation review complete", "unchecked"),
        ],
        corrections=[
            ("Draft response: ECG performed; tracing will be uploaded", "Final response: ECG not performed; no tracing exists", "NR 09 May 08:42"),
        ],
        signatures=[
            "Prepared by Maya Kapoor, 08 May 2026 15:36. Final response signed by Dr. Neha Rao, 09 May 2026 08:42.",
            "Accepted by data manager A. Thomas, 09 May 2026 09:14. Administrative closure not yet completed.",
        ],
        seed=1716,
        form_code="DM-DCF-02 / FINAL RESPONSE",
    )
    _place_full_scan(c, scan)
    _gold_scan(
        case,
        "Signed data clarification form Q-77",
        "Q-77 concerns subject 014-003's W2 ECG-performed field. The draft response 'ECG performed; tracing will be uploaded' is struck. The final response says ECG was not performed because the machine was unavailable and no tracing exists. PI response signed and site response accepted are checked. Request missing tracing is crossed. Production field updated, query closed, and deviation review complete are unchecked. Dr. Neha Rao signed the final response on 2026-05-09 at 08:42. A. Thomas accepted it at 09:14. The signed DCF controls over the provisional console response on page 7, but administrative closure still awaits upload.",
    )
    _facts(
        case,
        "q77",
        "Signed data clarification form Q-77",
        "form",
        [
            ("draft", "The draft Q-77 response saying ECG performed and tracing will be uploaded is struck.", 2),
            ("final", "The signed final response says ECG was not performed because the machine was unavailable and no tracing exists.", 2),
            ("pi-signed", "PI response signed is checked.", 1, ("PI response signed", "checked")),
            ("site-accepted", "Site response accepted is checked.", 1, ("Site response accepted", "checked")),
            ("tracing", "Request missing tracing is crossed.", 1, ("Request missing tracing", "crossed")),
            ("production", "Production field updated is unchecked.", 1, ("Production field updated", "unchecked")),
            ("closed", "Query closed is unchecked.", 2, ("Query closed", "unchecked")),
            ("deviation-complete", "Deviation review complete is unchecked.", 2, ("Deviation review complete", "unchecked")),
            ("signatures", "Dr. Neha Rao signed at 08:42 and A. Thomas accepted at 09:14 on 2026-05-09."),
            ("precedence", "The signed DCF controls over the provisional console response on page 7 while both states remain part of the record.", 2),
        ],
        budget=2,
    )

    # 17 - dense monitoring narrative and cross-page references.
    c = case.new_page(
        "Monitor field notes - source review chronology",
        subtitle="Contemporaneous narrative by Lina Sen | 08-09 May 2026",
        section_code="WORKPAPER / NOTES",
    )
    note_blocks = [
        ("08 May 2026 08:42 - opening and access", "Met MK in records room. Confirmed the data cut and obtained read-only portal access. The subject binder index matched sixteen screened identifiers. Pharmacy access was delayed until RP completed the morning count; no conclusions were recorded from inventory labels alone."),
        ("08 May 2026 10:18 - consent and delegation", "Compared the delegation log with the scanned verification worksheet. Roles for NR, MK, RP, and JD were in effect on the relevant dates. The subject 014-012 consent sequence was reviewed directly; applicability marks were treated as marked states rather than inferred omissions."),
        ("08 May 2026 11:26 - subject 014-003", "Traced the W2 visit from the roster through the visit log, eCRF, query console, and signed clarification route. The exported field and source history did not agree. I retained the console snapshot as evidence of its timestamp and routed final field resolution to the signed DCF."),
        ("08 May 2026 14:20 - subject 014-007 pharmacy chain", "Matched the receipt-ledger kit identity to the storage-excursion form and physical-count row. The physical count did not by itself establish disposition. Sponsor response, pharmacist authorization, checkbox state, and segregation witness were reviewed on the controlling form."),
        ("09 May 2026 08:12 - laboratory amendments", "Reviewed SH-204-52 custody, amended analytical report, and PI acknowledgement. The amendment changed the named analytical field without changing collection or receipt timestamps. SH-204-45 required separate receipt-source review because its portal row did not carry the handwritten correction."),
        ("09 May 2026 10:40 - deviations and actions", "Checked the deviation chronology against signed reviews. Several tracker entries remained working drafts. Due dates were not copied forward until the signed CAPA source was available. Open-item aging was calculated from the original opened timestamp, not from the latest response."),
    ]
    y = 675
    gold_notes: list[str] = []
    for heading, body in note_blocks:
        draw_label(c, heading, 42, y)
        y = draw_paragraph(c, body, 42, y - 17, 510, size=7.55, leading=10.2) - 12
        gold_notes.append(f"### {heading}\n\n{body}")
    case.add_gold("Page 17 - Monitor field notes - source review chronology", "\n\n".join(gold_notes))
    _facts(
        case,
        "notes",
        "Monitor source-review chronology",
        "text",
        [
            ("access", "At 08:42 on 2026-05-08, pharmacy access was deferred until RP completed the morning count."),
            ("014003", "At 11:26, the monitor retained subject 014-003's console snapshot as timestamp evidence but routed final field resolution to the signed DCF.", 2),
            ("014007", "At 14:20, the monitor found that subject 014-007's physical kit count did not by itself establish disposition.", 2),
            ("lab", "On 2026-05-09, the monitor treated the SH-204-52 amendment as changing the analytical field without changing collection or receipt timestamps."),
            ("sh20445", "SH-204-45 required separate receipt-source review because its portal row lacked the handwritten correction."),
            ("drafts", "Due dates were not copied from working trackers until the signed CAPA source was available."),
        ],
        budget=2,
    )

    # 18 - mixed ePRO source.
    c = case.new_page(
        "ePRO retraining source and device-event continuation",
        subtitle="Mixed source: signed competency image plus native helpdesk audit trail",
        section_code="ePRO / Q-91",
    )
    epro_scan = _scan_document(
        "ePRO RETRAINING AND COMPETENCY RECORD",
        "Subject 014-014 | Device EP-441 | Session 08 May 2026 13:30-13:58",
        [
            ("Observed tasks", ["Subject logged in with own credentials, entered a practice symptom diary, corrected a mistaken severity before submission, and synchronized while the device was online."]),
            ("Trainer note", ["Initial activation on 01 May failed because the temporary PIN had expired. Training used a replacement PIN generated at 13:24; no proxy entry was performed by site staff."]),
        ],
        controls=[
            ("Independent login observed", "checked"),
            ("Practice diary submitted", "checked"),
            ("Correction before submission observed", "checked"),
            ("Proxy login used", "unchecked"),
            ("Paper diary fallback", "disabled"),
            ("Competency accepted", "checked"),
        ],
        signatures=["Trainer Maya Kapoor 08 May 13:58; subject acknowledgment 08 May 13:59; monitor review LS 09 May 09:02."],
        seed=1718,
        width=1900,
        height=930,
        form_code="ePRO-TRN-07 / REV 4",
    )
    _place_mixed_scan(c, epro_scan, y=410, height=260)
    event_headers = ["Timestamp", "System event", "Actor", "Outcome"]
    event_rows = [
        ["01 May 10:02", "Activation link issued", "System", "Temporary PIN created"],
        ["01 May 10:21", "Activation attempt", "014-014", "PIN expired / rejected"],
        ["04 May 12:16", "Helpdesk ticket HD-551", "MK", "Retraining requested"],
        ["08 May 13:24", "Replacement PIN", "System", "One-time PIN generated"],
        ["08 May 13:31", "Device login", "014-014", "Successful"],
        ["08 May 13:47", "Practice diary sync", "EP-441", "Accepted"],
        ["08 May 14:03", "Q-91 response", "MK", "Training source attached"],
    ]
    draw_label(c, "Native helpdesk and device audit trail", 42, 380)
    draw_table(c, 42, 365, [110, 165, 90, 145], [event_headers, *event_rows], font_size=6.6, zebra=True)
    case.add_gold(
        "Page 18 - ePRO retraining and device-event continuation",
        "The signed record for subject 014-014 / device EP-441 documents retraining from 13:30 to 13:58 on 2026-05-08. Independent login observed, practice diary submitted, correction before submission observed, and competency accepted are checked. Proxy login used is unchecked. Paper diary fallback is disabled. MK trained and signed; LS reviewed on 2026-05-09 at 09:02.\n\n" + markdown_table(event_headers, event_rows),
    )
    _facts(
        case,
        "epro-form",
        "Scanned ePRO competency form",
        "form",
        [
            ("independent", "Independent login observed is checked.", 1, ("Independent login observed", "checked")),
            ("practice", "Practice diary submitted is checked.", 1, ("Practice diary submitted", "checked")),
            ("correction", "Correction before submission observed is checked.", 1, ("Correction before submission observed", "checked")),
            ("proxy", "Proxy login used is unchecked.", 2, ("Proxy login used", "unchecked")),
            ("paper", "Paper diary fallback is disabled.", 1, ("Paper diary fallback", "disabled")),
            ("accepted", "Competency accepted is checked.", 1, ("Competency accepted", "checked")),
            ("accepted-review", "LS reviewed the competency record on 2026-05-09 at 09:02."),
        ],
        budget=2,
    )
    _facts(
        case,
        "epro-events",
        "Native ePRO audit trail",
        "table",
        [
            ("failure", "Subject 014-014's 01 May activation attempt was rejected because the PIN expired."),
            ("replacement", "A replacement one-time PIN was generated on 2026-05-08 at 13:24."),
            ("sync", "Device EP-441's practice diary sync was accepted at 13:47."),
            ("q91", "MK attached the training source to Q-91 at 14:03."),
        ],
        budget=1,
    )

    # 19 - working CAPA tracker, deliberately superseded by page 25.
    c = case.new_page(
        "Corrective-action working tracker - draft 2",
        subtitle="Working copy exported 08 May 16:10 | Signed CAPA approval controls final owners and dates",
        section_code="CAPA / DRAFT",
    )
    capa_headers = ["Draft item", "Linked record", "Proposed action", "Draft owner", "Draft due", "Working state"]
    capa_rows = [
        ["C-01", "DEV-014-03 / Q-77", "Upload signed DCF and verify production field", "MK", "13 May", "Await signature"],
        ["C-02", "DEV-014-07", "Obtain RX-2 calibration certificate", "RP", "28 May", "Vendor contacted"],
        ["C-03", "K-204-146", "Document subject return attempts", "MK", "15 May", "Call planned"],
        ["C-04", "SH-204-45", "File corrected courier receipt", "MK", "14 May", "Receipt requested"],
        ["C-05", "DEV-014-09", "Review amended chemistry with PI", "NR", "10 May", "Report pending"],
        ["C-06", "DEV-014-10 / Q-91", "Attach competency source", "MK", "09 May", "Training planned"],
        ["C-07", "DEV-014-11 / Q-93", "Complete masking impact assessment", "NR", "20 May", "Template opened"],
        ["C-08", "Q-86", "File visit-window calculation", "MK", "16 May", "Calendar note draft"],
    ]
    draw_table(c, 30, 675, [60, 104, 190, 70, 66, 92], [capa_headers, *capa_rows], font_size=5.9, zebra=True)
    draw_badge(c, "Draft - not approved", 42, 340, AMBER)
    draw_paragraph(c, "Dates and owners on this page are proposals captured before final review. Keep them as draft audit history. Page 25 contains the signed CAPA approval and may change an owner, due date, or required evidence without invalidating this snapshot.", 42, 304, 510, size=8.5, leading=11.6)
    draw_paragraph(c, "Completion cannot be inferred from vendor contact, a planned call, a pending report, or an opened template. Those phrases describe working activity only.", 42, 216, 510, size=8.2, leading=11.2, color=MUTED)
    _gold_table(
        case,
        "Corrective-action working tracker - draft 2",
        capa_headers,
        capa_rows,
        "This page is draft 2, exported on 2026-05-08 at 16:10, and is not approved; it is retained as audit history.\n\nThe signed approval on page 25 controls final owners, due dates, and required evidence; vendor contact, planned calls, pending reports, and opened templates do not prove completion.",
    )
    _facts(
        case,
        "capa-draft",
        "Draft corrective-action tracker",
        "table",
        [
            ("status", "The page is draft 2 exported 2026-05-08 at 16:10 and is not approved.", 2),
            ("c02", "Draft item C-02 proposes RP obtain the RX-2 calibration certificate by 2026-05-28."),
            ("c05", "Draft item C-05 proposes NR review the amended chemistry by 2026-05-10."),
            ("c07", "Draft item C-07 proposes NR complete the masking impact assessment by 2026-05-20."),
            ("c08", "Draft item C-08 proposes MK file the visit-window calculation by 2026-05-16."),
            ("precedence", "The page explicitly defers final owners, dates, and evidence to the signed approval on page 25.", 2),
        ],
        budget=2,
    )

    # 20 - intended full-page scan: corrected courier receipt.
    c = case.new_page(
        "Courier and laboratory receipt SH-204-45",
        subtitle="Scanned custody source | Handwritten decimal correction retained",
        section_code="LAB / RECEIPT",
    )
    scan = _scan_document(
        "SPECIMEN COURIER AND LABORATORY RECEIPT",
        "Shipment SH-204-45 | Subject 014-003 | PK-W2 | Accession AC-76881",
        [
            (
                "Site handoff",
                [
                    "Specimen collected 21 Apr 2026 at 08:44 into tube PK-303. Tube label matched subject 014-003 and visit W2. Site placed tube in shipper at 16:58.",
                    "Courier Apex pickup occurred 21 Apr at 17:35. Airway bill 77194510. External shipper seal S-449 was intact at handoff.",
                ],
            ),
            (
                "Laboratory receipt",
                [
                    "NCL laboratory received the shipper on 23 Apr 2026 at 16:40. Accession AC-76881 was assigned after identity and volume review.",
                    "The receipt clerk initially wrote the probe reading with a misplaced decimal. The contemporaneous logger printout was attached and the entry was corrected before acceptance.",
                    "Specimen volume 3.8 mL; no hemolysis; tube and requisition identifiers matched. The delay from collection was retained as a custody exception.",
                ],
            ),
            (
                "Exception routing",
                [
                    "Custody exception CE-204-12 was opened for elapsed transit. Analytical acceptance was decided separately from the exception's administrative closure.",
                ],
            ),
        ],
        controls=[
            ("External seal intact at site handoff", "checked"),
            ("External seal intact at lab receipt", "checked"),
            ("Tube identity matched requisition", "checked"),
            ("Specimen rejected", "unchecked"),
            ("Analytical use accepted", "checked"),
            ("Custody exception closed", "unchecked"),
        ],
        corrections=[
            ("Probe temperature at receipt 22.1 C", "Probe temperature at receipt 2.1 C", "EB 23 Apr 16:52"),
        ],
        signatures=[
            "Site release Maya Kapoor, 21 Apr 2026 17:02. Courier J. Wynn, 21 Apr 17:35.",
            "Laboratory receipt E. Brown, 23 Apr 2026 16:52. Supervisor acceptance C. Liu, 23 Apr 17:10.",
        ],
        seed=1720,
        form_code="NCL-CUST-08 / AC-76881",
    )
    _place_full_scan(c, scan)
    _gold_scan(
        case,
        "Courier and laboratory receipt SH-204-45",
        "Shipment SH-204-45 for subject 014-003 / PK-W2 was collected 2026-04-21 at 08:44, handed to Apex at 17:35, and received by NCL on 2026-04-23 at 16:40 as accession AC-76881. The original probe temperature 22.1 C is struck and corrected to 2.1 C by EB at 16:52. External seal intact at site handoff, external seal intact at lab receipt, tube identity matched, analytical use accepted are checked. Specimen rejected and custody exception closed are unchecked. Custody exception CE-204-12 remains administratively open even though analytical use was accepted.",
    )
    _facts(
        case,
        "receipt",
        "Corrected specimen receipt scan",
        "form",
        [
            ("identity", "SH-204-45 is subject 014-003's W2 PK specimen and laboratory accession AC-76881."),
            ("times", "It was collected on 2026-04-21 at 08:44, picked up at 17:35, and received on 2026-04-23 at 16:40."),
            ("correction", "Original receipt temperature 22.1 C is struck and corrected to 2.1 C by EB at 16:52.", 2),
            ("seal-site", "External seal intact at site handoff is checked.", 1, ("External seal intact at site handoff", "checked")),
            ("seal-lab", "External seal intact at lab receipt is checked.", 1, ("External seal intact at lab receipt", "checked")),
            ("accepted", "Analytical use accepted is checked.", 2, ("Analytical use accepted", "checked")),
            ("rejected", "Specimen rejected is unchecked.", 2, ("Specimen rejected", "unchecked")),
            ("exception", "Custody exception CE-204-12 remains open even though analytical use was accepted.", 2),
        ],
        budget=2,
    )

    # 21 - mixed dosing worksheet.
    c = case.new_page(
        "014-016 dosing source and timed observations",
        subtitle="Mixed source: marked worksheet plus native observation series",
        section_code="DOSING / AE-014-05",
    )
    dose_scan = _scan_document(
        "UNSCHEDULED DOSING DECISION WORKSHEET",
        "Subject 014-016 | 04 May 2026 | Linked AE-014-05 and masking review Q-93",
        [
            ("Decision context", ["Capillary glucose was confirmed before the planned dose. The PI gave a verbal instruction at 08:11 and signed the source at 18:34 after the safety call."]),
            ("Source note", ["The original administered selection was made while preparing the blank worksheet and was crossed before any product left controlled custody. Kit K-204-190 remained in the dosing room lockbox during observation."]),
        ],
        controls=[
            ("Dose administered", "crossed"),
            ("Dose withheld", "checked"),
            ("Rescue carbohydrate given", "checked"),
            ("Emergency transfer required", "unchecked"),
            ("Unblinded pharmacist consulted", "checked"),
            ("Subject discharged with escort", "checked"),
        ],
        corrections=[("Dose administered at 08:15", "Dose withheld before administration", "NR 04 May 08:11")],
        signatures=["Verbal order NR 08:11; witnessed MK 08:12. PI source signature NR 18:34 after safety call."],
        seed=1721,
        width=1900,
        height=1020,
        form_code="DOSE-UNS-03 / SOURCE",
    )
    _place_mixed_scan(c, dose_scan, y=410, height=260)
    obs_headers = ["Time", "Glucose mg/dL", "Symptoms", "Intervention / observation"]
    obs_rows = [
        ["07:58", "62", "Tremor, sweating", "Pre-dose measurement"],
        ["08:12", "60", "Tremor", "15 g oral carbohydrate"],
        ["08:27", "71", "Improving", "Observed; no product released"],
        ["08:44", "84", "Resolved", "Snack provided"],
        ["09:05", "91", "None", "Discharged with spouse"],
        ["18:16", "88 self-report", "None", "Safety call completed"],
    ]
    draw_label(c, "Native timed observation series", 42, 380)
    draw_table(c, 42, 365, [78, 108, 118, 206], [obs_headers, *obs_rows], font_size=6.65, zebra=True)
    case.add_gold(
        "Page 21 - Subject 014-016 dosing worksheet and observations",
        "For subject 014-016 on 2026-05-04, Dose administered is crossed out and Dose withheld is checked. Rescue carbohydrate given and Unblinded pharmacist consulted are checked. Subject discharged with escort is checked. Emergency transfer required is unchecked. NR corrected the prepared administered entry to dose withheld before administration at 08:11. The 18:16 safety call recorded self-reported glucose 88 mg/dL and no symptoms.\n\n" + markdown_table(obs_headers, obs_rows),
    )
    _facts(
        case,
        "dose-form",
        "Marked dosing decision worksheet",
        "form",
        [
            ("administered", "Dose administered is crossed."),
            ("withheld", "Dose withheld is checked.", 2, ("Dose withheld", "checked")),
            ("withheld-correction", "The correction says the dose was withheld before administration.", 2),
            ("rescue", "Rescue carbohydrate given is checked.", 1, ("Rescue carbohydrate given", "checked")),
            ("transfer", "Emergency transfer required is unchecked.", 1, ("Emergency transfer required", "unchecked")),
            ("consult", "Unblinded pharmacist consulted is checked.", 1, ("Unblinded pharmacist consulted", "checked")),
            ("escort", "Subject discharged with escort is checked.", 1, ("Subject discharged with escort", "checked")),
        ],
        budget=2,
    )
    _facts(
        case,
        "observations",
        "Timed glucose observation series",
        "table",
        [
            ("baseline", "At 07:58, glucose was 62 mg/dL with tremor and sweating."),
            ("rescue", "At 08:12, glucose was 60 mg/dL and 15 g oral carbohydrate was given."),
            ("recovery", "Glucose rose to 91 mg/dL by 09:05 and the subject was discharged with a spouse."),
            ("call", "The 18:16 safety call recorded self-reported glucose 88 mg/dL and no symptoms."),
        ],
        budget=1,
    )

    # 22 - intended full-page scan: PI review states.
    c = case.new_page(
        "Principal-investigator deviation review sheet",
        subtitle="Scanned review states | Each mark is independently meaningful",
        section_code="PI REVIEW / 09 MAY",
    )
    scan = _scan_document(
        "PRINCIPAL INVESTIGATOR DEVIATION REVIEW",
        "HTX-204 | Site 014 | Review meeting 09 May 2026 10:05-10:32",
        [
            (
                "Review instructions",
                [
                    "A checked Reviewed box confirms the PI reviewed the listed source and classification. An unchecked box means review remains outstanding. A crossed box withdraws the proposed review item. A disabled box means PI review is not applicable.",
                ],
            ),
            (
                "Items presented",
                [
                    "DEV-014-03 - subject 014-003 W2 ECG source correction; major classification proposed; signed DCF available.",
                    "DEV-014-07 - subject 014-007 IP storage excursion; major classification; pharmacy source available.",
                    "DEV-014-08 - subject 014-009 visit-window calculation; class awaiting calendar adjudication.",
                    "DEV-014-09 - subject 014-011 repeat chemistry evidence; amended report available after the ordinary cut.",
                    "DEV-014-10 - subject 014-014 ePRO activation issue; training evidence attached.",
                    "DEV-014-11 - subject 014-016 unblinded detail; masking impact assessment not yet attached.",
                ],
            ),
            (
                "Meeting note",
                [
                    "The PI reviewed only the rows marked below. Availability of a linked document does not convert an unchecked review state to complete.",
                ],
            ),
        ],
        controls=[
            ("DEV-014-03 reviewed", "checked"),
            ("DEV-014-07 reviewed", "checked"),
            ("DEV-014-08 reviewed", "unchecked"),
            ("DEV-014-09 reviewed", "checked"),
            ("DEV-014-10 PI review required", "disabled"),
            ("DEV-014-11 reviewed", "unchecked"),
            ("Proposed DEV-014-06 review", "crossed"),
            ("All deviations complete", "unchecked"),
        ],
        signatures=[
            "Rows reviewed and signed by Dr. Neha Rao, 09 May 2026 10:32. Monitor witness Lina Sen, 10:33.",
            "DEV-014-08 and DEV-014-11 remain on the action route. DEV-014-10 PI review is not applicable under WI-CLIN-17 section 6.4.",
        ],
        seed=1722,
        form_code="PI-DEV-05 / REV 6",
    )
    _place_full_scan(c, scan)
    _gold_scan(
        case,
        "Principal-investigator deviation review sheet",
        "DEV-014-03 reviewed, DEV-014-07 reviewed, and DEV-014-09 reviewed are checked. DEV-014-08 reviewed and DEV-014-11 reviewed are unchecked. DEV-014-10 PI review required is disabled. Proposed DEV-014-06 review is crossed out. All deviations complete is unchecked. Dr. Neha Rao signed reviewed rows on 2026-05-09 at 10:32; LS witnessed at 10:33. The unchecked states remain open even though some linked documents are available.",
    )
    _facts(
        case,
        "pi-review",
        "PI deviation review scan",
        "form",
        [
            ("dev03", "DEV-014-03 reviewed is checked."),
            ("dev07", "DEV-014-07 reviewed is checked."),
            ("dev08", "DEV-014-08 reviewed is unchecked.", 2),
            ("dev09", "DEV-014-09 reviewed is checked."),
            ("dev10", "DEV-014-10 PI review required is disabled.", 1, ("DEV-014-10 PI review required", "disabled")),
            ("dev11", "DEV-014-11 reviewed is unchecked.", 2),
            ("withdrawn", "Proposed DEV-014-06 review is crossed."),
            ("complete", "All deviations complete is unchecked.", 2),
        ],
        budget=2,
    )

    # 23 - mixed medication reconciliation source.
    c = case.new_page(
        "014-004 medication source and coding",
        subtitle="Mixed source: signed medication marks plus native coding map",
        section_code="MEDICATION / ET",
    )
    med_scan = _scan_document(
        "EARLY-TERMINATION MEDICATION RECONCILIATION",
        "Subject 014-004 | Early termination 24 Apr 2026 | AE-014-01 dizziness",
        [
            ("Medication source", ["Amlodipine 5 mg once daily started 2021; losartan 50 mg once daily started 2023; study drug listed separately in accountability source."]),
            ("Reconciliation note", ["The coordinator initially marked amlodipine stopped. The PI review found that losartan, not amlodipine, was held for two days during the dizziness assessment. The source correction retains the original mark."]),
        ],
        controls=[
            ("Amlodipine discontinued", "crossed"),
            ("Amlodipine continued", "checked"),
            ("Losartan held 24-25 Apr", "checked"),
            ("Losartan permanently stopped", "unchecked"),
            ("New concomitant medication", "unchecked"),
        ],
        corrections=[("Amlodipine discontinued 24 Apr", "Amlodipine continued; losartan held 24-25 Apr", "NR 27 Apr 09:16")],
        signatures=["Coordinator MK 24 Apr 11:20; correction authorized NR 27 Apr 09:16; monitor verified LS 09 May 11:05."],
        seed=1723,
        width=1900,
        height=1020,
        form_code="CM-ET-04 / SOURCE",
    )
    _place_mixed_scan(c, med_scan, y=410, height=260)
    code_headers = ["Source term", "WHODrug preferred name", "ATC", "Coded action qualifier"]
    code_rows = [
        ["Amlodipine 5 mg QD", "AMLODIPINE", "C08CA01", "Ongoing"],
        ["Losartan 50 mg QD", "LOSARTAN", "C09CA01", "Interrupted"],
        ["Study drug HTX-204", "BLINDED THERAPY", "-", "Withdrawn per protocol"],
    ]
    draw_label(c, "Native coding continuation", 42, 380)
    draw_table(c, 42, 365, [135, 150, 80, 145], [code_headers, *code_rows], font_size=6.8, zebra=True)
    case.add_gold(
        "Page 23 - Subject 014-004 medication reconciliation",
        "Amlodipine discontinued is crossed out and Amlodipine continued is checked. Losartan held 24-25 Apr is checked; Losartan permanently stopped and New concomitant medication are unchecked. NR corrected the source on 2026-04-27 at 09:16.\n\n" + markdown_table(code_headers, code_rows),
    )
    _facts(
        case,
        "med-form",
        "Marked medication reconciliation",
        "form",
        [
            ("amlodipine-stop", "Amlodipine discontinued is crossed.", 2, ("Amlodipine discontinued", "crossed")),
            ("amlodipine-continue", "Amlodipine continued is checked.", 2, ("Amlodipine continued", "checked")),
            ("losartan-held", "Losartan held 24-25 Apr is checked.", 1, ("Losartan held 24-25 Apr", "checked")),
            ("losartan-stop", "Losartan permanently stopped is unchecked.", 1, ("Losartan permanently stopped", "unchecked")),
            ("new-med", "New concomitant medication is unchecked.", 1, ("New concomitant medication", "unchecked")),
        ],
        budget=2,
    )
    _facts(
        case,
        "med-codes",
        "Medication coding continuation",
        "table",
        [
            ("amlodipine", "Amlodipine maps to WHODrug AMLODIPINE, ATC C08CA01, action qualifier Ongoing."),
            ("losartan", "Losartan maps to WHODrug LOSARTAN, ATC C09CA01, action qualifier Interrupted."),
            ("study", "HTX-204 maps to BLINDED THERAPY with action qualifier Withdrawn per protocol."),
        ],
        budget=1,
    )

    # 24 - transfer audit.  This page proves receipt and integrity of individual
    # repository objects; it deliberately does not synthesize field answers,
    # source precedence, entity histories, or packet page locations.
    c = case.new_page(
        "Controlled-record receipt and import audit",
        subtitle="Monitoring repository ingest | Object-level custody, not clinical reconciliation",
        section_code="REPOSITORY / IMPORT",
    )
    import_headers = ["Object", "Repository key", "Received", "Custodian", "Integrity check", "Import disposition", "Reviewer"]
    import_rows = [
        ["DCF Q-77", "DQC/014/Q77/F1", "09 May 09:26", "AT", "SHA-256 matched", "Imported v1", "LS 09:34"],
        ["Receipt SH-204-45", "LAB/AC76881/R2", "09 May 09:41", "EB", "Signature valid", "Imported v2", "LS 09:48"],
        ["Lab AC-77152", "LAB/AC77152/A2", "09 May 07:22", "CL", "Issuer chain valid", "Imported amended", "NR 08:06"],
        ["ePRO competency", "EPRO/014014/TR1", "08 May 14:03", "MK", "Signature valid", "Imported v1", "LS 09:02"],
        ["Dose worksheet", "SRC/014016/DW1", "09 May 10:02", "MK", "Two-page hash matched", "Imported v1", "NR 10:11"],
        ["PI review sheet", "REG/DEV/PI09MAY", "09 May 10:38", "NR", "Signature valid", "Imported v1", "LS 10:41"],
        ["Visit adjudication", "DQC/014/Q86/A1", "09 May 11:36", "MK", "Signature valid", "Staged for upload", "LS 11:42"],
        ["CAPA approval", "CAPA/014/02/F1", "09 May 12:24", "LS", "Dual signature valid", "Imported final", "QA 12:31"],
        ["Action assignment", "MV03/ACTION/I1", "09 May 16:08", "LS", "Acknowledgments valid", "Imported issued", "QA 16:14"],
        ["Masking template", "REG/014016/MASK/D0", "09 May 16:22", "NR", "Unsigned draft", "Quarantined draft", "QA 16:28"],
    ]
    draw_table(c, 22, 675, [78, 104, 72, 52, 99, 105, 68], [import_headers, *import_rows], font_size=5.55, zebra=True)
    draw_label(c, "Scope limitation", 42, 270)
    import_note = (
        "An import disposition establishes only that a named object reached the controlled repository with the recorded integrity result. "
        "Imported, staged, and quarantined are distinct states. This audit does not decide which value controls a clinical field, does not close a query or deviation, and does not replace review of the underlying record."
    )
    draw_paragraph(c, import_note, 42, 248, 510, size=8.4, leading=11.7)
    _gold_table(case, "Controlled-record receipt and import audit", import_headers, import_rows, import_note)
    import_bindings = {
        ("DCF Q-77", "Import disposition"),
        ("Receipt SH-204-45", "Repository key"),
        ("Lab AC-77152", "Import disposition"),
        ("Visit adjudication", "Import disposition"),
        ("CAPA approval", "Integrity check"),
        ("Masking template", "Integrity check"),
        ("Masking template", "Import disposition"),
    }
    case.add_region(
        "p24.import",
        "Controlled-record repository import audit",
        "table",
        table_leaves("p24.import", import_headers, import_rows, scored_bindings=import_bindings),
        budget=2,
        closed_world=True,
        primary_axis="table_reconstruction",
        secondary_axes=["precise_recall"],
    )
    _facts(
        case,
        "import-scope",
        "Repository import scope limitation",
        "text",
        [
            ("states", "Imported, staged, and quarantined are distinct repository states."),
            ("not-control", "An import disposition does not decide which value controls a clinical field.", 2),
            ("not-close", "The import audit does not close a query or deviation.", 2),
        ],
        budget=1,
        primary_axis="source_precedence",
    )

    # 25 - intended full-page scan: signed CAPA approval superseding page 19.
    c = case.new_page(
        "Signed CAPA approval and revised obligations",
        subtitle="Scanned final approval | Revised dates supersede draft tracker only for named fields",
        section_code="CAPA / FINAL",
    )
    scan = _scan_document(
        "CORRECTIVE AND PREVENTIVE ACTION PLAN - FINAL APPROVAL",
        "HTX-204 Site 014 | CAPA-014-02 | Approved 09 May 2026 12:18",
        [
            (
                "Approved corrective actions",
                [
                    "C-01: MK uploads signed Q-77 DCF and verifies the production field by 10 May 12:00; evidence is repository audit screenshot plus query export.",
                    "C-02: RP obtains the RX-2 calibration certificate by 12 May 17:00; evidence must cover service reset and device serial RX2-441.",
                    "C-03: MK documents three contact attempts for K-204-146 return by 13 May 15:00; evidence is contact log and accountability annotation.",
                    "C-04: MK files the corrected SH-204-45 receipt by 11 May 12:00; evidence is the signed receipt image and CE-204-12 reference.",
                    "C-05: NR documents review of the amended chemistry by 09 May 17:00; evidence is PI acknowledgement in the lab portal.",
                    "C-06: MK attaches the ePRO competency record by 09 May 14:00; evidence is the signed training source and Q-91 audit entry.",
                    "C-07: NR completes the DEV-014-11 masking impact assessment by 11 May 16:00; evidence is signed assessment and Q-93 response.",
                    "C-08: MK uploads the signed Q-86 window calculation by 11 May 12:00; evidence is the adjudication sheet and production calendar note.",
                ],
            ),
            (
                "Preventive action",
                [
                    "RP adds a weekly refrigerator-certificate availability check to the pharmacy opening log beginning 13 May. MK adds source-precedence review to coordinator refresher training by 20 May.",
                ],
            ),
            (
                "Change from draft",
                [
                    "Final review accelerated C-02, C-04, C-07, and C-08 and changed the required evidence. Draft dates on page 19 remain audit history and are not completion targets.",
                ],
            ),
        ],
        controls=[
            ("CAPA approved by PI", "checked"),
            ("CAPA accepted by monitor", "checked"),
            ("Sponsor escalation required", "unchecked"),
            ("Draft due dates remain operative", "crossed"),
            ("Effectiveness check required", "checked"),
            ("CAPA complete at approval", "unchecked"),
        ],
        signatures=[
            "PI approval Neha Rao 09 May 2026 12:14. Monitor acceptance Lina Sen 09 May 12:18.",
            "Effectiveness check owner: LS. Review window 21 May 09:00-22 May 17:00. Completion requires evidence, not assignment alone.",
        ],
        seed=1725,
        form_code="CAPA-014-02 / FINAL",
    )
    _place_full_scan(c, scan)
    _gold_scan(
        case,
        "Signed CAPA approval and revised obligations",
        "CAPA-014-02 was approved on 2026-05-09. Final C-01: MK upload Q-77 DCF and verify production field by 2026-05-10 12:00. Final C-02: RP obtain RX-2 calibration certificate by 2026-05-12 17:00. Final C-03: MK document three K-204-146 return contact attempts by 2026-05-13 15:00. Final C-04: MK file corrected SH-204-45 receipt by 2026-05-11 12:00. Final C-05: NR document amended-chemistry review by 2026-05-09 17:00. Final C-06: MK attach ePRO competency record by 2026-05-09 14:00. Final C-07: NR complete DEV-014-11 masking impact assessment by 2026-05-11 16:00. Final C-08: MK upload signed Q-86 window calculation by 2026-05-11 12:00. CAPA approved by PI is checked. CAPA accepted by monitor is checked. Effectiveness check required is checked. Sponsor escalation required and CAPA complete at approval are unchecked. Draft due dates remain operative is crossed. The final signed dates control. LS owns the effectiveness check scheduled for 2026-05-21 through 2026-05-22.",
    )
    _facts(
        case,
        "capa-final",
        "Signed final CAPA approval",
        "form",
        [
            ("c01", "Final C-01 assigns MK to upload Q-77 DCF and verify the production field by 2026-05-10 at 12:00."),
            ("c02", "Final C-02 assigns RP to obtain the RX-2 calibration certificate by 2026-05-12 at 17:00.", 2),
            ("c04", "Final C-04 assigns MK to file the corrected SH-204-45 receipt by 2026-05-11 at 12:00."),
            ("c07", "Final C-07 assigns NR to complete the DEV-014-11 masking impact assessment by 2026-05-11 at 16:00.", 2),
            ("c08", "Final C-08 assigns MK to upload the signed Q-86 window calculation by 2026-05-11 at 12:00.", 2),
            ("pi-approved", "CAPA approved by PI is checked.", 1, ("CAPA approved by PI", "checked")),
            ("monitor-accepted", "CAPA accepted by monitor is checked.", 1, ("CAPA accepted by monitor", "checked")),
            ("effectiveness-required", "Effectiveness check required is checked.", 1, ("Effectiveness check required", "checked")),
            ("sponsor-escalation", "Sponsor escalation required is unchecked.", 1, ("Sponsor escalation required", "unchecked")),
            ("not-complete", "CAPA complete at approval is unchecked.", 1, ("CAPA complete at approval", "unchecked")),
            ("draft", "Draft due dates remain operative is crossed.", 2, ("Draft due dates remain operative", "crossed")),
            ("signed-control", "The final signed CAPA dates control over draft dates.", 2, {"evidence": ["CAPA", "final", "signed", "control", "draft"]}),
            ("effectiveness", "LS owns the effectiveness check scheduled for 2026-05-21 through 2026-05-22."),
        ],
        budget=2,
    )

    # 26 - aging table, not a duplicate of final action assignments.
    c = case.new_page(
        "Open-item aging and evidence status",
        subtitle="Calculated 09 May 13:00 | Age runs from original opening timestamp",
        section_code="ITEM AGING",
    )
    aging_headers = ["Item", "Entity", "Opened", "Age", "Latest evidence", "Evidence state", "Next controlled record"]
    aging_rows = [
        ["Q-77", "014-003", "22 Apr 16:05", "16 d 20 h", "Signed DCF received", "Accepted / not closed", "Production audit"],
        ["CE-204-12", "SH-204-45", "23 Apr 16:52", "15 d 20 h", "Corrected receipt", "Receipt verified", "Exception closure"],
        ["K-204-146 return", "014-003", "05 May 09:05", "4 d 3 h", "No returned kit", "Contact evidence absent", "CAPA C-03"],
        ["Q-84", "014-008", "23 Apr 10:20", "16 d 2 h", "Courier ticket", "Portal receipt absent", "Interface post"],
        ["Q-86", "014-009", "07 May 08:30", "2 d 4 h", "Adjudication drafted", "Signature route", "Signed page 27"],
        ["Q-88", "014-011", "28 Apr 09:10", "11 d 3 h", "Amended report", "PI reviewed", "Query close"],
        ["Q-91", "014-014", "04 May 12:16", "5 d 0 h", "Competency source", "Attached", "Console close"],
        ["Q-93", "014-016", "05 May 11:40", "4 d 1 h", "PI review incomplete", "Assessment absent", "CAPA C-07"],
        ["DEV-014-08", "014-009", "07 May 09:05", "2 d 3 h", "Window calculation", "PI review absent", "Signed page 27"],
        ["CAPA-014-02", "Site 014", "09 May 12:18", "0 d 0 h", "Final approval", "Assigned / open", "Action sheet p28"],
    ]
    draw_table(c, 24, 675, [74, 60, 65, 50, 112, 105, 122], [aging_headers, *aging_rows], font_size=5.65, zebra=True)
    draw_label(c, "Interpretation", 42, 288)
    draw_paragraph(c, "Accepted, verified, reviewed, attached, assigned, and closed are not interchangeable. The evidence-state column records the latest demonstrated state. The next-controlled-record column identifies what must still occur; it does not assert that the event has occurred.", 42, 266, 510, size=8.3, leading=11.4)
    draw_paragraph(c, "Q-77 therefore remains aged from 22 April even after receipt of its signed DCF. CAPA-014-02 is assigned and open at approval, so its age begins on 9 May rather than inheriting the age of every linked issue.", 42, 178, 510, size=8.3, leading=11.4, color=MUTED)
    _gold_table(
        case,
        "Open-item aging and evidence status",
        aging_headers,
        aging_rows,
        "Calculated on 09 May 2026 at 13:00. Accepted, verified, reviewed, attached, assigned, and closed are distinct evidence states. Q-77 is aged 16 d 20 h from 22 Apr 2026 at 16:05; CE-204-12 is aged 15 d 20 h. The next-controlled-record field identifies what must still occur and does not assert completion.",
    )
    _facts(
        case,
        "aging",
        "Open-item aging and evidence status",
        "table",
        [
            ("q77", "At 2026-05-09 13:00, Q-77 is aged 16 d 20 h from 2026-04-22 16:05 and is accepted but not closed.", 2),
            ("ce", "CE-204-12 is aged 15 d 20 h; its corrected receipt is verified but exception closure remains next."),
            ("k146", "The K-204-146 return item has absent contact evidence and routes to CAPA C-03."),
            ("q86", "Q-86 is on signature route and points to signed page 27."),
            ("q93", "Q-93 has PI review incomplete, assessment absent, and routes to CAPA C-07.", 2),
            ("capa", "CAPA-014-02 is assigned and open, not complete, at approval."),
            (
                "states",
                "The page explicitly distinguishes accepted, verified, reviewed, attached, assigned, and closed states.",
                1,
                {"evidence": ["accepted", "verified", "reviewed", "attached", "assigned", "closed"]},
            ),
        ],
        budget=2,
    )

    # 27 - mixed signed visit-window adjudication and native audit trail.
    c = case.new_page(
        "Subject 014-009 visit-window adjudication",
        subtitle="Mixed source: signed classification above, native calculation lineage below",
        section_code="Q-86 / DEV-014-08",
    )
    window_scan = _scan_document(
        "SIGNED VISIT-WINDOW ADJUDICATION",
        "Subject 014-009 | W2 attended 06 May 2026 | Query Q-86 | DEV-014-08",
        [
            ("Protocol calculation", ["V1 date 19 Apr 2026 is study day 1. W2 target is study day 15, corresponding to 03 May. Allowed window is plus or minus two calendar days: 01 May through 05 May inclusive."]),
            ("Adjudication", ["Attendance on 06 May is one day beyond the allowed window. The visit procedures remain usable. The discrepancy is retained as a minor protocol deviation and is not reclassified as missed visit."]),
            ("Administrative state", ["The site response is accepted. Closure requires upload of this signed calculation to the production query record and confirmation that the deviation link is active."]),
        ],
        controls=[
            ("Within allowed window", "crossed"),
            ("Minor deviation", "checked"),
            ("Major deviation", "unchecked"),
            ("Missed visit", "unchecked"),
            ("Site response accepted", "checked"),
            ("Q-86 closed", "unchecked"),
        ],
        signatures=["Calculated MK 09 May 10:46; adjudicated NR 09 May 11:22; monitor concurrence LS 09 May 11:28."],
        seed=1727,
        width=1900,
        height=1020,
        form_code="WIN-ADJ-06 / SIGNED",
    )
    _place_mixed_scan(c, window_scan, y=404, height=266)
    audit_headers = ["Audit event", "Timestamp", "Actor", "State after event"]
    audit_rows = [
        ["Calendar note created", "07 May 08:12", "MK", "Draft"],
        ["Q-86 opened", "07 May 08:30", "AT", "Open"],
        ["Deviation linked", "07 May 09:05", "MK", "Class pending"],
        ["Calculation signed", "09 May 11:22", "NR", "Signed source posted"],
        ["Monitor concurred", "09 May 11:28", "LS", "Ready to upload"],
        ["Production upload due", "11 May 12:00", "MK", "Not yet evidenced"],
    ]
    draw_label(c, "Native calculation audit trail", 42, 375)
    draw_table(c, 42, 360, [150, 110, 70, 180], [audit_headers, *audit_rows], font_size=6.65, zebra=True)
    case.add_gold(
        "Page 27 - Subject 014-009 visit-window adjudication",
        "For subject 014-009, V1 on 2026-04-19 is day 1; W2 target is 2026-05-03 and the allowed window is 2026-05-01 through 2026-05-05 inclusive. Attendance on 2026-05-06 is one day beyond the window. Within allowed window is crossed out. Minor deviation and site response accepted are checked. Major deviation, missed visit, and Q-86 closed are unchecked. NR adjudicated on 2026-05-09 at 11:22; LS concurred at 11:28. Production upload is due 2026-05-11 at 12:00 and is not yet evidenced.\n\n" + markdown_table(audit_headers, audit_rows),
    )
    _facts(
        case,
        "window-form",
        "Signed visit-window adjudication",
        "form",
        [
            ("window", "Subject 014-009's allowed W2 window is 2026-05-01 through 2026-05-05 inclusive."),
            ("attendance", "Attendance on 2026-05-06 is one day beyond the window."),
            ("within", "Within allowed window is crossed.", 1, ("Within allowed window", "crossed")),
            ("minor", "Minor deviation is checked.", 2, ("Minor deviation", "checked")),
            ("major", "Major deviation is unchecked.", 2, ("Major deviation", "unchecked")),
            ("missed", "Missed visit is unchecked.", 2, ("Missed visit", "unchecked")),
            ("accepted", "Visit-window site response accepted is checked.", 2, ("Site response accepted", "checked")),
            ("q86-closed", "Q-86 closed is unchecked.", 2, ("Q-86 closed", "unchecked")),
        ],
        budget=2,
    )
    _facts(
        case,
        "window-audit",
        "Visit-window audit trail",
        "table",
        [
            ("sign", "NR signed the calculation at 11:22 and LS concurred at 11:28 on 2026-05-09."),
            ("upload", "Production upload is due to MK on 2026-05-11 at 12:00 and is not yet evidenced.", 2),
            ("state", "After monitor concurrence, the state is Ready to upload rather than closed."),
        ],
        budget=1,
    )

    # 28 - mixed tail action sheet.  This is intentionally an assignment record,
    # not a final findings recap.
    c = case.new_page(
        "Post-visit action assignment and routing",
        subtitle="Selected tail obligations | Assignment does not mean completion",
        section_code="ACTION ROUTE / 09 MAY",
    )
    action_scan = _scan_document(
        "POST-VISIT ACTION ASSIGNMENT",
        "HTX-204 Site 014 | Issued 09 May 2026 15:48 | Monitor Lina Sen",
        [
            (
                "Assigned evidence actions",
                [
                    "A-201 / Q-77: MK uploads the signed DCF and production-field audit by 10 May 12:00. Notify data manager AT after upload.",
                    "A-202 / K-204-153: RP uploads the RX-2 calibration certificate for device RX2-441 by 12 May 17:00. The certificate must cover the 18 Apr service reset.",
                    "A-203 / K-204-146: MK records three subject-return contact attempts and annotates accountability by 13 May 15:00.",
                    "A-204 / DEV-014-11: NR signs the masking impact assessment and Q-93 response by 11 May 16:00.",
                    "A-205 / Q-86: MK uploads the signed visit-window calculation and verifies the deviation link by 11 May 12:00.",
                ],
            ),
            (
                "Escalation rule",
                [
                    "If A-202 is not evidenced by its deadline, RP calls the sponsor supply line the same day and LS records the escalation in CAPA-014-02. Do not substitute an email saying the vendor was contacted for the certificate itself.",
                    "If A-204 is late, site recruitment pauses until the masking impact assessment is signed. This conditional pause is not active at issuance.",
                ],
            ),
        ],
        controls=[
            ("A-201 assigned", "checked"),
            ("A-201 complete", "unchecked"),
            ("A-202 assigned", "checked"),
            ("A-202 complete", "unchecked"),
            ("A-203 assigned", "checked"),
            ("A-204 assigned", "checked"),
            ("A-205 assigned", "checked"),
            ("All post-visit actions complete", "unchecked"),
        ],
        signatures=[
            "Assignments acknowledged: MK 09 May 15:52; RP 09 May 15:56; NR 09 May 16:02.",
            "Issued by LS 09 May 15:48. Evidence review will occur against the signed CAPA fields, not against this acknowledgment alone.",
        ],
        seed=1728,
        width=2100,
        height=1120,
        form_code="MV-ACT-12 / ISSUED",
    )
    _place_mixed_scan(c, action_scan, y=385, height=285)
    route_headers = ["Owner", "Primary route", "Escalation contact", "Review window"]
    route_rows = [
        ["MK", "Secure trial repository", "AT / data management", "10-13 May"],
        ["RP", "Restricted pharmacy vault", "Sponsor supply line", "12 May"],
        ["NR", "PI electronic signature queue", "LS / monitor", "11 May"],
        ["LS", "CAPA effectiveness file", "Clinical lead", "21-22 May"],
    ]
    draw_label(c, "Native routing directory", 42, 355)
    draw_table(c, 42, 340, [70, 170, 145, 125], [route_headers, *route_rows], font_size=6.7, zebra=True)
    case.add_gold(
        "Page 28 - Post-visit action assignment and routing",
        "A-201 assigns MK to upload the signed Q-77 DCF and production-field audit by 2026-05-10 at 12:00. A-202 assigns RP to upload the RX-2 calibration certificate for RX2-441 by 2026-05-12 at 17:00; the certificate must cover the 18 April service reset. A-203 assigns MK to document three K-204-146 return contact attempts by 2026-05-13 at 15:00. A-204 assigns NR to sign the masking impact assessment and Q-93 response by 2026-05-11 at 16:00. A-205 assigns MK to upload the signed visit-window calculation and verify the deviation link by 2026-05-11 at 12:00. A-201 assigned is checked. A-202 assigned is checked. A-201 complete is unchecked. A-202 complete is unchecked. A-203 assigned is checked. A-204 assigned is checked. A-205 assigned is checked. All post-visit actions complete is unchecked. If A-202 is not evidenced by its deadline, RP calls the sponsor supply line the same day and LS records the escalation in CAPA-014-02; an email that a vendor was contacted does not replace the certificate. LS owns the CAPA effectiveness file review from 21 May 2026 through 22 May 2026.\n\n" + markdown_table(route_headers, route_rows),
    )
    _facts(
        case,
        "actions",
        "Post-visit action assignment scan",
        "form",
        [
            ("a201-assignment", "A-201 assigns MK to upload Q-77 evidence by 2026-05-10 at 12:00.", 2),
            ("a201-assigned", "A-201 assigned is checked.", 2, ("A-201 assigned", "checked")),
            ("a201-complete", "A-201 complete is unchecked.", 2, ("A-201 complete", "unchecked")),
            ("a202-assignment", "A-202 assigns RP to upload the RX2-441 calibration certificate by 2026-05-12 at 17:00.", 2),
            ("a202-assigned", "A-202 assigned is checked.", 2, ("A-202 assigned", "checked")),
            ("a202-complete", "A-202 complete is unchecked.", 2, ("A-202 complete", "unchecked")),
            ("a203", "A-203 assigns MK to document three K-204-146 return contact attempts by 2026-05-13 at 15:00."),
            ("a203-assigned", "A-203 assigned is checked.", 1, ("A-203 assigned", "checked")),
            ("a204", "A-204 assigns NR to sign the masking impact assessment and Q-93 response by 2026-05-11 at 16:00.", 2),
            ("a204-assigned", "A-204 assigned is checked.", 1, ("A-204 assigned", "checked")),
            ("a205", "A-205 assigns MK to upload the signed visit-window calculation and verify the deviation link by 2026-05-11 at 12:00.", 2),
            ("a205-assigned", "A-205 assigned is checked.", 1, ("A-205 assigned", "checked")),
            ("all", "All post-visit actions complete is unchecked.", 2, ("All post-visit actions complete", "unchecked")),
            ("escalation", "If A-202 is late, RP must call the sponsor supply line that day and LS must record CAPA escalation."),
            ("evidence", "A vendor-contact email does not substitute for the RX2-441 calibration certificate."),
        ],
        budget=2,
    )
    _facts(
        case,
        "routing",
        "Native action routing directory",
        "table",
        [
            ("mk", "MK uses the secure trial repository and escalates to AT/data management during 2026-05-10 through 2026-05-13."),
            ("rp", "RP uses the restricted pharmacy vault and sponsor supply line on 2026-05-12."),
            ("nr", "NR uses the PI electronic signature queue and escalates to LS on 2026-05-11."),
            ("ls", "LS owns the CAPA effectiveness file review from 21 May 2026 through 22 May 2026."),
        ],
        budget=1,
    )

    # 29 - native eligibility review.  The rows extend subject identity and
    # state over twenty-seven pages without restating downstream answers.
    c = case.new_page(
        "Eligibility-source verification register",
        subtitle="Field-level review against consent, screening laboratory, and investigator signoff",
        section_code="ELIGIBILITY / VERIFY",
    )
    elig_headers = ["Subject", "Consent version", "Key criterion source", "Investigator decision", "Decision time", "Exception / locator", "Monitor state"]
    elig_rows = [
        ["014-001", "6.0", "HbA1c 9.1% / NCL-4401", "Not eligible", "03 Apr 11:08", "I-04 threshold", "Verified 08 May"],
        ["014-002", "6.0", "eGFR 78 / NCL-4418", "Eligible", "05 Apr 07:46", "None", "Verified 08 May"],
        ["014-003", "6.0", "QTc 438 ms / ECG-993", "Eligible", "07 Apr 08:38", "W2 ECG separate", "Verified 08 May"],
        ["014-004", "6.0", "HbA1c 7.7% / NCL-4462", "Eligible", "10 Apr 09:44", "ET does not alter entry", "Verified 09 May"],
        ["014-005", "6.0", "eGFR 71 / NCL-4480", "Eligible", "12 Apr 08:51", "None", "Verified 08 May"],
        ["014-006", "6.0", "eGFR 42 / NCL-4511", "Not eligible", "15 Apr 10:14", "I-07 threshold", "Verified 08 May"],
        ["014-007", "6.0", "Potassium 4.2 / NCL-4540", "Eligible", "18 Apr 08:36", "Excursion post-decision", "Verified 09 May"],
        ["014-008", "6.0", "HbA1c 8.2% / NCL-4568", "Eligible", "20 Apr 08:43", "Receipt later pending", "Verified 08 May"],
        ["014-009", "6.0", "QTc 444 ms / ECG-1018", "Eligible", "19 Apr 09:28", "Window issue later", "Verified 09 May"],
        ["014-011", "6.0", "Creatinine 1.22 / NCL-4619", "Eligible", "26 Apr 08:16", "Later amended repeat", "Verified 09 May"],
        ["014-012", "6.0", "Translated diary / W-14", "Eligible", "28 Apr 10:55", "Waiver affects diary only", "Verified 08 May"],
        ["014-016", "6.0", "Glucose 94 / NCL-4691", "Eligible", "04 May 07:31", "Masking issue post-dose", "Verified 09 May"],
    ]
    elig_y = draw_table(c, 20, 675, [52, 62, 124, 76, 72, 127, 75], [elig_headers, *elig_rows], font_size=5.5, row_padding=2.8, zebra=True)
    elig_note_y = draw_paragraph(c, "Eligibility is a decision at the recorded time. Later adverse events, deviations, laboratory amendments, or withdrawal do not retroactively change the signed enrollment decision. The exception column points to distinct evidence without adjudicating it.", 42, elig_y - 22, 510, size=8.0, leading=11.0, color=MUTED)
    eligibility_review_note = (
        "The monitor verified each row in the sequence consent signature, criterion measurement, and investigator decision. "
        "A later laboratory correction would trigger eligibility reassessment only if it changed a criterion that existed before randomization; no such reassessment is recorded in this register. "
        "The W2 ECG discrepancy, K-204-153 excursion, amended repeat chemistry, visit-window deviation, and masking review all arose after their subjects' enrollment decisions and remain separate longitudinal records."
    )
    draw_paragraph(c, eligibility_review_note, 42, elig_note_y - 7, 510, size=7.7, leading=10.5, color=INK)
    _gold_table(case, "Eligibility-source verification register", elig_headers, elig_rows, "Eligibility is a decision at its recorded time; later events do not retroactively change the enrollment decision. " + eligibility_review_note)
    _selected_table_region(
        case,
        "eligibility",
        "Eligibility-source verification register",
        elig_headers,
        elig_rows,
        [
            ("014-001", "Key criterion source"), ("014-001", "Investigator decision"),
            ("014-003", "Exception / locator"), ("014-007", "Decision time"),
            ("014-012", "Key criterion source"), ("014-012", "Exception / locator"),
            ("014-016", "Key criterion source"), ("014-016", "Investigator decision"),
        ],
        consequential=[("014-001", "Investigator decision"), ("014-012", "Exception / locator")],
    )
    _facts(case, "eligibility-rule", "Eligibility chronology rule", "text", [
        ("time", "Eligibility is a decision at the recorded decision time."),
        ("later", "Later deviations or withdrawal do not retroactively change the enrollment decision.", 2),
        ("reassessment", "No later laboratory correction triggered an eligibility reassessment in this register.", 2),
    ], budget=1, primary_axis="long_context_coherence")

    # 30 - full-page scan: masking access and emergency-code audit.
    c = case.new_page(
        "Randomization and masking-access audit",
        subtitle="Scanned restricted source | Role, access reason, and code-break state",
        section_code="MASKING / ACCESS",
    )
    scan = _scan_document(
        "RANDOMIZATION AND MASKING ACCESS AUDIT",
        "HTX-204 | Site 014 | System RTS-204 | Audit through 09 May 2026 16:00",
        [
            ("Authorized roles", [
                "Ravi Patel has unblinded pharmacy access for receipt, assignment confirmation, accountability, and product disposition. Jaya Das may witness counts but has no code-view permission.",
                "Neha Rao, Maya Kapoor, and Lina Sen remain blinded. Emergency code access requires PI initiation, medical-monitor callback, and a separately generated break certificate.",
            ]),
            ("Subject 014-016 access sequence", [
                "04 May 08:06 - RP viewed kit K-204-190 assignment to confirm controlled custody after low glucose. Access reason recorded as pharmacy custody check; no treatment code was disclosed to the blinded team.",
                "04 May 18:29 - site note by MK included the phrase unblinded pharmacist consulted. The phrase disclosed a role interaction, not the assigned treatment. Q-93 was opened for masking-impact review.",
                "09 May 15:20 - audit search found no emergency code-break request, no treatment-code display, and no break certificate for subject 014-016.",
            ]),
            ("Other restricted events", [
                "18 Apr 13:52 - RP opened sponsor response SR-204-19 for K-204-153 disposition. 06 Apr 14:26 - RP received shipment PS-778. Neither event exposed a subject treatment assignment to blinded users.",
            ]),
        ],
        controls=[
            ("014-016 emergency code break initiated", "unchecked"),
            ("014-016 treatment code displayed", "unchecked"),
            ("014-016 pharmacy custody access", "checked"),
            ("Jaya Das code-view permission", "disabled"),
            ("Masking impact review required", "checked"),
            ("Immediate recruitment pause active", "unchecked"),
        ],
        corrections=[
            ("Access classification: emergency unblinding", "Access classification: restricted pharmacy custody check; no treatment code displayed", "QA 09 May 15:44"),
        ],
        signatures=[
            "Restricted audit extracted by system administrator P. Iyer, 09 May 2026 15:20.",
            "QA classification signed by S. Mehta, 09 May 15:44. PI masking assessment remains a separate record.",
        ],
        seed=1730,
        form_code="RTS-AUD-09 / RESTRICTED",
    )
    _place_full_scan(c, scan)
    _gold_scan(case, "Randomization and masking-access audit", "014-016 pharmacy custody access is checked.\n\n014-016 emergency code break initiated is unchecked.\n\n014-016 treatment code displayed is unchecked.\n\nThe 2026-05-04 08:06 access was by RP for kit K-204-190 custody; no treatment code was disclosed to the blinded team. The 2026-05-04 18:29 site note disclosed that an unblinded pharmacist was consulted, which revealed a role interaction but not the assigned treatment. Jaya Das code-view permission is disabled. Masking impact review required is checked and immediate recruitment pause active is unchecked. The original emergency-unblinding classification is corrected to restricted pharmacy custody check with no treatment code displayed by QA on 2026-05-09 at 15:44.")
    _facts(case, "masking-access", "Scanned masking-access audit", "form", [
        ("custody", "For subject 014-016, pharmacy custody access is checked.", 2, ("014-016 pharmacy custody access", "checked")),
        ("break", "014-016 emergency code break initiated is unchecked.", 2, ("014-016 emergency code break initiated", "unchecked")),
        ("display", "014-016 treatment code displayed is unchecked.", 2, ("014-016 treatment code displayed", "unchecked")),
        ("jaya", "Jaya Das code-view permission is disabled.", 1, ("Jaya Das code-view permission", "disabled")),
        ("review", "Masking impact review required is checked.", 2, ("Masking impact review required", "checked")),
        ("pause", "Immediate recruitment pause active is unchecked.", 2, ("Immediate recruitment pause active", "unchecked")),
        ("correction", "QA corrected emergency unblinding to restricted pharmacy custody check with no treatment code displayed on 2026-05-09 at 15:44.", 2),
        ("role", "The site note disclosed an unblinded pharmacist interaction but not the assigned treatment."),
    ], budget=2, primary_axis="low_quality_scan", secondary_axes=("form_state", "source_precedence"))

    # 31 - native central-laboratory method/version register.
    c = case.new_page(
        "Laboratory method, units, and report-version register",
        subtitle="Analytical metadata is versioned independently from specimen custody",
        section_code="LAB / METHOD CONTROL",
    )
    method_headers = ["Accession / test", "Subject", "Method", "Units", "Report version", "Verified value / state", "Version note"]
    method_rows = [
        ["AC-76881 / PK", "014-003", "LC-MS/MS M-204.7", "ng/mL", "Final v1", "Accepted", "Custody exception separate"],
        ["NCL-4540 / potassium", "014-007", "ISE CHM-14", "mmol/L", "Final v1", "4.2", "Eligibility specimen"],
        ["NCL-4592 / potassium", "014-007", "ISE CHM-14", "mmol/L", "Final v1", "5.8 H", "AE trigger"],
        ["NCL-4627 / potassium", "014-007", "ISE CHM-14", "mmol/L", "Final v1", "4.6", "Repeat resolved"],
        ["NCL-4568 / HbA1c", "014-008", "HPLC A1C-9", "%", "Final v1", "8.2", "Receipt interface delayed"],
        ["AC-77152 / creatinine v1", "014-011", "Enzymatic CRE-3", "mg/dL", "Preliminary v1", "1.74 H", "Transcription superseded"],
        ["AC-77152 / creatinine v2", "014-011", "Enzymatic CRE-3", "mg/dL", "Final amended v2", "1.47 H", "Controls analytical value"],
        ["AC-77152 / eGFR", "014-011", "CKD-EPI 2021", "mL/min/1.73 m2", "Final amended v2", "54 L", "Derived from amended creatinine"],
        ["NCL-4691 / glucose", "014-016", "Hexokinase GLU-6", "mg/dL", "Final v1", "94", "Eligibility specimen"],
        ["SITE-016 / glucose", "014-016", "Meter GM-22", "mg/dL", "Source series", "62 to 91", "Point-of-care; not central lab"],
        ["NCL-4710 / PK", "014-014", "LC-MS/MS M-204.7", "ng/mL", "Final v1", "Accepted", "No analytical amendment"],
        ["NCL-4664 / chemistry", "014-012", "Panel CHM-22", "SI mixed", "Final v1", "Within ranges", "Waiver unrelated"],
    ]
    method_y = draw_table(c, 18, 675, [94, 47, 94, 68, 86, 89, 98], [method_headers, *method_rows], font_size=5.5, row_padding=2.8, zebra=True)
    draw_paragraph(c, "A report version can supersede an analytical value while leaving method identity, collection, receipt, and accession custody intact. Point-of-care meter values remain source observations and must not be relabeled as central-laboratory results.", 42, method_y - 20, 510, size=8.0, leading=11.0, color=MUTED)
    _gold_table(case, "Laboratory method, units, and report-version register", method_headers, method_rows, "Analytical versioning does not rewrite independent custody, and point-of-care results are not central-laboratory results.")
    _selected_table_region(case, "methods", "Laboratory method and version register", method_headers, method_rows, [
        ("AC-76881 / PK", "Method"), ("NCL-4592 / potassium", "Verified value / state"),
        ("AC-77152 / creatinine v1", "Report version"), ("AC-77152 / creatinine v1", "Verified value / state"),
        ("AC-77152 / creatinine v2", "Report version"), ("AC-77152 / creatinine v2", "Verified value / state"),
        ("AC-77152 / eGFR", "Method"), ("AC-77152 / eGFR", "Verified value / state"),
        ("SITE-016 / glucose", "Method"), ("SITE-016 / glucose", "Version note"),
    ], consequential=[("AC-77152 / creatinine v2", "Verified value / state"), ("SITE-016 / glucose", "Version note")])
    _facts(case, "method-rule", "Laboratory versioning rule", "text", [
        ("version", "A report amendment can supersede an analytical value without changing independent specimen custody.", 2),
        ("poc", "Point-of-care meter values must not be relabeled as central-laboratory results.", 2),
    ], budget=1, primary_axis="source_precedence")

    # 32 - mixed calibration certificate and native service events.
    c = case.new_page(
        "RX2-441 calibration certificate and service lineage",
        subtitle="Mixed source: certificate image plus repository service audit",
        section_code="PHARMACY / CALIBRATION",
    )
    cert_scan = _scan_document(
        "REFRIGERATOR CALIBRATION CERTIFICATE",
        "Device RX2-441 | Site 014 RX-2 | Certificate CAL-441-2026-05",
        [
            ("Calibration result", ["Three-point as-left verification completed 12 May 2026 at 14:10: nominal 2.0 C observed 2.1 C; nominal 5.0 C observed 5.0 C; nominal 8.0 C observed 7.9 C. All points passed the plus or minus 0.3 C acceptance limit."]),
            ("Service-history coverage", ["Certificate review includes the controller reset performed 18 Apr 2026 at 13:18 under service ticket SV-8821. No sensor replacement occurred. Next calibration due 12 Nov 2026."]),
        ],
        controls=[
            ("As-left calibration passed", "checked"),
            ("18 Apr service reset covered", "checked"),
            ("Sensor replaced", "unchecked"),
            ("Certificate provisional", "unchecked"),
        ],
        signatures=["Technician O. Gill 12 May 14:26; metrology reviewer V. Chen 12 May 15:18. Certificate issued 12 May 15:24."],
        seed=1732,
        width=1900,
        height=960,
        form_code="CAL-441-2026-05 / FINAL",
    )
    _place_mixed_scan(c, cert_scan, y=408, height=262)
    service_headers = ["Repository event", "Timestamp", "Actor", "Object / state", "Evidence effect"]
    service_rows = [
        ["Vendor upload", "12 May 16:07", "O. Gill", "CAL-441 PDF", "Quarantine ingest"],
        ["Malware and hash check", "12 May 16:14", "System", "SHA-256 7a91...c204", "Passed"],
        ["Pharmacy review", "12 May 16:28", "RP", "Device RX2-441", "Service date matched"],
        ["CAPA evidence link", "12 May 16:36", "RP", "C-02 / A-202", "Certificate attached"],
        ["Monitor verification", "12 May 16:42", "LS", "CAL-441 final", "A-202 evidenced"],
        ["Deadline comparison", "12 May 17:00", "System", "C-02 due", "Evidence 18 min early"],
    ]
    draw_label(c, "Native repository service audit", 42, 378)
    draw_table(c, 38, 363, [118, 92, 72, 112, 116], [service_headers, *service_rows], font_size=6.45, zebra=True)
    gold_service_rows = [[_expand_protocol_dates(value) for value in row] for row in service_rows]
    case.add_gold("Page 32 - RX2-441 calibration certificate and service lineage", "Certificate CAL-441-2026-05 for device RX2-441 passed all three as-left points: observed 2.1 C, 5.0 C, and 7.9 C at nominal 2.0 C, 5.0 C, and 8.0 C. It covers the 2026-04-18 controller reset under SV-8821, records no sensor replacement, and is final rather than provisional. As-left calibration passed and 18 Apr service reset covered are checked. Sensor replaced and Certificate provisional are unchecked. The certificate was issued at 15:24 on 2026-05-12.\n\n" + markdown_table(service_headers, gold_service_rows))
    _facts(case, "cal-form", "Scanned calibration certificate", "form", [
        ("passed", "As-left calibration passed is checked.", 2, ("As-left calibration passed", "checked")),
        ("reset", "18 Apr service reset covered is checked.", 2, ("18 Apr service reset covered", "checked")),
        ("sensor", "Sensor replaced is unchecked.", 1, ("Sensor replaced", "unchecked")),
        ("provisional", "Certificate provisional is unchecked.", 1, ("Certificate provisional", "unchecked")),
        ("points", "RX2-441 observed 2.1 C, 5.0 C, and 7.9 C at nominal 2.0 C, 5.0 C, and 8.0 C respectively."),
    ], budget=2, primary_axis="low_quality_scan", secondary_axes=("form_state",))
    _selected_table_region(case, "cal-audit", "Native calibration evidence audit", service_headers, service_rows, [
        ("Pharmacy review", "Object / state"), ("CAPA evidence link", "Evidence effect"),
        ("Monitor verification", "Timestamp"), ("Monitor verification", "Evidence effect"),
        ("Deadline comparison", "Evidence effect"),
    ], budget=1, consequential=[("Monitor verification", "Evidence effect")])
    # 33 - native consent-version and re-consent applicability ledger.
    c = case.new_page(
        "Consent-version transition and applicability ledger",
        subtitle="Version history, subject notification, and protocol-specific applicability",
        section_code="CONSENT / VERSION",
    )
    consent_headers = ["Subject", "Initial ICF", "Change trigger", "Notification", "Re-consent state", "Optional / translated component", "Evidence locator"]
    consent_rows = [
        ["014-002", "v6.0 / 05 Apr", "None before cut", "Not required", "Current", "Biobank accepted", "ICF-002-V6"],
        ["014-003", "v6.0 / 07 Apr", "Safety letter SL-12", "30 Apr 10:12", "Acknowledged; no new signature", "Biobank declined", "ACK-003-SL12"],
        ["014-004", "v6.0 / 10 Apr", "Withdrawal", "24 Apr 10:11", "No re-consent after ET", "Biobank declined", "ET-004"],
        ["014-005", "v6.0 / 12 Apr", "None before cut", "Not required", "Current", "Biobank accepted", "ICF-005-V6"],
        ["014-007", "v6.0 / 18 Apr", "Safety letter SL-12", "30 Apr 11:03", "Acknowledged; no new signature", "Biobank accepted", "ACK-007-SL12"],
        ["014-008", "v6.0 / 20 Apr", "None before cut", "Not required", "Current", "Biobank declined", "ICF-008-V6"],
        ["014-009", "v6.0 / 19 Apr", "Safety letter SL-12", "01 May 08:22", "Acknowledged; no new signature", "Biobank declined", "ACK-009-SL12"],
        ["014-011", "v6.0 / 26 Apr", "None before cut", "Not required", "Current", "Biobank accepted", "ICF-011-V6"],
        ["014-012", "v6.0 / 28 Apr", "Translated diary need", "28 Apr 10:20", "Main ICF current", "Diary waiver W-14; biobank declined", "W14 / ICF-012-V6"],
        ["014-013", "v6.0 / 29 Apr", "Lost contact", "Attempted 05 May", "Unable to notify", "Biobank declined", "FU-013"],
        ["014-014", "v6.0 / 01 May", "None before cut", "Not required", "Current", "Biobank accepted", "ICF-014-V6"],
        ["014-016", "v6.0 / 04 May", "Masking review", "Not a consent trigger", "Current", "Biobank declined", "ICF-016-V6"],
    ]
    consent_y = draw_table(c, 18, 675, [48, 68, 93, 78, 104, 124, 61], [consent_headers, *consent_rows], font_size=5.5, row_padding=2.8, zebra=True)
    draw_paragraph(c, "Safety-letter acknowledgment, re-consent, optional-component choice, translated-diary accommodation, and study withdrawal are separate states. W-14 addresses diary language support and does not replace or translate the main ICF.", 42, consent_y - 20, 510, size=8.0, leading=11.0, color=MUTED)
    _gold_table(case, "Consent-version transition and applicability ledger", consent_headers, consent_rows, "Safety-letter acknowledgment, re-consent, optional-component choice, translated-diary accommodation, and study withdrawal are separate states. W-14 addresses translated-diary support and does not replace or translate the main ICF.")
    _selected_table_region(case, "consent-ledger", "Consent-version applicability ledger", consent_headers, consent_rows, [
        ("014-003", "Re-consent state"), ("014-004", "Re-consent state"),
        ("014-009", "Notification"), ("014-012", "Re-consent state"),
        ("014-012", "Optional / translated component"), ("014-013", "Re-consent state"),
        ("014-016", "Change trigger"), ("014-016", "Notification"),
    ], consequential=[("014-012", "Optional / translated component"), ("014-013", "Re-consent state")])
    _facts(case, "consent-separation", "Consent-state separation", "text", [
        ("w14", "Waiver W-14 addresses translated diary support and does not replace or translate the main ICF.", 2),
        ("states", "Safety-letter acknowledgment, re-consent, optional-component choice, and withdrawal are separate states."),
    ], budget=1, primary_axis="long_context_coherence")

    # 34 - native protocol-amendment implementation evidence.
    c = case.new_page(
        "Protocol Amendment 6 implementation ledger",
        subtitle="Site activation controls and evidence of implementation before enrollment",
        section_code="REGULATORY / AMENDMENT",
    )
    amend_headers = ["Control", "Requirement", "Owner", "Target", "Evidence timestamp", "Evidence object", "Status / exception"]
    amend_rows = [
        ["A6-01", "IRB approval filed", "MK", "22 Mar", "21 Mar 16:44", "IRB-204-A6", "Complete"],
        ["A6-02", "PI training", "NR", "24 Mar", "23 Mar 09:32", "TR-A6-NR", "Complete"],
        ["A6-03", "Coordinator training", "MK", "24 Mar", "23 Mar 11:18", "TR-A6-MK", "Complete"],
        ["A6-04", "Pharmacy manual v4", "RP", "25 Mar", "24 Mar 14:06", "PHM-V4-RP", "Complete"],
        ["A6-05", "ICF v6.0 release", "MK", "27 Mar", "26 Mar 10:22", "ICF-V6-REL", "Complete"],
        ["A6-06", "eCRF ECG field update", "AT", "28 Mar", "28 Mar 18:42", "ECG-R6-DEP", "Complete"],
        ["A6-07", "ePRO build validation", "MK", "29 Mar", "29 Mar 15:05", "EPRO-UAT-14", "Complete"],
        ["A6-08", "Lab manual acknowledgment", "MK", "29 Mar", "30 Mar 08:14", "LABM-V6-MK", "1 day late; accepted"],
        ["A6-09", "Delegation update", "NR", "31 Mar", "31 Mar 09:26", "DL-014-R6", "Complete"],
        ["A6-10", "Screening tools replace", "MK", "31 Mar", "31 Mar 12:40", "SCR-A6-PACK", "Complete"],
        ["A6-11", "Old consent quarantine", "MK", "01 Apr", "01 Apr 08:18", "ICF-V5-Q", "Complete"],
        ["A6-12", "Readiness signoff", "NR", "02 Apr", "02 Apr 17:06", "SIV-A6-CLOSE", "Complete before first consent"],
    ]
    amend_y = draw_table(c, 20, 675, [48, 125, 48, 58, 86, 96, 127], [amend_headers, *amend_rows], font_size=5.5, row_padding=2.8, zebra=True)
    amend_note_y = draw_paragraph(c, "The one-day late laboratory-manual acknowledgment is retained as implementation history. Readiness signoff occurred before the first subject consent on 3 April; the late acknowledgment does not imply an unapproved enrollment.", 42, amend_y - 20, 510, size=8.0, leading=11.0, color=MUTED)
    amendment_review_note = (
        "Implementation was evaluated by control, not by a single completion percentage. The eCRF deployment, consent release, delegation update, old-consent quarantine, and readiness signoff each required their own evidence object. "
        "A6-08 was accepted as a one-day documentation lateness because the laboratory manual itself was available before screening, while A6-12 remained the gate for enrollment. "
        "No row authorizes retroactive substitution of Amendment 5 materials after the 2 April readiness signature."
    )
    draw_paragraph(c, amendment_review_note, 42, amend_note_y - 7, 510, size=7.7, leading=10.5, color=INK)
    _gold_table(case, "Protocol Amendment 6 implementation ledger", amend_headers, amend_rows, "A6-08 was one day late but accepted; A6-12 readiness signoff on 02 Apr 2026 preceded first consent on 03 Apr 2026. " + amendment_review_note)
    _selected_table_region(case, "amendment", "Protocol Amendment 6 implementation ledger", amend_headers, amend_rows, [
        ("A6-01", "Evidence timestamp"), ("A6-04", "Evidence object"),
        ("A6-06", "Requirement"), ("A6-06", "Evidence timestamp"),
        ("A6-08", "Status / exception"), ("A6-11", "Evidence object"),
        ("A6-12", "Evidence timestamp"), ("A6-12", "Status / exception"),
    ], consequential=[("A6-08", "Status / exception"), ("A6-12", "Status / exception")])
    _facts(case, "amendment-time", "Amendment implementation chronology", "text", [
        ("late", "The lab-manual acknowledgment was one day late but accepted."),
        ("ready", "Readiness signoff on 2026-04-02 preceded first subject consent on 2026-04-03.", 2),
        ("gate", "A6-12 readiness signoff remained the enrollment gate."),
    ], budget=1, primary_axis="long_context_coherence")

    # 35 - native safety follow-up contact and medical-review chronology.
    c = case.new_page(
        "Safety follow-up communication chronology",
        subtitle="Contact attempts, clinical evidence, and medical-review states remain distinct",
        section_code="SAFETY / FOLLOW-UP",
    )
    follow_headers = ["Event / subject", "Timestamp", "Channel", "Initiator", "Clinical content", "Resulting state", "Next obligation"]
    follow_rows = [
        ["AE-014-01 initial / 014-004", "24 Apr 18:05", "Phone", "NR", "Dizziness improved after withdrawal", "Follow-up obtained", "Confirm stop date"],
        ["AE-014-01 resolution / 014-004", "27 Apr 09:02", "Clinic", "MK", "Symptoms resolved", "Resolution dated 27 Apr", "Safety reconciliation"],
        ["AE-014-03 arrange / 014-007", "19 Apr 08:44", "Phone", "MK", "Repeat potassium arranged", "Contact complete", "Obtain final result"],
        ["AE-014-03 result / 014-007", "03 May 09:18", "Portal", "MK", "Potassium 4.6 mmol/L", "Resolved 03 May", "Close follow-up"],
        ["AE-014-04 request / 014-011", "28 Apr 09:10", "Query", "AT", "Repeat chemistry requested", "Evidence absent", "Receive amended report"],
        ["AE-014-04 review / 014-011", "09 May 08:06", "Portal", "NR", "Amended creatinine reviewed", "Medical review complete", "Close Q-88"],
        ["AE-014-05 call / 014-016", "04 May 18:16", "Phone", "NR", "Glucose 88; no symptoms", "Safety call complete", "Masking assessment"],
        ["AE-014-05 day-1 / 014-016", "05 May 08:20", "Phone", "MK", "No recurrent symptoms", "Day-1 follow-up complete", "PI causality review"],
        ["AE-014-07 / 014-009", "04 May 17:26", "Phone", "MK", "Injection-site pain resolved", "Resolution confirmed", "No further call"],
        ["AE-014-08 ticket / 014-014", "04 May 12:16", "Helpdesk", "MK", "Missed diary entries; PIN expired", "Device issue open", "Retrain subject"],
        ["AE-014-08 evidence / 014-014", "08 May 14:03", "Console", "MK", "Competency source attached", "Evidence attached", "Console closure"],
        ["FU-013 / 014-013", "05 May 17:20", "Phone/SMS", "MK", "Third contact attempt unanswered", "Lost to follow-up", "Certified letter"],
    ]
    follow_y = draw_table(c, 18, 675, [87, 71, 55, 49, 134, 98, 82], [follow_headers, *follow_rows], font_size=5.5, row_padding=2.7, zebra=True)
    draw_paragraph(c, "A completed call does not prove medical review, query closure, or deviation closure. Each row records only the state produced by that event; later source must supply any subsequent transition.", 42, follow_y - 20, 510, size=8.0, leading=11.0, color=MUTED)
    _gold_table(case, "Safety follow-up communication chronology", follow_headers, follow_rows, "A completed contact does not itself prove medical review or administrative closure. Each event records only the resulting state at its timestamp.")
    _selected_table_region(case, "safety-follow", "Safety follow-up chronology", follow_headers, follow_rows, [
        ("AE-014-01 resolution / 014-004", "Resulting state"), ("AE-014-03 result / 014-007", "Clinical content"),
        ("AE-014-04 request / 014-011", "Resulting state"), ("AE-014-04 review / 014-011", "Next obligation"),
        ("AE-014-05 call / 014-016", "Clinical content"), ("AE-014-05 call / 014-016", "Next obligation"),
        ("AE-014-08 evidence / 014-014", "Resulting state"), ("FU-013 / 014-013", "Resulting state"),
    ], consequential=[("AE-014-05 call / 014-016", "Next obligation"), ("FU-013 / 014-013", "Resulting state")])
    _facts(case, "follow-rule", "Safety state-transition rule", "text", [
        ("contact", "A completed safety contact does not by itself prove medical review, query closure, or deviation closure.", 2),
        ("event", "Each event row records only the state produced at that timestamp."),
    ], budget=1, primary_axis="long_context_coherence")

    # 36 - mixed ePRO exception report and diary continuity table.
    c = case.new_page(
        "ePRO exception report and diary continuity",
        subtitle="Mixed source: signed exception image plus native day-level export",
        section_code="ePRO / CONTINUITY",
    )
    exception_scan = _scan_document(
        "ePRO DATA EXCEPTION ASSESSMENT",
        "Subject 014-014 | Device EP-441 | Exception EX-551 | Assessed 09 May 2026",
        [
            ("Missing interval", ["Daily symptom diaries due 02 May and 03 May were not transmitted. The activation PIN had expired; device logs show no successful login during the interval."]),
            ("Data-integrity assessment", ["No site-user session, proxy entry, backdated entry, or paper transcription was found. Retraining restored prospective entry beginning 08 May. Missing diary days remain missing and are not reconstructed from interview."]),
        ],
        controls=[
            ("02 May diary received", "unchecked"),
            ("03 May diary received", "unchecked"),
            ("Proxy entry detected", "unchecked"),
            ("Backfill permitted", "disabled"),
            ("Prospective use restored", "checked"),
        ],
        signatures=["Assessment MK 09 May 09:18; data-integrity review AT 09 May 10:04; monitor concurrence LS 09 May 10:12."],
        seed=1736,
        width=1900,
        height=960,
        form_code="EPRO-EX-05 / SIGNED",
    )
    _place_mixed_scan(c, exception_scan, y=408, height=262)
    diary_headers = ["Diary date", "Login", "Entry state", "Symptom score", "Sync timestamp", "Audit note"]
    diary_rows = [
        ["01 May", "Failed 10:21", "No entry", "-", "-", "Expired PIN"],
        ["02 May", "None", "Missing", "-", "-", "No successful session"],
        ["03 May", "None", "Missing", "-", "-", "No successful session"],
        ["04 May", "None", "Not due after lock", "-", "-", "Helpdesk ticket open"],
        ["08 May practice", "13:31", "Practice accepted", "2 corrected to 1", "13:47", "Correction before submit"],
        ["08 May daily", "19:06", "Submitted", "1", "19:08", "First prospective diary"],
        ["09 May daily", "18:42", "Submitted", "0", "18:44", "Own credentials"],
    ]
    draw_label(c, "Native day-level diary export", 42, 378)
    draw_table(c, 36, 363, [83, 78, 105, 85, 86, 73], [diary_headers, *diary_rows], font_size=6.15, zebra=True)
    case.add_gold("Page 36 - ePRO exception report and diary continuity", "Backfill permitted is disabled.\n\nFor subject 014-014, 02 May diary received and 03 May diary received are unchecked. Proxy entry detected is unchecked. Prospective use restored is checked. Missing days remain missing and are not reconstructed.\n\n" + markdown_table(diary_headers, diary_rows))
    _facts(case, "exception-form", "Scanned ePRO exception assessment", "form", [
        ("may02", "02 May diary received is unchecked.", 2, ("02 May diary received", "unchecked")),
        ("may03", "03 May diary received is unchecked.", 2, ("03 May diary received", "unchecked")),
        ("proxy", "Proxy entry detected is unchecked.", 2, ("Proxy entry detected", "unchecked")),
        ("backfill", "Backfill permitted is disabled.", 2, ("Backfill permitted", "disabled")),
        ("restored", "Prospective use restored is checked.", 1, ("Prospective use restored", "checked")),
    ], budget=2, primary_axis="low_quality_scan", secondary_axes=("form_state",))
    _selected_table_region(case, "diary", "Native ePRO diary continuity", diary_headers, diary_rows, [
        ("02 May", "Entry state"), ("03 May", "Audit note"),
        ("08 May practice", "Symptom score"), ("08 May practice", "Sync timestamp"),
        ("08 May daily", "Entry state"), ("09 May daily", "Audit note"),
    ], budget=1, consequential=[("02 May", "Entry state"), ("03 May", "Audit note")])
    # 37 - native accountability transaction continuation.
    c = case.new_page(
        "Investigational-product transaction ledger",
        subtitle="Receipt, assignment, dispense, return, quarantine, and transfer are distinct movements",
        section_code="PHARMACY / TRANSACTIONS",
    )
    tx_headers = ["Transaction", "Timestamp", "Kit", "Subject", "Movement", "Quantity / balance", "Source / resulting state"]
    tx_rows = [
        ["TX-101", "06 Apr 14:26", "K-204-153", "Unassigned", "Receipt", "+30 / 30", "PS-778; locator corrected"],
        ["TX-118", "18 Apr 08:54", "K-204-153", "014-007", "RTS assignment", "0 / 30", "Assignment only"],
        ["TX-119", "18 Apr 10:10", "K-204-153", "014-007", "Quarantine", "0 / 30", "QG-19 / shelf Q1"],
        ["TX-120", "18 Apr 14:02", "K-204-153", "014-007", "Disposition entry", "0 / 30", "Do not dose source"],
        ["TX-121", "18 Apr 14:12", "K-204-153", "014-007", "Dispense attempt", "0 / 30", "Blocked; no custody transfer"],
        ["TX-144", "02 May 09:01", "K-204-158", "014-008", "Dispense", "-30 / 0", "Subject custody"],
        ["TX-152", "05 May 09:18", "K-204-146", "014-003", "Expected return", "0 / 0", "Kit not presented"],
        ["TX-153", "06 May 11:20", "K-204-160", "014-009", "Return", "+3 / 3", "Count witnessed JD"],
        ["TX-158", "08 May 07:52", "K-204-171", "014-011", "Accountability review", "0 / 0", "Subject custody"],
        ["TX-161", "08 May 14:35", "K-204-153", "014-007", "Physical count", "0 / 30", "Quarantine verified"],
        ["TX-167", "09 May 12:24", "K-204-153", "014-007", "CAPA link", "0 / 30", "Calibration evidence assigned"],
        ["TX-172", "09 May 15:52", "K-204-146", "014-003", "Contact action", "0 / 0", "Three attempts assigned"],
        ["TX-188", "12 May 16:42", "K-204-153", "014-007", "Evidence verification", "0 / 30", "Calibration accepted"],
        ["TX-194", "13 May 10:18", "K-204-153", "014-007", "Sponsor return", "-30 / 0", "Transfer SRN-551 sealed"],
    ]
    tx_y = draw_table(c, 16, 675, [51, 74, 67, 56, 86, 89, 173], [tx_headers, *tx_rows], font_size=5.5, row_padding=2.5, zebra=True)
    draw_paragraph(c, "A randomization assignment or attempted dispense with zero movement does not establish subject custody. For K-204-153, the balance remains 30 through calibration verification and becomes zero only at the documented sponsor-return transfer on 13 May.", 42, tx_y - 18, 510, size=7.8, leading=10.6, color=MUTED)
    _gold_table(case, "Investigational-product transaction ledger", tx_headers, tx_rows, "Assignment and blocked dispense do not establish subject custody. K-204-153 remains at balance 30 until sponsor return on 13 May.")
    _selected_table_region(case, "transactions", "Investigational-product transaction ledger", tx_headers, tx_rows, [
        ("TX-101", "Quantity / balance"), ("TX-119", "Source / resulting state"),
        ("TX-121", "Quantity / balance"), ("TX-121", "Source / resulting state"),
        ("TX-152", "Source / resulting state"), ("TX-161", "Quantity / balance"),
        ("TX-188", "Source / resulting state"), ("TX-194", "Quantity / balance"),
        ("TX-194", "Source / resulting state"),
    ], consequential=[("TX-121", "Source / resulting state"), ("TX-194", "Quantity / balance")])
    _facts(case, "transaction-rule", "Accountability movement rule", "text", [
        ("assignment", "An RTS assignment does not establish subject custody."),
        ("balance", "K-204-153 remains at balance 30 through calibration verification and reaches balance 0 only on sponsor return at 2026-05-13 10:18.", 2),
    ], budget=1, primary_axis="long_context_coherence")

    # 38 - full-page scan: role-specific training and delegation correction.
    c = case.new_page(
        "Role-specific training and delegation correction",
        subtitle="Scanned staff source | Training, delegation, and system access are separate",
        section_code="STAFF / TRAINING",
    )
    scan = _scan_document(
        "ROLE-SPECIFIC TRAINING AND DELEGATION CORRECTION",
        "HTX-204 | Site 014 | Review completed 10 May 2026",
        [
            ("Ravi Patel - unblinded pharmacist", [
                "Protocol Amendment 6 pharmacy module completed 24 Mar 2026 at 14:06. Delegated receipt, temperature review, accountability, quarantine, disposition execution after sponsor instruction, and destruction documentation.",
                "RTS restricted access role PHARM-U granted 24 Mar at 16:18. Annual GCP remains current through 31 Jan 2027.",
            ]),
            ("Jaya Das - pharmacy witness", [
                "Count-and-seal verification module completed 25 Mar 2026 at 09:14. Delegated independent count, external-seal observation, and witness signature only.",
                "The original worksheet incorrectly included product disposition decision. NR crossed that task on 26 Mar because JD has no sponsor-response review or disposition authority. RTS code-view access is disabled for this role.",
            ]),
            ("Maya Kapoor - blinded coordinator", [
                "Source entry, consent discussion, ePRO training, and query-response preparation completed 23 Mar. No pharmacy disposition or treatment-code access is delegated.",
            ]),
        ],
        controls=[
            ("RP pharmacy module complete", "checked"),
            ("RP restricted RTS role active", "checked"),
            ("JD count-and-seal module complete", "checked"),
            ("JD product disposition authority", "crossed"),
            ("JD treatment-code access", "disabled"),
            ("MK treatment-code access", "disabled"),
        ],
        corrections=[
            ("JD delegated product disposition decision", "JD delegated witness count and seal verification only; no disposition decision", "NR 26 Mar 10:08"),
        ],
        signatures=[
            "Training records verified by LS 10 May 2026 09:22. Delegation correction certified by NR 26 Mar 10:08 and reverified 10 May 09:28.",
        ],
        seed=1738,
        form_code="TR-DLG-12 / CORRECTED",
    )
    _place_full_scan(c, scan)
    _gold_scan(case, "Role-specific training and delegation correction", "JD treatment-code access is disabled.\n\nRP pharmacy module complete and RP restricted RTS role active are checked. JD count-and-seal module complete is checked. JD product disposition authority is crossed. MK treatment-code access is disabled. The original JD disposition-decision delegation is corrected to witness count and seal verification only, with no disposition decision, by NR on 2026-03-26 at 10:08.")
    _facts(case, "staff-training", "Scanned role-specific training and delegation correction", "form", [
        ("rp-module", "RP pharmacy module complete is checked.", 1, ("RP pharmacy module complete", "checked")),
        ("rp-rts", "RP restricted RTS role active is checked.", 1, ("RP restricted RTS role active", "checked")),
        ("jd-module", "JD count-and-seal module complete is checked.", 1, ("JD count-and-seal module complete", "checked")),
        ("jd-disposition", "JD product disposition authority is crossed.", 2, ("JD product disposition authority", "crossed")),
        ("jd-code", "JD treatment-code access is disabled.", 2, ("JD treatment-code access", "disabled")),
        ("mk-code", "MK treatment-code access is disabled.", 2, ("MK treatment-code access", "disabled")),
        ("correction", "NR corrected JD's delegation to witness count and seal verification only, with no disposition decision, on 2026-03-26 at 10:08.", 2),
    ], budget=2, primary_axis="low_quality_scan", secondary_axes=("form_state", "source_precedence"))

    # 39 - native query audit trail with multiple transitions per entity.
    c = case.new_page(
        "Data-query state-transition audit trail",
        subtitle="Chronological events retain provisional, accepted, updated, and closed states",
        section_code="QUERY / AUDIT",
    )
    qa_headers = ["Audit event", "Timestamp", "Query", "Subject", "Actor", "Transition", "Evidence / note"]
    qa_rows = [
        ["EV-7701", "22 Apr 16:05", "Q-77", "014-003", "AT", "Created -> Open", "W2 ECG mismatch"],
        ["EV-7708", "06 May 18:04", "Q-77", "014-003", "MK", "Draft saved", "Yes; tracing requested"],
        ["EV-7722", "09 May 09:14", "Q-77", "014-003", "AT", "Response accepted", "Signed DCF reviewed"],
        ["EV-7735", "10 May 10:24", "Q-77", "014-003", "AT", "Production field updated", "ECG not performed"],
        ["EV-7736", "10 May 10:41", "Q-77", "014-003", "AT", "Open -> Closed", "Audit screenshot linked"],
        ["EV-7810", "23 Apr 10:20", "Q-84", "014-008", "AT", "Created -> Open", "Central receipt absent"],
        ["EV-7861", "09 May 08:18", "Q-88", "014-011", "NR", "PI review posted", "Amended report acknowledged"],
        ["EV-7863", "09 May 09:02", "Q-88", "014-011", "AT", "Open -> Closed", "Final amended report"],
        ["EV-7904", "08 May 14:03", "Q-91", "014-014", "MK", "Evidence attached", "Competency source"],
        ["EV-7907", "09 May 10:16", "Q-91", "014-014", "AT", "Answered -> Closed", "Prospective use restored"],
        ["EV-8001", "07 May 08:30", "Q-86", "014-009", "AT", "Created -> Open", "Visit-window calculation"],
        ["EV-8032", "11 May 10:42", "Q-86", "014-009", "MK", "Signed calculation uploaded", "Deviation link active"],
        ["EV-8034", "11 May 11:15", "Q-86", "014-009", "AT", "Open -> Closed", "Minor deviation retained"],
        ["EV-8102", "05 May 11:40", "Q-93", "014-016", "AT", "Created -> Open", "Masking assessment absent"],
        ["EV-8160", "13 May 15:26", "Q-93", "014-016", "NR", "Signed response uploaded", "Assessment MA-016"],
        ["EV-8164", "14 May 08:22", "Q-93", "014-016", "AT", "Open -> Closed", "No treatment code disclosed"],
    ]
    qa_y = draw_table(c, 16, 675, [57, 73, 45, 54, 41, 124, 202], [qa_headers, *qa_rows], font_size=5.5, row_padding=2.4, zebra=True)
    draw_paragraph(c, "A draft response, accepted response, production-field update, and administrative closure are four different transitions. The event sequence must be preserved per query; a later closure does not erase the earlier open duration or provisional text.", 42, qa_y - 17, 510, size=7.7, leading=10.4, color=MUTED)
    _gold_table(case, "Data-query state-transition audit trail", qa_headers, qa_rows, "A draft response, accepted response, production-field update, and administrative closure are four different transitions. The event sequence must be preserved per query; a later closure does not erase the earlier open duration or provisional text.")
    _selected_table_region(case, "query-audit", "Data-query state-transition audit trail", qa_headers, qa_rows, [
        ("EV-7708", "Transition"), ("EV-7708", "Evidence / note"),
        ("EV-7722", "Timestamp"), ("EV-7735", "Transition"),
        ("EV-7736", "Timestamp"), ("EV-7907", "Transition"),
        ("EV-8032", "Evidence / note"), ("EV-8034", "Timestamp"),
        ("EV-8160", "Evidence / note"), ("EV-8164", "Transition"),
    ], consequential=[("EV-7736", "Timestamp"), ("EV-8164", "Transition")])
    _facts(case, "query-transition-rule", "Query transition chronology", "text", [
        ("distinct", "Draft response, accepted response, production-field update, and administrative closure are distinct transitions.", 2),
        ("history", "Later query closure does not erase earlier open duration or provisional text."),
    ], budget=1, primary_axis="long_context_coherence")

    # 40 - native causality and clinical-decision review register.
    c = case.new_page(
        "Investigator safety and dosing decision register",
        subtitle="Clinical causality, dosing action, and masking impact are independently reviewed",
        section_code="PI / CLINICAL REVIEW",
    )
    decision_headers = ["Review", "Subject / event", "Source reviewed", "PI conclusion", "Signed", "Operational effect", "Separate pending item"]
    decision_rows = [
        ["DR-01", "014-004 / AE-01", "ET note + medication source", "Related dizziness; resolved 27 Apr", "27 Apr 09:24", "Study drug withdrawn", "Query stop-date reconcile"],
        ["DR-02", "014-007 / AE-03", "Potassium 5.8 -> 4.6", "Unrelated; resolved 03 May", "03 May 10:06", "No dose from K-204-153", "Calibration evidence"],
        ["DR-03", "014-011 / AE-04", "Amended creatinine 1.47", "Possible; grade 1", "09 May 08:06", "Continue follow-up", "Q-88 close"],
        ["DR-04", "014-016 / AE-05", "Dose sheet + glucose series", "Related; grade 2", "04 May 18:34", "Dose withheld", "Masking assessment"],
        ["DR-05", "014-016 / discharge", "09:05 observation", "Stable for escorted discharge", "04 May 09:12", "Same-day discharge", "18:16 safety call"],
        ["DR-06", "014-003 / ECG", "Corrected eCRF + DCF", "ECG not performed", "09 May 08:42", "Field correction", "Repository update"],
        ["DR-07", "014-009 / window", "Signed calculation", "Minor deviation", "09 May 11:22", "Visit usable", "Production upload"],
        ["DR-08", "014-014 / ePRO", "Competency + exception", "Missing days not backfilled", "09 May 10:12", "Prospective use", "Console closure"],
        ["DR-09", "014-012 / W-14", "Consent + waiver", "Diary accommodation only", "08 May 12:06", "Main ICF unchanged", "Waiver expiration"],
        ["DR-10", "014-003 / custody", "SH-204-45 receipt", "Analytical use acceptable", "23 Apr 17:10", "PK result usable", "CE-204-12 closure"],
        ["DR-11", "014-016 / masking", "Restricted access audit", "Clinical causality unaffected", "10 May 10:28", "No dose change", "Impact assessment unsigned"],
        ["DR-12", "Site 014 / CAPA", "Final CAPA-014-02", "Actions proportionate", "09 May 12:14", "Assignments active", "Effectiveness check"],
    ]
    decision_y = draw_table(c, 16, 675, [47, 88, 109, 129, 72, 81, 70], [decision_headers, *decision_rows], font_size=5.5, row_padding=2.6, zebra=True)
    decision_note_y = draw_paragraph(c, "The masking-review row does not reopen the signed dose decision or causality assessment. It asks whether restricted-role information reached blinded decision-makers. Clinical conclusions and masking impact must therefore remain separate in the reconstruction.", 42, decision_y - 18, 510, size=7.9, leading=10.8, color=MUTED)
    decision_review_note = (
        "For subject 014-016, the low glucose, rescue carbohydrate, and dose-withheld decision were recorded before the coordinator wrote the restricted-role phrase at 18:29. "
        "DR-04 and DR-05 therefore remain clinical decisions supported by contemporaneous measurements, while DR-11 records only that masking impact was still unsigned on 10 May. "
        "A later masking conclusion may resolve Q-93 without changing the earlier glucose series, discharge decision, dose action, or AE causality classification."
    )
    draw_paragraph(c, decision_review_note, 42, decision_note_y - 7, 510, size=7.7, leading=10.5, color=INK)
    _gold_table(case, "Investigator safety and dosing decision register", decision_headers, decision_rows, "The masking-review row does not reopen the signed dose decision or causality assessment. It asks whether restricted-role information reached blinded decision-makers. Clinical conclusions and masking impact must therefore remain separate in the reconstruction. " + decision_review_note)
    _selected_table_region(case, "pi-decisions", "Investigator clinical-decision register", decision_headers, decision_rows, [
        ("DR-02", "PI conclusion"), ("DR-02", "Operational effect"),
        ("DR-04", "PI conclusion"), ("DR-04", "Operational effect"),
        ("DR-06", "PI conclusion"), ("DR-08", "PI conclusion"),
        ("DR-09", "Operational effect"), ("DR-11", "PI conclusion"),
        ("DR-11", "Separate pending item"), ("DR-12", "Separate pending item"),
    ], consequential=[("DR-04", "Operational effect"), ("DR-11", "Separate pending item")])
    _facts(case, "decision-separation", "Clinical and masking decision separation", "text", [
        ("masking", "Masking review asks whether restricted-role information reached blinded decision-makers."),
        ("separate", "Masking impact does not reopen the signed dose decision or clinical causality assessment.", 2),
        ("sequence", "Subject 014-016's clinical measurements and dose-withheld decision preceded the 18:29 restricted-role phrase.", 2),
    ], budget=1, primary_axis="source_precedence")

    # 41 - native evidence-request and intake queue.
    c = case.new_page(
        "Evidence request and intake queue",
        subtitle="Requested, received, verified, rejected, and superseded are non-equivalent states",
        section_code="MONITOR / EVIDENCE",
    )
    request_headers = ["Request", "Object requested", "Issued", "Due", "Receipt event", "Verification state", "Residual blocker"]
    request_rows = [
        ["ER-201", "Q-77 DCF + production audit", "09 May 12:24", "10 May 12:00", "10 May 10:31", "Verified 10:38", "None"],
        ["ER-202", "RX2-441 calibration certificate", "09 May 12:24", "12 May 17:00", "12 May 16:07", "Verified 16:42", "None"],
        ["ER-203", "Three K-204-146 contact attempts", "09 May 12:24", "13 May 15:00", "Two attempts by 13:00", "Incomplete", "Third attempt absent"],
        ["ER-204", "Corrected SH-204-45 receipt", "09 May 12:24", "11 May 12:00", "09 May 09:41", "Verified 09:48", "CE closure separate"],
        ["ER-205", "PI chemistry acknowledgment", "09 May 12:24", "09 May 17:00", "09 May 08:06", "Verified retrospectively", "None"],
        ["ER-206", "ePRO competency + exception", "09 May 12:24", "09 May 14:00", "09 May 10:12", "Verified 10:16", "None"],
        ["ER-207", "Masking assessment + Q-93", "09 May 12:24", "11 May 16:00", "Draft 11 May 15:18", "Rejected unsigned", "Signed assessment absent"],
        ["ER-207R", "Masking assessment signed", "11 May 15:24", "13 May 16:00", "13 May 15:26", "Verified 15:44", "Q-93 close separate"],
        ["ER-208", "Signed Q-86 calculation", "09 May 12:24", "11 May 12:00", "11 May 10:42", "Verified 10:58", "None"],
        ["ER-209", "Q-84 lab receipt interface", "09 May 13:06", "12 May 12:00", "Courier ticket only", "Insufficient", "Portal receipt absent"],
        ["ER-210", "K-204-153 sponsor-return note", "12 May 16:42", "14 May 12:00", "13 May 10:26", "Verified 11:04", "None"],
        ["ER-211", "FU-013 certified letter", "09 May 13:10", "15 May 17:00", "Not received", "Open", "Mail proof absent"],
    ]
    request_y = draw_table(c, 16, 675, [49, 148, 72, 70, 100, 89, 68], [request_headers, *request_rows], font_size=5.5, row_padding=2.6, zebra=True)
    request_note_y = draw_paragraph(c, "A draft can satisfy routing without satisfying evidence. A verified object may close its evidence request while a linked query, custody exception, or follow-up remains separately open. Superseding ER-207 with ER-207R preserves the rejected unsigned submission.", 42, request_y - 18, 510, size=7.9, leading=10.8, color=MUTED)
    queue_review_note = (
        "Verification time records completion of reviewer checks, not the earlier upload event. Rejected objects remain immutable in the intake history, and a revised due date requires an approved replacement obligation rather than an edited timestamp. "
        "For restricted pharmacy and masking artifacts, the submitting owner cannot substitute self-attestation for monitor or QA verification. A receipt event with an insufficient object therefore leaves the request open even when it arrived before the deadline."
    )
    draw_paragraph(c, queue_review_note, 42, request_note_y - 7, 510, size=7.7, leading=10.5, color=INK)
    _gold_table(case, "Evidence request and intake queue", request_headers, request_rows, "A draft can satisfy routing without satisfying evidence. A verified object may close its evidence request while a linked query, custody exception, or follow-up remains separately open. Superseding ER-207 with ER-207R preserves the rejected unsigned submission. " + queue_review_note)
    _selected_table_region(case, "evidence-queue", "Evidence request and intake queue", request_headers, request_rows, [
        ("ER-202", "Receipt event"), ("ER-202", "Verification state"),
        ("ER-203", "Verification state"), ("ER-203", "Residual blocker"),
        ("ER-204", "Residual blocker"), ("ER-207", "Verification state"),
        ("ER-207R", "Receipt event"), ("ER-207R", "Verification state"),
        ("ER-209", "Verification state"), ("ER-211", "Residual blocker"),
    ], consequential=[("ER-203", "Residual blocker"), ("ER-207", "Verification state"), ("ER-209", "Verification state")])
    _facts(case, "evidence-rule", "Evidence intake state rule", "text", [
        ("draft", "A draft can satisfy routing without satisfying the requested evidence."),
        ("separate", "A verified object may close its evidence request while a linked query or custody exception remains open.", 2),
        ("history", "ER-207R supersedes ER-207 without erasing the rejected unsigned submission."),
        ("verification-time", "Verification time records completion of reviewer checks rather than the upload event."),
    ], budget=1, primary_axis="long_context_coherence")

    # 42 - full-page scan: translated-diary waiver W-14.
    c = case.new_page(
        "Protocol waiver W-14 - translated diary accommodation",
        subtitle="Scanned signed waiver | Scope and expiration are field-specific",
        section_code="WAIVER / W-14",
    )
    scan = _scan_document(
        "PROTOCOL WAIVER W-14 - TRANSLATED DIARY ACCOMMODATION",
        "HTX-204 | Site 014 | Subject 014-012 | Approved 27 Apr 2026",
        [
            ("Request and rationale", [
                "The subject can complete the main English informed-consent discussion with interpreter support but requires a sponsor-controlled Hindi diary aid for daily symptom wording. The aid does not add, remove, or reinterpret protocol questions.",
                "Waiver applies only to the paper diary aid issued while certified ePRO Hindi text is unavailable. It does not waive main ICF v6.0, screening criteria, visit windows, safety reporting, or source-signature requirements.",
            ]),
            ("Controls", [
                "Use translation TD-HI-204 revision 1, issued as a paired English/Hindi booklet. Coordinator reads the English item identifier before the subject records the Hindi response. Completed pages are transcribed into ePRO by the subject during the next visit with an audit note.",
                "Authorization expires 31 May 2026 or on release of certified ePRO Hindi text, whichever occurs first. Sponsor medical monitor may revoke earlier in writing.",
            ]),
        ],
        controls=[
            ("Main ICF requirement waived", "unchecked"),
            ("Translated diary aid authorized", "checked"),
            ("Screening criteria waived", "unchecked"),
            ("Visit windows waived", "unchecked"),
            ("Subject proxy entry authorized", "unchecked"),
            ("Paired English/Hindi booklet required", "checked"),
        ],
        signatures=[
            "Requested MK 26 Apr 15:12; approved medical monitor D. Bose 27 Apr 08:48; PI acknowledgment NR 27 Apr 09:06.",
            "Expiration: 31 May 2026 or certified Hindi ePRO release, whichever occurs first.",
        ],
        seed=1742,
        form_code="W-14 / FINAL APPROVAL",
    )
    _place_full_scan(c, scan)
    _gold_scan(case, "Protocol waiver W-14 - translated diary accommodation", "Waiver W-14 for subject 014-012 authorizes translated diary aid TD-HI-204 revision 1 and requires a paired English/Hindi booklet. Main ICF requirement waived, screening criteria waived, visit windows waived, and subject proxy entry authorized are unchecked. Translated diary aid authorized and paired English/Hindi booklet required are checked. The waiver expires 2026-05-31 or when certified Hindi ePRO text is released, whichever occurs first. D. Bose approved it on 2026-04-27 at 08:48; NR acknowledged at 09:06.")
    _facts(case, "waiver", "Scanned translated-diary waiver W-14", "form", [
        ("icf", "Main ICF requirement waived is unchecked.", 2, ("Main ICF requirement waived", "unchecked")),
        ("diary", "Translated diary aid authorized is checked.", 2, ("Translated diary aid authorized", "checked")),
        ("criteria", "Screening criteria waived is unchecked.", 1, ("Screening criteria waived", "unchecked")),
        ("window", "Visit windows waived is unchecked.", 1, ("Visit windows waived", "unchecked")),
        ("proxy", "Subject proxy entry authorized is unchecked.", 2, ("Subject proxy entry authorized", "unchecked")),
        ("paired", "Paired English/Hindi booklet required is checked.", 1, ("Paired English/Hindi booklet required", "checked")),
        ("revision", "W-14 authorizes TD-HI-204 revision 1 for subject 014-012."),
        ("expiry", "W-14 expires on 2026-05-31 or certified Hindi ePRO release, whichever occurs first.", 2),
    ], budget=2, primary_axis="low_quality_scan", secondary_axes=("form_state", "source_precedence"))

    # 43 - native translated-diary controlled-copy log.
    c = case.new_page(
        "Translated-diary controlled-copy and transcription log",
        subtitle="Waiver W-14 implementation for subject 014-012",
        section_code="DIARY / W-14",
    )
    diarylog_headers = ["Event", "Timestamp", "Copy / day", "English item", "Hindi aid state", "Actor", "Audit result"]
    diarylog_rows = [
        ["Issue", "28 Apr 11:12", "TD-HI-204-014", "Paired booklet", "Rev 1 sealed", "MK", "Subject receipt signed"],
        ["Day 1", "28 Apr 20:04", "Diary 01", "SYM-01 severity", "Hindi response 1", "014-012", "Complete"],
        ["Day 2", "29 Apr 19:42", "Diary 02", "SYM-01 severity", "Hindi response 0", "014-012", "Complete"],
        ["Day 3", "30 Apr 20:18", "Diary 03", "SYM-02 nausea", "Hindi response 0", "014-012", "Complete"],
        ["Day 4", "01 May 21:03", "Diary 04", "SYM-03 dizziness", "Hindi response 1", "014-012", "Complete"],
        ["Day 5", "02 May 20:51", "Diary 05", "SYM-01 severity", "Hindi response 1", "014-012", "Complete"],
        ["Day 6", "03 May 19:38", "Diary 06", "SYM-02 nausea", "Hindi response 0", "014-012", "Complete"],
        ["Day 7", "04 May 20:26", "Diary 07", "SYM-03 dizziness", "Hindi response 0", "014-012", "Complete"],
        ["Review", "05 May 09:20", "Diary 01-07", "Identifiers matched", "No translation change", "MK", "Ready for subject entry"],
        ["Subject entry", "05 May 09:34", "ePRO batch B-14", "Seven item IDs", "Entered by subject", "014-012", "Audit note W14 linked"],
        ["Coordinator check", "05 May 09:46", "ePRO batch B-14", "Values compared", "No discrepancy", "MK", "Verified; no proxy"],
        ["Copy return", "05 May 10:02", "TD-HI-204-014", "Paired booklet", "Rev 1 returned", "MK", "Vault slot TR-6"],
    ]
    diarylog_y = draw_table(c, 18, 675, [66, 72, 85, 106, 109, 54, 84], [diarylog_headers, *diarylog_rows], font_size=5.5, row_padding=2.7, zebra=True)
    draw_paragraph(c, "Coordinator comparison is verification, not proxy entry. The subject entered all seven item identifiers into ePRO, and the audit note links the paper aid without converting the Hindi responses into a new translation version.", 42, diarylog_y - 20, 510, size=8.0, leading=11.0, color=MUTED)
    _gold_table(case, "Translated-diary controlled-copy and transcription log", diarylog_headers, diarylog_rows, "The subject, not the coordinator, entered the seven items; coordinator comparison is not proxy entry.")
    _selected_table_region(case, "waiver-log", "Translated-diary controlled-copy log", diarylog_headers, diarylog_rows, [
        ("Issue", "Copy / day"), ("Issue", "Hindi aid state"),
        ("Day 4", "Hindi aid state"), ("Review", "Audit result"),
        ("Subject entry", "Actor"), ("Subject entry", "Audit result"),
        ("Coordinator check", "Audit result"), ("Copy return", "Audit result"),
    ], consequential=[("Subject entry", "Actor"), ("Coordinator check", "Audit result")])
    _facts(case, "waiver-log-rule", "Translated-diary transcription responsibility", "text", [
        ("subject", "Subject 014-012 entered all seven diary item identifiers into ePRO."),
        ("proxy", "Coordinator comparison was verification and not proxy entry.", 2),
        ("version", "The Hindi responses remained under TD-HI-204 revision 1."),
    ], budget=1, primary_axis="long_context_coherence")

    # 44 - native CAPA evidence-verification matrix.
    c = case.new_page(
        "CAPA evidence verification matrix",
        subtitle="Evidence acceptance is evaluated against each final approved obligation",
        section_code="CAPA / EVIDENCE",
    )
    evidence_headers = ["CAPA item", "Final obligation", "Due", "Evidence received", "Verifier", "Verification result", "Linked item state"]
    evidence_rows = [
        ["C-01", "Q-77 DCF + production audit", "10 May 12:00", "10 May 10:31", "LS 10:38", "Meets both elements", "Q-77 closed 10:41"],
        ["C-02", "RX2-441 certificate covering reset", "12 May 17:00", "12 May 16:07", "LS 16:42", "Final certificate accepted", "A-202 evidenced"],
        ["C-03", "Three K-204-146 contact attempts", "13 May 15:00", "Two by 13 May 13:00", "LS 13:08", "Incomplete", "A-203 open"],
        ["C-04", "Corrected SH-204-45 receipt", "11 May 12:00", "09 May 09:41", "LS 09:48", "Receipt accepted", "CE closure separate"],
        ["C-05", "PI amended-chemistry review", "09 May 17:00", "09 May 08:06", "LS 12:46", "Portal acknowledgment valid", "Q-88 closed"],
        ["C-06", "ePRO competency + Q-91 audit", "09 May 14:00", "09 May 10:12", "LS 10:16", "Both elements accepted", "Q-91 closed"],
        ["C-07", "Signed masking assessment + Q-93", "11 May 16:00", "Unsigned draft 11 May", "LS 15:24", "Rejected; signature absent", "Revised due approved"],
        ["C-07R", "Signed assessment MA-016", "13 May 16:00", "13 May 15:26", "LS 15:44", "Accepted under revision", "Q-93 closure pending"],
        ["C-08", "Signed Q-86 calculation + link", "11 May 12:00", "11 May 10:42", "LS 10:58", "Both elements accepted", "Q-86 closed 11:15"],
        ["P-01", "Weekly certificate check added", "13 May opening", "13 May 07:42", "RP 07:48", "Opening-log field active", "Effectiveness pending"],
        ["P-02", "Coordinator precedence refresher", "20 May 17:00", "Scheduled 18 May", "LS", "Not yet due", "Attendance absent"],
        ["EC-01", "CAPA effectiveness review", "21-22 May", "Not yet due", "LS", "Open", "Archive hold"],
    ]
    evidence_y = draw_table(c, 16, 675, [51, 154, 70, 89, 64, 97, 71], [evidence_headers, *evidence_rows], font_size=5.5, row_padding=2.5, zebra=True)
    draw_paragraph(c, "C-07R is an approved revised obligation, not a silent overwrite of the late C-07 evidence failure. C-04 evidence acceptance does not close CE-204-12, and preventive-action assignment does not establish effectiveness.", 42, evidence_y - 18, 510, size=7.8, leading=10.7, color=MUTED)
    _gold_table(case, "CAPA evidence verification matrix", evidence_headers, evidence_rows, "C-07R is an approved revised obligation, not a silent overwrite of the late C-07 evidence failure. C-04 evidence acceptance does not close CE-204-12, and preventive-action assignment does not establish effectiveness.")
    _selected_table_region(case, "capa-evidence", "CAPA evidence verification matrix", evidence_headers, evidence_rows, [
        ("C-01", "Verification result"), ("C-02", "Evidence received"),
        ("C-02", "Linked item state"), ("C-03", "Verification result"),
        ("C-04", "Linked item state"), ("C-07", "Verification result"),
        ("C-07R", "Due"), ("C-07R", "Verification result"),
        ("C-08", "Linked item state"), ("EC-01", "Linked item state"),
    ], consequential=[("C-02", "Linked item state"), ("C-03", "Verification result"), ("C-07", "Verification result")])
    _facts(case, "capa-evidence-rule", "CAPA evidence-state rule", "text", [
        ("revision", "C-07R preserves rather than erases the rejected unsigned C-07 submission.", 2),
        ("ce", "C-04 evidence acceptance does not itself close CE-204-12.", 2),
        ("effectiveness", "Preventive-action assignment does not establish CAPA effectiveness."),
    ], budget=1, primary_axis="source_precedence")

    # 45 - native action-state ledger after evidence intake.
    c = case.new_page(
        "Post-visit action state-transition ledger",
        subtitle="As of 13 May 2026 13:00 | Assignment, evidence, completion, and closure",
        section_code="ACTION / TRANSITIONS",
    )
    state_headers = ["Action", "Assigned", "Evidence event", "Evidence state", "Completion decision", "Administrative state", "Residual requirement"]
    state_rows = [
        ["A-201 / Q-77", "09 May 15:52", "10 May 10:31", "Verified", "Complete 10 May 10:38", "Q-77 closed 10:41", "None"],
        ["A-202 / RX2-441", "09 May 15:56", "12 May 16:07", "Verified 16:42", "Complete 12 May 16:42", "CAPA evidence linked", "Sponsor return record"],
        ["A-203 / K-204-146", "09 May 15:52", "Two calls by 13 May 13:00", "Incomplete", "Not complete", "Open", "Third attempt by 15:00"],
        ["A-204 / masking", "09 May 16:02", "Unsigned draft 11 May", "Rejected", "Revised due 13 May", "Open", "Signed MA-016"],
        ["A-205 / Q-86", "09 May 15:52", "11 May 10:42", "Verified 10:58", "Complete 11 May 10:58", "Q-86 closed 11:15", "None"],
        ["ER-204 / receipt", "09 May 12:24", "09 May 09:41 pre-existing", "Verified", "Evidence satisfied", "CE-204-12 open", "Exception closure"],
        ["ER-205 / chemistry", "09 May 12:24", "09 May 08:06 pre-existing", "Verified", "Evidence satisfied", "Q-88 closed", "None"],
        ["ER-206 / ePRO", "09 May 12:24", "09 May 10:12", "Verified", "Evidence satisfied", "Q-91 closed", "None"],
        ["ER-209 / receipt", "09 May 13:06", "Courier ticket only", "Insufficient", "Not complete", "Q-84 open", "Portal receipt"],
        ["ER-210 / return", "12 May 16:42", "13 May 10:26", "Under review", "Not decided", "Open", "Verify sealed transfer"],
        ["ER-211 / FU-013", "09 May 13:10", "No mail proof", "Absent", "Not complete", "Open", "Certified-letter receipt"],
        ["EC-01 / effectiveness", "09 May 12:18", "Review not due", "Not applicable yet", "Not complete", "Open", "21-22 May review"],
    ]
    state_y = draw_table(c, 14, 675, [79, 72, 121, 80, 109, 101, 32], [state_headers, *state_rows], font_size=5.5, row_padding=2.4, zebra=True)
    draw_paragraph(c, "Completion is recorded only after the required evidence is verified. A linked query may close after action completion; a custody exception may remain open after its evidence action is satisfied. Pre-existing evidence retains its original timestamp.", 42, state_y - 18, 510, size=7.8, leading=10.6, color=MUTED)
    _gold_table(case, "Post-visit action state-transition ledger", state_headers, state_rows, "Completion is recorded only after the required evidence is verified. A linked query may close after action completion; a custody exception may remain open after its evidence action is satisfied. Pre-existing evidence retains its original timestamp.")
    _selected_table_region(case, "action-states", "Post-visit action state-transition ledger", state_headers, state_rows, [
        ("A-201 / Q-77", "Administrative state"), ("A-202 / RX2-441", "Completion decision"),
        ("A-202 / RX2-441", "Residual requirement"), ("A-203 / K-204-146", "Evidence state"),
        ("A-203 / K-204-146", "Residual requirement"), ("A-204 / masking", "Evidence state"),
        ("A-205 / Q-86", "Administrative state"), ("ER-204 / receipt", "Administrative state"),
        ("ER-209 / receipt", "Evidence state"), ("EC-01 / effectiveness", "Residual requirement"),
    ], consequential=[("A-202 / RX2-441", "Completion decision"), ("A-203 / K-204-146", "Evidence state"), ("A-204 / masking", "Evidence state")])
    _facts(case, "action-state-rule", "Action completion and closure rule", "text", [
        ("complete", "Action completion follows evidence verification.", 2),
        ("independent", "A custody exception may remain open when its evidence action is satisfied."),
        ("timestamps", "Pre-existing evidence retains its original timestamp."),
    ], budget=1, primary_axis="long_context_coherence")

    # 46 - full-page scan: final masking-impact assessment.
    c = case.new_page(
        "Final masking-impact assessment MA-016",
        subtitle="Scanned signed assessment | Subject 014-016 and Q-93",
        section_code="MASKING / FINAL",
    )
    scan = _scan_document(
        "MASKING IMPACT ASSESSMENT MA-016 - FINAL",
        "HTX-204 | Site 014 | Subject 014-016 | Signed 13 May 2026",
        [
            ("Records reviewed", [
                "Reviewed dosing worksheet, timed glucose observations, RTS restricted-access audit, pharmacy access record for kit K-204-190, site note dated 04 May, Q-93 history, and staff role/delegation records.",
                "The blinded note stated that an unblinded pharmacist was consulted. It did not include treatment assignment, kit-arm mapping, RTS code, or product identity. RP's RTS session was limited to controlled-custody confirmation.",
            ]),
            ("Impact conclusion", [
                "No emergency code break occurred and no treatment code was displayed to NR, MK, LS, or the subject. The phrase disclosed a restricted-role interaction but did not reveal treatment. Clinical dosing and AE causality decisions were based on glucose and symptoms before the note was written.",
                "Masking impact is assessed as none. No data exclusion, dose reassessment, or recruitment pause is required. Site coaching is required to avoid naming restricted roles in blinded notes.",
            ]),
            ("Administrative disposition", [
                "Q-93 response may be closed after this signed assessment is uploaded and the coaching acknowledgment is attached. Assessment completion does not itself perform console closure.",
            ]),
        ],
        controls=[
            ("Emergency code break occurred", "unchecked"),
            ("Treatment code disclosed", "unchecked"),
            ("Masking impact identified", "unchecked"),
            ("Clinical decision affected", "unchecked"),
            ("Blinded-note coaching required", "checked"),
            ("Recruitment pause required", "unchecked"),
            ("Assessment complete", "checked"),
            ("Q-93 closed on this form", "unchecked"),
        ],
        signatures=[
            "Assessment author NR 13 May 2026 15:18. Independent QA review S. Mehta 15:36. Monitor acceptance LS 15:44.",
        ],
        seed=1746,
        form_code="MA-016 / FINAL SIGNED",
    )
    _place_full_scan(c, scan)
    _gold_scan(case, "Final masking-impact assessment MA-016", "MA-016 is the final masking-impact assessment for subject 014-016. Emergency code break occurred, treatment code disclosed, masking impact identified, clinical decision affected, recruitment pause required, and Q-93 closed on this form are unchecked. Blinded-note coaching required and assessment complete are checked. MA-016 concludes no masking impact because the role-interaction phrase disclosed no treatment assignment or code. NR signed MA-016 at 15:18, QA reviewed at 15:36, and LS accepted at 15:44 on 2026-05-13. Console closure remains a later administrative event.")
    _facts(case, "masking-final", "Scanned final masking-impact assessment", "form", [
        ("break", "Emergency code break occurred is unchecked.", 2, ("Emergency code break occurred", "unchecked")),
        ("code", "Treatment code disclosed is unchecked.", 2, ("Treatment code disclosed", "unchecked")),
        ("impact", "Masking impact identified is unchecked.", 2, ("Masking impact identified", "unchecked")),
        ("clinical", "Clinical decision affected is unchecked.", 2, ("Clinical decision affected", "unchecked")),
        ("coaching", "Blinded-note coaching required is checked.", 1, ("Blinded-note coaching required", "checked")),
        ("pause", "Recruitment pause required is unchecked.", 2, ("Recruitment pause required", "unchecked")),
        ("complete", "Assessment complete is checked.", 2, ("Assessment complete", "checked")),
        ("q93", "Q-93 closed on this form is unchecked.", 2, ("Q-93 closed on this form", "unchecked")),
        ("conclusion", "MA-016 concludes no masking impact because the note disclosed no treatment assignment or code.", 2),
        ("signatures", "NR signed MA-016 at 15:18, QA reviewed at 15:36, and LS accepted at 15:44 on 2026-05-13."),
    ], budget=2, primary_axis="low_quality_scan", secondary_axes=("form_state", "source_precedence"))

    # 47 - native query, deviation, and exception closure ledger.
    c = case.new_page(
        "Query, deviation, and exception closure ledger",
        subtitle="State as of 14 May 2026 09:00 | Closure requires its own dated event",
        section_code="CLOSURE / LEDGER",
    )
    close_headers = ["Record", "Entity", "Evidence-complete time", "Closure authority", "Closure time", "Final administrative state", "Retained open dependency"]
    close_rows = [
        ["Q-77", "014-003 ECG", "10 May 10:38", "AT", "10 May 10:41", "Closed", "DEV-014-03 effectiveness"],
        ["DEV-014-03", "014-003 ECG", "10 May 10:38", "NR", "10 May 11:06", "Closed; major retained", "CAPA effectiveness"],
        ["CE-204-12", "SH-204-45", "09 May 09:48", "CL", "11 May 09:22", "Closed; analytical use retained", "None"],
        ["Q-84", "014-008 receipt", "Not complete", "AT", "-", "Open", "Portal receipt absent"],
        ["Q-86", "014-009 window", "11 May 10:58", "AT", "11 May 11:15", "Closed", "DEV-014-08 close"],
        ["DEV-014-08", "014-009 window", "11 May 10:58", "NR", "11 May 11:24", "Closed; minor retained", "None"],
        ["Q-88", "014-011 chemistry", "09 May 08:18", "AT", "09 May 09:02", "Closed", "AE follow-up routine"],
        ["DEV-014-09", "014-011 evidence", "09 May 12:46", "NR", "09 May 13:04", "Closed; major retained", "CAPA effectiveness"],
        ["Q-91", "014-014 ePRO", "09 May 10:12", "AT", "09 May 10:16", "Closed", "Missing days retained"],
        ["DEV-014-10", "014-014 activation", "09 May 10:12", "MK", "09 May 10:26", "Closed; minor retained", "Prospective diary review"],
        ["Q-93", "014-016 masking", "13 May 15:44", "AT", "14 May 08:22", "Closed", "Coaching acknowledgment"],
        ["DEV-014-11", "014-016 masking", "13 May 15:44", "NR", "14 May 08:34", "Closed; major retained", "CAPA effectiveness"],
        ["A-203", "K-204-146 return", "Not complete", "LS", "-", "Open", "Third contact attempt"],
        ["EC-01", "CAPA-014-02", "Not due", "LS", "-", "Open", "21-22 May review"],
    ]
    close_y = draw_table(c, 14, 675, [71, 84, 90, 76, 78, 115, 80], [close_headers, *close_rows], font_size=5.5, row_padding=2.4, zebra=True)
    draw_paragraph(c, "Evidence-complete time and closure time are intentionally separate. Closing a query does not erase the retained deviation class, missing diary days, or effectiveness obligation. A dash in closure time means the item remains open.", 42, close_y - 18, 510, size=7.8, leading=10.6, color=MUTED)
    _gold_table(case, "Query, deviation, and exception closure ledger", close_headers, close_rows, "Evidence-complete time and closure time are intentionally separate. Closing a query does not erase the retained deviation class, missing diary days, or effectiveness obligation. A dash in closure time means the item remains open.")
    _selected_table_region(case, "closure", "Query, deviation, and exception closure ledger", close_headers, close_rows, [
        ("Q-77", "Closure time"), ("DEV-014-03", "Final administrative state"),
        ("CE-204-12", "Closure time"), ("Q-84", "Final administrative state"),
        ("Q-86", "Closure time"), ("DEV-014-08", "Final administrative state"),
        ("Q-91", "Retained open dependency"), ("Q-93", "Closure time"),
        ("DEV-014-11", "Final administrative state"), ("A-203", "Retained open dependency"),
        ("EC-01", "Final administrative state"),
    ], consequential=[("Q-77", "Closure time"), ("Q-84", "Final administrative state"), ("Q-93", "Closure time")])
    _facts(case, "closure-rule", "Closure chronology rule", "text", [
        ("separate", "Evidence-complete time and administrative closure time are separate fields.", 2),
        ("history", "Closing a query does not erase a retained deviation class or missing diary days."),
        ("dash", "A dash in closure time means the item remains open."),
    ], budget=1, primary_axis="long_context_coherence")

    # 48 - native archive exception register.  This is a tail control, not a
    # recap of all findings or a map to their controlling pages.
    c = case.new_page(
        "Archive-readiness exception register",
        subtitle="Tail control as of 15 May 2026 09:30 | Only unresolved archive conditions",
        section_code="ARCHIVE / HOLDS",
    )
    archive_headers = ["Hold", "Object / entity", "Condition at 15 May", "Owner", "Next evidence", "Due / review", "Archive effect"]
    archive_rows = [
        ["H-01", "A-203 / K-204-146", "Two contact attempts documented", "MK", "Third attempt + annotation", "15 May 12:00 revised", "Accountability tab held"],
        ["H-02", "Q-84 / 014-008", "Portal receipt still absent", "AT", "Interface receipt event", "16 May 12:00", "Lab-query tab held"],
        ["H-03", "FU-013 / 014-013", "Certified-mail proof absent", "MK", "Postal acceptance receipt", "15 May 17:00", "Follow-up tab held"],
        ["H-04", "EC-01 / CAPA-014-02", "Effectiveness review not due", "LS", "21-22 May effectiveness record", "22 May 17:00", "CAPA finalization held"],
        ["H-05", "P-02 training", "Session scheduled, attendance absent", "LS", "Signed attendance roster", "20 May 17:00", "Training tab held"],
        ["H-06", "K-204-153 sponsor return", "Sealed transfer verified 13 May", "RP", "Courier delivery confirmation", "16 May 17:00", "Pharmacy shipment subtab held"],
        ["H-07", "Q-93 coaching", "Coaching assigned after closure", "NR", "Blinded-note coaching acknowledgment", "15 May 16:00", "Masking subtab held"],
        ["H-08", "TD-HI-204-014", "Returned booklet in vault TR-6", "MK", "Destruction or reissue decision", "31 May expiry", "Waiver subtab active"],
        ["H-09", "CE-204-12", "Closed 11 May; receipt retained", "CL", "None", "Complete", "No hold"],
        ["H-10", "Q-77 production audit", "Closed 10 May; screenshot verified", "AT", "None", "Complete", "No hold"],
        ["H-11", "MA-016", "Assessment and Q-93 closed", "NR", "Coaching acknowledgment only", "15 May 16:00", "Assessment itself releasable"],
        ["H-12", "MV-03 workpaper", "Monitor signatures complete", "LS", "Resolve H-01 through H-08", "After all holds", "Packet index held"],
    ]
    archive_y = draw_table(c, 16, 675, [43, 108, 127, 48, 127, 80, 59], [archive_headers, *archive_rows], font_size=5.5, row_padding=2.5, zebra=True)
    draw_paragraph(c, "This register lists archive conditions only. A held subtab may coexist with a closed clinical query, and a releasable assessment may still have a coaching follow-up. No-hold rows are retained to prevent an already closed item from being reopened by inference.", 42, archive_y - 18, 510, size=7.9, leading=10.7, color=MUTED)
    _gold_table(case, "Archive-readiness exception register", archive_headers, archive_rows, "This register lists archive conditions only. A held subtab may coexist with a closed clinical query, and a releasable assessment may still have a coaching follow-up. No-hold rows are retained to prevent an already closed item from being reopened by inference.")
    _selected_table_region(case, "archive", "Archive-readiness exception register", archive_headers, archive_rows, [
        ("H-01", "Condition at 15 May"), ("H-01", "Next evidence"),
        ("H-02", "Archive effect"), ("H-04", "Due / review"),
        ("H-06", "Condition at 15 May"), ("H-07", "Next evidence"),
        ("H-08", "Due / review"), ("H-09", "Archive effect"),
        ("H-11", "Archive effect"), ("H-12", "Archive effect"),
    ], consequential=[("H-01", "Next evidence"), ("H-04", "Due / review"), ("H-12", "Archive effect")])
    _facts(case, "archive-rule", "Archive-hold interpretation", "text", [
        ("scope", "The tail register records archive conditions only; it is not a recap of all clinical findings.", 1, {"evidence": [["tail", "archive"], ["register"], ["conditions"], ["only"], ["not", "no"], ["recap", "summary"], ["clinical"], ["findings"]]}),
        ("coexist", "A held subtab may coexist with a closed clinical query.", 2),
        ("no-reopen", "No-hold rows prevent already closed items from being reopened by inference."),
    ], budget=1, primary_axis="long_context_coherence")

    if set(INTENDED_PAGE_MODALITY) != set(range(1, 49)):
        raise ValueError("Intended page modality map must cover pages 1 through 48 exactly")
    record = case.finish()
    rasterize_pdf_pages(
        case.pdf_path,
        case.pdf_path,
        {
            5: ScanProfile(seed=1705, dpi=168, skew_degrees=-0.12, noise_level=1.10, blur_radius=0.14, jpeg_quality=91, contrast=1.04),
            8: ScanProfile(seed=1708, dpi=160, skew_degrees=0.15, noise_level=1.25, blur_radius=0.16, jpeg_quality=90, contrast=1.04),
            11: ScanProfile(seed=1711, dpi=156, skew_degrees=-0.20, noise_level=1.45, blur_radius=0.19, jpeg_quality=89, contrast=1.05),
            12: ScanProfile(seed=1712, dpi=150, skew_degrees=0.24, noise_level=1.65, blur_radius=0.21, jpeg_quality=88, contrast=1.04),
            16: ScanProfile(seed=1716, dpi=164, skew_degrees=-0.14, noise_level=1.20, blur_radius=0.16, jpeg_quality=90, contrast=1.04),
            20: ScanProfile(seed=1720, dpi=152, skew_degrees=0.18, noise_level=1.55, blur_radius=0.20, jpeg_quality=88, contrast=1.04),
            22: ScanProfile(seed=1722, dpi=158, skew_degrees=-0.16, noise_level=1.35, blur_radius=0.18, jpeg_quality=89, contrast=1.04),
            25: ScanProfile(seed=1725, dpi=148, skew_degrees=0.22, noise_level=1.60, blur_radius=0.20, jpeg_quality=87, contrast=1.04),
            30: ScanProfile(seed=1730, dpi=154, skew_degrees=-0.18, noise_level=1.40, blur_radius=0.18, jpeg_quality=89, contrast=1.04),
            38: ScanProfile(seed=1738, dpi=150, skew_degrees=0.20, noise_level=1.55, blur_radius=0.20, jpeg_quality=88, contrast=1.04),
            42: ScanProfile(seed=1742, dpi=156, skew_degrees=-0.15, noise_level=1.30, blur_radius=0.17, jpeg_quality=90, contrast=1.04),
            46: ScanProfile(seed=1746, dpi=148, skew_degrees=0.23, noise_level=1.65, blur_radius=0.21, jpeg_quality=87, contrast=1.04),
        },
        metadata={
            "Creator": "Helio clinical archive imaging",
            "Producer": "Enterprise Document Services",
        },
    )
    return record
