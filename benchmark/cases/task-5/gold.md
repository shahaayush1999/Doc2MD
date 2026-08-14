# Northstar Cold Chain Supplier Cutover Authorization

## 1. Controlled precedence sheet

| Field | Controlled value | Field | Controlled value |
| --- | --- | --- | --- |
| File | SV-2048 | Revision | E |
| Issued | 12 Jul 2026 18:40 MST | Cutover start | 14 Jul 2026 22:00 MST |
| Controlled lots | PX-771 and TZ-219 | Coordinator | Avery Kim |

| Priority | Record | Controls | Does not control |
| --- | --- | --- | --- |
| 1 | Page 5 executed authorization | Selective GO/HOLD, exclusions, signed corrections | Rates or exception closure |
| 2 | Page 4 dependency / exception sheet | Directed gates, exception state, accepted evidence | Commercial ceiling |
| 3 | Page 3 approved reconciliation | Current rates, ceiling, and invoice route | Operational release |
| 4 | Page 2 cutover workplan | Sequence, windows, handoffs, and task gates | Final authorization |

A lower-priority record may add detail but cannot reverse the highest applicable controlled state.

## 2. Grouped cutover workplan

| ID | Group | Site / asset | Activity | Owner | Window | Gate / evidence | State |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T-01 | PHOENIX | Phoenix / Dock 4 | Reserve the controlled bay and verify that Kestrel access list AC-44 remains active. | Avery Kim | 14 Jul 21:15-21:45 | FC-119 acknowledged; AC-44 posted | READY |
| T-02 | PHX (cont.) | Phoenix / Sensor P-14 | Shift live telemetry from KG-2 to BG-5 while maintaining parallel capture. | Lin Chen | 14 Jul 21:45-22:25 | TV-19 delta <=0.3 C for 30 continuous min | CONDITIONAL |
| T-04 | PHX (cont.) | Phoenix / Lot PX-771 | Transfer 48 eligible pallets after T-02 and condition C-1 release the lot. | Rina Singh | 14 Jul 22:30-00:10 | SC-77: 48 moved; 0 orphan pallets | BLOCKED: T-02 |
| T-03 | TUCSON | Tucson / Cage C | Seal Kestrel returns and complete a dual count before custody release. | Mateo Soto | 14 Jul 22:05-22:45 | IC-882 signed by Northstar and carrier | READY |
| T-05 | TUS (cont.) | Tucson / Lot TZ-219 | Transfer 26 eligible pallets; keep six QA-61 cases segregated. | Jordan Cole | 14 Jul 22:50-00:00 | QR-203 or segregated-custody receipt | READY: EXCLUDE 6 |
| T-06 | BOTH SITES | Both sites / credentials | Reconcile both lots, then close Kestrel credentials only after the waiver. | Avery Kim | 15 Jul 00:20-01:00 | REC-2048 zero unresolved + EX-07 signed | HOLD |

| Trigger | Notify | Channel | Required content |
| --- | --- | --- | --- |
| T-02 passes | Phoenix floor lead | BR-2048 | P-14 final delta and validation end time |
| T-04 completes | Inventory control | IC-WEST | PX-771 moved count and orphan count |
| RB-12 invoked | Both site leads | BR-2048 | Last completed task and custody location |

When RB-12 is invoked, stop the active transfer, preserve custody at the last confirmed location, and report the last completed task on BR-2048.

## 3. Submitted-to-approved commercial reconciliation

| Line | Submitted / superseded | Approved / current | Approval note |
| --- | --- | --- | --- |
| Boreal implementation | ~~Q-884 rev B / $19,200~~ | Q-884 rev C / $18,600 | Fixed fee |
| Kestrel overlap | ~~3 nights / $6,480~~ | Maximum 2 nights / $4,320 | Only while EX-07 remains open |
| Sensor validation | TV-19 / $2,150 | TV-19 / $2,150 | No change |
| Contingency | ~~$4,500~~ | $3,000 | Only if EX-07 extends overlap |
| Request / ceiling | ~~Submitted total / $32,330~~ | NTE ceiling / $28,070 | Reapproval above ceiling |

| Vendor | PO | Cost center | Reviewer | Route |
| --- | --- | --- | --- | --- |
| Boreal Storage | 44018-3 | CC-7420 | Jonah Mercer | AP-West / transition |
| Kestrel Logistics | 44007-9 | CC-7420 | Jonah Mercer | AP-West / overlap |
| ThermoVision | 43991-2 | CC-7314 | Nadia Brooks | AP-Quality / validation |

Raster finance stamp: Jonah Mercer; 09 Jul 2026 16:42 MST; approved reconciliation; control RC-2048-E; cost validation is not operational release.

## 4. Dependency graph and exception register

- `T-01 -> T-02` - bay ready
- `T-02 -> C-1` - delta proof
- `C-1 -> T-04` - releases
- `T-02 -> T-04` - gates
- `T-03 -> T-05` - custody
- `E-08 -> T-05` - exclude 6
- `C-2 -> T-05` - eligible only
- `T-04 -> T-06` - reconcile PX
- `T-05 -> T-06` - reconcile TZ
- `EX-07 -> T-06` - waiver
- `C-3 -> T-06` - close access
- `C-4 -> RB-12` - breach
- `RB-12 -> T-04` - halts
- `RB-12 -> T-05` - halts

| Exception | Affected obligation | Current finding | Owner | Due | Accepted closure evidence | State |
| --- | --- | --- | --- | --- | --- | --- |
| E-05 | T-02 telemetry gate | Parallel baseline differs by 0.2 C after probe alignment. | Lin Chen | 12 Jul 15:00 MST | Signed TV-19 trace with 30-minute comparison | CLOSED |
| EX-07 | T-06 credential closure | Kestrel access waiver is with counsel; physical cutover may proceed while access is retained. | Isha Patel | 14 Jul 18:00 MST | Countersigned waiver WA-771 | OPEN |
| E-08 | T-05 Tucson inventory | Six QA-61 cases remain quarantined and are outside the eligible transfer quantity. | Dara Nwosu | 14 Jul 22:45 MST | QR-203 release or segregated custody receipt | OPEN - EXCLUDE |
| E-09 | Boreal invoice route | Draft purchase order omitted the transition suffix. | Jonah Mercer | 09 Jul 12:00 MST | Issued PO 44018-3 | CLOSED |
| E-11 | T-03 carrier release | Carrier arrival is forecast at 22:55, ten minutes after the planned count window. | Mateo Soto | 14 Jul 22:15 MST | Dispatch update in BR-2048 and revised custody time | WATCH |
| E-14 | T-04 scan evidence | Scanner SC-77B is the approved fallback if SC-77 loses sync. | Rina Singh | 14 Jul 22:20 MST | Both batch IDs recorded in IC-WEST | MONITOR |

## 5. Executed selective authorization

### Controlling decision

- [x] Physical cutover - GO
- [ ] Physical cutover - HOLD
- [ ] Kestrel credential decommission - RELEASE
- [x] Kestrel credential decommission - HOLD until C-3

### Inventory included

- [x] Phoenix PX-771 - 48 eligible pallets
- [x] Tucson TZ-219 - 26 eligible pallets
- [ ] QA-61 quarantine - six cases; excluded and retained in segregated custody

### Required gates

- [x] C-1 TV-19 delta <=0.3 C for 30 continuous min before T-04
- [x] C-2 QA-61 cases remain segregated before T-05
- [x] C-3 EX-07 signed + REC-2048 zero unresolved before T-06
- [x] C-4 Invoke RB-12 at selected continuous deviation

Rollback threshold: ( ) >0.5 C / 5 min; (x) >1.0 C / 10 continuous min; ( ) >1.5 C / 15 min.

### Executed correction

Cutover start: ~~14 JUL 2026 21:30 MST~~. Avery Kim corrected the handwritten current value to **14 JUL 2026 22:00 MST**, initialed **AK / 10 JUL 09:18**.

### Recorded signatures

- Executive sponsor Mara Velez - APPROVED - 10 Jul 2026 09:12 MST
- Cutover lead Avery Kim - ACCEPTED - 10 Jul 2026 09:18 MST
- Quality Dara Nwosu - APPROVED, QA-61 EXCLUDED - 10 Jul 2026 09:26 MST

Effective record: 10 Jul 2026 09:30 MST.
