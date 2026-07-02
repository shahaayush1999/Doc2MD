# Doc2MD-Hard-11 Calibration Results

These results are from the current generated `Doc2MD-Hard-11` suite, version `0.3.0`. Raw run outputs live under ignored `runs/` directories and are not committed.

`Doc2MD-Hard-11` supersedes the earlier `Doc2MD-Hard-12` calibration. The older suite was too saturated, especially by older OpenAI models, and several simple cases were removed from the active manifest.

## Limited Calibration

This is not a final leaderboard. To control cost, only three calibration models were run after the suite revision.

| Model | Score | Family minimum | Cost | Total latency | Avg latency | Input tokens | Output tokens | Failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `vertex-gemini-3.1-flash-lite` | 89.2 | 0.0 | $0.004921 | 23.820s | 2.165s | 7,172 | 2,085 | 0% |
| `openai-gpt-5-nano` | 76.5 | 0.0 | $0.001687 | 57.247s | 5.204s | 14,539 | 2,399 | 0% |
| `openai-gpt-4o-mini` | 71.4 | 0.0 | $0.043476 | 75.368s | 6.852s | 282,389 | 1,862 | 0% |

## Family Scores

| Family | Gemini 3.1 Flash Lite | GPT-5 Nano | GPT-4o Mini |
| --- | ---: | ---: | ---: |
| Visibility | 100.0 | 100.0 | 76.9 |
| Spatial | 0.0 | 0.0 | 0.0 |
| Layout | 100.0 | 77.7 | 80.9 |
| Forms | 100.0 | 86.7 | 100.0 |
| Tables | 81.5 | 66.7 | 66.7 |
| Visual | 100.0 | 100.0 | 60.9 |

## Current Read

The revised suite has materially better separation than the earlier Hard-12 slice:

- GPT-5 Nano dropped from `87.0` on the old active suite to `76.5`.
- GPT-4o Mini dropped from `84.8` to `71.4`.
- Gemini 3.1 Flash Lite still scores high at `89.2`, which is acceptable for a cheap strong visual model but still leaves room for harder cases.

The highest-signal cases so far are:

- `H03-raster-gantt`: all three tested models fail exact visual span reconstruction.
- `H13-scientific-two-column`: GPT-5 Nano scores `64.0`; GPT-4o Mini scores `40.0`.
- `H15-landscape-heatmap`: GPT-5 Nano and GPT-4o Mini score `66.7`; Gemini 3.1 Flash Lite scores `81.5`.
- `H16-multipanel-metrics`: GPT-4o Mini scores `60.9` while the newer models pass.

Still-saturated or weaker-signal cases:

- `H01` and `H02` remain useful visibility policy checks, but they are not enough for model differentiation.
- `H14-three-column-poster` is currently saturated by the tested models and may need replacement or harder scoring.
- `H16` separates GPT-4o Mini, but GPT-5 Nano and Gemini 3.1 both solve it.

Next calibration should not run the full model matrix yet. The next useful checks are `gpt-5.4-nano` and `gemini-3.5-flash` on this revised suite, after one more pass replacing or hardening saturated cases.
