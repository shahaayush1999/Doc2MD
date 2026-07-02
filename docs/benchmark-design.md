# Doc2MD Benchmark Design

Doc2MD evaluates whether a model can convert a document into faithful Markdown: preserving text, reading order, structure, tables, forms, figures, charts, captions, and useful descriptions of non-text visual content. It is not a summarization, QA, citation, or OCR torture benchmark.

The current benchmark direction is deliberately compact: build a small suite of hard, realistic document cases, run cheap capable models first, and only expand once the suite proves it can separate model behavior.

## Current Suite

The current runnable candidate is **Doc2MD-Hard-11**:

- 11 documents.
- 11 total PDF pages.
- Generated from `scripts/generate_hard_benchmark.py`.
- Stored under `benchmark/cases/`.
- Scored by deterministic checklist checks in each case's `checks.json`.
- Designed to be difficult for models that rely too heavily on extracted PDF text, superficial OCR, or generic table transcription.

The target is not to trick models with artificial prompt-injection style documents. The cases are synthetic, but each represents a common real document failure mode.

## Case Families

| Family | Cases | What it probes |
| --- | --- | --- |
| Visibility semantics | H01, H02 | Visible rendered content must win over hidden or covered stale PDF text. |
| Spatial normalization | H03 | A raster Gantt chart must become explicit task/owner/start/end rows. |
| Tables in context | H15 | Wide heatmap table, slash markers, legend semantics, weekend columns. |
| Forms and dense state binding | H12 | Bilingual labels, checkbox state, exact case IDs, blank/pending semantics. |
| Visual facts | H16 | Multi-panel line chart, stacked bar chart, matrix, and cross-panel warning. |
| Layout and reading order | H07, H11, H13, H14, H17 | Broken slide exports, sidebars, scientific paper columns, borderless pitch-deck matrices, redlined contracts, margin comments. |

## Scoring

Each case has weighted deterministic checks:

- `all`: required regex patterns all appear.
- `none`: prohibited regex patterns do not appear.
- `ordered`: required terms appear in the intended reading order.
- `near`: required terms appear within a local window.

The current scorer reports:

- Case score.
- Overall macro score.
- Family scores and family minimum.
- Category scores.
- Estimated cost.
- Latency.
- Input and output tokens.
- Failure rate.
- Weakest failed checks.

The scorer is intentionally simple for now. It should stay simple until the suite itself proves useful. Future versions can add Markdown parsing, table-grid scoring, and structured block alignment after the hard cases are stable.

## Calibration Rule

The first bar is: **calibration must preserve known capability ordering**.

For the current model set, Gemini 3.5 Flash should score clearly above Gemini 3.1 Flash Lite on visual-to-structure cases, and Gemini 3.1 Flash Lite should not be judged mainly against GPT-5.4 Nano because GPT Nano is a weaker visual reasoner. If the best public model saturates the suite, that is acceptable only if cheaper models still separate cleanly and the benchmark reports score, cost, latency, and tokens as a Pareto frontier.

## Expansion Policy

Do not grow the benchmark by accumulation. Add a case only when it covers a realistic failure mode that is not already represented.

Good candidates for future replacement cases:

- A technical/API excerpt with code blocks and callouts.
- A legal or policy excerpt with nested numbering and footnotes.
- A lightly degraded scan where OCR is necessary but not the main challenge.
- A genuinely hard scientific figure with subpanels and caption references.
- A multi-page section where a figure/table is referenced before appearing.

Keep extreme OCR, heavy handwriting, adversarial PDF internals, 100-page long-document stress tests, and leakage/tie-break cases outside the core suite until the compact benchmark is validated.
