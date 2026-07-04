# Helio Therapeutics HTX-204 Site 014 Monitoring Packet

Monitor visit 2026-05-08, data cut 2026-05-06. Site 014 is not clean-ready. Major open items are DEV-014-03 missed W2 ECG for subject 014-003 and DEV-014-07 temperature excursion for kit K-204-153. Subject 014-004 withdrew after related dizziness.

## Packet Overview
Site 014 / Harbor Endocrine was monitored by L. Sen on 2026-05-08 with data cut 2026-05-06. The overview identifies enrollment, visit grid, labs, AE/deviation, IP accountability, and query/final sections. The monitor conclusion says the site is not clean-ready.

## Enrollment
| Subject | Status | Date | Arm / reason | Note |
| --- | --- | --- | --- | --- |
| 014-001 | screen fail | 2026-04-03 | HbA1c 9.1% | not randomized |
| 014-002 | randomized | 2026-04-05 | Arm B | completed W4 |
| 014-003 | randomized | 2026-04-07 | Arm A | missed W2 ECG |
| 014-004 | withdrawn | 2026-04-10 | Arm B | AE dizziness |
| 014-005 | randomized | 2026-04-12 | Arm A | completed W4 |
| 014-006 | screen fail | 2026-04-15 | eGFR 42 | not randomized |
| 014-007 | randomized | 2026-04-18 | Arm B | IP temperature excursion |
| 014-008 | randomized | 2026-04-20 | Arm A | central lab pending |

## Visit Schedule
| Subject | Visit | Date | State | Kit | Note |
| --- | --- | --- | --- | --- | --- |
| 014-002 | V1 | 04-05 | done | kit K-204-118 | ECG normal |
| 014-002 | W2 | 04-19 | done | kit K-204-142 | diary returned |
| 014-002 | W4 | 05-03 | done | kit K-204-166 | dose reduced |
| 014-003 | V1 | 04-07 | done | kit K-204-121 | ECG missing |
| 014-003 | W2 | 04-21 | partial | kit K-204-146 | ECG not done |
| 014-004 | V1 | 04-10 | done | kit K-204-128 | AE onset |
| 014-004 | W2 | 04-24 | withdrawn | - | early termination |
| 014-007 | V1 | 04-18 | done | kit K-204-153 | temp excursion |

## Labs
| Subject | Test | Result | Flag | Reference | Unit |
| --- | --- | --- | --- | --- | --- |
| 014-002 | ALT | 38 |  | 0-45 | U/L |
| 014-002 | Creatinine | 1.11 |  | 0.60-1.30 | mg/dL |
| 014-003 | ALT | 67 | H | 0-45 | U/L |
| 014-003 | eGFR | 58 | L | >=60 | mL/min |
| 014-004 | Hemoglobin | 10.8 | L | 12.0-16.0 | g/dL |
| 014-007 | Potassium | 5.6 | H | 3.5-5.1 | mmol/L |

## Adverse Events
| AE | Subject | Term | Severity | Relatedness | Outcome |
| --- | --- | --- | --- | --- | --- |
| AE-014-01 | 014-004 | dizziness | moderate | related | withdrawn 2026-04-24 |
| AE-014-02 | 014-002 | nausea | mild | possibly related | dose reduced W4 |
| AE-014-03 | 014-007 | hyperkalemia | moderate | unrelated | repeat lab normal |

## Deviations
| Deviation | Subject | Description | Class | Status/action |
| --- | --- | --- | --- | --- |
| DEV-014-03 | 014-003 | W2 ECG missed | major | open query Q-77 |
| DEV-014-07 | 014-007 | IP temp 9.1C for 3h | major | do not dose kit K-204-153 |
| DEV-014-02 | 014-002 | diary page late | minor | resolved |

## IP Accountability
| Kit | Subject | Dispensed | Returned | Temp flag | Final state |
| --- | --- | --- | --- | --- | --- |
| K-204-118 | 014-002 | 30 | 4 | none | accounted |
| K-204-142 | 014-002 | 30 | 6 | none | accounted |
| K-204-166 | 014-002 | 15 | 2 | none | dose reduced |
| K-204-121 | 014-003 | 30 | 5 | none | accounted |
| K-204-146 | 014-003 | 30 | not returned | none | open |
| K-204-153 | 014-007 | 0 | quarantined | 9.1C for 3h | do not dose |

## Temperature Excursion Source
| Time | Temp | Action |
| --- | --- | --- |
| 04-18 09:10 | 8.4C | alarm |
| 04-18 10:10 | 9.1C | quarantine K-204-153 |
| 04-18 12:10 | 7.8C | still above range |
| 04-18 13:05 | 5.2C | returned to range |
Kit K-204-153 must not be dosed; the dispense count is zero even though the kit appears in the visit source.

## ECG Source and Query Q-77
| Field | Visible state |
| --- | --- |
| Subject | 014-003 |
| Visit | W2 / 2026-04-21 |
| ECG checkbox | unchecked |
| Reason | machine unavailable |
| Query | Q-77 open; PI response pending |
The missed ECG is a major deviation and remains open.

## Concomitant Medication Review
| Subject | Medication | Start | Stop | Relevance |
| --- | --- | --- | --- | --- |
| 014-002 | metformin | baseline | ongoing | allowed |
| 014-004 | meclizine | 04-11 | 04-24 | AE dizziness |
| 014-007 | potassium supplement | 04-01 | 04-19 | hyperkalemia context |
Potassium supplement context does not make AE-014-03 related to study drug.

## Monitor Query Log
| Query | Subject | Issue | State |
| --- | --- | --- | --- |
| Q-74 | 014-004 | AE stop date | answered |
| Q-77 | 014-003 | W2 ECG missing | open |
| Q-81 | 014-007 | temperature excursion dosing | answered: do not dose |
| Q-84 | 014-008 | central lab pending | open |
Open queries are Q-77 and Q-84. Q-81 is answered.

## eCRF Checkbox Audit
| Subject | Field | Visible state | Data entry |
| --- | --- | --- | --- |
| 014-003 | W2 ECG performed | unchecked | blank |
| 014-004 | Withdrawal due to AE | checked | dizziness |
| 014-007 | Kit dispensed | unchecked | quarantined |
| 014-008 | Central lab reviewed | unchecked | pending |
Unchecked boxes must not be treated as blank text omissions.

## Sample Shipment Manifest
| Shipment | Subject | Tube | Drawn | Received | State |
| --- | --- | --- | --- | --- | --- |
| SH-204-44 | 014-002 | PK-2 | 04-19 08:12 | 04-20 09:02 | accepted |
| SH-204-45 | 014-003 | PK-2 | 04-21 08:44 | 04-23 16:40 | temperature late |
| SH-204-46 | 014-008 | central lab | 04-20 09:15 | pending | not reviewed |
Shipment SH-204-45 is accepted with a late-temperature note, not rejected.

## Data Cleaning Readiness
| Domain | Open | Critical blocker |
| --- | --- | --- |
| Enrollment | 0 | none |
| ECG | 1 | Q-77 / 014-003 |
| Drug accountability | 1 | K-204-153 quarantine |
| Central lab | 1 | 014-008 pending |
| AE | 0 | none |
Site is not clean-ready because ECG, IP accountability, and central lab remain open.

## Principal Investigator Signoff
| Statement | Visible state |
| --- | --- |
| PI reviewed AE-014-01 | checked |
| PI reviewed DEV-014-03 | unchecked |
| PI reviewed DEV-014-07 | checked |
| Clean-ready attestation | unchecked |
| Signed by | Dr. Neha Rao / 2026-05-08 |
Clean-ready attestation is unchecked.

## Final Monitor Recap
| Control item | Final state |
| --- | --- |
| Site clean-ready | No |
| Critical subject | 014-003 |
| Critical kit | K-204-153 |
| Open queries | Q-77 and Q-84 |
| Withdrawn subject | 014-004 due related dizziness |
| Do not dose | K-204-153 |
This final recap controls the site status.