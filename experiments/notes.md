# Doc2MD Experiment Notes

Scratchpad for case-by-case benchmark exploration. Keep this concise: what was tested, what broke, and whether the case seems benchmark-worthy.

## Pricing Assumptions

Using standard API pricing as of 2026-07-02:

- OpenAI `gpt-5.4-nano`: $0.20 / 1M input tokens, $1.25 / 1M output tokens.
- Google Vertex `gemini-3.1-flash-lite`: $0.25 / 1M input tokens, $1.50 / 1M output tokens.

## Case 001: Figure Trap

Purpose: stress inline non-text element reconstruction without making OCR the whole task.

Design:

- One born-digital PDF page.
- Surrounding paragraphs and bullets are extractable PDF text.
- Two embedded raster figures contain important information:
  - A flow diagram with exact stage labels and anchor code `VIS-37B`.
  - A line chart with quarter/value pairs and threshold note.

Hypothesis:

- Gemini should be stronger at describing the embedded figures.
- GPT nano may preserve surrounding text but omit or underspecify visual details.

Result, first run:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000627 | 2.75s | 600 in / 318 out |
| `gpt-5.4-nano` | 82.8% | $0.000727 | 7.94s | 1139 in / 399 out |

Useful failures:

- GPT misread visual anchor `VIS-37B` as `VIS-3TB`.
- GPT hallucinated the interpretation cue as `Q1 crosses the review threshold`; the chart says Q4 crosses it.
- Gemini reconstructed all required facts and was cheaper/faster on this case.

Assessment:

- Good first differentiator for image/figure description.
- Too easy for Gemini; next case should make visual structure denser or require ordering across several small visual elements.

## Case 002: Inspection Matrix

Purpose: test a compact embedded screenshot/table with similar row labels (`A-17` vs `A-71`, `Alpha valve` vs `Alpha value`) and row-attached metadata.

Result, first run:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 100.0% | $0.000654 | 8.03s | 1124 in / 343 out |
| `gemini-3.1-flash-lite` | 100.0% | $0.000669 | 3.02s | 600 in / 346 out |

Findings:

- Both models reconstructed the embedded matrix correctly.
- This is not an accuracy differentiator at current difficulty.
- It is still useful for Pareto-frontier reporting: Gemini was much faster and used fewer input tokens; OpenAI was marginally cheaper here because its output price table is lower.

Next stress direction:

- Make the visual element denser with more small labels and require a selected subset of marked cells, not full transcription of an obvious table.

## Case 003: Visual Grid

Purpose: stress dense visual labels and selective markings. Surrounding extractable text lists the marked cell IDs and path IDs, but the per-cell codes are only inside the embedded visual grid.

Result, first run:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 100.0% | $0.000963 | 8.98s | 1140 in / 588 out |
| `gemini-3.1-flash-lite` | 26.3% | $0.000989 | 3.66s | 600 in / 559 out |

Useful failures:

- Gemini correctly identified which cells were red-bordered and which cells were in the blue path.
- Gemini did not extract the per-cell codes (`ZN-104`, `MX-219`, etc.), which were only present inside the visual grid.
- OpenAI extracted the required marked-cell codes and path codes, but also made minor errors on unscored, unimportant non-marked cells (`C03`, `C26`, `C28`). This suggests scoring should focus on benchmark-relevant fields rather than rewarding full-grid verbosity.

Assessment:

- Strong differentiator. This is the best case so far.
- Realistic enough: dashboard/grid screenshots with important marked cells are common document content.
- Keep this style, but vary density and marking types to avoid overfitting to one grid pattern.

## Current Aggregate

Across the first three tiny exploratory cases:

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 94.3% | $0.002343 | 24.95s | 4733 |
| `gemini-3.1-flash-lite` | 75.4% | $0.002285 | 9.43s | 3023 |

Interpretation:

- Gemini is consistently faster and uses fewer input tokens in this harness.
- OpenAI currently wins aggregate accuracy because Case 003 exposes a Gemini weakness on dense visual-grid code extraction.
- Case 001 favors Gemini, Case 002 saturates, Case 003 favors OpenAI.
- This is enough evidence to keep exploring visual selective-reconstruction cases instead of plain text extraction.

## Case 004: Claims Form

Purpose: test realistic form/screenshot reconstruction: checked boxes, unchecked boxes, selected radio decision, field/value binding, reviewer note, and stamp text.

Result, first run after scorer cleanup:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000642 | 3.14s | 600 in / 328 out |
| `gpt-5.4-nano` | 97.6% | $0.000616 | 7.62s | 1097 in / 317 out |

Useful failures:

- GPT reconstructed all checkbox/radio state correctly but misread Provider NPI `NPI-4410-77` as `NPI-P4410-77`.
- Gemini reconstructed all checked/unchecked states and fields correctly.

Assessment:

- Mostly saturated; useful for cost/latency frontier, not a strong accuracy differentiator.
- Form-state scoring needs explicit negative checks because unchecked options are part of the record.

## Current Aggregate After 4 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 95.1% | $0.002959 | 32.57s | 6147 |
| `gemini-3.1-flash-lite` | 81.6% | $0.002927 | 12.57s | 3951 |

Interpretation:

- Gemini remains much faster and more token-efficient.
- Overall cost is nearly tied at this scale.
- Accuracy separation is still mostly driven by Case 003, so the next useful experiments should create variants of dense visual selective extraction rather than more ordinary forms.

## Case 005: Capacity Dashboard

Purpose: test exact reconstruction from a multi-series chart: legend, ordered series values, alert box, lowest-value callout, monthly totals, and a note about which series leads.

Result, first run after scorer cleanup:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 100.0% | $0.000550 | 6.07s | 1089 in / 266 out |
| `gemini-3.1-flash-lite` | 100.0% | $0.000555 | 2.83s | 600 in / 270 out |

Findings:

- Both models reconstructed all series values, totals, alert, and note correctly.
- Initial scorer was too strict because it expected every value to be paired directly with month labels; both models used ordered Jan-Apr series descriptions, which is faithful.
- This case is not an accuracy differentiator. It is useful evidence that ordinary clean multi-series charts are too easy.

Assessment:

- Saturated. Do not spend more time on clean chart cases.
- To make charts useful, try denser dashboards with small multiples, overlapping labels, tiny legends, or selective extraction from only highlighted points.

## Current Aggregate After 5 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 96.1% | $0.003509 | 38.64s | 7502 |
| `gemini-3.1-flash-lite` | 85.3% | $0.003482 | 15.40s | 4821 |

Interpretation:

- Gemini remains about 2.5x faster and uses far fewer input tokens.
- Total cost remains effectively tied at this tiny scale.
- Accuracy separation still comes mostly from Case 003. The strongest benchmark direction remains dense visual selective extraction with small codes/labels.

## Case 006: Aging Heatmap

Purpose: test dense table reconstruction plus marker-state fidelity. The source image is a receivables aging heatmap; the faithful target is the full table with red-corner flagged cells explicitly marked.

Result after retargeting scorer from "flagged only" to full-table + flag-state fidelity:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 88.5% | $0.001053 | 3.35s | 600 in / 602 out |
| `gpt-5.4-nano` | 53.8% | $0.001014 | 8.93s | 1088 in / 637 out |

Useful failures:

- GPT reconstructed most rows but misread Acme North `INV-152` as `INV-162`.
- GPT failed to preserve the red-corner flag state for the actual flagged cells.
- Gemini reconstructed every row correctly and marked all true flagged cells.
- Gemini added false-positive flag emphasis to some unflagged cells (`INV-166`, `INV-360`, `INV-462`).

Assessment:

- Strong Doc2MD-style differentiator after retargeting.
- Better than "flagged only" scoring because faithful reconstruction can include the whole table.
- Keep this direction: dense tables where visual marker state must be preserved, with penalties for both missed markers and false-positive markers.

## Current Aggregate After 6 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 89.0% | $0.004523 | 47.56s | 9227 |
| `gemini-3.1-flash-lite` | 85.8% | $0.004535 | 18.75s | 6023 |

Interpretation:

- Gemini remains much faster and token-lighter.
- Cost is effectively tied after six exploratory cases.
- Accuracy is now close overall, but the cases reveal different weaknesses: GPT struggles more with visual marker state and occasional small-code OCR; Gemini can over-mark false positives in dense visual tables and failed the dense code grid in Case 003.

## Case 007: Dependency Map

Purpose: test visual topology reconstruction: near-duplicate node codes, selected green path, blocked red-diamond nodes, dashed fallback-only edge, and non-selected dependencies.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000714 | 3.54s | 600 in / 376 out |
| `gpt-5.4-nano` | 91.7% | $0.000734 | 8.05s | 1108 in / 410 out |

Useful failures:

- GPT preserved all node codes and the selected path.
- GPT incorrectly stated `VAL-0B8` was blocked in one diagram-detail sentence, while later also saying the blocked nodes were `VAL-08B` and `HOLD-22`.
- GPT also implied `MAP-731` had blocked/selected edge state; scorer treated this as a false-positive blocked-state issue.
- Gemini reconstructed the selected path, blocked nodes, dashed fallback edge, and near-duplicate codes correctly.

Assessment:

- Moderate differentiator and very Doc2MD-relevant.
- Visual topology with near-duplicate codes is worth keeping, but this specific case may be slightly too easy because the action line repeats the selected path and blocked nodes. A harder variant should hide the selected path summary and require all topology from the image.

## Current Aggregate After 7 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 89.4% | $0.005257 | 55.61s | 10745 |
| `gemini-3.1-flash-lite` | 87.8% | $0.005249 | 22.29s | 6999 |

Interpretation:

- Aggregate accuracy is close, but failure modes differ by visual task type.
- Gemini remains much faster and more token-efficient.
- Best benchmark directions so far: dense visual grids with small codes, dense tables with marker-state fidelity, and dependency diagrams with near-duplicate labels/topology.

## Case 008: Routing Diagram

Purpose: harder version of Case 007. The selected route is not repeated in the surrounding PDF text; models must recover it from green arrows in the image. Also tests blocked nodes, dashed fallback-only edges, and near-duplicate codes.

Result after scorer cleanup:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 88.5% | $0.000615 | 2.72s | 600 in / 310 out |
| `gpt-5.4-nano` | 82.0% | $0.000656 | 6.39s | 1091 in / 350 out |

Useful failures:

- Both models preserved node labels, fallback-only edges, and near-duplicate code warnings.
- Neither model explicitly reconstructed the selected route `SRC-01 -> AUTH-7A -> PACK-L3 -> QA-02 -> REL-5`.
- GPT also missed the blocked state for `AUTH-A7`; it only clearly marked `QA-20` as blocked.
- Gemini correctly captured both blocked nodes and fallback edges, but still omitted the selected route.

Assessment:

- Stronger and cleaner than Case 007 because path details do not leak in the body/action text.
- Very Doc2MD-relevant: diagrams often require preserving topology, not just listing visible labels.
- Next variant should remove the legend text summary too, leaving only visual arrow styles, or require a markdown edge list for every edge with state.

## Current Aggregate After 8 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 88.5% | $0.005913 | 62.00s | 12186 |
| `gemini-3.1-flash-lite` | 87.9% | $0.005864 | 25.01s | 7909 |

Interpretation:

- Aggregate accuracy is now nearly tied.
- Gemini is still much faster and uses fewer tokens.
- The best differentiators are no-leak visual topology, dense marker-state tables, and dense small-code visual grids.

## Case 009: Routing Diagram Without Legend

Purpose: stricter follow-up to Case 008. The source keeps the same near-duplicate topology, selected green route, blocked red-diamond nodes, and dashed fallback-only edges, but removes the in-figure legend/summary text. The PDF text still says to use the selected route, but does not reveal the route or fallback edges.

Result after scorer cleanup:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 83.1% | $0.000536 | 6.07s | 1092 in / 254 out |
| `gemini-3.1-flash-lite` | 60.6% | $0.000444 | 2.33s | 600 in / 196 out |

Useful failures:

- GPT reconstructed the selected route `SRC-01 -> AUTH-7A -> PACK-L3 -> QA-02 -> REL-5` and both blocked nodes.
- GPT missed the `PACK-3L` node and did not name the `PACK-3L -> QA-02` fallback-only edge.
- Gemini preserved all node labels and both blocked nodes.
- Gemini did not explicitly reconstruct the selected route, missed both exact fallback-only edges, and incorrectly said `PACK-3L` was blocked.

Assessment:

- Strong Doc2MD differentiator. Removing the legend exposes a real gap in visual topology reconstruction.
- This supports making diagram cases require explicit Markdown edge lists with edge state, not just prose descriptions.
- The benchmark should include no-leak diagrams where the only source of topology state is the visual styling.

## Current Aggregate After 9 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 87.9% | $0.006449 | 68.08s | 13532 |
| `gemini-3.1-flash-lite` | 84.9% | $0.006308 | 27.35s | 8705 |

Interpretation:

- GPT now has the higher aggregate accuracy because it handled no-legend route topology better.
- Gemini remains about 2.5x faster and uses substantially fewer tokens.
- The benchmark is starting to find non-saturated areas: dense visual grids, marker-state tables, and diagram topology without textual leakage.

## Case 010: Scrambled Stream Order

Purpose: test whether models preserve visible reading order for extractable PDF text when the PDF content stream is deliberately out of visual order. The rendered table shows rows 1 through 8, but `pypdf` extracts row codes as `E-118, B-219, H-906, A-104, F-604, C-033, G-441, D-772`.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000660 | 3.11s | 600 in / 340 out |
| `gpt-5.4-nano` | 55.0% | $0.000435 | 5.20s | 300 in / 300 out |

Useful failures:

- GPT preserved all row contents but output the exact scrambled extraction order: 5, 2, 8, 1, 6, 3, 7, 4.
- Gemini reconstructed the visible table order perfectly: 1 through 8.
- This suggests GPT's PDF path may be leaning heavily on extracted text order for this kind of vector-text PDF, while Gemini appears more layout-aware on this case.

Assessment:

- Excellent benchmark direction. It is not OCR, it is realistic PDF structure pathology.
- This tests the core Doc2MD requirement: reconstruct the original reading experience, not just dump text tokens.
- Add more variants later: multi-column articles, footnotes, sidebars, and tables with shuffled cell draw order.

## Current Aggregate After 10 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 86.4% | $0.006968 | 30.45s | 9645 |
| `gpt-5.4-nano` | 84.6% | $0.006884 | 73.27s | 14132 |

Interpretation:

- Gemini retakes the aggregate lead because Case 010 exposed a major reading-order failure in GPT.
- GPT was cheaper on this single case because OpenAI counted far fewer input tokens, but it failed the key requirement.
- Strongest benchmark candidates now: scrambled PDF content order, no-leak visual topology, dense visual grids, and marker-state tables.

## Case 011: Two-Column Stream Order

Purpose: realistic follow-up to Case 010. The page is a two-column operations memo with a sidebar and footnote. Visually, the main memo reads `S1-S4` in the left column, then `S5-S8` in the right column. The PDF content stream is deliberately drawn as `S5-S8`, sidebar, footnote, then `S1-S4`.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000645 | 2.85s | 600 in / 330 out |
| `gpt-5.4-nano` | 56.1% | $0.000446 | 5.57s | 394 in / 294 out |

Useful failures:

- GPT preserved the text but output the content stream order: `S5-S8`, sidebar, footnote, then `S1-S4`.
- Gemini reconstructed the visible reading order: `S1-S8`, then sidebar, then footnote.
- This confirms Case 010 was not only a table artifact; it generalizes to a common two-column document layout.

Assessment:

- Excellent benchmark direction. Real PDFs often have content streams that do not match reader order.
- This should become a core Doc2MD axis: layout reading order for extractable vector text.
- Later variants: multi-column newsletter, footnotes anchored mid-column, marginal callouts, and a table split across columns.

## Current Aggregate After 11 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 87.6% | $0.007613 | 33.30s | 10575 |
| `gpt-5.4-nano` | 82.0% | $0.007330 | 78.85s | 14820 |

Interpretation:

- Gemini is now clearly ahead on aggregate accuracy, mainly due to layout-order cases and some visual cases.
- GPT remains slightly cheaper in total dollars here, but its wrong-order outputs are not faithful Doc2MD conversions.
- The current strongest non-saturated axis is extractable-PDF layout order, followed by no-leak diagram topology and dense marker-state visuals.

## Case 012: Redline Strikethrough

Purpose: test whether models preserve visible edit state when extractable PDF text contains both deleted and replacement values, but only the visual strike-through indicates deletion. The page is a contract revision sheet with five old values struck through and five replacement values shown inline.

Result after scorer cleanup:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 100.0% | $0.000256 | 7.26s | 232 in / 168 out |
| `gemini-3.1-flash-lite` | 100.0% | $0.000432 | 2.24s | 600 in / 188 out |

Useful findings:

- Both models preserved deleted values as Markdown strikethrough and kept replacement values inline.
- GPT used tight Markdown syntax like `~~$12,400~~`; Gemini used spaced syntax like `~~ $12,400 ~~`.
- This case is saturated for the two cheap models, but still useful as a sanity case for redline formatting.

Assessment:

- Not a strong differentiator in this clean form.
- A harder follow-up would need denser redlines, overlapping handwritten-style annotations, conflicting margin comments, or replacements without explanatory body text.
- Keep redline state as a possible benchmark category, but do not over-invest until harder variants break at least one model.

## Current Aggregate After 12 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 88.7% | $0.008045 | 35.55s | 11363 |
| `gpt-5.4-nano` | 83.5% | $0.007586 | 86.10s | 15220 |

Interpretation:

- Case 012 did not change the qualitative picture because both models saturated it.
- GPT was cheaper on this simple redline page, but slower.
- Best axes remain extractable-PDF layout order, no-leak diagram topology, dense visual grids, and marker-state tables.

## Case 013: Hidden Text Layer

Purpose: test whether models reconstruct the visible document rather than a conflicting invisible/OCR-like text layer. The rendered page shows one remittance table, while `pypdf` extracts both the visible values and hidden white-text values: `INV-HID-999`, `$1,111.11`, `PAY-00X`, `South-99`, `Noor Iqbal`, and `Use hidden values`.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000350 | 2.05s | 600 in / 133 out |
| `gpt-5.4-nano` | 51.6% | $0.000276 | 5.08s | 232 in / 184 out |

Useful failures:

- GPT reconstructed the visible table correctly, but then added a second table containing every invisible conflicting value.
- Gemini reconstructed only the visible table and ignored the hidden layer.
- This is similar to the layout-order failures: GPT appears to rely heavily on extracted PDF text even when it contradicts the visual document.

Assessment:

- Strong Doc2MD benchmark direction. It is not OCR; it tests bad OCR/text layers in PDFs.
- Very realistic for documents with stale OCR overlays, hidden accessibility text, or machine-generated text layers.
- Add harder variants later: hidden text partially overlapping visible text, old OCR layer under scanned pages, hidden table cells, and hidden instructions that conflict with visible action text.

## Current Aggregate After 13 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 89.5% | $0.008394 | 37.60s | 12096 |
| `gpt-5.4-nano` | 81.1% | $0.007863 | 91.18s | 15636 |

Interpretation:

- Gemini pulls further ahead because it handled the hidden-layer and layout-order cases correctly.
- GPT is slightly cheaper in total dollars, but the hidden-layer output is materially unfaithful.
- Best axes now: extractable-PDF layout order, hidden/OCR text layer mismatch, no-leak diagram topology, dense visual grids, and marker-state tables.

## Case 014: Redaction Overlay

Purpose: test whether models preserve visible redaction bars instead of leaking selectable text underneath. The PDF renders black bars for SSN, account token, and access code, but `pypdf` extracts the covered strings: `482-19-7742`, `tok_live_8JQ4`, and `RAVEN-91`.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000357 | 2.23s | 600 in / 138 out |
| `gpt-5.4-nano` | 25.0% | $0.000213 | 4.91s | 208 in / 137 out |

Useful failures:

- GPT leaked all three covered values directly in the Markdown table.
- GPT also failed to represent the sensitive rows as redacted.
- Gemini output `[Redacted]` for all three covered fields and preserved the visible non-sensitive fields.

Assessment:

- Very strong benchmark direction. It is realistic, objective, cheap, and exposes a severe fidelity failure.
- This belongs with hidden text layer mismatch as a core axis: visible page must win over extracted text.
- Later variants: partial redactions, redacted table cells mixed with unredacted cells, redacted signatures, and black bars over multi-line paragraphs.

## Current Aggregate After 14 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 90.3% | $0.008751 | 39.83s | 12834 |
| `gpt-5.4-nano` | 77.0% | $0.008076 | 96.09s | 15981 |

Interpretation:

- Gemini is now clearly superior on fidelity despite slightly higher total cost in this exploratory set.
- GPT's extraction-heavy behavior is especially bad on redactions, hidden text layers, and layout order.
- Current initial-benchmark shortlist: redaction overlays, hidden/OCR text layer mismatch, extractable-PDF layout order, no-leak diagram topology, dense visual grids, and marker-state tables.

## Case 015: Correction Overlay

Purpose: test whether models preserve the final visible correction layer when stale text remains underneath white patches. The rendered page shows corrected values only; `pypdf` extracts stale values first (`$2,410.00`, `2026-07-01`, `Q-SOUTH-2`, `Noor Iqbal`) and corrected values later.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000339 | 2.08s | 600 in / 126 out |
| `gpt-5.4-nano` | 52.5% | $0.000232 | 4.79s | 215 in / 151 out |

Useful failures:

- GPT emitted the stale covered values as the main field values, then added corrected values as orphan rows.
- Gemini reconstructed only the final visible corrected table.
- This confirms the visible-layer-vs-extracted-text issue is not limited to redactions or hidden OCR text.

Assessment:

- Strong benchmark direction. Common in edited PDFs and generated business documents.
- Should be grouped with redaction overlays and hidden text layers under a broader "visible final state vs stale PDF layer" axis.
- Later variants: multiline corrections, corrected table cells with partial old text still visible, and overlapping white patches that leave fragments.

## Current Aggregate After 15 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 90.9% | $0.009090 | 41.90s | 13560 |
| `gpt-5.4-nano` | 75.4% | $0.008307 | 100.88s | 16347 |

Interpretation:

- Gemini keeps widening the fidelity lead, mostly on cases where visible final state conflicts with extractable PDF text.
- GPT remains slightly cheaper but repeatedly returns unfaithful stale/hidden text.
- Best current benchmark axes: visible final state vs stale PDF layer, extractable-PDF layout order, no-leak diagram topology, dense visual grids, and marker-state tables.

## Case 016: Bad OCR Overlay

Purpose: scanned-PDF variant of the visible-state problem. The visible raster scan contains authoritative values (`BDG-47K`, `18.6 mSv`, `QA-7`, `SPL-204`, `Cleared`), while the invisible OCR layer contains conflicting values (`BDG-74X`, `81.9 mSv`, `QA-1`, `SPL-240`, `Quarantined`).

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000396 | 2.28s | 600 in / 164 out |
| `gpt-5.4-nano` | 50.0% | $0.000568 | 5.74s | 1132 in / 273 out |

Useful failures:

- GPT reconstructed the visible scan correctly, but then appended the bad OCR layer values.
- Gemini reconstructed only the visible scan values.
- This confirms the stale-layer issue also applies when the correct content is rasterized and the conflicting content is machine text.

Assessment:

- Strong benchmark direction for real scanned PDFs with bad OCR overlays.
- This is not a pure OCR benchmark because the issue is conflict resolution between visible scan and OCR layer.
- Later variants: noisier scans, skewed scans, bad OCR with partial overlap, and multi-page scanned packets.

## Current Aggregate After 16 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 91.5% | $0.009486 | 44.18s | 14324 |
| `gpt-5.4-nano` | 73.8% | $0.008875 | 106.62s | 17752 |

Interpretation:

- Gemini is now far ahead on fidelity and still much faster.
- GPT's repeated failure mode is clear: it often includes extracted hidden/stale/OCR text even when the visible document contradicts it.
- Best current benchmark axis: visible final state vs stale PDF layer, including hidden text, redaction overlays, correction overlays, and bad OCR overlays.

## Case 017: Rotated Margin Notes

Purpose: test whether models preserve visible rotated and marginal text: a left vertical side note, a right vertical margin ID, and a diagonal stamp.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 100.0% | $0.000260 | 5.19s | 248 in / 168 out |
| `gemini-3.1-flash-lite` | 100.0% | $0.000480 | 2.53s | 600 in / 220 out |

Useful findings:

- Both models preserved all rotated annotations: `HOLD LOT H-77 UNTIL QC-4 SIGNS`, `ROT-51B`, and `AFTER 16:30 USE BAY DELTA`.
- Raw text extraction also included the rotated annotations cleanly, so this vector-text form is not a strong trap.
- Gemini described the orientations more faithfully; GPT preserved the text but not the visual orientation.

Assessment:

- Saturated in this form. Keep as a sanity case only.
- A harder follow-up would need rasterized rotated notes, low contrast stamps, overlapping marginalia, or handwritten-style annotations.

## Current Aggregate After 17 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 92.0% | $0.009966 | 46.71s | 15144 |
| `gpt-5.4-nano` | 75.4% | $0.009135 | 111.81s | 18168 |

Interpretation:

- Case 017 is not a differentiator.
- The benchmark should prioritize conflict cases where visible document state disagrees with extractable text, plus selected visual topology and marker-state cases.

## Case 018: Raster Callout Card

Purpose: test whether models preserve image-only visible callouts embedded inside a raster inspection card. Plain PDF extraction contains only the shell text, not the card values or callouts.

Result after scorer cleanup:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 100.0% | $0.000488 | 6.16s | 1083 in / 217 out |
| `gemini-3.1-flash-lite` | 100.0% | $0.000512 | 2.75s | 600 in / 241 out |

Useful findings:

- Both models reconstructed the base card values: `PAL-204`, `Cold-3`, `Iris Shah`, and `SL-88Q`.
- Both preserved the callouts: `DO NOT SHIP`, `hold pending retest`, `RETEST BAY C`, `TEMP CAP 4C`, and `INSPECTOR N-17`.
- Gemini described spatial/callout relationships more explicitly, but both were faithful enough.

Assessment:

- Saturated in this clean, high-contrast form.
- Image-only callouts are still relevant, but need harder variants: denser labels, lower contrast, overlapping arrows, smaller text, or ambiguous callout ownership.

## Current Aggregate After 18 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 92.4% | $0.010478 | 49.46s | 15985 |
| `gpt-5.4-nano` | 76.7% | $0.009622 | 117.96s | 19468 |

Interpretation:

- Clean raster callouts do not differentiate the models.
- The strongest benchmark direction remains visible final state vs stale/extractable PDF layer.
- Visual-only tasks need to be denser or more ambiguous to avoid saturation.

## Case 019: Dense Raster Callout Association

Purpose: test image-only callout ownership with near-duplicate equipment IDs. The PDF text layer contains only the shell text; the equipment IDs, callout labels, and arrow ownership are raster-only.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 100.0% | $0.000500 | 5.95s | 1086 in / 226 out |
| `gemini-3.1-flash-lite` | 100.0% | $0.000460 | 2.80s | 600 in / 207 out |

Useful findings:

- Both models correctly attached `LEAK TRACE` to `VLV-104`, `LOCK OUT` to `PUMP-22`, `OK TO RUN` to `FAN-7`, and `SENSOR DRIFT` to `TANK-3`.
- Both preserved the near-duplicate untagged IDs: `VLV-140`, `PUMP-2Z`, `FAN-1`, and `TANK-8`.
- This confirms that clean high-contrast raster callout association is still too easy, even when ownership is arrow-based.

Assessment:

- Saturated. Do not add more clean visual-callout cases at this difficulty.
- Harder visual-only variants need clutter, small text, intersecting arrows, low contrast, partial occlusion, multi-page references, or require cross-checking a figure against surrounding instructions.
- The best current benchmark axes remain visible final state vs stale/extractable PDF layer, extractable-PDF layout order, dense visual grids, marker-state tables, and no-leak topology.

## Current Aggregate After 19 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 92.8% | $0.010938 | 52.26s | 16792 |
| `gpt-5.4-nano` | 78.0% | $0.010122 | 123.91s | 20780 |

Interpretation:

- Case 019 did not change the main story: both models handle clean raster callouts, but Gemini remains far stronger overall because GPT repeatedly fails visible-vs-hidden text conflicts.
- Gemini is still much faster and uses fewer tokens; GPT is slightly cheaper in total dollars across these 19 tiny probes.

## Case 020: AcroForm Filled Widgets

Purpose: test a realistic filled-form PDF. Static labels are extractable, but the entered text values are rasterized inside form boxes and do not appear in page text extraction. Radio/checkbox states are visible widgets.

Result after scorer cleanup:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000519 | 3.15s | 600 in / 246 out |
| `gpt-5.4-nano` | 79.5% | $0.000510 | 6.36s | 1177 in / 220 out |

Useful failures:

- GPT recovered the rasterized text field values (`VEN-4092-Q`, `Northstar Reagents LLC`, `RT-072-441`, `ACCT-8831`, `Ops-7A`, `MR`).
- GPT incorrectly marked `C-Corp` as selected in the visible form section, then contradicted itself by appending `[FORM FIELD] tax_class: LLC`.
- GPT did not explicitly preserve the checked state for `Expedite review` or the unchecked state for `W-9 received`.
- Gemini reconstructed the filled values and states faithfully using a compact Markdown table with `[x]` and `[ ]`.

Assessment:

- Good moderate differentiator. Filled form/state reconstruction is realistic and objective.
- This belongs near marker-state cases: selection state is part of the document record, not a decorative detail.
- Harder variants could mix disabled fields, crossed-out stale values, dropdowns, multi-page forms, or ambiguous checkbox alignment.

## Current Aggregate After 20 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 93.2% | $0.011457 | 55.42s | 17638 |
| `gpt-5.4-nano` | 78.0% | $0.010633 | 130.27s | 22177 |

Interpretation:

- Case 020 reinforces that form/widget state is a useful benchmark axis.
- Gemini remains the clear fidelity leader while also using fewer tokens and roughly half the latency.
- GPT is still slightly cheaper in total dollars, but the quality gap is driven by concrete fidelity failures rather than subjective formatting.

## Case 021: CropBox Hidden Margin

Purpose: test whether models follow the rendered page boundaries. The visible PDF page shows only a dispatch table, but the PDF content stream contains decoy text far outside the MediaBox/CropBox. `pypdf` extracts the decoys; the rendered page does not show them.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000376 | 2.28s | 620 in / 147 out |
| `gpt-5.4-nano` | 43.7% | $0.000403 | 6.49s | 327 in / 270 out |

Useful failures:

- GPT reconstructed the visible dispatch table correctly.
- GPT also leaked every cropped-away decoy: `Z21-CROPPED-DECOY`, `SHP-9999`, `Mirage Logistics`, `$9,999.99`, and `Use cropped margin values`.
- Gemini reconstructed only the rendered page content and did not include the decoys.

Assessment:

- Very strong benchmark direction. It is realistic for cropped/scanned/print-prep PDFs and cleanly tests visible page fidelity versus raw content extraction.
- This belongs in the same family as hidden text, redaction overlays, correction overlays, and bad OCR overlays: rendered visible state must win over extractable stale/hidden content.

## Current Aggregate After 21 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 93.5% | $0.011833 | 57.70s | 18405 |
| `gpt-5.4-nano` | 76.4% | $0.011035 | 136.76s | 22774 |

Interpretation:

- Crop/off-page hidden content is one of the strongest axes so far.
- GPT's repeated failure mode is now very clear: it often trusts extractable PDF content even when the rendered page contradicts or excludes it.
- Gemini remains faster, lower-token, and much more faithful, while GPT remains only slightly cheaper in total dollars.

## Case 022: Clipping Mask Hidden Text

Purpose: test whether models respect PDF clipping masks. The visible page shows an authorization table, but the content stream contains a conflicting hidden block drawn outside the active clipping area. `pypdf` extracts the hidden block; the rendered page does not show it.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000345 | 2.44s | 600 in / 130 out |
| `gpt-5.4-nano` | 43.7% | $0.000251 | 7.39s | 230 in / 164 out |

Useful failures:

- GPT reconstructed the visible authorization table correctly.
- GPT also leaked the clipped hidden block wholesale: `REQ-0000`, `Tariq Noor`, `$99,000.00`, `West-9`, and `Use clipped values`.
- Gemini reconstructed only the visible page.

Assessment:

- Very strong benchmark direction, like Case 021 but using clipping rather than page boxes.
- This confirms the broader axis: rendered visibility semantics matter, not just text extraction.
- The annotation/free-text path was briefly explored but rejected because annotation text did not render reliably with the local generator.

## Current Aggregate After 22 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 93.8% | $0.012178 | 60.13s | 19135 |
| `gpt-5.4-nano` | 74.9% | $0.011286 | 144.15s | 23168 |

Interpretation:

- Clipping masks join crop boxes, hidden text layers, bad OCR overlays, redactions, and correction overlays as core visibility-semantics cases.
- GPT is now consistently failing by including raw extractable content that is not visible in the rendered document.
- Gemini remains the better fidelity/cost-latency frontier despite a slightly higher total dollar cost in this small run.

## Case 023: Raster Correction Markup

Purpose: test raster-only red pen correction markup: struck-through cells, arrows, replacement callouts, and near-duplicate PO rows. The PDF text layer only contains shell text; all table values and corrections are image-only.

Result after scorer cleanup:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 73.5% | $0.000696 | 2.88s | 600 in / 364 out |
| `gpt-5.4-nano` | 44.1% | $0.000477 | 5.23s | 1083 in / 208 out |

Useful failures:

- GPT produced a generic image summary and did not faithfully reconstruct most table rows or tie corrections to the affected PO rows.
- Gemini reconstructed most rows and the `PO-181` corrections, but misread printed `PO-181` amount `$3,300.00` as `$5,030.00`.
- Gemini also misassigned the `RELEASE - KL` correction to `PO-271` instead of `PO-217`.

Assessment:

- Useful visual-markup differentiator, but less clean than visibility-semantics traps because interpretation of arrows/corrections can be visually ambiguous.
- Worth keeping as a realistic scanned-paperwork axis if the final benchmark includes a small visual markup section.
- A cleaner follow-up should make the correction arrows less visually close to neighboring rows while keeping the table image-only.

## Current Aggregate After 23 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 92.9% | $0.012874 | 63.01s | 20099 |
| `gpt-5.4-nano` | 73.6% | $0.011763 | 149.38s | 24459 |

Interpretation:

- Gemini remains ahead on fidelity and latency, though this case shows even Gemini can fail on visual correction ownership.
- GPT's image-only reconstruction remains shallow compared with Gemini on table/details.
- Strongest current axes: rendered visibility semantics, filled form/widget state, dense visual grids/marker states, and selected visual topology/correction ownership.

## Case 024: Invisible Text Render Mode

Purpose: test PDF text rendering mode 3. The visible invoice is normal, but a conflicting hidden invoice block is present in the content stream using invisible text rendering mode. `pypdf` extracts the hidden block; the rendered page does not show it.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000359 | 2.29s | 600 in / 139 out |
| `gpt-5.4-nano` | 43.7% | $0.000252 | 5.96s | 234 in / 164 out |

Useful failures:

- GPT reconstructed the visible invoice correctly.
- GPT also leaked the invisible render-mode block: `INV-0000`, `Ghost Holdings`, `$88,888.88`, `2026-01-01`, and `Use invisible values`.
- Gemini reconstructed only the visible invoice.

Assessment:

- Very strong benchmark direction. It is another cheap, objective visibility-semantics trap.
- Initial alpha-zero transparency attempt was rejected because Poppler still rendered the supposedly transparent text; render mode 3 produced the intended behavior.

## Current Aggregate After 24 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 93.2% | $0.013232 | 65.30s | 20838 |
| `gpt-5.4-nano` | 72.3% | $0.012015 | 155.34s | 24857 |

Interpretation:

- Visibility-semantics cases are the clearest and most objective benchmark core so far.
- GPT repeatedly includes non-visible extractable text; Gemini consistently respects the rendered page on these cases.
- GPT remains slightly cheaper in total dollars, but much slower and substantially less faithful.

## Case 025: Multi-Page Raster Cross Reference

Purpose: test whether models preserve two related raster-only pages: a batch matrix on page 1 and a marker legend on page 2. The PDF text layer contains only shell text and cross-page instructions; lot rows and marker meanings are image-only.

Result after correcting scorer target:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000916 | 3.40s | 1120 in / 424 out |
| `gpt-5.4-nano` | 100.0% | $0.001019 | 7.39s | 2074 in / 483 out |

Findings:

- Both models reconstructed the page 1 matrix and page 2 legend correctly.
- Both preserved the instruction to combine/resolve markers, but neither generated a derived combined-resolution table.
- That is correct for Doc2MD: the benchmark should score faithful reconstruction, not extra inference unless the source document visibly contains that derived table.

Assessment:

- Saturated under the proper Doc2MD target.
- Useful as a guardrail against over-scoring task-answering behavior.
- Not a strong accuracy differentiator unless the visible source is made denser, more ambiguous, or contains a rendered combined table.

## Current Aggregate After 25 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 93.5% | $0.014148 | 68.70s | 22382 |
| `gpt-5.4-nano` | 73.4% | $0.013033 | 162.72s | 27414 |

Interpretation:

- Case 025 confirms that plain multi-page raster table/legend reconstruction is too easy.
- The benchmark core should stay centered on rendered visibility semantics and visual ownership/state, not derived reasoning tasks.
- Gemini remains the clear fidelity/latency leader; GPT remains slightly cheaper but much slower and worse on visibility traps.

## Case 026: Opaque Image Over Text

Purpose: test z-order visibility. The PDF draws stale extractable approval text first, then covers it with an opaque raster approval card containing different visible values. `pypdf` extracts only the stale values from under the image; the render shows only the raster card.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 97.6% | $0.000356 | 2.02s | 600 in / 137 out |
| `gpt-5.4-nano` | 41.5% | $0.000568 | 5.66s | 1119 in / 275 out |

Useful failures:

- GPT first reconstructed the visible raster card correctly.
- GPT then appended the stale covered text from extraction: `APV-OLD-999`, `Slate Mining`, `$91,000.00`, `West-0`, `Revoked`, and `Use stale covered values`.
- Gemini reconstructed only the visible card values, but omitted the exact `OPAQUE-26` card title.

Assessment:

- Very strong benchmark direction.
- This is a clean variant of the same core problem as redactions/corrections/crop/clipping/invisible render mode: providers that merge raw extraction with vision can leak non-visible content.
- Keep this as a core visibility-semantics case.

## Current Aggregate After 26 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 93.7% | $0.014504 | 70.72s | 23119 |
| `gpt-5.4-nano` | 72.2% | $0.013601 | 168.39s | 28808 |

Interpretation:

- Case 026 strengthens the visibility-semantics thesis.
- GPT's failure is not that it cannot see the visible card; it can. The failure is that it also includes stale non-visible extraction text.
- Gemini is now clearly better on fidelity and latency across this exploratory suite, despite GPT remaining slightly cheaper in total dollars.

## Case 027: Hidden Optional Content Layer

Purpose: test PDF optional content groups/layers. The visible page shows a dispatch table, while a conflicting disabled PDF layer contains stale values. Local validation: Poppler renders only the visible table, while `pypdf` extracts both visible and disabled-layer text.

Result after reweighting blank output lower:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 26.5% | $0.000055 | 3.43s | 104 in / 27 out |
| `gemini-3.1-flash-lite` | 26.5% | $0.000168 | 1.55s | 600 in / 12 out |

Useful failures:

- OpenAI returned: “The document contains no readable text or images...”
- Gemini returned: `[Image: The original document is a blank white page.]`
- Neither model leaked the hidden layer, but neither reconstructed the visible page either.

Assessment:

- Not a good high/low model differentiator in this two-model run.
- Still an important ingestion-compatibility case: provider PDF pipelines may mishandle optional content groups and treat the whole page as blank.
- Keep this as a possible “PDF feature support” case, separate from the cleaner visibility traps where models can see the page but choose whether to leak hidden extraction text.

## Current Aggregate After 27 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 91.2% | $0.014672 | 72.27s | 23731 |
| `gpt-5.4-nano` | 70.5% | $0.013655 | 171.82s | 28939 |

Interpretation:

- The optional-content-layer case reduces both averages but does not change the relative frontier.
- The strongest benchmark core is still rendered visibility where the model can see the page: crop boxes, clipping, invisible text render mode, covered text, redactions, and correction overlays.
- Optional content groups are worth tracking, but probably as a compatibility bucket rather than the main differentiation axis.

## Case 028: Reversed Glyph Order

Purpose: test whether models preserve rendered text order when important values are drawn glyph-by-glyph in reverse PDF content order. Local extraction sees the values as separated reversed glyphs; Poppler renders normal values.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 100.0% | $0.000169 | 6.05s | 177 in / 107 out |
| `gemini-3.1-flash-lite` | 100.0% | $0.000325 | 2.40s | 600 in / 117 out |

Findings:

- Both models reconstructed all visible values exactly: `KIT-904A`, `BATCH-17Q`, `LANE-C3`, `SUM-8F2`, and `HOLD-42`.
- Neither leaked or used the reversed glyph extraction artifacts.
- This case is saturated for the two cheap models.

Assessment:

- Useful negative result: simple reversed glyph/content-stream order is not enough to differentiate these providers.
- Do not make this a core benchmark axis unless combined with denser layout, overlapping text, or a more realistic extraction-order failure.

## Current Aggregate After 28 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 91.5% | $0.014997 | 74.67s | 24448 |
| `gpt-5.4-nano` | 71.6% | $0.013825 | 177.87s | 29223 |

Interpretation:

- The aggregate gap remains dominated by visibility-semantics and raster/detail ownership cases.
- Case 028 slightly raises both averages and reinforces that extraction-order weirdness alone may already be handled by provider pipelines.
- Next useful direction should return to realistic visual ownership/state or visibility traps rather than more simple stream-order cases.

## Case 029: Small-Symbol Triage Board

Purpose: test row ownership of small visual symbols in an image-only table with near-duplicate row IDs, owners, and item names. Local extraction contains only shell text; all rows, symbols, statuses, and routes are raster-only.

Result after adding a small penalty for hallucinated external image URLs:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 96.0% | $0.000728 | 3.32s | 600 in / 385 out |
| `gpt-5.4-nano` | 64.6% | $0.000725 | 10.38s | 1077 in / 408 out |

Useful failures:

- GPT preserved the overall table but blurred near-duplicates: `R-140` became Mira Chen/valve kit instead of Mira Chan/value kit, and `R-014`/`R-041` became Valer Ortiz rather than Vale/Vela Ortiz.
- GPT described the red diamond as a red circle/X, missing the exact symbol type.
- Gemini reconstructed all row bindings correctly, but hallucinated an external image URL in the Markdown image target.

Assessment:

- Strong differentiator and realistic: small icons/status badges in screenshots are common document content.
- This complements visibility-semantics cases by stressing image-only row binding rather than hidden text leakage.
- Keep this style, but future variants should include fake-link penalties and maybe more cramped symbols only if the render remains objectively readable.

## Current Aggregate After 29 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 91.6% | $0.015725 | 78.00s | 25433 |
| `gpt-5.4-nano` | 71.3% | $0.014550 | 188.25s | 30708 |

Interpretation:

- Small visual row-state ownership is a useful second core axis after rendered visibility semantics.
- Gemini remains much faster and more faithful; GPT remains slightly cheaper but loses heavily on image-only row details.
- The fake external URL issue should be treated as a fidelity error in image-description cases.

## Case 030: Overstamped Status Table

Purpose: test row-specific visible stamps in an image-only table with near-duplicate lot IDs and owner names. The PDF text layer has only shell text; the table is raster-only.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 100.0% | $0.000643 | 8.76s | 1079 in / 342 out |
| `gemini-3.1-flash-lite` | 100.0% | $0.000648 | 3.05s | 600 in / 332 out |

Findings:

- Both models reconstructed every row correctly, including printed status, visible stamp, and final visible state.
- Both handled near-duplicate lot IDs (`LOT-88A`/`LOT-88B`, `LOT-8BA`/`LOT-8AB`, `LOT-80A`/`LOT-08A`) correctly.

Assessment:

- Saturated. Large, explicit row stamps are too easy for both providers.
- The useful stress direction is not “stamps” by itself; it is smaller row-state symbols, cramped ownership, or visually competing marks.
- Keep Case 029-style small-symbol ownership over this cleaner stamp table if we need a compact differentiator.

## Current Aggregate After 30 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 91.9% | $0.016373 | 81.04s | 26365 |
| `gpt-5.4-nano` | 72.3% | $0.015193 | 197.01s | 32129 |

Interpretation:

- Large, clean visual overlays saturate; small-symbol ownership still creates useful separation.
- Gemini remains the fidelity/latency leader; GPT remains slightly cheaper but much slower and less reliable on visual detail cases.

## Case 031: Dense Checkbox Matrix

Purpose: test checked/unchecked state reconstruction in an image-only matrix with near-duplicate ticket labels, accounts, and findings. Local extraction contains only shell text; the matrix rows are raster-only.

Result after scorer cleanup to accept blank Markdown cells as faithful unchecked boxes:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 100.0% | $0.000652 | 5.92s | 1073 in / 350 out |
| `gemini-3.1-flash-lite` | 40.2% | $0.000456 | 2.54s | 600 in / 204 out |

Useful failures:

- GPT reconstructed the full checkbox matrix faithfully, using blank cells for unchecked states and checked icons for selected states.
- Gemini summarized the image but did not reconstruct the row-level matrix.
- Gemini again hallucinated an external image URL in the Markdown image target.

Assessment:

- Strong differentiator, but in the opposite direction from the small-symbol case: GPT wins because it produced the actual table.
- This suggests scoring should accept faithful checkbox-table conventions, not require every unchecked cell to be verbalized.
- Checkbox matrices are worth keeping as a separate visual-state axis because output style matters: summary is not enough for Doc2MD.

## Current Aggregate After 31 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 90.2% | $0.016829 | 83.59s | 27169 |
| `gpt-5.4-nano` | 73.2% | $0.015845 | 202.92s | 33552 |

Interpretation:

- Case 031 is useful because it exposes a Gemini failure mode: high-level image summary instead of faithful table reconstruction.
- The aggregate still favors Gemini, but not all visual-state cases do.
- Benchmark scoring needs to reward faithful Markdown conventions such as empty checkbox cells, while penalizing summary-only image descriptions and fake external image URLs.

## Case 032: Checkbox Matrix Transcription Cue

Purpose: A/B test against Case 031. Same image-only checkbox matrix shape, but the visible image and shell action explicitly say to reconstruct/transcribe the table row by row rather than summarize it.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `vertex-gemini-3.1-flash-lite` | 100.0% | $0.000572 | 2.50s | 600 in / 281 out |
| `gpt-5.4-nano` | 100.0% | $0.000620 | 9.08s | 1076 in / 324 out |

Findings:

- Gemini switched from summary-only in Case 031 to full row-level table reconstruction here.
- GPT remained correct and used explicit checked/unchecked checkbox glyphs.
- The visible document instruction changed output style materially.

Assessment:

- Useful diagnostic pair with Case 031.
- For Doc2MD, benchmark documents should generally not rely on “please transcribe this table” cues, but such cues reveal when a model is capable yet defaults to summary.
- Scoring should distinguish capability failure from output-style failure where possible.

## Current Aggregate After 32 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 90.6% | $0.017400 | 86.08s | 28050 |
| `gpt-5.4-nano` | 74.0% | $0.016466 | 212.01s | 34952 |

Interpretation:

- The Case 031/032 pair is important: Gemini can reconstruct the checkbox matrix, but may choose summary unless the document strongly cues table transcription.
- GPT is slower and more token-heavy, but more consistent on this checkbox-matrix pair.
- The best final benchmark should include cases that do not over-cue the desired output style, because Doc2MD requires faithful reconstruction by default.

## Case 033: Action Ledger Stamps

Purpose: test whether the Case 031 summary-vs-table failure generalizes to a different image-only worksheet: row-level checkboxes plus visible stamps, near-duplicate case IDs, and no explicit transcription cue beyond the normal Doc2MD instruction.

Result after scorer cleanup to accept `✅` and `⬜` checkbox glyphs:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 100.0% | $0.000709 | 6.94s | 1083 in / 394 out |
| `gemini-3.1-flash-lite` | 41.1% | $0.000390 | 2.18s | 600 in / 160 out |

Useful failures:

- GPT reconstructed the full table faithfully, using emoji checkbox glyphs for checked and unchecked cells.
- Gemini produced only a high-level image description with column names and stamp labels, but omitted row-level case/client/issue/state reconstruction.
- This repeats the Case 031 behavior on a new layout, so it is likely a real output-style weakness rather than a one-off.

Assessment:

- Strong differentiator for Doc2MD because summary-only image descriptions lose core document information.
- Keep this axis: image-only operational worksheets with stateful cells and no special transcription cue.
- Scoring must keep accepting common checkbox conventions while requiring row-level ownership.

## Current Aggregate After 33 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 89.1% | $0.017790 | 88.26s | 28810 |
| `gpt-5.4-nano` | 74.8% | $0.017175 | 218.95s | 36429 |

Interpretation:

- Gemini still leads aggregate fidelity and latency, but the un-cued worksheet/table reconstruction axis now clearly favors GPT.
- The emerging benchmark should include both rendered-visibility traps, where Gemini dominates, and un-cued visual table reconstruction, where GPT is currently more consistent.
- This split is useful: Doc2MD should not collapse into a single OCR-like dimension or a single provider-favored case family.

## Case 034: Action Ledger Transcription Cue

Purpose: A/B test against Case 033. Same image-only action ledger, but the visible image and shell action explicitly say to reconstruct the table itself with every checkbox and stamp cell.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000651 | 2.55s | 600 in / 334 out |
| `gpt-5.4-nano` | 100.0% | $0.000677 | 7.59s | 1078 in / 369 out |

Findings:

- Gemini switched from summary-only in Case 033 to a faithful row-level Markdown table.
- GPT remained faithful and used checkbox glyphs.
- This mirrors the Case 031/032 pair: Gemini is capable, but its default output style may underserve Doc2MD unless the document itself strongly cues table reconstruction.

Assessment:

- Useful diagnostic pair with Case 033.
- The final benchmark should include both cued and un-cued variants sparingly: cued variants isolate capability, while un-cued variants test whether models naturally satisfy the Doc2MD contract.

## Current Aggregate After 34 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 89.4% | $0.018441 | 90.81s | 29744 |
| `gpt-5.4-nano` | 75.5% | $0.017852 | 226.53s | 37876 |

Interpretation:

- The A/B pattern is now replicated across two different visual table layouts.
- Gemini is faster and usually more faithful on visibility semantics, but it has a consistent un-cued image-table summarization failure.
- GPT is slower but more table-reconstruction oriented on these worksheet cases.

## Case 035: Hidden Annotation Contents

Purpose: test a non-rendered PDF annotation-content trap. The visible page contains a short memo; the PDF object tree contains a hidden `/Text` annotation with stale popup contents saying `DENY ROUTE Q-99`, `Mira Chen`, and `priority override urgent popup`.

Validation:

- `pdftotext` extracts only the visible memo text.
- The rendered page does not show the annotation icon or contents.
- `pypdf` confirms one hidden text annotation object with the stale contents.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 100.0% | $0.000139 | 4.11s | 172 in / 84 out |
| `gemini-3.1-flash-lite` | 100.0% | $0.000285 | 2.07s | 600 in / 90 out |

Findings:

- Neither model leaked the hidden annotation contents.
- Both reconstructed the visible memo faithfully.

Assessment:

- Useful negative result. Hidden annotation contents are not a differentiator for these two provider pipelines in this setup.
- If revisited, make the annotation visible as an icon but closed, or use other metadata channels such as `/ActualText`, attachment descriptions, or tagged-PDF alternate text.

## Current Aggregate After 35 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 89.7% | $0.018726 | 92.88s | 30434 |
| `gpt-5.4-nano` | 76.2% | $0.017991 | 230.65s | 38132 |

Interpretation:

- The aggregate changed only because Case 035 saturated.
- Hidden-annotation leakage is less promising than visibility traps involving rendered overlays, crop boxes, clipping masks, invisible text render mode, or opaque images over stale text.
- The strongest current axes remain rendered visibility semantics and un-cued image-table reconstruction.

## Case 036: Stale ActualText Layer

Purpose: test stale `/ActualText` marked-content alternate text. The rendered page visibly says `APPROVE ROUTE T-31`, `Lena Ortiz`, and `Blue-7`, but the PDF `/ActualText` says `DENY ROUTE Z-99`, `Mira Chen`, and `Red-4`.

Validation:

- `pdftotext` extracts the stale `/ActualText` values.
- The rendered page visibly shows the correct printed values.
- The content stream contains both the visible text and stale `/ActualText`.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000275 | 2.61s | 600 in / 83 out |
| `gpt-5.4-nano` | 12.9% | $0.000137 | 4.59s | 170 in / 82 out |

Useful failures:

- GPT copied the stale `/ActualText`: `DENY ROUTE Z-99`, `Mira Chen`, and `Red-4`.
- Gemini followed the rendered page and returned the visible printed values.

Assessment:

- Strong visibility-semantics case and more realistic than a totally hidden annotation.
- This suggests provider pipelines differ materially on whether they trust accessibility/alternate text over rendered glyphs.
- Keep this axis; consider variants with stale `/Alt` on figures or tagged-table cells.

## Current Aggregate After 36 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 90.0% | $0.019001 | 95.49s | 31117 |
| `gpt-5.4-nano` | 74.5% | $0.018127 | 235.23s | 38384 |

Interpretation:

- Case 036 is one of the cleanest provider-pipeline differentiators so far.
- The visibility axis should include alternate-text traps, not just visual overlays and clipping.
- Cost alone is misleading here: GPT was cheaper because it appears to have used a text extraction path, but that path produced the wrong document.

## Case 037: Stale Figure Alt Text

Purpose: test stale `/Alt` text on a raster figure. The visible image says `SHIP BATCH C-71`, `Noor Vale`, `4 C cold chain`, and `Green lane`; the PDF figure `/Alt` says `SCRAP BATCH X-09`, `Mira Chen`, `22 C ambient`, and `Red lane`.

Validation:

- `pdftotext` extracts only the shell text, not the visible raster facts or stale `/Alt`.
- The rendered page visibly shows the correct release card.
- The content stream wraps the image `Do` operator in `/Figure << /Alt (...) >> BDC`.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000350 | 2.51s | 600 in / 133 out |
| `gpt-5.4-nano` | 100.0% | $0.000400 | 5.39s | 1080 in / 147 out |

Findings:

- Neither model copied the stale figure `/Alt` text.
- Both described the visible raster figure correctly.

Assessment:

- Useful negative result: stale figure `/Alt` does not reproduce the Case 036 `/ActualText` failure.
- For now, `/ActualText` is the stronger metadata trap. Figure alt text may need tagged-PDF structure-tree wiring, not just marked content, to affect provider extraction.

## Current Aggregate After 37 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 90.2% | $0.019350 | 98.00s | 31850 |
| `gpt-5.4-nano` | 75.2% | $0.018527 | 240.62s | 39611 |

Interpretation:

- Case 037 slightly raises both averages because it saturated.
- The useful distinction is now sharper: stale `/ActualText` is dangerous; stale marked-content figure `/Alt` is ignored or outweighed by vision.
- Next metadata variants should focus on text-bearing marked content or structure-tree alternates rather than plain figure alt text.

## Case 038: Visible Artifact Stamp

Purpose: test whether visible text tagged as a PDF `/Artifact` is dropped. The visible page includes a red correction stamp `CORRECTED TOTAL $47,200`, while the content stream wraps that text in `/Artifact BMC ... EMC`.

Validation:

- `pdftotext` still extracts the correction stamp.
- The rendered page visibly shows the stamp.
- The content stream confirms `/Artifact` around `CORRECTED TOTAL $47,200`.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 100.0% | $0.000143 | 3.98s | 175 in / 86 out |
| `gemini-3.1-flash-lite` | 100.0% | $0.000321 | 2.35s | 600 in / 114 out |

Findings:

- Both models preserved the visible correction stamp.
- Gemini described the stamp as an image-like visual element; GPT emitted it as text. Both are faithful enough.

Assessment:

- Useful negative result. Artifact tagging alone is not enough to make visible text disappear from these provider pipelines.
- This is less promising than stale `/ActualText`; continue prioritizing cases where extractable text conflicts with rendered text.

## Current Aggregate After 38 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 90.5% | $0.019671 | 100.35s | 32564 |
| `gpt-5.4-nano` | 75.8% | $0.018670 | 244.60s | 39872 |

Interpretation:

- Case 038 saturated and mainly confirms that simple artifact tagging is not a differentiator.
- Metadata traps are only useful when they alter extraction content, as `/ActualText` did in Case 036.
- Current strongest axes remain rendered-visibility conflicts and un-cued image-table reconstruction.

## Case 039: Raster Timeline Ownership

Purpose: test spatial ownership in a raster-only timeline board with near-duplicate lane names (`Alpha Pump`/`Alpha Pump A`, `Beryl Gate`/`Beryl Gait`), multi-day bars, and single-day diamond milestones.

Validation:

- `pdftotext` extracts only the shell text; all timeline facts are image-only.
- The rendered board is readable at PDF scale.

Result after scorer cleanup to separate label ownership, milestone day placement, and true span endpoints:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 82.6% | $0.000721 | 3.25s | 600 in / 381 out |
| `gpt-5.4-nano` | 63.3% | $0.000592 | 5.37s | 1078 in / 301 out |

Useful failures:

- GPT preserved most lane labels but collapsed many multi-day bars into a single table cell, losing span endpoints.
- Gemini reconstructed most lane ownership and several spans, but still missed or under-specified some spans such as `Alpha Pump` bars and `Beryl Gait` starting on Monday.
- Neither model confused the near-duplicate lane names in the major false-positive checks.

Assessment:

- Useful realistic visual-spatial case. It does not fully break both models, but it exposes a meaningful fidelity gap around duration/span representation.
- This complements checkbox/worksheet cases: the key difficulty is not text OCR, but whether visual extent across columns is preserved in Markdown.

## Current Aggregate After 39 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 90.3% | $0.020393 | 103.60s | 33545 |
| `gpt-5.4-nano` | 75.5% | $0.019262 | 249.97s | 41251 |

Interpretation:

- Timeline/spatial cases are promising if scoring explicitly separates ownership from span duration.
- Gemini remains stronger on image-spatial fidelity, while GPT is cheaper on this case but materially less faithful.
- Future variants should increase span ambiguity carefully, not by making text smaller, but by using overlapping bars, partial-day segments, or legends that affect duration semantics.

## Case 040: Raster Half-Day Timeline

Purpose: harder variant of Case 039. Same kind of raster-only timeline, but each day is split into AM/PM halves. The model must preserve half-day placement, not just lane labels or dates.

Validation:

- `pdftotext` extracts only the shell text; all schedule facts are image-only.
- The rendered board is readable, including AM/PM headers and labels.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 41.2% | $0.000515 | 2.37s | 600 in / 243 out |
| `gpt-5.4-nano` | 38.2% | $0.000514 | 6.00s | 1084 in / 238 out |

Useful failures:

- Both models mostly described the grid and listed labels, but did not reconstruct the AM/PM placements.
- GPT hallucinated extra/misread labels such as `ref G5`, `X52`, and `gate`.
- Gemini preserved the label set better, but still omitted the actual half-day schedule.

Assessment:

- Strong hard case for both models. It is not saturated and directly targets visual extent/position semantics.
- This is a better stress direction than more metadata traps: realistic operational timelines with sub-cell placement are difficult even when text is legible.
- Scoring should keep separating label recognition from placement fidelity, because both models can see labels without reconstructing the document information.

## Current Aggregate After 40 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 89.1% | $0.020907 | 105.97s | 34388 |
| `gpt-5.4-nano` | 74.6% | $0.019776 | 255.97s | 42573 |

Interpretation:

- Case 040 lowers both averages and confirms that sub-cell visual placement is a useful benchmark axis.
- Gemini remains better overall and faster, but this case is hard for both cheap models.
- Future variants should stay realistic: shift/rota boards, Gantt charts with partial-day or partial-week blocks, and calendars where position conveys meaning.

## Case 041: Half-Day Timeline Transcription Cue

Purpose: A/B variant of Case 040. The raster board and PDF shell explicitly instruct the model to reconstruct a `Lane | Item | Start | End` table and include AM/PM in every time cell.

Validation:

- `pdftotext` extracts only the shell text; timeline facts remain image-only.
- The rendered board is readable and includes the visible table cue both above and below the raster timeline.
- The 041 scorer accepts row-per-item Markdown tables while keeping the AM/PM placement checks strict.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 88.2% | $0.000943 | 3.45s | 600 in / 529 out |
| `gpt-5.4-nano` | 23.5% | $0.000821 | 7.31s | 1093 in / 482 out |

Useful failures:

- Gemini followed the visible cue and produced the desired table, but still misread some span endpoints: `ship C71` ended at Thu PM instead of Thu AM, and `N44` was placed at Thu AM instead of Thu PM.
- GPT did not produce the requested start/end table. It misread lane names and labels, including `Berry Gate`, `K50`, and `ref G95`, and converted the chart into loose bullets.

Assessment:

- The visible cue substantially helps Gemini, moving from 41.2% on Case 040 to 88.2% on the table-cued variant.
- The same cue does not rescue GPT nano; this is a strong model-differentiating case.
- This suggests the benchmark should include paired cases: one measuring spontaneous reconstruction of visual structure, and one measuring whether explicit document instructions improve faithful Markdown reconstruction.

## Current Aggregate After 41 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 89.0% | $0.021851 | 109.42s | 35517 |
| `gpt-5.4-nano` | 73.3% | $0.020597 | 263.27s | 44148 |

Interpretation:

- Gemini remains the stronger cheap model for this benchmark, especially when the document gives visible reconstruction instructions.
- GPT nano is competitive on simple text-layer cases, but current raster schedule/table cases expose substantial visual-spatial reconstruction weakness.

## Case 042: Raster Split-Shift Rota

Purpose: raster-only rota with day columns split into `Early` and `Late` subcolumns. The model must reconstruct `Resource | Assignment | Start | End | Flag` and preserve small red conflict flags.

Validation:

- `pdftotext` extracts only shell text; assignment labels, placements, spans, and conflict flags are image-only.
- The rendered board is readable at PDF scale.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 21.8% | $0.000503 | 5.57s | 1098 in / 227 out |
| `gemini-3.1-flash-lite` | 20.0% | $0.000551 | 3.32s | 600 in / 267 out |

Useful failures:

- Neither model reconstructed the requested table.
- Gemini listed the visible labels and described the grid, but did not attach assignments to resources, dates, Early/Late shifts, or flags.
- GPT also stayed at image-summary level and misread `Rift QA` as `Rigt QA`.
- The negative checks slightly reward absence of specific wrong placements, but the substantive row/placement checks all fail.

Assessment:

- Strong hard case. Compared with Case 041, the likely added difficulty is that the board has more rows, more spans, and a separate `Flag` field encoded by small visual marks.
- This is useful, but probably too coarse as a diagnostic because both models fail before attempting row reconstruction. A follow-up should simplify one variable at a time: same rota without flags, then same rota with flags, or fewer rows with identical flags.

## Current Aggregate After 42 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 87.4% | $0.022401 | 112.74s | 36384 |
| `gpt-5.4-nano` | 72.1% | $0.021100 | 268.84s | 45473 |

Interpretation:

- Rota/schedule cases are now the clearest non-saturated direction.
- The next useful design should isolate which factor breaks reconstruction: row count, span length, split subcolumns, or small conflict markers.

## Case 043: Clean Split-Shift Rota

Purpose: simplified version of Case 042 with three rows, three days, no conflict flags, and an explicit visible instruction to create `Resource | Assignment | Start | End`.

Validation:

- `pdftotext` extracts only shell text; all assignment placements are image-only.
- The rendered board is readable and materially simpler than Case 042.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 21.2% | $0.000593 | 4.20s | 600 in / 295 out |
| `gpt-5.4-nano` | 18.8% | $0.000697 | 7.84s | 1091 in / 383 out |

Useful failures:

- Gemini described the board and named several placements in prose, but still did not produce the requested start/end table and omitted span endpoints such as `kit R7` ending on Wed 08 Early.
- GPT attempted a wide grid instead of the requested normalized table, but shifted several assignments into the wrong columns and misread `Rift QA` as `Rnift QA`.
- The simplification did not restore faithful reconstruction, which suggests the split-subcolumn grid itself is a hard axis, not only the row count or conflict flags.

Assessment:

- Clean split-shift grids are still hard for both cheap models.
- The next diagnostic should test whether the prompt/output format is the bottleneck: provide an explicit empty table scaffold in visible text, or use a source table image rather than a Gantt-style grid. If models still fail, the issue is visual cell-to-row reconstruction; if they improve, the issue is choosing the right Markdown representation.

## Current Aggregate After 43 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 85.9% | $0.022994 | 116.95s | 37279 |
| `gpt-5.4-nano` | 70.9% | $0.021797 | 276.68s | 46947 |

Interpretation:

- Case 041 showed that visible instructions can help when the model is already close to reconstructing the table.
- Cases 042 and 043 show a harder failure mode: models summarize the visual grid or choose the wrong Markdown structure instead of normalizing each visual block into start/end rows.

## Case 044: Clean Rota With Empty Scaffold

Purpose: paired diagnostic for Case 043. Same clean split-shift rota, but the PDF includes a visible blank `Resource | Assignment | Start | End` scaffold below the image. This tests whether the failure is just output-format selection.

Validation:

- `pdftotext` exposes the blank scaffold headers and action, but not the answer rows.
- The rendered source is readable: same rota image plus an empty table scaffold.
- The 044 scorer was tightened to require actual filled Markdown table rows, so image-description matches do not count as row reconstruction.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 20.7% | $0.000585 | 5.77s | 1098 in / 292 out |
| `gemini-3.1-flash-lite` | 20.7% | $0.000666 | 2.54s | 600 in / 344 out |

Useful failures:

- Neither model filled the visible scaffold.
- Gemini described several cell placements in prose, but preserved the empty table rather than completing it. It also misread `review D6` as Tue Late and `close X4` as Wed Early.
- GPT preserved the empty scaffold and summarized the board, with one label error: `swap N6` instead of `swap N5`.

Assessment:

- The bottleneck is not merely choosing a table shape. Even with a visible blank scaffold, both models treat the document as something to describe/preserve rather than converting the visual schedule into filled normalized rows.
- This is a strong benchmark axis, but scoring must distinguish "described visual board" from "faithfully reconstructed table semantics".

## Current Aggregate After 44 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 84.4% | $0.023660 | 119.49s | 38223 |
| `gpt-5.4-nano` | 69.7% | $0.022382 | 282.44s | 48337 |

Interpretation:

- For Gantt/rota visuals, explicit instructions and blank scaffolds are not enough; the hard part is converting spatial cells/spans into semantic rows.
- Next useful probe: use a source that is already a rasterized table, not a Gantt grid, to separate table OCR/reconstruction from visual-span-to-table normalization.

## Case 045: Rasterized Rota Table

Purpose: same normalized rota facts as Cases 043/044, but rendered directly as a raster-only table rather than a Gantt-style grid. This separates image-table reconstruction from visual-span-to-row normalization.

Validation:

- `pdftotext` extracts only shell text and the action; all table rows are image-only.
- The rendered raster table is clear and includes repeated resource names.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000578 | 2.64s | 600 in / 285 out |
| `gpt-5.4-nano` | 70.6% | $0.000656 | 8.13s | 1086 in / 351 out |

Useful failures:

- Gemini reconstructed the image-only table exactly.
- GPT reconstructed the table structure and most rows, but misread every `Rift QA` row as `Ritt QA`, causing all Rift row checks to fail.

Assessment:

- This cleanly separates the problem: raster table reconstruction is easy for Gemini and tractable for GPT, while Gantt/rota spatial normalization is hard for both.
- Strong benchmark direction: include paired cases where the same facts appear as a normal table and as a spatial schedule. The delta measures layout-to-semantics ability, not just OCR.

## Current Aggregate After 45 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 84.7% | $0.024237 | 122.12s | 39108 |
| `gpt-5.4-nano` | 69.7% | $0.023038 | 290.57s | 49774 |

Interpretation:

- Gemini is now clearly on the Pareto frontier among the two cheap models: higher accuracy, lower latency, and similar total cost.
- GPT’s weak point is not only image OCR; it also makes small textual substitutions in raster tables and often fails to normalize spatial schedules.

## Case 046: Merged-Cell Rota Table

Purpose: same rota facts as Case 045, but the raster table uses merged resource cells. The target Markdown should repeat the resource name on every assignment row.

Validation:

- `pdftotext` extracts only shell text and the action; all table rows are image-only.
- The rendered table is readable and clearly shows row-spanning `Nova Ops`, `Quarry Desk`, and `Rift QA` cells.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano` | 100.0% | $0.000600 | 6.51s | 1083 in / 307 out |
| `gemini-3.1-flash-lite` | 87.4% | $0.000660 | 2.95s | 600 in / 340 out |

Useful failures:

- GPT reconstructed the merged-cell image table exactly and expanded resource names correctly.
- Gemini expanded most rows but incorrectly assigned `case T2` to `Quarry Desk` instead of `Rift QA`.

Assessment:

- Merged cells are a useful realistic table variant, but not automatically harder for both models.
- This reverses the usual image-task ordering and is useful benchmark hygiene: include cases where GPT can win so the benchmark does not just measure Gemini-favored visual skills.
- The paired table cases now suggest three separable axes: ordinary raster table OCR, merged/grouped-cell ownership, and Gantt/spatial normalization.

## Current Aggregate After 46 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 84.8% | $0.024897 | 125.07s | 40048 |
| `gpt-5.4-nano` | 70.4% | $0.023638 | 297.08s | 51164 |

Interpretation:

- Gemini remains the better aggregate cheap model, but Case 046 shows GPT can beat it on specific table-structure transformations.
- The benchmark should keep paired and counterexample cases, not only cases that maximize model separation in one direction.

## Case 047: Blank Carry-Down Rota Table

Purpose: same rota facts as Cases 045/046, but repeated resource cells are visually blank after the first row in each group. The target Markdown must fill blanks from the previous visible resource.

Validation:

- `pdftotext` extracts only shell text and the action; all table rows are image-only.
- The rendered table is readable and clearly shows blank resource cells for repeated values.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000623 | 3.10s | 600 in / 315 out |
| `gpt-5.4-nano` | 36.8% | $0.000682 | 8.21s | 1086 in / 372 out |

Useful failures:

- Gemini filled every blank resource cell correctly.
- GPT preserved the blank resource cells instead of carrying down values, despite repeating the instruction. It also misread `Rift QA` as `Riff QA`.

Assessment:

- Strong realistic differentiator. Blank carry-down values are common in operational spreadsheets/tables, and faithful Markdown should expand them.
- Interesting contrast with Case 046: GPT handled merged cells perfectly but failed blank carry-down; Gemini failed one merged-cell ownership edge but handled blank carry-down perfectly.
- This suggests grouped-table semantics should be a dedicated benchmark family, with variants for repeated labels, merged cells, blank carry-down cells, and ditto marks.

## Current Aggregate After 47 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 85.1% | $0.025520 | 128.17s | 40963 |
| `gpt-5.4-nano` | 69.7% | $0.024320 | 305.29s | 52622 |

Interpretation:

- Gemini remains better on aggregate and is much faster.
- The best benchmark shape so far is paired realistic transformations: same facts shown as normal table, merged table, blank carry-down table, and spatial rota. These isolate where each model breaks.

## Case 048: Ditto-Mark Rota Table

Purpose: same rota facts as Cases 045-047, but repeated resource values are shown with a `"` ditto mark. The target Markdown must expand the ditto marks into explicit resource names.

Validation:

- `pdftotext` extracts only shell text and the action; all table rows are image-only.
- The rendered table is readable and clearly shows `"` marks in repeated resource cells.

Result:

| Model | Score | Cost | Latency | Tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 100.0% | $0.000654 | 2.84s | 600 in / 336 out |
| `gpt-5.4-nano` | 36.8% | $0.000608 | 6.52s | 1086 in / 313 out |

Useful failures:

- Gemini expanded every ditto mark correctly.
- GPT copied or misread shorthand cells instead of expanding them: `"` remained in several resource rows, one ditto mark became `W`, `kit R7` became `kill R7`, and `Rift QA` became `Riff QA`.

Assessment:

- Strong realistic differentiator, consistent with Case 047.
- Carry-down shorthand appears to be a weakness for GPT nano and a strength for Gemini flash-lite.
- Grouped-table semantics are now one of the clearest benchmark families: normal repeated labels, merged cells, blank carry-down cells, and ditto marks all test different reconstruction assumptions.

## Current Aggregate After 48 Cases

| Model | Avg score | Total cost | Total latency | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 85.4% | $0.026174 | 131.01s | 41899 |
| `gpt-5.4-nano` | 69.0% | $0.024929 | 311.81s | 54021 |

Interpretation:

- Gemini continues to dominate the Pareto view among these two cheap models: higher score, materially faster, modestly higher total cost.
- GPT's recurring failures are now clear: image text substitutions, failure to expand blank/ditto repeated-value cells, and failure to normalize spatial schedule grids.

## Design Pivot: Doc2MD-Core-25

After external benchmark research, subagent ideation, and GPT-5.5 Pro's recommendation, stop growing cases serially. The exploration above is useful evidence, but not the benchmark.

New direction:

- Build `Doc2MD-Core-25`: 25 documents, roughly 60-90 pages.
- Use 5 public calibration cases and 20 hidden scored cases.
- Keep family-level scores plus cost, latency, tokens, failure rate, and repeated-run variance.
- Use structured gold objects and typed scoring, not only regex checks or one gold Markdown string.
- Treat current generated cases as research pool / evidence for failure modes.

Strongest confirmed families so far:

- Grouped-table semantics: repeated labels, merged cells, blank carry-down cells, ditto marks.
- Spatial schedule normalization: Gantt/rota/roadmap visuals converted into semantic rows.
- Raster table reconstruction: useful paired contrast against spatial visuals.

See `docs/benchmark-design.md` for the current benchmark design.
