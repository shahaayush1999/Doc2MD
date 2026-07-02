# Doc2MD-Hard-12 Calibration Results

These results are from the first calibration pass against the generated `Doc2MD-Hard-12` suite. Raw run outputs live under ignored `runs/` directories and are not committed.

## Models

| Model | Score | Family minimum | Cost | Total latency | Avg latency | Input tokens | Output tokens | Failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `vertex-gemini-3.1-flash-lite` | 86.8 | 0.0 | $0.004696 | 23.970s | 1.998s | 8,344 | 1,740 | 0% |
| `openai-gpt-5.4-nano` | 84.7 | 0.0 | $0.004819 | 70.093s | 5.841s | 14,028 | 1,611 | 0% |

## Family Scores

| Family | Gemini 3.1 Flash Lite | GPT-5.4 Nano |
| --- | ---: | ---: |
| Visibility | 100.0 | 100.0 |
| Spatial | 0.0 | 0.0 |
| Tables | 80.4 | 80.4 |
| Forms | 100.0 | 97.3 |
| Visual | 100.0 | 83.3 |
| Layout | 100.0 | 100.0 |

## Current Read

The suite is not saturated. Both models miss `H03-raster-gantt`, where the expected behavior is to infer exact start/end spans from a raster Gantt chart and bind them to the correct task rows. Both also miss parts of `H10-continuation-register`, where blank and ditto group cells must be expanded across pages.

Gemini is currently stronger on this small suite. GPT-5.4 Nano misses the `Median repair: 18.6h` KPI binding in `H06-ops-dashboard` and changes `SRV-88-ES` to `SRV-88-FS` in `H12-bilingual-credit`.

This is enough separation to justify building the next iteration from the hard-suite design, but not enough to treat the current numbers as a benchmark leaderboard. The next useful step is to add a small number of targeted cases only if they probe new realistic failure modes.
