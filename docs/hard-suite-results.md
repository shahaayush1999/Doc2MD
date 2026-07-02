# Doc2MD-Hard-11 Calibration Results

These results are from the current generated `Doc2MD-Hard-11` suite, version `0.4.0`. Raw run outputs live under ignored `runs/` directories and are not committed.

Version `0.4.0` switches the primary score from deterministic checklist scoring to gold-answer-key comparison with a Gemini 3.1 Flash Lite judge. Each case's `gold.md` is the source of truth. The deterministic checks remain in `score.json` as an audit signal, but they do not determine the headline score.

These scores are not directly comparable with the earlier `0.3.1` deterministic calibration. Each score below is from one judged run; repeat variance should be measured before publishing leaderboard claims.

## Calibration

| Model | Score | Accuracy | Family minimum | Model cost | Judge cost | Total latency | Avg latency | Failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `vertex-gemini-3.5-flash` | 96.9 | 97.7 | 86.5 | $0.034167 | $0.006243 | 31.333s | 2.848s | 0% |
| `vertex-gemini-3.1-flash-lite` | 92.5 | 92.3 | 46.5 | $0.005192 | $0.006633 | 26.005s | 2.364s | 0% |
| `openai-gpt-5.4-nano` | 90.5 | 90.5 | 66.5 | $0.005022 | $0.007125 | 66.212s | 6.019s | 0% |
| `openai-gpt-5-nano` | 83.7 | 83.2 | 40.5 | $0.001754 | $0.007686 | 62.513s | 5.683s | 0% |
| `openai-gpt-4o-mini` | 75.5 | 73.2 | 30.5 | $0.043617 | $0.007510 | 81.552s | 7.414s | 0% |

## Family Scores

| Family | Gemini 3.5 Flash | Gemini 3.1 Flash Lite | GPT-5.4 Nano | GPT-5 Nano | GPT-4o Mini |
| --- | ---: | ---: | ---: | ---: | ---: |
| Visibility | 99.5 | 99.2 | 99.4 | 99.4 | 93.8 |
| Spatial | 98.8 | 46.5 | 66.5 | 40.5 | 30.5 |
| Layout | 96.6 | 95.9 | 90.9 | 86.2 | 90.4 |
| Forms | 98.8 | 99.3 | 90.8 | 87.0 | 50.0 |
| Tables | 100.0 | 100.0 | 99.3 | 93.8 | 40.0 |
| Visual | 86.5 | 93.5 | 85.3 | 69.5 | 70.0 |

## Current Read

The gold-key judge gives better signal than the deterministic checklist for this suite:

- `H15-landscape-heatmap` now heavily penalizes GPT-4o Mini because it loses the red-slash condition and corrupts several table cells. The old checklist overestimated this response.
- `H17-redlined-contract` now heavily penalizes GPT-5 Nano because it reverses inserted/deleted text. The old checklist caught some of this, but not enough.
- `H03-raster-gantt` remains the strongest visual-spatial separator. Gemini 3.5 Flash scores `98.8`; all other tested models are weak or incomplete.
- `H16-multipanel-metrics` now separates models on whether they preserve the required cross-panel warning instead of replacing it with generic analysis.

The current ordering is more plausible than the deterministic `0.3.1` pass: Gemini 3.5 Flash leads overall, Gemini 3.1 Flash Lite remains strong, GPT-5.4 Nano is close on many text-heavy cases but weaker on visual-spatial reconstruction, and older/smaller models fall further behind.

## Evaluator Caveats

The judge is itself an LLM, so these scores have evaluator variance. It is especially important to repeat judge runs for close comparisons, and to inspect judge findings when a result contradicts qualitative review.

Using Gemini 3.1 Flash Lite as judge also means Gemini-family candidates are not evaluated by a provider-independent system. The deterministic audit and manual inspection should be used to catch suspicious self-family bias until a multi-judge or human-audited calibration exists.

Next work should focus on repeat variance for the new gold-key judge and on strengthening the remaining saturated cases, not on adding many more documents.
