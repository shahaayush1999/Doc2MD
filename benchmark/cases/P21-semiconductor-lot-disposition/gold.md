# Aster Microdevices Lot Q8R7-22 Disposition File

Product AMX-4100, Fab 3, LVT gate flow, MRB 2026-06-11. Final MRB state: release wafers 01, 02, 04, 06, 08, 10, and 11; wafer 09 is conditional pending REL-22-A; wafers 03, 05, and 12 remain on engineering hold; wafer 07 is scrap and must not be counted in ship yield.

## Wafer Summary
| Wafer | Good die | Defect % | Probe yield | Final state | Note |
| --- | --- | --- | --- | --- | --- |
| 01 | 18,420 | 0.83 | 97.8 | release | center-edge normal |
| 02 | 18,216 | 0.86 | 97.1 | release | one edge cluster |
| 03 | 17,604 | 1.24 | 93.8 | hold | map quadrant B4 |
| 04 | 18,390 | 0.81 | 97.6 | release | normal |
| 05 | 17,118 | 1.42 | 91.9 | hold | scratch arc |
| 06 | 18,275 | 0.88 | 96.9 | release | normal |
| 07 | 16,902 | 1.58 | 90.6 | scrap | metal flakes |
| 08 | 18,301 | 0.79 | 97.4 | release | normal |
| 09 | 17,880 | 1.06 | 95.5 | conditional | param drift |
| 10 | 18,144 | 0.90 | 96.8 | release | normal |
| 11 | 18,013 | 0.95 | 96.2 | release | normal |
| 12 | 17,422 | 1.31 | 92.7 | hold | edge bead |

## Traveler and Route
| Step | Tool | Recipe | Start | End | Visible state |
| --- | --- | --- | --- | --- | --- |
| Implant P3 | IMP-17 | BORON_LVT_042 | 05:12 | 05:58 | accepted |
| Ash | ASH-04 | ASH_STD_18 | 06:10 | 06:34 | accepted |
| Wet clean | WET-12 | SC1_SC2_09 | 06:48 | 07:22 | accepted |
| PVD TiN | PVD-03 | TIN_GATE_31 | 08:06 | 09:44 | alarm at 09:18 |
| Anneal | RTP-08 | RTP_LVT_22 | 10:01 | 10:29 | accepted |
| Metrology | CDSEM-06 | GATE_LVT_QC | 10:45 | 11:56 | reviewed |
PVD-03 alarm at 09:18 triggered containment. The lot continued to RTP-08 only after engineering released the already-loaded chamber sequence.

## Recipe Source Conflict
| Source | Recipe shown | Status | Meaning |
| --- | --- | --- | --- |
| Traveler page | TIN_GATE_31 | current | used for lot |
| Tool alarm printout | TIN_GATE_30 | stale header | screen cache |
| MES audit | TIN_GATE_31 | confirmed | controls |
| Engineer note | increase clamp purge | future only | not used for this lot |
TIN_GATE_31 controls the actual run; TIN_GATE_30 appears only on a stale tool-alarm header.

## Wafer Maps
Wafer 03 has C3 cluster at B4, C4, and B5. Wafer 05 has S2 scratch cells E2, F2, and E3. Wafer 07 has M1 metal-flake cells D5, D6, and E5. Wafer 09 has P4 at F3. Wafer 12 has E1 edge cells A6 and B6. Wafer 02 has one edge-marked A1 cell.

## Metrology
| Wafer | Site | CD nm | Delta | Flag | Reviewer note |
| --- | --- | --- | --- | --- | --- |
| Wafer | Site | CD nm | Delta | Flag | Reviewer note |
| 03 | B4 | 27.8 | +2.9 | H | matches map cluster |
| 03 | C4 | 27.4 | +2.5 | H | adjacent high |
| 05 | E2 | 24.1 | -1.8 | L | scratch path |
| 07 | D5 | 29.6 | +4.7 | H | flake shadow |
| 07 | D6 | 29.1 | +4.2 | H | flake shadow |
| 09 | F3 | 26.8 | +1.9 | watch | param drift only |
| 12 | A6 | 23.9 | -2.0 | L | edge bead |

## SPC Trend
| Run | Time | TiN thickness | Limit state | Comment |
| --- | --- | --- | --- | --- |
| R-2241 | 08:06 | 41.2 | inside | start |
| R-2242 | 08:22 | 42.0 | inside | stable |
| R-2243 | 08:38 | 43.8 | inside | rising |
| R-2244 | 08:54 | 45.6 | warning | near UCL |
| R-2245 | 09:10 | 47.4 | above UCL | alarm follows |
| R-2246 | 09:26 | 46.2 | warning | post alarm |
| R-2247 | 09:42 | 44.1 | inside | recovered |
R-2245 is above UCL at 47.4 nm. R-2244 and R-2246 are warning-state points but not rejects by themselves.

## Defects
| Code | Class | Count | Affected wafer | Disposition |
| --- | --- | --- | --- | --- |
| M1 | metal flake | 44 | 07 | scrap wafer 07 |
| S2 | scratch | 31 | 05 | hold for review |
| E1 | edge bead | 27 | 12 | hold |
| P4 | parametric drift | 19 | 09 | conditional release |
| C3 | center cluster | 16 | 03 | hold |

## Photo Register
IMG-221 W07 D5 and IMG-222 W07 D6 show M1 metal flakes and support scrap W07. IMG-223 W05 E2 shows S2 scratch and supports hold W05. IMG-224 W12 A6 shows E1 edge bead and supports hold W12. IMG-225 W09 F3 is clean visually but has P4 electrical drift and supports conditional W09.

## MRB Matrix
| Item | Decision | Reason | Owner |
| --- | --- | --- | --- |
| Wafer 07 | scrap | metal flakes M1 at D5/D6 | Y. Nishida |
| Wafer 05 | hold | scratch S2 crosses E2-F2 | A. Roy |
| Wafer 03 | hold | CD high at B4/C4 | M. Alvarez |
| Wafer 12 | hold | edge bead at A6 | K. Stone |
| Wafer 09 | conditional release | parametric drift P4, REL sample required | S. Han |
| Wafers 01,02,04,06,08,10,11 | release | within disposition limits | MRB |

## Reliability and Shipping
| Sample | Wafer | Stress | Result | Use |
| --- | --- | --- | --- | --- |
| REL-22-A | 09 | HTOL 168h | pending | condition for release |
| REL-22-B | 02 | TC 100 cyc | pass | reference |
| REL-22-C | 11 | HAST 96h | pass | reference |
| REL-22-D | 07 | not built | scrap | no reliability credit |
| Ship bucket | Wafers | Die count | Condition |
| --- | --- | --- | --- |
| Release now | 01,02,04,06,08,10,11 | 127,759 | standard COA |
| Conditional | 09 | 17,880 | hold shipment until REL-22-A pass |
| Engineering hold | 03,05,12 | 52,144 | do not ship |
| Scrap | 07 | 16,902 | do not include in yield |

## COA Holdback
Released wafers are 01,02,04,06,08,10,11. Conditional wafer 09 ships only after REL-22-A passes. Engineering hold wafers 03,05,12 and scrap wafer 07 are excluded from shipment. Signed COA must not use the preliminary all-wafer draft.

## Audit Trail
| Timestamp | Actor | Entry | Effect |
| --- | --- | --- | --- |
| 2026-06-10 12:18 | MES | PVD alarm attached | containment starts |
| 2026-06-10 14:40 | Yield eng | wafer map review complete | W03/W05/W07/W12 flagged |
| 2026-06-11 08:55 | MRB | W07 scrap, W09 conditional | controls final state |
| 2026-06-11 10:20 | Quality | COA holdback added | prevents draft all-wafer ship |
| 2026-06-11 13:30 | Planning | ship bucket split | 127,759 die release now |