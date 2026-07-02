# Doc2MD-Hard-11 Calibration Results

These results are from the current generated `Doc2MD-Hard-11` suite, version `0.3.1`. Raw run outputs live under ignored `runs/` directories and are not committed.

`Doc2MD-Hard-11` supersedes the earlier `Doc2MD-Hard-12` calibration. The older suite was too saturated, especially by older OpenAI models, and several simple cases were removed from the active manifest.

## Calibration

This is the first full calibration of the revised suite across the current comparison set. It is still not a public leaderboard; each score is from one run, and repeat variance should be measured before publishing claims.

| Model | Score | Family minimum | Cost | Total latency | Avg latency | Input tokens | Output tokens | Failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `vertex-gemini-3.5-flash` | 100.0 | 100.0 | $0.034167 | 31.333s | 2.848s | 7,172 | 2,601 | 0% |
| `vertex-gemini-3.1-flash-lite` | 84.8 | 0.0 | $0.005192 | 26.005s | 2.364s | 7,172 | 2,266 | 0% |
| `openai-gpt-5.4-nano` | 78.5 | 0.0 | $0.005022 | 66.212s | 6.019s | 12,009 | 2,096 | 0% |
| `openai-gpt-5-nano` | 70.0 | 0.0 | $0.001754 | 62.513s | 5.683s | 14,539 | 2,567 | 0% |
| `openai-gpt-4o-mini` | 63.9 | 0.0 | $0.043617 | 81.552s | 7.414s | 282,389 | 2,097 | 0% |

## Family Scores

| Family | Gemini 3.5 Flash | Gemini 3.1 Flash Lite | GPT-5.4 Nano | GPT-5 Nano | GPT-4o Mini |
| --- | ---: | ---: | ---: | ---: | ---: |
| Visibility | 100.0 | 100.0 | 100.0 | 100.0 | 76.9 |
| Spatial | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Layout | 100.0 | 86.7 | 73.9 | 58.8 | 65.3 |
| Forms | 100.0 | 100.0 | 94.5 | 90.9 | 54.5 |
| Tables | 100.0 | 100.0 | 100.0 | 85.2 | 85.2 |
| Visual | 100.0 | 100.0 | 100.0 | 100.0 | 82.6 |

## Current Read

The revised suite has materially better separation than the earlier Hard-12 slice:

- GPT-5 Nano dropped from `87.0` on the old active suite to `70.0`.
- GPT-4o Mini dropped from `84.8` to `63.9`.
- GPT-5.4 Nano scores `78.5`, above GPT-5 Nano but clearly below Gemini 3.1 Flash Lite.
- Gemini 3.5 Flash scores `100.0`, which is expected for the current best public visual model and gives a useful ceiling.

The highest-signal cases so far are:

- `H03-raster-gantt`: Gemini 3.5 Flash gets `100`; all other tested models get `0`.
- `H07-broken-pitch-slide`: now an overlapping GTM timeline. Gemini 3.5 Flash gets `100`; Gemini 3.1 Flash Lite and OpenAI models get `33.3` because they list card text but do not reconstruct visual month spans as spans.
- `H13-scientific-two-column`: Gemini models get `100`; OpenAI models range from `40.0` to `76.0`.
- `H14-three-column-poster`: the new borderless team matrix catches GPT-5 Nano's row/column transpose (`54.5`) and a smaller GPT-5.4 Nano structure/name issue (`87.9`), while Gemini models and GPT-4o Mini pass.
- `H15-landscape-heatmap`: Gemini models get `100`; OpenAI nano/mini models get `85.2`.
- `H12-bilingual-credit`: now penalizes checkbox state errors. GPT-4o Mini drops to `54.5` because it marks the pending-part checkbox as checked.
- `H16-multipanel-metrics`: GPT-4o Mini gets `82.6`; newer models pass.

Still-saturated or weaker-signal cases:

- `H01` and `H02` remain useful visibility policy checks, but they are not enough for model differentiation.
- `H16` separates GPT-4o Mini, but the newer models solve it.

Evaluator audit notes from this pass:

- Regex-looking negative checks must use raw regex patterns, not `none_check`, which intentionally escapes literals.
- H07 span checks were manually audited so month headers alone cannot satisfy visual-span reconstruction.
- H12 now scores checked and unchecked checkbox states separately.
- H17 redline negatives were narrowed to actual wrong claims, avoiding penalties for correct policy wording.

Next work should focus on repeat variance on version `0.3.1` and one more replacement for still-saturated checks, not on adding more total cases.
