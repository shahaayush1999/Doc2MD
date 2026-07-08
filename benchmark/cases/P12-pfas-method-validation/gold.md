# MV-PFAS-24-017 Rev A: LC-MS/MS Validation of 12 PFAS

North River Environmental Laboratory validated EPA 533 modified isotope dilution LC-MS/MS for 12 PFAS in finished drinking water. Instrument: SCIEX 6500+ QTRAP, ESI negative. Column: Waters Acquity BEH C18, 2.1 x 50 mm, 1.7 um. Injection 5 uL. Mobile A is 5 mM ammonium acetate in water and Mobile B is methanol. Study dates are 2024-04-08 to 2024-04-19.

## Workflow and Manifest

Workflow: receipt -> preservation check -> SPE extraction -> nitrogen dry-down -> reconstitution -> LC-MS/MS -> review.

Gradient table: 0.0 min 35% B flow 0.30 mL/min; 0.5 min 35% B 0.30; 6.0 min 95% B 0.35; 8.5 min 95% B 0.35; 8.6 min 35% B 0.30; 11.0 min 35% B 0.30.

Manifest rows include FB-240408-01 field blank collected 2024-04-08 09:10 received 15:42 pH 6.8 chlorine <0.02 volume 252 OK; DW-240408-02 finished water pH 7.2 volume 251 OK; DW-240408-03 pH 7.1 volume 249 OK; DW-240409-04 pH 7.4 volume 250 OK; DW-240409-05 pH 7.3 volume 250 OK; LRB-240410-01 prepared; LCS-240410-01 prepared; MSD-240410-03 prepared.

## Calibration

Equations: R = A_native / A_IS. C_sample = ((R - b) / m) * DF. LOD = t_(n-1,0.99) * SD_low. U95 = k * sqrt(u_cal^2 + u_rep^2 + u_vol^2 + u_rec^2), k=2.

Calibration table includes all analytes PFBA, PFPeA, PFHxA, PFHpA, PFOA, PFNA, PFDA, PFBS, PFHxS, PFOS, 6:2 FTS, and HFPO-DA with quantifier/qualifier transitions, RT, slope m, intercept b, R2, range, LOD, and LOQ. Key rows: PFOA uses 13C8-PFOA, quantifier 413>369, qualifier 413>169, RT 4.41, m 0.0749, b 0.0044, R2 0.9994, range 0.25-80, LOD 0.08, LOQ 0.25. PFOS uses 13C8-PFOS, 499>80, 499>99, RT 5.64, m 0.0915, b 0.0081, R2 0.9982, range 0.50-100, LOD 0.22, LOQ 0.50. HFPO-DA uses 13C3-HFPO-DA, 329>285, 329>169, RT 3.71, R2 0.9993, LOD 0.14, LOQ 0.50.

## Calibration Curves and Residuals

Plotted levels include PFOA response values 0.0232 at 0.25 ng/L, 0.0419 at 0.50, 0.0791 at 1.00, 0.1538 at 2.00, 0.3785 at 5.00, 0.7530 at 10.00, 1.5012 at 20.00, 3.7501 at 50.00, and 5.9960 at 80.00. PFOS response values are 0.0540 at 0.50, 0.0992 at 1.00, 0.1910 at 2.00, 0.4658 at 5.00, 0.9216 at 10.00, 1.8360 at 20.00, 4.5860 at 50.00, and 9.1510 at 100.00. HFPO-DA response values are 0.0460 at 0.50 through 6.7160 at 80.00.

Residual table: PFOA max absolute residual 7.8%, 0 failing points, weighted 1/x2 retained. PFOS max absolute residual 10.6%, 0 failing points, high calibrator within +/-15%. HFPO-DA max absolute residual 6.1%, 0 failing points, no curvature observed.

## Table S4 Accuracy and Precision

Table S4 is one continuation table across pages 4 and 5. Rows 1-7: PFBA 96/8.4, 101/4.6, 99/3.8, N 7 Pass; PFPeA 93/9.1, 98/5.2, 101/4.1 Pass; PFHxA 91/10.3, 97/5.8, 100/4.3 Pass; PFHpA 95/7.9, 99/4.9, 102/4.0 Pass; PFOA 98/6.8, 103/3.7, 101/3.2 Pass; PFNA 97/7.2, 102/4.1, 100/3.6 Pass; PFDA 92/11.5, 96/6.3, 99/4.9 Pass. Acceptance is 70-130% recovery and RSD <= 20%. Low level equals 2x LOQ for PFOA/PFNA/PFDA and equals LOQ for remaining analytes.

Rows 8-12: PFBS 104/9.7, 99/4.8, 98/4.0 Pass; PFHxS 101/8.9, 100/4.4, 97/3.9 Pass; PFOS 89/12.6, 95/6.7, 96/5.1 Pass; 6:2 FTS 86/14.8, 92/7.4, 94/6.3 Pass; HFPO-DA 99/7.5, 104/4.2, 103/3.5 Pass.

Matrix spike table for DW-240408-03: PFOA native 3.42, spike 10.00, MS 96, MSD 98, RPD 2.1, no flag. PFOS native 0.74, MS 91, MSD 88, RPD 3.4, flag J-native below 2x LOQ. PFHxS native 1.16, MS 102, MSD 99, RPD 3.0. HFPO-DA native <0.50, MS 105, MSD 106, RPD 1.0, U-native. 6:2 FTS native <1.00, MS 84, MSD 87, RPD 3.5, low bias monitored.

## Batch Sequence and Chromatograms

{md_table(seq_rows[0], seq_rows[1:])}

Sequence 18 DW-240409-04 at 11:51 has InternalStd_OK No, carryover Yes, state Reinject. Sequence 19 DW-240409-04-RI at 12:18 has InternalStd_OK Yes, carryover Yes, state Accepted and controls final results. Review trail: M. Iyer 2024-04-19 14:05, L. Chen 2024-04-22 09:40, R. Patel 2024-04-22 16:10.

Chromatogram panel facts: A LRB blank PFOS has no peak and noise 41 cps. B CAL-0.5 PFOS has RT 5.64, area 4,572, S/N 12. C DW-240408-03 PFOA has RT 4.41, area 25,621, concentration 3.42 ng/L. D DW-240408-03 PFOS has RT 5.65, area 6,318, concentration 0.74 ng/L. E DW-240408-03-MS PFHxS has RT 4.63, area 98,114, concentration 11.36 ng/L. F DW-240409-04 original vs reinjection IS overlay has original IS recovery 38% and reinjection IS recovery 91%. Retention windows: PFOA 4.41 +/-0.08, PFHxS 4.63 +/-0.08, 6:2 FTS 5.19 +/-0.10, PFOS 5.64 +/-0.10.

## Final Results and Uncertainty

Final result rows include FB-240408-01 PFOA <0.25 U and PFOS <0.50 U; DW-240408-02 PFOA 2.18 U95 0.42 Fig S7C, PFOS 0.62 J U95 0.18 Fig S7D, PFHxS 0.91 J U95 0.21 Table S5; DW-240408-03 PFOA 3.42 U95 0.55 Fig S7C, PFOS 0.74 J U95 0.19 Fig S7D, HFPO-DA <0.50 U Table S2; DW-240409-04 PFOA 1.06 J U95 0.25 Seq 19 and PFOS <0.50 U Seq 19; DW-240409-05 PFOA 4.87 U95 0.72 Table S8 and PFOS 1.34 U95 0.29 Table S8.

Uncertainty budget: Calibration PFOA 5.2%, PFOS 7.4%, HFPO-DA 4.8%; repeatability 4.1/6.9/3.7; volume 1.5/1.5/1.5; recovery 3.6/5.1/3.2; combined u 7.7/11.4/6.9; expanded U k=2 15.4/22.8/13.8. Qualifiers: U means not detected, J estimated, RI reinjection, MS matrix spike, MSD matrix spike duplicate.
