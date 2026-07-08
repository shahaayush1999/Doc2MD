# MetroGrid Outage OI-26-731 Feeder 12R

Outage started 2026-07-02 15:42 and normal restoration was at 19:06 for 8,960 customers. Final cause is failed polymer cutout F-12B, not the draft tree-contact note. Cutout tag F12B-882 was sent to the asset lab.

## SCADA Alarm Sequence
| Time | Device | State | Note |
| --- | --- | --- | --- |
| 15:42:11 | R12 breaker | trip | phase B ground |
| 15:42:14 | Recloser 12R-3 | lockout | third shot |
| 15:42:19 | Relay 50G | pickup | 7.8 kA momentary |
| 15:43:02 | Cap bank CB-4 | offline | voltage sag |
| 15:44:33 | OMS | 8,960 out | nested outage created |
| 16:05:20 | Switch S-18 | opened | crew isolation |
| 16:31:05 | Switch S-22 | opened | Riverside isolated |
| 17:11:00 | DER-44 | 0 kW | curtailment verified |
| 17:18:44 | Tie T-7 | closed | backfeed hospital |
| 18:05:02 | F-12B | replaced | Maple lateral test passed |
| 19:06:10 | R12 breaker | closed | normal restored |

## One-Line Diagram
R12 bay feeds S-18, F-12B, S-22, Riverside, T-7 tie, Hospital loop, and DER-44 PV. F-12B is the fault point. T-7 ties to feeder 9Q and backfeeds the hospital after DER-44 is curtailed.

## Switching
| Step | Time | Action | Crew | Customers restored |
| --- | --- | --- | --- | --- |
| 1 | 16:05 | open S-18 | Crew A | 0 |
| 2 | 16:31 | open S-22 | Crew B | 0 |
| 3 | 16:47 | test Maple lateral | Crew A | 0 |
| 4 | 17:11 | verify DER-44 at 0 kW | Control | 0 |
| 5 | 17:18 | close T-7 | Crew C | 4,820 |
| 6 | 18:05 | replace cutout F-12B | Crew A | 6,140 |
| 7 | 18:42 | patrol Riverside taps | Crew B | 6,140 |
| 8 | 19:06 | close R12 breaker | Control | 8,960 |
| 9 | 19:32 | normalize T-7 | Crew C | all stable |

## Customer Impact
| Segment | Customers | Critical load / note | Restored |
| --- | --- | --- | --- |
| Maple lateral | 2,820 | 0 | 18:05 |
| Maple care home spur | 86 | assisted living | 18:05 |
| Hospital loop | 1,240 | 1 hospital | 17:18 |
| Riverside apartments | 3,100 | 2 elevators | 19:06 |
| Industrial park | 1,800 | 0 | 19:06 |
| Traffic signal cabinet TS-12 | 1 service | intersection | 17:18 |
| Lift station LS-4 | 1 service | wastewater | 19:06 |

Critical customer notifications:
| Recipient | Segment | Time | Method | Message state |
| --- | --- | --- | --- | --- |
| Hospital facility desk | Hospital loop | 16:04 | phone | ETA pending |
| Hospital facility desk | Hospital loop | 17:21 | phone | restored via T-7 |
| City traffic | TS-12 | 17:25 | radio | signal power back |
| Wastewater duty officer | LS-4 | 18:18 | phone | awaiting feeder close |
| Industrial park contact | Industrial park | 19:09 | email | normal restored |
| Care home manager | Maple care home spur | 18:08 | phone | restored after F-12B change |

## Evidence
| Evidence | Visible value | Finding |
| --- | --- | --- |
| Weather radar | cell passed 15:36-15:50 | wind gust context |
| Patrol photo P1 | char mark at F-12B | failed cutout |
| Patrol photo P2 | clear span; no branch contact | tree cause superseded |
| SCADA | phase B ground | matches F-12B |
| Relay oscillography | single phase-to-ground impulse | not lightning signature |
| DER log | DER-44 curtailed 17:11 | safe backfeed |
| Cutout tag | F12B-882 polymer barrel split | removed for lab |
| Draft report | tree contact | superseded |
| Final report | failed polymer cutout F-12B | controls |

Lab disposition: cutout barrel F12B-882 has polymer split and is archived by Protection; Kearney 65K fuse link has melt pattern consistent and is reviewed by Asset Engineering; crossarm has no flashover trace; tree sample was not collected because vegetation was not applicable.

## Crew Patrol Photo Sheet
The field-media register preserves P1 F-12B char mark supporting failed cutout, P2 clear span/no tree contact superseding the draft tree cause, P3 S-18 open tag, and P4 T-7 backfeed tag.

## DER Backfeed Clearance
| Check | Value | State |
| --- | --- | --- |
| DER-44 output | 0 kW at 17:11 | curtailed |
| Visible open point | S-22 open | confirmed |
| T-7 close | 17:18 | allowed after clearance |
| Reverse power alarm | none | safe |
| Clearance item | Operator entry | Field confirmation | Release state |
| --- | --- | --- | --- |
| DER-44 disconnect | open 17:06 | visible at POI | accepted |
| SCADA output | 0 kW at 17:11 | telemetry stable 5 min | accepted |
| Feeder 9Q load | 74% after transfer | under emergency rating | accepted |
| Reverse power | none | relay 67P clear | accepted |
| Hospital ATS | normal source lost | T-7 source accepted | accepted |
| T-7 permission | issued 17:16 | close allowed 17:18 | accepted |
| DER restore | after normalize | 19:34 call to site | deferred |
| Site acknowledgment | R. Valdez 19:36 | DER owner confirms | logged |
The T-7 close is valid only after SCADA output, field-visible disconnect, feeder 9Q load, hospital ATS state, and reverse-power relay are accepted. DER restore is deferred until after feeder normalization and site acknowledgment by R. Valdez at 19:36.

## Draft Report Excerpt
| Draft field | Draft value | Final value |
| --- | --- | --- |
| Cause | tree contact | failed polymer cutout F-12B |
| Hospital restore | 18:05 | 17:18 |
| DER status | not mentioned | curtailed 17:11 |
| Revision item | Draft entry | Reviewer mark | Final treatment |
| --- | --- | --- | --- |
| Cause | tree contact | crossed in red | failed polymer cutout F-12B |
| Hospital restore | 18:05 | circled time mismatch | 17:18 via T-7 |
| DER status | not mentioned | blue margin note | curtailed 17:11 |
| Weather | primary cause | downgraded | context only |
| Photo P2 | not referenced | added by reviewer | no tree contact |
This draft excerpt remains visible context, but the final investigation signoff controls cause, hospital restoration time, and DER status.

## Final Investigation Signoff
| Signer | Role | Visible state |
| --- | --- | --- |
| N. Ortega | Distribution Ops | signed 2026-07-03 09:12 |
| R. Mehta | Protection Eng | signed 2026-07-03 10:44 |
| S. Kim | Regulatory | signed 2026-07-03 11:20 |
| Tree crew | not required | blank |
| Review gate | Owner | Visible state | Exception |
| --- | --- | --- | --- |
| Ops sequence | N. Ortega | signed 09:12 | none |
| Protection review | R. Mehta | signed 10:44 | F-12B curve attached |
| Regulatory review | S. Kim | signed 11:20 | major-event no |
| Vegetation review | Tree crew | blank | not required |
| DER review | A. Patel | initialed 10:58 | restore after normalize |
The blank tree-crew line is intentional because vegetation was ruled out.

## Regulatory Notice
| Field | Value | Note |
| --- | --- | --- |
| Major event | No | below threshold |
| Critical customer | 1 hospital | restored 17:18 |
| Notice due | 2026-07-05 12:00 | internal |
| Cause category | equipment failure | polymer cutout |
| Recipient | Channel | Due / sent | Payload note |
| --- | --- | --- | --- |
| Hospital liaison | phone | sent 17:21 | backfeed restored |
| City OEM | email | sent 18:12 | critical customer update |
| State PUC log | portal | due 2026-07-05 12:00 | below major threshold |
| Internal claims | ticket | sent 2026-07-03 08:40 | equipment failure category |
| DER owner | phone | sent 19:34 | normalization complete |
| Asset engineering | work order | sent 2026-07-03 09:05 | F12B-882 lab teardown |
| Vegetation contractor | no dispatch | not required | P2 ruled out tree contact |
The PUC portal item is due even though the incident is below the major-event threshold. Asset engineering receives work order follow-up for F12B-882; vegetation contractor is not dispatched because P2 ruled out tree contact.

## Final Restoration Recap
| Control item | Final state | Evidence |
| --- | --- | --- |
| Cause | failed F-12B cutout | patrol photo + SCADA |
| Hospital | restored 17:18 | T-7 backfeed |
| All customers | restored 19:06 | R12 breaker close |
| Draft tree contact | superseded | no tree contact photo |
| DER-44 | curtailed 17:11 | safe backfeed |
| Metric | Final value | Source | Reviewer note |
| --- | --- | --- | --- |
| CAIDI window | 3h 24m | OMS export | exclude 19:32 normalize |
| Critical restoration | 95 minutes | T-7 close | hospital priority |
| Customers interrupted | 8,960 | OMS | same as overview |
| Cause code | equipment failure | final report | not weather |
| Follow-up WO | WO-7714 | asset replacement | cutout audit route |
The 19:32 normalization step is operating cleanup, not customer restoration. Customer restoration stops at the 19:06 R12 breaker close.