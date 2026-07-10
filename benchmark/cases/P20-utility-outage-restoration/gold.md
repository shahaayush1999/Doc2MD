# Feeder 12R Outage Investigation

## Incident record

| Field | Recorded value |
| --- | --- |
| Outage start | 2 Jul 2026 15:42 |
| Customers interrupted | 8,960 |
| Critical customers | Hospital loop; traffic signal TS-12; lift station LS-4 |
| Hospital restoration | 17:18 via tie T-7 |
| All-customer restoration | 19:06 via R12 breaker close |
| Network normalized | 19:32 after T-7 opened |

| Record | Clock basis | Custodian | State |
| --- | --- | --- | --- |
| SCADA alarm export | Sub-second | System control | Frozen 20:00 |
| Switching order 12R-731 | 24-hour local | Control room | Signed |
| OMS restoration series | 5-minute bins | Outage management | Final |
| Patrol media P1-P3 | GPS device time | Crew A | Uploaded |
| Investigation report | Revision 2 | Protection engineering | Signed 3 Jul |

## SCADA alarm sequence

| Time | Device | State | System note |
| --- | --- | --- | --- |
| 15:42:11 | R12 breaker | Trip | Phase B ground |
| 15:42:14 | Recloser 12R-3 | Lockout | Third shot |
| 15:42:19 | Relay 50G | Pickup | 7.8 kA momentary |
| 15:43:02 | Cap bank CB-4 | Offline | Voltage sag |
| 15:44:33 | OMS | 8,960 out | Nested outage created |
| 16:05:20 | Switch S-18 | Opened | Crew isolation |
| 16:31:05 | Switch S-22 | Opened | Riverside isolated |
| 17:11:00 | DER-44 | 0 kW | Curtailment verified |
| 17:18:44 | Tie T-7 | Closed | Hospital backfeed |
| 18:05:02 | F-12B | Replaced | Maple test passed |
| 18:55:18 | Switch S-18 | Closed | Upstream path staged |
| 19:00:41 | Switch S-22 | Closed | Riverside path staged |
| 19:06:10 | R12 breaker | Closed | Normal source restored |

## Switching order

| Step | Time | Action | Authority | Cumulative restored |
| --- | --- | --- | --- | --- |
| 1 | 16:05 | Open S-18 | Crew A / Control | 0 |
| 2 | 16:31 | Open S-22 | Crew B / Control | 0 |
| 3 | 16:47 | Test Maple lateral | Crew A | 0 |
| 4 | 17:11 | Verify DER-44 at 0 kW | System control | 0 |
| 5 | 17:18 | Close tie T-7 | Crew C / Control | 4,820 |
| 6 | 18:05 | Replace and test F-12B | Crew A | 6,140 |
| 7 | 18:42 | Patrol Riverside taps | Crew B | 6,140 |
| 8 | 18:55 | Close S-18 | Crew A / Control | 6,140 |
| 9 | 19:00 | Close S-22 | Crew B / Control | 6,140 |
| 10 | 19:06 | Close R12 breaker | System control | 8,960 |
| 11 | 19:32 | Open T-7 / normalize | Crew C / Control | 8,960 stable |

| Role | Name | Signed |
| --- | --- | --- |
| Switching authority | N. Ortega | 2 Jul 19:40 |
| Field lead | R. Mehta | 2 Jul 19:44 |
| Control desk | A. Patel | 2 Jul 19:45 |

## Feeder one-line and DER clearance

Directed feeder relations: R12 bay -> S-18 (normal feed); S-18 -> F-12B (Maple lateral); F-12B -> S-22 (12R trunk); S-22 -> Riverside (12R load); S-22 -> T-7 (tie branch); T-7 -> Hospital (temporary backfeed); Feeder 9Q -> T-7 (9Q source); DER-44 -> F-12B (PV backfeed risk).

| Clearance item | Operator entry | Field confirmation | State |
| --- | --- | --- | --- |
| DER-44 disconnect | Open 17:06 | Visible at POI | Accepted |
| SCADA output | 0 kW 17:11 | Stable 5 min | Accepted |
| Feeder 9Q load | 74% after transfer | Below emergency rating | Accepted |
| Reverse power | None | Relay 67P clear | Accepted |
| Hospital ATS | Normal source lost | T-7 source accepted | Accepted |
| T-7 permission | Issued 17:16 | Close at 17:18 | Accepted |
| DER restore | After normalize | Site call 19:34 | Deferred |

## Restoration progression and customer impact

OMS cumulative restoration: 15:42 = 0, 16:31 = 0, 17:18 = 4,820, 18:05 = 6,140, 19:06 = 8,960, 19:32 = 8,960. The parent-block increments are 4,820 at 17:18, 1,320 at 18:05, and 2,820 at 19:06, totaling 8,960. The 19:32 value is normalization, not a new customer restoration. Critical-service rows are nested callouts and must not be added again.

| Segment | Customers | Critical load | Restored |
| --- | --- | --- | --- |
| 9Q transfer block | 4,820 | Includes hospital + TS-12 | 17:18 |
| Hospital loop | 1,240 | Hospital | 17:18 |
| TS-12 | 1 service | Traffic signal | 17:18 |
| Maple tested block | 1,320 | Includes care home spur | 18:05 |
| Care home spur | 86 | Assisted living | 18:05 |
| Riverside / industrial block | 2,820 | Includes LS-4 | 19:06 |
| LS-4 | 1 service | Lift station | 19:06 |

## Patrol field media

P1 F-12B at 16:18 shows a blackened split polymer cutout barrel under the phase-B conductor. P2 Maple span at 16:23 shows a clear span with vegetation set back and no branch contact. P3 S-18 at 16:31 shows the switch blade open with a yellow S-18 OPEN hold tag.

## Draft report and reviewer markup

Revision 1 preliminary cause TREE CONTACT is struck out and revised to failed polymer cutout F-12B. Hospital restoration 18:05 is struck and corrected to 17:18 via T-7. DER-44 status is corrected to curtailed at 17:11. Weather is context; P2 rules out tree contact.

| Evidence | Observed state | Use in Revision 2 |
| --- | --- | --- |
| Photo P1 | Split / char at F-12B | Supports equipment failure |
| Photo P2 | Clear span / no contact | Rejects tree-contact draft |
| Relay 50G | Single phase-ground impulse | Matches failed cutout |
| Cutout tag F12B-882 | Polymer barrel split | Asset-lab teardown |
| Lightning log | None within 5 miles | Not causal |

## Revision 2 final investigation and notice

| Control field | Final value | Basis |
| --- | --- | --- |
| Cause | Failed polymer cutout F-12B | P1 + relay + tag F12B-882 |
| Hospital restoration | 17:18 | T-7 switching step 5 |
| All customers restored | 19:06 | R12 close / OMS |
| DER-44 | Curtailed 17:11 | 0 kW before T-7 close |
| Major-event threshold | No | 8,960 customers / 3 h 24 m |
| Follow-up | WO-7714 | Replace peer cutouts / lab teardown |

| Recipient | Channel | Due / sent | Payload |
| --- | --- | --- | --- |
| Hospital liaison | Phone | Sent 17:21 | Backfeed restored |
| City OEM | Email | Sent 18:12 | Critical-load update |
| State PUC log | Portal | Due 05 Jul 12:00 | Below major threshold |
| DER owner | Phone | Sent 19:34 | Normalization complete |
| Asset engineering | Work order | Sent 03 Jul 09:05 | F12B-882 teardown |
| Vegetation contractor | No dispatch | Not required | P2 rules out tree contact |

Final signoff: Operations/N. Ortega checked at 09:12; Protection/R. Mehta checked at 10:44; Regulatory/S. Kim checked at 11:20; Vegetation is disabled/not required.
