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

Figure 03 labels each standard as concentration in ng/L | response ratio.

- PFOA: 0.25 | 0.021, 1 | 0.077, 5 | 0.406, 20 | 1.393, 80 | 5.986
- PFOS: 0.5 | 0.042, 2 | 0.184, 10 | 0.958, 50 | 4.753, 100 | 8.177
- HFPO-DA: 0.5 | 0.044, 2 | 0.175, 10 | 0.790, 50 | 4.400, 80 | 6.632

Chart reconstruction: the horizontal x-axis is log concentration in ng/L and the vertical y-axis is response ratio. The legend maps the blue line and points to PFOA, green to PFOS, and amber to HFPO-DA. Each panel uses weighted 1/x^2 calibration and labels every point with both concentration and response. The PFOA series rises monotonically from 0.021 to 5.986. The PFOS series rises monotonically from 0.042 to 8.177. The HFPO-DA series rises monotonically from 0.044 to 6.632.

| Analyte | Weighted R2 | Max abs back-calc residual | Disposition |
| --- | --- | --- | --- |
| PFOA | 0.9986 | 11.8% at 0.25 ng/L | 1/x^2 retained |
| PFOS | 0.9978 | 14.6% at 100 ng/L | Upper point retained |
| HFPO-DA | 0.9989 | 9.7% at 0.50 ng/L | No curvature flag |

Acceptance: weighted R2 >= 0.995; standards +/-15%, with +/-20% permitted at the lowest level.

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
- Panel A, LRB-240410-01/PFOS quantifier: 5.64 min marker, noise window 38-44 cps, no integrated peak, file 240410_10.wiff.
- Panel B, DW-240408-03/PFOA quantifier: 4.41 min, area 25,621, quant/qual ratio 0.31, file 240410_14.wiff.
- Panel C, DW-240409-04/13C8-PFOA original: 4.39 min, IS recovery 38%, integration IR-18A, sequence 18.
- Panel D, DW-240409-04/13C8-PFOA reinjection: 4.40 min, IS recovery 91%, integration IR-19B, sequence 19.

| Panel | Review purpose | Related record | Use limitation |
| --- | --- | --- | --- |
| A | Reagent-blank trace | LRB-240410-01 | sample concentration |
| B | Target-analyte integration | DW-240408-03 | final batch release |
| C | Original internal standard | IR-18A | accepted result |
| D | Reinjection internal standard | IR-19B | correction scope |

The literal Use limitation values are `accepted result` for Panel C and `correction scope` for Panel D. Exact RT, area, ratio, and internal-standard recovery values come from the instrument annotations; the routing register supplies panel identity only.

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

The batch is released with J and U qualifiers preserved. DW-240409-04 is accepted as corrected from sequence 19/IR-19B under CR-24-044. The final determination does not erase provisional exports, rejected integrations, or maintenance records. L. Chen signed 22 Apr 2024 09:40 and R. Patel released 22 Apr 2024 16:10.
