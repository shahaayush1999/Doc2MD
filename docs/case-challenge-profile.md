# Doc2MD Case Challenge Profile

This internal profile defines why each case belongs in the canonical 7-case, 49-page suite. It is not included in model input.

| Case | Pages | Primary challenge | Boundary with the rest of the suite |
| --- | ---: | --- | --- |
| P07 launch readiness dossier | 7 | Cross-functional launch packet with dependencies, status heatmaps, region decisions, customer readiness, risk registers, and draft-versus-final precedence. | Owns business-readiness synthesis across mixed operational tables and charts. P20 and P21 also contain source-state conflicts, but their primary difficulty is technical incident or manufacturing evidence. |
| P12 PFAS method validation | 7 | Scientific supplement with equations, calibration and continuation tables, spike duplicates, chromatogram panels, reinjection state, qualifiers, and uncertainty. | Owns scientific notation, laboratory calculations, instrument evidence, and dense analytical-table reconstruction. |
| P15 architecture floorplan diagrams | 6 | Coordination set with a scaled floorplan, room and door geometry, rack elevations, directed topology, patch/VLAN bindings, panel schedules, and RFI resolution. | Owns building-scale spatial binding and engineering revision markup. P20 also contains a directed network, but as incident chronology rather than facilities coordination. |
| P17 clinical trial site monitoring | 9 | Longitudinal subject records, visit windows, lab flags, adverse events, protocol deviations, drug accountability, corrected eCRF states, and query closure. | Owns patient/site chronology and regulated form-state reconciliation. P21 is also a controlled release workflow, but for manufacturing lots rather than subjects and visits. |
| P20 utility outage restoration | 8 | SCADA sequence, switching log, feeder one-line, restoration chart, DER clearance, customer impact, source precedence, and annotated field evidence. | Owns grid topology, event order, restoration dependencies, and nested customer totals. Its three field-photo fixtures are synthetic and intentionally annotated by deterministic builder code. |
| P21 semiconductor lot disposition | 8 | Wafer maps, metrology, SPC exceptions, recipe conflict, SEM-style evidence, MRB decisions, reliability results, and shipping release logic. | Owns semiconductor spatial maps, process-control evidence, and lot-level disposition. Its four SEM-style fixtures are synthetic and are not real microscopy measurements. |
| P23 native text-layer recovery | 4 | A genuine malformed LibreOffice PDF export whose rendered pages are severely overlapped or clipped while legitimate native text preserves the recoverable memo, registers, tables, and controlling statement. | Owns provider-pipeline recovery from a broken office export. It is intentionally not a clean visual-reasoning case; its malformed layout must remain visible and its native text must remain recoverable. |

## Maintenance rules

- Keep a case only when it owns at least one realistic primary difficulty that no other scored case owns. Merge or remove redundant cases.
- Do not tune content to force an arbitrary model ranking or target score. If models saturate a fair case, report the saturation and use cost, latency, token use, and reliability as separate operating measures.
- Treat `source.pdf` as ground truth. Keep `gold.md`, `facts.json`, and `spec.md` synchronized with every source revision, including exact labels, values, geometry, chronology, and controlling document state.
- Audit overlaps deliberately. Shared primitives are acceptable when their document function differs; duplicated primary difficulty is not.
- Keep synthetic visual fixtures clearly identified in repository documentation and out of claims about real-world evidence.
- Preserve P23's visible corruption as an intentional exception to normal layout-quality expectations. Validate its native text recovery and source order instead of “fixing” its overlap.
