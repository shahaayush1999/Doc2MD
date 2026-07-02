# GPT-5.4 Nano Repeat Variance

Model: `openai-gpt-5.4-nano`  
Reasoning: `none`  
Suite: `Doc2MD-Hard-12`  
Repeats: 3 total runs, including the existing calibration run plus two fresh reruns.

For comparison, `openai-gpt-5-nano` does not support `reasoning: none`; its one-run comparison uses `reasoning: minimal`.

## Result

| Run | Score | Cost | Latency |
| --- | ---: | ---: | ---: |
| Repeat 1 | 91.0 | $0.004819 | 70.093s |
| Repeat 2 | 89.2 | $0.004816 | 61.980s |
| Repeat 3 | 90.5 | $0.004776 | 54.396s |

Mean score: **90.23**  
Sample standard deviation: **0.93**  
Range: **1.8**

## Case Stability

| Case | Scores | Read |
| --- | --- | --- |
| H03 raster Gantt | 0, 0, 25 | Stable model weakness. It usually copies labels into a time grid instead of reconstructing exact start/end spans. |
| H12 bilingual credit | 92, 92, 92 | Stable model weakness. It consistently reads `SRV-88-ES` as `SRV-88-FS`. |
| H09 insurance form | 100, 78.9, 100 | Unstable model behavior. One run flipped `Out-of-network` from checked to unchecked. |
| H07 broken pitch slide | 100, 100, 68.8 | Unstable reading-order behavior. One run placed the sticky note before Phase 3. |

## Evaluator Fixes Found

The first variance pass exposed scorer brittleness, not just model variance:

- `18.6 h` should match `18.6h`.
- Markdown emphasis should not break text checks such as `418 jobs`.

`src/score.ts` now strips simple Markdown emphasis, HTML tags, and normalizes hour-unit spacing before scoring.

After this normalization, H06 and H11 stopped being false negatives.
