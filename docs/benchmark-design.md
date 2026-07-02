# Doc2MD Benchmark Design

Doc2MD evaluates whether a model can convert a document into faithful Markdown: preserving text, reading order, structure, tables, forms, figures, charts, captions, annotations, and useful descriptions of non-text visual content. It is not summarization, QA, citation, or an OCR torture test.

## Release Target

The benchmark should consolidate around one scored suite: **Doc2MD-Core-16**.

There should not be separate public easy, hard, probe, sanity, or private variants before the first release. Development can generate candidate cases, but the repo should converge on one release benchmark with one score per model.

Public reporting stays simple:

| Model | Score | Cost | Time | Output tokens |
| --- | ---: | ---: | ---: | ---: |

Evaluator cost, judge runtime, family subscores, findings, and deterministic audit details are internal debugging artifacts, not public leaderboard columns.

## Current Status

`Doc2MD-Hard-15` v0.5.0 is a failed calibration, not the release suite.

It is useful as a development artifact because it showed what does and does not separate models. It is not useful as a ranking benchmark because GPT-4o Mini scores `81.1`, too close to current cheap models:

| Model | v0.5.0 Score |
| --- | ---: |
| Gemini 3.1 Flash Lite | 89.6 |
| GPT-5.4 Nano | 84.2 |
| GPT-4o Mini | 81.1 |

The failure mode is clear: many cases are clean, compact, single-challenge documents where OCR plus straightforward reconstruction is enough.

## Calibration Target

The first release should roughly target:

| Model class | Target score |
| --- | ---: |
| Text extraction / OCR-only baseline | 10-30 |
| Old weak multimodal model, e.g. GPT-4o Mini | 35-55 |
| Cheap current multimodal model | 55-75 |
| Strong visual/document model | 75-90 |
| Frontier model | 85-94 |
| Human-audited reconstruction | 97-100 |

If GPT-4o Mini scores above `60`, the benchmark is still too easy. If a case gives GPT-4o Mini above `85` and the best model above `92`, delete or rebuild it unless it is indispensable and very low weight.

## Design Principle

A case is useful only if a plaintext OCR transcript is insufficient to score well.

Every scored case should require at least one of:

- Dense row/column/person/date binding.
- Visual state that changes meaning: color, slash, hatch, strikeout, disabled, circled, checked, unchecked, moved, inserted, deleted.
- Spatial measurement or grid position.
- Multi-element consistency: table plus chart, form plus summary card, diagram plus punch list, note plus visible correction.
- Cross-page continuation or source precedence.
- Annotation anchoring: comments, arrows, sticky notes, margin notes, callouts.

Do not add cases by accumulation. Replace saturated cases.

## Current Case Triage

| Current case | Decision | Reason |
| --- | --- | --- |
| H01 Hidden Stale Release | Delete from scored suite | Fully saturated; relies on one PDF-layer trick. |
| H02 Opaque Stale Shipment | Rebuild | Good source-precedence idea, but unstable ordering. |
| H03 Raster Gantt | Rebuild before scoring | Hard, but model ordering is inverted. |
| H07 Pitch Timeline | Harden | Useful layout binding, but too weak. |
| H11 Two-Column Sidebar | Harden or replace | Clean two-column reading order is mostly solved. |
| H12 Bilingual Credit | Replace | Simple form state is saturated. |
| H13 Scientific Page | Harden | Important family, currently too clean. |
| H14 Borderless Matrix | Keep and harden | Strong separator; dense spatial binding works. |
| H15 Heatmap | Keep and harden | Best current separator; visual table semantics work. |
| H16 Metrics Dashboard | Rebuild before scoring | Inverted ordering suggests ambiguity or bad fact design. |
| H17 Redlined Contract | Replace | Redline is too clean and saturated. |
| H18 Financial ARR Bridge | Harden | Important family, but too easy. |
| H19 Insurance EOB | Replace | Saturated; table/form too clean. |
| H20 Floorplan Punch List | Replace | Table alone carries too much; map is too easy. |
| H21 Conference Schedule | Harden | Valuable, but needs harder spans/icons/continuation. |

## Doc2MD-Core-16

The release suite should be these 16 cases. Existing code can reuse current IDs later, but the design target is this single suite.

| ID | Case | What it tests |
| --- | --- | --- |
| D01 | Layered Release Packet | Source precedence across visible corrections, covered/stale text, and an appendix. |
| D02 | Borderless Executive Team Matrix v2 | Dense column binding with icons, spanning notes, and group headers. |
| D03 | Financial ARR Bridge With Waterfall | Multi-level financial table, signs, units, subtotal exclusions, footnotes, and chart consistency. |
| D04 | Operations Heatmap Calendar v2 | Dense visual table semantics: color, letter, slash, hatch, legend exceptions, weekend columns. |
| D05 | Raster Gantt With Change Callout | Bar-position start/end inference plus visible correction callout and dependencies. |
| D06 | Conference Schedule With Merged Cells | Multi-day room/time grid, merged cells, icons, cancellations, split sessions. |
| D07 | Corrected Bilingual Service Form | Checked/unchecked/disabled/crossed-out/circled/corrected form states. |
| D08 | Insurance EOB Appeal Packet | Multi-page EOB with summary/table conflicts, line items, footnotes, deadline, final responsibility. |
| D09 | Redlined Contract Negotiation | Insertions, deletions, moved text, unresolved comments, anchors, final effective clause. |
| D10 | Clinic Floorplan Punch List v2 | Map-only facts, rotated labels, legend symbols, table/map inconsistencies. |
| D11 | Network Architecture Swimlane Diagram | Nodes, swimlanes, arrows, retry loops, optional dashed paths, callouts. |
| D12 | Scientific Article Page v2 | Two-column paper with equation, subfigures, table notes, sidebar, footnote anchors. |
| D13 | Scientific Supplement Continuation | Multi-page table continuation, repeated headers, caption continuation, row footnotes. |
| D14 | Incident Dashboard With Cross-Panel Warning | Chart values, threshold band, stacked bars, matrix, warning derived from panels. |
| D15 | Operational Packet With Conflicting Attachments | Email, invoice, delivery slip, packing table, visible correction, conflicting dates. |
| D16 | Annotated Product Review Slide | UI screenshot, sticky notes, arrows, badges, decision table, annotation anchoring. |

## Difficulty Mix

The suite should be hard-skewed but not all extreme:

| Difficulty | Share | Purpose |
| --- | ---: | --- |
| Easy sanity | 5-10% | Catch broken prompting/OCR without deciding rankings. |
| Medium | 20-30% | Separate weak from competent models. |
| Hard | 60-70% | Drive leaderboard spread. |

For a 16-case suite, that means roughly:

- 1 easy case.
- 4 medium cases.
- 11 hard cases.

Saturated easy cases must have low influence. They should never let weak models coast to a high final score.

## Scoring

Each case should keep:

- `source.pdf`
- `gold.md`
- `facts.json`

The public score is the weighted case average. Each fact should be atomic and local, not a broad holistic instruction.

Fact categories should include:

- `table_cell`
- `form_state`
- `forbidden_text`
- `reading_order`
- `visual_relation`
- `chart_value`
- `redline_state`
- `cross_page_binding`
- `annotation_anchor`

Facts should include credit rules when structure matters. A value appearing somewhere in prose should not receive full credit if the task requires row/column binding, checkbox state, or comment anchoring.

Use case-level caps:

- Summary instead of reconstruction: max `50`.
- Primary table missing in table-heavy case: max `65`.
- Visible source-precedence failure: max `45`.
- Redline output only as clean final text: max `65`.
- Diagram case transcribes table but ignores diagram-only facts: max `65`.

## Release Rule

Before release:

- GPT-4o Mini should average `35-55`.
- Gemini 3.1 Flash Lite should be meaningfully above GPT-4o Mini.
- The gap between weak and strong models should be at least `25` points.
- Cases where weak models beat strong models must be manually inspected and rebuilt unless the inversion is clearly real.
- Text-only extraction should score poorly on most cases.

The benchmark is ready only when the suite creates real spread without relying on OCR degradation, malicious prompt injection, or unrealistic hidden traps.
