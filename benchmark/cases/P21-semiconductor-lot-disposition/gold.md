# Lot Q8R7-22 Material Review File

## Lot traveler and process source

| Step | Tool | Recipe | Start | End | Recorded state |
| --- | --- | --- | --- | --- | --- |
| Implant P3 | IMP-17 | BORON_LVT_042 | 05:12 | 05:58 | Accepted |
| Ash | ASH-04 | ASH_STD_18 | 06:10 | 06:34 | Accepted |
| Wet clean | WET-12 | SC1_SC2_09 | 06:48 | 07:22 | Accepted |
| PVD TiN | PVD-03 | TIN_GATE_31 | 08:06 | 09:44 | Alarm 09:18 |
| Anneal | RTP-08 | RTP_LVT_22 | 10:01 | 10:29 | Accepted |
| Metrology | CDSEM-06 | GATE_LVT_QC | 10:45 | 11:56 | Reviewed |

| Source | Recipe shown | State | Use for this lot |
| --- | --- | --- | --- |
| Traveler page | TIN_GATE_31 | Current | Yes |
| PVD alarm printout | TIN_GATE_30 | Stale cached header | No |
| MES audit event | TIN_GATE_31 | Confirmed | Yes / controls |
| Engineer note | Increase clamp purge | Future revision | Not used |

TIN_GATE_31 controls the actual lot run; TIN_GATE_30 is a stale alarm-printout header and the clamp-purge change is future only.

## Wafer-map review

Wafer 03 C3 cells: B4, C4, B5. Wafer 05 S2 cells: E2, F2, E3. Wafer 07 M1 cells: D5, D6, E5. Wafer 09 P4 cell: F3. Wafer 12 E1 cells: A6, B6. Wafer 02 E0 reference cell: A1.

| Code | Class | Map color | Disposition gate |
| --- | --- | --- | --- |
| M1 | Metal flake | Red | Scrap cluster |
| S2 | Scratch | Orange | Engineering hold |
| E1 | Edge bead | Yellow | Engineering hold |
| P4 | Parametric drift | Blue | Reliability condition |
| C3 | Center CD cluster | Violet | Remeasure / MRB |
| E0 | Edge mark | Gray | Reference only |

## CD-SEM metrology review

| Wafer / site | CD nm | Delta nm | Flag | Image ref | Reviewer note |
| --- | --- | --- | --- | --- | --- |
| 03 / B4 | 27.8 | +2.9 | H | IMG-221 | Matches C3 map |
| 03 / C4 | 27.4 | +2.5 | H | IMG-222 | Adjacent high |
| 05 / E2 | 24.1 | -0.8 | L-map | IMG-223 | Scratch path |
| 07 / D5 | 29.6 | +4.7 | H | IMG-224 | Flake shadow |
| 07 / D6 | 29.1 | +4.2 | H | IMG-225 | Adjacent flake |
| 09 / F3 | 26.8 | +1.9 | Watch | IMG-226 | Parametric only |
| 12 / A6 | 22.9 | -2.0 | L | IMG-227 | Edge bead |

| Rule | Condition | Required action |
| --- | --- | --- |
| CD-H | Delta >= +2.5 nm | MRB disposition |
| CD-L | Delta <= -2.0 nm | MRB disposition |
| Map correlation | Defect code at measured site | Review image and map together |
| Yield exception | Wafer yield >93% | Does not waive action-limit review |

## PVD thickness SPC and alarm interlocks

SPC points: R-2241 41.2 nm (Inside), R-2242 42.0 nm (Inside), R-2243 43.8 nm (Inside), R-2244 45.6 nm (Warning), R-2245 47.4 nm (Above UCL), R-2246 46.2 nm (Warning), R-2247 44.1 nm (Recovered). Warning is 45.0 nm and UCL is 47.0 nm.

| Interlock | Observed | Threshold | State | Disposition |
| --- | --- | --- | --- | --- |
| Chamber pressure | 4.8 mTorr | <=5.0 | Pass | Not root cause |
| Clamp purge | 18.1 slm | >=19.0 | Fail | Future increase only |
| Ti target age | 81.4 kWh | <=85 | Watch | Clean then continue |
| Monitor residual | +1.7 nm | +/-1.0 | Fail | R-2245 review |
| Alarm ack | 09:18 / J. Kwon | Required | Complete | Containment starts |

## SEM review contact sheet

IMG-224 / W07 D5 shows two bright irregular metal flakes, including an adjacent smaller flake. IMG-223 / W05 E2 shows a long diagonal scratch crossing the field. IMG-227 / W12 A6 shows a bright edge-residue band with small bead deposits. IMG-226 / W09 F3 is visually clean apart from low-level background specks; its P4 issue is parametric rather than a visible particle.

## Defect classification and MRB decisions

| Code | Class | Count | Wafer | Gate |
| --- | --- | --- | --- | --- |
| M1 | Metal flake | 44 | 07 | Scrap |
| S2 | Scratch | 31 | 05 | Engineering hold |
| E1 | Edge bead | 27 | 12 | Engineering hold |
| P4 | Parametric drift | 19 | 09 | Conditional |
| C3 | Center CD cluster | 16 | 03 | Remeasure / hold |

| Item | Decision | Reason | Owner |
| --- | --- | --- | --- |
| Wafer 07 | Scrap | M1 at D5/D6/E5 | Y. Nishida |
| Wafer 05 | Hold | S2 crosses E2/F2/E3 | A. Roy |
| Wafer 03 | Hold | C3 high CD B4/C4/B5 | M. Alvarez |
| Wafer 12 | Hold | E1 at A6/B6 | K. Stone |
| Wafer 09 | Conditional | P4; REL-22-A required | S. Han |
| 01,02,04,06,08,10,11 | Release | Inside disposition limits | MRB |

## Reliability conditions and shipping allocation

| Sample | Wafer | Stress | Result | Disposition use |
| --- | --- | --- | --- | --- |
| REL-22-A | 09 | HTOL 168 h | Pending | Condition for shipment |
| REL-22-B | 02 | TC 100 cycles | Pass | Reference |
| REL-22-C | 11 | HAST 96 h | Pass | Reference |
| REL-22-D | 07 | Not built | Scrap | No reliability credit |

| Bucket | Wafers | Good die | Shipment condition |
| --- | --- | --- | --- |
| Release now | 01,02,04,06,08,10,11 | 127,759 | Standard COA |
| Conditional | 09 | 17,880 | Wait for REL-22-A pass |
| Engineering hold | 03,05,12 | 52,144 | Do not ship |
| Scrap | 07 | 16,902 | Exclude from yield and COA |

## Certificate holdback and final audit trail

| COA field | Signed value | Application |
| --- | --- | --- |
| Lot | Q8R7-22 | All wafers |
| Released wafers | 01,02,04,06,08,10,11 | Ship now |
| Conditional wafer | 09 | After REL-22-A pass |
| Engineering hold | 03,05,12 | Excluded |
| Scrap | 07 | Excluded from yield and COA |
| Executed recipe | TIN_GATE_31 | MES confirmed |

| Time | Actor | Entry | Effect |
| --- | --- | --- | --- |
| 10 Jun 12:18 | MES | PVD alarm attached | Containment starts |
| 10 Jun 14:40 | Yield engineering | Map review complete | 03/05/07/12 flagged |
| 11 Jun 08:55 | MRB | 07 scrap; 09 conditional | Disposition controls |
| 11 Jun 10:20 | Quality | COA holdback signed | Draft all-wafer COA void |
| 11 Jun 13:30 | Planning | Ship buckets created | 127,759 die release |

The preliminary all-wafer COA is void; only the signed COA values authorize shipment.
