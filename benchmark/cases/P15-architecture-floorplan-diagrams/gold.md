# Orion Biologics Lab Network Renovation Packet

Rev C dated 2026-06-12 controls. Rev B labels Lab B door as D-214A, but Rev C changes the corridor door to D-214B and adds card reader CR-6 on the corridor side.

## Floor Plan A2.14

Suite 214 contains 214 Clean Prep measuring 18 ft 6 in x 12 ft 0 in, 215 Lab B measuring 16 ft 0 in x 12 ft 0 in, 216 Freezer measuring 10 ft 6 in x 12 ft 0 in, C2 Corridor, 217 Wash measuring 12 ft 0 in x 10 ft 0 in, and 218 IT Closet measuring 10 ft 6 in x 10 ft 0 in.

The egress arrow exits from Clean Prep toward C2 Corridor. Callout 6 is card reader CR-6 at the Lab B corridor door. Callout 9 is rack R2 in 218 IT Closet. Callout 11 is freezer FZ-3 in 216 Freezer. Door schedule: D-214B is the Lab B corridor door; D-214A is the old Rev B label and is superseded.

Door and room coordination schedule:

| Room/door | Rev C field condition | Linked artifact |
| --- | --- | --- |
| 214 Clean Prep | tablet dock on D214-01 | rack port CS-2/01 |
| 215 Lab B / D-214B | CR-6 corridor side; panel L2-15 | RFI-214B final |
| 216 Freezer | FZ-3 monitor at callout 11 | VLAN 240 + L2-17 |
| 218 IT Closet | rack R2, UPS A | panel L2-19 |

Field measurement note: overall suite width is 45 ft 0 in; overall depth is 22 ft 0 in. Door D-214B is the only door label revised by RFI-214B.

## Rack Elevation R2

Core switch CS-2 occupies U42-U43 and is a 48-port PoE switch. Patch panel PP-7 occupies U36-U37 for lab drops 214-218. Firewall FW-02 occupies U30-U31 and is HA secondary. UPS A occupies U24-U26 and is 2.2 kVA. Freezer monitor GW-3 is at U18. NVR camera bridge occupies U12-U13 and belongs to VLAN 240.

| Port | Drop | Room | Device | VLAN |
| --- | --- | --- | --- | --- |
| CS-2/01 | D214-01 | 214 Clean Prep | tablet dock | 210 |
| CS-2/07 | D215-03 | 215 Lab B | card reader CR-6 | 230 |
| CS-2/12 | D216-02 | 216 Freezer | FZ-3 monitor | 240 |
| CS-2/19 | D218-01 | 218 IT Closet | FW-02 mgmt | 99 |

## Network Topology N1.07

FW-02 connects to CS-2 over trunk VLAN 99/210/230/240. CS-2 connects to CR-6 over VLAN 230 access control. CS-2 connects to FZ-3 over VLAN 240 / 10.42.40.0/24. CS-2 connects to QA subnet over VLAN 210 / 10.42.10.0/24. CR-6 connects to NVR via badge event mirror. A dashed optional alert overlay runs from FZ-3 to NVR. VLAN 240 maps to freezer and camera telemetry; VLAN 230 is access control; VLAN 210 is QA devices.

Port and firewall rule extract:

| Rule/port | Source | Destination | VLAN | State |
| --- | --- | --- | --- | --- |
| ACL-230-06 | CR-6 | NVR event mirror | 230 to 240 | permit one-way |
| ACL-240-11 | FZ-3 | QA subnet telemetry | 240 to 210 | deny except broker |
| TRK-CS2-FW02 | CS-2 | FW-02 | 99/210/230/240 | tagged trunk |
| OPT-CAM | FZ-3 optional overlay | NVR | 240 | dashed / not base scope |

## Electrical Panel LP-2 Schedule

| Circuit | Load | Breaker | Emergency? | Room | Note |
| --- | --- | --- | --- | --- | --- |
| L2-11 | Bench outlets B | 20A/1P | No | 215 Lab B | GFCI |
| L2-13 | Autoclave AC-1 | 30A/2P | No | 217 Wash | dedicated |
| L2-15 | Door controller DC-6 | 20A/1P | Yes | 215 Lab B | feeds CR-6 |
| L2-17 | Freezer FZ-3 | 20A/1P | Yes | 216 Freezer | monitor required |
| L2-19 | Rack R2 UPS | 20A/1P | Yes | 218 IT Closet | UPS A |
| L2-21 | Spare | 20A/1P | No | - | hold for Rev D |

Emergency circuits are L2-15, L2-17, and L2-19. L2-17 is Freezer FZ-3 and matches floor-plan callout 11.

Load summary and emergency branch check:

| Branch | Connected load | Emergency load | Reviewer note |
| --- | ---: | ---: | --- |
| Normal receptacles | 3.2 kVA | 0.0 kVA | bench + autoclave only |
| Access control | 0.4 kVA | 0.4 kVA | DC-6 on L2-15 |
| Cold storage | 0.7 kVA | 0.7 kVA | FZ-3 on L2-17 |
| IT / UPS | 1.1 kVA | 1.1 kVA | R2 UPS on L2-19 |
| Spare capacity | 2.6 kVA | - | L2-21 held for Rev D |

Emergency branch labels match floor plan callouts is checked. L2-21 released for construction is unchecked. Freezer monitor moved to normal power is unchecked.

## RFI-214B

Question: CAD Rev B shows D-214A at Lab B corridor. Field sticker and security rough-in show D-214B. Which label controls for access control schedule?

Final answer: Use D-214B for the Lab B corridor door. Add CR-6 card reader on corridor side. Update access control schedule and panel LP-2 circuit L2-15. Rev C dated 2026-06-12 controls.

Revision cloud text: D-214B + CR-6.

| Field | Rev B | Rev C final |
| --- | --- | --- |
| Door label | D-214A | D-214B |
| Reader | none | CR-6 corridor side |
| Circuit | unassigned | L2-15 |
| Schedule status | draft | issued |
