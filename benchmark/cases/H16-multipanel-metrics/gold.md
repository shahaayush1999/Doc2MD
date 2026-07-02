# Multi-Panel Metrics Report

Operations metrics: panels must be described inline, not summarized.

## Panel A. Queue depth

Queue depth rises every day with values 12, 18, 29, 41, and 47. It ends at 47 on Friday.

## Panel B. Defect mix

Red means severe and blue means minor. Segment labels should be used, not total bar height.

| Lane | Minor / blue | Severe / red |
| --- | ---: | ---: |
| Ingest | 12 | 5 |
| Visual | 21 | 19 |
| Tables | 10 | 17 |

Visual has the most severe defects, with 19 severe defects. Tables has 17 severe defects and does not have the most severe defects.

## Panel C. Owner matrix

| Owner | Open | Aged | SLA |
| --- | ---: | ---: | --- |
| Noor | 14 | 6 | risk |
| Mira | 9 | 1 | ok |
| Ken | 24 | 11 | risk |

Reviewer instruction: describe each panel separately, then state one cross-panel warning. Do not copy panel titles as a substitute for chart facts.

Cross-panel warning: Ken has the highest aged count at 11. The defect mix warning is severe Visual defects, not total Tables defects.
