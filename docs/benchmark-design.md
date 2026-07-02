# Doc2MD Benchmark Design

Doc2MD evaluates whether a model can convert a document into faithful Markdown: preserving text, reading order, structure, tables, forms, figures, charts, captions, math/code, and useful descriptions of non-text visual content. It is not a summarization or QA benchmark.

The benchmark should be compact and diagnostic. Saturation is acceptable if score, cost, latency, tokens, and variance still identify a Pareto frontier.

## Recommendation

Build **Doc2MD-Core-25**:

- 25 documents total.
- Roughly 60-90 pages total.
- 5 public calibration documents.
- 20 hidden scored documents.
- Human-verified structured gold, not only gold Markdown.
- Family-level scores plus one headline score.
- Cost, latency, input tokens, output tokens, failure rate, and repeated-run variance reported with every model result.

The current generated experiments are useful as a research pool, but they should not become the benchmark by accumulation. Core cases should be selected deliberately from the taxonomy below.

## Related Benchmarks

Existing benchmarks cover pieces of the problem, but not the exact Doc2MD target: document-level Markdown reconstruction with cost-aware evaluation.

| Area | Relevant benchmarks | Overlap with Doc2MD | Gap for Doc2MD |
| --- | --- | --- | --- |
| PDF/document-to-Markdown parsing | [READoc](https://arxiv.org/html/2409.05137v3), [OmniDocBench](https://github.com/opendatalab/OmniDocBench), [olmOCR-Bench](https://huggingface.co/datasets/allenai/olmOCR-bench), fr-bench-pdf2md, ParseBench | Directly relevant to PDF parsing, Markdown/structured extraction, layout, reading order, tables. | Often larger, page-heavy, domain-specific, or not focused on a compact hidden document-level suite. |
| Layout analysis | PubLayNet, [DocLayNet](https://github.com/DS4SD/DocLayNet), DocBank, M6Doc | Layout blocks, headings, tables, captions, figures, reading order. | Layout detection is not faithful Markdown reconstruction. |
| Table extraction | [PubTables-1M](https://www.microsoft.com/en-us/research/publication/pubtables-1m/), PubTabNet, SciTSR, FinTabNet, TableBank, TEDS, GriTS | Table structure, spans, cell text, headers, blank cells. | Cropped-table benchmarks miss document context: captions, footnotes, surrounding text, placement, repeated headers. |
| Forms and key-value extraction | [FUNSD](https://guillaumejaume.github.io/FUNSD/), CORD, SROIE, Kleister, XFUND | Forms, receipts, key-value pairs, field labels, checkboxes. | KIE extracts selected fields; Doc2MD must reconstruct the full readable document. |
| Document VQA and long document understanding | [DocVQA](https://www.docvqa.org/), InfographicVQA, MP-DocVQA, [MMLongBench-Doc](https://arxiv.org/abs/2407.01523), SlideVQA | Multimodal document understanding, long PDFs, slides, infographics. | QA can succeed while most document content is dropped. |
| Chart and figure understanding | [ChartQA](https://arxiv.org/abs/2203.10244), ChartQAPro, PlotQA, DVQA, FigureQA | Chart facts, axes, legends, visual reasoning. | Chart QA asks isolated questions; Doc2MD needs inline figure reconstruction and durable visual facts. |
| OCR robustness | OCRBench, OCRBench v2, MDPBench, Real5-OmniDocBench | Scans, skew, physical capture, non-Latin scripts, hard OCR. | Doc2MD should include light robustness but not become an OCR torture test. |
| Formula recognition and Markdown validity | im2latex-100K, UniMER, CROHME, [CommonMark](https://commonmark.org/) | Formula markup, Markdown syntax validation. | Formula-only tasks miss document hierarchy, captions, citations, and surrounding content. |

## Taxonomy

Use families plus orthogonal tags. Report family-level scores, not only aggregate score.

### P0 Families

1. **Text, Hierarchy, And Reading Order**
   - Headings, paragraphs, nested lists, sidebars, footnotes, captions, headers/footers, multi-column flow.
   - Base requirement: if reading order or hierarchy fails, Markdown is not useful.

2. **Tables In Context**
   - Simple tables, multi-row headers, merged cells, blank carry-down cells, ditto marks, units, footnotes, totals, split/continued tables.
   - Highest-value failure family for business, finance, reports, statements, research, and policies.

3. **Forms And Key-Value Layouts**
   - Invoices, claims, applications, tax/government forms, receipts, statements, selected checkboxes, blank fields, signatures, stamps.
   - Tests layout semantics beyond flowing text.

4. **Figures, Charts, And Visual Facts**
   - Charts, dashboards, diagrams, images, figure captions, visual annotations, legends, data labels.
   - Doc2MD explicitly requires inline descriptions of non-text elements.

### P1 Families

5. **Slides, Brochures, Dashboards, And Non-Manhattan Layouts**
   - Pitch decks, strategy pages, brochures, marketing one-pagers, KPI dashboards.
   - Tests visual grouping, nonlinear reading order, callouts, icons, and layout hierarchy.

6. **Math, Code, Footnotes, Citations, And Special Formatting**
   - Technical docs, papers, textbooks, API docs, legal text, theorem/proof structure, formulas, code blocks.
   - Important, but should not dominate unless Doc2MD targets academic PDFs heavily.

7. **Mild Scan/OCR Robustness**
   - Light noise, skew, stamps, mild handwriting, redlines, rotated notes, camera-like artifacts.
   - Include a few cases, but do not let OCR difficulty swamp document reconstruction.

### P2 Stress Suites

Keep these outside Core initially:

- Heavy multilingual documents.
- Heavy handwriting.
- Extreme camera capture.
- Very long 50-200 page documents.
- Severe scan degradation.
- Highly adversarial PDF internals.

## Tags

Each document should have tags such as:

`born-digital`, `scan`, `photo`, `multi-column`, `nested-list`, `simple-table`, `complex-table`, `multi-page-table`, `form`, `checkbox`, `chart`, `figure`, `math`, `code`, `footnote`, `caption`, `slide`, `bilingual`, `handwriting-light`, `landscape`, `long-doc`, `redline`, `stamp`, `header-footer`, `watermark`.

## Doc2MD-Core-25

Target: 25 documents, 60-90 pages total. Most documents should be 1-6 pages. Include one 8-12 page document and one multi-page table case. Do not include 100-page documents in Core.

| ID | Case | Pages | Main Diagnostic Value |
| --- | --- | ---: | --- |
| D01 | Clean business memo or policy note | 2 | Headings, paragraphs, bold labels, lists, header/footer handling. |
| D02 | Technical/API documentation excerpt | 4-5 | Code blocks, inline code, callouts, links, numbered steps, small tables. |
| D03 | Academic paper excerpt | 5-6 | Two columns, abstract, hierarchy, equations, figure, references, footnotes. |
| D04 | Government/regulatory report section | 6-8 | Deep headings, footnotes, page numbers, boxed notices, appendices. |
| D05 | Legal contract or terms excerpt | 5-6 | Dense clauses, nested numbering, definitions, cross-references, signature block. |
| D06 | Invoice | 1 | Address blocks, invoice metadata, line-item table, totals, tax, payment terms. |
| D07 | Bank or credit-card statement | 2-3 | Repeated table headers, transaction rows, negative values, balances, dates. |
| D08 | Annual-report financial statement | 3-4 | Multi-level headers, units, footnotes, totals, indentation semantics. |
| D09 | Scientific complex table | 2 | Merged headers, symbols, units, citations, row groups. |
| D10 | Landscape/wide table page | 1 | Rotated/landscape reading order, many columns, table usability. |
| D11 | Multi-page table continuation | 4-5 | Continued table, repeated headers, continuation notes, footnotes after table. |
| D12 | Application form | 2 | Key-value fields, blanks, checkboxes/radio buttons, section labels. |
| D13 | Insurance/medical/lab-style form sample | 2 | Dense boxes, warnings, abbreviations, selected fields. Use deidentified/public samples only. |
| D14 | Tax/government form plus instructions | 3-4 | Line numbers, form fields, checkboxes, instruction text, tables. |
| D15 | Receipt or expense scan | 1 | Mild OCR noise, merchant/date/total, item rows, discounts/tax. |
| D16 | Short slide deck | 8 slides | Titles, bullets, icons, diagrams, chart slide, visible speaker-note-like text if present. |
| D17 | Marketing brochure or flyer | 2 | Non-Manhattan layout, callouts, columns, images, visual grouping. |
| D18 | Infographic or timeline | 1 | Icons, timeline order, large numerals, visual grouping, inline description. |
| D19 | Dashboard/business report page | 2 | KPI cards, multiple charts, legends, side notes, chart titles. |
| D20 | Single chart-heavy report page | 1 | Axis labels, legend, key values/trends, caption, numeric tolerance. |
| D21 | Scientific figure page | 2 | Multi-panel figure, caption, labels, in-text figure references. |
| D22 | Math lecture/textbook note | 3 | Theorem/proof structure, aligned equations, inline math, numbered equations. |
| D23 | Printed document with light handwriting | 2 | Typed text plus a few handwritten annotations, stamps, signatures. |
| D24 | Historical/newspaper scan | 1 | Multi-column OCR, mild degradation, headline hierarchy, captions. |
| D25 | Bilingual or non-English structured document | 2-3 | Headings plus table/form content outside English; global coverage probe without becoming multilingual OCR benchmark. |

### Public/Hidden Split

| Split | Size | Purpose |
| --- | ---: | --- |
| Public calibration | 5 documents | Full PDFs, gold Markdown, structured gold, scoring scripts, acceptable-output examples. Not used for leaderboard rank. |
| Hidden official | 20 documents | Leaderboard score. PDFs and gold kept private; models submit outputs or run through controlled harness. |
| Hidden refresh bank | 5-10 documents | Leakage checks, tie-breaks, annual/semiannual refresh. |

Suggested public calibration cases: D01, D08, D12, D18, D20. This gives examples across plain structure, tables, forms, visual layout, and chart reconstruction without revealing all difficult categories.

## Cases To Exclude From Core

Exclude cases that mostly measure something other than faithful document-to-Markdown reconstruction:

- Extreme camera photos, severe skew/warp, unreadable scans, CAPTCHA-like text.
- Heavy handwriting notebooks.
- Many near-duplicate invoices, receipts, or forms.
- Cropped-table-only, formula-only, chart-QA-only, or layout-box-only tasks.
- 50-200 page long documents in the initial suite.
- Documents whose gold answer is ambiguous without a policy.
- Synthetic gotchas that do not resemble real documents.

Headers, footers, page numbers, watermarks, logos, stamps, redactions, blank fields, and marginalia need explicit annotation policy.

## Gold Representation

Each document needs structured gold, not only gold Markdown.

| Gold Object | Required Fields |
| --- | --- |
| Blocks | `id`, `page`, `bbox`, `type`, `text`, `markdown`, `reading_order`, `parent_heading`, `style_attributes`. |
| Headings | Level, text, parent, section range. |
| Lists | Ordered/unordered, nesting, item text, continuation blocks. |
| Tables | Caption, placement anchor, canonical grid/HTML, rowspans/colspans, headers, units, footnotes, continuation metadata. |
| Forms | Field label, value, checkbox/radio state, blank/filled state, grouping. |
| Figures/charts | Placement anchor, caption, required description, verifiable fact tuples, prohibited unsupported claims. |
| Math/code | LaTeX, code text, language if visible, inline/block status. |
| Boilerplate policy | Preserve, omit, or optional for headers, footers, page numbers, watermarks, logos, repeated stamps. |

Allow multiple acceptable renderings. Complex tables may be valid as raw HTML inside Markdown when pipe tables cannot represent rowspans/colspans.

## Scoring Methodology

Do not use a single whole-output edit distance. Use a hybrid scorer:

- Markdown parsing.
- Block alignment.
- Element-level text metrics.
- Table-structure metrics.
- Visual fact checks.
- Form state checks.
- Hallucination and duplication penalties.
- Cost, latency, tokens, and failures tracked outside quality score.

### Normalization

Normalize before scoring:

- Unicode compatibility characters and ligatures.
- Hyphenation across line breaks.
- Repeated whitespace.
- Bullet, dash, and quote variants.
- Heading marker style.
- Table pipe spacing.
- Number formatting and thousands separators.
- Common OCR confusions only where appropriate.

Parse Markdown with a CommonMark-compatible parser. Parse Markdown pipe tables and HTML tables into canonical grids before table scoring.

### Alignment

Segment model output into blocks with a Markdown parser plus heuristics. Align predicted blocks to gold blocks using block type, normalized text similarity, page/order hints where available, and sequence constraints. Use LCS or Hungarian-style matching so duplicated/reordered blocks are penalized.

### Score Weights

Use a 100-point per-document score with applicable weights, then macro-average by family.

| Component | Weight | Notes |
| --- | ---: | --- |
| Text fidelity | 25 | Normalized similarity over aligned text blocks; omissions and duplications penalized. |
| Structure and reading order | 20 | Heading-tree F1, list nesting, block-order score, caption/footnote placement, section containment. |
| Tables | 20 | Table placement, caption association, structure, cell text, numeric tolerance, headers, continuation. |
| Forms and key-values | 10 | Label/value matching, checkbox/radio exactness, blank fields, signatures/stamps. |
| Figures, charts, and non-text visuals | 10 | Inline placement, caption preservation, required visual facts and numeric tolerances. |
| Math, code, and special formatting | 10 | Formula LaTeX, code blocks, inline code, superscripts/subscripts, citations, footnotes, meaningful emphasis. |
| Markdown validity and cleanliness | 5 | Parses cleanly, closed fences, renderable tables, no prompt chatter or JSON wrappers. |
| Hallucination penalty | up to -15 | Invented rows, values, captions, links, signatures, sections, or unsupported visual claims. |

Report overall macro score, family scores, and a family-minimum score.

### Visual Fact Scoring

Do not rely on open-ended LLM judging for visual descriptions. Score required fact tuples.

Example chart facts:

- `title = "Revenue by region"`
- `x_axis = ["Q1", "Q2", "Q3", "Q4"]`
- `y_axis = "Revenue ($M)"`
- `legend = ["North America", "Europe"]`
- `fact_1 = "North America is highest in Q4"`
- `fact_2 = "Europe increases from Q1 to Q4"`
- `value_tolerance = +/- 2% or +/- 1 tick interval`

The model gets credit for placing the visual description at the correct location and recovering required facts. Unsupported claims are penalized.

## Pareto Reporting And Repeats

For each model, report:

| Metric | Meaning |
| --- | --- |
| Doc2MD score | Overall macro score on hidden cases. |
| Family scores | Text/layout, tables, forms, visuals, special formatting, robustness. |
| Family minimum | Lowest family score. Prevents hiding catastrophic weakness. |
| Cost per document/page | API list price at evaluation date or normalized compute estimate. |
| Latency | Median and p95 wall-clock time per document. |
| Tokens | API-reported input/output tokens where available. |
| Output length | Markdown chars/tokens; catches verbosity and hallucination. |
| Failure rate | Timeouts, parser failures, refusals, truncated outputs. |
| Variance | Standard deviation or confidence interval across repeated runs. |

Run each model 3 times by default, even at temperature 0. Run 5 times for frontier models, close comparisons, or nondeterministic systems.

Primary score should be mean single-run performance. Also report median, best, worst, and bootstrap confidence intervals over documents and runs.

Pareto dominance: model A dominates model B only if A has equal or higher score and equal or lower cost/latency/tokens, with at least one strict improvement.

Separate frontier views:

- Full Doc2MD-Core.
- Text-heavy documents.
- Table-heavy documents.
- Visual/chart-heavy documents.
- Forms/enterprise documents.

## Benchmark Design Traps

Avoid these:

1. Using one gold Markdown string as the answer.
2. Over-indexing on OCR difficulty.
3. Table scoring without document context.
4. Open-ended visual judging.
5. Family imbalance.
6. Sparse unit tests that miss large omissions.
7. No hallucination or duplication penalty.
8. Ignoring cost, latency, tokens, and variance.
9. Ambiguous policies for boilerplate.
10. Too many public cases in a compact benchmark.

## Evidence From Current Experiments

The generated cases so far should be treated as exploratory evidence, not the final benchmark.

Useful findings:

- Normal raster table reconstruction is easy for Gemini and tractable for GPT, but GPT makes small substitutions (`Rift QA` -> `Ritt/Riff QA`).
- Spatial schedule/Gantt/rota grids are hard for both cheap models. The same facts rendered as a normal table are much easier, so the issue is visual-spatial normalization, not just OCR.
- Blank carry-down cells and ditto marks are strong realistic differentiators. Gemini expanded them perfectly; GPT preserved or misread shorthand.
- Merged cells reversed the usual ordering: GPT reconstructed one merged-cell table perfectly while Gemini made one ownership error.
- Explicit visual instructions and blank scaffolds did not force models to fill a normalized table from a spatial rota.
- Hidden/stale PDF metadata and overlay traps are real but should be used sparingly in Core to avoid turning the suite into PDF internals trivia.

These findings support grouped-table semantics and spatial schedule normalization as high-value families, but the official Core should balance them against reports, forms, slides, charts, technical documents, and mild OCR robustness.

## Near-Term Plan

1. Stop adding serial synthetic cases unless they answer a specific design question.
2. Keep `experiments/notes.md` as the exploration log.
3. Build `Doc2MD-Core-25` specs before generating more PDFs.
4. For each Core case, write a one-paragraph spec, expected gold object types, and scoring checklist before implementation.
5. Generate 5 public calibration cases first.
6. Validate scoring on one cheap model before running multiple models.
7. Add 20 hidden cases only after calibration cases prove the scoring shape is workable.
