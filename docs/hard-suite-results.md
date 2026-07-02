# Doc2MD-Hard-15 Calibration Result

`Doc2MD-Hard-15` v0.5.0 is a failed calibration. It should not be released as the public benchmark.

## Full-Bench Scores

| Model | Score | Cost | Time | Output tokens |
| --- | ---: | ---: | ---: | ---: |
| `vertex-gemini-3.1-flash-lite` | 89.6 | $0.007523 | 38.278s | 3,385 |
| `openai-gpt-5.4-nano` | 84.2 | $0.007224 | 100.334s | 3,160 |
| `openai-gpt-4o-mini` | 81.1 | $0.059601 | 106.295s | 3,067 |

The benchmark does not produce enough spread. GPT-4o Mini should not be within `8.5` points of Gemini 3.1 Flash Lite.

## Per-Case Scores

| ID | Case | Gemini 3.1 Flash Lite | GPT-5.4 Nano | GPT-4o Mini | Spread |
| --- | --- | ---: | ---: | ---: | ---: |
| H01 | Hidden Stale Release Card | 99.3 | 100.0 | 100.0 | 0.7 |
| H02 | Opaque Stale Shipment Overlay | 100.0 | 61.9 | 100.0 | 38.1 |
| H03 | Raster Gantt Shift Schedule | 12.0 | 16.0 | 44.5 | 32.5 |
| H07 | Overlapping GTM Timeline Slide | 77.7 | 70.7 | 67.0 | 10.7 |
| H11 | Two-Column Incident Report | 98.8 | 99.3 | 84.3 | 15.0 |
| H12 | Bilingual Service Credit | 99.5 | 94.1 | 100.0 | 5.9 |
| H13 | Scientific Paper With Embedded Table And Figure | 98.3 | 89.3 | 84.0 | 14.3 |
| H14 | Borderless Team Matrix Pitch Slide | 100.0 | 100.0 | 50.1 | 49.9 |
| H15 | Landscape Heatmap Escalation Plan | 100.0 | 100.0 | 35.4 | 64.6 |
| H16 | Multi-Panel Metrics Report | 67.2 | 42.3 | 81.7 | 39.4 |
| H17 | Redlined Data Processing Addendum | 98.5 | 97.8 | 97.8 | 0.7 |
| H18 | Financial ARR Bridge Board Pack | 100.0 | 98.8 | 88.0 | 12.0 |
| H19 | Insurance Explanation of Benefits | 94.2 | 99.3 | 100.0 | 5.8 |
| H20 | Clinic Floor-Plan Punch List | 98.3 | 100.0 | 98.5 | 1.7 |
| H21 | Conference Schedule Grid | 100.0 | 93.8 | 85.8 | 14.2 |

## Diagnosis

The current suite is too saturated because most pages are clean, compact, and single-challenge. OCR plus straightforward reconstruction is enough for an old multimodal model to score highly.

Saturated or weak cases:

- H01, H12, H17, H19, H20 are effectively solved.
- H11, H13, H18, H21 are not hard enough.
- H03 and H16 have inverted or suspicious model ordering and should be rebuilt before they are trusted.

Useful separators:

- H14 works because it requires dense column binding.
- H15 works because it requires dense visual table semantics.
- H07 is directionally useful but needs much harder layout and span binding.

## Decision

Do not create multiple public benchmark variants. Consolidate toward one release suite: `Doc2MD-Core-16`.

Use `Doc2MD-Hard-15` only as development evidence. The release suite should replace saturated cases instead of adding more cases on top.
