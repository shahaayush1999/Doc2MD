# Northstar Cold Chain Supplier Cutover Authorization

## 1. Regional cold-storage cutover approval

| Field | Controlled value | Field | Controlled value |
| --- | --- | --- | --- |
| File | SV-2048 | Revision | D |
| Prepared | 08 Jul 2026 | Effective | 10 Jul 2026 09:30 MST |
| Sites | Phoenix and Tucson | Coordinator | Avery Kim |

Northstar will transfer eligible Phoenix and Tucson inventory from Kestrel Logistics to Boreal Storage during the 14-15 July maintenance window. The change includes telemetry migration, physical custody transfer, invoice routing, and eventual closure of Kestrel credentials. Quarantined inventory remains under Northstar quality control.

| Priority | Record | Controls | Does not control |
| --- | --- | --- | --- |
| 1 | Page 5 final authorization | GO/HOLD state and release conditions | Individual rate details |
| 2 | Page 4 exception register | Exception scope, owner, and closure evidence | Commercial ceiling |
| 3 | Page 3 finance validation | Authorized cost ceiling and invoice route | Operational release |
| 4 | Page 2 cutover workplan | Task sequence, windows, and task gates | Final authorization |
| Reference | Email and meeting notes | Context only when cited by a controlled row | Any approval or closure |

A lower-priority record may supply detail but cannot reverse a higher-priority state. Closure applies only to the obligation named in the exception row. SV-2048 was prepared 08 Jul 2026 and became effective 10 Jul 2026 at 09:30 MST.

| Step | Owner | Required review | Exit record |
| --- | --- | --- | --- |
| 1 | Cutover lead | Sequence and operational gates | Page 2 workplan |
| 2 | Finance | Ceiling, PO, and invoice routing | Page 3 validation |
| 3 | Functional owners | Exception scope and evidence | Page 4 register |
| 4 | Sponsor and quality | Selective GO/HOLD authorization | Page 5 final record |

## 2. Cutover workplan and handoff sequence

| ID | Site / asset | Activity | Owner | Planned window | Gate / evidence | State |
| --- | --- | --- | --- | --- | --- | --- |
| T-01 | Phoenix / Dock 4 | Reserve the temperature-controlled bay; retain Kestrel access until EX-07 is signed. | Avery Kim | 14 Jul 22:00-23:00 MST | Facilities call FC-119 and access list AC-44 | READY |
| T-02 | Phoenix / Sensor P-14 | Move telemetry from Kestrel gateway KG-2 to Boreal gateway BG-5; preserve 15-minute data. | Lin Chen | 14 Jul 23:00-23:40 MST | Parallel-read delta <=0.3 C for 30 minutes | CONDITIONAL |
| T-03 | Tucson / Cage C | Seal returned Kestrel inventory and complete a dual count before carrier release. | Mateo Soto | 15 Jul 00:15-01:00 MST | Dual count sheet IC-882 | READY |
| T-04 | Phoenix / Lot PX-771 | Transfer 48 pallets only after the T-02 telemetry gate passes. | Rina Singh | 15 Jul 00:30-02:10 MST | Scan batch SC-77; zero orphan pallets | BLOCKED BY T-02 |
| T-05 | Tucson / Lot TZ-219 | Transfer 26 pallets and exclude six quarantined cases held under QA-61. | Jordan Cole | 15 Jul 01:20-02:20 MST | QA release QR-203 for eligible stock | READY |
| T-06 | Both sites / credentials | Close Kestrel credentials after inventory reconciliation and legal waiver confirmation. | Avery Kim | 15 Jul 04:30 MST | REC-2048 has zero unresolved items and EX-07 is signed | PENDING |

Approver sidebar, 08 Jul - Avery Kim: keep Kestrel Dock 4 access active until counsel signs EX-07. This margin note is advisory; page 5 controls release.

T-02 gates the PX-771 transfer in T-04. EX-07 does not block physical transfer; it blocks T-06 credential closure. T-05 may move only eligible Tucson stock while the six QA-61 cases remain segregated.

**Handoff matrix**

| Trigger | Notify | Channel | Required content |
| --- | --- | --- | --- |
| T-02 passes | Phoenix floor lead | Bridge BR-2048 | P-14 delta and validation end time |
| T-04 completes | Inventory control | Queue IC-WEST | PX-771 pallet count and orphan count |
| Any temperature breach | Quality on-call | QA hotline | Sensor, duration, peak delta, and lot |
| Rollback invoked | Both site leads | Bridge BR-2048 | Last completed task and custody location |

Invoke RB-12 if a temperature deviation exceeds 1.0 C for 10 continuous minutes. Stop the active transfer, preserve custody at the last confirmed location, and report the last completed task on bridge BR-2048.

## 3. Commercial validation and invoice routing

| Line | Basis | Amount | Approval condition |
| --- | --- | --- | --- |
| Boreal implementation | Quote Q-884 revision C | $18,600 | Fixed fee |
| Kestrel overlap | Two nights at $2,160 | $4,320 | Maximum two nights |
| Sensor validation | Work order TV-19 | $2,150 | P-14 parallel read |
| Contingency | Legal-delay allowance | $3,000 | Available only if EX-07 extends |

| Control | Value | Interpretation |
| --- | --- | --- |
| Base committed cost | $25,070 | Implementation, overlap, and sensor validation |
| Conditional contingency | $3,000 | Usable only while EX-07 extends the overlap |
| Not-to-exceed ceiling | $28,070 | Requires finance reapproval if exceeded |

| Vendor | PO | Cost center | Reviewer | Route |
| --- | --- | --- | --- | --- |
| Boreal Storage | 44018-3 | CC-7420 | Jonah Mercer | AP-West / transition |
| Kestrel Logistics | 44007-9 | CC-7420 | Jonah Mercer | AP-West / overlap |
| ThermoVision | 43991-2 | CC-7314 | Nadia Brooks | AP-Quality / validation |

Finance validates the ceiling and invoice route. It does not declare an exception closed, satisfy a task gate, or authorize physical release. Unused contingency is not committed spend.

Raster finance stamp: Jonah Mercer; 09 Jul 2026 16:42 MST; ceiling $28,070; control VC-2048; cost validation is not operational release.

## 4. Exception and closure-evidence register

| Exception | Affected obligation | Current finding | Owner | Due | Accepted closure evidence | State |
| --- | --- | --- | --- | --- | --- | --- |
| E-05 | T-02 telemetry gate | Parallel baseline differs by 0.2 C after probe alignment. | Lin Chen | 09 Jul 15:00 MST | Signed TV-19 trace with 30-minute comparison | CLOSED |
| EX-07 | T-06 credential closure | Kestrel access waiver is with counsel; physical cutover may proceed while access is retained. | Isha Patel | 14 Jul 18:00 MST | Countersigned waiver WA-771 | OPEN |
| E-08 | T-05 Tucson inventory | Six QA-61 cases remain quarantined and are outside the eligible transfer quantity. | Dara Nwosu | 15 Jul 01:00 MST | QR-203 release or segregated custody receipt | OPEN - EXCLUDE |
| E-09 | Boreal invoice route | Draft purchase order omitted the transition suffix. | Jonah Mercer | 09 Jul 12:00 MST | Issued PO 44018-3 | CLOSED |
| E-11 | T-03 carrier release | Carrier arrival is forecast at 01:10, ten minutes after the planned count window. | Mateo Soto | 15 Jul 00:30 MST | Dispatch update in BR-2048 and revised custody time | WATCH |
| E-12 | Tucson backup power | Backup power transfer test passed in 46 seconds against the 60 second limit. | Jordan Cole | 09 Jul 17:00 MST | Facilities test certificate FT-662 | CLOSED |

| Marker | Meaning | Operational consequence |
| --- | --- | --- |
| CLOSED | Listed evidence was accepted for that row | No effect on unrelated exceptions |
| OPEN - EXCLUDE | Affected inventory stays out of the authorized quantity | Eligible inventory may proceed |
| WATCH | Monitor and update the stated evidence channel | Continue unless a final condition fails |

Email acknowledgment is context only unless the relevant row cites it as accepted evidence. The signed page 5 authorization controls GO/HOLD state; the finance validation controls cost only.

## 5. Final implementation authorization

**PHYSICAL CUTOVER: GO.** Begin at 14 Jul 2026 22:00 MST for eligible inventory only. **KESTREL CREDENTIAL DECOMMISSION: HOLD** until C-3 is satisfied.

| Condition | Required state before action | Action governed | Failure response |
| --- | --- | --- | --- |
| C-1 | P-14 parallel-read delta <=0.3 C for 30 minutes | Start T-04 | Hold PX-771 at Phoenix |
| C-2 | Six QA-61 cases remain segregated unless QR-203 releases them | Start T-05 | Move eligible stock only |
| C-3 | EX-07 signed and REC-2048 has zero unresolved items | Close Kestrel credentials | Retain access and escalate |
| C-4 | No temperature deviation >1.0 C for 10 continuous minutes | Continue physical transfer | Invoke rollback RB-12 |

The GO decision permits the physical cutover; it does not close EX-07, release the six QA-61 cases, or waive telemetry and rollback gates. The finance stamp validates cost only. Page 4 remains the source for exception ownership and evidence.

| Role | Name | Decision | Recorded |
| --- | --- | --- | --- |
| Executive sponsor | Mara Velez | Approved | 10 Jul 2026 09:12 MST |
| Cutover lead | Avery Kim | Accepted | 10 Jul 2026 09:18 MST |
| Quality | Dara Nwosu | Approved with QA-61 exclusion | 10 Jul 2026 09:26 MST |
| Legal exception owner | Isha Patel | EX-07 remains open; not a release signature | Review due 14 Jul 18:00 MST |

Revision D supersedes Draft C. This authorization became effective at 10 Jul 2026 09:30 MST. The next control event is the first failed condition, completed rollback, or closure of C-3, whichever occurs first.
