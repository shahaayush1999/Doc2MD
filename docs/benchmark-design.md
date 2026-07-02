# Doc2MD Benchmark Design

Doc2MD evaluates whether a model can convert a document into faithful Markdown: preserving text, reading order, structure, tables, forms, figures, charts, captions, and useful descriptions of non-text visual content. It is not a summarization, QA, citation, or OCR torture benchmark.

The current benchmark direction is deliberately compact: build a small suite of hard, realistic document cases, run cheap capable models first, and only expand once the suite proves it can separate model behavior.

## Current Suite

The current runnable candidate is **Doc2MD-Hard-15**:

- 15 documents.
- 15 total PDF pages.
- Generated from `scripts/generate_hard_benchmark.py`.
- Stored under `benchmark/cases/`.
- Each case has an authoritative `gold.md` answer key.
- Each case has weighted fact obligations in `facts.json`.
- Scored by a Gemini 3.1 Flash Lite fact judge, with deterministic checklist checks retained as an audit signal.
- Designed to be difficult for models that rely too heavily on extracted PDF text, superficial OCR, generic table transcription, or single-pass visual summaries.

The target is not to trick models with artificial prompt-injection style documents. The cases are synthetic, but each represents a common real document failure mode. The v0.5.0 direction is compound document reasoning: pages where text, spatial grouping, tables, legends, checkboxes, charts, diagrams, footnotes, and reading order interact.

## Case Families

| Family | Cases | What it probes |
| --- | --- | --- |
| Visibility semantics | H01, H02 | Visible rendered content must win over hidden or covered stale PDF text. |
| Spatial normalization | H03, H21 | Gantt and schedule grids must become explicit rows with spans, owners, rooms, and legend semantics. |
| Tables in context | H15, H18 | Wide heatmaps and financial bridge tables require cell bindings, sign conventions, footnotes, and chart/table consistency. |
| Forms and dense state binding | H12, H19 | Bilingual labels, checkbox state, exact IDs, blank/pending semantics, EOB rows, summary cards, and deadlines. |
| Visual facts | H16, H20 | Multi-panel charts and floor-plan callouts require visual-to-text relation extraction. |
| Layout and reading order | H07, H11, H13, H14, H17 | Overlapping pitch-deck timelines, sidebars, scientific paper columns, borderless pitch-deck matrices, redlined contracts, margin comments. |

## Scoring

Each case is primarily scored by an LLM judge that receives:

- Case metadata.
- The known correct answer key from `gold.md`.
- Weighted fact obligations from `facts.json`.
- The candidate Markdown from the model run.

The current judge is `gemini-3.1-flash-lite` through Google Vertex with minimal reasoning. The judge compares semantic fidelity against the gold answer key and marks every fact obligation as `correct`, `partial`, `incorrect`, or `missing`. Different wording, table formatting, and natural-language descriptions are acceptable when they faithfully preserve the document's information.

The final score is a weighted dimension score:

| Dimension | Weight | Meaning |
| --- | ---: | --- |
| Accuracy | 75% | Weighted `facts.json` score for correct facts, numbers, labels, checkbox states, table bindings, chart/timeline bindings, redline state, and absence of contradictions. |
| Completeness | 10% | Coverage of all information in the gold answer key. |
| Structure | 10% | Reading order, grouping, table/list/form structure, and visual-to-text relationships. |
| Markdown quality | 5% | Clarity and usefulness of the Markdown representation. |

Accuracy dominates because a nicely structured Markdown document is still a bad reconstruction if it changes values, swaps labels, includes hidden/deleted text as current, or loses visible state. Computing accuracy from fact obligations makes the score more auditable than a single holistic judge number.

Each case also has weighted deterministic checks:

- `all`: required regex patterns all appear.
- `none`: prohibited regex patterns do not appear.
- `ordered`: required terms appear in the intended reading order.
- `near`: required terms appear within a local window.

Generator helpers distinguish escaped literal negatives from raw regex negatives. Use `none_check` only for literal strings and `none_regex_check` when a prohibited pattern intentionally uses regex syntax.

These checks no longer determine the primary score. They are stored under `deterministic` in each `score.json` so we can audit the LLM judge, catch obvious regressions, and identify where strict checklist scoring disagrees with semantic scoring.

The current scorer reports:

- Case score.
- Overall macro score.
- Family scores and family minimum.
- Judge dimension scores.
- Weighted fact score.
- Deterministic audit category scores.
- Model cost.
- Latency.
- Input and output tokens.
- Failure rate.
- Judge findings and weakest deterministic audit checks.

The public benchmark row should stay compact: one score per model, model cost, model time, and output tokens. Judge internals are for debugging the benchmark, not for leaderboard reporting.

## Calibration Rule

The first bar is: **calibration must preserve known capability ordering**.

For the current model set, Gemini 3.5 Flash should score clearly above Gemini 3.1 Flash Lite on visual-to-structure cases, and Gemini 3.1 Flash Lite should not be judged mainly against GPT-5.4 Nano because GPT Nano is a weaker visual reasoner. If the best public model saturates the suite, that is acceptable only if cheaper models still separate cleanly and the benchmark reports score, cost, latency, and output tokens.

## Expansion Policy

Do not grow the benchmark by accumulation. Add a case only when it covers a realistic failure mode that is not already represented.

Good candidates for future replacement cases:

- A technical/API excerpt with code blocks and callouts.
- A legal or policy excerpt with nested numbering and footnotes.
- A lightly degraded scan where OCR is necessary but not the main challenge.
- A genuinely hard scientific figure with subpanels and caption references.
- A multi-page section where a figure/table is referenced before appearing.

Keep extreme OCR, heavy handwriting, adversarial PDF internals, 100-page long-document stress tests, and leakage/tie-break cases outside the core suite until the compact benchmark is validated.
