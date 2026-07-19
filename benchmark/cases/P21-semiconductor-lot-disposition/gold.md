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

Wafer 03 shows a three-cell C3 cluster at B4, C4, and B5. Wafer 05's S2 coordinate set is E2, F2, and E3. Wafer 07 shows an adjacent M1 cluster at D5, D6, and E5. Wafer 09 marks only F3 as P4. Wafer 12 marks the A6 and B6 edge cells as E1. Wafer 02 marks only A1 as the gray E0 reference cell.

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

Chart reconstruction: the horizontal x-axis is run sequence and the vertical y-axis is TiN thickness in nm. The connected measured-series line represents PVD-03 TiN thickness. Blue points mean inside or recovered below the warning threshold; amber points mean warning at or above 45.0 nm but below 47.0 nm; a red point means above the 47.0 nm UCL. The amber dashed line is the 45.0 nm warning threshold and the red dashed line is the 47.0 nm UCL. The ordered run/value series rises from R-2241 / 41.2 through a peak at R-2245 / 47.4, then falls through R-2246 / 46.2 to R-2247 / 44.1.

| Interlock | Observed | Threshold | State | Disposition |
| --- | --- | --- | --- | --- |
| Chamber pressure | 4.8 mTorr | <=5.0 | Pass | Not root cause |
| Clamp purge | 18.1 slm | >=19.0 | Fail | Future increase only |
| Ti target age | 81.4 kWh | <=85 | Watch | Clean then continue |
| Monitor residual | +1.7 nm | +/-1.0 | Fail | R-2245 review |
| Alarm ack | 09:18 / J. Kwon | Required | Complete | Containment starts |

## SEM review contact sheet

The page labels only the archive frame and inspected site; the morphology must be recovered from each image. IMG-224 / W07 D5 shows two bright irregular metal flakes, including an adjacent smaller flake. IMG-223 / W05 E2 shows a long diagonal scratch crossing the field. IMG-227 / W12 A6 shows a bright edge-residue band with small bead deposits. IMG-226 / W09 F3 is visually clean apart from a fine-grained, speckled, or noisy low-level background texture.

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
| Wafer 07 | Scrap | Map W07-M1 plus IMG-224/225 | Y. Nishida |
| Wafer 05 | Hold | Map W05-S2 plus IMG-223 | A. Roy |
| Wafer 03 | Hold | Map W03-C3 plus metrology | M. Alvarez |
| Wafer 12 | Hold | Map W12-E1 plus IMG-227 | K. Stone |
| Wafer 09 | Conditional | P4 parametric; REL-22-A required | S. Han |
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

The scanned HTOL load ticket binds REL-22-A / wafer 09 to chamber H-17 and tray C4, loaded 2026-06-11 14:22. KT witnessed the door seal; humidity logger HL-88 is attached. The 24 h observation reports no electrical reject, but the final 168 h result remains pending and wafer 09 remains segregated. S. Han and M. Alvarez signed custody at 14:22 and 14:31.

## Defect-image verification worksheet

The scanned IQC-071 worksheet covers lot Q8R7-22 and image set IMG-223/224/226/227. Wafer-map comparison and neighboring-die review are checked. Independent morphology confirmation is unchecked. Preliminary all-wafer COA release is unchecked. Reticle excursion review is disabled as not applicable to the PVD-origin event. IMG-224's initial count of one is struck. Its corrected count is two reportable objects with the instruction `see controlled image archive`; the correction basis says the second object was resolved at archive magnification. R. Kim signed 2026-06-11 09:42 and A. Roy reviewed at 11:06.

| Archive object | Custodian | Checksum state | Packet role |
| --- | --- | --- | --- |
| IQC-071 | Incoming quality | Signed | Inspection worksheet |
| IMG set 223/224/226/227 | Fab image archive | Matched | Visual evidence |
| MAP-11JUN | Yield engineering | Matched | Coordinate source |
| COA-DRAFT-02 | Quality systems | Void | Not shipment authority |

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

The preliminary all-wafer COA is void; only the signed values above authorize shipment.
