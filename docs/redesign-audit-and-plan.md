# Doc2MD saturation diagnosis and redesign plan

Status: implemented corpus design awaiting anchor calibration. The historical scores below diagnose the retired 7-case corpus; they are not evidence about the replacement corpus.

## Answer-first diagnosis

The 92.4 versus 98.7 compression was caused primarily by construct loss, not by the anchors becoming similarly capable. The current corpus exposes native text on all 49 pages, contains no full-page scan, is short and sparse, and allocates most score weight to clean tables. Several visual answers are repeated in native captions, tables, or final summaries. The scorer also demonstrably credited facts that were absent from a candidate.

The current benchmark is therefore not safe to calibrate or publish. No new model inference should run until both the corpus modality and the evidence contract are replaced.

## Baseline data-quality profile

- 7 cases, 49 pages, 6,286 extractable words (about 128 per page).
- 39 native-only pages, 10 pages with both native text and an embedded raster, and 0 full-page raster pages.
- The nominal long-context case is 9 pages and only 1,219 extracted words.
- 117 scored regions and 1,946 leaves.
- Tables own 1,518 leaves (78.0%) and 57.55% of the equal-case score.
- Table, text, and structure regions together own 71.38% of the score before counting vector-chart labels that also survive text extraction.
- Embedded-raster regions represent only 12.58 score points. A conservative manual audit finds that at least 6.71 of those points are explicitly restated in native text, leaving at most about 5.88 points that require unique raster evidence.
- Historical Gemini 3.1 Flash-Lite results were perfect in five of seven cases across all three retired sample slots. P21 was unstable enough to reverse the anchor ordering in one sample.

### Case-level saturation evidence

| Current case | Pages / extracted words | Modality | Text-accessible score floor | Historical sample 001, Nano / Gemini | Disposition |
| --- | ---: | --- | ---: | ---: | --- |
| P07 launch readiness | 7 / 797 | 6 native, 1 mixed | 69.6% | 91.96 / 100 | Delete standalone; fold its useful multi-symbol matrix and precedence pattern into the long packet. |
| P12 PFAS validation | 7 / 1,015 | 5 native, 2 mixed | 65.5% | 82.16 / 100 | Keep role and harden substantially. |
| P15 architecture | 6 / 748 | 5 native, 1 mixed | 55.6% | 98.52 / 100 | Replace artifact; preserve technical spatial ownership. |
| P17 clinical monitoring | 9 / 1,219 | 7 native, 2 mixed | 77.8% | 100 / 100 | Replace as the long-context backbone. |
| P20 utility outage | 8 / 1,008 | 6 native, 2 mixed | 63.0% | 100 / 100 | Delete standalone; fold chronology, redline, and field-evidence patterns into other realistic packets. |
| P21 semiconductor | 8 / 936 | 7 native, 1 mixed | 72.4% | 86.21 / 84.48 | Keep role and harden; remove text that gives away image interpretation. |
| P23 office recovery | 4 / 563 | 3 native, 1 mixed | 95.8% | 86.25 / 97.92 | Preserve native-layer-recovery ownership but replace the benchmark-looking malformed artifact. |

The one-draw overall gap was only 5.33 points. P12 and P23 produced 79% of it, while P21 reversed the expected ordering. This is not broad capability differentiation.

## Proven scorer failure

GPT-5 Nano's historical P17 sample 001 used only image placeholders for pages 7 and 8. It did not contain `machine unavailable`, `MK`, `14:18`, `4.7`, `13:40`, `Return to stock`, or `Destroy`. Nevertheless, the evaluator marked all 17 scanned-form leaves correct.

Examples of invalid credit include:

- `4.7 C at 13:40` credited from a line containing only `9.1 C / 3 h` and `Quarantined`.
- Unchecked `Return to stock` and `Destroy` credited from a line that only said `Do not dose` was checked.
- Coordinator `MK` and the correction timestamp credited from an unrelated monitor-note line.

The deterministic evidence gate covered only generated table leaves and matched row key plus value without enforcing column identity. A correct value in the wrong field or a nearby row could therefore pass. Current scores must remain historical until typed evidence policies make such credit impossible.

## Consolidated suite design

Five cases are the smallest credible suite that does not force unrelated scientific, spatial, manufacturing-image, and malformed-office behaviors into implausible documents.

| Replacement role | Source disposition | Design envelope: pages | Native | Full scan | Mixed | Unique primary ownership |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Long regulated state packet | Replace P17; absorb P07 precedence and P20 chronology/redlines | 48 | 28 | 12 | 8 | Long-context completeness, entity continuity, chronology, form correction, and controlling state. |
| Scientific validation | Harden P12 | 12 | 6 | 3 | 3 | Exact scientific values, equations, dense/continued tables, OCR sequence records, and chromatograms. |
| Technical spatial coordination | Replace P15; absorb useful P20 one-line/photo patterns | 10 | 5 | 2 | 3 | Floorplans, directed networks, cross-sheet callouts, field markups, and spatial binding. |
| Manufacturing inspection | Harden P21 | 9 | 4 | 2 | 3 | Wafer coordinates, technical-image morphology, image-to-record binding, SPC, and MRB decisions. |
| Natural malformed-office recovery | Replace P23 source | 5 | 4 | 0 | 1 | Reading-order and table recovery from legitimate native objects when page rendering is clipped or overlapped. |
| **Total** |  | **84** | **47** | **19** | **18** |  |

These are the implemented physical counts. Every retained page carries plausible, independently useful, scored information. The resulting distribution is 56% native-only, 23% full-page scan, and 21% mixed pages.

## Capability contract

Each scored region will have a primary diagnostic axis, optional secondary axes, explicit source anchors, modality, text-only-recoverability status, and a source-to-gold section link.

| Diagnostic axis | Primary owner | Required independent evidence |
| --- | --- | --- |
| Precise recall | Scientific and long packets | Exact IDs, dates, signs, units, qualifiers, and state without native-text-only dominance. |
| Table reconstruction | Scientific and long packets | Header/row/column/value bindings, continuation, groups, and footnotes; exact column identity is enforced. |
| Layout and reading order | Malformed and technical packets | Recover section and table order without flattening locality. |
| Form and correction state | Long packet | Checked, unchecked, disabled, crossed, corrected, and signed states that are not restated in native prose. |
| Visual and spatial reasoning | Technical packet | Directed edges, adjacency, callouts, and field markup not recoverable from captions. |
| Image and chart evidence | Manufacturing and scientific packets | Morphology, trace behavior, thresholds, and bindings not duplicated in text. |
| Long-context coherence | Long packet | Multiple distant entity joins, tail coverage, table continuation, and evolving state—not one cliff-like completeness fact. |
| Source precedence | Long, scientific, and technical packets | Draft/final/redline/correction relationships with the controlling value explicitly preserved. |
| Malformed native recovery | Office packet | Page image alone is insufficient; legitimate native text must repair visible clipping/overlap. |

Diagnostic capability rollups explain results; they do not create arbitrary target-shaping weights. Public aggregation remains deliberate and case-level rather than page-weighted.

## Facts and evidence contract

The replacement facts schema must:

- Anchor each region to one or more source pages and the corresponding gold section.
- Separate modality from semantic claim type.
- Mark whether evidence is unique or redundantly corroborated and whether native text alone is sufficient.
- Use canonical claim identities so the same semantic fact is not scored repeatedly merely because it appears on several pages.
- Represent exact table bindings with table/header, row, column, and value identity.
- Represent form polarity and directed relationships explicitly.
- Remove generic, intuition-based partial credit. Qualitative descriptions are decomposed into explicit components.
- Require server-validated candidate evidence before `correct` credit.
- Preserve continuous signed region utility: correct is best, missing is zero credit, incorrect is below missing, and proven closed-world unsupported content is worse still.
- Clamp only the public case score.

The scorer regression suite must include reference, omission, wrong scalar/unit/sign, row/column swap, adjacent-row shift, entity swap, edge reversal, checkbox flip, superseded-as-current, wrong source binding, caption-only visual reconstruction, entity drift, tail and middle deletion, continuation corruption, detached footnote, extra closed-world row/form option, simultaneous correct-and-wrong assertions, flattened hierarchy, unrelated cited lines, and image-placeholder-only pages.

This requirement is implemented as two deliberately separate audit layers:

- `src/scorerMutationMatrix.test.ts` is the broad, provider-free deterministic matrix. It uses compact synthetic facts and candidates for 23 controlled mutations covering every defect class above. Every fixture first proves an all-correct reference, then asserts the exact changed leaf ids and statuses. Expected-leaf defects must produce no unsupported-claim penalty; novel closed-world rows/options must leave every expected leaf unchanged and incur exactly one region-derived penalty.
- `src/auditScorer.ts` is the narrower paid, corpus-grounded P23 evaluator audit. It makes exactly six one-shot judgments: reference, omission, scalar substitution, invoice misbinding, keyed hallucination, and wrong source precedence. Those calls test evaluator behavior on the real case, but they are not substitutes for the broader deterministic mutation matrix.

## Modality and leakage gates

Before paid inference, the release audit must show:

- Meaningful native-only, full-raster, mixed, and malformed-native coverage.
- Important score budget that is not recoverable from extracted native text.
- No visual-only answer in adjacent captions, other-page prose/tables, filenames, or section codes.
- Realistic corroboration classified as mixed and scored once rather than misrepresented as vision.
- At least one case whose page image is insufficient without native-layer recovery.
- At least one genuinely long packet with multiple independently scored distant joins and later-page obligations.

## Execution gate

No new provider calls are authorized by this plan until generation, rendering, all-page visual inspection, source/gold/facts audit, deterministic tests, preflight, and scorer counterfactuals pass. Then run GPT-5 Nano once and Gemini 3.1 Flash-Lite once, inspect their complete outputs and judgments, and attribute any gap by capability. A saturated or single-case-driven result remains release-blocking even if all code checks pass.
