from __future__ import annotations

from reportlab.lib.colors import HexColor

from .common import (
    AMBER,
    BLUE,
    GREEN,
    INK,
    LANDSCAPE,
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


def _room(c, x, y, width, height, name, dimensions):
    c.setStrokeColor(INK)
    c.setLineWidth(2.4)
    c.rect(x, y, width, height, fill=0, stroke=1)
    c.setFillColor(INK)
    c.setFont("DocSans-Bold", 7.2)
    c.drawCentredString(x + width / 2, y + height / 2 + 4, name)
    c.setFont("DocSans", 6.2)
    c.setFillColor(MUTED)
    c.drawCentredString(x + width / 2, y + height / 2 - 8, dimensions)


def build(output_root):
    case = CaseBuilder(
        output_root=output_root,
        case_id="P15-architecture-floorplan-diagrams",
        title="Suite 214 Laboratory Coordination Set",
        family="architectural and building systems",
        tags=["native-pdf", "floorplan", "rack-elevation", "directed-topology", "panel-schedule", "scanned-rfi"],
        page_count=6,
        purpose="Test spatial plan relations, rack-unit placement, directed network links, electrical bindings, checkbox state, and a scanned field revision.",
        source_modality="born-digital native technical drawing set with one embedded scanned field-RFI response",
        document_ref="ARC-214 · LAB COORDINATION SET · REV C",
        metadata_date="D:20260624110500-04'00'",
    )

    # Page 1 - transmittal and revision register.
    c = case.new_page(
        "Suite 214 coordination transmittal",
        subtitle="Orion Biologics | Laboratory renovation | Issue for construction coordination",
        section_code="TX-214-C",
    )
    draw_badge(c, "Revision C", 42, 684, BLUE)
    draw_label(c, "Issue summary", 42, 650)
    draw_paragraph(
        c,
        "Revision C incorporates the answered access-control RFI, updates the Lab B corridor door identifier, assigns the card reader circuit, and carries the coordinated rack and network sheets issued on 12 June 2026.",
        42,
        632,
        520,
        font="DocSans-Bold",
        size=9.2,
        leading=12.5,
    )
    register_headers = ["Sheet", "Title", "Revision", "Issue date", "Status"]
    register_rows = [
        ["A2.14", "Suite 214 floor plan", "C", "12 Jun 2026", "Coordinated"],
        ["T4.08", "Rack R2 elevation and ports", "C", "12 Jun 2026", "Coordinated"],
        ["N1.07", "Laboratory network topology", "C", "12 Jun 2026", "Coordinated"],
        ["E6.02", "Panel LP-2 schedule", "C", "12 Jun 2026", "Coordinated"],
        ["RFI-214B", "Lab B corridor door", "Answered", "12 Jun 2026", "Attached scan"],
    ]
    draw_label(c, "Document register", 42, 535)
    draw_table(c, 42, 520, [75, 210, 65, 95, 110], [register_headers, *register_rows], font_size=7.5, zebra=True)
    revision_headers = ["Revision", "Date", "Change", "Issued by"]
    revision_rows = [
        ["A", "28 May", "Existing-condition backgrounds", "M. Song"],
        ["B", "07 Jun", "Lab B door shown as D-214A", "M. Song"],
        ["C", "12 Jun", "Door D-214B; CR-6; circuit L2-15", "A. Verma"],
    ]
    draw_label(c, "Revision history", 42, 320)
    draw_table(c, 42, 305, [72, 76, 285, 105], [revision_headers, *revision_rows], font_size=7.5, zebra=True)
    c.setFillColor(HexColor("#F4F1E8"))
    c.roundRect(42, 105, 520, 72, 4, fill=1, stroke=0)
    draw_paragraph(c, "Revision C controls. The D-214A identifier remains only on the attached marked-up Revision B RFI sheet.", 56, 151, 490, size=8.8, leading=12, color=RED)
    case.add_gold(
        "Coordination transmittal",
        "Revision C controls and was issued 2026-06-12. Revision B used D-214A; Revision C uses D-214B, adds CR-6, and assigns L2-15.\n\n"
        + markdown_table(register_headers, register_rows)
        + "\n\n"
        + markdown_table(revision_headers, revision_rows),
    )
    case.add_region("p01.register", "Document register", "table", table_leaves("p01.register", register_headers, register_rows), closed_world=True)
    case.add_region("p01.revisions", "Revision history", "table", table_leaves("p01.revisions", revision_headers, revision_rows, consequential={("C", "Change")}), budget=2, closed_world=True)
    case.add_region("p01.control", "Revision control statement", "text", [leaf("p01.control.rev-c", "Revision C dated 2026-06-12 controls over Revision B.", harm=2), leaf("p01.control.old-id", "D-214A remains only on the attached marked-up Revision B RFI sheet.")])

    # Page 2 - landscape architectural floor plan.
    c = case.new_page(
        "A2.14 - Suite 214 floor plan",
        subtitle="Field dimensions, egress direction, equipment callouts, and coordinated door identity",
        section_code="REV C",
        page_size=LANDSCAPE,
    )
    x0, y0 = 70, 185
    plan_width = 635
    plan_scale = plan_width / 45
    lower_height = 10 * plan_scale
    upper_height = 12 * plan_scale
    plan_height = lower_height + upper_height
    upper_y = y0 + lower_height

    clean_width = 18.5 * plan_scale
    lab_width = 16 * plan_scale
    freezer_width = 10.5 * plan_scale
    wash_width = 12 * plan_scale
    corridor_width = 22.5 * plan_scale
    it_width = 10.5 * plan_scale

    clean_x = x0
    lab_x = clean_x + clean_width
    freezer_x = lab_x + lab_width
    wash_x = x0
    corridor_x = wash_x + wash_width
    it_x = corridor_x + corridor_width

    _room(c, clean_x, upper_y, clean_width, upper_height, "214 Clean Prep", "18 ft 6 in x 12 ft 0 in")
    _room(c, lab_x, upper_y, lab_width, upper_height, "215 Lab B", "16 ft 0 in x 12 ft 0 in")
    _room(c, freezer_x, upper_y, freezer_width, upper_height, "216 Freezer", "10 ft 6 in x 12 ft 0 in")
    _room(c, wash_x, y0, wash_width, lower_height, "217 Wash", "12 ft 0 in x 10 ft 0 in")
    _room(c, corridor_x, y0, corridor_width, lower_height, "C2 Corridor", "egress west")
    _room(c, it_x, y0, it_width, lower_height, "218 IT Closet", "10 ft 6 in x 10 ft 0 in")

    # Exterior glazing and two secondary door swings provide conventional
    # architectural symbols without changing the tested room geometry.
    c.setStrokeColor(HexColor("#FFFFFF"))
    c.setLineWidth(4)
    for room_x, room_width in ((clean_x, clean_width), (lab_x, lab_width), (freezer_x, freezer_width)):
        window_x = room_x + room_width / 2 - 2 * plan_scale
        c.line(window_x, y0 + plan_height, window_x + 4 * plan_scale, y0 + plan_height)
        c.setStrokeColor(BLUE)
        c.setLineWidth(0.8)
        c.line(window_x, y0 + plan_height - 2, window_x + 4 * plan_scale, y0 + plan_height - 2)
        c.line(window_x, y0 + plan_height + 2, window_x + 4 * plan_scale, y0 + plan_height + 2)
        c.setStrokeColor(HexColor("#FFFFFF"))
        c.setLineWidth(4)

    secondary_door_width = 2.5 * plan_scale
    for wall_x, hinge_y, opens_right in (
        (corridor_x, y0 + 2 * plan_scale, True),
        (it_x, y0 + 5 * plan_scale, False),
    ):
        c.setStrokeColor(HexColor("#FFFFFF"))
        c.setLineWidth(4)
        c.line(wall_x, hinge_y, wall_x, hinge_y + secondary_door_width)
        c.setStrokeColor(INK)
        c.setLineWidth(1)
        leaf_x = wall_x + secondary_door_width if opens_right else wall_x - secondary_door_width
        c.line(wall_x, hinge_y, leaf_x, hinge_y)
        if opens_right:
            c.arc(wall_x - secondary_door_width, hinge_y - secondary_door_width, wall_x + secondary_door_width, hinge_y + secondary_door_width, startAng=0, extent=90)
        else:
            c.arc(wall_x - secondary_door_width, hinge_y - secondary_door_width, wall_x + secondary_door_width, hinge_y + secondary_door_width, startAng=90, extent=90)

    # D-214B is a 3 ft door in the wall shared by Lab B and C2 Corridor.
    door_width = 3 * plan_scale
    door_hinge_x = lab_x + lab_width - 5.5 * plan_scale
    c.setStrokeColor(HexColor("#FFFFFF"))
    c.setLineWidth(4)
    c.line(door_hinge_x, upper_y, door_hinge_x + door_width, upper_y)
    c.setStrokeColor(INK)
    c.setLineWidth(1)
    c.line(door_hinge_x, upper_y, door_hinge_x, upper_y + door_width)
    c.arc(
        door_hinge_x - door_width,
        upper_y - door_width,
        door_hinge_x + door_width,
        upper_y + door_width,
        startAng=0,
        extent=90,
    )
    c.setStrokeColor(RED)
    c.setFillColor(HexColor("#FFF8F5"))
    c.rect(door_hinge_x + door_width + 3, upper_y - 9, 5, 7, fill=1, stroke=1)

    c.setStrokeColor(MUTED)
    c.setFillColor(MUTED)
    c.setLineWidth(0.7)
    c.line(x0, y0 + plan_height + 10, x0 + plan_width, y0 + plan_height + 10)
    c.drawCentredString(x0 + plan_width / 2, y0 + plan_height + 14, "45 ft 0 in overall")
    c.line(x0 - 18, y0, x0 - 18, y0 + plan_height)
    c.setFont("DocSans", 6.2)
    c.drawString(x0, y0 + plan_height + 1, "22 ft 0 in overall depth")
    draw_arrow(c, 290, upper_y + 55, 270, upper_y - 55, color=GREEN, width=2)
    c.setFillColor(GREEN)
    c.setFont("DocSans-Bold", 6.5)
    c.drawString(278, upper_y - 43, "EGRESS TO C2")
    callouts = [
        ("6", door_hinge_x + door_width + 13, upper_y - 14, "CR-6 / D-214B corridor side"),
        ("9", 600, 210, "Rack R2 / room 218"),
        ("11", 625, 365, "Freezer FZ-3 / room 216"),
    ]
    for number, x, y, label in callouts:
        c.setStrokeColor(RED)
        c.setFillColor(HexColor("#FFF8F5"))
        c.circle(x, y, 10, fill=1, stroke=1)
        c.setFillColor(RED)
        c.setFont("DocSans-Bold", 6.5)
        c.drawCentredString(x, y - 2, number)
        c.line(x + 10, y, x + 55, y + 22)
        c.setFont("DocSans", 6)
        c.drawString(x + 58, y + 19, label)
    coord_headers = ["Location", "Field condition", "Coordinated artifact"]
    coord_rows = [
        ["214 Clean Prep", "D214-01 tablet dock", "CS-2/01; VLAN 210"],
        ["215 Lab B", "D-214B; CR-6 corridor side", "CS-2/07; L2-15"],
        ["216 Freezer", "FZ-3 at callout 11", "CS-2/12; VLAN 240; L2-17"],
        ["218 IT Closet", "Rack R2 at callout 9", "CS-2/19; L2-19"],
    ]
    draw_table(c, 70, 151, [130, 240, 290], [coord_headers, *coord_rows], font_size=6.8, zebra=True)
    case.add_gold(
        "A2.14 - Suite 214 floor plan",
        "The suite is 45 ft 0 in wide and 22 ft 0 in deep. Rooms are 214 Clean Prep (18 ft 6 in x 12 ft 0 in), 215 Lab B (16 ft 0 in x 12 ft 0 in), 216 Freezer (10 ft 6 in x 12 ft 0 in), C2 Corridor, 217 Wash (12 ft 0 in x 10 ft 0 in), and 218 IT Closet (10 ft 6 in x 10 ft 0 in). The south wall of 215 Lab B directly adjoins C2 Corridor. D-214B is set in that shared wall, with reader CR-6 on the corridor side. The egress arrow runs from Clean Prep toward C2 Corridor. Callout 6 identifies CR-6 at D-214B; callout 9 is rack R2 in room 218; callout 11 is FZ-3 in room 216.\n\n"
        + markdown_table(coord_headers, coord_rows),
    )
    room_leaves = [
        leaf("p02.rooms.214", "Room 214 Clean Prep is 18 ft 6 in x 12 ft 0 in."),
        leaf("p02.rooms.215", "Room 215 Lab B is 16 ft 0 in x 12 ft 0 in."),
        leaf("p02.rooms.216", "Room 216 Freezer is 10 ft 6 in x 12 ft 0 in."),
        leaf("p02.rooms.217", "Room 217 Wash is 12 ft 0 in x 10 ft 0 in."),
        leaf("p02.rooms.218", "Room 218 IT Closet is 10 ft 6 in x 10 ft 0 in."),
        leaf("p02.rooms.lab-b-corridor", "The south wall of 215 Lab B directly adjoins C2 Corridor."),
        leaf("p02.rooms.overall-width", "Overall suite width is 45 ft 0 in."),
        leaf("p02.rooms.overall-depth", "Overall suite depth is 22 ft 0 in."),
    ]
    case.add_region("p02.plan", "Floor plan rooms and dimensions", "diagram", room_leaves, budget=2)
    case.add_region("p02.egress", "Egress arrow", "diagram", [leaf("p02.egress.direction", "The egress arrow runs from 214 Clean Prep toward C2 Corridor.", harm=2)])
    case.add_region("p02.callouts", "Plan callouts", "diagram", [leaf("p02.callout.6", "Callout 6 identifies reader CR-6 on the corridor side of D-214B in the shared wall between 215 Lab B and C2 Corridor.", harm=2), leaf("p02.callout.9", "Callout 9 is rack R2 in room 218 IT Closet."), leaf("p02.callout.11", "Callout 11 is freezer FZ-3 in room 216.")])
    case.add_region("p02.coordination", "Room coordination table", "table", table_leaves("p02.coordination", coord_headers, coord_rows), budget=2, closed_world=True)

    # Page 3 - rack elevation and patch bindings.
    c = case.new_page(
        "T4.08 - Rack R2 elevation",
        subtitle="IT Closet 218 | front elevation and patch schedule",
        section_code="REV C",
    )
    rack_x, rack_y, rack_h = 62, 180, 460
    c.setStrokeColor(INK)
    c.setLineWidth(1.5)
    c.rect(rack_x, rack_y, 155, rack_h, fill=0, stroke=1)
    devices = [
        (42, 2, "Core switch CS-2", "48-port PoE"),
        (36, 2, "Patch panel PP-7", "Drops 214-218"),
        (30, 2, "Firewall FW-02", "HA secondary"),
        (24, 3, "UPS A", "2.2 kVA"),
        (18, 1, "Gateway GW-3", "Freezer monitor"),
        (12, 2, "NVR bridge", "VLAN 240"),
    ]
    unit_h = rack_h / 44
    colors = ["#DCE8F4", "#F1F2F2", "#F2DADA", "#F4E9C7", "#DCEBDF", "#E7DFF0"]
    for index, (top_u, units, name, note) in enumerate(devices):
        y = rack_y + (top_u - 1) * unit_h
        c.setFillColor(HexColor(colors[index]))
        c.setStrokeColor(INK)
        c.rect(rack_x + 28, y, 118, units * unit_h, fill=1, stroke=1)
        c.setFillColor(INK)
        if units == 1:
            c.setFont("DocSans-Bold", 5.5)
            c.drawString(rack_x + 34, y + 3, f"{name} · {note}")
        else:
            c.setFont("DocSans-Bold", 5.8)
            c.drawString(rack_x + 34, y + units * unit_h / 2 + 2, name)
            c.setFont("DocSans", 5.8)
            c.drawString(rack_x + 34, y + units * unit_h / 2 - 6, note)
        c.setFont("DocSans", 5.5)
        c.drawRightString(rack_x + 24, y + 2, f"U{top_u}")
    patch_headers = ["Port", "Drop", "Room", "Device", "VLAN"]
    patch_rows = [
        ["CS-2/01", "D214-01", "214", "Tablet dock", "210"],
        ["CS-2/07", "D215-03", "215", "Card reader CR-6", "230"],
        ["CS-2/12", "D216-02", "216", "Freezer monitor FZ-3", "240"],
        ["CS-2/19", "D218-01", "218", "FW-02 management", "99"],
    ]
    draw_label(c, "Patch schedule", 250, 657)
    draw_table(c, 250, 642, [64, 64, 42, 126, 52], [patch_headers, *patch_rows], font_size=7.0, zebra=True)
    draw_label(c, "Rack notes", 250, 440)
    draw_paragraph(c, "Core switch CS-2 occupies U42-U43. PP-7 occupies U36-U37. FW-02 occupies U30-U31. UPS A occupies U24-U26. GW-3 is at U18. The NVR bridge occupies U12-U13.", 250, 422, 310, size=8.3, leading=11.5)
    case.add_gold(
        "T4.08 - Rack R2 elevation",
        "Rack placements: CS-2 U42-U43; PP-7 U36-U37; FW-02 U30-U31; UPS A U24-U26; GW-3 U18; NVR bridge U12-U13.\n\n"
        + markdown_table(patch_headers, patch_rows),
    )
    case.add_region("p03.rack", "Rack-unit elevation", "diagram", [leaf(f"p03.rack.{index:02d}", f"{name} occupies U{top_u}-U{top_u + units - 1}." if units > 1 else f"{name} occupies U{top_u}.") for index, (top_u, units, name, _note) in enumerate(devices, start=1)], budget=2)
    case.add_region("p03.patch", "Patch schedule", "table", table_leaves("p03.patch", patch_headers, patch_rows, consequential={("CS-2/07", "Device")}), budget=2, closed_world=True)

    # Page 4 - directed topology.
    c = case.new_page(
        "N1.07 - Laboratory network topology",
        subtitle="Directed service paths and access-control policy",
        section_code="REV C",
        page_size=LANDSCAPE,
    )
    nodes = {
        "FW-02": (65, 355),
        "CS-2": (220, 355),
        "CR-6": (395, 455),
        "FZ-3": (395, 270),
        "NVR": (590, 455),
        "QA subnet": (590, 270),
    }
    for name, (x, y) in nodes.items():
        c.setFillColor(HexColor("#F6F7F7"))
        c.setStrokeColor(INK)
        c.roundRect(x, y, 105, 38, 4, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("DocSans-Bold", 7)
        c.drawCentredString(x + 52.5, y + 14, name)
    edges = [
        ("FW-02", "CS-2", "trunk 99/210/230/240", False),
        ("CS-2", "CR-6", "VLAN 230", False),
        ("CS-2", "FZ-3", "VLAN 240", False),
        ("CS-2", "QA subnet", "VLAN 210", False),
        ("CR-6", "NVR", "badge event mirror", False),
        ("FZ-3", "NVR", "optional alert overlay", True),
    ]
    for source, destination, label, dashed in edges:
        sx, sy = nodes[source]
        dx, dy = nodes[destination]
        draw_arrow(c, sx + 105, sy + 19, dx, dy + 19, color=AMBER if dashed else BLUE, dashed=dashed)
        c.setFillColor(MUTED)
        c.setFont("DocSans", 5.8)
        c.drawCentredString((sx + 105 + dx) / 2, (sy + dy) / 2 + 27, label)
    rule_headers = ["Rule", "Source", "Destination", "VLAN", "State"]
    rule_rows = [
        ["ACL-230-06", "CR-6", "NVR event mirror", "230 -> 240", "Permit one-way"],
        ["SVC-210-QA", "CS-2", "QA subnet", "210", "Permit telemetry"],
        ["TRK-FW02-CS2", "FW-02", "CS-2", "99/210/230/240", "Tagged trunk"],
        ["OPT-CAM", "FZ-3", "NVR", "240", "Optional / dashed"],
    ]
    draw_table(c, 72, 205, [105, 94, 170, 115, 160], [rule_headers, *rule_rows], font_size=6.8, zebra=True)
    case.add_gold(
        "N1.07 - Laboratory network topology",
        "Directed links: FW-02 -> CS-2 trunk 99/210/230/240; CS-2 -> CR-6 VLAN 230; CS-2 -> FZ-3 VLAN 240; CS-2 -> QA subnet VLAN 210; CR-6 -> NVR badge event mirror; dashed optional FZ-3 -> NVR alert overlay.\n\n"
        + markdown_table(rule_headers, rule_rows),
    )
    case.add_region("p04.topology", "Directed network topology", "diagram", [leaf(f"p04.edge.{index:02d}", f"A {'dashed optional' if dashed else 'solid'} directed link runs from {source} to {destination} for {label}.", harm=2 if not dashed and source in {"FW-02", "CS-2"} else 1) for index, (source, destination, label, dashed) in enumerate(edges, start=1)], budget=2)
    case.add_region("p04.rules", "Access-control rule table", "table", table_leaves("p04.rules", rule_headers, rule_rows, consequential={("ACL-230-06", "State"), ("SVC-210-QA", "State")}), budget=2, closed_world=True)

    # Page 5 - electrical panel and actual check states.
    c = case.new_page(
        "E6.02 - Panel LP-2 schedule",
        subtitle="Connected loads and emergency-branch coordination",
        section_code="REV C",
    )
    panel_headers = ["Circuit", "Load", "Breaker", "Emergency", "Room", "Note"]
    panel_rows = [
        ["L2-11", "Bench outlets B", "20A/1P", "No", "215", "GFCI"],
        ["L2-13", "Autoclave AC-1", "30A/2P", "No", "217", "Dedicated"],
        ["L2-15", "Door controller DC-6", "20A/1P", "Yes", "215", "Feeds CR-6"],
        ["L2-17", "Freezer FZ-3", "20A/1P", "Yes", "216", "Monitor required"],
        ["L2-19", "Rack R2 UPS", "20A/1P", "Yes", "218", "UPS A"],
        ["L2-21", "Spare", "20A/1P", "No", "-", "Hold for Rev D"],
    ]
    draw_table(c, 42, 660, [62, 150, 75, 68, 45, 120], [panel_headers, *panel_rows], font_size=7.2, zebra=True)
    load_headers = ["Branch", "Connected", "Emergency", "Coordination note"]
    load_rows = [
        ["Normal receptacles", "3.2 kVA", "0.0 kVA", "Bench and autoclave"],
        ["Access control", "0.4 kVA", "0.4 kVA", "DC-6 on L2-15"],
        ["Cold storage", "0.7 kVA", "0.7 kVA", "FZ-3 on L2-17"],
        ["IT / UPS", "1.1 kVA", "1.1 kVA", "R2 UPS on L2-19"],
        ["Spare capacity", "2.6 kVA", "-", "L2-21 held for Rev D"],
    ]
    draw_label(c, "Load summary", 42, 395)
    draw_table(c, 42, 380, [140, 82, 82, 210], [load_headers, *load_rows], font_size=7.4, zebra=True)
    draw_label(c, "Issue checks", 42, 186)
    draw_checkbox(c, 44, 155, "checked", "Emergency labels match floor-plan callouts")
    draw_checkbox(c, 44, 130, "unchecked", "L2-21 released for construction")
    draw_checkbox(c, 44, 105, "unchecked", "Freezer monitor moved to normal power")
    case.add_gold(
        "E6.02 - Panel LP-2 schedule",
        markdown_table(panel_headers, panel_rows)
        + "\n\n"
        + markdown_table(load_headers, load_rows)
        + "\n\nIssue checks: Emergency labels match floor-plan callouts is checked. L2-21 released for construction is unchecked. Freezer monitor moved to normal power is unchecked.",
    )
    case.add_region("p05.panel", "Panel LP-2 schedule", "table", table_leaves("p05.panel", panel_headers, panel_rows, consequential={("L2-15", "Emergency"), ("L2-17", "Emergency")}), budget=2, closed_world=True)
    case.add_region("p05.loads", "Panel load summary", "table", table_leaves("p05.loads", load_headers, load_rows), closed_world=True)
    case.add_region("p05.checks", "Electrical issue checkboxes", "form", [leaf("p05.checks.labels", "Emergency labels match floor-plan callouts is checked.", harm=2), leaf("p05.checks.spare", "L2-21 released for construction is unchecked."), leaf("p05.checks.freezer", "Freezer monitor moved to normal power is unchecked.")], budget=2)

    # Page 6 - scanned RFI markup and native issue record.
    c = case.new_page(
        "RFI-214B - Lab B corridor door",
        subtitle="Scanned field response attached to Revision C issue record",
        section_code="ANSWERED 12 JUN",
    )
    scan_lines = [
        "RFI 214B   ACCESS CONTROL / ARCHITECTURAL",
        "Opened: 09 Jun 2026       Required on site: 13 Jun 2026",
        "",
        "QUESTION",
        "CAD Revision B identifies the Lab B corridor door as D-214A.",
        "Field sticker and security rough-in identify D-214B.",
        "Confirm door, reader side, and electrical circuit.",
        "",
        "ARCHITECT RESPONSE",
        "Use D-214A for the Lab B corridor door.",
        "Corrected: use D-214B. Add reader CR-6 on corridor side.",
        "Assign panel LP-2 circuit L2-15. Update access-control schedule.",
        "Revision C dated 12 Jun 2026 governs.",
        "",
        "A. Verma, Architect of Record     signed 12 Jun 2026",
        "Security review TN                contractor ack 13 Jun 2026",
    ]
    scan = make_scan("ORION BIOLOGICS / FIELD RFI RESPONSE", scan_lines, width=1350, height=820, seed=1516, marks=[(58, 410, "strike"), (1120, 650, "check"), (880, 438, "D-214B")])
    c.drawImage(image_reader(scan), 42, 275, width=520, height=315, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(HexColor("#9AA0A6"))
    c.rect(42, 275, 520, 315, fill=0, stroke=1)
    field_headers = ["Field", "Revision B", "Revision C"]
    field_rows = [
        ["Door identifier", "D-214A", "D-214B"],
        ["Reader", "None", "CR-6 corridor side"],
        ["Circuit", "Unassigned", "L2-15"],
        ["Schedule", "Draft", "Issued"],
    ]
    draw_table(c, 42, 245, [125, 150, 220], [field_headers, *field_rows], font_size=7.4, zebra=True)
    case.add_gold(
        "RFI-214B - Lab B corridor door",
        "The scanned response strikes the Revision B answer D-214A and corrects it to D-214B. Revision C uses D-214B, adds CR-6 on the corridor side, assigns LP-2 circuit L2-15, and updates the access-control schedule. A. Verma signed on 2026-06-12; security reviewer TN and the contractor acknowledged the response.\n\n"
        + markdown_table(field_headers, field_rows),
    )
    case.add_region(
        "p06.rfi-scan",
        "Scanned RFI response",
        "form",
        [
            leaf("p06.rfi.old", "The scanned Revision B answer D-214A is struck out."),
            leaf("p06.rfi.door", "The corrected controlling door identifier is D-214B.", harm=2),
            leaf("p06.rfi.reader", "CR-6 is added on the corridor side.", harm=2),
            leaf("p06.rfi.circuit", "Panel LP-2 circuit L2-15 is assigned to the reader.", harm=2),
            leaf("p06.rfi.revision", "Revision C dated 2026-06-12 governs."),
            leaf("p06.rfi.signoff.architect", "A. Verma signed the RFI on 2026-06-12."),
            leaf("p06.rfi.signoff.security", "Security reviewer initials are TN."),
        ],
        budget=2,
    )
    case.add_region("p06.fields", "RFI revision field table", "table", table_leaves("p06.fields", field_headers, field_rows, consequential={("Door identifier", "Revision C"), ("Reader", "Revision C")}), budget=2, closed_world=True)

    return case.finish()
