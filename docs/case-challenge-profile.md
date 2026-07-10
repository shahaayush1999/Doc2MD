# Doc2MD case challenge profile

This internal profile defines why each case belongs in the canonical five-case, 84-page suite. It is not included in model input.

| Case | Pages | Primary challenge | Boundary with the rest of the suite |
| --- | ---: | --- | --- |
| P12 PFAS method validation | 12 | Scientific equations, continued tables, full-page bench and sequence scans, calibration curves, chromatograms, exact calculations, and a cross-modal correction-to-release chain. | Owns scientific precision and analytical evidence. Its source-precedence chain is laboratory-specific rather than the broad longitudinal state tracked by P17. |
| P15 technical spatial coordination | 10 | Floorplans, directed topology, cross-sheet callouts, field markups, revision state, and exact equipment/network bindings across native, scanned, and mixed sheets. | Owns spatial and directed technical relationships. Other cases contain charts or maps, but do not require a coordinated drawing-set reconstruction. |
| P17 clinical site monitoring | 48 | A genuinely long regulated packet with distant entity joins, continued logs, scanned forms, corrected states, source precedence, cumulative chronology, and tail obligations. | Owns long-context completeness and longitudinal state. It absorbs the useful precedence, redline, and chronology patterns from retired P07 and P20 without duplicating their standalone cases. |
| P21 semiconductor lot disposition | 9 | Wafer coordinates, metrology/SPC state, full-page scanned reviews, SEM-style morphology, inspection-form state, mixed-source joins, and final MRB authority. | Owns technical-image-to-record binding and manufacturing disposition. Its committed SEM-style fixtures are synthetic and are not real microscopy measurements. |
| P23 native text-layer recovery | 5 | A genuine DOCX-to-LibreOffice PDF export with clipped/displaced visible layout while legitimate native objects retain recoverable task text, plus one raster-only finance stamp. | Owns the inverse-modality challenge: page images alone are insufficient, and the native layer must repair a malformed office rendering. |

## Construct coverage matrix

`P` marks primary ownership and `S` marks meaningful supporting coverage. A dash means the case is not relied on for that construct. This matrix is a design/semantic audit; measured budget shares remain in `reports/corpus-audit.json`.

| Required construct | P12 | P15 | P17 | P21 | P23 |
| --- | :---: | :---: | :---: | :---: | :---: |
| 1. Exact text, numbers, dates, IDs, units, signs, qualifiers, and states | P | S | P | S | P |
| 2. Row, column, header, and value binding | P | S | P | P | P |
| 3. Borderless, nested, continued, grouped, and footnoted tables | P | S | P | S | S |
| 4. Realistic long-context completeness | S | S | P | S | S |
| 5. Distant entity continuity and cross-references | S | P | P | S | S |
| 6. Chronology, cumulative state, totals, and dependencies | P | S | P | S | P |
| 7. Reading order, hierarchy, captions, footnotes, annotations, and locality | S | P | S | S | P |
| 8. Checked, unchecked, disabled, corrected, struck, and superseded states | S | P | P | S | S |
| 9. Draft/final/correction/redline source precedence | P | P | P | P | P |
| 10. Chart axes, legends, thresholds, colors, labels, trends, and values | P | – | S | P | – |
| 11. Diagram, map, floorplan, network, and directed/spatial relations | S | P | S | P | – |
| 12. Photo and technical-image evidence bound to records | S | P | S | P | S |
| 13. Born-digital native text | P | P | P | P | P |
| 14. Full-page raster and scanned material | P | P | P | P | – |
| 15. Mixed native/raster evidence in one document | P | P | P | P | P |
| 16. Human-readable skew, compression, stamps, and handwriting-like fields | P | P | P | P | S |
| 17. Legitimate malformed-export/native-layer recovery | – | – | – | – | P |
| 18. Explicit downstream-machine relationships across flexible Markdown | P | P | P | P | P |

## Implemented corpus accounting

- 84 pages: 47 native-only, 19 full-page raster, and 18 mixed.
- 12,490 words recoverable from native text, concentrated deliberately rather than present on every page.
- 200 scored regions, 1,205 atomic leaves, and 372 raw evidence-budget units.
- Under the official equal-case score, effective modality shares are 47.20% native text, 29.90% raster, 12.60% mixed, 7.99% vector geometry, and 2.31% native-layer recovery.
- Declared text-only-recoverable evidence is 46.77% by raw pooled budget and 47.20% under equal-case weighting. The stricter PDF text-layer audit recovers only 18.57% exactly, because declarations describe potential recoverability rather than proven complete extraction.
- The canonical reference audit supports 1,205/1,205 leaves. Seventy-four qualitative leaves are semantic-only and remain a mandatory human-review stratum.

## Maintenance rules

- Keep a case only when it owns at least one realistic primary difficulty that no other scored case owns.
- Do not tune content or weights to force anchor scores. Calibration bands are diagnostic release guardrails.
- Treat `source.pdf` as ground truth and keep `gold.md`, `facts.json`, and `spec.md` synchronized with every source revision.
- Score a semantic claim once through a canonical claim identity even when several pages corroborate it.
- Keep important visual facts out of adjacent native captions and summaries.
- Keep synthetic visual fixtures documented and out of claims about real-world evidence.
- Preserve P23's authentic export defect. Validate native-layer recovery instead of cosmetically repairing the source.
