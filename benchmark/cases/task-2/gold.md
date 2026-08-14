# Suite 214 Laboratory Coordination Set

## Coordination transmittal and sheet index

Package ARC-214-C is the RECORD ISSUE for the Orion Biologics Suite 214 laboratory renovation. The controlled index lists ten records from TX-01 through CL-214.

| Sheet | Record | Rev | Issued | Class |
| --- | --- | --- | --- | --- |
| TX-01 | Transmittal / index | C | 16 Jun | Record |
| A2.14-B | Archived floor plan | B | 07 Jun | Archive |
| A2.14 | Controlled floor plan | C | 12 Jun | Construction |
| A6.24 | RCP / MEP coordination | C | 12 Jun | Coordination |
| T4.08 | Rack R2 / patching | C | 13 Jun | Coordination |
| N1.07 | Network / access topology | C | 13 Jun | Coordination |
| E6.02 | LP-2 / field check | C | 14 Jun | Field check |
| RFI-214-17 | Door field response | A | 12 Jun | Response |
| PH-214 | Field photo record | A | 15 Jun | Photo record |
| CL-214 | Final issue release | C | 16 Jun | Release |

| Event | Date | Authority | Record effect |
| --- | --- | --- | --- |
| Rev B issue | 07 Jun | MS | Archived background |
| RFI response | 12 Jun | AV | Incorporated by Rev C |
| Rev C issue | 12 Jun | AV | Controls coordination |
| Record release | 16 Jun | LS | Closes package |

The authority order is final release, Revision C sheets, answered RFI, then archived Revision B record. Revision B is retained only as the archived background; Revision C controls coordination; RFI-214-17 is incorporated; the 16 June release closes the package.

## A2.14-B - Archived floor plan

Revision B is visibly stamped superseded and dated 7 June 2026; the archived field-background record is 214-B-0707. The overall footprint is 45 ft by 22 ft. Clean Prep 214 is 18 ft 6 in by 12 ft and is west of Lab B 215, which is 16 ft by 12 ft. Freezer 216 is east of Lab B; Lab B is directly north of corridor C2; Wash 217 is immediately west of corridor C2; IT Closet 218 is south of Freezer 216 and east of C2. The old Lab B opening is near the middle of its south wall, has a north swing into Lab B, and is keyed by callout 6. Callout 9 points to rack R2 in IT Closet 218; callout 11 points to FZ-3 in Freezer 216. The first egress segment runs from Lab B through the old opening and the second turns west along C2.

## A2.14 - Controlled floor plan and overlay

Revision C retains the 45 ft by 22 ft overall footprint but moves the Lab B opening 4 ft 6 in west of the dashed Revision B position. The dimension between the old and new opening hinge points is 4 ft 6 in. The current door is D-214B, is in the Lab B/C2 shared wall, and swings south into corridor C2. Reader CR-6 is on the corridor side at the east jamb. Callout 6 keys that reader and opening; callout 9 keys rack R2 in IT Closet 218; callout 11 keys FZ-3 in Freezer 216. Egress runs from Lab B through D-214B and then west along C2. The north arrow points toward the top of the sheet. The solid blue opening is Revision C's controlling current geometry; the dashed red opening is archived Revision B geometry.

## A6.24 - Reflected ceiling and MEP coordination

The ceiling plan places SD-4 north-west of bench B-2 and west of sprinkler SP-7. SP-7 is north-east of ceiling panel CP-4. Occupancy sensor OS-2 is south-east of CP-4. Light L-5 is north of CP-4. Return grille RG-2 is east of CP-4. The solid green VAV-214 supply arrow runs to SD-4. A dashed amber control arrow runs from OS-2 to CP-4; a dashed blue BAS link runs from CP-4 to BAS-214. The dashed old diffuser location is near SP-7; the red relocation arrow moves it west to the solid current SD-4 position, producing an 8 ft separation. The solid SD-4 symbol is current and the dashed old symbol is superseded. Conflict bubble C1 keys that resolved move.

## T4.08 - Rack R2 elevation and patching

Rack R2 placements are CS-2 at U42-U43, PP-7 at U36-U37, AC-6 at U31-U32, UPS-A at U26-U28, GW-3 at U19, NVR-B at U14-U15, and PDU-2 at U8. Callout B identifies the tray entry on the west/top side of the rack.

| Port | Drop | Endpoint | Location | VLAN | Medium |
| --- | --- | --- | --- | --- | --- |
| CS-2/01 | D214-01 | Tablet dock | 214-W | 210 | Cat6A |
| CS-2/07 | D215-03 | CR-6 | 215-S | 230 | Cat6A |
| CS-2/08 | D215-04 | DC-6 | R2/U31 | 230 | Cat6A |
| CS-2/12 | D216-02 | FZ-3 | 216-E | 240 | Cat6A |
| CS-2/13 | D216-03 | GW-3 | R2/U19 | 240 | Cat6A |
| CS-2/19 | D218-01 | FW-02 mgmt | 218-R2 | 99 | Cat6A |
| PP-7/21 | D214-11 | BAS-214 | 214-N | 120 | OM4 |
| PP-7/22 | D215-12 | CP-4 | 215-CLG | 120 | OM4 |

Internal patch paths are PP-7/07 -> CS-2/07 -> D215-03; PP-7/12 -> CS-2/12 -> D216-02; and PP-7/22 -> OM4-2 -> D215-12.

## N1.07 - Network and access-control topology

Directed edges are FW-02 to CS-2 (tagged trunk 99/210/230/240); CS-2 to CR-6 (VLAN 230 events); CR-6 to DC-6 (Wiegand); DC-6 to ACS-CORE (VLAN 230 authorization); CS-2 to FZ-3 (VLAN 240 telemetry); FZ-3 to QA-210 (one-way alarm); CR-6 to NVR-B (event mirror); and a dashed conditional FZ-3 to BAS-214 trend edge. The CR-6 event mirror branches to NVR-B before the DC-6 authorization target. No reverse authorization, mirror, or alarm edges are drawn.

| Path key | Transport | Mode | Policy |
| --- | --- | --- | --- |
| ACL-230-A | V230 | Auth | Permit one-way |
| MIR-230-B | V230 | Event | Permit one-way |
| TEL-240-Q | V240 | Alarm | Permit one-way |
| OPT-240-B | V240 | Trend | Conditional |

## E6.02 - Panel LP-2 and field check

| Circuit | Load | Breaker | Branch | Room | Record |
| --- | --- | --- | --- | --- | --- |
| L2-11 | Bench outlets B | 20A/1P | Normal | 215 | B-2 |
| L2-13 | Autoclave AC-1 | 30A/2P | Normal | 217 | AC-1 |
| L2-15 | Door controller | 20A/1P | Emergency | 215 | DC-6 |
| L2-17 | Freezer | 20A/1P | Emergency | 216 | FZ-3 |
| L2-19 | Rack UPS | 20A/1P | Emergency | 218 | UPS-A |
| L2-21 | Spare | 20A/1P | Normal | - | Future |

The embedded field-check record is EC-214-19, dated 14 June 2026. Its explicit states are:
- Torque witness marks complete: checked.
- L2-15 field tag installed: checked.
- L2-17 field tag installed: checked.
- L2-19 field tag installed: checked.
- L2-21 released for use: unchecked.
- Emergency transfer witnessed: checked.
- Reader polarity exception open: crossed out.

Technician JH and witness LS recorded that panel LP-2 was energized at 16:42 on 14 June 2026.

## RFI-214-17 - Lab B corridor opening

The field query was received on 2026-06-09. Maintain D-214A at Revision B position is unchecked, crossed by a red strike, and marked VOID. Issue architect response for construction is checked. The answered RFI voids D-214A and makes D-214B the controlling identifier. Architect AV directs a new opening 4 ft 6 in west of the old opening, a south swing into C2, CR-6 on the corridor-side east jamb, and DC-6 on LP-2 circuit L2-15. Revision C governs construction. The redline sketch places Lab B above corridor C2 with the door wall between them, shows the dashed old and solid new positions, dimensions the new opening 4 ft 6 in west of the old opening, and keys reader callout 6 on the east jamb. AV signed 2026-06-12; TN reviewed; contractor RK acknowledged 2026-06-13.

## PH-214 - Field photo and punch evidence

Photo 06 is a corridor-side view of D-214B. The reader is mounted on the image-right/east jamb, outside the Lab B opening; annotation A circles the reader rather than the opening. Photo 09 shows rack R2 in room 218. The overhead tray approaches from image-left/west and drops at the rack's west/top corner; annotation B circles that entry.

| Image | Captured | View | Custodian | Checksum |
| --- | --- | --- | --- | --- |
| PHOTO 06 | 15 Jun 09:16 | C2 south | TN | 8F4C-06A2 |
| PHOTO 09 | 15 Jun 09:42 | 218 west | TN | 1B77-09D5 |

## CL-214 - Final issue and signoff record

| Artifact | Revision | Digest | Recipient | Time |
| --- | --- | --- | --- | --- |
| A2.14 | C | 2E11-A214 | Field / RK | 17:22 |
| A6.24 | C | 9A40-A624 | MEP / JH | 17:22 |
| T4.08 | C | B817-T408 | Security / TN | 17:23 |
| N1.07 | C | 0C31-N107 | IT / SM | 17:23 |
| E6.02 | C | 7D14-E602 | Electrical / JH | 17:24 |
| RFI-214-17 | A | 6F82-R214 | Record / LS | 17:24 |

The release package is ARC-214-C. The embedded release form has IFC Revision C accepted checked, use archived Revision B background unchecked, RFI-214-17 incorporated checked, and open access-control punch items unchecked. Architect AV, Security TN, Electrical JH, and Owner LS sign the release. The release seal is 214-C-0616 and is dated 16 June 2026. Therefore Revision C controls, the archived plan cannot be used for set-out, the RFI directives are incorporated, and no access-control punch item remains open.
