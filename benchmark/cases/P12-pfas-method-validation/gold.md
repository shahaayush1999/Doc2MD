# PFAS Method Validation and Batch Release Packet

## Page 1 - Validation packet control and method scope

| Field | Controlled value |
| --- | --- |
| Study | MV-PFAS-24-017 |
| Instrument | SCIEX 6500+ QTRAP; ESI negative |
| Column | BEH C18, 2.1 x 50 mm, 1.7 um |
| Injection | 5 uL |
| Study interval | 08-22 Apr 2024 |
| Reporting basis | ng/L in original sample; U95 where quantified |

Source precedence: signed QA correction > accepted integration > provisional LIMS export. A signed QA correction controls only the fields it amends.

| Sample ID | Matrix | Collected | Received | Preserved | Release path |
| --- | --- | --- | --- | --- | --- |
| FB-240408-01 | Field blank | 08 Apr 09:10 | 08 Apr 15:42 | Trizma | Routine |
| DW-240408-02 | Finished water | 08 Apr 09:25 | 08 Apr 15:42 | Trizma | Routine |
| DW-240408-03 | Finished water | 08 Apr 09:40 | 08 Apr 15:42 | Trizma | MS/MSD |
| DW-240409-04 | Finished water | 09 Apr 10:05 | 09 Apr 16:20 | Trizma | Corrected |
| DW-240409-05 | Finished water | 09 Apr 10:20 | 09 Apr 16:20 | Trizma | Routine |

## Page 2 - Calibration model, transitions, and limits

Equations:
- **Response ratio:** `R = A_native / A_IS`
- **Concentration:** `C_sample = ((R - b) / m) x DF`
- **Spike recovery:** `Recovery % = ((C_spiked - C_native) / C_added) x 100`
- **Expanded uncertainty:** `U95 = 2 x sqrt(u_cal^2 + u_rep^2 + u_vol^2 + u_rec^2)`

The calibration table uses grouped headers for identity, transitions, retention, validated range, and limits.

| Analyte | Internal standard | Quantifier | Qualifier | RT min | Range ng/L | LOD / LOQ ng/L |
| --- | --- | --- | --- | --- | --- | --- |
| PFBA | 13C4-PFBA | 213>169 | 213>119 | 2.18 | 0.50-80 | 0.16 / 0.50 |
| PFPeA | 13C5-PFPeA | 263>219 | 263>169 | 2.74 | 0.50-80 | 0.13 / 0.50 |
| PFHxA | 13C5-PFHxA | 313>269 | 313>119 | 3.32 | 0.50-80 | 0.18 / 0.50 |
| PFHpA | 13C4-PFHpA | 363>319 | 363>169 | 3.86 | 0.50-80 | 0.15 / 0.50 |
| PFOA | 13C8-PFOA | 413>369 | 413>169 | 4.41 | 0.25-80 | 0.08 / 0.25 |
| PFNA | 13C9-PFNA | 463>419 | 463>169 | 4.95 | 0.25-80 | 0.09 / 0.25 |
| PFDA | 13C6-PFDA | 513>469 | 513>219 | 5.48 | 0.25-80 | 0.10 / 0.25 |
| PFBS | 18O2-PFBS | 299>80 | 299>99 | 3.05 | 0.50-100 | 0.17 / 0.50 |
| PFHxS | 18O2-PFHxS | 399>80 | 399>99 | 4.63 | 0.50-100 | 0.20 / 0.50 |
| PFOS | 13C8-PFOS | 499>80 | 499>99 | 5.64 | 0.50-100 | 0.22 / 0.50 |
| 6:2 FTS | 13C2-6:2FTS | 427>407 | 427>81 | 5.19 | 1.00-100 | 0.31 / 1.00 |
| HFPO-DA | 13C3-HFPO-DA | 329>285 | 329>169 | 3.71 | 0.50-80 | 0.14 / 0.50 |

| Symbol | Meaning | Rendering rule |
| --- | --- | --- |
| U | Not detected at the LOQ | Preserve the leading < sign and LOQ |
| J | Estimated concentration | Preserve the numeric value and J |
| - | No qualifier | Do not invent a textual qualifier |

## Page 3 - Calibration curves and residual disposition

Figure 03 is a 2x3 raster calibration-review plate in this panel order: PFOA, PFNA, PFOS, PFHxS, 6:2 FTS, HFPO-DA. Filled circles are included standards, an open diamond is an excluded standard, and inset bars are back-calculated residual percentages. The horizontal axis is log concentration in ng/L and the vertical axis is response ratio.

- **PFOA** - y = 0.0748x + 0.0021; R2 0.9986; range 0.25-80 ng/L. Levels: 0.25, 0.5, 1, 5, 20, 50, 80 ng/L. Responses: 0.021, 0.040, 0.077, 0.406, 1.393, 3.731, 5.986. Residuals: +11.8%, -6.1%, +3.4%, -2.8%, +1.9%, -4.2%, +5.1%. Review: Max residual +11.8% at 0.25 ng/L (L1). Disposition: L1 retained - within the +/-20% lowest-level allowance.
- **PFNA** - y = 0.0702x + 0.0008; R2 0.9964; range 0.25-80 ng/L. Levels: 0.25, 0.5, 1, 5, 20, 50, 80 ng/L. Responses: 0.018, 0.034, 0.070, 0.352, 1.411, 3.510, 5.621. Residuals: -18.7%, +9.2%, -5.5%, +3.1%, -2.4%, +4.8%, -3.0%. Review: Max residual -18.7% at 0.25 ng/L (L1). Disposition: L1 retained - within the +/-20% lowest-level allowance.
- **PFOS** - y = 0.0831x + 0.0184; R2 0.9978; range 0.50-100 ng/L. Levels: 0.5, 1, 2, 10, 25, 50, 100 ng/L. Responses: 0.042, 0.089, 0.184, 0.958, 2.392, 4.753, 8.177. Residuals: -9.4%, +4.1%, -3.8%, +2.5%, -6.2%, +7.9%, +14.6%. Review: Max residual +14.6% at 100 ng/L (L7). Disposition: Upper point retained - within the +/-15% criterion.
- **PFHxS** - y = 0.0817x + 0.0019; R2 0.9991; range 0.50-100 ng/L. Levels: 0.5, 1, 2, 10, 25, 50, 100 ng/L. Responses: 0.038, 0.080, 0.162, 0.821, 2.049, 4.086, 8.169. Residuals: +7.2%, -5.1%, +3.7%, -2.9%, +2.1%, -8.4%, +4.6%. Review: Max residual -8.4% at 50 ng/L (L6). Disposition: All seven levels retained - no residual flag.
- **6:2 FTS** - y = 0.0544x + 0.0007; R2 0.9981 after L2 exclusion; range 1.00-100 ng/L. Levels: 1, 2, 5, 10, 25, 50, 100 ng/L. Responses: 0.052, 0.141, 0.269, 0.548, 1.361, 2.716, 5.433. Residuals: -4.8%, +23.6%, +6.2%, -3.1%, +2.8%, -5.9%, +4.4%. Review: L2 residual +23.6% at 2.0 ng/L; vial bubble CAL-EX-06. Disposition: L2 excluded; six-level refit accepted under signed exception.
- **HFPO-DA** - y = 0.0830x + 0.0041; R2 0.9989; range 0.50-80 ng/L. Levels: 0.5, 1, 2, 10, 20, 50, 80 ng/L. Responses: 0.044, 0.086, 0.175, 0.790, 1.664, 4.400, 6.632. Residuals: +9.7%, -6.8%, +3.5%, -4.2%, +2.9%, +6.1%, -5.0%. Review: Max residual +9.7% at 0.50 ng/L (L1). Disposition: All seven levels retained - no curvature flag.

The general method rule is weighted 1/x^2, R2 >= 0.995, included standards within +/-15%, and the lowest included standard within +/-20%. Only the 6:2 FTS 2.0 ng/L L2 standard is excluded, under the source-visible CAL-EX-06 vial-bubble exception; the six-level refit is accepted.

## Page 4 - Table V4 accuracy and precision, part 1

| Analyte | Low rec / RSD % | Mid rec / RSD % | High rec / RSD % | n | State |
| --- | --- | --- | --- | --- | --- |
| PFBA | 96.0 / 8.4 | 101.0 / 4.6 | 99.0 / 3.8 | 7 | Pass |
| PFPeA | 93.0 / 9.1 | 98.0 / 5.2 | 101.0 / 4.1 | 7 | Pass |
| PFHxA | 91.0 / 10.3 | 97.0 / 5.8 | 100.0 / 4.3 | 7 | Pass |
| PFHpA | 95.0 / 7.9 | 99.0 / 4.9 | 102.0 / 4.0 | 7 | Pass |
| PFOA | 98.0 / 6.8 | 103.0 / 3.7 | 101.0 / 3.2 | 7 | Pass |
| PFNA | 97.0 / 7.2 | 102.0 / 4.1 | 100.0 / 3.6 | 7 | Pass |

| Level | Nominal basis | Replicates | Recovery | RSD |
| --- | --- | --- | --- | --- |
| Low | LOQ or 2 x LOQ | 7 on 7 days | 70-130% | <=20% |
| Mid | 10 ng/L | 7 on 7 days | 70-130% | <=20% |
| High | 80 ng/L | 7 on 7 days | 70-130% | <=20% |

Table V4 continues on page 5 with PFDA through HFPO-DA and repeated headers.

## Page 5 - Table V4 accuracy and precision, part 2

This page continues Table V4 from page 4; the repeated headers are not data rows.

| Analyte | Low rec / RSD % | Mid rec / RSD % | High rec / RSD % | n | State |
| --- | --- | --- | --- | --- | --- |
| PFDA | 92.0 / 11.5 | 96.0 / 6.3 | 99.0 / 4.9 | 7 | Pass |
| PFBS | 104.0 / 9.7 | 99.0 / 4.8 | 98.0 / 4.0 | 7 | Pass |
| PFHxS | 101.0 / 8.9 | 100.0 / 4.4 | 97.0 / 3.9 | 7 | Pass |
| PFOS | 89.0 / 12.6 | 95.0 / 6.7 | 96.0 / 5.1 | 7 | Pass |
| 6:2 FTS | 86.0 / 14.8 | 92.0 / 7.4 | 94.0 / 6.3 | 7 | Pass |
| HFPO-DA | 99.0 / 7.5 | 104.0 / 4.2 | 103.0 / 3.5 | 7 | Pass |

| Record | Affected result | Observation | Disposition |
| --- | --- | --- | --- |
| EX-24-011 | 6:2 FTS low-level day 2 | 61% recovery | Excluded: fortification omitted |
| EX-24-014 | PFOS low-level day 6 | 89% recovery; 12.6% RSD | Retained: within criteria |
| EX-24-017 | HFPO-DA mid day 4 | 104% recovery | Retained: within criteria |

EX-24-011 is excluded from n=7; its valid replacement contributes to the 86.0% 6:2 FTS low-level mean.

## Page 6 - Scanned extraction, fortification, and dilution record

| Prep ID | Material / sample | Initial | Aliquot | Final | Recorded target / DF |
| --- | --- | --- | --- | --- | --- |
| SPK-01 | LCS mixed native spike | 1.000 ng/uL | 10.00 uL | 1.000 L | 10.00 ng/L |
| SPK-02 | MS/MSD mixed native spike | 1.000 ng/uL | 10.00 uL | 1.000 L | 10.00 ng/L |
| DIL-03 | DW-240408-03 extract | 1.000 mL | 0.500 mL | 5.000 mL | DF 10.00 |
| DIL-04 | DW-240409-04 original extract | 1.000 mL | 1.000 mL | 1.000 mL | DF 1.00 |
| DIL-05 | DW-240409-04 reinjection vial | 0.800 mL | 0.400 mL | 0.800 mL | DF 2.00 |

| Sample | Bottle mL | Extract mL | SPE lot | Surrogate added | Analyst check |
| --- | --- | --- | --- | --- | --- |
| LRB-240410-01 | 250.0 | 1.000 | SPE-24-118 | 50.0 uL | MI 10 Apr 08:04 |
| LCS-240410-01 | 250.0 | 1.000 | SPE-24-118 | 50.0 uL | MI 10 Apr 08:08 |
| DW-240408-03 | 249.0 | 1.000 | SPE-24-118 | 50.0 uL | MI 10 Apr 08:17 |
| DW-240409-04 | 250.0 | 1.000 | SPE-24-118 | 50.0 uL | MI 10 Apr 08:23 |

- SPK-01 and SPK-02 verified against CRM certificate PFAS-MIX-2319, expiry 30 Sep 2024.
- DIL-05 prepared only after reinjection authorization MX-24-041; keep DIL-04 vial in audit storage.
- Balance check 10.0002 g against 10.0000 g; pipette P100 verification 99.6 uL at 20.1 C.

Analyst M. Iyer signed 10 Apr 2024 08:42; witness L. Chen signed 10 Apr 2024 08:51.

## Page 7 - Scanned LC-MS/MS sequence and technical review

| Seq | Type | Vial | Sample / control | Start | IS rec | Carryover | State |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 09 | Cal | A09 | CAL-80 | 09:54 | 103% | Clear | Accepted |
| 10 | Blank | B01 | LRB-240410-01 | 10:07 | 97% | Clear | Accepted |
| 11 | LCS | B02 | LCS-240410-01 | 10:20 | 94% | Clear | Accepted |
| 12 | Sample | B03 | FB-240408-01 | 10:33 | 96% | Clear | Accepted |
| 13 | Sample | B04 | DW-240408-02 | 10:46 | 92% | Clear | Accepted |
| 14 | Sample | B05 | DW-240408-03 | 10:59 | 89% | Clear | Accepted |
| 15 | MS | B06 | DW-240408-03-MS | 11:12 | 93% | Clear | Accepted |
| 16 | MSD | B07 | DW-240408-03-MSD | 11:25 | 90% | Clear | Accepted |
| 17 | CCV | B08 | CCV-10 | 11:38 | 95% | Clear | Accepted |
| 18 | Sample | B09 | DW-240409-04 | 11:51 | 38% | Clear | HOLD MX-24-041 |
| 19 | Sample | C01 | DW-240409-04-RI | 12:18 | 91% | Clear | Accepted |
| 20 | Sample | C02 | DW-240409-05 | 12:31 | 88% | Clear | Accepted |
| 21 | CCV | C03 | CCV-10-CLOSE | 12:44 | 93% | Clear | Accepted |

| Linked item | Entry |
| --- | --- |
| MX-24-041 | Opened 11:58 after sequence 18 IS recovery fell below 50% |
| Authorization | One reinjection after blank and needle-seat flush |
| Control rule | If reinjection IS is 50-150%, retain original only in audit trail |
| Review mark | Sequence 19 circled; sequence 18 struck once, still legible |

Sequence 18 is held under MX-24-041 at 38% IS recovery. Sequence 19 is the accepted reinjection at 91% IS recovery. Analyst M. Iyer signed 19 Apr 2024 14:05 and technical reviewer L. Chen signed 22 Apr 2024 09:40.

## Page 8 - Raw integration and chromatogram review

Instrument panel evidence:
- Panel A, LRB-240410-01 / PFOS Q1: 5.64 min, noise 38-44 cps, file 240410_10.wiff, no integration, NO PEAK / BLANK ACCEPTED.
- Panel B, DW-240408-03 / PFOA Q1: 4.41 min, area 25,621, Q1/Q2 ratio 0.31, file 240410_14.wiff, ACCEPTED / FINAL BATCH RESULT.
- Panel C, DW-240409-04 / 13C8-PFOA IS: 4.39 min, IS recovery 38%, IR-18A, file 240410_18.wiff, SEQ 18 HOLD / ORIGINAL REJECTED.
- Panel D, DW-240409-04-RI / 13C8-PFOA IS: 4.40 min, IS recovery 91%, IR-19B, file 240410_19.wiff, SEQ 19 ACCEPTED / CONTROLLING.
- Panel E, DW-240409-04 / PFOA Q1: 4.42 min, area 11,180, Q1/Q2 ratio 0.27, IR-18A linked, SEQ 18 NOT REPORTABLE.
- Panel F, DW-240409-04-RI / PFOA Q1: 4.41 min, area 8,420, Q1/Q2 ratio 0.30, IR-19B linked, SEQ 19 ACCEPTED / 1.06 ng/L J.
- Panel G, CCV-10-CLOSE / PFOA Q1: 4.41 min, back-calculated 10.31 ng/L, area 80,755, file 240410_21.wiff, ACCEPTED / 103.1% RECOVERY.
- Panel H, DW-240409-05 / 6:2 FTS Q2: 5.18 min, area 13,290, Q1/Q2 ratio 0.22, file 240410_20.wiff, REVIEWED / QUALIFIER CONFIRMED.

| Panel | Injection | Trace channel | Review role |
| --- | --- | --- | --- |
| A | Seq 10 | PFOS Q1 | Reagent blank |
| B | Seq 14 | PFOA Q1 | Batch sample |
| C | Seq 18 | 13C8-PFOA IS | Original internal standard |
| D | Seq 19 | 13C8-PFOA IS | Reinjection internal standard |
| E | Seq 18 | PFOA Q1 | Original quantifier |
| F | Seq 19 | PFOA Q1 | Reinjection quantifier |
| G | Seq 21 | PFOA Q1 | Closing CCV |
| H | Seq 20 | 6:2 FTS Q2 | Qualifier review |

The native index supplies injection and channel identity only; the visual plate controls trace measurements and review state.

## Page 9 - Blank, recovery, and continuing-calibration review

| Control | Analyte | Measured | Review criterion | Review state |
| --- | --- | --- | --- | --- |
| LRB-240410-01 | PFOA | <0.25 ng/L U | <0.25 ng/L | Meets |
| LRB-240410-01 | PFOS | <0.50 ng/L U | <0.50 ng/L | Meets |
| LCS-240410-01 | PFOA | 9.62 ng/L | 70-130% recovery | Calculate from SPK-01 |
| LCS-240410-01 | PFOS | 9.14 ng/L | 70-130% recovery | Calculate from SPK-01 |
| DW-240408-03-MS | PFOA | 13.02 ng/L | 70-130% recovery | Subtract native 3.42 |
| DW-240408-03-MSD | PFOA | 13.22 ng/L | RPD <=30% | Compare with MS |
| DW-240408-03-MSD | 6:2 FTS | 8.40 ng/L | 70-130% recovery | Native <1.00 U |
| CCV-10 | PFOA | 9.48 ng/L | 85-115% of 10.00 | Meets |
| CCV-10-CLOSE | PFOA | 10.31 ng/L | 85-115% of 10.00 | Meets |

| Computation | Required source join | Reviewer action |
| --- | --- | --- |
| LCS PFOA recovery | p6 SPK-01 target + p9 measured | Calculate; compare to 70-130% |
| LCS PFOS recovery | p6 SPK-01 target + p9 measured | Calculate; compare to 70-130% |
| MS PFOA recovery | p6 SPK-02 + native + p9 spiked | Subtract native; calculate |
| MSD PFOA recovery | p6 SPK-02 + native + p9 spiked | Subtract native; calculate |
| MS/MSD PFOA RPD | two calculated spike recoveries | Calculate; compare to <=30% |
| MSD 6:2 FTS recovery | p6 SPK-02 + p9 measured; native U | Treat native as zero; calculate |

The 10.00 ng/L SPK-01/SPK-02 targets come from page 6. The LCS recoveries are 96.2% PFOA and 91.4% PFOS; MS/MSD PFOA recoveries are 96.0% and 98.0% with 2.1% RPD; 6:2 FTS MSD recovery is 84.0%.

## Page 10 - Scanned maintenance and reinjection authorization

| Time | Observation / action | Measured check | Initials |
| --- | --- | --- | --- |
| 11:55 | Sequence 18 flagged by IS rule | 13C8-PFOA recovery 38% | MI |
| 12:00 | Pressure and source check | 6,820 psi; spray stable | MI |
| 12:04 | Needle-seat inspection | Visible salt film | LC |
| 12:08 | Needle seat flushed 3 x 500 uL | 50:50 MeOH:water | LC |
| 12:12 | System blank injected | PFOS carryover <0.08 ng/L | MI |
| 12:16 | IS check solution | 13C8-PFOA recovery 96% | MI |
| 12:17 | One reinjection authorized | Use retained DIL-05 vial | LC |

| Decision field | Signed entry |
| --- | --- |
| Permitted scope | DW-240409-04 only; one reinjection |
| Acceptance gate | IS recovery 50-150%; blank carryover below LOQ |
| If gate passes | Send both integrations to QA; do not select final concentration here |
| If gate fails | Invalidate sample result and request re-extraction |
| Audit preservation | Retain sequence 18, IR-18A, and original vial DIL-04 |

Salt residue was confined to the needle seat. No source cleaning, recalibration, or re-extraction was authorized. M. Iyer signed 19 Apr 2024 12:22 and L. Chen authorized at 12:24.

## Page 11 - LIMS export and signed QA correction

The page first contains provisional export PRELIM-LIMS-0419:

| Export row | Sample | Analyte | Result | Qual. | Source | Status |
| --- | --- | --- | --- | --- | --- | --- |
| E-104 | DW-240409-04 | PFOA | 1.84 ng/L | J | Seq 18 / IR-18A | Provisional |
| E-105 | DW-240409-04 | PFOS | <0.50 ng/L | U | Seq 18 / IR-18A | Provisional |
| E-106 | DW-240409-05 | PFOA | 4.87 ng/L | - | Seq 20 / IR-20A | Ready |

Signed correction CR-24-044 applies only to DW-240409-04. It supersedes PRELIM-LIMS-0419 fields derived from sequence 18/IR-18A and makes accepted sequence 19/IR-19B controlling. PFOA changes from 1.84 ng/L J to 1.06 ng/L J. PFOS remains <0.50 ng/L U with no qualifier change. Other batch results are unchanged. The reason is sequence 18 IS recovery below the 50-150% criterion. L. Chen signed 22 Apr 2024 09:40 and R. Patel signed 22 Apr 2024 16:10. The audit trail must not be overwritten. Controlled record order is provisional PRELIM-LIMS-0419 first, followed by signed CR-24-044.

## Page 12 - Final signed validation and batch determination

| Result ID | Sample | Analyte | Released result | Qual. | U95 | Authority |
| --- | --- | --- | --- | --- | --- | --- |
| R-01 | FB-240408-01 | PFOA | <0.25 ng/L | U | - | Routine |
| R-02 | DW-240408-02 | PFOA | 2.18 ng/L | - | 0.42 ng/L | Routine |
| R-03 | DW-240408-02 | PFOS | 0.62 ng/L | J | 0.18 ng/L | Routine |
| R-04 | DW-240408-03 | PFOA | 3.42 ng/L | - | 0.55 ng/L | Routine |
| R-05 | DW-240408-03 | PFOS | 0.74 ng/L | J | 0.19 ng/L | Routine |
| R-06 | DW-240409-04 | PFOA | 1.06 ng/L | J | 0.25 ng/L | CR-24-044 |
| R-07 | DW-240409-04 | PFOS | <0.50 ng/L | U | - | CR-24-044 |
| R-08 | DW-240409-05 | PFOA | 4.87 ng/L | - | 0.72 ng/L | Routine |

| Release check | Determination | Basis |
| --- | --- | --- |
| Calibration | Accepted | Weighted fits and residual review |
| Blanks and CCVs | Accepted | Opening and closing controls within criteria |
| Recovery / precision | Accepted | Valid n=7; documented EX-24-011 replacement |
| DW-240409-04 | Accepted as corrected | Sequence 19 / IR-19B / CR-24-044 |
| Batch release | RELEASED | J and U qualifiers retained exactly |

The batch is released with J and U qualifiers preserved. DW-240409-04's record lifecycle begins with held sequence 18 at 38% IS recovery and rejected original integration IR-18A, then continues through accepted DW-240409-04-RI sequence 19 at 91% IS recovery and controlling reinjection IR-19B. Panels E and F preserve the original not-reportable PFOA Q1 trace and the accepted reinjection trace. Signed CR-24-044 changes provisional PFOA 1.84 ng/L J to released R-06 at 1.06 ng/L J with U95 0.25 ng/L, while PFOS remains <0.50 ng/L U. The final determination does not erase provisional exports, rejected integrations, or maintenance records. L. Chen signed 22 Apr 2024 09:40 and R. Patel released 22 Apr 2024 16:10.
