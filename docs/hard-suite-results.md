# Doc2MD-Hard-11 Calibration Results

These results are from the current generated `Doc2MD-Hard-11` suite, version `0.3.0`. Raw run outputs live under ignored `runs/` directories and are not committed.

`Doc2MD-Hard-11` supersedes the earlier `Doc2MD-Hard-12` calibration. The older suite was too saturated, especially by older OpenAI models, and several simple cases were removed from the active manifest.

## Calibration

This is the first full calibration of the revised suite across the current comparison set. It is still not a public leaderboard; each score is from one run, and repeat variance should be measured before publishing claims.

| Model | Score | Family minimum | Cost | Total latency | Avg latency | Input tokens | Output tokens | Failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `vertex-gemini-3.5-flash` | 100.0 | 100.0 | $0.033996 | 31.795s | 2.890s | 7,172 | 2,582 | 0% |
| `vertex-gemini-3.1-flash-lite` | 90.9 | 0.0 | $0.004904 | 24.825s | 2.257s | 7,172 | 2,074 | 0% |
| `openai-gpt-5.4-nano` | 82.9 | 0.0 | $0.004846 | 64.466s | 5.861s | 12,009 | 1,955 | 0% |
| `openai-gpt-5-nano` | 75.4 | 0.0 | $0.001714 | 59.115s | 5.374s | 14,539 | 2,467 | 0% |
| `openai-gpt-4o-mini` | 75.1 | 0.0 | $0.043515 | 79.125s | 7.193s | 282,389 | 1,927 | 0% |

## Family Scores

| Family | Gemini 3.5 Flash | Gemini 3.1 Flash Lite | GPT-5.4 Nano | GPT-5 Nano | GPT-4o Mini |
| --- | ---: | ---: | ---: | ---: | ---: |
| Visibility | 100.0 | 100.0 | 100.0 | 100.0 | 76.9 |
| Spatial | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Layout | 100.0 | 100.0 | 84.0 | 71.6 | 80.9 |
| Forms | 100.0 | 100.0 | 92.0 | 86.7 | 100.0 |
| Tables | 100.0 | 100.0 | 100.0 | 85.2 | 85.2 |
| Visual | 100.0 | 100.0 | 100.0 | 100.0 | 82.6 |

## Current Read

The revised suite has materially better separation than the earlier Hard-12 slice:

- GPT-5 Nano dropped from `87.0` on the old active suite to `75.4`.
- GPT-4o Mini dropped from `84.8` to `75.1`.
- GPT-5.4 Nano scores `82.9`, above GPT-5 Nano but clearly below Gemini 3.1 Flash Lite.
- Gemini 3.5 Flash scores `100.0`, which is expected for the current best public visual model and gives a useful ceiling.

The highest-signal cases so far are:

- `H03-raster-gantt`: Gemini 3.5 Flash gets `100`; all other tested models get `0`.
- `H13-scientific-two-column`: Gemini models get `100`; OpenAI models range from `40.0` to `76.0`.
- `H14-three-column-poster`: the new borderless team matrix catches GPT-5 Nano's row/column transpose (`54.5`) and a smaller GPT-5.4 Nano structure/name issue (`87.9`), while Gemini models and GPT-4o Mini pass.
- `H15-landscape-heatmap`: Gemini models get `100`; OpenAI nano/mini models get `85.2`.
- `H16-multipanel-metrics`: GPT-4o Mini gets `82.6`; newer models pass.

Still-saturated or weaker-signal cases:

- `H01` and `H02` remain useful visibility policy checks, but they are not enough for model differentiation.
- `H16` separates GPT-4o Mini, but the newer models solve it.

Next work should focus on repeat variance and one or two replacement cases for still-saturated checks, not on adding more total cases.
