# Doc2MD-Hard-12 Calibration Results

These results are from the first calibration pass against the generated `Doc2MD-Hard-12` suite. Raw run outputs live under ignored `runs/` directories and are not committed.

## Models

| Model | Score | Family minimum | Cost | Total latency | Avg latency | Input tokens | Output tokens | Failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `vertex-gemini-3.5-flash` | 100.0 | 100.0 | $0.032127 | 29.827s | 2.486s | 8,344 | 2,179 | 0% |
| `vertex-gemini-3.1-flash-lite` | 91.7 | 0.0 | $0.004696 | 23.970s | 1.998s | 8,344 | 1,740 | 0% |
| `openai-gpt-5.4-nano` | 89.6 | 0.0 | $0.004819 | 70.093s | 5.841s | 14,028 | 1,611 | 0% |
| `openai-gpt-5-nano` | 87.0 | 0.0 | $0.001568 | 59.299s | 4.942s | 17,018 | 1,792 | 0% |
| `openai-gpt-4o-mini` | 84.8 | 0.0 | $0.050999 | 78.346s | 6.529s | 333,567 | 1,607 | 0% |

## Family Scores

| Family | Gemini 3.5 Flash | Gemini 3.1 Flash Lite | GPT-5.4 Nano | GPT-5 Nano | GPT-4o Mini |
| --- | ---: | ---: | ---: | ---: | ---: |
| Visibility | 100.0 | 100.0 | 100.0 | 100.0 | 76.9 |
| Spatial | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Tables | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| Forms | 100.0 | 100.0 | 97.3 | 97.3 | 100.0 |
| Visual | 100.0 | 100.0 | 83.3 | 100.0 | 100.0 |
| Layout | 100.0 | 100.0 | 100.0 | 75.9 | 82.2 |

## Current Read

The suite is mostly saturated by the best tested public model. `vertex-gemini-3.5-flash` scores 100/100. That is not automatically a failure if the benchmark is used to find a Pareto frontier, but it means this suite is not yet strong enough to be the final benchmark.

The meaningful differentiator is `H03-raster-gantt`: Gemini 3.5 Flash reconstructs exact task/owner/start/end rows from a raster Gantt chart, while Gemini 3.1 Flash Lite, GPT-5.4 Nano, GPT-5 Nano, and GPT-4o Mini do not. GPT-5.4 Nano also misses the `Median repair: 18.6h` KPI binding in `H06-ops-dashboard` and changes `SRV-88-ES` to `SRV-88-FS` in `H12-bilingual-credit`. GPT-5 Nano is lower than GPT-5.4 Nano on this single run, mostly from layout/reading-order misses; `reasoning: none` is unsupported for GPT-5 Nano, so this run uses `minimal`. GPT-4o Mini is lower again, but still scores 84.8, which is too high for an older weak model if this suite is meant to separate capability sharply. Its run also used far more input tokens than the GPT-5 family runs, so provider PDF handling and cost are confounded with model quality.

This is enough to validate one useful case pattern, but not enough to treat the current suite as a benchmark leaderboard. The next useful step is to replace saturated cases with more cases like H03: realistic visual-to-structure transformations where superior visual reasoners score cleanly higher without relying on adversarial tricks.
