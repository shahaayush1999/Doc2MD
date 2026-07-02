# Doc2MD-Hard-15 Calibration Status

The current generated suite is `Doc2MD-Hard-15`, version `0.5.0`. It has not yet been fully calibrated across the comparison model set.

Version `0.5.0` makes two important changes:

- Adds `facts.json` beside each `gold.md`. The evaluator now marks weighted fact obligations as `correct`, `partial`, `incorrect`, or `missing`, and the headline accuracy score is computed from those labels.
- Adds four compound document-reasoning cases: financial ARR bridge, insurance EOB, clinic floor-plan punch list, and conference schedule grid.

The previous `Doc2MD-Hard-11` v0.4.0 results are now historical and should not be compared directly with v0.5.0 results. The suite size changed from 11 to 15 cases, and the scoring method changed from holistic gold-key accuracy to weighted fact-obligation accuracy.

## Historical v0.4.0 Reference

These one-run scores are retained only as context for why v0.5.0 was created:

| Model | v0.4.0 Score | v0.4.0 Accuracy |
| --- | ---: | ---: |
| `vertex-gemini-3.5-flash` | 96.9 | 97.7 |
| `vertex-gemini-3.1-flash-lite` | 92.5 | 92.3 |
| `openai-gpt-5.4-nano` | 90.5 | 90.5 |
| `openai-gpt-5-nano` | 83.7 | 83.2 |
| `openai-gpt-4o-mini` | 75.5 | 73.2 |

The spread was too small because many cases were single-challenge pages. v0.5.0 shifts toward compound pages where table structure, visual relations, legends, numeric facts, footnotes, and reading order interact.

## Smoke Test

The fact-aware scorer was smoke-tested on the existing `openai-gpt-5-nano` run outputs for the 11 overlapping cases. It produced harsher scores on cases where previous holistic judging was too generous, especially `H03-raster-gantt`, which dropped to `9.5` because the weighted task/owner/time obligations were missing or wrong.

This is not a leaderboard result because the four new v0.5.0 cases have not been run for that model.

## Next Calibration

Run the full v0.5.0 suite for:

- `vertex-gemini-3.5-flash`
- `vertex-gemini-3.1-flash-lite`
- `openai-gpt-5.4-nano`
- `openai-gpt-5-nano`
- `openai-gpt-4o-mini`

For benchmark-development calibration, run at least three repetitions before treating close scores as meaningful. For publication-quality claims, use five repetitions and report mean, standard deviation, confidence intervals, family scores, worst-run score, cost, latency, and Pareto frontiers.
