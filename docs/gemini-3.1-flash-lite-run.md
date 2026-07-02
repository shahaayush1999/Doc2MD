# Gemini 3.1 Flash Lite Baseline Run

Date: 2026-07-02

Model: `gemini-3.1-flash-lite` via `@ai-sdk/google-vertex`

Thinking config: minimal budget (`thinkingBudget: 128`)

Benchmark: `Doc2MD-Core-25` version `0.1.0`

## Result

Final deterministic check score: **100.0 / 100.0**

Family scores:

| Family | Score |
| --- | ---: |
| Text structure | 100.0 |
| Forms/tables | 100.0 |
| Tables | 100.0 |
| OCR robustness | 100.0 |
| Visual layout | 100.0 |
| Special formatting | 100.0 |

Run metrics:

| Metric | Value |
| --- | ---: |
| Cases | 25 |
| PDF pages | 69 |
| API failures | 0 |
| Failure rate | 0.0% |
| Total estimated cost | $0.019943 |
| Total elapsed time | 57.7s |
| Average elapsed time | 2.3s/case |
| Input tokens | 38,630 |
| Output tokens | 6,857 |

## Manual Inspection Notes

The first scoring pass produced 94.4. Manual review showed that most misses were benchmark/scorer issues, not model failures:

- Markdown formatting such as `**Subtotal:** $3,785.00` failed exact checks for `Subtotal: $3,785.00`.
- Heading checks were too strict about exact heading level.
- D20 asked for chart values that were not visibly printed on the chart.
- D21 diagram labels were visually truncated by the PDF renderer.

Fixes made:

- Label/value checks now tolerate normal Markdown emphasis and punctuation.
- Heading checks match heading text across heading levels.
- Chart rendering now prints value labels.
- Single-value chart series now render as normal categorical bars.
- Diagram labels now wrap instead of truncating.

After targeted reruns for D20 and D21, the model scored 100.

## Interpretation

This version of the benchmark is useful as a harness and calibration suite, but it is not yet discriminative for strong models. Gemini 3.1 Flash Lite handled:

- Born-digital text and heading structure.
- Clean financial and operational tables.
- Multi-page table continuation.
- Forms, checkboxes, receipts, and simple scan-like pages.
- Simple diagrams, timelines, and chart descriptions.
- Code blocks, equations, and bilingual structured text.

The suite is likely too easy because most documents are synthetic, clean, and text-layer heavy. The visual tasks contain enough labels that a strong model can reconstruct them without much ambiguity.

## Next Benchmark Improvements

For the next pass, keep the 25-case shape but replace or upgrade several cases:

- Add rasterized pages for a subset of visual/table cases so providers cannot rely only on PDF text extraction.
- Use denser real-world table layouts: row groups, carried-down blank cells, multi-row headers, footnotes, and continued tables with page breaks inside row groups.
- Add scoring for table grid structure, not only presence of key strings.
- Add visual fact tuples with required local associations, such as `Panel C -> hallucinated chart trend`, rather than loose document-wide term checks.
- Add negative checks for unsupported substitutions and invented labels.
- Add mild layout damage that reflects real conversions: overlapped labels, shifted PowerPoint text boxes, crop-safe callouts, and crowded dashboard cards.
- Preserve this suite as the public calibration set or smoke suite; build a harder hidden/scored suite separately.
