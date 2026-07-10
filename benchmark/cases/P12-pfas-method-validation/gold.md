# PFAS Method Validation Supplement

## Method conditions and sample manifest

| Field | Recorded value |
| --- | --- |
| Instrument | SCIEX 6500+ QTRAP; ESI negative |
| Column | Acquity BEH C18, 2.1 x 50 mm, 1.7 um |
| Injection | 5 uL |
| Mobile phase A | 5 mM ammonium acetate in water |
| Mobile phase B | Methanol |
| Study dates | 8-19 April 2024 |

Workflow: Receipt -> Preservation -> SPE extraction -> Dry-down -> Reconstitution -> LC-MS/MS -> Review.

| Sample ID | Matrix | Collected | Received | pH | Cl mg/L | mL | State |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FB-240408-01 | Field blank | 08 Apr 09:10 | 08 Apr 15:42 | 6.8 | <0.02 | 252 | OK |
| DW-240408-02 | Finished water | 08 Apr 09:25 | 08 Apr 15:42 | 7.2 | <0.02 | 251 | OK |
| DW-240408-03 | Finished water | 08 Apr 09:40 | 08 Apr 15:42 | 7.1 | <0.02 | 249 | OK |
| DW-240409-04 | Finished water | 09 Apr 10:05 | 09 Apr 16:20 | 7.4 | <0.02 | 250 | OK |
| DW-240409-05 | Finished water | 09 Apr 10:20 | 09 Apr 16:20 | 7.3 | <0.02 | 250 | OK |
| LRB-240410-01 | Reagent blank | 10 Apr 07:30 | 10 Apr 07:30 | 6.9 | <0.02 | 250 | Prepared |
| LCS-240410-01 | Control sample | 10 Apr 07:35 | 10 Apr 07:35 | 7.0 | <0.02 | 250 | Prepared |
| MSD-240410-03 | Matrix spike dup. | 10 Apr 07:40 | 10 Apr 07:40 | 7.1 | <0.02 | 250 | Prepared |

## Calibration model and transitions

Equations:
- **Response ratio:** `R = A_native / A_IS`
- **Sample concentration:** `C_sample = ((R - b) / m) x DF`
- **Detection limit:** `LOD = t_(n-1,0.99) x SD_low`
- **Expanded uncertainty:** `U95 = 2 x sqrt(u_cal^2 + u_rep^2 + u_vol^2 + u_rec^2)`

The table has grouped identity, transition, retention, regression, fit, and reporting-limit headers.

| Analyte | Internal standard | Quant. | Qual. | RT | m | R2 | LOD / LOQ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PFBA | 13C4-PFBA | 213>169 | 213>119 | 2.18 | 0.0921 | 0.9987 | 0.16 / 0.50 |
| PFPeA | 13C5-PFPeA | 263>219 | 263>169 | 2.74 | 0.0875 | 0.9991 | 0.13 / 0.50 |
| PFHxA | 13C5-PFHxA | 313>269 | 313>119 | 3.32 | 0.0814 | 0.9985 | 0.18 / 0.50 |
| PFHpA | 13C4-PFHpA | 363>319 | 363>169 | 3.86 | 0.0778 | 0.9990 | 0.15 / 0.50 |
| PFOA | 13C8-PFOA | 413>369 | 413>169 | 4.41 | 0.0749 | 0.9967 | 0.08 / 0.25 |
| PFNA | 13C9-PFNA | 463>419 | 463>169 | 4.95 | 0.0712 | 0.9989 | 0.09 / 0.25 |
| PFDA | 13C6-PFDA | 513>469 | 513>219 | 5.48 | 0.0686 | 0.9986 | 0.10 / 0.25 |
| PFBS | 18O2-PFBS | 299>80 | 299>99 | 3.05 | 0.1033 | 0.9992 | 0.17 / 0.50 |
| PFHxS | 18O2-PFHxS | 399>80 | 399>99 | 4.63 | 0.0968 | 0.9988 | 0.20 / 0.50 |
| PFOS | 13C8-PFOS | 499>80 | 499>99 | 5.64 | 0.0915 | 0.9953 | 0.22 / 0.50 |
| 6:2 FTS | 13C2-6:2FTS | 427>407 | 427>81 | 5.19 | 0.0642 | 0.9979 | 0.31 / 1.00 |
| HFPO-DA | 13C3-HFPO-DA | 329>285 | 329>169 | 3.71 | 0.0839 | 0.9979 | 0.14 / 0.50 |

## Calibration curves and residual review

Curve labels are level ng/L / response ratio.

- PFOA: 0.25/0.021, 1/0.077, 5/0.406, 20/1.393, 80/5.986
- PFOS: 0.5/0.042, 2/0.184, 10/0.958, 50/4.753, 100/8.177
- HFPO-DA: 0.5/0.044, 2/0.175, 10/0.790, 50/4.400, 80/6.632

| Analyte | Max abs residual | Failing points | Review decision |
| --- | --- | --- | --- |
| PFOA | 7.8% | 0 | 1/x2 retained |
| PFOS | 10.6% | 0 | High calibrator inside +/-15% |
| HFPO-DA | 6.1% | 0 | No curvature |

## Table S4 - Accuracy and precision, part 1

| Analyte | Low rec / RSD | Mid rec / RSD | High rec / RSD | n | State |
| --- | --- | --- | --- | --- | --- |
| PFBA | 96 / 8.4 | 101 / 4.6 | 99 / 3.8 | 7 | Pass |
| PFPeA | 93 / 9.1 | 98 / 5.2 | 101 / 4.1 | 7 | Pass |
| PFHxA | 91 / 10.3 | 97 / 5.8 | 100 / 4.3 | 7 | Pass |
| PFHpA | 95 / 7.9 | 99 / 4.9 | 102 / 4.0 | 7 | Pass |
| PFOA | 98 / 6.8 | 103 / 3.7 | 101 / 3.2 | 7 | Pass |
| PFNA | 97 / 7.2 | 102 / 4.1 | 100 / 3.6 | 7 | Pass |

Acceptance: recovery 70-130%; RSD <= 20%. Table S4 continues on the next page with PFDA through HFPO-DA under repeated headers.

## Table S4 - Accuracy and precision, part 2

This page continues Table S4 from the prior page; repeated headers are not data rows.

| Analyte | Low rec / RSD | Mid rec / RSD | High rec / RSD | n | State |
| --- | --- | --- | --- | --- | --- |
| PFDA | 92 / 11.5 | 96 / 6.3 | 99 / 4.9 | 7 | Pass |
| PFBS | 104 / 9.7 | 99 / 4.8 | 98 / 4.0 | 7 | Pass |
| PFHxS | 101 / 8.9 | 100 / 4.4 | 97 / 3.9 | 7 | Pass |
| PFOS | 89 / 12.6 | 95 / 6.7 | 96 / 5.1 | 7 | Pass |
| 6:2 FTS | 86 / 14.8 | 92 / 7.4 | 94 / 6.3 | 7 | Pass |
| HFPO-DA | 99 / 7.5 | 104 / 4.2 | 103 / 3.5 | 7 | Pass |

| Analyte | Native | Spike | MS rec | MSD rec | RPD | Qualifier |
| --- | --- | --- | --- | --- | --- | --- |
| PFOA | 3.42 | 10.00 | 96 | 98 | 2.1 | None |
| PFOS | 0.74 | 10.00 | 91 | 88 | 3.4 | J: native <2x LOQ |
| PFHxS | 1.16 | 10.00 | 102 | 99 | 3.0 | None |
| HFPO-DA | <0.50 | 10.00 | 105 | 106 | 1.0 | U native |
| 6:2 FTS | <1.00 | 10.00 | 84 | 87 | 3.5 | Low bias monitored |

## Instrument sequence and reinjection review

| Seq | Type | Vial | Sample ID | Time | IS | Carry | State |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 01 | Blank | A01 | SBLK-01 | 08:10 | Y | Clear | Accepted |
| 02 | Cal | A02 | CAL-0.5 | 08:23 | Y | Clear | Accepted |
| 03 | Cal | A03 | CAL-1 | 08:36 | Y | Clear | Accepted |
| 04 | Cal | A04 | CAL-2 | 08:49 | Y | Clear | Accepted |
| 05 | Cal | A05 | CAL-5 | 09:02 | Y | Clear | Accepted |
| 06 | Cal | A06 | CAL-10 | 09:15 | Y | Clear | Accepted |
| 07 | Cal | A07 | CAL-20 | 09:28 | Y | Clear | Accepted |
| 08 | Cal | A08 | CAL-50 | 09:41 | Y | Clear | Accepted |
| 09 | Cal | A09 | CAL-80 | 09:54 | Y | Clear | Accepted |
| 10 | Blank | B01 | LRB-240410-01 | 10:07 | Y | Clear | Accepted |
| 11 | LCS | B02 | LCS-240410-01 | 10:20 | Y | Clear | Accepted |
| 12 | Sample | B03 | FB-240408-01 | 10:33 | Y | Clear | Accepted |
| 13 | Sample | B04 | DW-240408-02 | 10:46 | Y | Clear | Accepted |
| 14 | Sample | B05 | DW-240408-03 | 10:59 | Y | Clear | Accepted |
| 15 | MS | B06 | DW-240408-03-MS | 11:12 | Y | Clear | Accepted |
| 16 | MSD | B07 | DW-240408-03-MSD | 11:25 | Y | Clear | Accepted |
| 17 | CCV | B08 | CCV-10 | 11:38 | Y | Clear | Accepted |
| 18 | Sample | B09 | DW-240409-04 | 11:51 | N | Clear | Reinject |
| 19 | Sample | C01 | DW-240409-04-RI | 12:18 | Y | Clear | Accepted |
| 20 | Sample | C02 | DW-240409-05 | 12:31 | Y | Clear | Accepted |

Sequence 18 failed internal-standard recovery. Sequence 19 is the accepted reinjection used for final DW-240409-04 results. Analyst M. Iyer signed 2024-04-19 14:05; technical reviewer L. Chen signed 2024-04-22 09:40; QA reviewer R. Patel signed 2024-04-22 16:10.

## Chromatograms, final results, and uncertainty

Chromatogram axes are time (min) and intensity (cps). Panels: A LRB/PFOS has no reportable peak and noise 41 cps; B CAL-0.5/PFOS is 5.64 min, area 4,572, S/N 12; C DW-240408-03/PFOA is 4.41 min, area 25,621, 3.42 ng/L; D DW-240409-04 internal-standard overlay is 38% original and 91% on reinjection.

| Result ID | Sample | Analyte | Result | Qual. | U95 | Reference |
| --- | --- | --- | --- | --- | --- | --- |
| R-01 | FB-240408-01 | PFOA | <0.25 | U | - | p2 limit / context |
| R-02 | DW-240408-02 | PFOA | 2.18 | - | 0.42 | S7C / other sample |
| R-03 | DW-240408-02 | PFOS | 0.62 | J | 0.18 | S7B / cal context |
| R-04 | DW-240408-03 | PFOA | 3.42 | - | 0.55 | S7C / direct |
| R-05 | DW-240408-03 | PFOS | 0.74 | J | 0.19 | S7A / blank context |
| R-06 | DW-240409-04 | PFOA | 1.06 | J | 0.25 | S7D IS / Seq 19 |
| R-07 | DW-240409-04 | PFOS | <0.50 | U | - | S7D IS / Seq 19 |
| R-08 | DW-240409-05 | PFOA | 4.87 | - | 0.72 | No S7 panel |

| Analyte | u cal | u rep | u vol | u rec | U95 |
| --- | --- | --- | --- | --- | --- |
| PFOA | 5.2% | 4.1% | 1.5% | 3.6% | 15.4% |
| PFOS | 7.4% | 6.9% | 1.5% | 5.1% | 22.8% |
| HFPO-DA | 4.8% | 3.7% | 1.5% | 3.2% | 13.8% |
