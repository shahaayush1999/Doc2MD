# Suite 214 Laboratory Coordination Set

## Coordination transmittal

Revision C controls and was issued 2026-06-12. Revision B used D-214A; Revision C uses D-214B, adds CR-6, and assigns L2-15.

| Sheet | Title | Revision | Issue date | Status |
| --- | --- | --- | --- | --- |
| A2.14 | Suite 214 floor plan | C | 12 Jun 2026 | Coordinated |
| T4.08 | Rack R2 elevation and ports | C | 12 Jun 2026 | Coordinated |
| N1.07 | Laboratory network topology | C | 12 Jun 2026 | Coordinated |
| E6.02 | Panel LP-2 schedule | C | 12 Jun 2026 | Coordinated |
| RFI-214B | Lab B corridor door | Answered | 12 Jun 2026 | Attached scan |

| Revision | Date | Change | Issued by |
| --- | --- | --- | --- |
| A | 28 May | Existing-condition backgrounds | M. Song |
| B | 07 Jun | Lab B door shown as D-214A | M. Song |
| C | 12 Jun | Door D-214B; CR-6; circuit L2-15 | A. Verma |

## A2.14 - Suite 214 floor plan

The suite is 45 ft 0 in wide and 22 ft 0 in deep. Rooms are 214 Clean Prep (18 ft 6 in x 12 ft 0 in), 215 Lab B (16 ft 0 in x 12 ft 0 in), 216 Freezer (10 ft 6 in x 12 ft 0 in), C2 Corridor, 217 Wash (12 ft 0 in x 10 ft 0 in), and 218 IT Closet (10 ft 6 in x 10 ft 0 in). The south wall of 215 Lab B directly adjoins C2 Corridor. D-214B is set in that shared wall, with reader CR-6 on the corridor side. The egress arrow runs from Clean Prep toward C2 Corridor. Callout 6 identifies CR-6 at D-214B; callout 9 is rack R2 in room 218; callout 11 is FZ-3 in room 216.

| Location | Field condition | Coordinated artifact |
| --- | --- | --- |
| 214 Clean Prep | D214-01 tablet dock | CS-2/01; VLAN 210 |
| 215 Lab B | D-214B; CR-6 corridor side | CS-2/07; L2-15 |
| 216 Freezer | FZ-3 at callout 11 | CS-2/12; VLAN 240; L2-17 |
| 218 IT Closet | Rack R2 at callout 9 | CS-2/19; L2-19 |

## T4.08 - Rack R2 elevation

Rack placements: CS-2 U42-U43; PP-7 U36-U37; FW-02 U30-U31; UPS A U24-U26; GW-3 U18; NVR bridge U12-U13.

| Port | Drop | Room | Device | VLAN |
| --- | --- | --- | --- | --- |
| CS-2/01 | D214-01 | 214 | Tablet dock | 210 |
| CS-2/07 | D215-03 | 215 | Card reader CR-6 | 230 |
| CS-2/12 | D216-02 | 216 | Freezer monitor FZ-3 | 240 |
| CS-2/19 | D218-01 | 218 | FW-02 management | 99 |

## N1.07 - Laboratory network topology

Directed links: FW-02 -> CS-2 trunk 99/210/230/240; CS-2 -> CR-6 VLAN 230; CS-2 -> FZ-3 VLAN 240; CS-2 -> QA subnet VLAN 210; CR-6 -> NVR badge event mirror; dashed optional FZ-3 -> NVR alert overlay.

| Rule | Source | Destination | VLAN | State |
| --- | --- | --- | --- | --- |
| ACL-230-06 | CR-6 | NVR event mirror | 230 -> 240 | Permit one-way |
| SVC-210-QA | CS-2 | QA subnet | 210 | Permit telemetry |
| TRK-FW02-CS2 | FW-02 | CS-2 | 99/210/230/240 | Tagged trunk |
| OPT-CAM | FZ-3 | NVR | 240 | Optional / dashed |

## E6.02 - Panel LP-2 schedule

| Circuit | Load | Breaker | Emergency | Room | Note |
| --- | --- | --- | --- | --- | --- |
| L2-11 | Bench outlets B | 20A/1P | No | 215 | GFCI |
| L2-13 | Autoclave AC-1 | 30A/2P | No | 217 | Dedicated |
| L2-15 | Door controller DC-6 | 20A/1P | Yes | 215 | Feeds CR-6 |
| L2-17 | Freezer FZ-3 | 20A/1P | Yes | 216 | Monitor required |
| L2-19 | Rack R2 UPS | 20A/1P | Yes | 218 | UPS A |
| L2-21 | Spare | 20A/1P | No | - | Hold for Rev D |

| Branch | Connected | Emergency | Coordination note |
| --- | --- | --- | --- |
| Normal receptacles | 3.2 kVA | 0.0 kVA | Bench and autoclave |
| Access control | 0.4 kVA | 0.4 kVA | DC-6 on L2-15 |
| Cold storage | 0.7 kVA | 0.7 kVA | FZ-3 on L2-17 |
| IT / UPS | 1.1 kVA | 1.1 kVA | R2 UPS on L2-19 |
| Spare capacity | 2.6 kVA | - | L2-21 held for Rev D |

Issue checks: Emergency labels match floor-plan callouts is checked. L2-21 released for construction is unchecked. Freezer monitor moved to normal power is unchecked.

## RFI-214B - Lab B corridor door

The scanned response strikes the Revision B answer D-214A and corrects it to D-214B. Revision C uses D-214B, adds CR-6 on the corridor side, assigns LP-2 circuit L2-15, and updates the access-control schedule. A. Verma signed on 2026-06-12; security reviewer TN and the contractor acknowledged the response.

| Field | Revision B | Revision C |
| --- | --- | --- |
| Door identifier | D-214A | D-214B |
| Reader | None | CR-6 corridor side |
| Circuit | Unassigned | L2-15 |
| Schedule | Draft | Issued |
